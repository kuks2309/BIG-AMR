"""모터 값·Seer 값 두 표의 공용 헬퍼 회귀 — 창은 열되 하드웨어는 만지지 않는다.

두 표는 원래 16줄짜리 복붙이었고 한쪽만 고치면 갈라지는 상태였다. `_motor_table`·
`_fill_row` 로 합치면서, 갈라짐을 막는 건 이제 이 테스트다.

`QT_QPA_PLATFORM=offscreen` 으로 화면 없이 돈다. `MainWindow` 는 Seer 폴링 스레드를
띄우지만 daemon 이고 네트워크 실패는 로그로만 흐르므로 테스트를 막지 않는다.
CAN·판다는 제어권을 잡기 전까지 열리지 않으므로 이 테스트가 로봇을 움직이지 않는다.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield a


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    yield w
    w._seer_run = False          # 폴링 스레드 정지 요청
    w._run = False


@pytest.mark.parametrize("attr,rpm_header", [("tbl_motor", "회전(rpm)"),
                                             ("tbl_seer", "회전")])
def test_both_tables_have_same_shape(win, attr, rpm_header):
    """두 표는 헤더 한 칸만 다르고 나머지는 같아야 한다."""
    t = getattr(win, attr)
    assert (t.rowCount(), t.columnCount()) == (4, 4)
    assert [t.horizontalHeaderItem(c).text() for c in range(4)] == \
           ["모터", "각도(°)", rpm_header, "전류(A)"]


@pytest.mark.parametrize("attr", ["tbl_motor", "tbl_seer"])
def test_rows_are_labelled_by_node(win, attr):
    """행 순서가 노드 1~4 고정이어야 한다 — 어긋나면 값이 엉뚱한 축에 표시된다."""
    t = getattr(win, attr)
    assert [t.item(r, 0).text() for r in range(4)] == list(gui.MainWindow.ROWS)


@pytest.mark.parametrize("attr", ["tbl_motor", "tbl_seer"])
def test_cells_start_empty(win, attr):
    t = getattr(win, attr)
    assert {t.item(r, c).text() for r in range(4) for c in (1, 2, 3)} == {"—"}


def test_set_motor_values_writes_the_right_row_and_format(win):
    win.set_motor_values(3, deg=12.5, rpm=-30.0, amp=1.234)
    row = 2                                     # node3 = 세 번째 행
    assert win.tbl_motor.item(row, 1).text() == "+12.5"
    assert win.tbl_motor.item(row, 2).text() == "-30.0"
    assert win.tbl_motor.item(row, 3).text() == "+1.23"   # 전류만 소수 2자리


def test_none_leaves_the_cell_untouched(win):
    win._fill_row(win.tbl_seer, 4, (-7.0, None, 0.5))
    assert win.tbl_seer.item(3, 1).text() == "-7.0"
    assert win.tbl_seer.item(3, 2).text() == "—"          # None 은 덮어쓰지 않는다
    assert win.tbl_seer.item(3, 3).text() == "+0.50"


def test_unknown_node_is_ignored(win):
    """폴링이 예상 밖 노드를 물어와도 표를 깨뜨리지 않아야 한다."""
    win._fill_row(win.tbl_motor, 9, (1.0, 2.0, 3.0))
    assert {win.tbl_motor.item(r, c).text() for r in range(4) for c in (1, 2, 3)} == {"—"}


def test_the_two_tables_are_independent(win):
    """한쪽 표에 쓴 값이 다른 표로 새지 않아야 한다(공용 헬퍼의 대표 위험)."""
    win.set_motor_values(1, deg=1.0, rpm=2.0, amp=3.0)
    assert {win.tbl_seer.item(r, c).text() for r in range(4) for c in (1, 2, 3)} == {"—"}
