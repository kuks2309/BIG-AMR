# ADR 2026-08-14 — 라인 추종 모션 `line_follow` 신설 (2WS 액션 서버, mux source 13)

- **Status**: Proposed — 2026-08-14 (사용자 지시로 착수. 최종 verdict 는 저자가 찍지 않는다 —
  `coding.md:89` never-self-approve)
- **대상**: `trnav_2ws_interfaces`(액션 1종 추가) · `trnav_2ws_action_server`(서버 1개 신설) ·
  `trnav_motion_mux`(소스 1개 등록)
- **선행**: `docs/adr/2026-08-13-line-following-ai-port.md` (인식 계층 — `/line/error` 생산자)

## Context

인식 계층은 이식이 끝났다 — `line_vision/line_seg_node` 가 `/line/error`
(`ai_msgs/LineError`: `detected`·`offset`·`angle`·`confidence`·`camera`)를 발행한다.
이 오차를 소비해 실제로 주행하는 제어 계층이 없다.

원본(`kuks2309/TR_3D_Nav_ros2_ws`)의 제어 계층은 **이식 대상이 아니다.** 두 스택의 하부가
다르기 때문이다:

| | 원본 | Big-AMR |
| --- | --- | --- |
| 기구 | 2WD 차동 | 인라인 듀얼스티어 2WS |
| 제어 출력 | `geometry_msgs/Twist`(v, ω) | `trnav_msgs/WheelSetArray`(바퀴별 속도·조향각) |
| mux 입력 | `cmd_vel_mux` ← Twist | `trnav_motion_mux` ← `/motion/wheel_cmd/<name>` |
| 액션 소속 | `amr_motion_control_2wd` 단일 프로세스 8번째 서버 | 액션마다 **독립 노드**(`amr_*_node`), `ActionMutex` 로 상호배제 |

따라서 원본에서 **가져오는 것은 제어 법칙과 소실 상태기계뿐**이고, 서버 골격은 이 저장소의
`yaw_control` 패턴을 따라 새로 쓴다.

원본의 실주행 근거(1.0 m/s, 실라인 약 10 m 완주, 평균 `|offset|` 0.050)는 **2WD 차동 기체**의
것이다. 조향 동특성이 전혀 다른 이 기체에는 그대로 옮겨오지 않는다 — 게인은 재조정 대상이다.

## Decision

### D1. 위치 — `trnav_2ws_action_server` 의 11번째 액션 노드

`src/{include}/line_follow/` 디렉터리를 추가하고 독립 실행파일 `amr_line_follow_node` 를 만든다.
기존 10개 액션과 같은 구조(`TwoWsActionServerBase` 상속 + `ActionMutex` + 자기 mux 소스 선택)라
상호배제·조향 상류 가드·인라인 기하 전제 검사·`/motion/last_result` 보고를 그대로 물려받는다.

### D2. mux source id = **13**

`trnav_motion_mux.yaml` 의 Reserved IDs 주석이 계약 정본이다(2026-08-09 확정). 현재
`0~9`·`12`·`40` 사용 중이고 `10`·`11` 은 stanley 예약이므로 **침범하지 않고 13** 을 쓴다
(`turn_reverse` 가 12 를 택한 것과 같은 근거). 전용 토픽 `/motion/wheel_cmd/line_follow`.

**짝 슬롯을 만들지 않는다.** 전진·후진이 별도 액션인 다른 쌍(`translate`·`turn`·`yaw_control`·
`mpc`)과 달리, 라인 추종은 **`reverse` 를 goal 필드로** 받아 한 액션이 둘을 처리한다. 근거:
방향 전환의 본질이 **어느 카메라를 보느냐**이고 그것은 인식 계층 파라미터(§D5)라 제어 코드가
갈라질 이유가 `vx` 부호 하나뿐이다. `turn`/`turn_reverse` 가 「`vx` 부호 3곳을 빼면 같은 코드」
라는 중복 비용을 이미 등재해 두었으므로(그 표의 미해결 3번) 같은 비용을 새로 만들지 않는다.

### D3. 제어 법칙 — 조향각 공간 PD (원본의 ω 공간 PD 를 옮긴 것)

원본은 차동 기체라 **각속도 ω** 를 직접 냈다. 2WS 는 조향각 δ 를 내고 자전거 모형이 ω 를
만든다(`ω = vx·(tanδ_f − tanδ_r)/L`). 따라서 같은 PD 를 **δ 공간**으로 옮긴다:

```
δ = −sign(vx) · ( Kp_off·offset_f + Kd_off·offset_f' + Kp_ang·angle )   [rad]
δ = clamp(δ, ±max_steer_deg)
v = max_linear_speed · (1 − slow_gain·|offset_f|)
```

- `offset_f` 는 이동평균(`RecursiveMovingAverage`) 필터 출력, `offset_f'` 는 그 차분
- **부호 유도**: `offset` + = 라인이 진행방향 기준 오른쪽 → 진행방향을 오른쪽으로 돌려야 한다
  → 세계좌표 `ω < 0` 필요. counter-steer 에서 `ω = 2·vx·tanδ_f/L` 이므로 전진(`vx>0`)이면
  `δ_f < 0`, 후진(`vx<0`)이면 `δ_f > 0`. 그래서 `−sign(vx)` 가 붙는다.
  (`yaw_control` 이 후진에서 `err_deg` 를 반전하는 것과 같은 규약이다.)
- 조향 분배는 `counter_steer` 고정 — `δ_r = −δ_f`. 인라인 듀얼스티어의 기본 자세다
- I 항은 **두지 않는다**. `turn` 표가 「항상 0 이어야 할 게인은 함정」이라 기록했고, 원본도
  PD 였다

### D4. 라인 소실 — 조향 유지 + 감속 coast (원본 설계 계승)

원본 사용자 제안(사람 운전 방식)을 그대로 가져온다. 순수 상태기계 `LostCoastFsm`:

```
WAIT_LINE ──(양질 검출)──> FOLLOWING ──(소실)──> LOST_COAST ──(재검출)──> FOLLOWING
    │                                                  │
    └─(wait_line_timeout 초과 → abort -9)              └─(coast_timeout 초과)──> STOPPING → abort -9
```

- LOST_COAST: **조향 지령 유지, 구동은 감속만**(가속 금지). 블라인드 이동 상한 ≈ `v·coast_s`
- 재개 조건: `detected && conf ≥ 임계 && |offset| < resume_max_offset` — 화면 가장자리
  오검출로 복귀하지 않도록
- `/line/error` **스트림 자체 두절**(기본 0.5 s)은 유예 없이 즉시 정지·abort(-10). 소실
  (라인이 안 보임)과 두절(인식 노드가 죽음)은 다른 사건이고 후자에 coast 를 주면 눈 감고 달린다

### D5. 방향 ↔ 카메라 — 제어는 **검증만** 하고 전환하지 않는다

사용자 요구는 「직진 시 전방, 후진 시 후방」이다. 카메라 선택은 인식 노드의 `direction`
파라미터가 수행하고, 액션은 **수신한 `LineError.camera` 가 진행 방향과 맞는지 검사**한다.
불일치면 즉시 abort(-11).

- 전진 goal 인데 `cam_r` 오차가 들어오면 **뒤를 보며 앞으로 달린다** — 조향 부호가 반대라
  라인에서 멀어진다. 조용히 달리느니 기동 실패가 낫다(기존 인라인 전제 검사와 같은 판단)
- **대안(액션이 인식 노드 파라미터를 원격 설정)은 배제.** 노드 간 파라미터 쓰기는 실패
  모드(서비스 미준비·경합·되돌림 책임)를 새로 만들고, 전환 중 오차 발행 공백이 그대로
  「입력 두절」로 읽힌다. 전환은 정지 상태에서 런치·운용이 하고 제어는 계약 위반만 잡는다
- `camera` 필드가 빈 문자열이면(구 발행자) 경고만 하고 통과 — 계약을 모르는 발행자에게
  없는 위반을 씌우지 않는다

### D6. 종료 조건

| 조건 | 결과 |
| --- | --- |
| `max_duration_sec` 도달 (0 = 무제한) | 감속 정지 후 success(0) |
| `max_distance` 도달 (0 = 무제한, 측위 경로장 적산) | 감속 정지 후 success(0) |
| cancel | 감속 정지 후 -1 |
| 라인 소실(대기 초과 / coast 초과) | 감속 정지 후 -9 |
| `/line/error` 두절 | 즉시 정지 후 -10 |
| 카메라 불일치 | 즉시 정지 후 -11 |
| 측위 두절·점프·TF 실패 | -4 / -5 / -6 (기존 코드 재사용) |
| 조향 미도달 지속 | -8 (`yaw_control` 의 `gate_blocked` 감시 재사용) |

거리는 **경로장 적산**(매 주기 `|Δp|` 합)이다. 라인은 곡선이므로 `yaw_control` 의 시작
방향 투영(`projection`)을 쓰면 곡선 구간에서 진행량을 과소평가한다.

### D7. 게인은 goal 이 아니라 yaml

`yaw_control` 은 게인을 goal 필드로 받지만, 라인 추종 게인은 **주행 사이 반복 조정**이
전제다(원본도 그래서 yaml 이었고, 실주행에서 기본값이 최적이었음을 확인하는 데 스윕이
필요했다). `line_follow_params.yaml` 에 두고 goal 마다 재적재해 `ros2 param set` 으로
재기동 없이 조정한다. goal 은 **임무 파라미터만**(속도·방향·한도) 받는다.

### D8. 의존성

| 의존성 | License | 취약점 | 대안(배제 사유) |
| --- | --- | --- | --- |
| `trnav_2ws_action_server` → `ai_msgs` (`LineError` 구독) | Apache-2.0 (자체) | 해당 없음 | 표준 msg 조합(필드 의미 불명확 — 인식 ADR §D2 에서 배제) |
| `trnav_2ws_interfaces` → (추가 없음) | — | — | 액션 자체는 표준 타입만 쓴다 |

⚠ **모션 패키지가 AI 인터페이스 패키지에 의존하게 된다.** 빌드 순서 제약이 생기지만
인터페이스 패키지 하나뿐이고 런타임 AI 노드(torch·ultralytics)에는 의존하지 않는다.
원본 ADR 도 같은 결합을 같은 근거로 수용했다.

## Consequences

- (+) 기존 10개 액션과 상호배제 자동 확보, 조향 상류 가드·인라인 전제 검사·측위 감시·
  `/motion/last_result` 보고를 그대로 물려받는다
- (+) 제어 수학·소실 FSM 이 순수 헤더라 ROS 없이 gtest 로 검증된다
- (+) 방향 전환이 goal 필드 하나 — 액션이 둘로 갈라지지 않는다
- (−) `line_vision` 의 `direction` 과 goal 의 `reverse` 를 **운용이 맞춰야 한다**. 틀리면
  abort(-11) 로 드러나지만 자동 정렬은 되지 않는다(§D5 의 의도된 대가)
- (−) 게인이 yaml 이라 여러 라인·속도 구간에서 goal 별로 다른 게인을 쓸 수 없다. 필요해지면
  goal 오버라이드 필드를 추가한다(현재는 근거 없음)
- (−) 조향 동특성이 원본(차동)과 달라 **원본 게인은 출발점일 뿐이다.** 실기 재조정 필요
- ⚠ 인식 모델이 타 기체 학습본이라 검출률이 보장되지 않는다(인식 ADR §D5). 제어 검증은
  인식 재학습 전까지 SIL·합성 입력에 머문다

## Rollback Plan

git 가역: `src/{include}/line_follow/` 삭제 + `trnav_2ws_interfaces/action/AMRMotionLineFollow.action`
삭제 + 양 패키지 `CMakeLists.txt`·`package.xml` 원복 + `trnav_motion_mux.yaml` 의 `source_13`
블록과 `source_ids` 목록 원복 + `colcon build --packages-select trnav_2ws_interfaces
trnav_2ws_action_server trnav_motion_mux` 재빌드. 영속 상태·스키마·펌웨어 비관여.
기존 10개 액션은 무변경이므로 되돌림이 그들에게 영향을 주지 않는다.
