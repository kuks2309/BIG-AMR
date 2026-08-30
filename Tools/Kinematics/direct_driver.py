#!/usr/bin/env python3
"""헤드리스 구동 엔진 — AMR(Autonomous Mobile Robot) 4륜 독립조향 CAN 드라이버.

GUI 분리 원칙: 구동/제어 로직을 PyQt 에서 완전히 분리한 순수 로직 계층.
CAN 백엔드는 CanTransport 로 추상화(ADR 2026-07-28) — 이 모듈은 백엔드를 모르고 트랜스포트만 안다.
기구학 계산은 chassis_kinematics, SDO/RTR 코덱은 can_protocol 에 위임(단일 책임).

계층:
  chassis_kinematics  → 순수 수학 (math only)
  can_protocol        → SDO/RTR 코덱 (stdlib, CanFrame)
  can_transport       → CanTransport 백엔드 (socketcan/pcan/mock/panda)
  direct_driver(본)   → DirectDriver 상태기계·50Hz TX 루프  ← GUI/relay 가 여기를 import
  authority           → can-relay 주도권 코디네이터

원본: can_relay/drive_gui.py (can_relay_2026-07-10.zip)
프로토콜 근거: References/Tongyi-Motor-Controller/tongyi-canopen-protocol-reference.md
  노드 1/2=구동(0x60FF, 0.1rpm), 3/4=조향(0x607A). enable: 구동 0x6040=0x86, 조향=0x3F.

⚠ 실로봇 구동. 안전: 트랜스포트 arm 게이트(비무장 send 차단), 2단계 발진(조향 정렬 후 구동),
  E-STOP, 저속 기본. run() 은 비무장 트랜스포트면 구동을 거부(fail-safe). 실차는 안전구역+E-stop 상비.

사용:
    python3 direct_driver.py --selftest   # MockTransport 무-하드웨어 자가시험 (tegra 가능)
"""
import threading
import time

from can_protocol import guard_rtr, sdo_read, sdo_write, to_signed
from chassis_kinematics import (
    KIN_VMAX, STEER_90, STEER_HOME, VEL_MAX, twist_to_targets,
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


# ── 직접 주행 드라이버 (PC=마스터, 헤드리스) ────────────────────────────────
class DirectDriver(threading.Thread):
    """CAN 트랜스포트 마스터 스레드 — enable·guarding·50Hz TX·2단계 발진. GUI/백엔드 의존 0.

    transport 는 이미 open()·arm() 된 CanTransport(caller 소유·주입). run() 진입 시 비무장이면
    구동을 거부(fail-safe). 상태(_vel/_steer)를 락으로 보호하고 run() 이 CMD_HZ 로 송신.
    set_twist/set_mode/home_steer/estop 로 목표만 갱신.
    """

    def __init__(self, transport, steer_home=None, log=None):
        super().__init__(daemon=True)
        self.transport = transport
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

    @classmethod
    def from_channel(cls, channel, backend="socketcan", steer_home=None, log=None, arm=True):
        """하위호환 — 채널 문자열로 트랜스포트를 열고(기본 arm) DirectDriver 생성.

        구 DirectDriver(channel) 호출부 대체. arm=False 면 caller 가 preflight 후 명시 arm.
        """
        from can_transport import open_transport
        tp = open_transport(f"{backend}:{channel}").open()
        if arm:
            tp.arm()
        return cls(tp, steer_home=steer_home, log=log)

    def enable(self):
        # ⚠ 운용 전제(2026-07-09 실차 확인): 전원 인가 후 모터 자체 호밍이 끝난 뒤에 시작할 것 —
        #   호밍 완료 전 명령 시 조향이 잠긴 것처럼 보임 (issues_and_fixes 2026-07-09 항목 참조).
        for n in DRIVE_NODES:
            self.transport.send(sdo_write(n, 0x6040, CW_DRIVE_ENABLE, size=2)); self.tx += 1
        for n in STEER_NODES:
            self.transport.send(sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2)); self.tx += 1
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
        if not self.transport.is_armed:  # fail-safe: 비무장 트랜스포트면 구동 거부(프레임 0)
            self.log("[direct] ⚠ 트랜스포트 비무장 — 구동 중단 (arm() 필요)")
            return
        self.enable()
        guard_iv = 1.0 / GUARD_HZ
        cmd_iv = 1.0 / CMD_HZ
        next_guard = time.monotonic()
        while self.running:
            now = time.monotonic()
            with self._lock:
                vel = dict(self._vel); steer = dict(self._steer); pending = self._pending
            for n in DRIVE_NODES:
                self.transport.send(sdo_write(n, 0x60FF, vel[n], size=4)); self.tx += 1
            for n in STEER_NODES:
                self.transport.send(sdo_write(n, 0x607A, steer[n], size=4)); self.tx += 1
                # 매 사이클 controlword 0x3F 재전송 — PP new-setpoint 래치 (Seer 실측 동작 일치).
                # 1회만 보내면(enable 시) 서보가 새 조향 목표를 안 받아 이전 자세 방치→크랩. (issue: 전진=크랩)
                self.transport.send(sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2)); self.tx += 1
            if pending and now >= self._next_align_poll:
                # 2단계 발진: 조향 실측(0x6064)이 전 노드 목표 ±2° 안에 들어오면 vel 인가
                self._next_align_poll = now + STEER_ALIGN_POLL
                aligned = True
                for n in STEER_NODES:
                    r = sdo_read(self.transport, n, 0x6064, timeout=0.1)
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
                    self.transport.send(guard_rtr(n)); self.tx += 1
                next_guard = now + guard_iv
            time.sleep(cmd_iv)

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        try:
            for n in DRIVE_NODES:
                self.transport.send(sdo_write(n, 0x60FF, 0, size=4))
        except Exception:
            pass
        time.sleep(0.1)
        self.transport.disarm()
        self.transport.shutdown()


def _selftest() -> bool:
    """MockTransport 무-하드웨어 자가시험 (tegra 가능) — TX 경로 + 2단계 정렬 vel 게이트 검증."""
    from can_transport import MockTransport
    print("DirectDriver 자가시험 (MockTransport, 무-하드웨어):")
    tp = MockTransport().open(); tp.arm()
    d = DirectDriver(tp)
    d.start(); time.sleep(0.15)
    d.set_twist(0.05, 0, 0); time.sleep(0.1)   # 기구학 모드 송신 경로
    d.set_twist(0, 0, 0.1); time.sleep(0.1)
    d.home_steer(); time.sleep(0.05)           # 조향 홈복귀 경로
    d.estop(); time.sleep(0.05)
    tx = d.tx
    d.shutdown()
    ids = tp.sent_ids()
    ok = tx > 0 and 0x601 in ids and 0x603 in ids and 0x701 in ids
    print(f"  tx={tx} · arb-ids={[hex(i) for i in ids]} -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
