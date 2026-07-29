# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""프레임 끊김 표시(F6) · 레이아웃 변경 시 계측 기준선 초기화(F9) 회귀 테스트.

두 결함은 **조용한 실패**라 눈으로 찾을 수 없다:
  - F6: 프레임이 끊겨도 헤더가 마지막 FPS 를 계속 표시 → 정지 화면이 라이브처럼 보인다.
  - F9: 레이아웃 변경 후 `delta` 가 음수가 되어 정지 경고가 **영구히** 나가지 않는다.
근거: docs/adr/2026-07-28-cctv-ai-overlay-toggle.md §2
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# pip opencv-python 이 남긴 플러그인 경로 오염 제거 (app.py 와 동일 이유).
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

from vision_guard.main_window import (LatestDetectionStore, LatestFrameStore,
                                      MainWindow, CameraCell, _STALE_AFTER_S,
                                      _age_ms, bgr_to_pixmap)

TOPICS = ["/cam0/image_raw", "/cam1/image_raw"]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _pixmap():
    return bgr_to_pixmap(np.zeros((4, 6, 3), dtype=np.uint8))


class _Logger:
    """get_logger() 대역 — info/warn 문구를 모은다."""

    def __init__(self):
        self.infos = []
        self.warns = []

    def info(self, msg):
        self.infos.append(msg)

    def warn(self, msg):
        self.warns.append(msg)


# ── F6: 프레임 끊김 표시 ─────────────────────────────────────────────────────
def test_fresh_cell_shows_fps_not_stale(qapp):
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    assert "신호 없음" not in cell._header.text()


def test_cell_without_any_frame_is_left_alone(qapp):
    """프레임을 한 번도 못 받은 셀은 이미 'No Signal' 이므로 강등 대상이 아니다."""
    cell = CameraCell("cam0")
    assert cell.check_stale(now=10_000.0) is False


def test_stale_after_threshold_reports_no_signal(qapp):
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    changed = cell.check_stale(now=cell._last_stamp + _STALE_AFTER_S + 0.1)
    assert changed is True
    assert "신호 없음" in cell._header.text()


def test_stale_zeroes_fps_so_it_cannot_be_misread(qapp):
    """마지막 FPS 를 남겨두면 '잘 돌고 있다' 로 오독된다 — 반드시 0 이어야 한다."""
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    cell.update_frame(_pixmap())          # EMA 가 0 이 아닌 값을 갖게 한다
    assert cell._fps > 0.0
    cell.check_stale(now=cell._last_stamp + _STALE_AFTER_S + 0.1)
    assert cell._fps == 0.0


def test_not_stale_just_below_threshold(qapp):
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    assert cell.check_stale(now=cell._last_stamp + _STALE_AFTER_S - 0.1) is False
    assert "신호 없음" not in cell._header.text()


def test_check_stale_is_idempotent(qapp):
    """이미 강등된 셀은 상태 변화 없음(False)을 돌려 헤더를 다시 그리지 않는다."""
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    late = cell._last_stamp + _STALE_AFTER_S + 0.1
    assert cell.check_stale(now=late) is True
    assert cell.check_stale(now=late + 1.0) is False


def test_new_frame_recovers_from_stale(qapp):
    cell = CameraCell("cam0")
    cell.update_frame(_pixmap())
    cell.check_stale(now=cell._last_stamp + _STALE_AFTER_S + 0.1)
    assert "신호 없음" in cell._header.text()
    cell.update_frame(_pixmap())          # 프레임 복귀
    assert "신호 없음" not in cell._header.text()


def test_pump_marks_stale_cells(qapp):
    """`_pump` 은 갱신된 셀만 훑으므로 끊긴 셀을 따로 강등해야 한다."""
    store = LatestFrameStore()
    window = MainWindow(TOPICS, "1x2", store, logger=None)
    cell = window._cell_by_topic[TOPICS[0]]
    cell.update_frame(_pixmap())
    cell._last_stamp -= _STALE_AFTER_S + 1.0    # 과거로 밀어 끊김 상황을 만든다
    window._pump()                               # 새 프레임 없음
    assert "신호 없음" in cell._header.text()
    window.close()


# ── 검출 저장소: 토픽별 수신 추적 (2026-07-29 감사 F6 신규 구멍) ────────────
def _put(store, topic):
    store.put(topic, stamp_ns=0, source_size=(1280, 720), detections=())


def test_detection_store_reports_none_before_any_message():
    assert LatestDetectionStore().seconds_since_last(TOPICS) is None


def test_detection_store_flags_camera_that_never_reported():
    """한 대만 수신되면 나머지는 '한 번도 못 받음' 이므로 무한대로 드러나야 한다.

    회귀 방어 본체 — 종전에는 수신 시각이 단일 스칼라라, 한 대만 살아 있어도
    "방금 받았다" 로 보여 나머지 5대의 고장이 가려졌다.
    """
    store = LatestDetectionStore()
    _put(store, TOPICS[0])
    assert store.seconds_since_last(TOPICS) == float("inf")


def test_detection_store_uses_oldest_not_newest():
    """전부 수신됐으면 **가장 낡은** 것 기준이어야 한다 — 최신 기준이면 고장이 가려진다."""
    store = LatestDetectionStore()
    _put(store, TOPICS[0])
    store._last_recv[TOPICS[0]] -= 5.0        # 한 대만 5초 전으로 밀어 놓는다
    _put(store, TOPICS[1])
    assert store.seconds_since_last(TOPICS) >= 5.0


def test_detection_store_peek_does_not_clear():
    store = LatestDetectionStore()
    _put(store, TOPICS[0])
    assert store.peek(TOPICS[0]) is not None
    assert store.peek(TOPICS[0]) is not None   # 두 번째 조회도 살아 있어야 한다


# ── 박스 나이는 절대값 (2026-07-29 감사) ────────────────────────────────────
def test_age_ms_uses_absolute_difference():
    """표시 프레임이 검출 프레임보다 오래돼도(음수) 어긋남 크기는 같다.

    부호를 그대로 넘기면 `classify_age` 가 FRESH 로 분류해 어긋난 박스를 초록 실선으로 그린다.
    """
    assert _age_ms(1_000_000_000, 1_200_000_000) == pytest.approx(200.0)
    assert _age_ms(1_200_000_000, 1_000_000_000) == pytest.approx(200.0)


def test_age_ms_zero_when_stamp_missing():
    assert _age_ms(None, 123) == 0.0
    assert _age_ms(123, None) == 0.0


# ── F9: 레이아웃 변경 시 계측 기준선 초기화 ─────────────────────────────────
def test_layout_change_clears_report_baseline(qapp):
    store = LatestFrameStore()
    window = MainWindow(TOPICS, "1x2", store, logger=None)
    window._last_report_frames[TOPICS[0]] = 12345
    window._apply_layout("2x2")
    assert window._last_report_frames == {}
    window.close()


def test_stall_warning_fires_after_layout_change(qapp):
    """회귀 방어 본체 — 레이아웃 변경 직후 멈춘 카메라를 경고해야 한다.

    기준선을 지우지 않으면 `delta = 0 - 12345` 가 음수가 되어 `delta == 0` 검사를
    통과하지 못하고 경고가 영구히 나가지 않는다.
    """
    logger = _Logger()
    store = LatestFrameStore()
    window = MainWindow(TOPICS, "1x2", store, logger=logger, report_interval_sec=0)
    # 프레임을 좀 받아 누적을 쌓은 뒤 레이아웃을 바꾼다.
    for _ in range(5):
        window._cell_by_topic[TOPICS[0]].update_frame(_pixmap())
    window._report_display_stats()
    assert window._last_report_frames[TOPICS[0]] == 5

    window._apply_layout("2x2")           # 셀 재생성 → _frames_rendered = 0
    logger.warns.clear()
    window._report_display_stats()        # 새 프레임 0건 → 정지 경고가 나가야 한다
    assert logger.warns, "레이아웃 변경 후 정지 경고가 나가지 않았다(F9 회귀)"
    assert TOPICS[0] in logger.warns[0]
    window.close()


def test_report_stats_reports_no_negative_delta(qapp):
    """음수 delta 는 계측 오염의 신호 — 문구에 '-' 프레임 수가 나오면 안 된다."""
    logger = _Logger()
    store = LatestFrameStore()
    window = MainWindow(TOPICS, "1x2", store, logger=logger, report_interval_sec=0)
    for _ in range(3):
        window._cell_by_topic[TOPICS[0]].update_frame(_pixmap())
    window._report_display_stats()
    window._apply_layout("2x2")
    window._report_display_stats()
    assert not any("=-" in line for line in logger.infos), logger.infos
    window.close()
