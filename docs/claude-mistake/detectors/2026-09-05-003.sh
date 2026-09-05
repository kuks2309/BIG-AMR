#!/usr/bin/env bash
# 검출자 2026-09-05-003 — 세션 워크트리가 append-only 기록 파일에서 **남의 줄을 지우는가**.
#
# 사건: 공유 트리의 낡은 issues_and_fixes.md 를 세션 워크트리에 통째로 복사해 타 세션이
#       main 에 올린 항목을 지웠다. 기록 파일은 덧붙이기만 한다 — 삭제는 자기 세션 작성분만 허용.
#
# 계약: 2026-09-05-003.sh <repo-root> [base-ref=origin/main] [session-id]
#   · 대상: 기록 파일(아래 RECORD_GLOBS). 코드 파일의 삭제는 보지 않는다.
#   · 범위: 스테이징이 있으면 index vs base, 없으면 base..HEAD.
#   · 삭제된 각 줄을 base 에서 blame 해 그 커밋 제목에 `session/<session-id>` 가 있으면 자기 것(허용).
#     session-id 를 안 주면 기록 파일의 모든 삭제를 보고한다.
#   · 위반 시 `파일:줄: 내용` 출력 + exit 1, 없으면 exit 0.
set -u
ROOT=${1:?repo-root}; BASE=${2:-origin/main}; SID=${3:-}
cd "$ROOT" || exit 2
git rev-parse --verify -q "$BASE" >/dev/null || { echo "base ref 없음: $BASE" >&2; exit 2; }
RECORD_GLOBS=(
  'docs/issues_and_fixes/*.md' 'docs/claude-mistake/*.md' 'docs/user_instructions/*.md'
  'docs/user_instructions/sessions/*.md' 'docs/debt/registry.md' '*/docs/code_updates/*.md'
  'docs/code_updates/*.md'
)
if ! git diff --cached --quiet; then MODE=cached; DIFF=(git diff --cached -U0 "$BASE"); else MODE=head; DIFF=(git diff -U0 "$BASE"...HEAD); fi
TMPF=$(mktemp); trap 'rm -f "$TMPF"' EXIT
while IFS= read -r file; do
  [ -n "$file" ] || continue
  # base 쪽 줄번호를 hunk 헤더에서 추적한다
  "${DIFF[@]}" -- "$file" | awk -v F="$file" '
    /^@@/ { split($2, a, ","); n = substr(a[1], 2) + 0; next }
    /^--- / || /^\+\+\+ / { next }
    /^-/ { print n ":" substr($0, 2); n++; next }
    /^\+/ { next }
    { n++ }' | while IFS= read -r line; do
      n=${line%%:*}; content=${line#*:}
      h=$(git blame -L "$n,$n" --porcelain "$BASE" -- "$file" 2>/dev/null | head -1 | cut -d' ' -f1)
      subj=$(git log -1 --format=%s "$h" 2>/dev/null)
      if [ -n "$SID" ] && [[ "$subj" == *"session/$SID"* ]]; then continue; fi
      echo "$file:$n: 삭제된 남의 기록 줄 ← ${h:0:7} ($subj): ${content:0:80}"
      echo FAIL >> "$TMPF"
    done
done < <("${DIFF[@]}" --numstat -- "${RECORD_GLOBS[@]}" | awk '$2 > 0 {print $3}')
[ -s "$TMPF" ] && { echo "✗ append-only 기록에서 남의 줄 삭제 ($MODE vs $BASE)"; exit 1; }
exit 0
