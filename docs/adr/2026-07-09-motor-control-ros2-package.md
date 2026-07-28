# ADR 2026-07-09 — `src/Motor_Control/` ROS2 패키지 `motor_control` 신설

Status: Accepted (사용자 지시 sess:c64c0e35 2026-07-09: ① "CAN으로 AMR 모터 구동, ROS2 기반" ② "src/Motor_Control 에 패키지를 작성할 것임" ③ "속도·조향을 한 세트로 만들면 DD 타입도 커버")

## 배경 (Context)

- 설계 입력 SSOT: [docs/ros2_driver/2026-07-09-design-inputs.md](../ros2_driver/2026-07-09-design-inputs.md) — 버스·스케일·운동학·브링업(기동 캡처 전수 디코드 포함) 실측 ✓.
  - **[조건 누락 정정 2026-07-27]** 위 "실측 ✓" 일괄 요약은 SSOT 문서 자신이 남긴 **미확정 항목을 가린다**.
    같은 문서 §7 "미확정(⚠) — 구동 전 확인 항목"(`docs/ros2_driver/2026-07-09-design-inputs.md:77-88`) 중 특히:
    - `:84` "중간 조향각(0~90° 외) 지령 가능성 | Phase 2 연속 스워브 전제 | **잭업(바퀴 공중) 상태에서 소각도 시험**" —
      본 ADR §결정 2(아래 `DualSteerKinematics`, 연속 스워브 IK)가 바로 이 전제 위에 서 있다.
    - `:82` "브링업 137° 스윙의 물리 의미 | 0 기준점이 절대 엔코더 기준인지(어느 자세에서 꺼도 재현) 미확인 — **2회 전원 사이클 관측뿐**".
      - **[⚠ 2026-07-27 부분 해소 — 인용 이력 보존]** 위 `:82` 항목 중 **「137° 스윙의 물리 의미」는 확정됐다**:
        호밍 완료 후 **음의 리밋(원점)에서 조향 0° 로 복귀하는 설계된 이동**이며, 조향축에 **리밋 스위치가
        실재**하고 방식은 **Home 1(음의 리밋 트리거)** 이다(전 노드 `0x6098 = 1` 실기 판독;
        Handbook V7.0 §4.6 printed page 116). 복귀 목표 = node3 7,882,020 / node4 7,859,062 counts
        (= 리밋 기준 +137.45°/+137.05°, 57344 counts/°) ↔ EasyDRIVE `steerOffset` 138.000/137.250.
        근거: `Log/homing_capture_220350.jsonl`(Seer 주도 호밍 253,510 프레임) + 드라이브 파라미터 직접 판독.
        **여전히 미확정**: 「0 기준점의 전원 사이클 불변성」과 `steer_home_counts` 상수 불일치(debt-007).
    ⇒ **연속 IK 는 잭업 소각도 시험 전까지 미검증 전제 위에 있다.** 지면에서 중간 조향각 사용 금지.
- 검증 자산 재사용:
  - SDO 프레임·DirectDriver 송신 패턴 — [07_drive_gui.py](../../experiements/2026-07-08_pcan-relay-linux-handoff/_extracted/pcan_relay_test/07_drive_gui.py) (selftest ✓, 실차 재생 근거 ✓)
    - **[근거 미도달 2026-07-27]** 인용 파일이 본 저장소에 **부재**한다 — `find . -name '07_drive_gui.py'` **0건**.
      링크의 `experiements/`(오타) 는 물론 실제 `experiments/` 아래에도 없다(`ls experiments` → `capture`, `cctv_5cam_soak_20260726` 2개뿐).
      또한 SSOT 자신이 `docs/ros2_driver/2026-07-09-design-inputs.md:88` 에서 "DirectDriver 실차 미검증 | selftest(vcan)만 통과, 실차 T4 미실시"
      라고 적어 **"실차 재생 근거 ✓" 와 어긋난다**. ⇒ 위 두 ✓ 는 **미판정**으로 취급한다(원문 링크는 이력으로 보존).
      재판정 방법: 원본 스크립트와 실차 재생 캡처를 저장소에 첨부하고 프레임 단위 대조 로그를 인용할 것.
  - 연속 역기구학 `kin_inverse` — [ADR 2026-07-09-kinviz-multisteer-to-drive-gui](2026-07-09-kinviz-multisteer-to-drive-gui.md) (오라클 `libOdoCalculator.so` 대조 완전 일치 → Python 이식, 수학 selftest 5케이스 ✓)
    - **[근거 미도달 2026-07-27]** 인용된 근거가 본 저장소에 **하나도 없다** —
      `ls docs/adr/` 에 `2026-07-09-kinviz-multisteer-to-drive-gui.md` **없음**(현재 존재: 2026-07-09-motor-control-ros2-package.md,
      2026-07-20-…, 2026-07-24-…, 2026-07-26-… 4건, 2026-07-27-… 2건). `grep -rln kinviz docs/` 는 **본 파일 자신만** 반환.
      `find . -name 'libOdoCalculator*'` **0건**(오라클 바이너리도, 대조 로그도 없음).
      "완전 일치" 는 실제 조향각을 만드는 IK 에 대한 **최상급 검증 주장**인데 재현 가능한 근거가 인용돼 있지 않다.
      ⇒ **대조 로그를 첨부하기 전까지 "완전 일치" 는 미검증으로 취급**한다(패키지 README 도 같은 판정: `src/Actuators/motor_control/README.md:21-26`).
      재검증 방법: 오라클 바이너리(`libOdoCalculator.so`) 확보 → 동일 입력 5케이스 이상을 양쪽에 넣어 수치 대조 로그를 첨부.

## 결정 (Decision)

1. **패키지**: `src/Motor_Control/`(사용자 지정 폴더) 에 ament_python 패키지 **`motor_control`**(ament 소문자 규칙; 폴더명≠패키지명 허용) 생성. ROS2 Humble, rclpy.
   - **[경로 갱신 2026-07-27]** 위 경로는 **현재 저장소에 존재하지 않는다** — `ls src/` → `Actuators AI Comm Control Safety Sensors Tools`(`src/Motor_Control` 부재).
     실제 위치는 **`src/Actuators/motor_control/`** 이며 §2 가 규정한 모듈 구성과 일치한다
     (`src/Actuators/motor_control/motor_control/{kinematics.py, backend.py, protocol.py, driver_node.py}`, `config/tongyi_amr.yaml`).
     이동 경위를 기록한 문서를 찾지 못했으므로 **이동 사유는 단정하지 않는다**. (패키지 README 도 같은 경로 갱신을 이미 기재: `src/Actuators/motor_control/README.md:38`.)
2. **모듈 세트 추상화(사용자 설계 지시)**: 지령 단위 = `ModuleCommand(v[m/s], θ[rad]|None)` 배열.
   - `kinematics.py`: Twist→ModuleCommand[] — `DualSteerKinematics`(연속 스워브 IK = kin_inverse 이식) + `DiffDriveKinematics`(θ=None, 차동) → **DD 타입 커버리지 확보**
   - `backend.py`: ModuleCommand[]→CAN — `TongyiSdoBackend`(SDO 마스터: 브링업·enable·50Hz 지령·20Hz guard RTR·피드백 폴링). θ=None 모듈은 조향 지령 생략.
3. **의존성 추가** `python-can` — License: **LGPL-3.0** (동적 import 사용, 배포 비결합) · 취약점: 알려진 CVE 없음(2026-01 기준, 로컬 설치 3.x/4.x) · 대안: stdlib `socket(AF_CAN)`(RTR 포함 가능하나 재구현 비용), `ros2_socketcan`(토픽 우회 지연). 프로젝트 내 검증 이력(DirectDriver·relay 킷) 때문에 python-can 채택.
4. `ros2_canopen` 비채택: NMT-Operational+PDO 전제 — 본 버스는 Pre-operational+SDO 폴링(실측)이라 미검증 경로.

## 안전 설계 (Safety gates)

- **브링업 게이트**: 시작 시 0x6064 선판독 → 조향 실측이 홈에서 허용오차 초과 시(~~콜드 부팅 = 137° 물리 스윙 필요~~) 파라미터 `allow_homing_motion`(기본 false)이 아니면 **구동 거부**. ~~명시 허용 시에만 Seer 브링업 시퀀스 재현.~~
  - **[⚠ 2026-07-27 정정 — 게이트의 전제·판정식·적용범위 (원문 이력 보존. 게이트 존폐·기본값·코드는 변경하지 않음)]**

    **① 「콜드 부팅 = 137° 물리 스윙(=위험한 미지 거동)」 전제가 틀렸다.**
    콜드부팅 137° 조향 스윙은 이상거동이 아니라, **호밍 완료 후 음의 리밋(원점)에서 조향 0° 로 복귀하는
    설계된 이동**이다. 복귀 목표 counts 는 node3 = **7,882,020** / node4 = **7,859,062**
    (리밋 원점 기준 +137.45° / +137.05°, 57344 counts/°)이고 EasyDRIVE `steerOffset` **138.000 / 137.250**
    과 대응한다. 즉 이 목표값이 곧 **조향 0°** 다.
    근거: `Log/homing_capture_220350.jsonl`(Seer 주도 호밍, 수동청취 253,510 프레임 — t≈49.14 에 `0x607A`
    복귀 목표 지령, 소요 약 3 s) + 드라이브 파라미터 직접 판독(2026-07-27).
    ⇒ 「원인 미상」·「이상 스윙」·「Home 36/37 기계 하드스톱」류 서술은 **철회**한다. 조향축에는 **리밋
    스위치가 실재**하고 방식은 **Home 1(음의 리밋 트리거)** 이다 — 전 노드 `0x6098 = 1` 실기 판독으로 확정
    (Handbook V7.0 §4.6 printed page 116 의 공장 기본 RstMode 도 1).
    ※ 구동축(node1·2)은 기계 원점이 없어 **호밍하지 않는다**(Seer 도 조향 노드에만 호밍 프레임 송신).

    **② `0x6064` 단독으로는 콜드/웜을 가를 수 없다.**
    축이 물리적으로 홈(137.45°)에 있어도 `0x60FB:04=1`(RstStart) 직후부터 `0x6064` 는 **정확히 0 으로
    약 31 s 고정**된다(`Log/homing_capture_220350.jsonl` t≈18.0~49.2). 관측된 0 은 "부팅 상태" 가 아니라
    "호밍 루틴의 카운터 리셋 상태" 일 수 있다.
    ⇒ 최소 (`0x6064`, `0x6041` bit15, `0x6000:01` bit3) **3 중 조건** + 직전 `0x60FB:04` write 이력을 함께
    보고, 판정 불가면 `allow_homing_motion` 여부와 **무관하게 구동 거부**해야 한다.
    (구현 주석도 이미 같은 판정: `src/Actuators/motor_control/motor_control/backend.py:265-271`
    「'콜드/웜' 이분법은 성립하지 않는다」.)

    **③ 「명시 허용 시에만 Seer 브링업 시퀀스 재현」은 구현과 다르다.**
    게이트는 `_write_init_sequence()` **이전에 1 회만** 판정하고
    (`backend.py:185-187` — `_preflight_read() → _gate_homing_motion() → _write_init_sequence()`),
    init 시퀀스는 **게이트 통과 여부와 무관하게** 조향 노드에 `0x6099=2500`(Homing Speeds)·
    `0x60FB.4=1` 을 **무조건** 쓴다(`backend.py:362`, `:368`; `:367` 주석이 스스로
    「⚠ allow_homing_motion 게이트는 홈 이탈만 보므로 웜 상태에서도 이 줄은 실행된다」라고 적는다).
    `0x60FB.4` 의 의미는 확정됐다 — **RstStart(호밍 개시), "0-Reset off, 1-Reset on"**
    [Handbook V7.0 §6.9, page 171]. 「벤더 오브젝트·의미 미상」이 아니다.
    ⇒ **이 게이트는 호밍 스윙을 막는 수단이 아니다.** 호밍 완료 대기 게이트
    (`0x6041` bit15 0→1 복귀 + `0x6000:01` bit3 해제 확인 전 `0x607A` 송신 금지)를 별도로 두어야 한다.
    (본 정정은 서술만 고친다 — 동작 변경은 부채 등록 대상.)
- **조향 정착 게이트**: 조향 목표↔실측 편차 > `steer_settle_tol`(기본 3°) 동안 구동속도 0 (Seer 의 정지 중 국면 전환과 등가 — 이산/연속 모두 커버).
- cmd_vel 워치독(기본 200 ms) → vel 0 · `/estop` 래치 → vel 0 · 속도 상한 `vmax`(기본 0.2 m/s)·`wmax`(기본 0.3 rad/s).
- 미검증 부호 가정 2건(자매 ADR §가정: `kin_steer_sign=+1`, 구동노드↔전/후 매핑)은 **파라미터로 노출**, 첫 실차는 저속(≤0.05 m/s) 방향 확인 절차를 README 에 명기.
  - **[2026-07-27 정정 — "구동노드↔전/후 매핑" 은 미검증이 아니라 실측 반증됨]**
    `docs/code_review/motor_control-can-consistency/2026-07-26.md:43` "🔴 HIGH — 모듈 전/후(module_x) 노드 배정 반전 (실측 데이터와 정면 모순)",
    `:45` "실측: node1=FrontWalk x=**+0.604**, node2=RearWalk x=−0.596(`tongyi-canopen-protocol-reference.md` §1, EasyDRIVE canID config)",
    `:47` "코드: `module_x: [-0.5961, 0.6039]` → node1=**−0.5961(Rear)**",
    `:49` "저장 데이터가 이 가정을 반증(**node1=Front**)", `:52` 권고 "… (또는 ADR에 \"실측 반증됨\" 반영)".
    ⇒ 본 줄의 "미검증 가정" 등급은 **사실과 다르다**. 해당 항목은 반증된 상태다.
    **미판정으로 남는 것**: 이 반전이 실배선·`drive_sign` 과 상쇄되는지 여부. 판정에 필요한 측정 =
    **실차 저속(≤0.05 m/s) 크랩/스핀 방향 확인**(code_review `:52`).
    `config/tongyi_amr.yaml:57` 의 `module_x` 값은 그 측정 전까지 **변경하지 않는다**(현재 미수정 상태이며 `:57` 주석이 ⚠ 로 표기 중).
  - 참고: "**파라미터로 노출**" 이라는 서술 자체는 사실로 확인됨(`config/tongyi_amr.yaml` 의 `drive_sign`·`kin_steer_sign`·`module_x` 항목, `motor_control/driver_node.py` 파라미터 선언).

## Rollback Plan

- 신규 패키지 추가만(기존 코드 무변경) — 문제 시 `src/Motor_Control/` 삭제 + 본 ADR `Status: Superseded` 로 완전 복구. 영속 상태·스키마 없음.
  - **[경로 갱신 2026-07-27]** 이 롤백 절차를 **지금 그대로 실행하면 아무 것도 되돌리지 못한다** — `src/Motor_Control/` 는 현재 저장소에 부재(`ls src/` 확인).
    롤백 대상 경로는 **`src/Actuators/motor_control/`** 이다(§결정 1 의 경로 갱신 주석 참조). 원문은 이력으로 보존.
- 실차: 드라이버 파라미터는 휘발(드라이버 EEPROM 쓰기 없음 — 0x1010 Store 미사용), 로봇 전원 재투입 시 Seer 원상 운용 가능.

## 검증 계획

- 단위: `protocol`(SDO 인코드/디코드 왕복), `kinematics`(직진/후진접기/크랩/스핀/포화 5케이스 + DD 차동), `backend`(mock 버스로 브링업 순서·워치독·estop).
- 통합: vcan 셀프테스트(가상 슬레이브 응답) → colcon build + pytest 전체 PASS.
- 최종 verdict 는 저자 불가(never-self-approve) — 별도 code_review lane + 실차 저속 검증 소관.
