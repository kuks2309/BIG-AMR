#!/usr/bin/env python3
"""amap-2 실 시스템 신뢰성/안전 모니터 — 순차 A→B + Seer home신호 이상 검출.

목적:
  실 Seer↔판다↔모터 배선 상태에서, 판다를 통해 흐르는 CAN 트래픽을 관찰하여
  (1) Seer가 정상 폴링/모터가 정상 응답하는지,
  (2) **작동이상으로 Seer가 home(호밍/홈복귀) 신호를 내보내는지** 반드시 검출하여 문제 유무를 확인.

두 위상(순차):
  A. monitor (passthrough 리슨)  — 판다 SILENT, 송신 없음. 실 로봇 무개입(안전). 야간/무인 가능.
  B. gate    (intercept 투명중계) — 판다 SEER_GATE + intercept + auth=Seer(투명). 판다 삽입이
     Seer↔모터 통신을 교란하지 않는지 + 삽입 자극으로 Seer가 재호밍(home) 명령을 내는지 검증.
     ⚠ 실 버스에 판다 삽입 → 반드시 사람이 지켜보는 상태에서(attended).
     ~~heartbeat 유지~~, 종료 시 강제 passthrough 복귀.
     [정정 2026-07-27] **heartbeat(0xf3) 는 전송하지 않는다** — docstring 이 코드와 반대였다.
       코드 근거: 본 파일 `phase_gate` 의 `self.hb_on = False`(:170 부근)와 그 위 주석(:163-169),
                 `phase_gatecheck` 의 `self.hb_on = False`(:274 부근),
                 `_heartbeat` 스레드(:138-145)는 `hb_on` 이 False 면 아무것도 보내지 않는다.
       즉 이 경로는 `set_safety_mode(disable_checks=True)` 로 얻은 heartbeat_disabled 상태를
       **유지**하는 것이 의도다(위 주석 참조).

home신호(호밍/홈복귀) 판정 근거 — Tongyi CANopen SDO write(0x600+N) 디코드:
  0x607A Target_position  : 위치 명령. STEER_HOME 근처(±허용)면 **HOME(홈복귀)**, 그 외 위치이동.
  ~~0x6060 Modes=6          : **HOMING 모드 진입**~~
  0x6098 Homing_method / 0x6099 Homing_speeds : **HOMING 설정**
  ~~0x6040 Controlword bit4(0x1F 등) in homing : **HOMING 시작**~~
  0x60FF Target_velocity != 0 : 구동(모션)
⚠ 정정 (2026-07-27) — 위 호밍 판정 근거 중 3건이 매뉴얼·실측과 어긋난다:
  ① **`0x6060=6` 은 이 드라이브의 호밍 지표가 아니다.** 0x6060 Modes_of_operation 유효값은
     1(PP)/3(PV)/4(PT)/7/8/9/10 뿐이고 **6(CiA402 표준 Homing mode)은 문서에 없다**
     [Handbook V7.0 §6.6.3, page 152 / Handbook_V7.0.txt:7578-7592].
     오히려 Home 1/2 는 **PP(0x6060=1)** 에서만 유효하다 — "the driver needs to run in the PP mode
     to be valid" [같은 문서 §4.6, page 116 / .txt:5929-5931].
     실측도 일치: Log/homing_capture_220350.jsonl(253,510 프레임 전수)에서 `0x6060=6` **0건**,
     조향 노드 `0x6060=1` 이 t=49.0324(node4)/49.1134(node3) 에 각 1회(= 호밍 **완료 후** PP 설정).
  ② **호밍 활성 controlword 비트는 bit4 가 아니라 bit15(Reset Home) 다.**
     "Bit15: Reset Home is the motor homing activation bit. When this bit is set to 1, the homing
     operation is activated" [Handbook V7.0 §6.6.1, page 149-150 / .txt:7495-7497].
     bit4 는 PP 모드의 **New set-point** 이며 정상 주행 중 상시 세트된다(실차 controlword 0x3F)
     [같은 문서 page 150 표 / .txt:7481].
     ⇒ 현재 `(uval & 0x10)` 규칙은 정상 PP 지령을 「HOMING 시작」으로 **오탐**한다.
  ③ **실차 Seer 의 진짜 호밍 개시 트리거는 `0x60FB.04 = 1`(RstStart) 이며 판정 집합에 없다.**
     "60FB / sub 4 / RECORD / RstStart / UINT8 / RW", "0-Reset off, 1-Reset on"
     [Handbook V7.0 §6.9, page 171 / Appendix I, page 196; .txt:8596, :9659].
     실측: Log/homing_capture_220350.jsonl t=17.9252(node3) / t=17.9257(node4) 에 `0x60FB.4=1`
     각 1회 → 31 ms 뒤 `0x6041` bit15=0 최초 관측(t=17.9562/17.9567) = 호밍 개시.
     ⚠ 전이 시각 아님 — 직전 폴 t=5.138, 확정 구간 (5.138, 17.956].
     같은 캡처 전 구간에서 조향 controlword 는 **0x3F/0x86 뿐이고 bit15 는 0건**,
     `0x6098`(Homing method)은 **write·read 모두 0건**(드라이브 저장값 `0x6098=1` = Home 1 사용).
  ⇒ 현재 `decode_seer_write` 는 **실차의 실제 호밍 개시를 탐지하지 못한다**(안전 직결 미탐 공백).
     분기 수정은 거동 변경이므로 별도 승인 사항 — 본 정정은 서술만 한다.
~~정상 관찰(로봇 정차/노드대기) 시 위 write는 나오면 안 됨 → 나오면 이상신호로 로그·카운트.~~
[정정 2026-07-27] 위 무조건형은 `0x607A` 에 대해 **반증돼 있다.**
  · 정차 중 `0x607A` = home 값 지속 전송은 **정상**(position-hold)이다.
    실측: HANDOFF-amap2.md:28 "Seer가 steer 노드 3·4에 0x607A(Target_position) = 정확히 home 값을
          매 사이클 지속 전송", :31 "정차 position-hold(정상). 작동이상 home신호 아님"
          (NEXT-SESSION-PROMPT.md:13 동일).
  · 본 파일 자신의 분류·요약도 이미 그렇게 판정한다 — `decode_seer_write` 의 `home_hold` 분기(:102-104),
    `summary` 의 "ℹ Seer가 steer를 home위치로 지속 지령 = 정차 position-hold(정상)"(:253-254).
  ⇒ 정차 중 **이상 판정 대상**은 다음에 한한다:
      ~~0x6060=6 · 0x6098/0x6099 · homing controlword · **home 범위 밖** 0x607A · 0x60FF≠0.~~
      ⚠ 정정 (2026-07-27) — 위 집합은 **실차의 실제 호밍 트리거를 빠뜨리고 오탐을 포함한다.**
        정본 집합: **`0x60FB.04=1`(RstStart, 실측 트리거)** · `0x6099`(Homing speeds) ·
        `0x6098`(Homing method — 실차에서는 미기록) · controlword **bit15**(Reset Home) ·
        **home 범위 밖** `0x607A` · `0x60FF≠0`.
        제외: `0x6060=6`(이 드라이브 미지원 값) · controlword **bit4**(PP New set-point = 정상).
        [근거: Handbook V7.0 §6.9 page 171 · Appendix I page 196(0x60FB.4 RstStart),
               §6.6.1 page 149-150(bit15 Reset Home), §6.6.3 page 152(0x6060 유효값),
               §4.6 page 116(Home 1/2 는 PP 모드) /
         실측 Log/homing_capture_220350.jsonl t=17.9252·17.9257(0x60FB.4=1),
               t=17.9183·17.9188(0x6099=2500)]
  ⚠ 단, "home 범위 안/밖"의 기준인 STEER_HOME 자체가 미판정이다(아래 STEER_HOME 주석 참조).

위상 C(선택, gatecheck): auth=PC로 게이트를 닫고 PC는 구동하지 않은 채, Seer의 home/write가
  모터측(bus2)으로 **누출되지 않고 차단**되는지 검증 → 도킹 시 Seer의 지속 home지령이 PC와 충돌하지
  않음을 사전 확인(치명 안전항목). PC 구동은 안 하므로 모터는 안 움직임.

사용:
  python3 amap2_monitor.py monitor 30          # A만 30초(안전, 무개입)
  python3 amap2_monitor.py monitor 28800        # A 8시간 야간(무인 안전)
  python3 amap2_monitor.py gate 30              # B만 30초(attended, 판다 삽입, 투명중계)
  python3 amap2_monitor.py gatecheck 30        # C 30초(attended, 게이트가 Seer home 차단하는지)
  python3 amap2_monitor.py seq 30 30           # A 30초 → B 30초 → 자동 passthrough 복귀
로그: ~/docking_reliability/amap2_monitor.log (이상신호 전량 append)
"""
import os
import sys
import time
import struct
import threading

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from panda import Panda

SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE = 30
DRIVE_NODES = (1, 2)
STEER_NODES = (3, 4)
# ══ 정정 2026-08-03 ══ 값 갱신 [7871810, 7839894] → [7871815, 7840086].
#   **정본은 src/Comm/CAN/can_relay/config/machine/foil_a082.yaml `steer_home_counts` 하나다.**
#   여기 값은 그 사본이며, 정본이 바뀌면 함께 갱신한다.
#   이전 값은 0° 가 아니라 **raw 판독값**이었다 — 0° 는 Seer 각도로 역산해야 한다:
#         0° = CAN_0x6064 + Seer_deg × 57344
#   2026-08-02 종결은 이 식을 문서에 적어 놓고도 채택값에 적용하지 않았다. node3 은 그때
#   Seer 가 +0.0001° 라 오차가 6c 에 그쳐 안 드러났고, node4 는 +0.0035° 여서 193c 로 드러났다.
#   실측 확정 (2026-08-03 11:44, orin_steer_crosscheck.py, SILENT·passthrough, 송신 0건,
#   사용자 확인 Seer 표시 0°, 2회 독립 실행이 counts 단위까지 동일):
#     node3  CAN 7,871,823 + (−0.000°) → 0° = 7,871,816   (채택값과 1c 차)
#     node4  CAN 7,840,052 + (+0.001°) → 0° = 7,840,087   (채택값과 1c 차)
#   ⇒ 「구값은 출처 없는 값」이라는 2026-08-02 판정은 반증됐다 — 출처는 Seer 가 실시간으로
#     내는 0x607A 조향 목표이고, 값도 맞다. 근거 docs/homing/2026-08-03-can-relay-homing-assets.md §10
#   ⚠ 7882020 / 7859062 는 펌웨어 GOZERO 상수(호밍 후 정착 목표)이며 0° 가 아니다 — 별개 사안.
STEER_HOME = {3: 7871815, 4: 7840086}
# ── 이하 이력: 위 실측 이전의 「미판정」 서술이다. 원문 보존 ─────────────────
# ⚠ 미판정 — 이 홈 기준은 아직 확정된 값이 아니다 (값 변경 금지):
#   docs/verified_facts/2026-07-27.md:183-222 §B-1 "조향 홈 기준(steer_home_counts) ⚠ 안전 직결" 이
#   미판정 모순으로 분류한다 — Seer 1040 FrontSteer `encoder −7,871,810`(:191) vs 같은 시점
#   판다 read node3 ≈ −1,517 counts(:194) 로 **조향 노드에서만 7.87M counts(=137°) 어긋난다**
#   (구동 노드는 절댓값 일치 :199-203). 원인 후보 (a) 판다 read 오염 / (b) 기동 후 기준 재설정 미판정(:207-215).
#   정본 config 도 경고 상태: src/Actuators/motor_control/config/tongyi_amr.yaml:32
#     `steer_home_counts: [7871815, 7840086]  # ⚠ debt-007 판정 전까지 무비판 신뢰 금지`
#   ⇒ 본 파일의 home_hold / home_move 구분과 그에 근거한 "정상" 판정은 모두 **잠정**이다.
#     기준이 (b) 로 판명되면 판정이 뒤집힌다.
#   판정에 필요한 측정(§B-1): intercept off 상태에서 판다 0x6064 다중 read + 동시각 Seer 1040 encoder 대조.
# ⚠ 정정 (2026-07-27) — 위 "137° 어긋남"의 **원인 후보 (c)** 를 추가한다(§B-1 자체는 계속 열려 있음):
#   조향축에는 리밋 스위치가 실재하고 호밍 방식은 **Home 1(음의 리밋 트리거)** 이다
#   (전 노드 `0x6098 = 1` 실기 판독; Handbook V7.0 §4.6 page 115-116 기본 RstMode = 1).
#   호밍은 리밋(원점)에서 끝나는 것이 아니라 **원점 경유 후 조향 0° 로 복귀**하는 과정이므로,
#   드라이브 카운터 원점(리밋)과 조향 0° 사이에는 **설계상 137° 오프셋이 상존**한다.
#   ⇒ 7.87M counts(=137°) 차이는 "read 오염" 이나 "이상 스윙" 이 아니라 이 오프셋일 수 있다.
#   실측(Log/homing_capture_220350.jsonl):
#     · 호밍 진행 구간(t=17.93~49.0)에는 조향 `0x6064` 가 두 노드 모두 **정확히 0** 으로 보고된다
#       → 이 구간에 뜬 read 는 "위치 ≈ 0" 으로 오독된다(§B-1 측정 시 read 시각 확인 필요).
#     · 호밍 완료 후 Seer 가 조향 0° 로 지령·정착시킨 값 = **node3 7,882,020 / node4 7,859,062**
#       (t=49.14 이후 t=180 까지 고정, 각 6,319 프레임). 57344 counts/° 기준 +137.45°/+137.05°,
#       EasyDRIVE steerOffset 138.000/137.250 과 대응.
#   ⇒ 위 STEER_HOME 상수(7,871,815 / 7,840,086)는 같은 캡처의 **호밍 이전** 지령값이며,
#     호밍 후 정착값과 +10,205 / +18,976 counts(+0.178° / +0.331°) 어긋난다.
#     HOME_TOL(±20,000)이 이 차이를 덮으므로 현재 분류 거동은 바뀌지 않는다 — 값 변경 금지 유지.
HOME_TOL = 20000          # STEER_HOME ±허용(counts) — 이 안이면 홈복귀로 간주(≈0.35°)
LOGDIR = os.path.expanduser("~/docking_reliability")
LOGPATH = os.path.join(LOGDIR, "amap2_monitor.log")

DL_CMDS = {0x2F: 1, 0x2B: 2, 0x27: 3, 0x23: 4, 0x22: 4}  # expedited download 명령→바이트수


def log(msg):
    os.makedirs(LOGDIR, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOGPATH, "a") as f:
        f.write(line + "\n")


def decode_seer_write(addr, data):
    """Seer→모터 SDO write 프레임 분류. dict 반환 or None(비-write)."""
    if not (0x601 <= addr <= 0x604) or len(data) < 4:
        return None
    node = addr - 0x600
    cmd = data[0]
    if cmd == 0x40:            # upload request = 읽기 폴링(정상), 모션 아님
        return None
    if cmd not in DL_CMDS:
        return None
    index = data[1] | (data[2] << 8)
    sub = data[3]
    raw = bytes(data[4:8]) + b"\x00" * (8 - len(data))
    val = struct.unpack("<i", raw[:4])[0]
    uval = struct.unpack("<I", raw[:4])[0]

    # category: home_hold(정상 위치유지) / home_move(비home 위치이동) /
    #           homing(진짜 호밍 진입=이상후보) / motion(구동) / other
    kind, cat = None, None
    if index == 0x607A:                       # Target_position
        if node in STEER_HOME and abs(val - STEER_HOME[node]) <= HOME_TOL:
            kind, cat = "home위치유지 target_position", "home_hold"
        else:
            kind, cat = "위치이동 target_position=%d" % val, "home_move"
    # ⚠ 정정 (2026-07-27): 아래 0x6060==6 분기는 **사문(死文)** 이다 — 이 드라이브의 0x6060 유효값은
    #   1/3/4/7/8/9/10 이고 6 은 미지원 [Handbook V7.0 §6.6.3 page 152]. 실측 0건.
    #   실차 호밍 트리거인 `0x60FB.4=1`(RstStart) 분기는 **없어서 'other' 로 떨어진다**
    #   [Handbook V7.0 §6.9 page 171 / Log/homing_capture_220350.jsonl t=17.9252·17.9257].
    #   분기 추가·삭제는 거동 변경 → 별도 승인 필요. (docstring 정정 블록 ①③ 참조)
    elif index == 0x6060 and val == 6:        # Modes=homing
        kind, cat = "HOMING모드 진입(0x6060=6)", "homing"
    elif index in (0x6098, 0x6099):           # homing method/speed
        kind, cat = "HOMING설정(0x%X)" % index, "homing"
    elif index == 0x6040:                     # controlword
        # ⚠ 정정 (2026-07-27): 호밍 활성 비트는 bit4 가 아니라 **bit15(Reset Home)**
        #   [Handbook V7.0 §6.6.1 page 149-150]. bit4 는 PP 의 New set-point(정상) → 아래는 오탐 규칙.
        if (uval & 0x10) and (uval not in (0x3F, 0x86, 0x0F, 0x06, 0x07, 0x0)):
            kind, cat = "HOMING시작 controlword=0x%X" % uval, "homing"
        else:
            kind, cat = "controlword=0x%X" % uval, "other"
    elif index == 0x60FF:                     # Target_velocity
        if val != 0:
            kind, cat = "구동 target_velocity=%d" % val, "motion"
    if kind is None:
        return None
    return {"node": node, "index": index, "sub": sub, "val": val,
            "kind": kind, "cat": cat}


class Mon:
    def __init__(self):
        self.p = Panda()
        self.running = True
        self.hb_on = False
        self.stats = {"frames": 0, "seer_poll": 0, "motor_resp": 0, "guard": 0,
                      "home_hold": 0, "home_move": 0, "homing": 0, "motion": 0,
                      "leak": 0}    # leak: PC주도(gatecheck) 중 Seer write가 모터측(bus2)에 도달
        self.home_vals = {3: set(), 4: set()}   # steer target 값 추적(변동 감지)
        self.anom_log = []
        self.hb = threading.Thread(target=self._heartbeat, daemon=True)
        self.hb.start()

    def _heartbeat(self):
        while self.running:
            if self.hb_on:
                try:
                    self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")
                except Exception:
                    pass
            time.sleep(0.4)  # (게이트/gatecheck 경로는 hb_on=False로 이 스레드 미전송 — phase_gate 정정 주석 참조.
                             #  "debt-003" 은 원 프로젝트 번호이며 본 저장소 registry.md:9 와 다른 항목이다.)

    def _enable_can(self):
        for b in (SEER_BUS, MOTOR_BUS):
            self.p.set_can_speed_kbps(b, 250)
            self.p.set_can_enable(b, True)

    # ── 위상 A: passthrough 리슨(무개입) ──
    def phase_monitor(self, secs):
        self.p.set_safety_mode(0, 0)          # SILENT = 리슨온리(송신·ACK 없음)
        self._enable_can()
        time.sleep(0.2); self.p.can_recv()    # flush
        log("[A monitor] passthrough 리슨 %ds 시작 (무개입, 판다 송신 없음)" % secs)
        self._sniff(secs, "A")

    # ── 위상 B: intercept 투명중계(attended) ──
    def phase_gate(self, secs):
        self.p.set_safety_mode(SEER_GATE, 0)
        self._enable_can()
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer(투명)
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept 삽입
        # debt-003(⚠ 아래 번호 경고 참조): heartbeat(0xf3) 미전송. set_safety_mode(disable_checks=True)가
        # 이미 fail-safe를 껐고(0xf8→heartbeat_disabled=true), 0xf3를 보내면 이를 되살려
        # (heartbeat_disabled=false) USB 경합으로 못 대면 fail-safe→릴레이 OFF(passthrough)→
        # 게이트 물리 우회 누출. (docking_drive는 PC사망 안전상 heartbeat 유지, 별도 신뢰성 필요)
        #
        # ⚠ [정정 2026-07-27] 원 주석의 "실차 검증: 0xf3 미전송 시 정상상태 누출 0." 은
        #   실행일·로그경로·측정치가 하나도 인용돼 있지 않고, 관측 범위도 생략돼 있었다.
        #   출처로 보이는 orin_gate_nohb.py 의 실제 관측 조건:
        #     · 기본 관측창 8초, 1회 실행 (orin_gate_nohb.py:23 `secs = ... else 8`)
        #     · 전환 직후 **2초 정착 구간을 의도적으로 제외**하고 별도 카운트
        #       (:31-40 "전환 글리치/버스트 제외: 2초 정착 후 flush 하고 정상상태만 측정",
        #        정착 구간 누출은 `settle_leak` 로 따로 출력 :40)
        #     · 그 1회 결과로 "✅ 게이트 유지(누출 0) — 0xf3 미전송이 정답"(:77-78) 을 단정
        #   ⇒ 정확한 서술: "실차 관측(orin_gate_nohb.py, 8s × 1회, 전환 후 2s 정착 구간 제외):
        #      **정상상태** bus2 누출 0. 전환 구간 누출은 별도 계측 대상이며 0 이 확인된 바 없다."
        #      실행일·로그 경로는 미기록 — 재실행 시 여기에 기재할 것.
        #
        # ⚠ [정정 2026-07-27] 위 "debt-003" 은 **원 프로젝트(CAN-Relay) 번호**다. 본 저장소의 부채 정본
        #   docs/debt/registry.md:9 에서 debt-003 은
        #   "src/Actuators/motor_control/motor_control/backend.py:272-300 freewheel servo-off …
        #    Node Guarding RTR" 로, 판다 heartbeat/fail-safe 와 **무관한 항목**이다.
        #   (같은 충돌이 debt-002 인용에도 있다: registry.md:8 debt-002 = IMU base_link→imu_link
        #    static TF 마운트값인데, orin_debt002_char.py:1 · orin_hold_intercept.py:2 ·
        #    orin_termcheck.py:2 는 이를 다른 뜻으로 인용한다.)
        #   이식 과정에서 두 번호체계가 충돌한 것으로 보이나 **확인되지 않았다** → 인용은 지우지 않고
        #   병기만 한다. 조치: 내용을 registry.md 에 새 id 로 append 한 뒤 이 마커를 그 id 로 갱신할 것.
        self.hb_on = False
        time.sleep(0.2); self.p.can_recv()
        log("[B gate] intercept 투명중계 %ds 시작 (판다 삽입, auth=Seer). 지켜보는 중이어야 함." % secs)
        self._sniff(secs, "B")
        self._release_gate()

    def _release_gate(self):
        try:
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # passthrough
            self.p.set_safety_mode(0, 0)
        except Exception:
            pass
        self.hb_on = False
        log("[B gate] passthrough 복귀(판다 리슨/무개입).")

    def _sniff(self, secs, tag, pc_auth=False):
        """pc_auth=True(gatecheck): PC 주도이므로 Seer write가 모터측(bus2)에 도달하면 게이트 누출(이상)."""
        t0 = time.time()
        last = t0
        while time.time() - t0 < secs and self.running:
            for (addr, _, dat, bus) in self.p.can_recv():
                self.stats["frames"] += 1
                if 0x601 <= addr <= 0x604:
                    self.stats["seer_poll"] += 1
                elif 0x581 <= addr <= 0x584:
                    self.stats["motor_resp"] += 1
                elif 0x701 <= addr <= 0x704:
                    self.stats["guard"] += 1
                w = decode_seer_write(addr, dat)
                if not w:
                    continue
                cat = w["cat"]
                # gatecheck: PC주도 중 Seer write가 모터측 버스에 나타나면 = 게이트 누출(치명)
                if pc_auth and bus == MOTOR_BUS:
                    self.stats["leak"] += 1
                    rec = "[%s] ⚠게이트누출 Seer write가 모터측 도달 node%d %s" % (tag, w["node"], w["kind"])
                    self.anom_log.append(rec); log(rec)
                    continue
                if bus != SEER_BUS:
                    continue                 # 중복 집계 방지(Seer측만 계수)
                if cat == "home_hold":
                    self.stats["home_hold"] += 1
                    self.home_vals[w["node"]].add(w["val"] // 1000)   # 변동추적(1000단위)
                elif cat == "home_move":
                    self.stats["home_move"] += 1
                    self.home_vals[w["node"]].add(w["val"] // 1000)
                elif cat == "homing":
                    self.stats["homing"] += 1
                    rec = "[%s] ⚠HOMING신호 node%d %s (0x%04X=%d)" % (
                        tag, w["node"], w["kind"], w["index"], w["val"])
                    self.anom_log.append(rec); log(rec)
                elif cat == "motion":
                    self.stats["motion"] += 1
            now = time.time()
            if now - last >= 10:
                last = now
                s = self.stats
                log("[%s] 진행 frames=%d 폴링=%d 응답=%d guard=%d home유지=%d home이동=%d 모션=%d homing=%d 누출=%d"
                    % (tag, s["frames"], s["seer_poll"], s["motor_resp"], s["guard"],
                       s["home_hold"], s["home_move"], s["motion"], s["homing"], s["leak"]))
            time.sleep(0.005)

    def summary(self, pc_auth=False):
        s = self.stats
        ok_poll = s["seer_poll"] > 0
        ok_resp = s["motor_resp"] > 0
        no_homing = s["homing"] == 0          # 진짜 호밍진입 이벤트 없음
        no_leak = s["leak"] == 0
        # steer target 값이 home 부근에서 몇 종류로 유지되는지(변동=이동, 1~2종류=유지)
        spread = {n: len(v) for n, v in self.home_vals.items()}
        steady = all(c <= 3 for c in spread.values())   # 값 종류 적음 = position-hold
        log("── 요약 ──")
        log("총frames=%d · Seer폴링=%d(%s) · 모터응답=%d(%s) · guard=%d"
            % (s["frames"], s["seer_poll"], "정상" if ok_poll else "없음!",
               s["motor_resp"], "정상" if ok_resp else "없음!", s["guard"]))
        log("steer 지령: home위치유지=%d · 비home이동=%d · 구동=%d · HOMING진입=%d · 값종류=%s(%s)"
            % (s["home_hold"], s["home_move"], s["motion"], s["homing"], spread,
               "유지=정차" if steady else "변동=이동중"))
        if s["home_hold"] and steady and s["home_move"] == 0 and no_homing:
            log("ℹ Seer가 steer를 home위치로 지속 지령 = 정차 position-hold(정상). 호밍재진입·비home이동 없음.")
            log("  (근거: HANDOFF-amap2.md:28-31 실측 — 정차 중 0x607A=home 지속 전송은 정상 서보 동작.)")
        if no_homing:
            # ⚠ 조건 명시(정정 2026-07-27): home_hold/home_move 구분은 STEER_HOME 상수에 의존하는데,
            #   그 상수가 docs/verified_facts/2026-07-27.md §B-1 에서 미판정 모순으로 분류돼 있다.
            log("✅ 작동이상 HOMING(재호밍) 신호 없음 "
                "(단, 홈 기준 상수 STEER_HOME 이 미판정이므로 home_hold/home_move 구분은 잠정 — "
                "docs/verified_facts/2026-07-27.md §B-1).")
        else:
            log("⚠ HOMING 재진입 신호 %d건 — 작동이상 후보:" % s["homing"])
            for r in self.anom_log:
                log("   " + r)
        if pc_auth:
            if no_leak:
                log("✅ 게이트 차단 정상 — PC주도 중 Seer의 home/write가 모터측에 누출되지 않음(도킹 안전).")
            else:
                log("⚠ 게이트 누출 %d건 — PC주도 중 Seer write가 모터에 도달(도킹 시 충돌위험):" % s["leak"])
                for r in self.anom_log:
                    log("   " + r)
        verdict = ok_poll and ok_resp and no_homing and no_leak
        log("판정: %s" % ("정상" if verdict else "점검필요(위 ⚠ 확인)"))
        return verdict

    # ── gatecheck: PC 주도(auth=PC)로 두고 Seer home/write가 모터측에서 차단되는지 검증 ──
    def phase_gatecheck(self, secs):
        self.p.set_safety_mode(SEER_GATE, 0)
        self._enable_can()
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC(게이트 차단)
        self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept
        # 0xf3 미전송 유지 → fail-safe 비활성 유지 → 게이트 hold.
        # ⚠ "debt-003" 번호 충돌 및 "실차 누출0 검증" 의 관측 범위(8s×1회·정착 2s 제외)는
        #   phase_gate 의 정정 주석 참조.
        self.hb_on = False
        time.sleep(0.2); self.p.can_recv()
        log("[C gatecheck] auth=PC 게이트 %ds — Seer home/write의 모터측 누출 감시 (PC 구동은 안 함, 차단만 검증)." % secs)
        self._sniff(secs, "C", pc_auth=True)
        self._release_gate()

    def close(self):
        self.running = False
        time.sleep(0.1)
        try:
            self.p.close()
        except Exception:
            pass


def main():
    argv = sys.argv[1:]
    mode = argv[0] if argv else "monitor"
    m = Mon()
    pc_auth = False
    try:
        if mode == "monitor":
            secs = int(argv[1]) if len(argv) > 1 else 30
            m.phase_monitor(secs)
        elif mode == "gate":
            secs = int(argv[1]) if len(argv) > 1 else 30
            m.phase_gate(secs)
        elif mode == "gatecheck":
            secs = int(argv[1]) if len(argv) > 1 else 30
            m.phase_gatecheck(secs); pc_auth = True
        elif mode == "seq":
            a = int(argv[1]) if len(argv) > 1 else 30
            b = int(argv[2]) if len(argv) > 2 else 30
            m.phase_monitor(a)
            m.phase_gate(b)
        else:
            print(__doc__); return
        ok = m.summary(pc_auth=pc_auth)
        sys.exit(0 if ok else 2)
    finally:
        m.close()


if __name__ == "__main__":
    main()
