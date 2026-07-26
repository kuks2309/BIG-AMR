#!/usr/bin/env python3
"""헤드리스 구동 엔진 — AMR(Autonomous Mobile Robot) 4륜 독립조향 CAN 드라이버.

GUI 분리 원칙: 구동/제어 로직을 PyQt 에서 완전히 분리한 순수 로직 계층.
can_relay/drive_gui.py 의 CAN 프로토콜 헬퍼 + DirectDriver 를 GUI 없이 추출(로직 비트 동일).
기구학 계산은 chassis_kinematics 에 위임(단일 책임 — 이 모듈은 CAN 송신·상태기계만).

계층:
  chassis_kinematics  → 순수 수학 (math only)
  direct_driver(본)   → CAN 프로토콜 + DirectDriver 스레드  ← GUI/relay 가 여기를 import
  relay_authority     → can-relay 주도권 코디네이터

원본: can_relay/drive_gui.py (can_relay_2026-07-10.zip)
프로토콜 근거: References/Tongyi-Motor-Controller/tongyi-canopen-protocol-reference.md
  노드 1/2=구동(0x60FF, 0.1rpm), 3/4=조향(0x607A). enable: 구동 0x6040=0x86, 조향=0x3F.

⚠ 실로봇 구동. 안전: E-STOP, 저속 기본, 2단계 발진(조향 정렬 후 구동). 실차는 안전구역+E-stop 상비.

사용:
    python3 direct_driver.py --selftest [--channel vcan1]   # 무-Seer DirectDriver 자가시험
"""
import struct
import threading
import time

import can

from chassis_kinematics import (
    COUNTS_PER_RAD, KIN_DRIVE_SIGN, KIN_STEER_OF, KIN_STEER_SIGN, KIN_VMAX,
    M_S_PER_UNIT, STEER_HOME, STEER_90, VEL_MAX, twist_to_targets,
)

# ── 프로토콜 상수 (측정/설정 확정 — CAN 계층 전용) ─────────────────────────
DRIVE_NODES = (1, 2)
STEER_NODES = (3, 4)
CW_DRIVE_ENABLE = 0x86
CW_STEER_ENABLE = 0x3F
GUARD_HZ = 20
CMD_HZ = 50
DEFAULT_BITRATE = 250000

# 2단계 발진(조향 정렬 후 주행): 조향 실측(0x6064)이 목표에 들어와야 구동 vel 인가
STEER_ALIGN_TOL = 2 * 57344     # 도착 허용오차 2° (57,344 counts/°)
STEER_ALIGN_POLL = 0.3          # 정렬 확인 주기 (s)
STEER_ALIGN_TIMEOUT = 10.0      # 정렬 대기 상한 (s) — 초과 시 주행 취소(정지 유지)


# ── CAN 프로토콜 헬퍼 (SDO/RTR — Handbook V7.0 §6.7) ───────────────────────
def sdo_write(node, index, value, size=4):
    cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    data = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, 0]) + struct.pack("<i", value)[:size] + b"\x00" * (4 - size)
    return can.Message(arbitration_id=0x600 + node, data=data[:8], is_extended_id=False)


def guard_rtr(node):
    return can.Message(arbitration_id=0x700 + node, is_remote_frame=True, dlc=0, is_extended_id=False)


def sdo_read(bus, node, index, sub=0, timeout=0.2):
    """SDO expedited upload — Handbook V7.0 §6.7 (p.156-157): 0x40 요청 → 0x4F/4B/47/43 응답.

    반환 (unsigned값, 바이트수) 또는 None(무응답/abort). 부호 해석은 호출측(오브젝트 타입별).
    """
    req = can.Message(arbitration_id=0x600 + node,
                      data=bytes([0x40, index & 0xFF, (index >> 8) & 0xFF, sub, 0, 0, 0, 0]),
                      is_extended_id=False)
    bus.send(req)
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        m = bus.recv(timeout=timeout)
        if (not m or m.arbitration_id != 0x580 + node or getattr(m, "is_remote_frame", False)
                or len(m.data) < 4):
            continue
        d = m.data
        if d[1] != (index & 0xFF) or d[2] != ((index >> 8) & 0xFF) or d[3] != sub:
            continue
        nbytes = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}.get(d[0])
        if nbytes is None:  # 0x80 abort 포함
            return None
        return (int.from_bytes(d[4:4 + nbytes], "little"), nbytes)
    return None


def to_signed(v, bits):
    return v - (1 << bits) if v >= (1 << (bits - 1)) else v


# ── 직접 주행 드라이버 (PC=마스터, 헤드리스) ────────────────────────────────
class DirectDriver(threading.Thread):
    """CAN 버스 마스터 스레드 — enable·guarding·50Hz TX·2단계 발진. GUI 의존 0.

    채널은 모터 측 버스(can-relay 연동 시 can1). 상태(_vel/_steer)를 락으로 보호하고
    run() 이 CMD_HZ 로 송신. set_twist/set_mode/home_steer/estop 로 목표만 갱신.
    """

    def __init__(self, channel, steer_home=None, log=None):
        super().__init__(daemon=True)
        self.bus = can.Bus(channel=channel, interface="socketcan", receive_own_messages=False)
        self.log = log or (lambda *_: None)
        self.steer_home = dict(steer_home or STEER_HOME)
        self._lock = threading.Lock()
        self._vel = {1: 0, 2: 0}
        self._steer = dict(self.steer_home)
        self._pending = None          # (인가 대기 vel dict, 시작 monotonic) — 조향 정렬 후 발진
        self._next_align_poll = 0.0
        self.running = True
        self.mode = "STOP"
        self.tx = 0

    def enable(self):
        # ⚠ 운용 전제(2026-07-09 실차 확인): 전원 인가 후 모터 자체 호밍이 끝난 뒤에 시작할 것 —
        #   호밍 완료 전 명령 시 조향이 잠긴 것처럼 보임 (issues_and_fixes 2026-07-09 항목 참조).
        for n in DRIVE_NODES:
            self.bus.send(sdo_write(n, 0x6040, CW_DRIVE_ENABLE, size=2)); self.tx += 1
        for n in STEER_NODES:
            self.bus.send(sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2)); self.tx += 1
        self.log("[direct] enable (구동 0x86, 조향 0x3F)")

    def set_mode(self, mode, speed):
        """이산 모드 — 2단계 발진: 조향 목표만 먼저 걸고(vel 0), 실측 0x6064 정렬 확인 후 vel 인가."""
        h = self.steer_home
        s = max(0, min(int(speed), VEL_MAX))
        vel, steer = None, None
        if mode == "FORWARD":
            vel = {1: -s, 2: -s}; steer = dict(h)
        elif mode == "BACKWARD":
            vel = {1: s, 2: s}; steer = dict(h)
        elif mode == "CRAB_L":
            vel = {1: s, 2: s}; steer = {n: h[n] + STEER_90 for n in STEER_NODES}
        elif mode == "CRAB_R":
            vel = {1: -s, 2: -s}; steer = {n: h[n] + STEER_90 for n in STEER_NODES}
        elif mode == "SPIN_L":
            vel = {1: s, 2: -s}; steer = {n: h[n] + STEER_90 for n in STEER_NODES}
        elif mode == "SPIN_R":
            vel = {1: -s, 2: s}; steer = {n: h[n] + STEER_90 for n in STEER_NODES}
        with self._lock:
            self.mode = mode
            if steer is None:  # STOP 등 — 즉시 정지, 대기 취소
                self._vel = {1: 0, 2: 0}
                self._pending = None
            else:
                self._steer = steer
                self._vel = {1: 0, 2: 0}                      # 정렬 전 구동 금지
                self._pending = (dict(vel), time.monotonic())  # run 루프가 정렬 확인 후 인가
                self._next_align_poll = 0.0
        self.log(f"[direct] mode={mode} speed={s}" + ("" if steer is None else " — 조향 정렬 대기"))

    def set_twist(self, vx, vy, w, vmax=KIN_VMAX):
        """차체명령 (vx,vy,ω) → chassis_kinematics.twist_to_targets → 노드별 목표 갱신 (연속 제어)."""
        vel_units, steer_counts = twist_to_targets(vx, vy, w, vmax, self.steer_home)
        with self._lock:
            self.mode = "TWIST"
            self._pending = None  # 기구학 모드는 연속 제어 — 이산 발진 대기와 배타
            self._vel.update(vel_units)
            self._steer.update(steer_counts)
        self.log(f"[kin] vx={vx:.3f} vy={vy:.3f} ω={w:.3f}")

    def home_steer(self):
        """조향 홈 복귀 — vel 0 + 조향 목표=홈 (크랩/스핀 후 바퀴 정렬용 homing)."""
        with self._lock:
            self.mode = "HOME"
            self._vel = {1: 0, 2: 0}
            self._steer = dict(self.steer_home)
            self._pending = None
        self.log("[direct] steer home")

    def estop(self):
        with self._lock:
            self.mode = "ESTOP"; self._vel = {1: 0, 2: 0}; self._pending = None
        self.log("[direct] E-STOP")

    def run(self):
        self.enable()
        guard_iv = 1.0 / GUARD_HZ
        cmd_iv = 1.0 / CMD_HZ
        next_guard = time.monotonic()
        while self.running:
            now = time.monotonic()
            with self._lock:
                vel = dict(self._vel); steer = dict(self._steer); pending = self._pending
            for n in DRIVE_NODES:
                self.bus.send(sdo_write(n, 0x60FF, vel[n], size=4)); self.tx += 1
            for n in STEER_NODES:
                self.bus.send(sdo_write(n, 0x607A, steer[n], size=4)); self.tx += 1
                # 매 사이클 controlword 0x3F 재전송 — PP new-setpoint 래치 (Seer 실측 동작 일치).
                # 1회만 보내면(enable 시) 서보가 새 조향 목표를 안 받아 이전 자세 방치→크랩. (issue: 전진=크랩)
                self.bus.send(sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2)); self.tx += 1
            if pending and now >= self._next_align_poll:
                # 2단계 발진: 조향 실측(0x6064)이 전 노드 목표 ±2° 안에 들어오면 vel 인가
                self._next_align_poll = now + STEER_ALIGN_POLL
                aligned = True
                for n in STEER_NODES:
                    r = sdo_read(self.bus, n, 0x6064, timeout=0.1)
                    if r is None or abs(to_signed(r[0], r[1] * 8) - steer[n]) > STEER_ALIGN_TOL:
                        aligned = False
                        break
                if aligned:
                    with self._lock:
                        if self._pending:
                            self._vel = self._pending[0]
                            self._pending = None
                    self.log(f"[direct] 조향 정렬 완료 → 주행 ({self.mode})")
                elif now - pending[1] > STEER_ALIGN_TIMEOUT:
                    with self._lock:
                        self._pending = None
                    self.log("[direct] ⚠ 조향 정렬 시간초과 — 주행 취소(정지 유지)")
            if now >= next_guard:
                for n in DRIVE_NODES + STEER_NODES:
                    self.bus.send(guard_rtr(n)); self.tx += 1
                next_guard = now + guard_iv
            time.sleep(cmd_iv)

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        try:
            for n in DRIVE_NODES:
                self.bus.send(sdo_write(n, 0x60FF, 0, size=4))
        except Exception:
            pass
        time.sleep(0.1)
        self.bus.shutdown()


def _selftest(channel="vcan1") -> bool:
    """무-Seer DirectDriver 송신 경로 검증 (가상 CAN 필요: sudo modprobe vcan; sudo ip link add vcan1 type vcan; sudo ip link set vcan1 up)."""
    print(f"DirectDriver 자가시험 (채널 {channel}):")
    try:
        d = DirectDriver(channel)
    except Exception as e:
        print(f"  SKIP — 버스 {channel} 없음: {e}")
        print("  (vcan 준비: sudo modprobe vcan && sudo ip link add vcan1 type vcan && sudo ip link set vcan1 up)")
        return True  # 버스 부재는 실패 아님(무-하드웨어 환경)
    d.start(); time.sleep(0.2)
    d.set_twist(0.05, 0, 0); time.sleep(0.2)   # 기구학 모드 송신 경로
    d.set_twist(0, 0, 0.1); time.sleep(0.2)
    d.home_steer(); time.sleep(0.1)            # 조향 홈복귀 경로
    d.estop(); time.sleep(0.1)
    tx = d.tx
    d.shutdown()
    ok = tx > 0
    print(f"  tx={tx} 프레임 -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    import sys
    ch = "vcan1"
    if "--channel" in sys.argv:
        ch = sys.argv[sys.argv.index("--channel") + 1]
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest(ch) else 1)
    print(__doc__)
