---
id: 2026-07-31-004
type: mistake
category: context-missing
status: closed
reflected_assets:
  - docs/adr/2026-07-31-can-relay-cpp-motor-layer.md
  - docs/debt/registry.md (debt-021, debt-022)
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-motion-motor-chain.md
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/MEMORY.md
---

# 2026-07-31 21:15 (KST) — can_relay ROS2 드라이버를 저장소 모션 스택(QD/2WS)의 명령 계약과 대조하지 않고 단독 설계

## 무엇을 했는가

2026-07-29 세션에서 신설한 ROS2 드라이버 `src/Comm/CAN/can_relay/` 의 상위 인터페이스를
`cmd_vel`(`geometry_msgs/Twist`) 구독 + `joint_states` 발행으로 설계하고
`docs/adr/2026-07-29-can-relay-ros2-package.md` 로 승인받았다.

그 설계에서:

- `cmd_vel` 을 받아 `motor_control.kinematics` 를 대여해 **패키지 안에서 역기구학을 수행**하고,
  축별 조향각 편차가 1.0° 를 넘으면 지령을 거부하도록 했다(`driver_node.py:182-187`).
- ADR §Consequences 에 「`cmd_vel` 은 동일각(직진/크랩)만 지원한다. 스핀·선회는 축별 각이
  갈리므로 명시 거부한다」(:135), 「2WS 모션 스택이 기다리는 `wheel_motor_state` 발행자는
  아직 만들지 않았다(Phase 2)」(:136) 라고 적었다.

## 무엇이 잘못이었나

같은 저장소에 이미 있던 모션 스택의 **명령 계약을 조사하지 않고** 상위 인터페이스를 정했다.

1. **저장소의 모터 계층 계약은 `cmd_vel` 이 아니다.** 상류 원본 `kuks2309/TR_Nav_ros2_ws`
   (HEAD `ad7520981d500fa5881e548ef22fc92d0d7fe4a1`, 2026-07-31 대조)의 체인은
   `action server ─WheelSetArray→ trnav_motion_mux ─/motor/wheel_cmd→ amr_motor_cmd_translator
   ─MotorCmdArray→ amr_canopen_motor_driver` 이며,
   `grep -rn "cmd_vel" src/Control/AMR-Motor/` → **0건**이다. `cmd_vel` 은 모터 계층에 닿지 않는다.
   ⇒ 설계한 인터페이스가 **체인의 어느 노드와도 연결되지 않는다.**

2. **조사할 수 있는 위치에 있었다.** `Motion_Control/QD` 6패키지는 2026-07-26 에 이 저장소로
   이식됐고(`docs/adr/2026-07-26-qd-motion-port.md`), `Motion_Control/2WS` 도 같은 날 파생됐다
   (`docs/adr/2026-07-26-2ws-motion-from-qd-refactor.md`). can_relay ADR 은 **3일 뒤**다.
   `trnav_msgs/MotorCmd.msg` 는 `1=walk_front, 2=walk_rear, 3=steer_front, 4=steer_rear` 를
   주석에 명시하고 있었고, 이는 can_relay 가 채택한 `drive_nodes: [1,2]`·`steer_nodes: [3,4]` 와
   **정확히 같은 배정**이다. 같은 파일을 열었으면 계층이 어긋났음을 그 자리에서 알 수 있었다.

3. **회전이 불가능해졌다.** 1.0° 편차 게이트는 축간거리 1.2 m 기하에서 **최소 선회반경 68.8 m**
   를 강제한다. `wmax: 0.3 rad/s` 파라미터 중 실제 통과하는 최댓값은 `0.00291 rad/s`(0.97%)다.
   한편 `trnav_qd_kinematics/.../qd_bicycle_model.hpp` 의 `DualBicycleCommand` 는
   `omega = vx * (tan(delta_f) - tan(delta_r)) / L` 이라 **회전은 전·후 조향각이 다른 것이
   정의**다. ⇒ bicycle 모델을 쓰는 액션 서버 **9종 중 6종**(`mpc`, `mpc_reverse`, `yaw_control`,
   `yaw_control_reverse`, `translate_forward`, `translate_reverse`)의 지령이 전부 거부된다.

4. **정직하게 적어 둘 것** — 2WS 스택의 존재 자체를 몰랐던 것은 아니다. ADR :136 이 2WS 를
   언급한다. 그러나 그것을 **피드백 발행자(`wheel_motor_state`) 하나를 Phase 2 에 추가하면 되는
   일**로 축소 인식했고, **명령 경로 전체가 다른 계약**이라는 사실에는 도달하지 못했다.
   즉 "몰랐다"가 아니라 **"조사 없이 작다고 가정했다"** 가 정확한 서술이다.

## 사용자 지적

> "cmd_vel (Twist) 그러니 설계를 잘못한거지
>  /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Control/Motion_Control/QD와
>  /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Control/Motion_Control/2WS 에
>  연결되도록 설계를 안하고 단독으로 설계한 결과이지"

앞선 같은 세션의 지적 두 건이 이 결론으로 이어졌다 —
「`cmd_vel (Twist) VOLATILE` ?? 현재 모션과 어울리나요?」,
「`Motion_Control/QD` 과 연동하려면 bicycle 모드 기능과 연동이 되어야 하지 않을까?」.

## 원인 분석

`context-missing`. 조사 범위를 **드라이버 자신의 하류(판다·CAN·드라이브)** 로 한정하고
**상류(누가 이 드라이버에 지령을 보내는가)** 를 조사 대상으로 삼지 않았다.

can_relay ADR 은 하류 근거를 매우 촘촘히 쌓았다 — 실측 캡처 253,510 프레임과 바이트 대조,
안전 요건 S1~S10 을 84건 회귀로 고정, 사고 이력 인용. 그 철저함이 **상류 미조사를 가렸다.**
"하류가 이렇게 탄탄하니 설계가 검증됐다"는 인상이 만들어졌고, 정작 인터페이스가 누구와
연결되는지는 검증 항목에 없었다. ADR §Verification 이 나열한 확인 경로도 전부 자기 노드
내부(engage → 클램프 → NaN 거부 → 워치독 → 정지)이며, **다른 노드와의 연결을 확인한 항목이 0**이다.

`cmd_vel` 을 고른 근거도 조사가 아니라 관례였다. ROS2 이동로봇의 기본 인터페이스가 `cmd_vel`
이라는 일반 지식을 이 저장소의 실제 구성보다 앞세웠다.

**재발이다.** `2026-07-28-010`(기존 자산 조사 누락 — ICP 오도메트리)의 §재발 방지가
「기능 도입 검토 시 사용자 저장소를 먼저 조사한다」를 메모리에 기록했는데, 그 다음 날
can_relay 설계에서 같은 조사가 다시 생략됐다. `2026-07-27-004`(저장소 전수 조사 누락)와도
같은 계열이다. `docs/claude-mistake/INDEX.md` §메타 패턴이 이미 결론지은
**「주입만으로는 막히지 않는다」** 가 또 확인됐다 — 메모리에 적어 두는 것만으로는 조사 행위가
발생하지 않는다.

## 재발 방지

- **설계 정정을 ADR 로 고정**: `docs/adr/2026-07-31-can-relay-cpp-motor-layer.md` (Status: Proposed).
  C++ 포팅 시 인터페이스를 모터 계층으로 내린다 — `/motor/low_cmd`(`MotorCmdArray`) 구독,
  `/motor/low_state`(`MotorStateArray`) 발행, `cmd_vel`·역기구학 대여·1.0° 게이트 제거,
  안전 계층(S1~S10) 전량 존치. bicycle 선회는 기능 추가가 아니라 **계층 하강으로** 해소된다.
- **부채 등록**: `debt-021`(체인 상류 `trnav_motion_mux`·`amr_motor_cmd_translator` 부재 —
  can_relay 만 고쳐서는 체인이 안 이어짐), `debt-022`(조향 환산 책임 경계 미확정 —
  `steer_offset` 이중 적용 위험).
- **신규 메모리** `biguamr-motion-motor-chain.md` 에 **체인 계약을 값으로 기록**한다 —
  토픽명·메시지 타입·QoS·motor_id 배정·저장소 부재 노드. 다음 세션이 조사하지 않아도 계약을
  알 수 있게 한다(메모리에 "조사하라"고 적는 방식은 2026-07-28-010 에서 실패했으므로,
  이번에는 **지시가 아니라 사실**을 적는다).
- **조사 순서의 교훈**: 새 노드·드라이버를 설계할 때 하류(장치)만이 아니라 **상류(지령원)를
  같은 깊이로 조사한다.** 구체적으로 "이 노드에 지령을 보낼 노드가 저장소에 실재하는가,
  그 노드는 어떤 토픽·메시지로 보내는가"를 ADR §Context 에 근거와 함께 적는다.
  can_relay ADR 에는 그 문단이 없었다.
