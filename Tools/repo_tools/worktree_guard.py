#!/usr/bin/env python3
"""공유 워킹트리를 쓰는 다중 세션에서 **남의 HEAD 를 건드리는 git 조작**을 막는다.

이 저장소는 하나의 `.git` 을 여러 세션이 공유한다(`git worktree list` 가 10개 이상).
그래서 아래 두 조작이 조용히 남의 작업을 망친다 — 둘 다 실제로 발생했다.

  ① 브랜치 포인터 이동 — 링크드 워크트리 안에서 `git checkout -B main <ref>` 를 하면
     공유 트리가 체크아웃 중인 `main` 이 통째로 끌려간다. 파일은 그대로인데 HEAD 만
     수십 커밋 앞으로 가서, 다른 세션들에게 수백 건의 유령 staged 항목으로 보인다.
  ② 워크트리 제거 — `git worktree remove --force` 를 경로 패턴으로 훑으면 남의 워크트리가
     걸린다. `--force` 는 "미커밋 변경이 있으면 거부" 안전장치를 무력화한다.

`git_workflow.md` §2-1 은 ①을 명시로 금지하지만(「⚠ 공유 HEAD 주의 — git switch 금지」)
문서 규칙일 뿐 기계 강제가 없었다. 이 도구가 그 자리를 채운다.

설계 원칙: 금지만으로는 막히지 않는다. 그래서 판정(`check-*`)뿐 아니라 **위험한 명령 형태를
쓸 필요 자체를 없애는 안전 경로**(`safe-merge`)를 함께 제공한다.

사용법
------
  # 위험 여부 판정 (exit 1 = 하면 안 됨)
  python3 Tools/repo_tools/worktree_guard.py check-branch <브랜치명>
  python3 Tools/repo_tools/worktree_guard.py check-remove <워크트리경로> --session-id <8자리>

  # 안전한 대안 — base 를 체크아웃하지 않고 병합·push
  python3 Tools/repo_tools/worktree_guard.py safe-merge <세션브랜치> [--base main] [--dry-run]

설계·평가: docs/code_review/worktree-guard/
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 실패:\n{r.stderr.strip()}")
    return r.stdout.strip()


def worktrees(cwd=None):
    """[(경로, 체크아웃된 브랜치 또는 None)] — `git worktree list --porcelain` 파싱."""
    out, cur, res = git("worktree", "list", "--porcelain", cwd=cwd), {}, []
    for line in out.split("\n") + [""]:
        if not line:
            if cur:
                res.append((cur.get("worktree"), cur.get("branch")))
                cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur["worktree"] = val
        elif key == "branch":
            cur["branch"] = val.replace("refs/heads/", "")
    return res


def this_worktree(cwd=None):
    return os.path.realpath(git("rev-parse", "--show-toplevel", cwd=cwd))


def cmd_check_branch(args):
    """대상 브랜치가 다른 워크트리에 체크아웃돼 있으면 거부."""
    here = this_worktree()
    for path, branch in worktrees():
        if branch == args.branch and os.path.realpath(path) != here:
            print(f"❌ 거부 — '{args.branch}' 는 다른 워크트리가 체크아웃 중이다:\n"
                  f"     {path}\n"
                  f"   여기서 그 브랜치를 옮기면(checkout -B / branch -f / reset) 그쪽 HEAD 가\n"
                  f"   통째로 끌려간다. 파일은 남지만 그 세션은 유령 staged 항목을 보게 된다.\n"
                  f"   대안: worktree_guard.py safe-merge <브랜치>")
            return 1
    print(f"✔ '{args.branch}' 를 다른 워크트리가 잡고 있지 않다 — 옮겨도 남의 HEAD 는 움직이지 않는다.")
    return 0


def cmd_check_remove(args):
    """이 세션이 만든 워크트리가 아니면 거부."""
    target = os.path.realpath(args.path)
    here = this_worktree()
    if target == here:
        print("❌ 거부 — 지금 서 있는 워크트리다.")
        return 1
    known = {os.path.realpath(p): b for p, b in worktrees()}
    if target not in known:
        print(f"❌ 거부 — git 이 아는 워크트리가 아니다: {target}")
        return 1
    branch, sid = known[target] or "(detached)", args.session_id
    if not sid:
        print(f"❌ 거부 — --session-id 가 없어 소유를 판정할 수 없다. 브랜치 '{branch}', 경로 {target}")
        return 1
    if not (branch.startswith(f"session/{sid}") or f"-ses-{sid}" in target):
        print(f"❌ 거부 — 이 세션({sid}) 소유가 아니다. 브랜치 '{branch}', 경로 {target}\n"
              f"   미커밋 파일은 복구 수단이 없다. 소유 세션이 정리하게 두어라.")
        return 1
    print(f"✔ 이 세션({sid}) 소유로 확인됨 — 브랜치 '{branch}'")
    return 0


def cmd_safe_merge(args):
    """base 를 체크아웃하지 않고 병합·push. 어떤 브랜치 포인터도 이동하지 않는다."""
    remote, base, branch = args.remote, args.base, args.branch
    git("fetch", remote, "--quiet")
    tmp = tempfile.mkdtemp(prefix="wg-merge-")
    wt = os.path.join(tmp, "wt")
    try:
        # --detach — 지역 브랜치를 만들지도, 옮기지도 않는다. 이것이 안전성의 근거다.
        git("worktree", "add", "--detach", "--quiet", wt, f"{remote}/{base}")
        before = git("rev-parse", "HEAD", cwd=wt)
        git("merge", "--no-ff", "-m", args.message or f"Merge branch '{branch}'", branch, cwd=wt)
        after = git("rev-parse", "HEAD", cwd=wt)
        if before == after:
            print(f"※ 병합 결과가 {remote}/{base} 와 같다 — 올릴 것이 없다.")
            return 0
        print(f"병합: {before[:7]} → {after[:7]}\n올라갈 커밋:")
        print(git("log", "--oneline", f"{remote}/{base}..HEAD", cwd=wt))
        if args.dry_run:
            print("\n--dry-run — push 하지 않았다.")
            return 0
        git("push", remote, f"HEAD:{base}", cwd=wt)
        print(f"✔ {remote}/{base} push 완료 — 이 저장소의 어떤 브랜치도 이동하지 않았다.")
        return 0
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check-branch", help="이 워크트리에서 그 브랜치를 옮겨도 되는가")
    p.add_argument("branch")

    p = sub.add_parser("check-remove", help="이 워크트리를 지워도 되는가")
    p.add_argument("path")
    p.add_argument("--session-id", default=os.environ.get("CLAUDE_SESSION_ID", "")[:8])

    p = sub.add_parser("safe-merge", help="base 를 체크아웃하지 않고 병합·push")
    p.add_argument("branch")
    p.add_argument("--remote", default="origin")
    p.add_argument("--base", default="main")
    p.add_argument("--message", default=None)
    p.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()
    return {"check-branch": cmd_check_branch,
            "check-remove": cmd_check_remove,
            "safe-merge": cmd_safe_merge}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
