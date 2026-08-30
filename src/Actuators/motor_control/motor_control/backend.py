"""Tongyi SDO 폴링 마스터 백엔드 — ModuleCommand[] → CAN.

브링업(선판독 → 홈 편차 게이트 → init) → enable → 50Hz 지령 + 20Hz guard RTR + 피드백 폴링.
안전 게이트: 조향 홈 편차 검출 시 기동 거부 / 조향 미정착 시 구동속도 0 / cmd 워치독·E-stop 래치 → vel 0.

⚠ 조향 홈 기준·호밍 거동은 미판정 — docs/debt/registry.md debt-007
  (Seer 실측 호밍 시퀀스 전문은 docs/verified_facts/2026-07-27.md §A-8).

스레드 모델: TX 루프 = 유일한 버스 writer(브링업은 TX 시작 전 단독) / RX 루프 = 상태 dict 유일 writer.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from . import protocol as P
from .kinematics import ModuleCommand


class BringupRefused(RuntimeError):
    """조향 0x6064 가 steer_home 에서 homing_tol 이상 이탈했으나 allow_homing_motion=False.

    ⚠ 이탈 원인은 미판정이다(호밍 진행 중 0 반환 포함) — docs/debt/registry.md debt-007.
    """


class NodeSilent(RuntimeError):
    """브링업 선판독에서 노드 무응답."""


@dataclass
class ModuleConfig:
    """휠 모듈 1개의 노드 배선. steer_node=None ⇒ 조향축 없음(DD 타입)."""

    drive_node: int
    steer_node: int | None = None
    # 조향 홈 절대 counts. driver_node 가 `steer_home_counts` 파라미터로 채운다.
    # 정본은 src/Comm/CAN/can_relay/config/machine/foil_a082.yaml 하나다(2026-08-02 실측 확정).
    # ⚠ 기본값 0 은 「미설정」이 아니라 그대로 0x607A 로 나가는 값이다 — YAML 미로드 시
    #   바퀴가 ≈−137° 로 돈다. can_relay 는 같은 문제를 「값 없으면 거부」로 막았다(debt-032).
    # 호밍 후 정착 목표(7,882,020 / 7,859,062)와는 +0.178°/+0.331° 다르다 — 호밍은 0° 에
    #   정확히 놓지 않는다. docs/verified_facts/2026-07-27.md §A-8 ③-4
    steer_home: int = 0


@dataclass
class NodeState:
    pos: int | None = None
    status: int | None = None
    error: int | None = None
    current: int | None = None
    last_seen: float = 0.0
    aborts: int = 0


def _to_can(frame: P.Frame):
    try:
        import can  # 지연 import — 순수 로직 테스트 시 python-can 불요
    except ImportError:
        from types import SimpleNamespace

        return SimpleNamespace(arbitration_id=frame.can_id, data=frame.data,
                               is_remote_frame=frame.is_rtr)
    if frame.is_rtr:
        return can.Message(arbitration_id=frame.can_id, is_remote_frame=True, dlc=0,
                           is_extended_id=False)
    return can.Message(arbitration_id=frame.can_id, data=frame.data, is_extended_id=False)


class TongyiSdoBackend:
    """SDO 폴링 단독 마스터. bus 는 python-can Bus 호환(send/recv/shutdown)."""

    # Seer 기동 init 실측값 (기동 캡처 tongyi_250k_startup_20260708_103448_can0.asc 전수 디코드)
    GUARD_TIME_MS = 500
    LIFE_FACTOR = 1
    PROFILE_VELOCITY = 30000
    PROFILE_ACC = 250
    PROFILE_DEC = 250
    # 0x6099 Homing Speeds, 단위 0.1 r/min ⇒ 2500 = 250 rpm [Handbook V7.0 §6.9 page 171]
    # ⚠ 물리 호밍 탐색 속도(−리밋 탐색). Seer 실측값과 동일 — 임의 상향 금지.
    HOMING_SPEED = 2500

    def __init__(self, bus, modules: list[ModuleConfig], *,
                 m_s_per_unit: float, drive_sign: int, counts_per_rad: float, steer_sign: int,
                 vel_limit_units: int, cmd_hz: float = 50.0, guard_hz: float = 20.0,
                 cmd_timeout: float = 0.2, steer_settle_tol_counts: int = 172032,
                 allow_homing_motion: bool = False, homing_tol_counts: int = 286720,
                 bringup_read_timeout: float = 2.0, logger=None):
        self.bus = bus
        self.modules = list(modules)
        self.m_s_per_unit = float(m_s_per_unit)
        self.drive_sign = int(drive_sign)
        self.counts_per_rad = float(counts_per_rad)
        self.steer_sign = int(steer_sign)
        self.vel_limit_units = int(vel_limit_units)
        self.cmd_hz = float(cmd_hz)
        self.guard_hz = float(guard_hz)
        self.cmd_timeout = float(cmd_timeout)
        self.steer_settle_tol_counts = int(steer_settle_tol_counts)
        self.allow_homing_motion = bool(allow_homing_motion)
        self.homing_tol_counts = int(homing_tol_counts)
        self.bringup_read_timeout = float(bringup_read_timeout)
        self.log = logger or (lambda *_: None)

        self.drive_nodes = [m.drive_node for m in self.modules]
        self.steer_nodes = [m.steer_node for m in self.modules if m.steer_node is not None]
        self._all_nodes = sorted(set(self.drive_nodes + self.steer_nodes))

        self._lock = threading.Lock()          # 지령 목표 보호 (writer: set_command/estop/freewheel, reader: TX)
        self._vel_units = {n: 0 for n in self.drive_nodes}
        self._steer_counts = {m.steer_node: m.steer_home for m in self.modules if m.steer_node is not None}
        self._last_cmd_time = 0.0
        self._estop = False
        self._freewheel = False                # 구동축 servo-off(견인/정비). TX 루프가 전이에서 실 송신

        self._state_lock = threading.Lock()    # 피드백 상태 보호 (writer: RX 스레드)
        self._nodes: dict[int, NodeState] = {n: NodeState() for n in self._all_nodes}
        self.tx_count = 0
        self.rx_count = 0
        self.settling = False

        self._running = False
        self._rx_thread: threading.Thread | None = None
        self._tx_thread: threading.Thread | None = None
        self._slow_objs = [P.OBJ_STATUSWORD, P.OBJ_ERROR_CODE, P.OBJ_CURRENT_ACTUAL]
        self._slow_idx = 0

    # ── 공개 API ────────────────────────────────────────────────────────────
    def start(self):
        """RX 기동 → 선판독·브링업 게이트 → init 시퀀스 → TX 루프 기동."""
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True, name="tongyi-rx")
        self._rx_thread.start()
        self._preflight_read()
        self._gate_homing_motion()
        self._write_init_sequence()
        self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True, name="tongyi-tx")
        self._tx_thread.start()
        self.log("[backend] started (bring-up complete)")

    def set_command(self, commands: list[ModuleCommand]):
        """SI 단위 모듈 지령 → 디바이스 단위 목표 갱신 + 워치독 스탬프."""
        by_drive = {m.drive_node: m for m in self.modules}
        with self._lock:
            if self._estop:
                return  # E-stop 중 신규 지령 무시(해제 직후 stale 창 급발진 방지)
            if self._freewheel:
                return  # freewheel(견인) 중 신규 지령 무시(해제 직후 stale 창 급발진 방지)
            for cmd in commands:
                mod = by_drive.get(cmd.drive_node)
                if mod is None:
                    continue
                u = int(round(self.drive_sign * cmd.velocity_mps / self.m_s_per_unit))
                self._vel_units[mod.drive_node] = max(-self.vel_limit_units,
                                                      min(self.vel_limit_units, u))
                if mod.steer_node is not None and cmd.steer_rad is not None:
                    self._steer_counts[mod.steer_node] = int(round(
                        mod.steer_home + self.steer_sign * cmd.steer_rad * self.counts_per_rad))
            self._last_cmd_time = time.monotonic()

    def estop(self, engage: bool):
        with self._lock:
            self._estop = bool(engage)
            if engage:
                self._vel_units = {n: 0 for n in self.drive_nodes}
        self.log(f"[backend] E-STOP {'ENGAGED' if engage else 'released'}")

    def freewheel(self, engage: bool):
        """구동축 servo-off(free spin) 토글 — 견인/정비 전용.

        engage=True: 구동 노드 servo enable 해제(0x6040=CW_DISABLE) → 바퀴 자유회전.
          ⚠ 홀딩토크 상실 — 경사면에서 굴러갈 수 있음(정지·평지·촉 확보 후 사용).
          조향축은 영향 없음(현 위치 hold). vel 목표를 0으로 리셋.
        engage=False: 구동 노드 재-enable(0x86 + PV 모드) → 신선한 지령 전까지 워치독으로 vel 0.
        실제 CAN 송신은 상태 전이에서 TX 루프(유일 버스 writer)가 수행한다.
        """
        with self._lock:
            self._freewheel = bool(engage)
            if engage:
                self._vel_units = {n: 0 for n in self.drive_nodes}
        self.log(f"[backend] FREEWHEEL {'ENGAGED (구동 servo-off, 홀딩토크 없음)' if engage else 'released (재-enable)'}")

    def snapshot(self) -> dict:
        """진단·오도메트리용 상태 사본."""
        with self._state_lock:
            nodes = {n: NodeState(s.pos, s.status, s.error, s.current, s.last_seen, s.aborts)
                     for n, s in self._nodes.items()}
        with self._lock:
            vel = dict(self._vel_units)
            steer = dict(self._steer_counts)
            es = self._estop
            fw = self._freewheel
        return {"nodes": nodes, "vel_units": vel, "steer_counts": steer, "estop": es,
                "freewheel": fw, "settling": self.settling, "tx": self.tx_count, "rx": self.rx_count}

    def shutdown(self):
        """정지(vel 0) 송신 후 스레드 종료. 버스는 소유자로서 닫는다."""
        self._running = False
        for t in (self._tx_thread, self._rx_thread):
            if t is not None:
                t.join(timeout=1.0)
        try:
            for n in self.drive_nodes:
                self._send(P.sdo_write(n, P.OBJ_TARGET_VELOCITY, 0, size=4))
            time.sleep(0.05)
        except Exception:
            pass
        try:
            self.bus.shutdown()
        except Exception:
            pass

    # ── 내부: 브링업 ────────────────────────────────────────────────────────
    def _preflight_read(self):
        """전 노드 0x6064 선판독 — 무응답 노드 검출 + 조향 홈 편차 판정 입력.

        ⚠ 호밍 진행 중이면 0x6064 가 0 을 반환한다 — docs/debt/registry.md debt-007 §①.
        """
        deadline = time.monotonic() + self.bringup_read_timeout
        pending = set(self._all_nodes)
        while pending and time.monotonic() < deadline:
            for n in sorted(pending):
                self._send(P.sdo_read(n, P.OBJ_POSITION_ACTUAL))
            time.sleep(0.05)
            with self._state_lock:
                pending = {n for n in pending if self._nodes[n].pos is None}
        if pending:
            raise NodeSilent(f"브링업 선판독 무응답 노드: {sorted(pending)}")

    def _gate_homing_motion(self):
        """조향 실측이 홈에서 이탈했는지 검출 — 물리 스윙 허용 없이는 기동 거부.

        ⚠ 이탈 원인 미판정, 0x6041 bit15 를 함께 읽기 전에는 종결 금지 — docs/debt/registry.md debt-007.
        """
        with self._state_lock:
            deltas = {m.steer_node: abs((self._nodes[m.steer_node].pos or 0) - m.steer_home)
                      for m in self.modules if m.steer_node is not None}
        cold = {n: d for n, d in deltas.items() if d > self.homing_tol_counts}
        if cold and not self.allow_homing_motion:
            deg = {n: round(d / (self.counts_per_rad * 3.14159265 / 180.0), 1) for n, d in cold.items()}
            raise BringupRefused(
                f"조향 실측이 홈에서 {deg} ° 벗어남. "
                f"참고: 직전에 호밍했다면 +0.178°/+0.331° 는 **정상**이다 — 호밍은 조향을 0° 가 "
                f"아니라 펌웨어 GOZERO 지점에 놓는다(2026-08-03 10회 실측, σ≈3 counts). "
                f"그보다 큰 편차는 원인 미판정이다(debt-007 은 2026-08-02 종결, 잔여는 debt-034). "
                f"주변 확보 후 파라미터 allow_homing_motion:=true 로 재시작하세요. "
                f"참고: 브링업은 호밍 트리거를 보내지 않는다 — 물리 스윙은 GUI '호밍' 요청 시에만 발생. "
                f"⚠ 7,882,020/7,859,062 는 조향 0° 가 아니라 펌웨어 GOZERO(호밍 후 정착) 목표다 — "
                f"0° 에서 +0.178°/+0.331° 벗어나 있다. 조향 0° 정본은 steer_home_counts 다.")
        if cold:
            self.log(f"[backend] 조향 홈 대비 편차 검출(브링업은 호밍 트리거를 보내지 않음): {cold}")

    def _write_init_sequence(self):
        """init 시퀀스(프레임 간 ~2ms). Seer 실측 순서의 **부분** 재현 — 호밍 트리거는 보내지 않는다.

        ⚠ 0x6041 bit15 완료 대기가 없다 — 다른 마스터가 호밍 중이면 그 축에 PP+0x607A 를 거는
          잔여 위험 미해소. Seer 실측 시퀀스 전문: docs/verified_facts/2026-07-27.md §A-8.
        """
        seq: list[P.Frame] = []
        for n in self.drive_nodes:
            seq += [P.sdo_write(n, P.OBJ_CONTROLWORD, P.CW_DRIVE_ENABLE, size=2),
                    P.sdo_write(n, P.OBJ_TARGET_VELOCITY, 0, size=4),
                    P.sdo_write(n, P.OBJ_LIFE_FACTOR, self.LIFE_FACTOR, size=1),
                    P.sdo_write(n, P.OBJ_GUARD_TIME, self.GUARD_TIME_MS, size=2),
                    P.sdo_write(n, P.OBJ_MODES, 3, size=1)]
        for n in self.steer_nodes:
            seq += [P.sdo_write(n, P.OBJ_CONTROLWORD, P.CW_DRIVE_ENABLE, size=2),
                    P.sdo_write(n, P.OBJ_HOMING_SPEED, self.HOMING_SPEED, size=4),
                    # ⚠ 호밍 트리거(0x60FB.4=1 RstStart)는 브링업에서 보내지 않는다 — 제어권 획득마다
                    #   조향축이 137° 왕복하기 때문. 호밍은 GUI '호밍' 버튼 → 판다 0xea 시퀀서
                    #   (Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h)로만 요청한다.
                    # 종전: P.sdo_write(n, P.OBJ_VENDOR_60FB, 1, size=1, sub=0x04)
                    P.sdo_write(n, P.OBJ_LIFE_FACTOR, self.LIFE_FACTOR, size=1),
                    P.sdo_write(n, P.OBJ_GUARD_TIME, self.GUARD_TIME_MS, size=2),
                    P.sdo_write(n, P.OBJ_MODES, 1, size=1),
                    P.sdo_write(n, P.OBJ_PROFILE_VELOCITY, self.PROFILE_VELOCITY, size=4),
                    P.sdo_write(n, P.OBJ_PROFILE_ACC, self.PROFILE_ACC, size=4),
                    P.sdo_write(n, P.OBJ_PROFILE_DEC, self.PROFILE_DEC, size=4)]
        for f in seq:
            self._send(f)
            time.sleep(0.002)

    # ── 내부: 루프 ──────────────────────────────────────────────────────────
    def _tx_loop(self):
        cmd_iv = 1.0 / self.cmd_hz
        guard_iv = 1.0 / self.guard_hz
        next_guard = time.monotonic()
        tick = 0
        fw_active = False   # TX-로컬 freewheel 적용 상태(엣지 검출용 — 이 스레드 단독 소유)
        while self._running:
            now = time.monotonic()
            with self._lock:
                estopped = self._estop
                freewheel = self._freewheel
                stale = (now - self._last_cmd_time) > self.cmd_timeout
                vel = {n: 0 for n in self.drive_nodes} if (estopped or stale) \
                    else dict(self._vel_units)
                steer = dict(self._steer_counts)
            # freewheel 상태 전이(구동축 servo-off ↔ 재-enable) — TX 단독 writer 유지
            # NOTE(debt-003): servo-off 1회 assert + guard 폴링 지속. HW가 조용히 재-enable하면 주기 재-assert 필요(벤치 미확인)
            if freewheel and not fw_active:
                for n in self.drive_nodes:
                    self._send(P.sdo_write(n, P.OBJ_CONTROLWORD, P.CW_DISABLE, size=2))
                fw_active = True
            elif not freewheel and fw_active:
                for n in self.drive_nodes:
                    self._send(P.sdo_write(n, P.OBJ_CONTROLWORD, P.CW_DRIVE_ENABLE, size=2))
                    self._send(P.sdo_write(n, P.OBJ_MODES, 3, size=1))
                fw_active = False
            # 조향 정착 게이트: 목표↔실측 편차 초과 시 이번 틱 구동 0
            with self._state_lock:
                unsettled = any(
                    self._nodes[sn].pos is not None and abs(steer[sn] - self._nodes[sn].pos)
                    > self.steer_settle_tol_counts for sn in self.steer_nodes)
            self.settling = unsettled
            if unsettled:
                vel = {n: 0 for n in self.drive_nodes}
            if not fw_active:   # freewheel 중 구동 지령 억제(servo-off 유지)
                for n in self.drive_nodes:
                    self._send(P.sdo_write(n, P.OBJ_TARGET_VELOCITY, vel[n], size=4))
            for sn in self.steer_nodes:
                if estopped:
                    # ⚠ E-stop 은 조향 신규 setpoint 만 억제 — PP 모드라 축은 멈추지 않고 직전 0x607A
                    #   목표까지 계속 회전한다(미해소). docs/code_review/motor_control/2026-07-26.md
                    #   §Medium 「_tx_loop — E-stop이 조향 지령을 차단하지 않음」
                    continue
                self._send(P.sdo_write(sn, P.OBJ_TARGET_POSITION, steer[sn], size=4))
                self._send(P.sdo_write(sn, P.OBJ_CONTROLWORD, P.CW_STEER_SETPOINT, size=2))
            if now >= next_guard:
                for n in self._all_nodes:
                    self._send(P.guard_rtr(n))
                next_guard = now + guard_iv
            # 피드백: 위치는 격틱(노드당 cmd_hz/2), 저속 오브젝트는 0.1s 마다 1건 순환
            if tick % 2 == 0:
                for n in self._all_nodes:
                    self._send(P.sdo_read(n, P.OBJ_POSITION_ACTUAL))
            if tick % max(1, int(self.cmd_hz * 0.1)) == 0:
                obj = self._slow_objs[self._slow_idx % len(self._slow_objs)]
                node = self._all_nodes[(self._slow_idx // len(self._slow_objs)) % len(self._all_nodes)]
                self._slow_idx += 1
                self._send(P.sdo_read(node, obj))
            tick += 1
            time.sleep(max(0.0, cmd_iv - (time.monotonic() - now)))

    def _rx_loop(self):
        while self._running:
            try:
                msg = self.bus.recv(timeout=0.1)
            except Exception:
                if self._running:
                    time.sleep(0.05)
                continue
            if msg is None or getattr(msg, "is_remote_frame", False):
                continue
            can_id = msg.arbitration_id
            node = can_id & 0x7F
            if P.GUARD_BASE <= can_id <= P.GUARD_BASE + 0x7F and node in self._nodes:
                with self._state_lock:
                    self._nodes[node].last_seen = time.monotonic()
                    self.rx_count += 1
                continue
            resp = P.parse_sdo_response(can_id, bytes(msg.data)) if len(msg.data) >= 8 else None
            if resp is None or resp.node not in self._nodes:
                continue
            with self._state_lock:
                st = self._nodes[resp.node]
                st.last_seen = time.monotonic()
                self.rx_count += 1
                if resp.kind == "read":
                    if resp.index == P.OBJ_POSITION_ACTUAL:
                        st.pos = resp.value
                    elif resp.index == P.OBJ_STATUSWORD:
                        st.status = resp.value & 0xFFFF
                    elif resp.index == P.OBJ_ERROR_CODE:
                        st.error = resp.value & 0xFFFF
                    elif resp.index == P.OBJ_CURRENT_ACTUAL:
                        st.current = ((resp.value & 0xFFFF) ^ 0x8000) - 0x8000  # INT16
                elif resp.kind == "abort":
                    st.aborts += 1

    def _send(self, frame: P.Frame):
        self.bus.send(_to_can(frame))
        self.tx_count += 1
