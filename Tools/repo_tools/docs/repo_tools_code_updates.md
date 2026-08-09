# repo_tools Code Updates

저장소 운용 스크립트(`Tools/repo_tools/`)의 수정 이력. coding.md §수정 이력 기록에 따라
**이력은 여기와 git commit message 가 담당**하고, 소스 주석은 현재 사실만 담는다.

## 2026-08-10 — `worktree_guard.py` 신설

- **무엇을**: 공유 `.git` 을 여러 세션이 나눠 쓰는 이 저장소에서 **남의 HEAD 를 건드리는 git
  조작**을 막는 도구. 하위 명령 3종 — `check-branch`(다른 워크트리가 잡은 브랜치 이동 거부),
  `check-remove`(이 세션 소유 아닌 워크트리 제거 거부),
  `safe-merge`(`--detach` 임시 워크트리에서 병합 후 `HEAD:<base>` push).
- **왜**: `git_workflow.md` §2-1 이 「⚠ 공유 HEAD 주의 — `git switch` 금지」로 명시 금지하지만
  **기계 강제가 없어** 두 사건이 실제로 났다.
  - `docs/claude-mistake/2026-08-10-001_shared-head-moved-from-linked-worktree.md` —
    링크드 워크트리에서 `git checkout -B main origin/main` 을 실행해 공유 트리의 `main` 이
    40여 커밋 이동, 유령 staged 167건 발생(복구 완료, 파일 손실 0).
  - `docs/claude-mistake/2026-08-06-003_removed-other-session-worktree.md` (open) —
    `git worktree remove --force` 를 경로 패턴으로 훑어 타 세션 워크트리 삭제.
- **설계 판단**: `check-*` 만으로는 또 하나의 "조심하라"에 그친다. 그래서 **위험한 명령 형태를
  쓸 필요 자체를 없애는** `safe-merge` 를 함께 넣었다 — 지역 브랜치를 만들지도 옮기지도 않으므로
  사고 기전이 구조적으로 재현되지 않는다.
- **검증 4/4**: ① 링크드 워크트리에서 `check-branch main` → 공유 트리를 지목하며 `exit 1`
  ② 무관 브랜치 → `exit 0`(무조건 거부 아님) ③ 타 세션 워크트리 `check-remove` → `exit 1`
  ④ `safe-merge --dry-run` 전후 `git rev-parse main` 동일.
  실사용 검증: 본 도구의 커밋 자체를 `safe-merge` 로 `origin/main` 에 올렸고, 그때 공유 트리
  `main` 은 `4dfb626` 불변·staged 0건이었다.
- **설계 인벤토리**: `docs/code_review/worktree-guard/2026-08-10.md`
  (coding.md §2 에 따라 코드 작성 **전**에 작성 — 인벤토리 게이트가 강제했다).
- **남는 것**: `git_workflow` 훅에 `check-branch`·`check-remove` 를 PreToolUse 게이트로 얹으면
  사람이 도구를 부르지 않아도 막힌다. 그 훅 번들은 SSOT(Single Source of Truth)가 외부
  저장소라 다운스트림 직접 수정이 금지돼 있어 **사용자 승인 사항**이다.

## 2026-08-06 — `branch_superseded.py` 신설 (이력 소급 기재)

- **무엇을**: 병합 전 게이트. 비교 기준을 공유 워킹트리로 고정하고, `.py` 는 `ast` 로 정의 심볼
  집합을 비교해 주석·docstring 을 읽지 않는다. 출력은 공유트리 전용(▲)/브랜치 전용(▼) 심볼.
- **왜**: `docs/claude-mistake/2026-08-06-001_merge-decision-from-comments-not-code.md` —
  병합 충돌을 **주석 문구 비교**로 판정하고 비교 대상을 `origin/main` 하나로 한정한 사건.
- **판정 수위**: 심볼 차이만으로는 개명·의도적 제거를 구분할 수 없어 **`미정 — 사람이 확인해야
  한다`(exit 1)** 로 낮췄다. 심볼 차이는 판정이 아니라 읽어야 할 목록이다.
