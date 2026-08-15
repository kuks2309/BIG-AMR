#!/usr/bin/env python3
"""can_relay 드라이버 노드 감시 — 상태 기록과 복귀 지시.

판정은 이 파일에 없다. 전부 `health.py`(순수)에 있고 여기는 **관측을 모아 넘기고 결과를
실행하는 껍데기**다 — `safety.py` ← `backend.py` 와 같은 배치다.

## 이 노드가 하지 않는 것 (의도적)

- **정지시키지 않는다.** CAN 에 쓰지 않고 판다를 열지 않는다. 정지의 근간은 펌웨어
  fail-safe 이고, 그것을 부르는 수단(심박 중단)은 백엔드가 소유한다. 감시자에게 정지
  책임을 주면 감시자가 죽는 순간 정지 수단이 사라진다 — 그래서 **감시자는 죽어도 되는
  물건**으로 만든다.
- **프로세스를 되살리지 않는다.** 재기동은 systemd 소관이다. 여기서 프로세스를 띄우면
  systemd 와 둘이 같은 프로세스를 관리하게 된다.
- **조향·구동 지령을 복원하지 않는다.** 조향은 죽어 있는 동안 Seer 가 움직였을 수 있어
  기록값을 밀어넣으면 실제와 다른 각으로 튀고, 구동은 재기동이 곧 재출발이 되면 안 된다.
  기록은 **대조용**이며 복원 대상은 제어권(`engaged`) 하나다.

## 기록 위치가 tmpfs 인 이유

조향 홈 설정은 **전원이 켜져 있는 동안만 유효**하다. 전원 사이클 뒤에 "이전엔 engaged
였다"는 기록으로 복귀하면 기준 없는 상태에서 제어권을 잡는다. tmpfs 는 재부팅 시
소멸하고, 그래도 남는 경우를 대비해 `boot_id` 를 함께 적어 대조한다.

## 인터페이스

| 방향 | 이름 | 타입 |
|---|---|---|
| 구독 | `/diagnostics` | `diagnostic_msgs/DiagnosticArray` |
| 발행 | `~/status` | `diagnostic_msgs/DiagnosticArray` (감시자 자신의 판정) |
| 호출 | `/<target>/engage` | `std_srvs/SetBool` |
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Optional

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node
from std_srvs.srv import SetBool

from .health import (DEAD, HOLD, IDLE, RESTORE, RUNNING, WAIT, ZOMBIE,
                     Observation, SupervisorConfig, boot_id, decide,
                     default_state_dir, is_outage, next_prev, next_was_down,
                     parse_diag, proc_alive, prune_stamps,
                     restore_call_expired)


class RelaySupervisor(Node):
    """`/diagnostics` 를 보고 상태를 기록하고, 재기동 후 제어권을 되돌린다."""

    def __init__(self):
        """파라미터 → 기록 경로 확보 → 구독·클라이언트·타이머."""
        super().__init__("relay_supervisor")

        p = self.declare_parameters("", [
            ("target_node", "can_relay_node"),
            ("diag_name_prefix", "can_relay"),   # DiagnosticStatus.name 접두
            ("state_dir", ""),                   # 빈 값 = default_state_dir()
            ("tick_hz", 2.0),
            ("diag_timeout_s", 3.0),
            ("restore_enabled", True),
            ("restart_limit", 3),
            ("restart_window_s", 120.0),
            ("zombie_after_s", 45.0),
            ("restore_call_timeout_s", 10.0),
            ("restore_settle_s", 3.0),
        ])
        g = {d.name: d.value for d in p}

        self.cfg = SupervisorConfig(
            diag_timeout_s=float(g["diag_timeout_s"]),
            restore_enabled=bool(g["restore_enabled"]),
            restart_limit=int(g["restart_limit"]),
            restart_window_s=float(g["restart_window_s"]),
            zombie_after_s=float(g["zombie_after_s"]),
            restore_call_timeout_s=float(g["restore_call_timeout_s"]),
            restore_settle_s=float(g["restore_settle_s"]),
        )
        self._target = str(g["target_node"])
        self._prefix = str(g["diag_name_prefix"])

        state_dir = str(g["state_dir"]) or default_state_dir()
        self._state_path = os.path.join(state_dir, "state.json")
        try:
            os.makedirs(state_dir, exist_ok=True)
        except OSError as exc:
            self.get_logger().error(
                f"상태 기록 디렉터리를 만들지 못했다 ({state_dir}: {exc}) — "
                f"감시는 계속하되 복귀는 되지 않는다")

        self._boot = boot_id()
        self._prev = self._load()
        self._cur: Optional[dict] = None
        self._last_diag: Optional[float] = None     # monotonic
        self._was_down = False
        self._restore_stamps: list = list(
            (self._prev or {}).get("restore_stamps") or [])
        self._verdict = WAIT
        self._pending = None            # 진행 중인 engage 호출 future
        self._pending_since = None      # 그 호출을 보낸 시각(monotonic)
        self._cur_seen_since = None     # 두절 후 진단이 다시 흐르기 시작한 시각(monotonic)
        self._last_saved = None         # 마지막으로 기록한 내용의 지문(내용 불변 시 재기록 생략)

        self.sub_diag = self.create_subscription(
            DiagnosticArray, "/diagnostics", self._on_diag, 10)
        self.pub_status = self.create_publisher(DiagnosticArray, "~/status", 10)
        self.cli_engage = self.create_client(SetBool, f"/{self._target}/engage")

        self.create_timer(1.0 / float(g["tick_hz"]), self._on_tick)
        self.get_logger().info(
            f"감시 시작 — 대상 '{self._target}' · 기록 {self._state_path} · "
            f"두절 임계 {self.cfg.diag_timeout_s}s · "
            f"복귀 {'활성' if self.cfg.restore_enabled else '비활성'}"
            + (f" · 직전 기록 engaged={self._prev.get('engaged')}"
               if self._prev else " · 직전 기록 없음"))

    # ── 구독 ──────────────────────────────────────────────────────────
    def _on_diag(self, msg: DiagnosticArray):
        """can_relay 진단 1건을 뽑아 현재 상태로 삼는다. 다른 발행자는 무시한다."""
        for st in msg.status:
            if not str(st.name).startswith(self._prefix):
                continue
            self._cur = parse_diag(st.values, st.level, st.message)
            self._last_diag = time.monotonic()
            return

    # ── 주기 판정 ─────────────────────────────────────────────────────
    def _on_tick(self):
        """관측 조립 → `decide` → 기록·복귀·발행. 판정 로직은 여기 두지 않는다."""
        now = time.monotonic()
        age = None if self._last_diag is None else (now - self._last_diag)
        stale = age is not None and age > self.cfg.diag_timeout_s
        if age is None or stale:
            self._cur = None
        # 안정화 시계 — 진단이 흐르는 동안만 간다. 끊기면(또는 복귀 직후 폐기되면) 리셋.
        if self._cur is None:
            self._cur_seen_since = None
        elif self._cur_seen_since is None:
            self._cur_seen_since = now

        # 상태 갱신(잘라내기)은 여기서 명시적으로 — 조회가 상태를 바꾸지 않게 한다.
        self._restore_stamps = prune_stamps(self._restore_stamps, time.time(),
                                            self.cfg.restart_window_s)
        obs = Observation(
            cur=self._cur,
            diag_age=age,
            # 프로세스 순회는 두절일 때만 한다 — 정상 구간에서 /proc 을 매 틱 훑을 이유가 없다.
            proc_alive=proc_alive(self._target) if stale else None,
            was_down=self._was_down,
            restarts_in_window=len(self._restore_stamps),
            cur_settle_s=(None if self._cur_seen_since is None
                          else now - self._cur_seen_since),
        )
        verdict, why = decide(self._prev, obs, self.cfg)

        if verdict != self._verdict:
            # ⚠ rclpy 로거는 **호출 지점(파일:줄)마다 severity 를 고정**한다 — 한 줄에서
            #   warn/info 를 골라 부르면 두 번째 호출이
            #   `ValueError: Logger severity cannot be changed between calls` 로 죽는다.
            #   그래서 분기마다 별도 호출 지점을 둔다.
            line = f"{self._verdict} → {verdict} — {why}"
            if verdict in (DEAD, ZOMBIE, HOLD):
                self.get_logger().warn(line)
            else:
                self.get_logger().info(line)
            self._verdict = verdict

        self._was_down = next_was_down(self._was_down, verdict,
                                       is_outage(obs, self.cfg))

        if self._cur is not None:
            # 내용이 바뀔 때만 쓴다 — 무변화 기록을 2 Hz 로 반복할 이유가 없다
            # (`saved_at` 은 지문에서 제외 — 그것만 바뀌는 재기록은 무의미하다).
            fingerprint = (tuple(sorted(self._cur.items())),
                           tuple(self._restore_stamps))
            if fingerprint != self._last_saved:
                self._save(self._cur)
                self._last_saved = fingerprint
        # 직전 상태 승격 — 판정 **뒤에** 한다. 앞에서 하면 재기동 직후의 engaged=False 가
        # 곧바로 prev 가 되어 복귀 조건이 스스로 사라진다.
        self._prev = next_prev(self._prev, self._cur, verdict)

        if verdict == RESTORE:
            self._restore()

        self._publish(verdict, why, obs)

    def _restore(self):
        """`~/engage true` 를 한 번 부른다.

        진행 중 호출이 있으면 새로 부르지 않는다 — 서비스가 늦으면 매 틱 재호출이 쌓여
        제어권 조작이 중복된다.
        """
        now = time.monotonic()
        if self._pending is not None and not self._pending.done():
            if not restore_call_expired(self._pending_since, now, self.cfg):
                return
            # 시한 초과 — future 를 버리고 재시도한다. 버리지 않으면 응답이 영영 오지 않는
            # 호출 하나가 이후 모든 복귀를 막는다.
            self.get_logger().warn(
                f"복귀 호출 무응답 {self.cfg.restore_call_timeout_s:.0f}s — 포기하고 재시도한다")
            self._pending.cancel()
            self._pending = None
            self._pending_since = None
        if not self.cli_engage.service_is_ready():
            self.get_logger().warn(
                f"복귀 보류 — /{self._target}/engage 가 아직 준비되지 않았다",
                throttle_duration_sec=5.0)
            return
        self._restore_stamps.append(time.time())
        req = SetBool.Request()
        req.data = True
        self._pending = self.cli_engage.call_async(req)
        self._pending_since = now
        self._pending.add_done_callback(self._on_restore_done)
        self.get_logger().warn(
            f"복귀 지시 — /{self._target}/engage true "
            f"(창 내 {len(self._restore_stamps)}/{self.cfg.restart_limit}회)")

    def _on_restore_done(self, future):
        """복귀 응답 처리. 성공하면 구 진단을 버린다."""
        if future is not self._pending:
            # 버린(시한 초과·취소) 호출의 늦은 콜백 — 현재 호출의 상태를 건드리면 안 된다.
            # rclpy 는 executor 가 붙은 future 의 콜백을 태스크로 미룰 수 있어, 이 검사가
            # 없으면 취소 콜백이 **새 호출의 송신 시각을 지워** 시한 판정이 다시는 서지 않는다.
            return
        self._pending_since = None
        if future.cancelled():
            return
        try:
            res = future.result()
        except Exception as exc:
            self.get_logger().error(f"복귀 호출 실패: {type(exc).__name__}: {exc}")
            return
        if not res.success:
            self.get_logger().error(f"복귀 거부 — {res.message}")
            return
        # 복귀 이전에 받은 진단을 버린다 — engaged=False 인 옛 상태라 그대로 판정에 쓰면
        # 방금 한 복귀를 되돌린 것으로 읽힌다. `_was_down` 은 여기서 내리지 않는다
        # (`next_was_down` 이 `RUNNING` 관측으로만 내린다).
        self._cur = None
        self.get_logger().info(f"복귀 완료 — {res.message}")
        was = (self._prev or {}).get("steer_target_deg")
        if was is not None:
            # 목표는 복원하지 않는다 — 재기동한 드라이버의 조향 목표는 상위가 다시 지령하기
            # 전까지 없는 것이 정상이다. 여기는 기록만 남긴다.
            self.get_logger().info(f"기록된 사망 직전 조향 목표 {was}° — 복원하지 않는다")

    # ── 기록 ──────────────────────────────────────────────────────────
    def _save(self, state: dict):
        """상태를 원자적으로 저장한다(임시파일 + `os.replace`).

        중간에 죽어도 반쪽 파일이 남지 않아야 한다 — 반쪽 JSON 은 다음 기동에서
        「기록 없음」으로 읽혀 복귀가 조용히 사라진다.
        """
        rec = dict(state)
        rec["boot_id"] = self._boot
        rec["saved_at"] = time.time()
        rec["restore_stamps"] = list(self._restore_stamps)
        d = os.path.dirname(self._state_path)
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".json")
            with os.fdopen(fd, "w") as f:
                json.dump(rec, f, ensure_ascii=False)
            os.replace(tmp, self._state_path)
        except OSError as exc:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)      # 실패한 임시파일이 tmpfs 에 쌓이지 않게
                except OSError:
                    pass
            self.get_logger().error(
                f"상태 기록 실패 ({self._state_path}: {exc})",
                throttle_duration_sec=30.0)

    def _load(self) -> Optional[dict]:
        """기록을 읽는다. **`boot_id` 가 다르면 폐기**한다.

        전원 사이클을 넘긴 기록으로 복귀하면 조향 홈 기준이 없는 상태에서 제어권을
        잡는다(홈 설정은 전원이 켜져 있는 동안만 유효하다).
        """
        try:
            with open(self._state_path, "r") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            return None
        if not isinstance(rec, dict):
            return None
        saved = str(rec.get("boot_id") or "")
        if self._boot and saved and saved != self._boot:
            self.get_logger().warn(
                "직전 기록을 폐기한다 — 다른 부팅의 것이다(전원 사이클). "
                "조향 홈은 전원 사이클마다 무효이므로 복귀하지 않는다")
            return None
        return rec

    # ── 발행 ──────────────────────────────────────────────────────────
    def _publish(self, verdict: str, why: str, obs: Observation):
        """감시자 자신의 판정을 진단으로 낸다 — 감시자가 도는지 밖에서 보이게."""
        st = DiagnosticStatus()
        st.name = "can_relay_supervisor: 노드 감시"
        st.hardware_id = self._target
        st.level = {
            RUNNING: DiagnosticStatus.OK,
            IDLE: DiagnosticStatus.OK,
            WAIT: DiagnosticStatus.WARN,
            RESTORE: DiagnosticStatus.WARN,
            HOLD: DiagnosticStatus.ERROR,
            DEAD: DiagnosticStatus.ERROR,
            ZOMBIE: DiagnosticStatus.ERROR,
        }.get(verdict, DiagnosticStatus.WARN)
        st.message = f"{verdict} — {why}"
        st.values = [
            KeyValue(key="verdict", value=verdict),
            KeyValue(key="diag_age_s",
                     value="—" if obs.diag_age is None else f"{obs.diag_age:.1f}"),
            KeyValue(key="was_down", value=str(self._was_down)),
            KeyValue(key="restores_in_window", value=str(len(self._restore_stamps))),
            KeyValue(key="state_path", value=self._state_path),
            KeyValue(key="prev_engaged",
                     value=str((self._prev or {}).get("engaged", "—"))),
        ]
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        arr.status = [st]
        self.pub_status.publish(arr)


def main(args=None):
    """진입점. 감시자는 제어 경로 밖이므로 단일 스레드 실행기로 충분하다."""
    rclpy.init(args=args)
    node = None
    try:
        node = RelaySupervisor()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
