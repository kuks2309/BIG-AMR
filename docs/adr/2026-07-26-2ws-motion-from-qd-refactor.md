# ADR 2026-07-26 — 2WS 모션 스택 신설 (QD refactor + ~~Foil_A082 실측~~ inline 기하)

> ### ⚠ 2026-07-27 정정 요약 (원문은 이력 보존을 위해 지우지 않는다)
> 제목·:22 의 「**Foil_A082 실측** inline 기하」 라벨과 :28 의 「**정본(2 source 교차확인)**」 은
> 근거보다 강하다. 상세는 §근거·검증 아래 정정 블록 참조. **값(0.6039 / −0.5961 / −0.0014 / 1.200)은
> 하나도 바꾸지 않았다** — 서술·근거 등급만 정정한다.

## 상태
채택(생성·빌드·기구학 검증 완료). ROS2 Humble / Jetson(aarch64) colcon build error 0,
2WS `TwoWsDualSteerIK` 출력이 Seer 원본(`chassis_kinematics.py`)과 실측 기하에서 완전 일치.

## 맥락
현재 실물 AMR = **Foil_A082**(Seer 라이브 API 1000 판독: feature `rbk_multisteer` active).
구동 방식 = **앞뒤 센터라인 2 조향-구동휠(inline dual-steer)** — Seer 분류 multisteer.
이식했던 `QD` 스택은 upstream(TR_Nav) 명칭 "Quad-Drive **diagonal**"이고, 딸려온
`robot_geometry_qd.yaml` 은 **Carrier AGV 대각(y=±0.135)** 플레이스홀더라 실물과 기하가 다름.
`QdDualSteerIK` 는 휠 좌표를 인자로 받는 **기하 무관 설계**라 코드 로직은 실물에도 그대로 유효.

## 결정
`QD` 6패키지를 `src/Control/Motion_Control/2WS/` 로 **복사·리네임하여 독립 스택 신설**하고,
geometry 를 실측 inline 값으로 교체:

- 패키지: `trnav_2ws_{interfaces,msgs,kinematics,core,motion,action_server}`
  (QD 의 `trnav_{interfaces,msgs,qd_kinematics,motion_core,motion_qd,motion_action_server}` 대응)
- 네임스페이스 `trnav::motion::qd` → `trnav::motion::two_ws`, 클래스 `Qd*` → `TwoWs*`
  (QD 와 colcon 패키지명·심볼 충돌 회피 → 공존 가능). C++ 식별자 규칙상 "2ws" 불가 → `two_ws`.
- **geometry** [`trnav_2ws_core/config/robot_geometry_2ws.yaml`]: ~~Foil_A082 실측~~ inline
  (⚠ 2026-07-27: "Foil_A082 실측" 라벨은 **미판정** — 아래 정정 ① 참조)
  - W1 Front(앞) = (+0.6039, −0.0014), W2 Rear(뒤) = (−0.5961, −0.0014) — **y≈0 센터라인**
  - wheel_radius = 0.125, gear_walk = 32.0, wheelbase = 1.200
  - platform enum 은 `QD_DIAGONAL` 재사용(wheel_set_packer 의 "2륜 pack" 경로일 뿐, 대각/inline 무관 동일).

## 근거·검증
- ~~**정본(2 source 교차확인)**~~: `Tools/Kinematics/chassis_kinematics.py`(Seer live_models.hpp 추출 KIN_NODE_XY)
  + `src/Actuators/motor_control/config/tongyi_amr.yaml`(실물 driver: module_x=[-0.5961, 0.6039], module_y=[-0.0014,-0.0014], track_width=1.2).

> ### ⚠ 2026-07-27 정정 — 위 근거 문단 (원문은 이력 보존용으로 남김. **값 변경 0건**)
>
> #### ① 「Foil_A082 실측 기하」 = **미판정 모순**
> 같은 수치의 출처로 인용된 파일들은 이 기하를 **Roll_A084** 에 귀속한다:
> - `Tools/Kinematics/chassis_kinematics.py:29` 「기하: **Roll_A084 실측 config (live_models.hpp:67)** —
>   Front x=+0.6039, Rear x=-0.5961, y=-0.0014 (휠베이스 1.200 m)」
> - `Tools/Kinematics/README.md:75` 「바퀴 기하: **Roll_A084 실측 config** (`live_models.hpp:67`) …」
> - 형제 ADR [2026-07-26-qd-ik-pm90-unique-solution.md](2026-07-26-qd-ik-pm90-unique-solution.md) §근거·검증
>   「동일 기하 **Roll_A084**」
>
> 반면 실물은 **Foil_A082** 다 — 본 ADR §맥락 :8「현재 실물 AMR = Foil_A082(Seer 라이브 API 1000 판독)」,
> `Tools/Can_Relay/FIELD-RECORD-2026-07-25.md:76`(로봇 Foil_A082, RBK v3.4.5.22).
> **Foil_A082 를 직접 실측했다는 기록은 저장소에 없다.**
>
> ⇒ **미판정**: 「Roll_A084 의 `live_models.hpp` 추출값을 Foil_A082 에 적용한 것」인지
> 「Foil_A082 자체 실측」인지 **어느 쪽인지 알 수 없다**. 어느 쪽으로도 값을 고치지 않는다.
> **판정에 필요한 측정**: (a) Foil_A082 실기에서 앞/뒤 휠 중심 간 종방향 거리와 y 오프셋 직접 실측,
> 또는 (b) 해당 로봇의 `live_models.hpp` / Seer API 1000 판독으로 `KIN_NODE_XY` 재확인.
>
> #### ② 「2 source 교차확인」 철회
> 1. **독립 교차확인이 아니다.** 두 source 는 동일 원본(Seer `live_models.hpp`) 파생이다
>    (`chassis_kinematics.py:29` 가 명시). 같은 뿌리에서 나온 두 사본은 서로를 검증하지 못한다.
> 2. **두 번째 source 는 스스로 '가정'이라 표기하며, 이미 🔴HIGH 로 반증 지적된 상태다** —
>    `src/Actuators/motor_control/config/tongyi_amr.yaml` 헤더 「⚠ drive_sign·kin_steer_sign·**module_x
>    (node1=Rear)** 는 미검증 가정 포함」, 및 module_x 항목 주석 「⚠ node1=Rear 가정(부호 정합 도출)」.
>    `docs/code_review/motor_control-can-consistency/2026-07-26.md` §3
>    「🔴 HIGH — 모듈 전/후(module_x) 노드 배정 반전 (**실측 데이터와 정면 모순**) … 실측: node1=FrontWalk
>    x=**+0.604**, node2=RearWalk x=−0.596 … 저장 데이터가 이 가정을 **반증**(node1=Front)」.
>    `docs/verified_facts/2026-07-27.md` §C 도 「`module_x` 노드 전/후 배정 (code_review 에서 🔴HIGH 로
>    지적된 모순이 **미해소** 상태)」로 분류한다.
>    (원 실측표: `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md` §1
>    EasyDRIVE canID config. ⚠ **2026-07-28** — 재인용처였던 `Tools/amr_test_gui/amr_test_gui/constants.py:60-67`
>    은 구 GUI 폐기로 삭제됐다(docs/adr/2026-07-28-old-gui-removal.md). 정본은 위 reference 문서 §1 하나뿐이므로 그쪽을 볼 것.)
> 3. **파생 config 에서 경고가 소실됐다** — `src/Control/Motion_Control/2WS/trnav_2ws_core/config/
>    robot_geometry_2ws.yaml` 의 `w1_x: 0.6039 # m Front(앞) (motor_control node2 = +0.6039)` 는
>    '⚠ 가정' 표시를 떼고 확정 서술로 적혀 있다. **그 파일은 이 정정의 담당 영역 밖이라 손대지 않았다** —
>    후속 작업자가 반드시 같은 경고를 반영할 것.
>
> ⇒ 전/후 배정(어느 노드가 앞인가)은 **미판정**이며, 값(0.6039 / −0.5961)은 바꾸지 않는다.
> **판정에 필요한 측정**: 저속(≤0.05 m/s) 크랩/스핀에서 node1/node2 중 어느 축이 앞인지 육안 + IMU 로 확인.
> 주의: 이 배정은 spin·crab·오도메트리 yaw 부호에 영향을 준다(직진 등속에서는 드러나지 않는다 —
> code_review 같은 절).
>
> #### ③ `track_width=1.2` 는 wheelbase 의 교차 근거가 **아니다**
> `tongyi_amr.yaml` 의 `track_width` 는 종방향 축거가 아니라 **diff_drive 전용 횡방향 파라미터**다 —
> `src/Actuators/motor_control/motor_control/driver_node.py:80` `("track_width", 1.2),  # diff_drive 용`,
> :92 `DiffDriveKinematics(drive_nodes[0], drive_nodes[1], g["track_width"], g["vmax"])`,
> `src/Actuators/motor_control/motor_control/kinematics.py:125-126`
> `vl = vx - wz * self.track_width / 2.0` / `vr = vx + wz * self.track_width / 2.0`(**좌우** 분배).
> 값 1.2 가 우연히 0.6039+0.5961 과 같을 뿐이다. (해당 config 자신도 이미 정정돼 있다 —
> `tongyi_amr.yaml` track_width 주석 「⚠ 이 값은 **좌우 트랙폭 실측이 아니라 휠베이스**다」.)
>
> ⇒ 올바른 서술: **`wheelbase = 1.200` 은 module_x 두 값의 차(0.6039 − (−0.5961))에서 도출한 값**이며,
> `track_width` 인용은 독립 근거가 아니다. 같은 오인용이
> `src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml` 의 wheelbase 주석에도
> 복제돼 있다(담당 영역 밖 — 미수정, 후속 처리 필요).
- **빌드**: 6/6 finished, **error 0**. stderr = `-Wformat`(%d vs size_t) 경고뿐(원본 잔존). action 노드 9종 설치.
- **기구학 검증**: `TwoWsDualSteerIK`(실측 기하) 실행 결과 = Seer 원본과 소수4자리 일치 —
  직진(0°), 크랩(+90°), 스핀(Front +89.87°/0.1208, Rear −89.87°/0.1192, y-offset 비대칭까지 동일).
- 미검증(정직): 런타임(SIL/HIL/실차) 거동·조향부호(kin_steer_sign)·drive_sign 은 범위 밖.

## 기각안
- QD config 만 실측값으로 교체(별도 2WS 없이) | QD 명칭("diagonal")·upstream 정체성과 충돌, 폴더 구조(QD/4IS/DD/2WS) 취지 위반. → 별도 2WS 스택.
- 공유 패키지(interfaces/msgs/core) 는 QD 재사용 | 2WS 가 QD/ 빌드에 종속돼 독립성 상실. → 전 패키지 리네임(자립).

> ### ⚠ 2026-07-31 부분 supersede — 위 기각안 중 **msgs 부분만** 뒤집힘 (원문은 이력 보존)
>
> `trnav_2ws_msgs` 는 **폐기**되고 `trnav_msgs` 하나로 통합됐다.
> 정본: [ADR 2026-07-31 — 체인 상류 2노드 이식 + 메시지 패키지 통합](2026-07-31-motion-motor-chain-mux-translator-port.md).
>
> **뒤집힌 이유** — 위 기각 사유("QD/ 빌드에 종속")는 `trnav_msgs` 가 `Motion_Control/QD/` **아래**
> 있다는 전제에서만 성립한다. 그것을 `Motion_Control/Common/` 으로 꺼내자 **종속 자체가 사라졌다.**
> 더불어 상류 조사 결과 `trnav_msgs` 는 QD 전용이 아니라 **20개 패키지가 공유하는 워크스페이스
> 공통 계약**이고(DD 스택 `trnav_motion_dd`·`trnav_dd_kinematics` 포함), `WheelSet.msg:1` 이
> 스스로 「Per-wheel motion command (**platform-agnostic**)」라 선언하며 QD/DD/4WS/Ackermann
> 해석을 나란히 적는다. 플랫폼별 사본은 **내용 동일·타입 비호환** 패키지를 플랫폼 수만큼 늘린다.
>
> **유효한 부분** — kinematics·core·motion·action_server 의 리네임(`trnav_2ws_*`,
> 네임스페이스 `trnav::motion::two_ws`, 클래스 `TwoWs*`)과 geometry 교체 결정은 **그대로 유효하다.**
> 이번 supersede 는 msgs 1개 패키지에 한정된다.
>
> **부작용** — 타입 불일치가 우연히 제공하던 「QD·2WS 동시 기동 차단」이 사라졌다 → **debt-024**.

## 영향·주의
- Scope: 신규 6패키지(코드 로직 무변경, 리네임+geometry config 만). QD 스택 무영향.
- **QD 와 공존**: 패키지명·네임스페이스·심볼 분리로 동일 workspace 빌드 가능. action 노드 실행파일명은
  동일(`amr_mpc_node` 등)이나 **패키지 한정 실행**(`ros2 run trnav_2ws_action_server amr_mpc_node`)이라 무충돌.
- **run-time 파라미터 주의**: launch 의 geometry param 경로가 `robot_geometry_2ws.yaml` 을 가리키는지 배포 시 확인.
- 관련: [2026-07-26-qd-motion-port.md](2026-07-26-qd-motion-port.md), [2026-07-26-qd-ik-pm90-unique-solution.md](2026-07-26-qd-ik-pm90-unique-solution.md).
- ~~Confidence: high(빌드·기구학 대조·2 source 기하).~~
  → **⚠ 2026-07-27 정정 — Confidence 분리 표기**:
  - 빌드(colcon 6/6, error 0): **high**.
  - 기구학 대조(SW-vs-SW, 소수 4자리 일치): **medium** — 물리 측정이 아니라 참조 파이썬 모듈과의 비교이며,
    그 모듈은 노드매핑·조향부호를 스스로 '가정'으로 표기한다(`chassis_kinematics.py:15-16,30,33`).
  - 기하 출처(「Foil_A082 실측」·「2 source 교차확인」): **미판정** — 위 정정 ①② 참조.
  Not-tested: 실차 거동, 부호 가정(kin_steer_sign·drive_sign), module_x 전/후 배정, Foil_A082 기하 실측.
