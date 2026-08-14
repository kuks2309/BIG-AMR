# 2026-08-14 — line_follow 다자 리뷰 합의 결함 6건 수정 (CCG: Codex + Gemini + Claude)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: CCG(Claude-Codex-Gemini) · mux(multiplexer) · SIL(Software In the Loop) ·
> FSM(Finite State Machine) · PD(Proportional-Derivative)

- 사용자 지시: 2026-08-14 "/ccg 다시 코드 검토해봅시다" → "2자 이상 같은 결함에 대해서 먼저 수정"
- 리뷰 산출물: `.omc/artifacts/ask/codex-line-follow-review.md` ·
  `.omc/artifacts/ask/gemini-line-follow-review.md`
- 대상: `trnav_2ws_action_server` 의 `line_follow` · `trnav_2ws_interfaces` 액션 정의

**2인 이상이 같은 결함을 지목한 것만** 이번 배치에서 고쳤다. 단독 지적은 아래 「미처리」 참조.

## 고친 것 — 6건

### 1. 감속 정지가 안전 게이트를 우회해 서 있던 기체를 움직임 (Codex 치명 · Claude 재현)

`v_current`(속도 프로파일 상태)는 `TransientGuard` 의 `gate_blocked` 와 무관하게 계속 자랐고,
`rampToStop()` 은 그 값을 `speed_scale` 없이 그대로 발행했다. 조향축이 고장나 구동이 0 으로
묶인 상태에서 취소·타임아웃이 나면, 정지 루틴이 오히려 기체를 밀어낸다.

- 실제로 낸 몸체 속도 `v_body_cmd = v_current × speed_scale` 를 신설하고 감속 기준으로 삼음
- `gate_blocked` 인 주기에는 `v_current` 를 0 으로 되돌려 프로파일이 누적되지 않게 함

### 2. 라인 대기 시한을 준비 단계가 먹어치움 (Codex 치명 · Claude 지적)

`wait_line_timeout_sec`(기본 3 s)이 `execute()` 진입 시각을 기준으로 계산돼, mux 전환과 Phase 0
조향 정렬(한도 5 s)이 먼저 소진했다. 조향 이동은 실측 수 초가 걸리므로 라인이 보이기도 전에
`-9` 로 죽을 수 있었다. 기준을 **주 루프 진입 시각**(`wait_line_start`)으로 분리했다.

### 3. 노드 종료를 완주로 보고 (Codex 높음 · Claude 지적)

주 루프가 `while (rclcpp::ok())` 라 Ctrl-C·shutdown 으로 빠져나와도 성공 경로로 흘렀다.
`reached_goal` 플래그를 두고, 성공 조건으로 `break` 한 경우가 아니면 **`-12`(node_shutdown)**
로 abort 한다.

### 4. 감속률이 0 이하이면 정지가 끝나지 않음 (Gemini 치명 · Codex 보통)

`stop_decel ≤ 0` 이면 `rampToStop()` 의 속도가 줄지 않아 무한 루프가 되고, 그 사이 `ActionMutex`
를 쥐고 있어 취소·수동 지령까지 전부 거부된다. 이중으로 막았다:

- `reloadTuning()` 에 **값 범위 강제** — 감속률·율제한·시한 하한, 신뢰도·offset 정규화 범위,
  필터 창 정수 하한. NaN 도 하한으로 접힌다(`!(v >= lo)` 판정)
- `rampToStop()` 자체에 **10 s 예산**을 둬 파라미터와 무관하게 루프가 유한임을 보장

### 5. coast 가 "유지"하는 값이 실제 발행 조향이 아니었음 (Codex 높음 · Claude 확인)

`LOST_COAST` 는 `steer_cmd`(율제한 **전** 목표)를 유지했다. 소실 순간 목표가 25° 인데 실제
발행이 5° 였다면, 라인을 못 보는 동안에도 25° 를 향해 계속 꺾였다 — 곡률이 오히려 커진다.
`steer_hold`(방금 실제로 낸 조향)를 신설해 coast·정지가 그 값을 고정한다.

### 6. mux 전환 실패를 경고만 하고 주행 지속 (Codex 높음 · Gemini 높음)

전환에 실패하면 지령이 하류로 안 나가는데, 영상 폐루프라 오차는 계속 들어와 **한 번도 안
움직이고 `max_duration` 도달로 성공**을 보고했다. 기본 동작을 **`-13`(motion_source_unavailable)
abort** 로 바꾸고, mux 없이 도는 SIL·벤치를 위해 `line_follow_require_motion_source`(기본 true)
탈출구를 뒀다.

**부수**: 측정 스냅샷에 `header.stamp` 기준 goal 경계 필터를 넣었다(Codex 보통 · Gemini 높음).
직전 goal 이 남긴 프레임이 리셋 직후 새 수신시각을 달고 통과해 카메라 불일치(`-11`)를 만들던
경로다. 미분항도 **새 측정이 왔을 때만** 갱신하고 분모를 실제 측정 간격으로 바꿨다(Codex 높음 ·
Claude 지적) — 15~26 Hz 입력을 50 Hz 로 중복 삽입해 D항이 펄스가 되던 문제.

## 검증

| 항목 | 결과 |
| --- | --- |
| colcon 빌드 | `trnav_2ws_interfaces` · `trnav_2ws_action_server` 오류 0 |
| 단위 테스트 | 19 tests, 0 failures (무회귀) |
| 주석 검사기 | 5파일 불일치 0 |
| **mux 가드 실동작** | mux 미기동 상태에서 goal → **`-13`**, wheel 지령 **0건** (종전에는 2 s 주행 후 `status 0`) |
| [A] 정상 추종(SIL) | status **0** · 전륜조향 −3.48~0.00° |
| [B] 카메라 불일치 | **−11** |
| [C] 라인 소실 | **−9** (t=2.6 s) |
| [D] 후진 추종 | **0** · 전륜조향 +0.00~+3.48° |

[A] 의 최대 속도가 0.087 → **0.063 m/s** 로 낮아졌다. 이는 회귀가 아니라 **1번 수정이 동작하는
증거**다 — 스모크에는 조향 플랜트가 없어 조향 오차가 게이트 임계를 넘고, 그동안 속도 프로파일이
더는 누적되지 않는다.

## 미처리 — 단독 지적 (다음 배치)

| 결함 | 지목 | 심각도 |
| --- | --- | --- |
| `max_duration_sec` 가 준비·대기 시간을 포함해 **안 움직이고 성공** 가능 | Codex | 치명 |
| 인식 런치가 `line_seg_params.yaml` 을 싣지 않고 `flip_180` 를 안 넘김 — 설정이 죽어 있음 | Gemini | 치명 |
| 커브 감속이 `angle`·조향 포화를 무시 → 급커브에서 최고속 | Codex | 높음 |
| detached execute 스레드가 객체 수명 초과 (베이스 상속) | Codex | 높음 |
| `centerline` 이 짧은 수평 오검출도 valid 로 통과 → 즉시 최대 조향 | Codex | 보통 |
| `conf_threshold` 이중 존재로 제어 측 튜닝 무효 | Gemini | 보통 |
| `-3`·`-9` 코드가 서로 다른 원인을 뭉갬 | Gemini | 높음·보통 |
| `rampToStop` 중 feedback 미발행 | Gemini | 보통 |

**2번(인식 런치)은 치명이며 다음 배치의 첫 항목이어야 한다** — 내가 문서에 「실기 부호 확인 전
주행 금지」라고 적은 그 `flip_180` 이 런치 경로로는 도달하지 않는다.
