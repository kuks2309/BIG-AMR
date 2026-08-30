
> ## ⚠ 강제 장치 미설치 고지 (2026-07-27 감사 확인)
>
> 본 문서와 `docs/claude_guideline/**` 는 여러 곳에서 `⟦CI:<id>⟧` 표기가 `checks/<id>.sh`(pre-commit·CI)로
> **기계 강제된다 / "못 속인다" / "차단"** 이라고 서술한다(예: 아래 coding §, debt §;
> docs/claude_guideline/coding/coding.md:22, docs/claude_guideline/debt/debt.md:17,35,72).
> **2026-07-27 확인 결과 본 저장소에는 그 강제 장치가 하나도 없다.**
>
> 근거(저장소 루트 `/home/nvidia/Project/Ford-CATL-AMR/Big-AMR` 에서 실행):
> - `find . -maxdepth 3 -name checks -type d` → 0건 (`checks/` 디렉터리 자체가 없음 → `checks/*.sh` 전부 부재)
> - `find . -maxdepth 4 -name check-mapping.sh` → 0건 (debt.md:72 가 요구하는 매핑 스크립트 부재)
> - `ls .pre-commit-config.yaml` → No such file or directory
> - `ls .github/workflows` → No such file or directory
> - `git config --get core.hooksPath` → 빈 값, `.git/hooks/` 는 `*.sample` 13개뿐(활성 훅 0)
> - `.claude/settings.json` 의 훅은 Claude 세션용 reminder/게이트이며 `checks/*.sh` 를 호출하지 않음
>
> **따라서 설치 전까지 `⟦CI:*⟧` 는 기계 강제되지 않는다 — 전 항목을 `⟦권고⟧` 로 취급하고,
> 준수 여부는 수동 검증 근거(명령·출력·파일:줄)를 남겨 증명한다.**
> (규칙 자체는 유효하며 삭제하지 않는다. 강제 장치 설치 시 이 고지를 갱신할 것.)

## 저장소 디렉토리 배치 (repo-specific)

**새 파일·새 디렉토리를 만들기 전 의무 확인** — 정본 규약은 [README.md §디렉토리 배치 규약](README.md) 이다.

- **ROS2 패키지**(`package.xml` 보유) → `src/<도메인>/…` (colcon 은 `src/` 아래만 발견)
- **비-ROS2 독립 도구**(colcon 불요, `python3` 즉시 실행)·펌웨어·현장 킷·벤치 → **`Tools/<도구명>/`**
- **UI** → 독립 `src/UI/` 를 만들지 말고 대상 패키지 아래 `…/ui/` 에 종속

### 루트 도구 폴더는 `Tools`(복수) 하나뿐 — 2026-07-28 병합 종결

저장소 루트에 `Tool/`(단수)·`tools/`(소문자)를 **새로 만들지 않는다.** 새 도구는 예외 없이 `Tools/` 아래.
2026-07-28 에 잔존 `Tool/` 껍데기(타 세션 OMC 상태 5파일뿐, git 추적 0건)를 삭제해 병합을 끝냈고,
루트 `.gitignore` 의 판다 펌웨어 규칙 4줄도 `Tool/…` → `Tools/…` 로 정정했다.

- **적용 범위는 이 저장소 경로뿐**이다. 타 PC(Personal Computer)·타 저장소 경로(amap-2, `kuks2309/CAN-Relay`, 이식 원본 등)는
  우리 규약이 미치지 않으므로 **그대로 둔다** — 고치지도, 주석을 달지도 않는다.
- **벤더 소스도 예외가 아니다.** 상류에서 들여온 디렉토리라도 이 저장소 안에 있으면 `Tools/` 로 맞춘다.
  2026-07-28 `orbbec_camera/tools/` → `Tools/` 개명(`CMakeLists.txt` 6줄 동반 수정, 빌드 검증).
  이 저장소는 서브모듈·상류 원격이 없어(`git submodule status` 0건, remote 는 `origin` 하나) merge 로
  되돌아올 경로가 없다 — 상류 신버전을 다시 들여올 때 그 시점에 재적용한다.
- **과거 문서의 `Tool/` 표기**: 특정 커밋 시점 경로 인용(예: "커밋 `fdc1c51` 의 `Tool/amr_test_gui/`")은
  역사적 사실이므로 **고치지 않는다.** 현재 저장소를 가리키는 인용만 정정 대상이다.
- 디렉토리 **이동·병합·개명** 시에는 지목된 경로만 보지 말고 `find . -type d -iname '<이름>*'` 로
  전수 조사한 뒤 대상 목록을 먼저 합의한다 — 누락 사례:
  [docs/claude-mistake/2026-07-27-004](docs/claude-mistake/2026-07-27-004_repo-wide-dir-survey-skipped.md).

> 강제 상태: **미설치**(`⟦권고⟧`). 위 "강제 장치 미설치 고지" 와 동일하게 수동 준수·근거 기록으로 지킨다.

<!-- kuks_agent_setup:coding -->
## 코드 작성 SOP (coding)

코드 작성/구현/수정 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것) — 바로 구현 직행 말고 먼저 [docs/claude_guideline/coding/coding.md](docs/claude_guideline/coding/coding.md) 를 Read 한 뒤 절차를 따른다 — 입구 작업분류(trivial fast-path) → 사전조사(함수표·전역변수표 read) → 사전승인(ADR) → 구현 → 검증(테스트·보안, never-self-approve) → 후속갱신(이중 기록). 강제는 `⟦CI:<id>⟧` ↔ `checks/<id>.sh`(pre-commit·CI)만 진짜, 그 외는 `⟦권고⟧`. **(2026-07-27 정정: 본 저장소에는 `checks/` · pre-commit · CI 가 모두 미설치 — 위 "강제 장치 미설치 고지" 참조. 현재 `⟦CI:*⟧` 는 기계 강제되지 않으므로 설치 전까지 전 항목을 `⟦권고⟧` 로 취급하고 수동 검증 근거를 남긴다.)** 명명·스타일은 `conventions.md`, 언어/포맷터는 `stack.md`, 도메인(ros2/embedded/numeric/concurrency/memory)은 트리거 시 `docs/claude_guideline/coding/domains/` 적용.

<!-- kuks_agent_setup:code_review -->
- "코드 리뷰"/"코드 분석" 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/code_review/review.md 를 Read 한 뒤 9단계 SOP(인벤토리[목적·함수표·전역표·의존성] + severity 평가 + 산출물 docs/code_review/<주제>/YYYY-MM-DD.md(루트 정본+패키지 병기 이중기록) + 플로우차트 .drawio 기록)를 따른다. 일반 탐색+요약으로 대체 금지. (도메인: docs/claude_guideline/code_review/domains/)

<!-- kuks_agent_setup:external_reference -->
- 외부 참조 문서(매뉴얼·datasheet·SDK·표준) 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/external_reference/handling.md 를 Read 한 뒤 보관(**루트 `References/`** — 복수·대문자 R 고정, 소문자 `references/`·단수 `reference/`·`Reference/` 금지)·인용(출처·페이지·버전)·원문 대조 검증 규칙을 따른다. 기억 의존 추정(환각) 금지. **타 저장소의 참조 폴더는 철자를 고치지 말고 저장소 이름을 접두로 붙여 인용**한다(예: `T-Robot_seer_gui/references/…`). (도메인: docs/claude_guideline/external_reference/domains/)

<!-- kuks_agent_setup:user_instruction -->
- 사용자 지시는 UserPromptSubmit hook 이 이 세션 전용 파일(docs/user_instructions/sessions/{session_id}.md)에 자동 기록하고 SessionEnd 에 단일 누적 로그(docs/user_instructions/user_instructions.md)로 병합한다(규칙: docs/claude_guideline/user_instruction/recording.md). 모델은 다른 세션 기록·병합 로그를 현재 작업 소스로 읽지 않는다(세션 격리).

<!-- kuks_agent_setup:sw_structure -->
- "SW 구조"/"구조 분석"/"클래스 관계"/"호출 관계" 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/sw_structure/structure.md 를 Read 한 뒤 파일 의존 그래프 + 클래스 다이어그램 + 시퀀스 다이어그램 + 연결 관계표 + 구조 관찰(산출물은 루트 정본 docs/sw_structure/<주제>/YYYY-MM-DD.md + 패키지 병기 <패키지루트>/docs/sw_structure/<주제>/ 이중기록 + ①②③ 다이어그램 .drawio(파일그래프·클래스·시퀀스, 박스·화살표 검증))을 작성한다. 결함 평가는 code_review 소관.

<!-- kuks_agent_setup:debt -->
## 부채 관리 (debt)

기술·이해·의도 부채/TODO/FIXME 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것) — 먼저 [docs/claude_guideline/debt/debt.md](docs/claude_guideline/debt/debt.md) 를 Read 한 뒤 절차로 **등록·추적·상환**한다 — 식별된 부채는 `docs/debt/registry.md` 에 등록(id·유형·위치·사유·상태·상환계획), 코드의 `TODO`/`FIXME`/`HACK` 은 debt id 를 참조(`# TODO(debt-042): ...`, 맨 마커는 `⟦CI:debt-marker⟧` 차단**〔예정〕**). **(2026-07-27 정정: "차단"을 수행할 주체가 없다 — `checks/debt-marker.sh` 는 물론 `checks/` 디렉터리 자체가 부재(`find . -maxdepth 3 -name checks -type d` → 0건), 활성 git hook·CI 워크플로 없음. 따라서 현재는 차단되지 않고 **수동 준수**가 필요하다. 규칙은 유지, 강제만 미설치.)** 식별은 작업 SOP(coding §2/§4/§5/§6)가, 등록·추적은 debt 가 소유. 미설치 시 식별만 주석/ADR 에 남김(graceful).

<!-- kuks_agent_setup:issue_fix -->
- 버그 수정 / 이슈 해결 / 빌드 실패 / 에러 진단 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/issue_fix/issue_fix.md 를 Read 한 뒤 진단→제안(승인)→구현→검증→기록(docs/issues_and_fixes/issues_and_fixes.md) 사이클을 따른다. 즉답 패치 직행 금지.

<!-- kuks_agent_setup:mistake -->
- Claude 의 실수·규칙 위반이 발생하거나 사용자가 지적하면(정정·재발 포함) **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/mistake/mistake.md 를 Read 한 뒤 type 판정(명시 규칙 1+ 위반이면 rule-violation 우선) → `docs/claude-mistake/YYYY-MM-DD-NNN.md` 에 entry 기록(frontmatter 5 필드 + 고정 5 절) → 재발 방지를 자산에 반영(`reflected_assets` 1+)까지 수행한다. 기록 없는 "다음부터 잘하기" 종결 금지.

<!-- kuks_agent_setup:git_workflow -->
- git 작업(commit/push/merge/PR/branch) 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/git_workflow/git_workflow.md 를 Read 한 뒤 따른다 — 협업 모드 확인(README `git 협업 모드: solo|team` 선언 우선, 미선언 시 사용자 문의·README 기록), 명시 staging(내 점유 파일만, `-A`/`.` 금지), 커밋 규약(`type(scope): subject` + `Session:` trailer + Co-Authored-By), **커밋 직후 즉시 safepush**(`hooks/git_workflow-safepush.sh` — push 미루기 금지), 다중 원격 전부 push. 타 세션 점유 파일은 편집하지 않는다(차단 시 충돌 프로토콜: 해제 대기 → 재독 → 편집, 또는 사용자 허락 후 override). 파일 수정은 Write/Edit 도구로만(Bash 파일쓰기 금지). 임의 커밋/푸시 직행 금지.

<!-- kuks_agent_setup:reverse_engineering -->
- 리버스 엔지니어링(reverse engineering)·재구현·구조 분석·검증 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/reverse_engineering/principle.md 를 Read 한 뒤 제1원칙(재구현 출력은 원본과 100% 동일, 원본 입력으로 양쪽 구동 후 비트 대조)과 §6 분석 보고 원칙(`[존재]`(nm/disasm) vs `[동작]`(호출 도달성+배포자산 대조) 라벨 분리, 동작 주장은 배포자산 대조 전 "확정" 금지)을 따른다. 추정·환각 금지.

<!-- kuks_agent_setup:session_workflow -->
- 세션 생애주기(시작→진행→종료)는 session_workflow 훅이 관리한다: 세션 목적 선언 게이트(`목적: …` 입력 시 훅이 자동 등록), 활성 세션 레지스트리·파일 충돌 경보, 종료 시 미커밋 잔여 handoff 박제(규칙: docs/claude_guideline/session_workflow/session_workflow.md). 모델은 목적 미등록 상태에서 실질 작업 전에 사용자에게 목적을 확인하고, 종료·커밋 보고는 이 세션 작업만 담되 타 세션·공유 트리 상태는 사용자 결정이 필요한 경보 1줄로 제한한다.
