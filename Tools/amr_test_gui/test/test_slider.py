"""조향 슬라이더 회귀 — 슬라이더는 **명령 입력**이지 실측 표시가 아니다.

한때 `_redraw_wheel` 이 실측 각도를 슬라이더에 되쓰는 바람에, 손을 떼면 0.2 초 안에
눈금이 제자리로 튕겨 슬라이더가 통째로 먹통이 됐다(2026-07-28). 그 되먹임이 다시
들어오는 것을 여기서 막는다.

`_steer_axis` 만 가짜로 바꾸므로 CAN 도 판다도 열리지 않는다.
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
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    w._run = True                       # 제어권 보유 상태로 둔다
    yield w
    w._seer_run = False
    w._run = False


@pytest.fixture
def cmds(win, monkeypatch):
    """나간 조향 지령을 (node, deg) 로 기록한다."""
    out = []
    monkeypatch.setattr(win, "_steer_axis",
                        lambda node, deg: (out.append((node, deg)), deg)[1])
    return out


# ── 되먹임 금지 (핵심 회귀) ────────────────────────────────────────────────
def test_measurement_never_moves_the_slider(win, cmds):
    """실측이 흘러들어와도 사용자가 넣은 목표를 덮어쓰면 안 된다."""
    win.sld_front.setValue(30)
    win._meas_deg = {3: 0.0, 4: 0.0}          # 실측은 아직 0°
    for _ in range(5):                         # 폴링이 여러 번 돌아도
        win._redraw_wheel()
    assert win.sld_front.value() == 30


def test_wheel_drawing_still_follows_measurement(win, cmds):
    """슬라이더는 목표를 지키되, 그림은 실측을 그려야 한다."""
    win.sld_front.setValue(30)
    win.sld_rear.setValue(30)
    win._meas_deg = {3: 5.0, 4: -5.0}
    win._redraw_wheel()
    assert (win.wheel.front_deg, win.wheel.rear_deg) == (5.0, -5.0)


def test_preview_when_no_measurement(win, cmds):
    """실측이 없을 때만 슬라이더 값을 그림에 미리 보여준다."""
    win._run = False
    win._meas_deg = {}
    win._seer_deg = {}
    win.sld_front.setValue(20)
    win.sld_rear.setValue(-20)
    win._redraw_wheel()
    assert (win.wheel.front_deg, win.wheel.rear_deg) == (20.0, -20.0)


# ── 지령이 나가는 조건 ────────────────────────────────────────────────────
def test_keyboard_or_groove_click_sends_immediately(win, cmds):
    """`sliderReleased` 가 오지 않는 조작(키보드·홈 클릭)에서도 지령이 나가야 한다."""
    win.sld_front.setValue(45)
    assert cmds == [(3, 45.0)]


def test_dragging_does_not_flood_the_bus(win, cmds):
    """끄는 동안은 매 틱 보내지 않는다 — 버스가 지령으로 찬다."""
    win.sld_rear.setSliderDown(True)
    for v in (5, 10, 15, 20):
        win.sld_rear.setValue(v)
    assert cmds == []


def test_release_sends_once_with_the_final_value(win, cmds):
    win.sld_rear.setSliderDown(True)
    for v in (5, 10, 15, 20):
        win.sld_rear.setValue(v)
    win.sld_rear.setSliderDown(False)      # Qt 가 이때 sliderReleased 를 낸다
    assert cmds == [(4, 20.0)], "놓는 순간 마지막 값으로 정확히 1회"


def test_each_slider_commands_only_its_own_axis(win, cmds):
    win.sld_front.setValue(10)
    win.sld_rear.setValue(-10)
    assert cmds == [(3, 10.0), (4, -10.0)]


def test_no_command_without_authority(win, cmds):
    win._run = False
    win.sld_front.setValue(60)
    assert cmds == []


# ── 라벨 ──────────────────────────────────────────────────────────────────
def test_label_shows_target_and_measurement_side_by_side(win, cmds):
    """되먹임을 뺀 자리를 라벨이 메운다 — 목표와 실측을 나란히."""
    win._meas_deg = {3: 12.34, 4: 0.0}
    win.sld_front.setValue(30)
    txt = win.lab_front.text()
    assert "+30°" in txt and "+12.3" in txt


def test_label_omits_measurement_when_absent(win, cmds):
    win._run = False
    win._meas_deg = {}
    win._seer_deg = {}
    win.sld_front.setValue(15)
    assert win.lab_front.text() == "+15°"


# ── 레이아웃 (잡을 수 있는 크기인가) ──────────────────────────────────────
def test_slider_is_big_enough_to_grab(app):
    """한때 78×20 px 밖에 안 돼(1 px = 2.3°) 핸들을 잡을 수 없었다.

    이름·값 라벨과 한 줄에 나란히 놓은 배치가 원인이었다. 슬라이더가 자기 줄을
    통째로 쓰도록 바꿨고, 그 폭이 다시 줄어들면 여기서 걸린다.
    """
    w = gui.MainWindow()
    try:
        w.resize(1200, 800)
        w.show()
        app.processEvents()
        app.processEvents()
        for name, sld in (("front", w.sld_front), ("rear", w.sld_rear)):
            geo = sld.geometry()
            span = sld.maximum() - sld.minimum()
            assert geo.width() >= 240, f"{name} 슬라이더 폭 {geo.width()}px — 너무 좁다"
            assert geo.height() >= 24, f"{name} 슬라이더 높이 {geo.height()}px — 잡기 어렵다"
            assert span / geo.width() <= 1.0, \
                f"{name} 1 px 당 {span / geo.width():.2f}° — 미세 조정 불가"
    finally:
        w._seer_run = False


def test_groove_click_steps_are_coarse_enough(app):
    """홈을 클릭했을 때 5° 씩 움직여야 쓸 만하다(기본 10% = 18° 는 너무 크다)."""
    w = gui.MainWindow()
    try:
        assert w.sld_front.pageStep() == 5
        assert w.sld_rear.pageStep() == 5
    finally:
        w._seer_run = False
