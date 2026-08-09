---
id: 2026-08-10-001
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - Tools/repo_tools/worktree_guard.py
  - docs/code_review/worktree-guard/2026-08-10.md
---

# 2026-08-10 07:30 (KST) — 링크드 워크트리에서 공유 트리의 `main` 을 밀어버렸다

## 무엇을 했는가

세션 산출물을 `main` 에 병합하라는 지시를 받고, 내가 만든 링크드 워크트리
`Big-AMR-ses-66e0baff-hl` 안에서 다음을 실행했다.

```bash
git checkout -q -B main origin/main     # ← 이것
git merge --no-ff -m "Merge branch 'session/66e0baff-homing-labels' …" session/66e0baff-homing-labels
git push -q origin main
```

병합과 push 는 의도대로 됐다(`d46347a` 가 `origin/main` 에 반영됨). 그러나 `checkout -B main`
이 **공유 워킹트리가 체크아웃 중인 `main` 브랜치 포인터를 4dfb626 → d46347a 로 이동**시켰다.
공유 트리의 작업 파일은 그대로인데 HEAD 만 40여 커밋 앞으로 가서, `git status` 가
**167건을 staged 변경·삭제로 보고**하는 상태가 됐다. 42개 세션이 공유하는 트리다.

정리 단계에서 내가 직접 발견해 `git reset --mixed 4dfb626` 으로 복구했다(index 백업 후,
`--hard` 아님). 파일 손실 0건 — 다른 세션들의 미커밋 작업(`gui.py`·`backend.py`·
`issues_and_fixes.md`·미추적 `test_kinematics.py` 등)과 총 미커밋 374건이 사고 전과 동일함을
확인했다.

## 무엇이 잘못이었나

- `docs/claude_guideline/git_workflow/git_workflow.md` §2-1 —
  「**⚠ 공유 HEAD 주의 — `git switch` 금지, `git worktree` 사용.** 다중 세션이 하나의
  워킹트리·하나의 HEAD 를 공유하므로 `git switch`/`git checkout -b` 로 브랜치를 바꾸면
  HEAD 가 **전역 이동**해 동시에 작업 중인 **다른 세션까지 그 브랜치로 끌려간다**.」
- 같은 §2-1 — 「`main` 반영(merge)은 **사용자가 수행**한다」. 사용자가 병합을 지시했으므로
  수행 자체는 승인 범위였으나, 방법은 위 금지 조항을 지켰어야 했다.
- `git_workflow.md` §1 「push 전 확인」 — 대상 저장소가 정확한지 확인하도록 요구한다.
  나는 push 대상(`origin/main`)만 확인하고 **그 명령이 공유 트리에 남긴 부작용은 확인하지
  않은 채** 「병합 성공」·「main push 완료」를 연속으로 선언했다.

## 사용자 지적

사용자 지적 전에 스스로 발견했다. 종료 점검으로 돌린 `git status` 에 `MM`·`D` 항목이
쏟아지는 것을 보고 즉시 진단·복구하고 보고했다. 이후 사용자가 「기록하고 종료 가능할까요?」
라고 물어 본 entry 를 작성했다.

## 원인 분석

가시성·강제력 점검:

- **규칙은 알고 있었고 같은 세션에서 읽었다.** `git_workflow.md` 를 이 세션에서 두 번 Read 했고
  (커밋 요청 시, 이식 요청 시), §2-1 의 경고문은 그 파일 안에서 굵게 강조된 유일한 ⚠ 블록이다.
  게다가 그 규칙을 지키려고 **일부러 worktree 를 만들었다** — 즉 규칙의 존재도, 목적도 알고
  있었는데 그 worktree **안에서** 금지된 조작을 했다. 「주입만으로는 막히지 않는다」
  (2026-07-28-005)의 재확인이다.
- **금지 목록의 형태가 실제 명령과 어긋났다.** 규칙이 이름을 댄 것은 `git switch` 와
  `git checkout -b` 다. 내가 쓴 것은 `git checkout -B`(대문자)였고, 그것은 "브랜치 전환"이
  아니라 "브랜치 재지정"이라 머릿속에서 다른 동작으로 분류됐다. **금지된 것은 명령 이름이
  아니라 「공유 중인 브랜치를 움직이는 것」인데, 규칙이 예시로 든 두 형태만 패턴 매칭했다.**
  같은 형태의 실패가 이 저장소에 이미 있다 — 2026-08-06-003 의 「내가 찾는 것과 패턴이 잡는
  것을 같다고 가정」.
- **부작용을 확인할 지점이 절차에 없었다.** 병합·push 는 각각 성공을 반환했고 나는 그
  반환값만 보고 다음 단계로 갔다. 공유 트리는 다른 디렉터리라 내 시야 밖이었고, 종료 점검이
  아니었다면 그대로 세션을 닫았을 것이다.
- **선행 사건의 재발 방지가 미설치였다.** 동종 사건 `2026-08-06-003`(타 세션 워크트리 삭제)이
  `status: open` 으로 남아 있고, 그 §재발 방지 후보 ②가 바로 「`git_workflow` 훅에 게이트를
  얹는다」였다. 그 구멍이 닫히지 않은 채 같은 계열의 두 번째 사고가 났다.

## 재발 방지

**`Tools/repo_tools/worktree_guard.py` 신설** — 문서 금지를 기계 판정으로 바꾸고, 위험한
명령을 **쓸 필요 자체를 없앤다**. 선행 사건 2026-08-06-003 의 기전도 함께 덮는다.

| 하위 명령 | 막는 것 | 판정 |
| --- | --- | --- |
| `check-branch <브랜치>` | 다른 워크트리가 체크아웃 중인 브랜치를 여기서 이동 | 해당 시 `exit 1` + 대안 안내 |
| `check-remove <경로>` | 이 세션 소유가 아닌 워크트리 제거(2026-08-06-003) | 소유 불명·타 세션이면 `exit 1` |
| `safe-merge <브랜치>` | — | `--detach` 임시 워크트리에서 병합 후 `HEAD:<base>` 로 push. **지역 브랜치를 만들지도 옮기지도 않는다** |

핵심은 세 번째다. `check-*` 는 또 하나의 "조심하라"에 그치지만, `safe-merge` 는 **금지된
명령 형태를 쓰지 않고도 목적을 달성하는 경로**라 이번 실패의 직접 원인(형태 패턴 매칭)이
성립할 여지를 없앤다.

검증 4건(전부 통과):

1. **사고 재현 검출** — 링크드 워크트리에서 `check-branch main` → 공유 트리 경로를 지목하며
   `exit 1`.
2. **음성 대조** — 아무도 잡고 있지 않은 브랜치는 `exit 0` (무조건 거부하는 도구가 아님).
3. **타 세션 워크트리** — `check-remove …-ses-c9ea2414 --session-id 66e0baff` →
   `session/c9ea2414-pose` 소유를 지목하며 `exit 1`.
4. **불변성** — `safe-merge --dry-run` 전후 `git rev-parse main` 이 `4dfb626` 로 동일 →
   이 경로에서는 사고 기전이 **구조적으로 재현 불가**.

설계·평가 인벤토리: `docs/code_review/worktree-guard/2026-08-10.md`
(coding.md §2 에 따라 코드 작성 **전**에 함수표를 만들었다 — 인벤토리 게이트가 이를 강제했다).

> 남는 것: `git_workflow` 훅에 `check-branch`·`check-remove` 를 PreToolUse 게이트로 얹으면
> 사람이 도구를 부르지 않아도 막힌다. 다만 그 훅 번들은 SSOT 가 외부 저장소라 다운스트림
> 직접 수정이 금지돼 있어(`git_workflow.md` §변경 절차) **사용자 승인 사항**이다.
> 이는 2026-08-06-003 의 재발 방지 후보 ②와 같은 항목이며, 본 entry 의 closure 는
> 그 훅 없이도 성립한다 — `safe-merge` 가 위험 경로를 대체하기 때문이다.
