#!/usr/bin/env bash
# 음성 대조 표본 — 임시 저장소를 만들어 검출자가 (1) 남의 항목 삭제에 exit 1, (2) 덧붙이기에 exit 0,
# (3) 자기 세션 항목 삭제(session-id 제공)에 exit 0 인지 확인한다. 사용: make.sh [검출자 경로]
set -eu
DET=${1:-"$(cd "$(dirname "$0")/.." && pwd)/2026-09-05-003.sh"}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cd "$T"; git init -q -b main; git config user.email f@x; git config user.name f
mkdir -p docs/issues_and_fixes
printf '# 로그\n\n---\n\n## 2026-09-01\n\n### [Fix] A 세션 항목\n\n- **상태**: 완료\n' > docs/issues_and_fixes/issues_and_fixes.md
git add -A; git commit -qm "merge(session/aaaa): A 항목"
printf '## 2026-09-02\n\n### [Fix] B 세션 항목\n\n- **상태**: 완료\n' >> docs/issues_and_fixes/issues_and_fixes.md
git add -A; git commit -qm "merge(session/bbbb): B 항목"
fail=0
# (1) B(남의 것) 삭제 → exit 1
git checkout -q -b s1; sed -i '/B 세션 항목/,$d' docs/issues_and_fixes/issues_and_fixes.md; git add -A
if "$DET" "$T" main aaaa >/dev/null; then echo "✗ (1) 남의 항목 삭제를 못 잡음"; fail=1; else echo "✓ (1) 남의 항목 삭제 → exit 1"; fi
git reset -q --hard; git checkout -q main; git branch -q -D s1
# (2) 덧붙이기만 → exit 0
git checkout -q -b s2; printf '## 2026-09-03\n\n### [Fix] C\n' >> docs/issues_and_fixes/issues_and_fixes.md; git add -A
if "$DET" "$T" main aaaa >/dev/null; then echo "✓ (2) 덧붙이기 → exit 0"; else echo "✗ (2) 덧붙이기를 오탐"; fail=1; fi
git reset -q --hard; git checkout -q main; git branch -q -D s2
# (3) A(자기 것) 삭제 + session-id → exit 0 ; session-id 없이 → exit 1
git checkout -q -b s3; sed -i '/A 세션 항목/d' docs/issues_and_fixes/issues_and_fixes.md; git add -A
if "$DET" "$T" main aaaa >/dev/null; then echo "✓ (3a) 자기 항목 삭제(session-id) → exit 0"; else echo "✗ (3a) 자기 항목 삭제를 차단"; fail=1; fi
if "$DET" "$T" main >/dev/null; then echo "✗ (3b) session-id 없이 삭제를 허용"; fail=1; else echo "✓ (3b) session-id 없이 삭제 → exit 1"; fi
exit $fail
