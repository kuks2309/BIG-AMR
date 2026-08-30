#!/usr/bin/env python3
"""session_workflow-state-guard.py 회귀 시험.

실행: python3 docs/claude_guideline/session_workflow/hooks/test_state_guard.py
훅을 실제 서브프로세스로 띄우고 stdin JSON 을 먹여 stdout 계약(ask / 무출력)을 검증한다.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "session_workflow-state-guard.py")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

ASK, PASS = "ask", "pass"

CASES = [
    # (기대, 라벨, 명령, tool_name)
    (ASK, "실제 위반 재현 — save_session 직접 호출",
     'python3 -c "import session_state as ss; ss.save_session(root, sid, meta)"', "Bash"),
    (ASK, "상태 파일 rm (handoff 아님)",
     "rm .git/session_workflow/active/8fde06da.json", "Bash"),
    (ASK, "리다이렉션 쓰기",
     'echo "{}" > .git/session_workflow/active/abc.json', "Bash"),
    (ASK, "상태 모듈 소스 sed -i",
     "sed -i s/a/b/ docs/claude_guideline/session_workflow/hooks/session_state.py", "Bash"),
    (ASK, "복합 명령 중 한 세그먼트가 쓰기",
     'cd /tmp && python3 -c "import session_state; session_state.save_session(1,2,3)"', "Bash"),
    (ASK, "cp 로 상태 파일 덮어쓰기",
     "cp /tmp/x.json .git/session_workflow/active/abc.json", "Bash"),

    (PASS, "cat 읽기",
     "cat .git/session_workflow/active/8fde06da.touched", "Bash"),
    (PASS, "glob grep 읽기",
     'grep -l "INDEX.md" .git/session_workflow/active/*.touched', "Bash"),
    (PASS, "§0 유일 예외 — handoff 삭제",
     "rm .git/session_workflow/handoff/8fde06da.md", "Bash"),
    (PASS, "§0 예외 — 플래그 붙은 handoff 삭제",
     "rm -f .git/session_workflow/handoff/8fde06da.md", "Bash"),
    (PASS, "override 주석",
     'python3 -c "import session_state; session_state.save_session(1,2,3)"  # sw:allow-state-write',
     "Bash"),
    (PASS, "훅 디렉터리 ls — 상태 저장소 아님",
     "ls -la docs/claude_guideline/session_workflow/hooks/", "Bash"),
    (PASS, "무관한 명령",
     "git status --short --branch", "Bash"),
    (PASS, "Bash 아닌 툴",
     "rm .git/session_workflow/active/abc.json", "Write"),
    (PASS, "세션 무관 문자열만 포함",
     'echo "session_id 는 훅이 넣는다"', "Bash"),
]


def run(cmd, tool_name):
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"command": cmd},
        "cwd": ROOT,
        "session_id": "test-session",
    })
    out = subprocess.run([sys.executable, GUARD], input=payload,
                         capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        return "error:rc=%d:%s" % (out.returncode, out.stderr.strip()[:200])
    if not out.stdout.strip():
        return PASS
    try:
        d = json.loads(out.stdout)
    except (json.JSONDecodeError, ValueError):
        return "error:비-JSON 출력"
    hso = d.get("hookSpecificOutput") or {}
    if hso.get("hookEventName") != "PreToolUse":
        return "error:hookEventName 누락"
    return hso.get("permissionDecision") or "error:decision 누락"


def main():
    fails = 0
    for expect, label, cmd, tool in CASES:
        got = run(cmd, tool)
        ok = (got == expect)
        fails += (not ok)
        print("%s  %-8s (기대 %-4s) %s" % ("PASS" if ok else "FAIL", got, expect, label))
    print("\n%d/%d 통과" % (len(CASES) - fails, len(CASES)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
