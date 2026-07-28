# motor_control — Tongyi AMR CAN 구동 ROS2 패키지

Seer 마스터를 대신해 CAN(SDO 폴링)으로 Tongyi 4축 서보(구동 N1·2 / 조향 N3·4)를 직접 구동한다.
설계 근거: [docs/ros2_driver/2026-07-09-design-inputs.md](../../../docs/ros2_driver/2026-07-09-design-inputs.md) ·
ADR: [docs/adr/2026-07-09-motor-control-ros2-package.md](../../../docs/adr/2026-07-09-motor-control-ros2-package.md)

## 구조 (모듈 세트 추상화)

```
Twist ─▶ kinematics (DualSteer | DiffDrive) ─▶ ModuleCommand[{v m/s, θ rad|None}]
      ─▶ backend TongyiSdoBackend ─▶ CAN SDO (0x60FF / 0x607A+0x3F / guard RTR)
```

- `protocol.py` — SDO 프레임 인코드/디코드 (기동 캡처 실측 바이트로 단위검증)
- `kinematics.py` — 모듈 세트 추상화. `DualSteerKinematics`(연속 스워브, 오라클 대조 완일치 수식 이식) + `DiffDriveKinematics`(θ=None — **DD 타입 커버**)
  - ⚠ **정정 2026-07-27 — "연속 스워브"는 구현 완료 기능이 아니라 Phase 2 미검증 항목이다.**
    이 하드웨어에서 중간 조향각(홈/90° 외)은 **미관측**이다
    (⚠ 좌표 정정 2026-07-27b — 아래 세 인용의 원 표기는 `design-inputs:45` · `:84` · `:95` 였으나 그 줄들에는 해당 문구가 없다.
     그 문서는 스스로 "인용은 가급적 줄번호 대신 **절 번호 + 원문 문구**로 할 것"이라 지시하므로 절 앵커로 바꾼다):
    [design-inputs.md](../../../docs/ros2_driver/2026-07-09-design-inputs.md) **§4 마지막 불릿**(현재 :88) "Seer 는 홈/90° **2상태만** 사용 — 중간 조향각 연속 스워브는 미관측(⚠ §7)",
    동 문서 **§7 표 행**(현재 :217) "중간 조향각(0~90° 외) 지령 가능성 | Phase 2 연속 스워브 전제 | **잭업(바퀴 공중) 상태에서 소각도 시험**",
    동 문서 **§8 항목 4**(현재 :228) "Phase 2: 중간 조향각 검증 후 연속 스워브 IK + odom 정밀화".
    → **잭업 소각도 시험 전 지면에서 중간 조향각 사용 금지**(안전 절차 6 참조).
  - ⚠ **정정 2026-07-27 — "오라클 대조 완일치"는 근거 문서가 이 저장소에 없다(미판정).**
    상위 ADR [2026-07-09-motor-control-ros2-package.md](../../../docs/adr/2026-07-09-motor-control-ros2-package.md) **§배경 「검증 자산 재사용」 › `kin_inverse` 항목**(현재 :28)이 오라클 `libOdoCalculator.so` 완전 일치를 주장하며
    (⚠ 좌표 정정 2026-07-27b — 원 표기는 `…md:10` 이었으나 그 줄은 design-inputs `:84` 인용 줄이고 오라클 주장이 없다. 같은 ADR :29-35 가 이미 「근거 미도달」로 같은 판정을 적어 두었다)
    `docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md` 를 인용하나 **그 파일은 `docs/adr/` 에 존재하지 않는다**(2026-07-27 `ls` 확인 — 근거 ADR 미이관).
    또 완일치 주장의 범위는 **역기구학 한정**이며, 정기구학(오도메트리) 쪽은 대조 벡터가 없다:
    [docs/code_review/motor_control/2026-07-26.md:300](docs/code_review/motor_control/2026-07-26.md) "정기구학 LSQ(#7)의 오라클 대조 벡터 회귀 테스트는 in-tree 미확인".
- `backend.py` — SDO 단독 마스터: 브링업 게이트 → Seer init 재현 → 50Hz 지령 + 20Hz guard RTR + 피드백 폴링
  - ⚠ **정정 2026-07-27 — "Seer init 재현" 은 재현이 아니다.** 실측(`Log/homing_capture_220350.jsonl`)에서
    Seer 는 조향축 init 을 **2국면**으로 나눠 쓰고 그 사이 **31.08 s 동안 write 를 전면 정지**한다:
    국면 A(호밍 트리거) `0x6040=0x86` → `0x6099=2500` → `0x60FB.4=1`(t=17.910~17.926)
    → [정지 ≈31.1 s: `0x6041` bit15=0, `0x6064`=0, t=47.025 −리밋 물림, t=48.999/49.080 bit15 0→1]
    → 국면 B(완료 후) `0x6040=0x86` → `0x100D=1` → `0x100C=500` → `0x6060=1`(PP) → `0x6081=30000`
    → `0x6083=250` → `0x6084=250` → `0x607A`=조향0°(t=49.140).
    본 구현은 A·B 를 2 ms 간격 한 버스트로 붙여 보낸다 — 완료 대기(`0x6041` bit15 0→1) 미구현
    (`motor_control/backend.py` › `TongyiSdoBackend._write_init_sequence()`).
    ⇒ 이 함수를 'Seer 실측 재현' 으로 인용하지 말 것.
    - ⚠ **좌표·사실 재확인 2026-07-27b** — 원 표기는 `motor_control/backend.py:330-351` 이었다.
      **`backend.py` 는 현재 동시 편집 중이라 줄번호가 계속 밀린다**(같은 세션 내 2회 측정에서 494줄 → 549줄).
      따라서 줄번호 대신 **함수명 + 원문 문구**로 인용한다.
      또한 그 함수 **본문이 그 사이 바뀌었다**: 호밍 트리거 `0x60FB.4=1` 은 브링업에서 **제거**돼 주석으로만 남아 있다
      (`_write_init_sequence()` 안의 "── 호밍 트리거는 **브링업에서 보내지 않는다** (2026-07-27 제거) ──" /
      "종전: P.sdo_write(n, P.OBJ_VENDOR_60FB, 1, size=1, sub=0x04)").
      따라서 「국면 A(호밍 트리거)를 그대로 보낸다」는 서술은 **현행 코드에 대해서는 성립하지 않는다**
      (완료 대기 미구현이라는 지적 자체는 유효). 원 서술은 이력 보존을 위해 남긴다.
- `driver_node.py` — `/cmd_vel`·`/estop`·`/freewheel` 구독, `/odom`(+TF)·`/joint_states`·`/diagnostics` 발행
  - ⚠ **정정 2026-07-27 — 기존 서술에 `/freewheel` 구독이 누락돼 있었다.** 현행 코드는 3개를 구독한다:
    `motor_control/driver_node.py` › `MotorControlNode.__init__` 의 `create_subscription(...)` 3줄
    (`"cmd_vel"` · `"estop"` · `"freewheel"`).
    (⚠ 좌표 정정 2026-07-27b — 원 표기 `:89`·`:90`·`:91` 은 `declare_parameters` 블록 주석 줄이다.
     `driver_node.py` 도 동시 편집으로 줄번호가 밀리므로(296줄 → 364줄, 같은 세션 2회 측정) 줄번호를 쓰지 않는다.)
    `/freewheel` 은 **구동축 servo-off(홀딩토크 상실)** 를 일으키는 안전 민감 토픽이다 —
    `motor_control/backend.py` › `TongyiSdoBackend.freewheel()` docstring
    "⚠ 홀딩토크 상실 — 경사면에서 굴러갈 수 있음(정지·평지·촉 확보 후 사용)". 안전 절차 7 참조.
    (⚠ 좌표 정정 2026-07-27b — 원 표기 `backend.py:163` 에는 그 문구가 없다.)

## 빌드·테스트

```bash
cd <workspace> && colcon build --packages-select motor_control
pytest src/Actuators/motor_control/test -q   # 버스 불요 (FakeBus)
# ⚠ 정정 2026-07-27: 구 경로 `src/Motor_Control/test` 는 현재 저장소에 존재하지 않는다
#   (`ls src/` = Actuators AI Comm Control Safety Sensors).
#   ⚠ 좌표 정정 2026-07-27b: 원 표기는 위 목록 끝에 `Tools` 를 포함했으나 `Tools/` 는 `src/` 아래가 아니라
#   **저장소 루트**에 있다(2026-07-27 `ls src/` 재실행 — 6개 항목뿐). 결론(구 경로 부재)은 그대로다.
#   실제 테스트 위치: src/Actuators/motor_control/test/{test_backend,test_kinematics,test_protocol}.py
```

## 실행

```bash
# CAN 브링업 (relay 킷 스크립트 재사용)
sudo ip link set can1 up type can bitrate 250000
ros2 launch motor_control motor_control.launch.py
ros2 topic pub -r 10 /cmd_vel geometry_msgs/Twist '{linear: {x: 0.05}}'
ros2 topic pub -1 /estop std_msgs/Bool '{data: true}'   # E-STOP
```

## ⚠ 안전 절차 (첫 실차 — 반드시 순서대로)

1. **전제**: Seer 마스터 분리(단독 마스터), 안전구역 + 하드 E-stop 상비.
2. **콜드 부팅 주의**: 전원 투입 직후 조향 위치≈0 → 브링업 시 **조향 137° 물리 스윙** 발생.
   기본값 `allow_homing_motion: false` 는 이때 기동을 거부한다. 주변 확보 확인 후
   `allow_homing_motion:=true` 로 재시작(가능하면 잭업 상태에서).
   - ⛔ **조건 추가 2026-07-27 — 위 "재시작" 절차는 현재 금지 상태다(무조건 절차가 아니다).**
     `steer_home_counts` 에 **미판정 모순**이 있어, 정본 config 가 이 게이트 해제를 명시적으로 금지한다:
     [config/tongyi_amr.yaml](config/tongyi_amr.yaml) `steer_home_counts` 위 **「사용 규칙(판정 전까지)」 주석**
     "사용 규칙(판정 전까지): allow_homing_motion 게이트(홈 5° 이탈 시 브링업 거부)를 **끄지 말 것**.
     그 게이트가 이 불일치를 잡아내는 방어선이다. 끄고 진행하면 137° 지령이 나갈 수 있다."
     모순 내용은 같은 파일 **「⚠ 미해소 모순 (2026-07-27 관측, debt-007) — 아래 값을 쓰기 전에 반드시 읽을 것.」 블록**
     (2026-07-27 관측: Seer 호밍 완료·바퀴 직진 상태인데 판다 read 0x6064≈0, 설계상 ≈7.87M 이어야 함).
     - ⚠ **좌표 정정 2026-07-27b** — 위 두 인용의 원 표기는 `config/tongyi_amr.yaml:30-31` · `:20-29` 였고
       그 줄들에는 인용 문구가 **없다**(당시 대조에서는 `vmax`/`wmax` 와 「단독 마스터 전제」 주석이었다).
       이 yaml **역시 동시 편집으로 줄번호가 계속 밀리므로**(같은 세션 안에서 160줄 → **295줄**) 줄번호를 쓰지 않고
       **주석 제목 문구**로 인용한다.
     - ⚠ **인용된 「방어선」 서술은 같은 파일이 스스로 철회했다**(원 인용은 이력 보존을 위해 남긴다):
       `config/tongyi_amr.yaml` 의 **「[정정 5] 사용 규칙 정정」** 항목 — "allow_homing_motion 게이트는 이 불일치의 '방어선' 이 아니다 …
       게이트는 계속 false 로 두되(존폐는 이번 범위 밖), 안전 근거로 인용하지 말 것."
       ⇒ **"끄지 말 것" 이라는 지시는 유지**하되, 그 근거를 「이 게이트가 137° 스윙을 막는다」로 읽지 말 것.
     실제로 137° 범위이탈이 node4 물리 갇힘을 일으킨 사고가 있었다:
     [docs/claude-mistake/2026-07-27-002 §무엇을 했는가](../../../docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md)(현재 **:19-20**) "node4가 **물리적으로 137°(정상 ±90° 범위 밖)로 밀려 갇혔고**".
     (⚠ 좌표 정정 2026-07-27b — 원 표기 `:17-18` 은 「## 무엇을 했는가」 제목과 그 앞 빈 줄이다.)
     → **판정 전까지 `allow_homing_motion` 을 true 로 두지 말 것.**
     판정에 필요한 측정: Seer 호밍 완료 직후 조향 `0x6064` 를 (a) 판다 경유 read (b) CAN 직결 read 두 경로로 동시 취득해 ≈0 / ≈7.87M 중 어느 쪽인지 대조.
   - ⚠ **정정 2026-07-27 (실기 캡처 `Log/homing_capture_220350.jsonl`, 판다 수동청취 180 s / 253,510 프레임).
     위 항목 2 의 전제 3 개가 실측으로 반증됐다. 원문은 이력 보존용으로 남긴다.**
     1. ❌ "전원 투입 직후 조향 위치≈0" → 캡처 시작(t=0~5.16 s)의 조향 `0x6064` 는
        **N3 7,871,818 / N4 7,840,084**(≈137°)로 이미 홈 부근이다. `0x6064` 가 0 이 되는 것은
        브링업이 `0x60FB.4=1`(RstStart)을 쓴 **뒤**의 호밍 진행 구간뿐이다
        (t=18.15~49.07, 약 31 s 동안 정확히 0). ⇒ `0x6064≈0` 은 콜드 부팅의 표지가 아니다.
     2. ❌ "`allow_homing_motion: false` 는 이때 기동을 거부한다"를 **안전근거로 쓸 수 없다.**
        이 게이트는 `0x6064` 가 `steer_home` 에서 `homing_tol` 이상 이탈했는지만 본다
        (`motor_control/backend.py` › `TongyiSdoBackend._gate_homing_motion()` — `cold = {n: d for n, d in deltas.items() if d > self.homing_tol_counts}`). 게이트를 통과하는 웜 상태에서도 브링업은
        `0x60FB.4=1` 을 **조건 없이** 송신하므로(`motor_control/backend.py:368`,
        같은 파일 `:294-296`) −리밋 탐색 ≈31 s + 조향 0° 복귀 ≈3 s 의 물리 스윙이 **매 기동 발생**한다.
        ⇒ 스윙은 콜드/웜 조건부가 아니다.
        - ⚠ **좌표·사실 정정 2026-07-27b (원 서술은 위에 그대로 보존)** — 세 인용을 직접 대조한 결과:
          · `backend.py:283-304` → 함수 시작은 맞았으나 끝 좌표는 `cold = {...}` 줄이었다. **`backend.py` 는 동시 편집으로
            줄번호가 계속 밀리므로**(같은 세션 2회 측정 494줄 → 549줄) 함수명 + 원문 문구 앵커로 바꿔 인용한다.
          · `backend.py:368` → **인용 문구가 없다.** 실제 `0x60FB.4=1` 쓰기는 **2026-07-27 에 제거**돼 지금은 주석으로만 남아 있다
            (`_write_init_sequence()` 안 "── 호밍 트리거는 **브링업에서 보내지 않는다** (2026-07-27 제거) ──" /
            "종전: P.sdo_write(n, P.OBJ_VENDOR_60FB, 1, size=1, sub=0x04)").
          · `backend.py:294-296` → 인용 문구 자체는 **실재한다**(`_gate_homing_motion()` docstring
            "이 게이트는 **물리 스윙을 막지 못한다.** 통과 후 `_write_init_sequence` 가 `0x60FB.4=1`(RstStart)을 조건 없이 송신하므로 …").
            다만 그 docstring 은 트리거 제거 **이전** 서술이라 현행 본문과 어긋난다 — 같은 파일이 이미
            "…는 현행 코드에 대해 **거짓**이다. 해당 write 는 `# 종전: P.sdo_write(n, P.OBJ_VENDOR_60FB, …)` 로 주석 처리돼 있고"
            라고 자체 정정을 덧붙여 두었다.
          ⇒ **「물리 스윙이 매 기동 발생한다」는 현행 코드에 대해 단정할 수 없다** — 브링업 경로에 트리거 쓰기가 없기 때문이다.
            반대로 「스윙이 절대 없다」고도 단정하지 않는다(`_write_init_sequence()` 주석이 "호밍이 필요하면 **명시적으로** 요청한다 —
            GUI '호밍' 버튼 → 판다 펌웨어 시퀀서" 라는 별도 경로를 남긴다).
            판정에 필요한 측정: 실차 브링업 1회를 CAN 캡처해 조향 노드로 나가는 `0x60FB` sub4 write 유무와 조향 실이동을 기록.
            그 전까지 **안전 절차의 물리 클리어·잭업·E-stop 요구는 그대로 유지**한다(스윙 가능성을 배제하지 않는다).
     3. ❌ 위 "판정에 필요한 측정"(판다 경유 vs CAN 직결 read 대조)은 이미 반증된 가설을 겨냥한다.
        debt-007 의 (a) 판다 read 오염 · (b) 호밍 후 위치기준 재설정 은 같은 캡처로 반증됐고,
        실제 원인은 **(c) read 시각이 호밍 진행 구간이었다** 이다(같은 read 가 호밍 밖에서는 홈 값을 정확히 반환).
        필요한 측정은 두 경로 대조가 아니라 **`0x6041` bit15(호밍 완료)와 read 시각의 정렬**이며,
        그 측정은 위 캡처로 이미 수행됐다.
     - ✅ 아울러 **137° 스윙 자체는 이상거동이 아니다** — 호밍 완료 후 −리밋 원점에서 조향 0° 로
       복귀하는 설계된 이동이다. 목표는 절대 **7,882,020(N3) / 7,859,062(N4) counts**
       (= +137.45° / +137.05°, 57344 counts/°; EasyDRIVE steerOffset 138.000 / 137.250 대응).
       조향축 리밋 스위치는 실재하며 방식은 **Home 1(음의 리밋 트리거)** — 전 노드 `0x6098 = 1`
       실기 판독 확정, Handbook 기본 RstMode 도 1 [Handbook V7.0 §4.6 page 116 · §6.9 page 171].
       (⚠ `0x6098` 을 임의로 바꾸면 — 예: Home 35 — RstMode 가 0 으로 리셋돼 호밍이 죽는다 [§4.6 page 122].)
       위 5-6 줄의 "137° 범위이탈 사고"는 **호밍이 아니라 미검증 수동 지령**으로 발생한 별건이다.
     - ⚠ 구동축(N1·N2)은 호밍하지 않는다 — Seer 는 조향 노드에만 호밍 프레임을 보냈다(기계적 원점 없음).
     - ⇒ **실효 안전조치**(게이트가 아니라 이것에 의존할 것): (1) 조향 가동범위 물리 클리어
       (2) 가능하면 잭업 (3) 하드 E-stop 상비 (4) 브링업 후 ≈34 s 간 조향축 접근 금지.
       `allow_homing_motion` 게이트의 존폐는 별건이며 이 문서 갱신으로 동작을 바꾸지 않았다.
3. **미검증 부호 가정 2건** (`kin_steer_sign`, `module_x` 의 node1=Rear 매핑 — ADR §가정):
   저속(≤0.05 m/s) 크랩·스핀 1회로 방향 확인 → 반대면 파라미터 반전.
   - ⚠ **정정 2026-07-27 — `module_x` 의 node1=Rear 는 "미검증"이 아니라 실측 데이터에 의해 반증 지적된 상태다(config 미수정).**
     [docs/code_review/motor_control-can-consistency/2026-07-26.md](docs/code_review/motor_control-can-consistency/2026-07-26.md) **§3 「🔴 HIGH — 모듈 전/후(module_x) 노드 배정 반전」**(현재 :54-63) 이 지적:
     "실측: node1=FrontWalk x=**+0.604**, node2=RearWalk x=−0.596 … 코드 주석이 `⚠ node1=Rear 가정 (미검증)`으로 명시 → **저장 데이터가 이 가정을 반증(node1=Front).**"
     (⚠ 좌표 정정 2026-07-27b — 원 표기 `:45-52` 는 그 문서의 「각주1」 블록이며 위 문구가 없다.)
     1차 근거: `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md` **§1 노드 매핑 표**(현재 :39-46, node1 행은 :42 `| 1 | FrontWalk | 전 구동(속도) | +0.604 | 32 | 16384 |`).
     - ⚠ **좌표·등급 정정 2026-07-27b** — 원 표기 `:11-12` 에는 그 표가 없다(그 줄은 2026-07-27 감사 주석이다).
       또한 「(EasyDRIVE canID config, ✓ 실측 표기)」라는 등급 서술은 **그 문서가 스스로 낮춰 놓았다**:
       같은 문서 §1 머리(:39)는 "**노드 매핑** (EasyDRIVE canID) ~~✓~~ → **✓ config 스크린샷 근거 / ⚠ 코드 정본과 미판정 모순**",
       :52 는 "즉 x 좌표는 \"canID 표\"가 아니라 **config 스크린샷**이 근거다" 라고 적는다.
       ⇒ 「1차 근거 ✓ 실측」으로 인용하지 말 것. 원 서술은 이력 보존을 위해 남긴다.
     현재 config 는 **미수정**이다([config/tongyi_amr.yaml](config/tongyi_amr.yaml) 의 `module_x: [-0.5961, 0.6039]  # ⚠ node1=Rear 가정 (부호 정합 도출 — 출처 미인용, 아래 참조)` 줄).
     (⚠ 좌표 정정 2026-07-27b — 원 표기 `:18` 에는 그 줄이 없다. yaml 이 동시 편집 중이라(160줄 → 295줄) 줄번호 대신 값 문구로 인용한다.
      인용 주석도 현행 전문으로 갱신했다 — 원 인용은 `# ⚠ node1=Rear 가정` 까지였다.)
     값 변경은 실차 방향 확인 전까지 하지 않는다 — 같은 리뷰 **§3 「권고」 항목**(현재 :63) 의 조건이 남아 있기 때문이다:
     "부호가 실배선/`drive_sign`과 상쇄되는지는 실차 저속(≤0.05 m/s) 크랩/스핀 방향 확인으로 최종 확정".
     (⚠ 좌표 정정 2026-07-27b — 원 표기 `:52` 에는 그 문구가 없다.)
   - ⚠ `kin_steer_sign` 은 여전히 **미확정**이다([docs/debt/registry.md](../../../docs/debt/registry.md) debt-004 '미해결').
     확정 전까지 `driver_node` 의 crab/스핀 twist 사용 금지(debt-004 상환계획).
4. 속도 상한 `vmax` 는 검증 전 0.2 m/s 유지 (기구 최대 1.23 m/s).
5. 조향 정착 게이트: 조향 목표↔실측 편차 > `steer_settle_tol_deg` 동안 구동 자동 0 — 정상 동작(진단 WARN).
6. **중간 조향각(연속 스워브)은 지면 사용 금지**(추가 2026-07-27). 하드웨어에서 미관측·미검증 —
   [design-inputs.md](../../../docs/ros2_driver/2026-07-09-design-inputs.md) **§4 마지막 불릿 · §7 표 「중간 조향각(0~90° 외) 지령 가능성」 행 · §8 항목 4**.
   (⚠ 좌표 정정 2026-07-27b — 원 표기 `design-inputs:45,84,95` 의 세 줄에는 해당 문구가 없다. 현재 위치는 :88 · :217 · :228 이며,
    그 문서 자신이 "인용은 가급적 줄번호 대신 **절 번호 + 원문 문구**로 할 것"이라 지시한다.)
   **잭업(바퀴 공중) 소각도 시험**을 먼저 통과시킬 것.
   참고로 `STEER_LIMIT_RAD=2.443`(±140°)은 Seer config 기구 한계값이며 물리 실증 범위가 아니다 —
   실측 검증된 범위는 **±90°** (`Tools/amr_test_gui/amr_test_gui/ramp.py` 의 `STEER_LIMIT_DEG = 90.0` 위 주석,
   현재 :26-29 "기구 한계는 ±140°(kinematics.STEER_LIMIT_RAD=2.443)이나, **실측 검증된 범위가 ±90°** … 테스트 GUI 는 ±90° 로 좁힌다").
   (⚠ 좌표 정정 2026-07-27b — 원 표기 `ramp.py:16-19` 는 모듈 docstring 안의 `pc_crab_steer.py` 미존재 주석이며 ±90° 내용이 없다.)
7. **`/freewheel` 사용 주의**(추가 2026-07-27): 구동축 servo-off → **홀딩토크 상실**.
   `motor_control/backend.py` › `TongyiSdoBackend.freewheel()` docstring
   "⚠ 홀딩토크 상실 — 경사면에서 굴러갈 수 있음(정지·평지·촉 확보 후 사용)".
   (⚠ 좌표 정정 2026-07-27b — 원 표기 `backend.py:163` 에는 그 문구가 없다. `backend.py` 는 동시 편집으로 줄번호가
    계속 밀리므로(같은 세션 3회 측정: 그 문구가 :223 → :273 으로 이동) 줄번호 대신 함수명으로 인용한다.)
   → **정지 상태·평지·촉(고임목) 확보 후에만** engage 할 것. 경사면 금지.

## DD(differential drive) 타입 적용

`kinematics: "diff_drive"` + `module_drive_nodes: [L, R]` + `track_width` 설정 — 조향 노드 없이
동일 토픽 인터페이스로 동작(ModuleCommand θ=None → backend 가 조향 지령 생략).
