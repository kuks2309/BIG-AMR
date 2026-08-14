"""중복 실행 가드 회귀 (`gui.acquire_single_instance`).

판다는 한 프로세스만 열 수 있다. 두 창이 동시에 USB 를 잡으면 나중 창의 연결이 계속
실패하고, 먼저 잡은 쪽이 무엇을 하고 있는지 화면으로는 알 수 없다.

잠금은 `flock` 이라 프로세스가 죽으면 커널이 자동으로 푼다 — PID 파일만 두면 비정상
종료 뒤 찌꺼기가 남아 다음 실행을 영영 막는다. 아래 S4·S5 가 그 성질을 고정한다.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402


@pytest.fixture
def lock_path(tmp_path):
    """시험용 잠금 파일 — 실사용 `/tmp/amr_test_gui.lock` 을 건드리지 않는다."""
    return str(tmp_path / "gui.lock")


def test_first_caller_takes_the_lock(lock_path):
    """처음 부른 쪽이 잠금을 잡고 자기 PID 를 남긴다."""
    fh, holder = gui.acquire_single_instance(lock_path)
    try:
        assert fh is not None and holder is None
        with open(lock_path) as f:
            assert f.read().strip() == str(os.getpid())
    finally:
        if fh is not None:
            fh.close()


def test_second_caller_is_refused_with_the_holder_pid(lock_path):
    """두 번째 호출은 거부되고 **선점자 PID** 를 돌려준다 — 누구를 봐야 하는지 알려야 한다."""
    first, _ = gui.acquire_single_instance(lock_path)
    try:
        second, holder = gui.acquire_single_instance(lock_path)
        assert second is None, "두 번째 인스턴스가 잠금을 잡았다"
        assert holder == str(os.getpid())
    finally:
        first.close()


def test_lock_is_released_when_the_holder_closes(lock_path):
    """선점자가 사라지면 잠금이 풀린다 — 비정상 종료 뒤에도 다음 실행이 막히면 안 된다."""
    first, _ = gui.acquire_single_instance(lock_path)
    first.close()                                   # 프로세스 종료와 같은 효과
    second, holder = gui.acquire_single_instance(lock_path)
    try:
        assert second is not None, f"잠금이 남아 다음 실행을 막았다 (holder={holder})"
    finally:
        second.close()


def test_stale_lock_file_does_not_block(lock_path):
    """죽은 프로세스의 PID 가 적힌 파일이 남아 있어도 막지 않는다.

    PID 파일 방식이었다면 여기서 막혔을 것이다 — `flock` 은 파일 내용이 아니라 커널
    잠금을 보므로 찌꺼기 내용은 판정에 쓰이지 않는다.
    """
    with open(lock_path, "w") as f:
        f.write("999999")                           # 존재하지 않는 PID
    fh, holder = gui.acquire_single_instance(lock_path)
    try:
        assert fh is not None, f"찌꺼기 PID 파일이 실행을 막았다 (holder={holder})"
    finally:
        fh.close()


def test_main_refuses_a_second_instance(monkeypatch):
    """`main()` 이 잠긴 상태에서 **창을 만들지 않고** 1 을 반환한다(배선).

    가드 함수만 있고 `main()` 이 부르지 않으면 아무것도 막지 못한다.
    """
    made = []
    monkeypatch.setattr(gui, "acquire_single_instance",
                        lambda *a, **k: (None, "12345"))
    monkeypatch.setattr(gui, "MainWindow", lambda *a, **k: made.append(1))
    assert gui.main() == 1
    assert made == [], "이미 실행 중인데 창을 만들었다"
