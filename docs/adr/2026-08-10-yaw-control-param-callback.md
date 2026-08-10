# ADR 2026-08-10 — `yaw_control` 계열 파라미터 콜백 신설 (거짓 성공 제거)

- **Status**: Proposed — 2026-08-10 (**검증 전**. 최종 verdict 는 저자가 찍지 않는다 —
  `coding.md:88` never-self-approve)
- **Rollback**: 가역 — `git revert`. 영속 상태·스키마 변경 없음.
  ⚠ **외부 거동이 바뀐다** — 종전에 성공하던 `ros2 param set` 일부가 **실패로 응답**한다.
  되돌리면 종전(거짓 성공)으로 돌아간다.

## Context

`yaw_control` 에는 `add_on_set_parameters_callback` 이 **없다.** 모든 파라미터가 생성자에서만
읽히므로 `ros2 param set` 은 **`Set parameter successful` 을 반환하면서 거동을 바꾸지 않는다.**

2026-08-10 실측으로 확인했다 — 발산 탐지기 임계를 `param set` 으로 0.01° 로 낮추고 시험했으나
가드가 발화하지 않았다. 값이 바뀌지 않았기 때문이다. **현장에서 값을 조정했다고 믿고 시험하면
결과를 오독한다.**

같은 감사에서 **읽는 코드가 0건인 죽은 키 2개**도 나왔다 —
`yaw_control_max_steer_deg` · `yaw_control_i_max_deg`. 둘 다 **goal 필드로 넘어오는 값**이라
yaml 쪽 선언은 아무 의미가 없다.

## Decision

### D1. 콜백을 신설하고 **화이트리스트만 반영**한다

주기마다 멤버에서 읽히는 값만 hot-reload 대상이다.

```
double  max_timeout_sec · min_vx · walk_accel_limit · walk_decel_limit · steer_rate_limit
        heading_divergence_deg · gate_blocked_timeout_sec
int     heading_divergence_count
bool    enable_heading_divergence_guard · enable_localization_watchdog(다음 goal 부터)
```

범위를 벗어나면 `successful = false` 로 거부한다(`spin` 선례와 동일).

### D2. 화이트리스트 밖 키는 **명시적으로 거부**한다 — 이것이 본 ADR 의 핵심

`spin` 의 콜백은 화이트리스트에 없는 키를 **조용히 통과**시킨다. 그러면 거짓 성공이 그대로 남는다.
`yaw_control` 계열은 자기 네임스페이스(`yaw_control*_` · `transient_`)의 키 중 화이트리스트에
없는 것을 만나면 **거부하고 이유를 돌려준다**:

```
successful = false
reason = "<key> 는 생성자에서만 읽힌다 — yaml 을 고치고 노드를 재기동할 것"
```

대상: `pose_topic`(구독 생성 시점) · `localization_timeout_sec` · `position_jump_threshold`
(`LocalizationMonitor` 생성자) · `transient_*`(`TransientGuard` 생성자).

**「조용히 성공」보다 「시끄러운 실패」가 낫다.** 값이 안 먹는 것을 즉시 알 수 있다.

⚠ 다른 네임스페이스(기하·플랫폼 등 베이스 클래스 소관)는 **건드리지 않는다** —
이 노드가 판단할 근거가 없다. 그 범위의 거짓 성공은 남으며 별건이다.

### D3. 죽은 키 2개는 **삭제**한다

`yaw_control_max_steer_deg` · `yaw_control_i_max_deg` 를 yaml 에서 지운다.
설명 주석으로 남기지 않는다 — 2026-08-09 `spin_params.yaml` 과 같은 판단이다.
값은 goal 필드로 준다.

### D4. `yaw_control_reverse` 에도 동일 적용

접두만 `yaw_control_reverse_` 로 바뀐다. 저장소의 방향쌍 중복 비용을 그대로 따른다.

## Consequences

**얻는 것** — `param set` 의 성공/실패가 **사실과 일치**한다. 현장 튜닝 시 값이 먹었는지
즉시 알 수 있고, 안 먹는 키는 재기동이 필요하다는 사실이 응답으로 전달된다.

**비용** — 종전에 성공하던 set 호출이 실패로 바뀐다. 그 응답을 무시하고 성공을 가정하던
스크립트가 있으면 드러난다(드러나는 것이 목적이다).

**⚠ 미해결로 남기는 것**
- `spin`·`mpc`·`translate_*` 등 다른 액션의 화이트리스트 밖 거짓 성공은 그대로다.
- 베이스 클래스 소관 파라미터(기하·`control_rate_hz` 등)는 범위 밖이다.

## 검증 계획

```
1  빌드   colcon build
2  실행   (a) 화이트리스트 키 set → 성공 + 값 반영 확인(get 으로 재확인)
          (b) 비-화이트리스트 키(pose_topic) set → **실패** + 이유 문자열 확인
          (c) 범위 밖 값 set → 실패
3  회귀   정상 주행 1회로 거동 불변 확인
```

⚠ 최종 verdict 는 저자가 찍지 않는다(`coding.md:88`).
