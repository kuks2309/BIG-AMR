# ADR 2026-07-31 — can_relay C++ 포팅: 인터페이스를 모터 계층으로 내린다

> ## ❌ 정정 2026-08-03 15:40 — 호밍 실험 종결 (10회 연속 실측). 단, 바로 아래 「재정정 2026-08-03 17:00」 블록이 이 블록의 수치·판정을 갱신했다 — 본 문서 최신은 17:00 블록이다
>
> 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0**
> (`Tools/docking_field_kit/orin_home_experiment.py --repeat 10`, 15:33~15:40, 접지 상태, 펌웨어 `DEV-cc5e0491-DEBUG`)
>
> - **호밍은 정상 동작한다 — 10 / 10 성공**, 소요 **35.0 s**(편차 0.17 s). 09:58 `ERR_TIMEOUT` 1회 뒤
>   **12회 연속 성공**, 재현되지 않는다.
> - **호밍 후 정착값(10회 재현, σ ≈ 3 counts)**: node3 **7,882,021** · node4 **7,859,065**
>   → 조향 0° 대비 **+0.178° / +0.331°**. **결함이 아니라 설계 동작이다.**
> - **조향 0° = `[7871815, 7840086]`** — ⚠ 아래 원 배너에는 없는 유보: 이 0° 는 **Seer 좌표계 기준**이며
>   **물리적 직진과 같은지는 미확인**이다. 따라서 아래 ④ `steer_offset` 이중 적용 위험 판단 시
>   「0° = 물리 직진」을 전제로 삼지 말 것.
> - **counts/° = 57,344**(실측 기울기 1.000000) · `0x6098` = **1**(Home 1) · **리밋 스위치 실재**.
> - Seer 1005·1040 은 **둘 다 `0x6064` 유래** — 독립 앵커가 아니다. CAN↔Seer 교차검증은 성립하지 않는다.
> - 폐기된 주장(**인용 금지**): 「`Switch on disabled` 라 호밍 불가」 · 「`0x6098`=0 이라 비활성」 ·
>   「RstStart 고착」 · 「`0x6064`=0 은 전원 사이클 래치」 · 「이미 홈이면 무동작 즉시 완료」 ·
>   편차 표기 `+0.334°`/`+0.332°`(→ **`+0.331°`**).

> ## ❌ 재정정 2026-08-03 17:00 — 바로 위 15:40 블록의 수치·판정 오류 (원문은 삭제하지 않는다)
>
> 원자료 직접 재계산: `Log/home_experiment_260803_153319_summary.json` ·
> `Log/home_experiment_260803_09{1956,5815}_summary.json` · `Log/homing_edge_260803_144602.json` ·
> `Log/homing_edge_260803_152520.json` · `Log/homing_edge_260803_144305.json` ·
> `Log/seer_homing_260803_100813.jsonl` · `Log/steer_two_phase_260803_131305.jsonl` ·
> `Log/steer_xcheck_reboot_0deg*.jsonl` · `Log/homing_capture_220350.jsonl`.
>
> - **「12회 연속 성공」 → 12회.** 2026-08-03 에 FSM 이 실제로 돈 호밍은 **시도 13 / 성공 12 / 실패 1**:
>   09:58 `final_state=6`(ERR_TIMEOUT, 120.26 s) **실패** → 14:46 DONE 37.00 s · 15:25 DONE 34.91 s ·
>   15:33 10회 DONE. ⚠ **「15:33 10회 연속 10/10」 자체는 유효**하다. 15:33 summary 의 `baseline`(t=1.058)은
>   호밍이 아니라 **레지스터 스냅샷**이므로 회차에 넣지 말 것(`fsm_trace` 가 빈 5건도 개시되지 않아 제외).
> - **「35.0 s」 → 평균 35.07 s · 중앙 35.05 s** (최소 34.99 · 최대 35.16 — 「편차 0.17 s」는
>   표준편차가 아니라 **범위**다). WAIT(−리밋 탐색) **체류는 31.30 s**(10회 평균, state4→state8;
>   31.7 은 RESTORE 진입 절대시각 t≈31.69 로 체류가 아니다).
> - **「σ ≈ 3 counts」** = **모표준편차** node3 **2.80** · node4 **3.21**(표본 2.95 / 3.38, n=10).
> - **「counts/° = 57,344(기울기 1.000000)」 → node3 57,344.0(1.000000) · node4 57,344.3(1.000005).**
>   두 노드가 같은 값이 아니다(`Log/steer_two_phase_260803_131305.jsonl` A국면 −5°~+5° 5지점 회귀).
>   config `steer_counts_per_deg: 57344.0` 은 node4 에 대해 **반올림 채택값**이다.
> - **「결함이 아니라 설계 동작이다」 → 과잉 확정.** 보증되는 것은 **10회 재현되는 정착 동작**뿐이며,
>   정착 목표인 펌웨어 상수 `SEER_HOME_ZERO_N3/N4 = 7,882,020 / 7,859,062`
>   (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:212-213`)의 **적정성은 별건**(debt-016)이다.
>   ⇒ 「**재현되는 정착 동작(상수 적정성은 별건, debt-016)**」으로 적는다.
> - **「조향 0° = `[7871815, 7840086]`」 값은 유지**(`config/machine/foil_a082.yaml:134`)하되 **근거는 강등**한다:
>   1040 역산 `0° = CAN + Seer°×57344` 는 Seer ≈0° 자세에서 보정항이 node3 **−4c** / node4 **+34c** 에 그쳐
>   사실상 **항등식**이고(`Log/steer_xcheck_reboot_0deg*.jsonl`, n=3110/3111), `0x607A` 근거는 **선택 인용**이다
>   (`Log/homing_capture_220350.jsonl` node3: 7,871,815 **145/6,464 = 2.24%** · 7,882,020 **6,319/6,464 = 97.76%**).
>   ⇒ 「실측 확정」이 아니라 「**공학적 채택값**」. 아래 ④ 이중 적용 위험 판단의 유보는 그대로 유지된다.
> - **폐기 목록의 「`0x6064`=0 …」 항 — 「단 1회·재현 안 됨」이라는 폐기 근거는 [거짓]이다. 0 은 재현된다.**
>   09:19 baseline pos3=pos4=**0** · 09:58 run1 pre/post **0** · 10:08 `Log/seer_homing_260803_100813.jsonl`
>   node3 **10,327/10,327** · node4 **10,327/10,327** 전량 0 · 리부팅 후 14:43
>   `Log/homing_edge_260803_144305.json` before node4 pos=**0**.
>   ⚠ **인과는 양쪽 다 미판정** — 0 이 관측되는 조건에서도 호밍은 12회 성공했으므로 「0 이 호밍을 막는다」도
>   「전원 사이클로만 풀리는 래치」도 입증되지 않았다.

> ⚠ **조향 홈 관련 서술은 2026-08-03 실측으로 재정정됐다(2026-08-02 종결값이 틀렸다).
> 아래 원문은 이력으로 보존한다.**
> 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §10
> (값 정본은 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 의 `steer_home_counts`)
>
> - 홈(0°) = **`[7871815, 7840086]`** — 2026-08-03 11:44 실측 확정.
>   판다 SILENT·passthrough(제어권 미취득), 송신 0건(AST 검사), **사용자 확인 Seer 표시 0°**,
>   2회 독립 실행 동일: node3 CAN 7,871,823 + Seer −0.000° → **0° = 7,871,816**,
>   node4 CAN 7,840,052 + Seer +0.001° → **0° = 7,840,087** (채택값과 각 1 count 차).
> - ❌ **정정 2026-08-03** — 2026-08-02 종결이 채택한 `[7871810, 7839894]` 는 **틀렸다.**
>   0° 는 raw CAN 판독값이 아니라 `0° = CAN_0x6064 + Seer_deg × 57344` 로 역산해야 하는데,
>   그 종결은 이 식을 §4-2 에 적어 놓고도 **채택값에 적용하지 않고 raw 판독값을 0° 로 박았다.**
>   node3 은 오차 6c 라 드러나지 않았고 node4 는 **193c** 로 드러났다.
> - ❌ **철회** — 「구값 `7871815 / 7840086` 은 출처 없는 값」 판정. 출처는
>   **Seer 가 실시간으로 내는 `0x607A` 조향 목표**이며, 실측 0° 와 **양 노드 모두 1 count 이내**로 맞다.
> - ⚠ 차이 193c = **0.0034°** — **거동상 무의미**하다. 안전 문제가 아니라 정본 정확성 문제다.
> - **`7882020 / 7859062` 는 홈(0°)이 아니다** — **펌웨어 GOZERO 상수**(호밍 후 정착 목표)이며
>   0° 에서 **+0.178° / +0.331°** 벗어나 있다. **호밍은 조향을 0° 에 정확히 놓지 않는다.**
>   이 둘을 모두 "조향 홈"이라 부른 것이 4주간 재실험 반복의 원인이었다.
>   **이번 홈 값 정정과는 별개 사안이다.**
> - `debt-007` 은 **종결**(2026-08-02), `debt-016` 은 **해결**. 「미판정 · 값 변경 금지」 서술은
>   더 이상 유효하지 않다.
> - Seer 각도와 CAN counts 는 **음의 상관** — 0° 역산은 `CAN + Seer° × 57344`.

- **Status**: Proposed — 2026-07-31. 사용자가 계층 방향(모터 계층)을 선택했고 본 ADR 로 사전승인을
  받는다. **구현 착수 전이며 실기 검증 0.** 최종 verdict 는 저자가 찍지 않는다(coding SOP 룰 7).

> ⚠ **이름 주의** — 본 ADR 의 `can_relay` 는 **ROS2 드라이버 패키지**
> (`src/Comm/CAN/can_relay/`)다. `Tools/Can_Relay/` 의 판다 펌웨어 프로젝트가 아니다
> (debt-015 참조).

## Context

### 계기

Python 으로 작성된 `can_relay` 를 C++ 로 포팅하기에 앞서 ROS2 인터페이스 설계를 점검하던 중,
사용자가 두 가지를 지적했다.

1. `cmd_vel` 구독의 QoS(VOLATILE)가 현재 모션과 어울리는가
2. `src/Control/Motion_Control/QD` 와 연동하려면 bicycle 모드와 맞물려야 하지 않는가

두 지적을 검증하기 위해 상류 원본 `kuks2309/TR_Nav_ros2_ws` (HEAD `ad7520981d500fa5881e548ef22fc92d0d7fe4a1`,
2026-07-31 얕은 클론)의 모션→모터 체인을 전수 추적했다.

### 사실 1 — 상류 체인의 모터 계약은 `cmd_vel` 이 아니다

```
9종 action server ─ WheelSetArray ─→ /motion/wheel_cmd/<action>
      ↓
trnav_motion_mux  ─ WheelSetArray ─→ /motor/wheel_cmd
      ↓
amr_motor_cmd_translator (SI → CiA402 raw)
      ↓  MotorCmdArray → /motor/low_cmd
amr_canopen_motor_driver (can_channel "can0")
      ↑  MotorStateArray ← /motor/low_state
```

근거(클론 트리 기준 경로):

- `src/Control/AMR-Motor/amr_canopen_motor_driver/src/amr_canopen_motor_driver_node.cpp:61-64`
  — `/motor/low_cmd` 구독(`MotorCmdArray`), `/motor/low_state` 발행(`MotorStateArray`)
- `src/Control/AMR-Motor/amr_motor_cmd_translator/src/amr_motor_cmd_translator_node.cpp:76,88-92`
  — `/motor/wheel_cmd`(`WheelSetArray`) 구독 → `/motor/low_cmd` 발행
- `src/Control/AMR-Arbitration/trnav_cmd_vel_mux/src/trnav_cmd_vel_mux_node.cpp:19,69`
  — Twist→Twist **중재만** 한다(내비 스택용)
- `grep -rn "cmd_vel" src/Control/AMR-Motor/` → **0건**

⇒ **`cmd_vel` 은 모터 계층에 닿지 않는다.** 모터 계층의 계약은 `MotorCmdArray` / `MotorStateArray` 다.

### 사실 2 — 축 배정이 이미 일치한다

| | TR_Nav `amr_motor_cmd_translator_qd.yaml` | 본 저장소 `config/can_relay.yaml` |
|---|---|---|
| 구동 | `motor_id_walk_front: 1`, `motor_id_walk_rear: 2` | `drive_nodes: [1, 2]` |
| 조향 | `motor_id_steer_front: 3`, `motor_id_steer_rear: 4` | `steer_nodes: [3, 4]` |

`MotorCmd.msg` 주석도 동일하게 못박는다 — `1=walk_front, 2=walk_rear, 3=steer_front, 4=steer_rear`.
can_relay 는 물리 배정상 이미 `canopen_motor_driver` 자리의 노드다. 인터페이스만 두 계층 위를 본다.

### 사실 3 — bicycle 모드와 현재 게이트는 배타적이다 (사용자 지적 확인)

`trnav_qd_kinematics/include/trnav_qd_kinematics/qd_bicycle_model.hpp` 의 `DualBicycleCommand`
주석이 수식을 직접 적는다:

```
omega = vx * (tan(delta_f) - tan(delta_r)) / L
```

`omega ≠ 0` 이려면 `delta_f ≠ delta_r` 이다 — **회전은 전·후 조향각이 다른 것이 정의다.**

반면 `can_relay/driver_node.py:182-187` 은 축별 조향각 편차가 `1.0°` 를 넘으면 지령을 거부한다.
⇒ **bicycle 모드가 만들어내는 모든 선회 지령이 원천 거부된다.**

기하로 독립 확인한 수치(본 저장소 config 값 `module_x [0.6039, -0.5961]`, 축간거리 1.2 m):

| 항목 | 값 |
|---|---|
| `wmax` 파라미터 | 0.3 rad/s |
| 실제로 통과하는 최대 \|wz\| (vx = vmax = 0.2) | 0.00291 rad/s |
| 도달 가능 비율 | 0.97% (약 103배 못 미침) |
| 최소 선회반경 | 68.8 m ( = 1.2 m ÷ 1.0° in rad, vx 무관 상수) |

영향 범위는 9종 액션 서버 중 **6종**(`QdBicycleModel` 사용: `mpc`, `mpc_reverse`, `yaw_control`,
`yaw_control_reverse`, `translate_forward`, `translate_reverse`). 통과 가능한 것은 전 축 동일각인
`crab_linear` 계열뿐이다.

기존 코드 리뷰는 이 사항을 **Low [품질]** 로 분류했다
(`docs/code_review/can_relay_ros2/2026-07-29.md:250-253`, "스핀·선회는 미구현이다"). 본 ADR 은
그 판정을 뒤집지 않되 **정량 근거를 추가**한다 — 내비게이션 스택 연동을 전제하면 "회전 불가"이므로
severity 재평가가 필요하다(→ Consequences).

### 사실 4 — QoS 는 현행 유지가 맞다

상류가 같은 값을 쓴다.

```cpp
// amr_motor_cmd_translator_node.cpp:73
auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable().durability_volatile();
// amr_canopen_motor_driver_node.cpp:59
auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();
```

**RELIABLE + KeepLast(10) + VOLATILE** — 본 저장소 Python 구현의 실측 QoS와 동일
(2026-07-31 `ros2 topic info -v` 확인). 검토 중 제기됐던 `depth 1` 안은 상류와 어긋나므로 **철회**한다.

### 사실 5 — 본 저장소에는 체인 상류 2노드가 없다 (제약)

```
[있음] 2WS/QD action server 9종  → /motion/wheel_cmd/<action>  (WheelSetArray)
[부재] trnav_motion_mux           → /motor/wheel_cmd
[부재] amr_motor_cmd_translator   → /motor/low_cmd  (MotorCmdArray)
[부재] amr_canopen_motor_driver
[있음] can_relay (cmd_vel 인터페이스)
```

근거: `find src -type d \( -iname '*mux*' -o -iname '*translator*' -o -iname '*canopen*' -o -iname '*arbitration*' \)`
→ **0건**. 저장소의 `sil_*.launch.py` 들은 `trnav_motion_mux`·`trnav_motion_supervisor`·
`translate_sim_odom` 을 참조하지만 그 패키지들이 트리에 없다.

⇒ **can_relay 만 고쳐서는 체인이 이어지지 않는다.** 상류 반입이 선행 조건이다.

## Decision

`can_relay` C++ 포팅의 ROS2 인터페이스를 **모터 계층**으로 내린다.

1. **구독**: `/motor/low_cmd` — `trnav_msgs/MotorCmdArray`, QoS `KeepLast(10).reliable()`.
2. **발행**: `/motor/low_state` — `trnav_msgs/MotorStateArray`, 동일 QoS.
3. **제거**: `cmd_vel` 구독, `motor_control.kinematics` 대여(`_load_kinematics`), 축별 조향각
   1.0° 편차 게이트, `vmax`·`wmax`·`module_x`·`module_y`·`enable_cmd_vel` 파라미터.
   역기구학은 모션 계층 소관이므로 본 패키지에서 사라진다(중복 IK 금지 원칙은 그대로 지켜진다 —
   빌려 쓰던 것을 **아예 안 쓰게** 되는 방향이다).
4. **존치**: 안전 계층 전부 — 조향 ±`steer_limit_deg` 클램프, NaN 거부, bit15 위치 신뢰 판정,
   워치독, 피드백 TTL, `~/engage`·`~/stop`·`~/home` 서비스, `estop` 구독(TRANSIENT_LOCAL),
   `diagnostics` 발행, 판다 heartbeat 계약, 단일 제어 스레드 구조.
5. **`joint_states` 발행은 존치**하되 부가 출력으로 격하한다(`robot_state_publisher`·RViz 용).
   모터 계층 계약은 `/motor/low_state` 다.
6. **모듈 경계는 유지한다**: `safety` / `protocol` / `link` / `backend` / `node` 4+1 계층을 그대로
   C++ 로 옮긴다. 계층 변경은 최상위 `node` 에 국한된다.

> ❌ **정정 2026-08-03 15:40 (위 4항 인라인) — 존치 서비스 목록에 `~/home_cancel` 이 빠져 있다**
> Python 구현의 서비스는 4개다: `~/engage`(191) · `~/stop`(192) · `~/home`(193) · **`~/home_cancel`(194-195)**
> (`src/Comm/CAN/can_relay/can_relay/driver_node.py`). `~/home_cancel` 은 진행 중 호밍을 SW 로 취소하는
> **명시 경로**로, 펌웨어 `seer_home_cancel_frames()` 가 두 조향축에 `0x60FB:04 = 0` 을 쓴다
> (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:312-316`, 사용자 취소 진입 `:330-338`).
> **C++ 포팅에서 함께 존치해야 한다** — 빠지면 호밍 취소 수단이 사라진다.
> ⚠ 단 GOZERO_W 단계 타임아웃(`:521-522`)은 취소 프레임을 내지 않는다(`ERR_GOZERO` 로 상태만 전이).

### 안전 클램프의 기준계 (본 결정의 핵심 부수 조항)

`MotorCmd` 는 **raw 단위**다(`target_vel` 0.1 rpm, `target_pos` pulse). 현재 `safety.py` 의 클램프는
SI 기준(`deg`, `mm/s`)이다. 계층을 내리면 클램프 기준계가 바뀐다.

**결정**: 클램프는 **raw counts 지점에 그대로 둔다**(`safety.steer_deg_to_counts` 의 설계 규칙 4 —
"조향 클램프는 counts 를 만드는 지점에 있다"). 수신한 `target_pos` 를 `steer_home_counts` 기준으로
deg 환산 → ±`steer_limit_deg` 판정 → 초과 시 클램프한 counts 로 송신한다. 즉 **상류가 무엇을 보내든
모터 계층에서 물리 한계가 강제된다**. 이는 기존 설계 의도(상위 계층에만 두면 다른 상위가 붙었을 때
보호가 사라진다)와 정확히 일치한다.

## Alternatives (기각)

- **현재 인터페이스(`cmd_vel`) 그대로 이식** — 84개 테스트 동등성 대조가 가장 깨끗하고 포팅 위험이
  가장 낮다. 그러나 QD/2WS 체인과 연결점이 0 이고 bicycle 선회가 계속 거부된다. **기각** — 포팅의
  목적이 "돌아가는 코드를 C++ 로 옮기는 것"만이 아니라 모션 스택 연동이므로.
- **can_relay 에 bicycle 모드를 추가** — 사용자 지적의 직관적 해법이나, bicycle 모델은 모션 계층
  소관이고 모터 계층까지 내려오면 이미 휠별 `{velocity, steering}` 숫자다. 모터 드라이버에
  기구학을 넣으면 저장소에 4번째 역기구학이 생긴다. **기각.**
- **두 인터페이스 병행**(`MotorCmdArray` 주경로 + `cmd_vel` 잭업 시험용) — 지령원이 둘이 되어
  배타 장치가 필요하고, debt-018(모터 구동 패키지 2개 동시 기동 방지 장치 부재)과 같은 부류의
  위험을 패키지 **내부**에 새로 만든다. **기각.** 잭업 시험은 `~/steer_deg`·`~/drive_mmps`
  직접 지령으로 이미 가능하다.
- **`WheelSetArray`(`/motor/wheel_cmd`) 를 직접 구독해 translator 역할까지 흡수** — 부재한 상류
  1노드를 줄일 수 있으나, SI→raw 환산(gear 20/265.5, `pulses_per_rev` 65536, `direction`,
  `steer_offset_deg`)이 본 패키지로 들어와 상류와 이중 소유가 된다. **보류** — Consequences
  ③의 선행 조건 결정에 종속시킨다.

## Consequences

### 이득

- QD/2WS 체인에 **drop-in** 으로 붙는다. bicycle 선회가 자동으로 통한다 — 축별 각이 다른 것이
  거부 조건이 아니라 정상 데이터가 되기 때문이다(별도 기능 추가 불요).
- 역기구학 대여가 사라져 `motor_control` 패키지 의존이 끊긴다. 조건부 `cmd_vel` 구독이라는
  까다로운 분기(`driver_node.py:145-154`)도 함께 사라진다.
- QoS·축 배정·메시지 타입이 상류와 일치하므로 SIL/HIL launch 를 그대로 재사용할 수 있다.

### 비용 / 남는 위험

① **테스트 자산의 절반이 재작성 대상이다.** 2026-07-31 실측 커버리지:
   `safety.py` 100% · `protocol.py` 99% · `backend.py` 82% · `link.py` 45% · `driver_node.py` 0%
   (84 passed, 전체 57%). `safety`·`protocol`·`backend` 의 84개 테스트는 계층 변경의 영향을 받지
   않으므로 **C++ 동등성 대조 근거로 그대로 쓸 수 있다.** 재작성 대상은 `driver_node` 계층뿐이고
   그쪽은 원래 커버리지 0 이다 — 잃는 회귀 그물이 없다.

② **`link.py` 의 `PandaLink` 경로(커버리지 45%)는 여전히 회귀 그물 밖이다.** 계층 변경과 무관한
   기존 부채이며 본 ADR 로 해소되지 않는다.

③ **상류 2노드(`trnav_motion_mux`, `amr_motor_cmd_translator`) 부재가 선행 조건이다.**
   > **⚠ 2026-08-07 후속 — 해소됨(원문은 이력 보존).** 상환계획 (a) 가 채택돼 두 노드가
   > `src/Control/Motion_Control/Common/` 으로 이식됐고(ADR `2026-07-31-motion-motor-chain-mux-translator-port.md`),
   > 이후 다른 세션이 `trnav_motion_supervisor` 와 전 체인 SIL 런치까지 올렸다
   > (`origin/main` `bf6ba92`·`1de6d9f`). `/motor/low_cmd` 발행자는 이제 실재한다.
   결정 후에도 `/motor/low_cmd` 를 발행하는 노드가 저장소에 없다. 세 갈래가 있으며 **본 ADR 범위
   밖**이다(별도 결정 필요): (a) 두 노드를 TR_Nav 에서 추가 이식, (b) can_relay 가 `WheelSetArray` 를
   직접 구독(Alternatives 4번), (c) 시험 단계에서는 `/motor/low_cmd` 를 수동 발행해 검증.

④ **`steer_offset` 이중 적용 위험.** 상류 `amr_motor_cmd_translator` 는 이미
   `steer_offset_front/rear_deg: -1.676` 과 `direction_*: -1` 을 적용해 raw 를 만든다. 본 패키지의
   `steer_home_counts` 가 같은 보정을 또 걸면 이중 적용된다. **환산 책임 경계를 실기 검증 전에
   문서로 확정해야 한다.** 관련 미해결 부채: debt-007(호밍 후 영구 오프셋 미판정),
   debt-016(홈 상수 하드코딩 계승).

   > ❌ **정정 2026-08-03**: debt-007 은 **종결**(2026-08-02), debt-016 은 **해결**됐다 —
   > 「관련 미해결 부채」로 읽히는 위 서술은 더 이상 유효하지 않다. 조향 0° 는 2026-08-03 실측으로
   > **`[7871815, 7840086]`** 확정(실측 0° 와 1 count 이내). 단 ④가 지적한 **환산 책임 경계
   > 미확정(debt-022)** 자체는 여전히 **미해결**이며, `steer_offset` 이중 적용 위험도 그대로다.

⑤ **값 정렬 필요.** 상류 `amr_canopen_motor_driver.yaml` 과 본 패키지 파라미터가 다르다:

   | 항목 | TR_Nav | can_relay |
   |---|---|---|
   | 지령 워치독 | `watchdog_timeout_ms: 200` | `cmd_timeout_s: 0.3` (300 ms) |
   | 피드백 만료 | `fb_stale_timeout_ms: 300` | `feedback_ttl_s: 1.0` |
   | 조향 홈 | `steer_home_offset_front/rear: -6500000` | `steer_home_counts: [7871815, 7840086]` |

   홈 값은 부호·기준계가 아예 다르다. **실측 없이 맞추지 않는다**(debt-007 상환계획 ③).

   > ❌ **정정 2026-08-03**: 위 표의 `steer_home_counts: [7871815, 7840086]` 은 **현재도 정본이다.**
   > 2026-08-02 에 `[7871810, 7839894]` 로 교체됐으나, 2026-08-03 11:44 실측(판다 SILENT·송신 0건,
   > 사용자 확인 Seer 표시 0°)에서 실측 0°(node3 **7,871,816** / node4 **7,840,087**)와 **1 count 이내**로
   > 맞음이 확인돼 원값으로 되돌아왔다. debt-007 이 종결됐으므로 「실측 없이 맞추지 않는다」의 근거
   > 조항은 소멸했다 — 이제 **실측된 값**이다. 상류 `-6500000` 과 부호·기준계가 다르다는 지적 자체는
   > 유효하며, 정렬 여부는 debt-022(미해결) 소관이다.

⑥ **severity 재평가 대상.** `docs/code_review/can_relay_ros2/2026-07-29.md:250-253` 의 Low 판정은
   본 ADR 의 정량 근거(최소 선회반경 68.8 m, `wmax` 도달률 0.97%, 액션 서버 6/9 영향)를 반영해
   재평가되어야 한다. 판정 권위는 code_review 소관이며 저자가 렌더하지 않는다.

⑦ **줄번호 드리프트 발견.** 위 리뷰가 인용한 `driver_node.py:196-201` 은 현재 `:182-187` 이다.
   리뷰 산출물 갱신 시 함께 정정한다.

### 부채 등록

본 ADR 로 새로 식별된 항목을 `docs/debt/registry.md` 에 등록했다(coding SOP §6 — coding 은 식별만,
등록·추적은 debt 소관).

- **debt-021** (기술) — 위 ③ 체인 상류 2노드(`trnav_motion_mux`, `amr_motor_cmd_translator`) 부재.
  상환계획에 (a)추가이식 / (b)`WheelSetArray` 직접구독 / (c)수동발행 세 갈래를 명시했다.
- **debt-022** (이해) — 위 ④ 조향 환산 책임 경계 미확정(`steer_offset` 이중 적용 위험).
  debt-007·debt-016 과 얽혀 있어 실측 대조 전까지 어느 쪽 값도 바꾸지 않는다.

## Rollback

**N/A 아님 — 실제 절차를 적는다.** 다만 되돌림 비용은 낮다.

1. Python 구현(`src/Comm/CAN/can_relay/can_relay/*.py`)은 **삭제하지 않는다.** C++ 포팅은 새 소스
   트리로 추가하고, 두 구현이 공존하는 동안 `setup.py` 의 console_script 는 그대로 둔다.
2. 되돌림 = launch 에서 실행체를 Python 노드로 되돌리고 C++ 실행체 등록을 `CMakeLists.txt` 에서
   제거. 영속 상태·스키마·펌웨어 변경이 없으므로 그 외 복구 작업은 없다.
3. **단, 판다 펌웨어·드라이브 파라미터는 본 ADR 범위 밖이며 건드리지 않는다.** 만약 시험 중
   드라이브 파라미터를 쓰게 되면 그것은 별도 비가역 변경이므로 별도 ADR 과 롤백 절차를 요구한다.
4. Python 구현 삭제 시점은 C++ 구현이 실기 검증을 통과하고 code_review 가 외부 verdict 를 렌더한
   **이후**로 미룬다(never-self-approve).

## 검증 상태 (정직 표기)

- **완료**: 상류 체인 추적(파일·줄 인용), 축 배정 대조, bicycle 수식 확인, QoS 실측 대조
  (`ros2 topic info -v`, mock 링크 기동), 기하 계산(선회반경·도달률), 저장소 상류 부재 확인.
- **미완**: C++ 구현 0줄. 실기 구동 0회. `/motor/low_cmd` 를 실제로 흘려 본 적 없음.
  상류 2노드 부재 해소 방안 미결정(Consequences ③).
- 본 ADR 의 `Status` 는 `Proposed` 이며, 구현·검증 후 `Accepted` 로 갱신한다.
