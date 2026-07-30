#!/usr/bin/env python3
"""릴레이 구동 백엔드 — 단일 제어 스레드.

## 설계 규칙 (전부 실측 사고에서 나온 것)

1. **구동 지령은 주기 재송신한다.** 단발 송신은 프레임 하나가 유실되면 그대로
   끝이고, 지령원이 사라져도 드라이브가 마지막 값을 물고 계속 간다.
2. **워치독이 지령을 만료시킨다.** `cmd_timeout` 안에 갱신이 없으면 속도 0 으로
   수렴한다. 갱신은 "유효한 지령"일 때만 인정한다 — NaN 을 계속 퍼블리시하는
   노드가 워치독을 무한 연장하지 못하게 한다.
3. **정지 경로는 어떤 상태에서도 거부되지 않는다.** 폴링이 죽었든 제어권이
   흔들리든 `stop()` 은 항상 받아들여지고, 다음 틱이 아니라 즉시 시도한다.
4. **조향 클램프는 counts 를 만드는 지점에 있다**(`safety.steer_deg_to_counts`).
   상위 계층에만 두면 다른 상위가 붙었을 때 보호가 사라진다.
5. **호밍 중 위치를 믿지 않는다.** bit15=0 구간에서 0x6064 는 0 으로 고정되며
   각도로 환산하면 ≈−137° 가 상위로 흘러간다.
6. **호밍은 자동으로 하지 않는다.** 물리 스윙 100°+ 이고, **본 구현에는 취소 경로가
   없다** — `home()` 은 `0x60FB:04=1` 을 SDO 로 직접 보내고 그 뒤 상태워드만 본다.
   ⚠ "소프트웨어가 아예 못 멈춘다"는 뜻이 아니다: 판다 펌웨어의 호밍 시퀀서에는
   취소 프레임(`0x60FB:04=0`) 송신 경로가 있다
   (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:307-309`
   `seer_home_cancel_frames()`, USB `0xea` wValue=0 으로 기동). 본 패키지는 그 경로를
   쓰지 않으므로 **우리 쪽 중단 수단이 하드웨어 E-STOP 뿐인 것**이며, 이는 개선 여지다.
   따라서 명시 요청으로만 수행한다.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import protocol as P
from . import safety as S
from .link import BaseLink, LinkError, MOTOR_BUS, HEARTBEAT_PERIOD_S


@dataclass
class NodeState:
    """노드 하나의 최신 피드백. `last_seen` 은 신선도 판정에 쓴다."""

    position: Optional[int] = None
    statusword: Optional[int] = None
    velocity_raw: Optional[int] = None
    current_raw: Optional[int] = None
    digital_input: Optional[int] = None
    last_seen: float = 0.0
    aborts: int = 0
    last_abort: Optional[int] = None

    def fresh(self, now: float, ttl: float) -> bool:
        return self.last_seen > 0.0 and (now - self.last_seen) <= ttl


@dataclass
class RelayConfig:
    """배선·한계·주기. 값의 근거는 각 필드 주석과 safety.py 에 있다."""

    drive_nodes: tuple = (1, 2)
    steer_nodes: tuple = (3, 4)
    bus: int = MOTOR_BUS
    cmd_hz: float = 20.0            # 지령 재송신 주기
    poll_hz: float = 5.0            # 피드백 폴링 주기(gui.py 실측 주기와 동일)
    cmd_timeout_s: float = 0.3      # 워치독. 이 안에 갱신 없으면 속도 0
    feedback_ttl_s: float = 1.0     # 이보다 오래된 피드백은 없는 것으로 친다
    steer_limit_deg: float = S.STEER_LIMIT_DEG
    vel_max_units: int = S.VEL_MAX_UNITS
    steer_home: dict = field(default_factory=lambda: dict(S.DEFAULT_STEER_HOME))
    settle_tol_deg: float = 3.0
    allow_bringup: bool = False     # 구동/조향 init 시퀀스 송신 여부(실기 미검증)


class RelayBackend:
    """제어 스레드 하나가 송신·수신·심박을 모두 담당한다.

    스레드를 나누지 않는 이유: 판다 USB 핸들을 여러 스레드가 경합하면 heartbeat
    전송이 실패해 펌웨어가 릴레이를 스스로 풀어 버린 이력이 있다.
    """

    def __init__(self, link: BaseLink, cfg: RelayConfig,
                 log: Optional[Callable[[str], None]] = None):
        self.link = link
        self.cfg = cfg
        self._log = log or (lambda _m: None)

        self.nodes: dict[int, NodeState] = {
            n: NodeState() for n in tuple(cfg.drive_nodes) + tuple(cfg.steer_nodes)
        }

        self._lock = threading.Lock()
        self._drive_units = 0
        self._steer_counts: dict[int, int] = {}
        self._steer_target_deg: Optional[float] = None
        self._last_cmd_time = 0.0
        self._estop = False
        self._fault: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._homing = False

        self.tx_count = 0
        self.rx_count = 0
        self.watchdog_trips = 0

    # ── 수명주기 ──────────────────────────────────────────────────────
    def start(self):
        if self._running:
            raise RuntimeError("이미 기동돼 있다 — 두 번 부르면 버스 writer 가 둘이 된다")
        if not self.link.engaged:
            raise RuntimeError("제어권을 먼저 획득해야 한다")
        if self.cfg.allow_bringup:
            self._write_bringup()
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="can_relay",
                                        daemon=True)
        self._thread.start()
        self._log("백엔드 기동")

    def shutdown(self):
        """정지를 **먼저** 보내고 스레드를 내린다. 순서가 반대면 안 된다.

        두 번 불러도 안전하다 — 노드 종료 경로가 `~/engage false` 와 겹친다.
        """
        if not self._running and self._thread is None and self._drive_units == 0:
            return
        self.stop("shutdown")
        if self.link.engaged:
            try:
                self._send(self._drive_frames(0))
            except Exception as exc:
                self._log(f"종료 정지 송신 실패: {type(exc).__name__}: {exc}")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        self._log("백엔드 종료")

    # ── 지령 ──────────────────────────────────────────────────────────
    def set_drive_mmps(self, mmps: float, sign: int = 1):
        """구동 속도 지령. 비유한 값은 **거부**하고 워치독을 갱신하지 않는다."""
        if self._estop:
            return
        units = S.drive_mmps_to_units(mmps, sign, self.cfg.vel_max_units)
        with self._lock:
            self._drive_units = units
            self._last_cmd_time = time.monotonic()

    def set_steer_deg(self, deg: float):
        """조향 절대각 지령. ±limit 로 잘라서 보낸다(거부가 아니라 클램프).

        호밍 중에는 받지 않는다 — 드라이브 내부 루틴이 축을 쥐고 있다.
        """
        if self._homing:
            raise S.UnsafeCommand("호밍 진행 중에는 조향 지령을 보내지 않는다")
        applied = None
        counts = {}
        for n in self.cfg.steer_nodes:
            applied, c = S.steer_deg_to_counts(n, deg, self.cfg.steer_home,
                                               self.cfg.steer_limit_deg)
            counts[n] = c
        with self._lock:
            self._steer_counts = counts
            self._steer_target_deg = applied
            self._last_cmd_time = time.monotonic()
        if applied is not None and abs(applied - float(deg)) > 1e-9:
            self._log(f"조향 지령 {deg:+.1f}° → ±{self.cfg.steer_limit_deg:.0f}° "
                      f"클램프 적용 {applied:+.1f}°")
        return applied

    def stop(self, reason: str = ""):
        """구동 정지. **어떤 상태에서도 받아들인다.**

        조향은 현 위치를 유지한다 — PP 모드라 목표를 지운다고 서지 않고, 0° 로
        되돌리면 그것 자체가 100° 스윙이 될 수 있다.
        """
        with self._lock:
            self._drive_units = 0
            self._last_cmd_time = time.monotonic()
        # 즉시 송신은 best-effort 다. 제어권이 없으면 우리 프레임은 어차피 게이트에
        # 막히므로 시도하지 않는다 — 지령 자체(속도 0)는 위에서 이미 확정됐다.
        if self.link.engaged:
            try:
                self._send(self._drive_frames(0))
            except Exception as exc:
                self._log(f"즉시 정지 송신 실패(루프가 재시도한다): "
                          f"{type(exc).__name__}: {exc}")
        if reason:
            self._log(f"정지 — {reason}")

    def estop(self, engage: bool):
        """소프트 E-stop 래치. ⚠ 하드웨어 E-STOP 을 대체하지 않는다.

        조향축은 PP 모드라 직전 목표까지 계속 회전한다 — 이 함수는 구동만 세운다.
        """
        self._estop = bool(engage)
        if engage:
            self.stop("estop")
        self._log(f"E-stop {'인가' if engage else '해제'}")

    # ── 호밍 (명시 요청 전용) ─────────────────────────────────────────
    def home(self, speed: int = 2500, start_window_s: float = 10.0,
             timeout_s: float = 90.0) -> tuple[bool, str]:
        """조향 호밍. **물리 스윙 100°+ 가 발생하며 본 구현에는 취소 경로가 없다**
        (이 함수는 `0x60FB:04=1` 송신 후 상태워드만 관측한다 — 아래 `_send` 참조).
        ⚠ 범위 주의: 펌웨어에는 취소 경로가 실재한다 —
        `safety_seer_gate.h:307-309` `seer_home_cancel_frames()` 가 `0x60FB:04=0` 을 낸다.
        미사용일 뿐이므로 "불가능"이 아니라 "미구현"으로 적는다.

        시작하면 드라이브 내부 루틴이 수행하므로 **여기서는** 중단 수단이 하드웨어
        E-STOP 뿐이다. 호출 전 사람 확인 필수.
        """
        if self._homing:
            return False, "이미 호밍 중"
        if not self._running:
            return False, "백엔드가 기동돼 있지 않다"
        self.stop("호밍 전 구동 0")
        judge = S.HomingJudge(self.cfg.steer_nodes, start_window_s, timeout_s)
        with self._lock:
            for st in self.nodes.values():
                st.statusword = None    # 직전 상태워드를 완료로 오독하지 않도록
        self._homing = True
        try:
            frames = []
            for n in self.cfg.steer_nodes:
                frames.extend(P.homing_frames(n, speed, self.cfg.bus))
            self._send(frames)
            self._log("호밍 개시 — 조향축. 완료까지 30초 이상 걸린다")
            t0 = time.monotonic()
            while True:
                elapsed = time.monotonic() - t0
                with self._lock:
                    status = {n: self.nodes[n].statusword
                              for n in self.cfg.steer_nodes}
                result, why = judge.update(status, elapsed)
                if result is not None:
                    return result, why
                if not self._running:
                    return False, "백엔드가 내려갔다"
                time.sleep(0.1)
        finally:
            self._homing = False

    # ── 상태 ──────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        now = time.monotonic()
        with self._lock:
            nodes = {}
            for n, st in self.nodes.items():
                nodes[n] = {
                    "position": st.position,
                    "statusword": st.statusword,
                    "velocity_raw": st.velocity_raw,
                    "current_raw": st.current_raw,
                    "digital_input": st.digital_input,
                    "fresh": st.fresh(now, self.cfg.feedback_ttl_s),
                    "homed": S.is_homed(st.statusword),
                    "aborts": st.aborts,
                    "last_abort": st.last_abort,
                }
            return {
                "drive_units": self._drive_units,
                "steer_target_deg": self._steer_target_deg,
                "estop": self._estop,
                "homing": self._homing,
                "fault": self._fault,
                "running": self._running,
                "engaged": self.link.engaged,
                "tx": self.tx_count,
                "rx": self.rx_count,
                "watchdog_trips": self.watchdog_trips,
                "nodes": nodes,
            }

    def steer_angles_deg(self) -> dict:
        """축별 조향 실측각. **믿을 수 없는 축은 None** 이다.

        믿을 수 없는 경우: 상태워드 미확보 / 호밍 진행 중(bit15=0) / 피드백 만료.
        """
        now = time.monotonic()
        out = {}
        with self._lock:
            for n in self.cfg.steer_nodes:
                st = self.nodes.get(n)
                if st is None or not st.fresh(now, self.cfg.feedback_ttl_s):
                    out[n] = None
                    continue
                if not S.position_trustworthy(st.statusword) or st.position is None:
                    out[n] = None
                    continue
                home = self.cfg.steer_home.get(n)
                out[n] = None if home is None else \
                    (st.position - home) / S.COUNTS_PER_DEG
        return out

    def settled(self) -> bool:
        target = self._steer_target_deg
        if target is None:
            return False
        measured = {n: v for n, v in self.steer_angles_deg().items()
                    if v is not None}
        return S.settled(target, measured, self.cfg.steer_nodes,
                         self.cfg.settle_tol_deg)

    # ── 내부 ──────────────────────────────────────────────────────────
    def _drive_frames(self, units: int) -> list:
        return [P.drive_velocity_frame(n, units, self.cfg.bus)
                for n in self.cfg.drive_nodes]

    def _send(self, frames):
        frames = list(frames)
        if not frames:
            return
        self.link.send(frames)
        self.tx_count += len(frames)

    def _write_bringup(self):
        """브링업 시퀀스. ⚠ 실기 검증 이력이 없는 구간이다(기본 비활성)."""
        frames = []
        for n in self.cfg.drive_nodes:
            frames.extend(P.drive_init_frames(n, self.cfg.bus))
        for n in self.cfg.steer_nodes:
            frames.extend(P.steer_init_frames(n, self.cfg.bus))
        self._send(frames)
        self._log(f"브링업 {len(frames)} 프레임 송신 (⚠ 실기 미검증 경로)")

    def _loop(self):
        cfg = self.cfg
        cmd_iv = 1.0 / cfg.cmd_hz
        poll_iv = 1.0 / cfg.poll_hz
        next_poll = 0.0
        next_hb = 0.0
        while self._running:
            now = time.monotonic()
            try:
                if now >= next_hb:
                    self.link.heartbeat()
                    next_hb = now + HEARTBEAT_PERIOD_S

                # 워치독 — 유효 지령이 끊기면 속도 0 으로 수렴한다.
                with self._lock:
                    stale = (now - self._last_cmd_time) > cfg.cmd_timeout_s
                    units = 0 if (stale or self._estop) else self._drive_units
                    steer = dict(self._steer_counts)
                    if stale and self._drive_units != 0:
                        self._drive_units = 0
                        self.watchdog_trips += 1
                        self._log("워치독 — 지령 만료, 속도 0")

                frames = self._drive_frames(units)
                if not self._homing:
                    for n, counts in steer.items():
                        frames.extend(P.steer_target_frames(n, counts, cfg.bus))
                if now >= next_poll:
                    frames.extend(P.poll_frames(
                        tuple(cfg.drive_nodes) + tuple(cfg.steer_nodes), cfg.bus))
                    next_poll = now + poll_iv
                self._send(frames)
                self._drain()
                self._fault = None
            except (LinkError, Exception) as exc:
                # 조용히 죽지 않는다 — 상태에 남겨 진단이 집어낼 수 있게 한다.
                self._fault = f"{type(exc).__name__}: {exc}"
                self._log(f"제어 루프 오류: {self._fault}")
                time.sleep(0.05)
            time.sleep(max(0.0, cmd_iv - (time.monotonic() - now)))

    def _drain(self):
        """수신 처리. 판다는 fwd 여부와 무관하게 모든 프레임을 올려 준다."""
        for can_id, data, bus in self.link.recv():
            if bus != self.cfg.bus:
                continue
            resp = P.parse_sdo_response(can_id, data)
            if resp is None or resp.node not in self.nodes:
                continue
            self.rx_count += 1
            st = self.nodes[resp.node]
            with self._lock:
                st.last_seen = time.monotonic()
                if resp.kind == "abort":
                    st.aborts += 1
                    st.last_abort = resp.value
                    self._log(
                        f"SDO 거부 N{resp.node} 0x{resp.index:04X}:{resp.sub:02X} "
                        f"→ 0x{resp.value:08X} ({P.abort_text(resp.value)})")
                    continue
                if resp.kind != "read":
                    continue
                if resp.index == P.OBJ_POSITION_ACTUAL:
                    st.position = resp.value
                elif resp.index == P.OBJ_STATUSWORD:
                    st.statusword = resp.value & 0xFFFF
                elif resp.index == P.OBJ_VELOCITY_ACTUAL:
                    st.velocity_raw = resp.value
                elif resp.index == P.OBJ_CURRENT_ACTUAL:
                    st.current_raw = resp.value
                elif resp.index == P.OBJ_DIGITAL_INPUT and resp.sub == 1:
                    st.digital_input = resp.value
