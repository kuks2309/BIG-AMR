# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""bgr_to_pixmap 채널 순서·크기 회귀 테스트.

Format_BGR888 무복사 경로로 바꾸면서 가장 위험한 회귀는 **채널 순서 뒤바뀜**
(빨강↔파랑)이다. 눈으로만 확인하면 회색 장면에서는 드러나지 않으므로 순수 색
프레임으로 픽셀값을 직접 검증한다. GUI 없이 돌도록 offscreen 플랫폼을 쓴다.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# pip opencv-python 이 남긴 플러그인 경로 오염 제거 (app.py 와 동일 이유).
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

from vision_guard.main_window import bgr_to_pixmap


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_bgr(b, g, r, height=4, width=6):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = b
    frame[:, :, 1] = g
    frame[:, :, 2] = r
    return frame


@pytest.mark.parametrize(
    "bgr,expected_rgb",
    [
        ((255, 0, 0), (0, 0, 255)),      # 순수 파랑(BGR) -> RGB 값 (0,0,255)
        ((0, 0, 255), (255, 0, 0)),      # 순수 빨강
        ((0, 255, 0), (0, 255, 0)),      # 순수 초록
        ((10, 20, 30), (30, 20, 10)),    # 비대칭 값 — 스왑 여부를 확실히 잡는다
    ],
)
def test_bgr_to_pixmap_channel_order(qapp, bgr, expected_rgb):
    pixmap = bgr_to_pixmap(_make_bgr(*bgr))
    image = pixmap.toImage()
    color = image.pixelColor(2, 1)
    assert (color.red(), color.green(), color.blue()) == expected_rgb


def test_bgr_to_pixmap_dimensions(qapp):
    pixmap = bgr_to_pixmap(_make_bgr(1, 2, 3, height=48, width=64))
    assert (pixmap.width(), pixmap.height()) == (64, 48)


def test_bgr_to_pixmap_survives_source_release(qapp):
    """QPixmap 은 자체 복사본을 가져야 한다 — 원본 numpy 해제 후에도 픽셀 유지."""
    frame = _make_bgr(200, 100, 50)
    pixmap = bgr_to_pixmap(frame)
    del frame
    color = pixmap.toImage().pixelColor(0, 0)
    assert (color.red(), color.green(), color.blue()) == (50, 100, 200)


def test_bgr_to_pixmap_accepts_non_contiguous(qapp):
    """슬라이스 등 비연속 입력도 처리해야 한다(ascontiguousarray 경로)."""
    wide = _make_bgr(7, 8, 9, height=4, width=12)
    view = wide[:, ::2, :]  # 비연속 뷰
    assert not view.flags["C_CONTIGUOUS"]
    pixmap = bgr_to_pixmap(view)
    assert (pixmap.width(), pixmap.height()) == (6, 4)
    color = pixmap.toImage().pixelColor(0, 0)
    assert (color.red(), color.green(), color.blue()) == (9, 8, 7)
