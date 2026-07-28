#!/usr/bin/env python3
"""필드 도킹 드라이버 — PC(amap-2)가 판다를 통해 모터를 구동하며 Seer를 속인다.

동작: 판다 SEER_GATE + intercept + auth=PC 로 두고, 판다 CAN_TX(bus2=모터)로 Tongyi 4축을 구동.
     Seer(CAN0)의 쓰기는 게이트가 차단+가짜ack, 읽기·guard는 통과 → Seer는 모터 살아있다고 인식.
     heartbeat(0xf3) 주기 전송 → ~~PC 죽으면 판다가 fail-safe passthrough 복귀.~~
     [정정 2026-07-27] PC 사망 시 판다는 **SAFETY_SILENT 로 전환**한다(passthrough 모드가 아니다).
       근거: board/main.c:248-250 `if (current_safety_mode != SAFETY_SILENT) { set_safety_mode(SAFETY_SILENT, 0U); }`
             docs/verified_facts/2026-07-27.md:133,144-145 §A-5 — "heartbeat 상실 시 펌웨어는
             SAFETY_SILENT 로 복귀한다(passthrough 아님) … 여러 문서·주석에 있던
             'heartbeat 소실 시 fail-safe passthrough 복귀'는 부정확하다".
       또한 2026-07-27 추가로 같은 블록이 릴레이를 물리 통과로 되돌리고 PC 주도권을 내린다
             (main.c:252-258 `set_intercept_relay(false); pc_authority = false;`).
       ⇒ "passthrough 복귀" 는 **릴레이 상태에 한한 표현**이며 safety mode 는 SILENT 다.
       ⚠ 단, 이 릴레이 해제는 최신 펌웨어에만 있다 — 동봉 panda.bin.signed(2026-07-23 빌드)에는 없다
         (flash_panda.py 상단 정정 참조).

⚠ 실로봇 구동. 저속 기본, stop/release 상비. 안전구역+E-stop 필수.
⚠⚠ [추가 2026-07-27] 이 스크립트는 조향 안전 램프를 **우회한다.**
   Tools/amr_test_gui 의 `SteerRamp`(±90° 하드 클램프 · ≤30° 단계 전진 · 단계별 실측 추종 확인 후
   다음 단계 · 미추종 시 FAULT 래치)가 GUI 경로에는 코드로 강제돼 있으나, 본 스크립트에는 없다.
   docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md:59 이 그 잔존 gap 을
   명시한다 — "필드 스크립트(`Tools/docking_field_kit/*.py`)나 임시 스크립트로 0x607A 를 직접
   송신하면 램프를 우회한다."
   실제로 `steer_deg()`(:112-115 부근)는 클램프·단계 램프 없이 STEER_HOME + deg*COUNTS_PER_DEG 를
   산출하고, `home()` 은 현재 위치와 무관하게 홈으로 **직접 점프**하며, `_tx_loop` 가 그 값을
   0x607A 로 즉시 송신한다. 이는 2026-07-27 node4 137° 물리 갇힘 사고의 **직접 원인 유형**이다
   (같은 문서 :49 "전범위 직접 점프 금지", :54 "±90° 하드 클램프 · ≤30° 단계 전진 · 단계별 실측
   추종 확인 후에만 다음 단계").
   ⇒ 사용 전 같은 문서 §재발 방지 ①~④(정본 상수·부호 인용 → 저각 단계 램프 → 이탈 시 즉시
     home·중단 → 단일 read 를 물리 진실로 신뢰 금지)를 **수동으로** 지킬 것.
   (코드에 클램프·램프를 넣는 것은 거동 변경이므로 별도 승인 사항 — 본 정정은 서술만 한다.)

근거 프로토콜: References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md (원 서술: 실측 확정).
   ⚠ [정정 2026-07-27] 이 문서는 아래 상수들을 **뒷받침하지 않는다** — 7871815 · 7840086 · 57344 ·
     24.447 이 해당 문서에 한 건도 없다(grep 0건, 2026-07-27 확인). 상수별 출처는 아래 상수 블록 참조.
클론 핀맵: CAN0=Seer(H4/L5·6), CAN2=모터(H23/L24). PINMAP.md
   (원 문장의 `tools/docking_field_kit/` 는 이식 전 경로. 현재 위치는 `Tools/docking_field_kit/`).

사용(대화형):
    python3 docking_drive.py
    명령: take / enable / f [mmps] / b [mmps] / s(top) / steer [deg] / home / release / q
"""
import os
import sys
import time
import struct
import threading

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from panda import Panda

MOTOR_BUS, SEER_BUS = 2, 0
SEER_GATE = 30

# ── Tongyi 프로토콜 상수 — 출처별 검증등급 병기 ──
#    (원 배너: "Tongyi 프로토콜 상수 (실측 확정)" — 아래 STEER_HOME 에 대해서는 그 라벨이 성립하지 않는다.)
DRIVE_NODES = (1, 2)
STEER_NODES = (3, 4)
CW_DRIVE_ENABLE = 0x86      # 0x6040 구동 enable(1회)
CW_STEER_ENABLE = 0x3F      # 0x6040 조향 운전(매 setpoint)
STEER_HOME = {3: 7871815, 4: 7840086}
# ⚠ 미판정 모순 (값 변경 금지 — 실측 없이 바꿀 수 없다):
#   · docs/verified_facts/2026-07-27.md:183-222 §B-1 "조향 홈 기준(steer_home_counts) ⚠ 안전 직결"
#     이 값을 **미판정 모순**으로 분류한다: Seer 1040 FrontSteer `encoder −7,871,810`(:191) vs
#     같은 시점 판다 read node3 ≈ −1,517 counts(:194) — 조향 노드에서만 7.87M counts(=137°) 어긋난다.
#     구동 노드는 두 소스가 절댓값 일치(:199-203)하므로 계통 오차가 아니다.
#     원인 후보 (:207-215): (a) 제어권 보유 중 판다 read 오염 / (b) 기동 후 드라이브가 위치 기준 재설정
#       — (b) 라면 이 값은 **기동 전에만** 유효하다. 어느 쪽인지 아직 못 가렸다.
#   · 정본 config 도 이미 경고를 달았다:
#     src/Actuators/motor_control/config/tongyi_amr.yaml:32
#       `steer_home_counts: [7871815, 7840086]  # ⚠ debt-007 판정 전까지 무비판 신뢰 금지`
#   · 관련 설계문서 docs/ros2_driver/2026-07-09-design-inputs.md:56,81 은 ~~"부팅 시 0x6064≈0 이 정상,
#     홈 상수는 절대 목표(steerOffset 137.3°), 매 기동 시 스윙 필요"~~ 라고 적어 조건부임을 시사한다.
#     ⚠ 정정 (2026-07-27) — 인용한 세 조각이 모두 실기 캡처로 갱신됐다:
#       ① "steerOffset 137.3°" 라는 단일값은 **config 어디에도 없다** — EasyDRIVE 파라미터는 축별로
#          node3 **138.000000** / node4 **137.250000** 이다
#          [References/motor_configuration/motor-config-analysis.md:24-30, 119-121;
#           docs/verified_facts/2026-07-27.md:215].
#       ② STEER_HOME 의 출처가 확정됐다 — **(steerOffset + 괄호보정) × 57,344**:
#            node3 (138.000000 − 0.726422) × 57344 = 7,871,816  (본 상수 7,871,815, Δ≈1)
#            node4 (137.250000 − 0.529735) × 57344 = 7,840,087  (본 상수 7,840,086, Δ≈1)
#          실기 확증: Seer 가 호밍 **전** 구간(t=0.035~17.880)에 정확히 이 값을 0x607A 로 지령
#          [Log/homing_capture_220350.jsonl; motor-config-analysis.md:118-121].
#       ③ "부팅 시 0x6064≈0 이 정상" 은 성립하지 않는다 — 이 캡처의 baseline(t≈0.034) 0x6064 는
#          node3 7,871,818 / node4 7,840,084 로 홈 부근이다. `0x6064` 가 정확히 0 이 되는 것은
#          **호밍 진행 구간(t≈18.0~49.2)뿐**이며 실위치가 아니다.
#       ④ "매 기동 시 스윙" 은 이상거동이 아니라 **설계된 이동**이다 — 조향축에는 리밋 스위치가 실재하고
#          호밍은 Home 1(음의 리밋 트리거, 전 노드 `0x6098 = 1` 실기 판독)로 원점을 잡은 뒤
#          **조향 0° 로 복귀**하는 데까지가 한 절차다 [Handbook V7.0 §4.6 page 116].
#     ⚠⚠ 본 상수는 **호밍 전** 목표다. 호밍 **후** Seer 의 목표는 t≈49.14 에
#       node3 **7,882,020** / node4 **7,859,062** 로 전환되어 t=180 까지 유지된다(각 6,319 프레임).
#       차이 +10,205 / +18,976 counts = **+0.178° / +0.331°**. 호밍 후 기준으로 이 상수를 쓰면 그만큼
#       어긋난다 ⇒ 절대 counts 하드코딩 대신 **매 기동 호밍 후 0x6064 리드백을 정본**으로 삼을 것
#       [Log/homing_capture_220350.jsonl; motor-config-analysis.md:128-134].
#       (상수 값 자체는 변경하지 않았다 — 거동 변경은 별도 승인 사항.)
#   판정에 필요한 측정 (verified_facts §B-1 "판정에 필요한 측정"):
#     ① 제어권 미획득(intercept off) 상태에서 판다로 조향 0x6064 를 여러 번 read
#     ② 같은 순간 Seer 1040 `encoder` 동시 조회
#     ③ 부호만 다르고 절댓값이 같으면 (a) 판다 read 오염 확정 / 계속 어긋나면 (b) 기준 재설정 확정
STEER_90 = 5160960          # ⚠ STEER_HOME 과 동일하게 §B-1 판정에 종속(홈 기준 상대값)
COUNTS_PER_DEG = 57344      # 근거: docs/ros2_driver/2026-07-09-design-inputs.md:30,33
VEL_PER_MMPS = 24.447       # 0.1rpm/(mm/s): ±24447=±1.0m/s → 0.1rpm = mmps*24.447
                            # 근거: docs/ros2_driver/2026-07-09-design-inputs.md:30,33
VEL_MAX = 4889              # ≈0.2 m/s 안전 상한 (기존 GUI 동일)
CMD_HZ = 50
HEARTBEAT_S = 0.4          # fail-safe 임계(2s, ignition off) 아래로 → 게이트 fail-safe 복귀 방지
                           # 임계값 근거: board/main.c:164-165 HEARTBEAT_IGNITION_CNT_OFF 2U (값은 정합 확인됨)
                           # ⚠ 원 주석의 "debt-003" 은 **원 프로젝트(CAN-Relay) 번호**이며, 본 저장소
                           #   docs/debt/registry.md:9 의 debt-003(backend.py freewheel servo-off /
                           #   Node Guarding RTR)과 **다른 항목**을 가리킨다 → 재등록 필요(미판정 인용).


def sdo_write(node, index, value, size=4):
    cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    data = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, 0]) + struct.pack("<i", value)[:size] + b"\x00" * (4 - size)
    return (0x600 + node, data[:8])


class DockingDriver:
    def __init__(self):
        self.p = Panda()
        self._lock = threading.Lock()
        self._vel = {1: 0, 2: 0}
        self._steer = dict(STEER_HOME)
        self.running = True
        self.controlling = False
        self._enabled = False
        self.hb = threading.Thread(target=self._heartbeat, daemon=True)
        self.tx = threading.Thread(target=self._tx_loop, daemon=True)
        self.hb.start()
        self.tx.start()

    def _heartbeat(self):
        while self.running:
            try:
                self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")  # heartbeat 리셋
            except Exception:
                pass
            time.sleep(HEARTBEAT_S)

    def take(self):
        """주도권 PC 취득: 게이트 모드 + intercept + auth=PC."""
        self.p.set_safety_mode(SEER_GATE, 0)
        for b in (SEER_BUS, MOTOR_BUS):
            self.p.set_can_speed_kbps(b, 250)
            self.p.set_can_enable(b, True)
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC 먼저
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept
        self.controlling = True
        print("[take] 주도권 PC (intercept+게이트). Seer는 모터 살아있다고 인식 유지.")

    def enable(self):
        for n in DRIVE_NODES:
            self._send(*sdo_write(n, 0x6040, CW_DRIVE_ENABLE, size=2))
        for n in STEER_NODES:
            self._send(*sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2))
        self._enabled = True
        print("[enable] 구동 0x86, 조향 0x3F")

    def drive(self, mmps):
        s = max(-VEL_MAX, min(VEL_MAX, int(mmps * VEL_PER_MMPS)))
        with self._lock:
            self._vel = {1: -s, 2: -s}   # 전진=음(실측)
        print(f"[drive] {mmps} mm/s (vel={-s})")

    def steer_deg(self, deg):
        # ⚠ 클램프·단계 램프 없음 — 입력 각도가 그대로 0x607A 지령이 된다(_tx_loop).
        #   상단 ⚠⚠ 블록(SteerRamp 우회 / mistake 2026-07-27-002) 참조. 기준값 STEER_HOME 은 §B-1 미판정.
        with self._lock:
            self._steer = {n: STEER_HOME[n] + int(deg * COUNTS_PER_DEG) for n in STEER_NODES}
        print(f"[steer] {deg}°")

    def home(self):
        # ⚠ 현재 위치와 무관한 **전범위 직접 점프**가 될 수 있다(단계 램프 없음).
        #   mistake 2026-07-27-002:49 "전범위 직접 점프 금지" — 상단 ⚠⚠ 블록 참조.
        with self._lock:
            self._steer = dict(STEER_HOME); self._vel = {1: 0, 2: 0}
        print("[home] 조향 홈 + 정지")

    def stop(self):
        with self._lock:
            self._vel = {1: 0, 2: 0}
        print("[stop] 속도 0")

    def release(self):
        """주도권 Seer 반환: 속도0 → auth=Seer → passthrough."""
        self.stop(); time.sleep(0.2)
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # passthrough
        self.p.set_safety_mode(0, 0)
        self.controlling = False; self._enabled = False
        print("[release] Seer 주도권 반환 (passthrough).")

    def _send(self, aid, data):
        try:
            self.p.can_send(aid, data, MOTOR_BUS)
        except Exception:
            pass

    def _tx_loop(self):
        iv = 1.0 / CMD_HZ
        while self.running:
            if self.controlling and self._enabled:
                with self._lock:
                    vel = dict(self._vel); steer = dict(self._steer)
                for n in DRIVE_NODES:
                    self._send(*sdo_write(n, 0x60FF, vel[n], size=4))
                for n in STEER_NODES:
                    self._send(*sdo_write(n, 0x607A, steer[n], size=4))
                    self._send(*sdo_write(n, 0x6040, CW_STEER_ENABLE, size=2))  # PP 매 사이클 래치
            time.sleep(iv)

    def shutdown(self):
        try:
            if self.controlling:
                self.release()
        except Exception:
            pass
        self.running = False
        time.sleep(0.2)
        try:
            self.p.close()
        except Exception:
            pass


HELP = "명령: take / enable / f [mmps] / b [mmps] / s(top) / steer [deg] / home / release / q(quit)"


def main():
    d = DockingDriver()
    print("=== 필드 도킹 드라이버 ===\n" + HELP)
    try:
        while True:
            try:
                cmd = input("> ").strip().split()
            except EOFError:
                break
            if not cmd:
                continue
            c = cmd[0].lower()
            arg = float(cmd[1]) if len(cmd) > 1 else None
            if c == "take": d.take()
            elif c == "enable": d.enable()
            elif c == "f": d.drive(arg if arg else 50)
            elif c == "b": d.drive(-(arg if arg else 50))
            elif c in ("s", "stop"): d.stop()
            elif c == "steer": d.steer_deg(arg if arg is not None else 0)
            elif c == "home": d.home()
            elif c == "release": d.release()
            elif c in ("q", "quit", "exit"): break
            else: print(HELP)
    finally:
        d.shutdown()
        print("종료.")


if __name__ == "__main__":
    main()
