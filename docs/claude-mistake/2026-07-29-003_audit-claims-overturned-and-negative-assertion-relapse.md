---
id: 2026-07-29-003
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - docs/claude_guideline/code_review/checks/review-claim-lint.py#S6
  - docs/claude_guideline/code_review/review.md#VERSION-1.4.0
  - docs/code_review/can_relay_ros2/2026-07-29.md#적대적-반대심문에서-뒤집힌-1차-감사-결론-기록-의무
  - src/Comm/CAN/can_relay/can_relay/protocol.py:148-158
  - src/Comm/CAN/can_relay/config/can_relay.yaml:26-31
  - docs/debt/registry.md#debt-030
---

# 2026-07-29 13:58 (KST) — 10인 감사 결론 5건이 심문에서 뒤집힘 + 같은 세션에서 부정형 단정 재발

## 무엇을 했는가

사용자 지시(sess:520bf3ab 09:56 "10명 투입하여 관련 코드 검토해주세요. 적대적 토론 진행")로
리뷰어 10인을 병렬 투입해 `motor_control` · `gui.py` · 판다 펌웨어 · 2WS 스택을 감사했다.
그 뒤 같은 지시의 후반부("적대적 토론")에 따라 반대심문 3인(D1 변호 · D2 반증 · D3 심판)을
투입해 1차 결론을 공격시켰다. 심문 결과로 1차 감사 결론 5건이 뒤집혔고, 그 정정본을 근거로
`src/Comm/CAN/can_relay` 패키지를 작성했다.

뒤집힌 5건:

| # | 1차 감사 주장 | 심문 판정 |
| --- | --- | --- |
| B1 | "`gui.py` 에 드라이브 브링업 시퀀스가 **한 줄도 없다**"(리뷰어 3) | **거짓** — 호밍 3-SDO 가 `gui.py:942-944` 에 실재. 없는 것은 *구동축* 브링업뿐 |
| B2 | "조향 홈 상수가 *호밍 전 기준계*라 실측과 다르다"(리뷰어 1·5) | **논리 반증** — `7882020` 은 호밍 **전**에도 47 Hz 정상 목표였다. 기준계 변경이 아니다. 게다가 `docs/debt/registry.md` 에 이미 등록된 사실이라 신규 발견도 아니다 |
| B3 | "NaN cmd_vel → 최대속도 **전진**"(리뷰어 2) | **방향 미입증** — 최대속도는 확정이나 `drive_sign` 이 미판정이라 방향은 단정 불가 |
| B4 | "**emulate 중에만** Seer guard RTR 이 forward 된다"(리뷰어 7) | **조건 누락** — `safety_seer_gate.h:182-184` 의 `else` 가 무조건 `bus_fwd=2`. emulate 무관 항상 |
| B5 | "`motor_control` 확장이 옳다(중복이다)"(리뷰어 8) | **반박됨** — 두 경로는 안전 모델이 배타적이며 병합 시 guard RTR 정지수단이 무력화된다 |

이어서 신설 패키지 문서를 쓰면서 **같은 실패를 다시 했다** — `protocol.py` 의
`drive_init_frames` docstring 과 `config/can_relay.yaml` 주석에 "gui.py 에는 이 시퀀스가 없다"는
부정형 단정을 **확인 명령 없이** 적었다(D1). 사용자 지시 "오늘 수정한 오류 검토해서 반영할 것"
(13:58)을 받고 자기 산출물을 재감사하는 과정에서 발견해 근거 명령을 병기했다.

## 무엇이 잘못이었나

어긴 규칙의 명시 인용:

- `docs/claude_guideline/code_review/review.md:281` §룰 8 — "**추측 금지** — grep, LSP, 실측 인용".
  B1·B4 는 원문 대조 없이 범위를 넓혀 단정했다.
- `docs/claude_guideline/code_review/review.md:274` §룰 1 — "Core 5 항목 누락 0 — 누락 = SOP 위반".
  B4 는 `else` 절을 읽지 않아 분기 전수가 누락됐다.
- `CLAUDE.md` §리버스 엔지니어링 등록 항목 —
  "`[존재]`(nm/disasm) vs `[동작]`(호출 도달성+배포자산 대조) 라벨 분리, 동작 주장은 배포자산
  대조 전 «확정» 금지". B3 은 `drive_sign` 미판정 상태에서 방향을 확정형으로 서술했다.
- `docs/claude-mistake/INDEX.md` §메타 패턴 — "부정형 단정도 같은 뿌리(2026-07-27-003)",
  "부정형 단정이 또 재발(2026-07-28-005)". D1 은 이 항목이 **SessionStart hook 으로 이 세션
  시작 시 주입되어 눈앞에 있었는데도** 발생했다.

## 사용자 지적

- 09:56 "**적대적 토론 진행**" — 이 지시가 없었으면 B1~B5 가 정본으로 남아 그 위에 패키지를
  지었을 것이다. 특히 B5(중복이니 확장하라)를 따랐다면 `motor_control` 의 유일한 문서보증
  정지수단(guard RTR 중단)이 판다 경유에서 조용히 무력화된 코드를 만들었을 것이다.
- 13:58 "**오늘 수정한 오류 검토해서 반영할 것**" — 이 지시가 없었으면 D1(검증 명령 없는
  부정형 단정)이 신설 패키지 docstring 에 그대로 남았을 것이다.

## 원인 분석

가시성·강제력 점검:

- **규칙은 알고 있었고 주입까지 됐다.** SessionStart hook 이 INDEX §메타 패턴의 "부정형 단정"
  항목을 이 세션 최상단에 주입했다. 그럼에도 D1 이 발생했다 — 2026-07-28-005 가 남긴
  "**주입만으로는 막히지 않는다 — 강제 검사가 필요하다는 증거**" 가 그대로 재확인됐다.
- **강제 검사가 이 실패 유형을 못 잡는다.** `docs/claude_guideline/code_review/checks/review-claim-lint.py`
  는 S1~S5 를 검출하지만 "부정형 단정에 검증 명령이 병기됐는가" 검사는 없다. 실제로 오늘
  리뷰 산출물은 이 lint 를 **FAIL 0건으로 통과**했고, 그 상태에서 D1 이 다른 파일(docstring·
  yaml 주석)에 살아 있었다. lint 대상이 `docs/code_review/*.md` 로 한정된 것도 공백이다.
- **B1~B5 의 형태는 저장소 메타패턴과 동일하다** — INDEX §메타 패턴의 "자기 산출물 감사가
  자기 결론을 뒤집는다(2026-07-28-011·012·013)". 다만 이번엔 **뒤집는 절차가 사용자 지시로
  같은 턴 안에서 실행돼 오보고가 사용자에게 도달하지 않았다.** 즉 메커니즘은 작동했으나
  **그 메커니즘의 기동 조건이 여전히 사용자 지시**라는 점이 닫히지 않은 구멍이다.
- 병렬 10인 구조의 부작용: 각 리뷰어에게 "부정형 단정은 확인 명령 병기" 를 프롬프트로 걸었으나
  **그 준수 여부를 기계 검사하지 않았다.** B1·B4 는 그 지시를 받고도 어긴 결과물이다.

## 재발 방지

강제 메커니즘 보강 — ①② 적용 완료, ③은 사용자가 채택하지 않아 부채로 이관했다.

1. **(적용)** 신설 패키지의 부정형 단정에 **실행한 확인 명령과 결과(0건)를 인라인 병기**하고
   주장의 **범위 한계**까지 적었다 — "gui.py 가 controlword 를 아예 안 쓰는 것은 아니다,
   `gui.py:942` 는 조향축 호밍 전용" 형태.
   → `src/Comm/CAN/can_relay/can_relay/protocol.py:148-158`,
     `src/Comm/CAN/can_relay/config/can_relay.yaml:26-31`

2. **(적용 — 강제 메커니즘, closure 근거)** `review-claim-lint.py` 에 **S6 — 검증 명령 없는
   절대형 부정** 검사를 추가하고 검사 대상을 **소스 주석·docstring 까지 확대**했다
   (`.md` 는 S1~S6, 그 외는 S6 만). 사용자 승인 2026-07-29.
   → `docs/claude_guideline/code_review/checks/review-claim-lint.py`,
     `docs/claude_guideline/code_review/review.md` VERSION 1.3.0 → 1.4.0

   **게이트가 즉시 실효를 증명했다** — 도입 직후 전수 검사에서 *같은 세션에 내가 쓴 코드*
   3곳을 잡았고, 원문 대조 결과 **주장 자체가 과장이었다**: "호밍은 시작하면 소프트웨어가
   멈출 수 없다" → 사실은 **본 구현에 취소 경로가 없을 뿐**이고, 펌웨어에는 실재한다
   (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:307-309`
   `seer_home_cancel_frames()` 가 `0x60FB:04=0` 송신). 3곳을 "불가능" → "미구현" 으로 정정했다.

   설계 조정 2건도 실측으로 확정했다(오탐이 남으면 게이트가 꺼지므로):
   - 근거 인정 범위를 리뷰 SOP 룰 8 과 동일하게 맞췄다(①도구 호출·결과 **②`파일:줄` 인용**).
     ①만 인정했을 때 기존 통과 산출물 `docs/code_review/can_relay_firmware/2026-07-28.md` 에
     신규 FAIL 3건이 생겼고 원문 대조 결과 **3건 전부 오탐**이었다.
   - 일반형 "할 수 없다"·"알 수 없다" 는 대상에서 제외했다 — 인용된 사실에서 끌어낸 *결과
     서술*이라 오탐이 된다(`docs/code_review/trnav-icp-odometry/2026-07-28.md:256` 실측).
     문서화된 실패 사례는 전부 *존재·차단능력* 형이다.

   회귀 확인: 사고 재현본 FAIL 1건 검출 / 근거 병기본 PASS / 저장소 리뷰 산출물 6종 전부 FAIL 0.

3. **(미채택 — 부채 이관)** 다중 에이전트 감사에 **적대적 반대심문 라운드를 표준 절차로 편입**
   하는 안은 사용자가 이번에 채택하지 않았다(2026-07-29 선택: S6 만). 오늘 그 라운드는 사용자
   지시로 돌았고 결론 5건을 뒤집었다 — **지시가 없으면 돌지 않는다**는 구멍은 그대로 남는다.
   → `docs/debt/registry.md` **debt-030** 으로 등록해 추적한다.
