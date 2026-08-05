"""정착 판정이 **낡은 실측**을 쓰지 않는지 — 2026-08-03 리뷰 High ① 재발 방지.

## 무엇이 문제였나

`_wait_settle` 이 `self._meas_deg` 를 시각 없이 읽었다. `_meas_deg` 는 폴링 스레드가 채우는데
폴링이 예외로 죽으면 `_loop` 이 `self._run = False` 로 조용히 끝나고 **마지막 값이 그대로 남는다.**
그 값이 우연히 목표와 맞으면 「정착됐다」로 판정돼 **구동에 들어갔다** — 실제 바퀴 각도는 아무도
모르는 상태에서.

여기서는 그 경로를 시간으로 고정한다. `MEAS_TTL_S` 를 짧게 바꿔 만료를 즉시 만든다.
"""
from __future__ import annotations

import os
import sys
import time

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
    w._run = True                 # 제어권 보유 상태(판다 직독 경로)
    yield w
    w._seer_run = False
    w._run = False


def test_fresh_measurement_is_used(win):
    win._set_meas(3, 1.0)
    win._set_meas(4, 1.0)
    assert win._meas_angle(3) == pytest.approx(1.0)
    assert win._wait_settle(1.0, tol=3.0, timeout=0.3) is True


def test_stale_measurement_is_not_used(win, monkeypatch):
    """폴링이 멈춘 뒤에도 값이 남아 있으면 **정착으로 치지 않는다**."""
    monkeypatch.setattr(gui, "MEAS_TTL_S", 0.2)
    win._set_meas(3, 1.0)
    win._set_meas(4, 1.0)
    time.sleep(0.3)                                  # 폴링이 끊긴 상황
    assert win._meas_deg[3] == pytest.approx(1.0)    # 값은 남아 있다
    assert win._meas_angle(3) is None                # 그러나 쓰지 않는다
    assert win._wait_settle(1.0, tol=3.0, timeout=0.3) is False


def test_settle_requires_both_axes_fresh(win, monkeypatch):
    """한 축만 신선하면 정착이 아니다 — crab 은 앞뒤가 같아야 성립한다."""
    monkeypatch.setattr(gui, "MEAS_TTL_S", 0.3)
    win._set_meas(3, 1.0)
    time.sleep(0.35)
    win._set_meas(4, 1.0)                            # 4번만 갱신
    assert win._meas_angle(3) is None
    assert win._meas_angle(4) == pytest.approx(1.0)
    assert win._wait_settle(1.0, tol=3.0, timeout=0.3) is False


def test_measurement_cannot_be_written_without_timestamp(win):
    """값과 시각은 **한 지점**에서만 함께 쓰인다 — 따로 쓸 수 있으면 언젠가 따로 쓰인다."""
    assert hasattr(win, "_set_meas")
    src = open(gui.__file__, encoding="utf-8").read()
    # `_meas_deg[...] = ` 대입은 `_set_meas` 안에서 딱 한 번만 나와야 한다
    assert src.count("self._meas_deg[node] = deg") == 1


def test_stale_value_does_not_reach_the_wheel_drawing(win, monkeypatch):
    """그림도 낡은 값을 실측인 척 그리지 않는다(슬라이더 미리보기로 떨어진다)."""
    monkeypatch.setattr(gui, "MEAS_TTL_S", 0.2)
    win.sld_front.setValue(40)
    win.sld_rear.setValue(40)
    win._set_meas(3, 1.0)
    win._set_meas(4, 1.0)
    time.sleep(0.3)
    win._redraw_wheel()
    assert win.wheel.front_deg == pytest.approx(40.0), "만료된 실측이 그림에 남았다"
