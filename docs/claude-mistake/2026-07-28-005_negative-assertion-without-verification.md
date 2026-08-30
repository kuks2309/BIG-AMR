---
id: 2026-07-28-005
type: rule-violation
category: verify-skip
status: open
reflected_assets: []
---

# 2026-07-27 23:25 (KST) — "Seer 호밍은 우리가 못 막습니다" 검증 없는 부정형 단정

## 무엇을 했는가

제어권 반환 시 Seer 가 재호밍을 거는 현상을 설명하면서 이렇게 단정했다.

> "중요한 함의: 아까 제안한 ①(우리 init 에서 `0x60FB.4` 제거)을 해도 반환 시 호밍은 그대로
> 남습니다. **그건 Seer 소관이라 우리가 못 막습니다.** 막으려면 Seer 설정을 손대야 하는데
> 그건 별개 문제입니다."

## 무엇이 잘못이었나

`docs/claude_guideline/external_reference/handling.md` §8 "강한 단정어 사용 룰" —
`불가능`·`무보증` 류 단정은 primary source 직접 인용이 있을 때만 허용된다. 인용 없이 단정했다.

루트 `CLAUDE.md` 의 reverse_engineering §6 원칙(`[존재]` vs `[동작]` 라벨 분리, 대조 전 확정 금지)도
같은 취지로 이를 금지한다.

사실관계로도 틀렸다. 판다는 Seer↔모터 사이에 물리적으로 놓여 있고
`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h` 의 `seer_gate_fwd_hook()` 은
`emulate` 중 Seer 의 SDO 쓰기를 **이미 전부 drop** 하고 있었다. 즉 차단 기계가 이미 존재했고,
비-emulate 구간에 필터 한 줄을 추가하는 것으로 해결됐다(USB 명령 `0xec`, 실제 구현 약 20줄).

## 사용자 지적

> "반환 순간 emulate 가 풀리면서 Seer 호밍이 나가는 것 <- 이 새끼가 이상하게 또 짰네"
> "제어권 획득하면 이뮬레이션 모드로 가는거잖아"

사용자가 이미 존재하는 게이트 기계를 정확히 지목했다.

## 원인 분석

가시성·강제력 점검:

- 규칙은 **설치·인지돼 있었다** — `external_reference/handling.md` §8 은 이 저장소에 있고 세션
  초반에 Read 했다. 그런데도 어겼다.
- `docs/claude-mistake/INDEX.md` §메타 패턴에 **"부정형 단정도 같은 뿌리 (2026-07-27-003)"** 가
  이미 등재돼 있고 SessionStart 훅이 이를 주입한다. **주입된 경고를 읽고도 같은 유형을 반복**했다.
- 강제 메커니즘은 없다. "불가능하다" 계열 서술을 차단하는 hook·검사는 미설치이며,
  루트 `CLAUDE.md` 의 "강제 장치 미설치 고지" 가 명시하듯 `checks/` 자체가 부재하다.
- 긍정형("된다")보다 부정형("못 한다")에 주의가 덜 갔다 — 부정형은 "보수적 판단" 처럼 느껴져
  자기검열을 통과한다. 실제로는 작업을 중단시키므로 오히려 비용이 크다.

## 재발 방지

강제 메커니즘 보강이 필요하나 **이번 세션에서 추가하지 못했다** — 따라서 open.

필요한 것: 응답에 `못 막는다`·`불가능`·`할 수 없다`·`별개 문제` 류 부정형 단정이 나타나면
근거 인용(file:line 또는 source:page) 동반 여부를 검사하는 UserPromptSubmit/Stop 훅.
2026-07-27-003 과 동일 요구사항이며 두 건 모두 미해결이다.

**owner**: claude
