"""Shared pytest fixtures and helpers for trnav_motion_mux validation tests.

Unifies the subprocess runner across test_validation_v1_v5.py and
test_validation_v6_v10.py. Uses Popen + SIGINT fallback (consistent with
the worker-4 pattern) and resolves fixture path via ament_index to handle
both build-dir and install-dir test execution.
"""

import os
import signal
import subprocess
from typing import Tuple


def fixture_path(filename: str) -> str:
    """Resolve a fixture yaml path.

    Priority:
      1. ament_index share dir (``share/trnav_motion_mux/test/fixtures``) for
         installed-tree colcon test execution.
      2. Repository-relative path next to the test files — used when the
         package has not been installed yet (uncommon in CI but handy for
         local iteration).
    """
    try:
        from ament_index_python.packages import get_package_share_directory
        share_dir = get_package_share_directory("trnav_motion_mux")
        candidate = os.path.join(share_dir, "test", "fixtures", filename)
        if os.path.isfile(candidate):
            return candidate
    except Exception:
        # ament_index may not be set up in some environments; fall back.
        pass

    here = os.path.dirname(__file__)
    return os.path.join(here, "fixtures", filename)


def run_mux_with_yaml(
    yaml_filename: str,
    timeout: float = 5.0,
) -> Tuple[int, str]:
    """Run ``trnav_motion_mux_node`` once with the given fixture params file.

    Uses Popen + communicate(timeout) + SIGINT fallback so that both
    FATAL-terminating cases (expected non-zero exit within a few seconds)
    and WARN-only cases (node keeps running, needs SIGINT to collect output)
    are covered by a single helper.

    Returns (returncode, stderr_text). ``returncode`` may be ``None``-like
    when the process was interrupted; callers should accept either non-zero
    or a negative signal value to signal "FATAL seen" depending on context.
    """
    yaml_path = fixture_path(yaml_filename)

    # preexec_fn=os.setsid: 자식을 새 process group leader 로 시작 → 그룹 전체에
    # SIGINT/SIGKILL 전달 가능. ros2 run wrapper 가 SIGINT 를 자식 node 에 forward
    # 안 하는 문제를 우회 (2026-05-16, V-10 hang 해결).
    proc = subprocess.Popen(
        [
            "ros2", "run", "trnav_motion_mux", "trnav_motion_mux_node",
            "--ros-args", "--params-file", yaml_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
    )

    try:
        _, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stderr
    except subprocess.TimeoutExpired:
        # Node is still running (WARN-only or non-FATAL case). Request a
        # graceful shutdown of the entire process group then collect output.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            _, stderr = proc.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            _, stderr = proc.communicate()
        return proc.returncode, stderr
