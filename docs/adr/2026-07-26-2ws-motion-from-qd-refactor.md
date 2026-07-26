# ADR 2026-07-26 — 2WS 모션 스택 신설 (QD refactor + Foil_A082 실측 inline 기하)

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
- **geometry** [`trnav_2ws_core/config/robot_geometry_2ws.yaml`]: Foil_A082 실측 inline
  - W1 Front(앞) = (+0.6039, −0.0014), W2 Rear(뒤) = (−0.5961, −0.0014) — **y≈0 센터라인**
  - wheel_radius = 0.125, gear_walk = 32.0, wheelbase = 1.200
  - platform enum 은 `QD_DIAGONAL` 재사용(wheel_set_packer 의 "2륜 pack" 경로일 뿐, 대각/inline 무관 동일).

## 근거·검증
- **정본(2 source 교차확인)**: `Tools/Kinematics/chassis_kinematics.py`(Seer live_models.hpp 추출 KIN_NODE_XY)
  + `src/Actuators/motor_control/config/tongyi_amr.yaml`(실물 driver: module_x=[-0.5961, 0.6039], module_y=[-0.0014,-0.0014], track_width=1.2).
- **빌드**: 6/6 finished, **error 0**. stderr = `-Wformat`(%d vs size_t) 경고뿐(원본 잔존). action 노드 9종 설치.
- **기구학 검증**: `TwoWsDualSteerIK`(실측 기하) 실행 결과 = Seer 원본과 소수4자리 일치 —
  직진(0°), 크랩(+90°), 스핀(Front +89.87°/0.1208, Rear −89.87°/0.1192, y-offset 비대칭까지 동일).
- 미검증(정직): 런타임(SIL/HIL/실차) 거동·조향부호(kin_steer_sign)·drive_sign 은 범위 밖.

## 기각안
- QD config 만 실측값으로 교체(별도 2WS 없이) | QD 명칭("diagonal")·upstream 정체성과 충돌, 폴더 구조(QD/4IS/DD/2WS) 취지 위반. → 별도 2WS 스택.
- 공유 패키지(interfaces/msgs/core) 는 QD 재사용 | 2WS 가 QD/ 빌드에 종속돼 독립성 상실. → 전 패키지 리네임(자립).

## 영향·주의
- Scope: 신규 6패키지(코드 로직 무변경, 리네임+geometry config 만). QD 스택 무영향.
- **QD 와 공존**: 패키지명·네임스페이스·심볼 분리로 동일 workspace 빌드 가능. action 노드 실행파일명은
  동일(`amr_mpc_node` 등)이나 **패키지 한정 실행**(`ros2 run trnav_2ws_action_server amr_mpc_node`)이라 무충돌.
- **run-time 파라미터 주의**: launch 의 geometry param 경로가 `robot_geometry_2ws.yaml` 을 가리키는지 배포 시 확인.
- 관련: [2026-07-26-qd-motion-port.md](2026-07-26-qd-motion-port.md), [2026-07-26-qd-ik-pm90-unique-solution.md](2026-07-26-qd-ik-pm90-unique-solution.md).
- Confidence: high(빌드·기구학 대조·2 source 기하). Not-tested: 실차 거동, 부호 가정.
