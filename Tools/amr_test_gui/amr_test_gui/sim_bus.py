"""SimBus — dry-run 시뮬레이터 버스(하드웨어 무접촉).

ADR 2026-07-27-amr-test-gui 검증계단 ① 용. 실제 Tongyi 드라이브 대신 SDO 요청에 응답해
backend·램프·UI·FAULT 경로를 실차 없이 검증한다. **물리 모델이 아니다** — 프로토콜 표면만 모사한다.

모사 범위: SDO expedited write ack(0x60) · read 응답(0x43) · Node Guarding 응답.
조향은 지령(0x607A)을 향해 `steer_rate_dps` 로 수렴, 구동은 지령(0x60FF)을 위치로 적분한다.
`stuck_nodes` 로 특정 노드를 무응답/부동(不動) 상태로 만들어 램프 FAULT 경로를 재현할 수 있다.
"""
from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from .motor_control_import import protocol as P
from .constants import COUNTS_PER_DEG, COUNTS_PER_M, M_S_PER_UNIT, STEER_HOME_COUNTS


class SimBus:
    """python-can Bus 호환 시뮬레이터: send / recv / shutdown."""

    def __init__(self, *, drive_nodes=(1, 2), steer_nodes=(3, 4),
                 steer_rate_dps: float = 45.0, stuck_nodes=(), silent_nodes=(),
                 logger=print):
        self.log = logger
        self.drive_nodes = tuple(drive_nodes)
        self.steer_nodes = tuple(steer_nodes)
        self.steer_rate = float(steer_rate_dps) * COUNTS_PER_DEG   # counts/s
        self.stuck = set(stuck_nodes)      # 지령을 받지만 움직이지 않음 → 램프 FAULT 재현
        self.silent = set(silent_nodes)    # SDO 응답 자체를 안 함 → 브링업 NodeSilent 재현
        self._lock = threading.Lock()
        self._q: list = []
        self._t0 = time.monotonic()
        self._pos = {n: 0 for n in self.drive_nodes}
        self._pos.update({n: STEER_HOME_COUNTS.get(n, 0) for n in self.steer_nodes})
        self._steer_target = {n: STEER_HOME_COUNTS.get(n, 0) for n in self.steer_nodes}
        self._steer_pending: dict[int, int] = {}   # 0x607A 수신분 — 0x6040=0x3F 로만 래치
        self._vel = {n: 0 for n in self.drive_nodes}
        self._status = {n: 0x1237 for n in (*self.drive_nodes, *self.steer_nodes)}  # 임의 정상값
        self._error = {n: 0 for n in (*self.drive_nodes, *self.steer_nodes)}
        self._last = time.monotonic()
        self.tx_count = 0

    # ── 물리(모사) 적분 ─────────────────────────────────────────────────────
    def _integrate(self):
        now = time.monotonic()
        dt = now - self._last
        if dt <= 0:
            return
        self._last = now
        for n in self.steer_nodes:
            if n in self.stuck:
                continue
            cur, tgt = self._pos[n], self._steer_target[n]
            step = self.steer_rate * dt
            self._pos[n] = tgt if abs(tgt - cur) <= step else cur + (step if tgt > cur else -step)
        for n in self.drive_nodes:
            if n in self.stuck:
                continue
            self._pos[n] += int(self._vel[n] * M_S_PER_UNIT * COUNTS_PER_M * dt)

    # ── python-can 호환 표면 ────────────────────────────────────────────────
    def send(self, msg):
        self.tx_count += 1
        with self._lock:
            self._integrate()
            if getattr(msg, "is_remote_frame", False):
                node = msg.arbitration_id - P.GUARD_BASE
                if node not in self.silent:
                    self._q.append(SimpleNamespace(
                        arbitration_id=P.GUARD_BASE + node, data=b"\x05", is_remote_frame=False))
                return
            aid, data = msg.arbitration_id, bytes(msg.data)
            node = aid - P.SDO_RX_BASE
            if node in self.silent or len(data) < 8:
                return
            cmd = data[0]
            index = data[1] | (data[2] << 8)
            sub = data[3]
            val = int.from_bytes(data[4:8], "little", signed=True)
            if cmd in (0x2F, 0x2B, 0x23):          # write
                if index == P.OBJ_TARGET_POSITION and node in self.steer_nodes:
                    # PP 모드: 0x607A 만으로는 적용되지 않는다. 0x6040=0x3F(신규 setpoint) 를
                    # 받아야 래치된다 — 실기 거동을 모사해야 컨트롤워드 누락 회귀를 dry-run 이
                    # 잡을 수 있다(리뷰 #M9).
                    self._steer_pending[node] = val
                elif index == P.OBJ_CONTROLWORD and node in self.steer_nodes:
                    if (val & 0xFFFF) == P.CW_STEER_SETPOINT and node in self._steer_pending:
                        self._steer_target[node] = self._steer_pending.pop(node)
                elif index == P.OBJ_TARGET_VELOCITY and node in self.drive_nodes:
                    self._vel[node] = val
                self._reply(node, 0x60, index, sub, 0)
            elif cmd == 0x40:                       # read
                self._reply(node, 0x43, index, sub, self._read_obj(node, index))

    def _read_obj(self, node: int, index: int) -> int:
        if index == P.OBJ_POSITION_ACTUAL:
            return self._pos.get(node, 0)
        if index == P.OBJ_STATUSWORD:
            return self._status.get(node, 0)
        if index == P.OBJ_ERROR_CODE:
            return self._error.get(node, 0)
        if index == P.OBJ_CURRENT_ACTUAL:
            return 12                               # 0.12 A 임의 정상값
        return 0

    def _reply(self, node: int, cmd: int, index: int, sub: int, value: int):
        payload = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, sub]) + \
            int(value).to_bytes(4, "little", signed=True)
        self._q.append(SimpleNamespace(arbitration_id=P.SDO_TX_BASE + node,
                                       data=payload, is_remote_frame=False))

    def recv(self, timeout: float = 0.1):
        deadline = time.time() + timeout
        while True:
            with self._lock:
                if self._q:
                    return self._q.pop(0)
            if time.time() >= deadline:
                return None
            time.sleep(0.001)

    def shutdown(self):
        self.log("[SimBus] dry-run 버스 종료.")

    # ── 시험 조작 ───────────────────────────────────────────────────────────
    def set_stuck(self, node: int, stuck: bool):
        """노드를 부동 상태로 만들어 램프 FAULT 경로를 재현한다."""
        with self._lock:
            self.stuck.add(node) if stuck else self.stuck.discard(node)
