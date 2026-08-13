# 적대 검토 의뢰서 — comment_check

외부 모델(codex·gemini 등)에 이 도구의 **적대 검토**를 시킬 때 그대로 넘기는 브리프다.
재사용을 위해 **수치를 여기 적지 않는다** — 수치는 `README.md` 의 실측 표가 유일한 출처다.
(여기에 숫자를 박으면 README 와 갈라져 낡는다. 이 도구가 막으려는 바로 그 부채다.)

사용 예:

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  "Tools/comment_check/REVIEW_BRIEF.md 를 읽고 그 지시대로 적대 검토를 수행하라."

gemini -m gemini-flash-latest --approval-mode yolo -p "$(cat Tools/comment_check/REVIEW_BRIEF.md)"
```

---

너는 **이 도구를 무너뜨리려는 적대적 검토자**다. 칭찬은 쓸모없다. 반증만 쓴다.
한국어로 답하라. **추정 금지** — 실행하고 출력을 붙여라.
저장소 파일은 수정하지 마라(임시 파일은 `/tmp`).

## 대상

- `Tools/comment_check/check_comments.py` — 검사기
- `Tools/comment_check/test_check_comments.py` — 회귀 테스트
- `Tools/comment_check/README.md` — 사용법·실측·한계 선언

## 배경

이 저장소의 2WS 모션 스택(`src/Control/Motion_Control/2WS/**`)에서 코드와 어긋나는 주석을
사람/에이전트가 라인 단위로 찾아 고쳤다(커밋 `6fb9663`, `2cf1971`). 이 도구는 그중
**기계로 재도출 가능한 부분만** 자동화한 것이다.

## 검증 대상 주장

`README.md` 의 **「실측」 절에 적힌 모든 수치**가 검증 대상이다. 먼저 그 절을 읽고,
각 수치를 아래 명령으로 **직접 재현**한 뒤 일치 여부를 판정하라. 불일치하면 그 자체가 결함이다.

```bash
python3 Tools/comment_check/test_check_comments.py                              # 회귀 테스트
python3 Tools/comment_check/check_comments.py src/Control/Motion_Control/2WS/   # 오탐 측정
python3 Tools/comment_check/check_comments.py Tools/comment_check/              # 자기 적용
git worktree add --detach /tmp/pre 6fb9663^                                     # 수정 전 트리 → 재현율
```

## 답해야 할 것 (근거는 반드시 `파일:줄` + 실행한 명령과 출력)

1. **거짓 통과** — 잡아야 하는데 조용히 지나가는 입력을 **만들어 실행해 보여라**.
   노릴 곳: `_strip_cxx_strings`·`_strip_py_strings`, `extract_comments`(C++ 블록/Python
   docstring/XML `<description>`), `RepoIndex.exists_path` 의 `endswith`,
   `qualified_exists` 의 `scope_files` 휴리스틱, `_eval_expr`, `RANGE_HINT_RE`, `_tolerance_for`.

2. **오탐** — 정상 주석인데 플래그되는 입력을 만들어라. README 의 오탐 0 주장을 깨라.

3. **억제 마커 악용** — `comment-check: ignore` 로 막아서는 안 될 것이 막히는가?
   저장소에서 이 마커의 현재 사용처를 전수 조사하고(`grep -rn`) 각각이 정당한지 판정하라.

4. **검사기 자신의 버그** — 인덱스 어긋남, 정규식 취약점, `eval` 안전성, 성능, 종료 코드,
   `--checks` 인자 처리.

5. **재현율 반증** — README 가 「기계로 재도출 불가」라 적은 유형이 실제로는 잡을 수 있는가?
   정답지는 `git show 6fb9663 --unified=0` · `git show 2cf1971 --unified=0` 의 `-` 줄
   (= 고치기 전의 틀린 주석)이다. **하나라도 찾으면 그 주장은 거짓이다.**

6. **저비용 신규 검사** — 있다면 정답지에서 **몇 건 잡는지 실제로 세어라**. 추정치는 받지 않는다.
   새 검사는 오탐도 함께 측정해야 한다 — 재현율만 올리고 오탐을 만드는 제안은 기각한다.

## 규칙

- 근거 없는 지적은 감점이다. 재현 명령과 출력을 함께 적어라.
- README 「외부 적대 검토에서 나온 것」에 **이미 적힌 항목**을 새 발견인 양 쓰지 마라 —
  재현 확인만 하고 상태(고침/미고침)가 정확한지 판정하라.
