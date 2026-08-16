# 2026-08-15 — line_follow 제어를 공통분/차이분 2입력으로 재구성 (heading 목표 옵션화)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: IK(Inverse Kinematics) · SIL(Software In the Loop) · CTE(Cross Track Error) ·
> PD(Proportional-Derivative) · FOV(Field Of View) · TF(Transform)

- 사용자 지시: 2026-08-15 「앞뒤바퀴 cte를 줄이고 앞뒤 바퀴 차이로 heading angle 조향하면되는데」
  → 「제어를 공통분/차이분 2입력으로 재구성하고 delta_heading 의 목표만 옵션으로 고르게 합니다 …
  이 방향으로 진행할까요? **진행**」 → 「완벽히 해주세요」
- 설계 근거: `docs/adr/2026-08-15-line-follow-common-diff-control.md`
- 선행: `code_updates/2026-08-15-line-follow-fix-reapply.md` · `code_updates/2026-08-15-line-sim-curved-line.md`

## 바꾼 것

### 1. 제어 코어 — 단일 조향값 → 조향 입력 3개

`line_follow_core.hpp` 의 `computeCommand()`(단일 `steer_rad`)를 `computeSteer()`
(`SteerInputs{theta_body, delta_cte, delta_heading, v_target, offset_used}`)로 교체했다.
`TwoWsCrabIK::compute(vx, theta_body, delta_cte, delta_heading)` 입력에 그대로 대응한다.

| 입력 | 구동원 | 역할 |
| --- | --- | --- |
| `theta_body` | `angle` × `kp_angle` | 진행 방향을 라인 접선에 정렬 |
| `delta_cte` | `offset_used` 의 PD | 횡오차 제거 (공통분 = crab) |
| `delta_heading` | `heading_mode` 가 정한 목표 | 차체 heading (차이분) |

서버는 `bicycle_model_->toIKResult(DualBicycleCommand{...})` 대신
`crab_ik_->compute(...)` 를 쓴다. Phase 0 직후 `crab_ik_->setInitial(0.0, reverse ? -1 : 1)`
로 기준을 고정한다. `bicycle_model_` 은 휠베이스 조회용으로만 남았다.

### 2. `heading_mode` — 모드 분기가 아니라 목표 선택

`AMRMotionLineFollow.action` 에 Goal `heading_mode`(0=FOLLOW_LINE·1=HOLD·2=ABSOLUTE)와
`target_yaw_deg`, Feedback `heading_error_deg`·`offset_used` 를 추가했다. 기본 0 이 종전
거동이라 기존 goal 은 영향이 없다. HOLD·ABSOLUTE 는 맵 기준 yaw 를 목표로 삼으므로
측위가 없으면 abort(−4) 한다.

### 3. 진행 방향 계수를 넣었다가 뺐다 — IK 가 이미 처리한다

`computeSteer()` 는 `reverse` 인자를 받지 않는다. `TwoWsCrabIK` 가 `−delta_heading` 을
**진행 기준 뒷바퀴**에 주므로(`qd_crab_inverse_kinematics.cpp:114`) 후진에서는 그 offset 을
받는 물리 바퀴가 바뀌고, 그 결과 yaw rate 부호가 진행 방향과 무관하게 `delta_heading` 을
따른다. 방향 계수를 곱하면 후진이 양의 되먹임이 된다.

시험 `CrabIkYawRateSignFollowsDeltaHeadingBothDirections` 가 실제 IK 출력으로 전진·후진
omega 가 같은 부호·같은 크기임을 확인한다(그래서 이 시험만 `trnav_2ws_kinematics` 를 링크한다).

### 4. 곡선 편향 보상 `curve_bias_gain`

전방주시는 곡선에서 완벽히 추종해도 `offset` 이 0 이 아니다(주시점이 원호에서 `d²/2R` 벗어남).
`offset_bias = angle · d/(2·hw)` 이므로 빼낸다. SIL 기하(d=1.0·hw=0.6)에서 0.8333.
커브 감속만은 **보상 전** 값으로 판단한다.

### 5. 차이분의 두 계수를 분리했다 — feedforward ≠ 되먹임

**측정으로 드러난 결함**: 처음엔 `delta_heading = kp_heading·(−angle)` 하나로 뒀는데,
곡선 SIL 에서 R=2 가 `−9`(라인 소실)로 끝났고 최대 heading 오차가 48.9° 까지 갔다.

원인은 `FOLLOW_LINE` 의 「오차」가 **없애야 할 편차가 아니라 곡률 그 자체**라는 데 있다 —
라인을 정확히 타고 있어도 `angle = −κ·d` 로 남는다. 필요한 앞뒤 차는 `2·atan(κL/2) ≈ κL`
이고 `κ = −angle/d` 이므로 계수는 **`L/lookahead` = 1.2** 여야 하는데 1.0 을 쓰고 있었다.
모든 반경에서 약 17 % 부족했다:

| R (m) | 필요 차이 `2·atan(κL/2)` | 계수 1.0 | 계수 L/d = 1.2 |
| --- | --- | --- | --- |
| 20 | 3.44° | 2.86° | 3.44° |
| 10 | 6.87° | 5.73° | 6.88° |
| 5 | 13.69° | 11.46° | 13.75° |
| 3 | 22.62° | 19.10° | 22.92° |
| 2 | 33.40° | 28.65° | 34.38° |

그래서 `k_curve_heading`(곡률 환산, `FOLLOW_LINE` 전용, D 항 없음)과
`kp_heading`·`kd_heading`(yaw 오차 되먹임, `HOLD`·`ABSOLUTE` 전용)을 분리했다.
`k_curve_heading = L/d` 는 `kp_angle = L/2d` 의 정확히 2배라, 곡선에서 crab 성분 0 의
순수 counter-steer 가 된다(`front = −rear`). 시험 3건이 이 관계를 건다.

### 6. 차이분 포화는 바퀴각 한계의 2배

`max_steer_rad`(25°)를 차이분에도 1배로 걸었더니 R=2 가 요구하는 33.4° 가 25° 로 잘렸다
(시험 `CurveFeedforwardMatchesRequiredCounterSteer` 가 검출). 차이분은 **바퀴각 두 개의 차**라
앞 +25°·뒤 −25° 인 순간에도 물리적으로 성립하므로 한계는 2배가 맞다. 실제 바퀴 한계는
하류 `TwoWsCrabIK` 가 Phase 0 기준 ±25° 로 건다.

### 7. 그 밖

- coast·정지가 유지하는 자세를 **진행 기준** 앞·뒤로 잡는다. 물리 바퀴 순서(W1,W2)로
  잡으면 후진에서 유지값이 `delta_heading` 만큼 어긋난다.
- 가드에 넣는 yaw rate 추정을 **실제로 낸 바퀴각**에서 뽑는다. 지령값을 쓰면 IK clamp 와
  조향 율제한이 깎아낸 몫만큼 과대평가된다.
- `validateGoal` 이 `heading_mode` 범위를 검사한다(미정의 값 거부).
- `steer_rate_limit` 0.35 → **0.8**. 근거는 수정된 미분항 기준 재실행한 스윕이다:
  0.15 이하에서 진동(반전 4회·peak 0.98), 0.25~1.2 평탄, 2.0 재악화. 무릎(0.25)에서 3.2배 여유.
  무릎은 1.0·0.3 m/s 에서 같았다 — 속도가 아니라 조향축 응답이 정한다.

## 검증

- 단위시험 `line_follow_core_test` **35건 PASS**(종전 30건 + 곡률 feedforward 3건 + 포화 2건).
- 곡률 SIL 스윕: 아래 「측정」 절.
- 빌드: `colcon build --packages-select trnav_2ws_action_server` 경고 0.

## 측정 — 곡률 스윕 (1.0 m/s, 8 m, 전진)

`avg|offset|` 은 **곡선에서 품질 지표가 아니다** — 완벽 추종이어도 전방주시 편향만큼 0 이
아니다. 그래서 실제 횡거리(로봇 위치 ↔ 원호)를 함께 잰다.

### 곡률별 (feedforward 계수 L/d = 1.2, `curve_bias_gain` 0.8333, `steer_rate_limit` 0.35)

| R (m) | status | 주행 (m) | **실제 CTE 평균 (m)** | 최대 (m) | 측정 `avg\|offset\|` | 필요 앞바퀴각 |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 0 | 8.017 | **0.0002** | 0.0003 | 0.0420 | 1.7° |
| 10 | 0 | 8.004 | **0.0004** | 0.0006 | 0.0840 | 3.4° |
| 5 | 0 | 8.014 | **0.0006** | 0.0009 | 0.1679 | 6.8° |
| 3 | 0 | 8.005 | **0.0003** | 0.0006 | 0.2795 | 11.3° |
| 2 | 0 | 8.002 | **0.0015** | 0.0022 | 0.4177 | 16.7° |
| 1.5 | 0 | 8.009 | **0.0045** | 0.0057 | 0.5531 | 21.8° |
| 1.3 | **−9** | 2.364 | 0.0211 | 0.1043 | 0.6814 | 24.8° |
| 1.2 | **−9** | 1.619 | 0.0207 | 0.0981 | 0.7145 | 26.6° |
| 1.0 | **−9** | 0.920 | 0.0166 | 0.0810 | 0.7853 | 31.0° |

R=1.5 까지 **밀리미터급**으로 원호를 탄다. 측정 `avg|offset|` 이 반경에 반비례해 커지는 것은
품질 저하가 아니라 **전방주시 편향 그 자체**다(= 0.8333·κ·d, 표의 값과 소수 셋째 자리까지 일치).

한계는 R ≈ 1.3~1.5 m 이고, 계산과 맞는다 — 순수 counter-steer 의 필요 바퀴각
`atan(κL/2)` 가 `TwoWsCrabIK` 의 ±25° clamp 를 넘는 지점이 **R = 1.287 m** 다.
R=1.3 은 여유가 0.2° 뿐이라 과도에서 넘어간다. **조향 각속도가 아니라 IK 의 소프트웨어
clamp 가 먼저 걸린다.**

### `steer_rate_limit` 0.8 확인 (yaml 값으로 곡선 재실행)

위 표는 종전 값 0.35 로 쟀다. 실제 배포값 0.8 에서 같은 곡률을 다시 재어 열화가 없음을 확인했다.

| R (m) | CTE 평균 @0.35 | CTE 평균 @**0.8** |
| --- | --- | --- |
| 5 | 0.0006 | 0.0006 |
| 2 | 0.0015 | 0.0015 |
| 1.5 | 0.0045 | 0.0047 |

곡선의 정상상태는 조향각이 **일정**해 각속도 요구가 0 이므로 이 파라미터가 제약이 되지 않는다.
직선 스윕이 정한 값을 곡선이 뒤집지 않는다는 뜻이다.

### 비교 — 계수를 고치기 전 (같은 조건, `k_curve_heading` 없이 `kp_heading` 1.0)

| R (m) | status | 주행 (m) |
| --- | --- | --- |
| 20 · 10 · 5 · 3 | 0 | 8.0 |
| 2 | **−9** | 2.993 |
| 1.5 | **−9** | 1.548 |

### 부수 결함 — 가상 센서의 원호 진행량이 반 바퀴에서 뒤집혔다

R=2 가 6.038 m 에서 `−9` 로 끝났는데 **그 순간 실제 CTE 는 2.2 mm** 였다. 제어가 아니라
`line_sim_sensor` 문제였다: `_measure_arc` 가 진행량을 `normalize_angle`(±π)로 접어
**π·R 을 지나는 순간 along 이 음수**가 되고 「구간 밖」으로 판정했다. 한계 거리 π·R 가
R=3(9.42 m)에서는 8 m 주행을 겨우 덮고 R=2(6.28 m)에서는 못 덮은 것이다.
[0, 2π) 로 접고 구간 상한을 `min(length, 원주)` 로 바꿨다(시험 4건 추가, 무회귀 확인).

## 측정 — `heading_mode` (0.5 m/s, 4 m)

직선 시나리오는 라인을 진행축에서 **왼쪽 0.25 m** 로 놓아 「옆으로 붙는」 동작을 만든다.
`yaw 편차` 는 목표(HOLD·FOLLOW_LINE 은 시작 yaw, ABSOLUTE 는 시작+10°) 대비 최대 편차.

| 시나리오 | mode | status | 주행 (m) | 종료 yaw | **목표 대비 yaw 편차(최대)** | max \|offset\| |
| --- | --- | --- | --- | --- | --- | --- |
| 직선(옆 0.25 m) | FOLLOW_LINE | 0 | 4.003 | 0.00° | **0.00°** | 0.413 |
| 직선(옆 0.25 m) | HOLD | 0 | 4.003 | 0.00° | **0.00°** | 0.409 |
| 직선(옆 0.25 m) | **ABSOLUTE +10°** | 0 | 4.001 | **9.71°** | 정착 후 2.80° | 0.412 |
| 곡선 R=5 | FOLLOW_LINE | 0 | 4.003 | **49.90°**(라인을 따라 돎) | — | 0.168 |
| 곡선 R=5 | **HOLD** | **−9** | 3.211 | **0.00°** | **0.00°** | 0.998 |

- **직선에서는 FOLLOW_LINE 과 HOLD 가 같다** — 둘 다 yaw 편차 0.00°. 재구성의 직접적인
  결과다: 횡오차를 **공통분(crab)** 이 없애므로 옆으로 붙는 데 차체를 돌릴 이유가 없고,
  라인이 평행하면 `angle ≈ 0` 이라 FOLLOW_LINE 의 차이분도 0 이다. 종전 counter-steer 는
  같은 상황에서 「틀었다 되돌리는」 동작을 했다. **모드 차이는 곡선에서 드러난다.**
- **ABSOLUTE 는 목표각으로 돌아 유지한다** — +10° 지시에 9.71° 로 끝났고 그 상태로 라인을
  계속 따라갔다(정착 후 편차 2.80°).
- **곡선에서 HOLD 는 「원리적 한계」가 아니라 조향 범위에 걸린다.** 차체를 고정한 채 곡선을
  따라가려면 crab 각이 **경로가 돈 만큼** 누적돼야 하는데, `TwoWsCrabIK` 가 Phase 0 기준
  ±25° 로 조인다. R=5 에서 25° 는 호 2.18 m 이고, 실제로 3.21 m 에서 `|offset|` 이 1.0 에
  닿아 소실됐다. 그동안 **yaw 편차는 0.00° 로 유지**됐다 — 유지가 실패한 것이 아니라
  누적 crab 이 소진된 것이다. 같은 곡선을 FOLLOW_LINE 으로 돌면 차체가 49.90° 돌며 완주한다.

## 측정 — 후진 회귀 (0.5 m/s, 4 m)

방향 계수를 뺀 것이 옳은지 거는 시험이다. 계수가 필요했다면 후진 곡선이 발산해야 한다.

| 시나리오 | status | 주행 (m) | **실제 CTE 평균 (m)** | 최대 (m) | 부호 반전 |
| --- | --- | --- | --- | --- | --- |
| 후진 직선(옆 0.10 m) | 0 | 4.010 | 0.0739 → 라인에 정착(3.87 s) | 0.1000 | 0 |
| 후진 곡선 R=5 | 0 | 4.007 | **0.0003** | 0.0004 | 0 |

후진 곡선의 추종 품질(0.3 mm)이 전진 R=5(0.6 mm)와 같다. **방향 계수는 필요 없다**는 것이
단위시험(IK omega 부호)과 폐루프 양쪽에서 확인됐다.

## 남은 것

- 실카메라 기하(주시거리·기준행 반폭)를 재어 `curve_bias_gain` 을 실기 값으로 정하는 일.
  현재 0.8333 은 **SIL 기하 전용**이다.
- 곡선에서 HOLD 를 길게 쓰려면 `TwoWsCrabIK` 의 ±25° clamp 를 라인 추종 전용으로 넓히는
  별건 결정이 필요하다(그 마진은 crab 횡이동의 ±90° wrap 진동 회피용이다).
- 실기 주행은 안전 확인 후 별도 진행.
