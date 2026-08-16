# ADR 2026-08-15 — 라인 추종 제어를 공통분/차이분 2입력으로 재구성 (heading 목표를 옵션화)

- **Status**: Implemented(구현·SIL 검증 완료) — 2026-08-15. **최종 verdict 는 저자가 찍지
  않는다**(`coding.md:89` never-self-approve) — 검토자 승인 대기
- **대상**: `trnav_2ws_action_server`(line_follow 제어부) · `trnav_2ws_interfaces`(goal 필드) ·
  `line_sim_sensor`(곡선 라인 지원)
- **선행**: `docs/adr/2026-08-14-line-follow-2ws-action.md`(현행 단일입력 설계)

## Context

현행 `line_follow` 는 조향을 **한 개의 값**으로 낸다 — `δ_f = δ`, `δ_r = −δ`(counter-steer 고정).
그러면 차체는 항상 라인 접선을 따라 돌아가며, **heading 을 독립적으로 지정할 수 없다.**

사용자 요구는 「heading 각도를 유지하면서 주행」이었다. 이에 저자는 처음에 crab 을 **별도
모드**로 두자고 제안하고 「곡선에서는 원리적 한계가 온다」고 설명했다. **그 설명은 틀렸다.**
사용자 지적대로 crab 은 속도 벡터 자체를 회전시키므로 차체가 돌지 않아도 곡선을 따라갈 수
있고, 한계는 원리가 아니라 **조향 범위·조향 속도**라는 정량 제약이다.

그리고 올바른 일반형은 사용자가 제시한 분해다 — **앞뒤 공통분이 횡오차를 줄이고, 앞뒤
차이가 heading 을 세운다.** 이 저장소에는 그 형태가 이미 있다:

```cpp
// qd_crab_inverse_kinematics.cpp:62-63
double base_raw = theta_body + delta_cte;    // 공통분
double rear_raw = base_raw - delta_heading;  // 차이(rear offset)
```

즉 heading 유지/비유지는 **모드가 아니라 `delta_heading` 의 목표를 무엇으로 두느냐**의 차이다.

## Decision

### D1. 제어를 2입력으로 재구성한다 — 모드 분기를 만들지 않는다

카메라 신호를 두 입력에 나눠 싣는다:

| 입력 | 구동원 | 역할 |
| --- | --- | --- |
| `theta_body` | 라인 기울기 `angle` | 진행 방향을 라인 접선에 정렬 |
| `delta_cte` | `offset` 의 PD(Proportional-Derivative) | 횡오차 제거 |
| `delta_heading` | `target_yaw − robot_yaw` 의 PD | heading 을 목표로 세운다 |

`hold_heading` 이라는 별도 모드 분기를 만들지 않는다. **분기를 두면 두 벌의 제어 경로가
생겨 검증도 두 벌**이 되고, 실제 차이는 `delta_heading` 의 목표 하나뿐이다.

### D2. heading 목표는 goal 옵션 — 3가지

```
uint8   heading_mode   # 0=FOLLOW_LINE(기본, 현행 동작) · 1=HOLD(고정) · 2=ABSOLUTE(지정각)
float64 target_yaw_deg # heading_mode=2 에서만 사용. 1 은 goal 수락 시점의 yaw 를 잡는다
```

- `FOLLOW_LINE`: heading 목표 = 라인 접선 방향(= 현행 counter-steer 와 같은 거동)
- `HOLD`: goal 수락 시점의 yaw 를 고정 목표로
- `ABSOLUTE`: `target_yaw_deg` 를 고정 목표로

기본값 0 이므로 **기존 goal 은 거동이 바뀌지 않는다**(하위 호환).

### D3. IK 는 `TwoWsCrabIK` 를 쓴다 — 새 기구학을 만들지 않는다

이미 공통분/차이분 형태이고 `crab_linear` 로 실기 검증된 코드다. 새로 쓰면 같은 것을 두 벌
두게 된다.

⚠ **주의 — heading 권한이 자세에 의존한다.** 그 파일의 주석(`:56-61`)이 crab 횡이동
(base steer ≈ 90°)에서는 `omega ∝ Δ·cos(base)` 이고 `cos(89.3°)=0.012` 라 **heading 보정
권한이 거의 0** 이라고 기록해 두었다. 라인 추종은 base 가 0° 부근(전진)이라 `cos(0°)=1` 로
권한이 최대일 **것으로 계산되지만 이는 미검증 추론**이며, SIL(Software In the Loop)로 확인한다.

### D3-1. `delta_heading` 에 진행 방향 계수를 곱하지 않는다

앞뒤 차이분은 전진·후진에서 부호를 뒤집어야 할 것처럼 보이지만 **그렇지 않다.**
`TwoWsCrabIK` 는 `−delta_heading` 을 **「진행 기준 뒷바퀴」**에 주고(`qd_crab_inverse_kinematics.cpp:114`,
`w2_is_rear = (front_dir > 0)`), 후진이면 그 뒷바퀴가 물리 W1 로 바뀐다. 그래서

```
omega = vx_body · (tan δ_W1 − tan δ_W2) / L
  전진: δ_W1 = base, δ_W2 = base − Δh  →  omega ≈ (+|v|)·(+Δh)/L
  후진: δ_W1 = base − Δh, δ_W2 = base  →  omega ≈ (−|v|)·(−Δh)/L
```

**두 경우 모두 yaw rate 부호가 `Δh` 를 따른다.** 여기에 방향 계수를 곱하면 후진이 양의
되먹임이 되어 heading 이 발산한다. 그래서 `computeSteer()` 는 `reverse` 인자를 아예 받지
않는다 — 진행 방향은 IK 의 `vx` 부호와 위 뒷바퀴 지정이 전담한다.

계약은 시험이 건다: `line_follow_core_test.cpp` 의 `CrabIkYawRateSignFollowsDeltaHeadingBothDirections`
가 실제 `TwoWsCrabIK` 출력으로 전진·후진 omega 가 **같은 부호·같은 크기**임을 확인한다.

### D3-2. 전방주시 곡선 편향을 뺀다 — `curve_bias_gain`

전방주시(lookahead) 방식은 곡선에서 **완벽히 추종해도 `offset` 이 0 이 아니다.** 주시점이
원호에서 `d²/2R` 만큼 벗어나기 때문이다(d = 주시거리, R = 반경). 이를 오차로 보고 없애려
들면 과조향한다. 같은 상태에서 `angle ≈ −κ·d` 이므로 편향은 `angle` 에 비례한다:

```
offset_bias = angle · d / (2 · half_width)      # half_width = 기준행 반폭(정규화 분모)
```

SIL 기하(d=1.0 m, hw=0.6 m)에서 계수는 **0.8333**. 이 값을 빼면 남는 것이 진짜 횡오차다.
곡선을 따라가는 조향은 `angle` 항이 담당하고, 그 기하학적 정답은

```
kp_angle = L / (2·d) = 1.2 / 2.0 = 0.6
```

으로 **현행 값과 이미 같다**(우연이 아니라 원본 2WD 게인이 같은 기하를 갖고 있었다).

이 보상이 필요한 근거는 실측이다 — 보상 전 컨트롤러는 완벽 추종 상태에서조차
R=5/3/2/1.5 에 대해 `offset` 이 −0.165/−0.270/−0.393/−0.505 로 읽혀, R=2 에서 **필요 조향
16.7° 자리에 27.1° 를 지령**해 포화했다. 커브 감속만은 **보상 전** 값으로 판단한다 —
편향이 큰 곡선일수록 실제로 느려야 하기 때문이다.

### D4. 곡선 라인을 SIL 에 넣는다 — 한계를 재기 위해

`line_sim_sensor` 의 `LineSegment` 에 `curvature`(1/m, + = 좌선회)를 추가한다. 0 이면 현행
직선과 완전히 같다(기존 시험 22건 무회귀).

측정 대상은 **어느 제약이 먼저 걸리는가**다:

| 후보 제약 | 값 | 성격 |
| --- | --- | --- |
| 조향 범위 | `TwoWsCrabIK` 의 Phase 0 기준 **±25°** clamp | **소프트웨어 마진**(wrap 진동 회피용). 물리 한계는 상류 113.32°·하류 115° |
| 조향 각속도 | 지령 율제한 0.8 rad/s(46°/s) vs 플랜트 57.1°/s. 필요량 `dβ/dt = v·κ` | 하드웨어·설정 혼합 |
| 인식 기하 | 라인이 화면에서 기울면 `fit_centerline` 주방향 판정·기준행 교차가 나빠진다 | 센서 |

곡률 스윕으로 세 후보의 발현 순서와 한계 곡률을 뽑는다.

### D5. 차이분의 포화는 바퀴각 한계의 **2배**

`Gains::max_steer_rad`(25°)를 차이분에도 1배로 걸면 R=2.7 m 보다 조인 곡선이 요구하는
`2·atan(κL/2)` 를 낼 수 없다. 차이분은 **바퀴각 두 개의 차**이므로 앞 +25°·뒤 −25° 인
순간에도 성립한다 — 한계는 2배다. 실제 바퀴 한계는 하류 `TwoWsCrabIK` 가 Phase 0 기준
±25° 로 건다(그 값이 곡률 한계를 정한다 — 아래 표).

### D6. 곡률 한계는 IK 의 ±25° 가 정한다 (계산 + SIL 실측 일치)

순수 counter-steer(crab 성분 0)에서 필요 바퀴각은 `δ = atan(κL/2)` 이므로

| 제약 | 조건 | 한계 반경 |
| --- | --- | --- |
| `TwoWsCrabIK` ±25° clamp | `atan(κL/2) ≤ 25°` | **R ≥ 1.29 m** |
| 인식 FOV(주시 1.0·반폭 0.6) | `\|offset\| = κ·d²/(2·hw) ≤ 1` | R ≥ 0.83 m |
| 조향 각속도 | 정상 곡률에서는 정상상태라 요구량 0 | 진입 과도에서만 |

즉 **조향 각속도가 아니라 IK 의 소프트웨어 clamp 가 먼저 걸린다.** 그 clamp 는 crab
횡이동의 ±90° wrap 진동을 막으려는 마진이지 물리 한계(상류 113.32°)가 아니므로, 더 조인
곡선이 필요하면 라인 추종 전용으로 넓히는 것이 별건 결정으로 가능하다.

## Consequences

- (+) heading 유지가 **모드가 아니라 목표 설정**이 되어 제어 경로가 하나로 유지된다
- (+) `TwoWsCrabIK` 재사용 — 새 기구학·새 검증 불요
- (+) 기본값이 현행 거동이라 하위 호환 — 단 **거동 자체는 달라진다**(아래)
- ⚠ **직선에서 옆으로 붙는 방식이 바뀐다.** 횡오차를 공통분(crab)이 없애므로 차체를 돌리지
  않는다. 종전 counter-steer 는 「틀었다 되돌리는」 동작이었다. SIL 실측으로 라인이 평행하면
  FOLLOW_LINE 과 HOLD 가 **같은 거동**(yaw 편차 0.00°)이고, 두 모드의 차이는 곡선에서만
  드러난다(R=5·4 m: FOLLOW_LINE 49.90° 회전 완주 vs HOLD 0.00° 유지·3.21 m 에서 crab 소진)
- (−) 제어 입력이 1개 → 3개로 늘어 튜닝 파라미터가 는다(`delta_cte` PD + 곡률 feedforward
  + `delta_heading` PD). 다만 셋 중 둘(`kp_angle`·`k_curve_heading`)은 **기하가 값을 정하므로**
  튜닝 대상이 아니다
- (−) `TwoWsCrabIK` 의 ±25° clamp 가 **곡률 한계를 정한다**(R ≥ 1.29 m, 계산·SIL 일치).
  더 조인 곡선이 필요하면 라인 추종 전용으로 넓히는 별건 결정이 필요하다
- (−) 곡선 편향 계수는 **카메라 기하에 종속**이다. SIL 값 0.8333 은 주시 1.0 m·반폭 0.6 m
  기준이므로 실카메라의 주시거리·기준행 반폭을 재기 전에는 실기에 그대로 쓸 수 없다
- ⚠ `steer_rate_limit` 0.8 은 **직선 스윕**으로 정했다. 곡선에서는 정상상태 요구 각속도가
  0 이라 제약이 되지 않으나, 진입 과도는 별도로 재야 한다

## Rollback Plan

git 가역: `line_follow_action_server.{hpp,cpp}` 의 제어부 원복 + `AMRMotionLineFollow.action`
의 필드 2개 삭제 + `line_sim_sensor` 의 `curvature` 필드 삭제 + 재빌드. `heading_mode` 기본값이
현행 거동이므로 **롤백 전에도 기존 goal 은 영향을 받지 않는다.** 영속 상태·스키마·펌웨어 비관여.
