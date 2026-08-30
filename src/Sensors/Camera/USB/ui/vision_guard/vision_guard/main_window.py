# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""PyQt5 GUI for AMR VisionGuard.

Renders up to six camera streams in a user-selectable grid (1x1 .. 3x3). The ROS
thread writes the latest frame per topic into a ``LatestFrameStore``; the GUI
thread drains it on a timer and renders. All widget mutation happens here on the
Qt GUI thread (Qt cross-thread rule).
"""

import threading
import time

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .layouts import LAYOUT_PRESETS, parse_layout, smallest_layout_for
from .overlay import FRESH, build_view_boxes, detector_status

# 오버레이 그리기 상수 — 전부 **위젯 좌표**라 레이아웃 배율과 무관하게 일정하다.
_BOX_PEN_PX = 2
_OVERLAY_FONT_PT = 9
_BOX_COLOR_FRESH = (0, 220, 80)     # 초록 — 신선
_BOX_COLOR_STALE = (200, 160, 0)    # 황색 — 낡음(점선과 함께)
_NS_PER_MS = 1_000_000
# 검출 정상 갱신 주기(초). 실측 카메라당 약 4.8 Hz → 약 0.21 s.
# "응답 없음" 판정은 이 값의 2배를 넘을 때다.
_DETECTION_PERIOD_S = 0.21
# AI 상태 문구 갱신 주기(초). 렌더 타이머와 **독립**이며, 렌더율(기본 10 Hz)과 같은 빈도로
# setText 할 이유가 없어 1 s 로 둔다.
_AI_STATUS_PERIOD_S = 1.0


def _age_ms(frame_stamp_ns, detection_stamp_ns):
    """표시 중인 프레임과 검출 프레임의 시각차(ms) = 실제 시각적 어긋남.

    둘 중 하나라도 시각이 없으면 0 을 돌려 신선 취급한다 — 나이를 모른다는 이유로 박스를
    감추면 정보가 사라지고, 반대로 만료 처리하면 정상 동작에서도 박스가 안 보인다.
    """
    if frame_stamp_ns is None or detection_stamp_ns is None:
        return 0.0
    # **절대값**이다. 표시 프레임이 검출 프레임보다 오래된 경우(음수)에도 시각적
    # 어긋남의 크기는 같다 — 음수를 그대로 넘기면 `classify_age` 가 FRESH 로 분류해
    # 실제로 어긋난 박스를 초록 실선으로 그린다(2026-07-29 감사).
    return abs(frame_stamp_ns - detection_stamp_ns) / _NS_PER_MS

# Exponential-moving-average weight for the displayed FPS readout.
#
# ⚠ 이 EMA 는 `dt` 가 아니라 `1/dt` 를 평균하므로 Jensen 부등식으로 **구조적 상향 편향**이
# 있다 — 소크 실측에서 표기 25.7~25.9 vs 실측 21.1~21.4(약 +4 fps 과대, P3/F10).
# **성능 근거로는 헤더 숫자를 쓰지 말고** `_report_display_stats` 의 `프레임수/경과` 를 쓸 것.
_FPS_EMA_ALPHA = 0.1

# 프레임이 이 시간 이상 끊기면 헤더를 '신호 없음' 으로 강등한다.
#
# `_fps` 는 ``update_frame`` 안에서만 갱신되므로 이 강등이 없으면 프레임이 끊겨도 헤더가
# **마지막 FPS 를 영원히 표시**하고, ``_pixmap`` 도 지워지지 않아 정지 화면이 라이브처럼 보인다.
# CCTV 에서 얼어붙은 화면과 "아무도 없는 살아있는 화면"이 구별되지 않는 것은 감시 기능의
# 조용한 실패다(2026-07-28 적대적 설계 검토 F6, docs/adr/2026-07-28-cctv-ai-overlay-toggle.md).
#
# 2 s 는 캡처 29.7 fps·렌더 기본 10 Hz 실측 8.9~9.3 fps 기준 정상 간격(약 110 ms)의 18배라
# 오탐이 없고,
# 사람이 화면을 보고 이상을 알아채기 전에 표시가 바뀔 만큼 짧다.
_STALE_AFTER_S = 2.0


class LatestFrameStore:
    """Thread-safe latest-frame-per-topic store (bounded memory).

    Decouples the ROS ingest rate from the GUI render rate: the ROS thread
    overwrites the latest frame per topic (older unrendered frames are dropped,
    not queued) and the GUI thread drains it at its own timer rate. Memory is
    bounded to (num cameras x 1 frame).

    Replaces the previous per-frame queued PyQt signal, which grew Qt's event
    queue without bound at 5x30 fps and OOM-killed the process (~11 GB in ~1 h,
    2026-07-27 CCTV soak).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._latest = {}

    def put(self, topic, frame, stamp_ns=None):
        """Store the newest frame for ``topic`` (ROS thread). Overwrites.

        ``stamp_ns`` 는 프레임 **취득 시각**(header.stamp)이다. 검출 박스의 나이를 재려면
        "지금 화면에 그려진 프레임이 언제 것인가" 를 알아야 하는데, 종전에는 이 값을 버렸다.
        payload 만 튜플로 늘렸을 뿐 덮어쓰기·유계성 계약은 그대로다.
        """
        with self._lock:
            self._latest[topic] = (frame, stamp_ns)

    def drain(self):
        """Return pending {topic: (frame, stamp_ns)} and clear it (GUI thread)."""
        with self._lock:
            pending = self._latest
            self._latest = {}
        return pending


class LatestDetectionStore:
    """Thread-safe latest-detection-per-topic store.

    `LatestFrameStore` 와 **의미론이 다르다**: 읽어도 비우지 않는다(peek). 검출은 카메라당
    약 4.9 Hz 인데 GUI 는 기본 10 Hz 로 그리므로, 프레임처럼 "읽고 비우면" 약 2틱 중 1틱만
    박스가 있어 초당 약 5회 점멸한다(`render_hz:=30` 이면 6틱 중 1틱으로 더 심해진다).
    대신 **나이 기반으로 만료**시켜 오래된 박스가 영원히 남지 않게 한다
    (2026-07-28 적대적 설계 검토 F5).

    메모리는 토픽당 스냅샷 1개로 유계다 — 궤적·이력을 쌓지 않는다.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._latest = {}
        # **토픽별** 마지막 수신 시각. 단일 스칼라로 두면 6대 합산(약 29 Hz)을 보게 되어
        # 카메라 1대의 탐지가 완전히 죽어도 나머지 5대가 타이머를 갱신해 "감시 중" 이
        # 유지된다 — 카메라 단위 고장을 놓친다(2026-07-29 감사 F6 신규 구멍).
        self._last_recv: dict = {}

    def put(self, topic, stamp_ns, source_size, detections):
        """최신 검출로 덮어쓴다 (ROS 스레드).

        :param stamp_ns: 검출이 수행된 **원본 프레임의 취득 시각**(header.stamp).
        :param source_size: `(width, height)` 검출 기준 원본 해상도.
        :param detections: `ai_msgs/Detection` 목록.
        """
        with self._lock:
            self._latest[topic] = (stamp_ns, source_size, tuple(detections))
            self._last_recv[topic] = time.monotonic()

    def peek(self, topic):
        """`(stamp_ns, source_size, detections)` 또는 None. **비우지 않는다.**"""
        with self._lock:
            return self._latest.get(topic)

    def seconds_since_last(self, topics=None):
        """**가장 낡은** 카메라의 마지막 검출 수신 후 경과(초).

        최댓값을 쓰는 이유: 한 대라도 끊기면 드러나야 한다. 평균이나 최신값을 쓰면
        나머지가 정상인 동안 고장이 가려진다.

        벽시계가 아니라 `monotonic` 을 쓴다 — NTP 보정이나 RTC 이상으로 시계가 튀어도
        "탐지기가 죽었다" 로 오판하지 않게 한다.

        :param topics: 감시 대상 토픽 목록. None 이면 수신 이력이 있는 것만 본다.
        :returns: 경과 초. **감시 대상 중 한 번도 못 받은 토픽이 있으면 `inf`**,
            아무것도 못 받았으면 None.
        """
        now = time.monotonic()
        with self._lock:
            if topics is None:
                stamps = list(self._last_recv.values())
                if not stamps:
                    return None
            else:
                stamps = [self._last_recv.get(t) for t in topics]
                if not stamps or all(s is None for s in stamps):
                    return None
                if any(s is None for s in stamps):
                    return float("inf")   # 한 번도 못 받은 카메라 = 가장 낡음
        return now - min(stamps)


def bgr_to_pixmap(frame):
    """Convert an HxWx3 BGR uint8 numpy array to a QPixmap.

    Qt reads BGR directly (Format_BGR888), so no channel-swap copy is needed —
    the QImage just wraps the numpy buffer. Measured on the Orin (1280x720):
    the previous RGB888 path (``frame[:, :, ::-1]`` + ``QImage.copy()``) cost
    ~9.2 ms per camera, which put a 13.9 fps ceiling on a 6-camera grid; this
    path costs ~1.1 ms including the pixmap conversion.

    QImage does not own the buffer, so the pixels are handed to a QPixmap here,
    while ``frame`` is still referenced by this frame's scope — QPixmap owns its
    own copy, so the returned object stays valid after the numpy array is freed.
    """
    frame = np.ascontiguousarray(frame)  # decoded frames are already contiguous
    height, width, _ = frame.shape
    image = QImage(frame.data, width, height, 3 * width, QImage.Format_BGR888)
    return QPixmap.fromImage(image)


class CameraCell(QFrame):
    """One grid tile: a scaled video image with a name + FPS header."""

    def __init__(self, title):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #101418; color: #d8dee9;")

        self._title = title
        self._last_stamp = None
        self._fps = 0.0
        # 프레임 끊김 여부. True 면 헤더가 FPS 대신 '신호 없음' 을 보여준다(F6).
        self._stale = False
        # 누적 렌더 프레임 수 — 장시간 내구 시 "이 카메라가 몇 프레임이나 그려졌나"
        # 를 로그로 남기기 위한 카운터(정지 구간 사후 식별).
        self._frames_rendered = 0

        self._header = QLabel(title)
        self._header.setStyleSheet("color: #88c0d0; font-weight: bold; padding: 2px;")

        self._video = QLabel("No Signal")
        self._video.setAlignment(Qt.AlignCenter)
        self._video.setStyleSheet("color: #4c566a;")
        self._video.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._video.setMinimumSize(160, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(self._header)
        layout.addWidget(self._video, stretch=1)

        self._pixmap = None
        # 표시 중인 프레임의 취득 시각(ns) — 박스 나이 계산의 기준.
        self._frame_stamp_ns = None
        # (stamp_ns, (w, h), detections) 또는 None. 소유는 MainWindow 쪽 저장소.
        self._detections = None
        self._overlay_on = False

    def set_overlay(self, enabled):
        """박스 표시 on/off. 상태 소유는 MainWindow 이고 셀은 반영만 한다."""
        if self._overlay_on == enabled:
            return
        self._overlay_on = enabled
        self._render()

    def set_detections(self, snapshot):
        """최신 검출 스냅샷을 반영한다. None 이면 박스를 지운다."""
        self._detections = snapshot
        if self._overlay_on:
            self._render()

    def set_title(self, title):
        self._title = title
        self._refresh_header()

    def stats(self):
        """(표시 FPS, 누적 렌더 프레임 수) — 내구 로깅용 스냅샷."""
        return self._fps, self._frames_rendered

    def update_frame(self, pixmap, stamp_ns=None):
        """Store the newest frame and update the measured display FPS.

        :param stamp_ns: 프레임 취득 시각(header.stamp). 박스 나이 계산에 쓴다.
        """
        self._frame_stamp_ns = stamp_ns
        now = time.monotonic()
        if self._last_stamp is not None:
            dt = now - self._last_stamp
            if dt > 0:
                inst = 1.0 / dt
                self._fps = (
                    inst if self._fps == 0.0
                    else (1 - _FPS_EMA_ALPHA) * self._fps + _FPS_EMA_ALPHA * inst
                )
        self._last_stamp = now
        self._stale = False
        self._frames_rendered += 1
        self._pixmap = pixmap
        self._render()
        self._refresh_header()

    def check_stale(self, now):
        """프레임 끊김을 판정해 헤더 표시를 강등/복구한다(GUI 타이머가 매 틱 호출).

        :param now: ``time.monotonic()`` 기준 현재 시각.
        :returns: 상태가 바뀌었으면 True (헤더를 다시 그렸다는 뜻).

        프레임을 한 번도 못 받은 셀(``_last_stamp is None``)은 이미 "No Signal" 을
        표시하고 있으므로 건드리지 않는다.
        """
        if self._last_stamp is None:
            return False
        stale = (now - self._last_stamp) > _STALE_AFTER_S
        if stale == self._stale:
            return False
        self._stale = stale
        if stale:
            # 마지막 측정값을 남겨두면 "9 fps 로 잘 돌고 있다" 로 오독된다.
            self._fps = 0.0
        self._refresh_header()
        return True

    def resizeEvent(self, event):  # noqa: N802 (Qt override name)
        self._render()
        super().resizeEvent(event)

    def _render(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        if self._overlay_on and self._detections is not None:
            self._paint_boxes(scaled)
        self._video.setPixmap(scaled)

    def _paint_boxes(self, scaled):
        """축소된 픽스맵 **위에** 박스를 그린다.

        축소 후에 그리는 것이 핵심이다 — 원본 해상도에 구우면 3x3 배율(약 0.28)에서 2 px 선이
        0.57 px 로 뭉개져 보이지 않는다. 여기서는 선 두께·글자 크기가 위젯 좌표라 어느
        레이아웃에서나 일정하다(적대적 설계 검토 F7).

        `scaled` 는 `scaled()` 가 만든 새 픽스맵이므로 여기에 그려도 원본 `_pixmap` 은 온전하다.
        """
        stamp_ns, source_size, detections = self._detections
        if not detections:
            return
        age_ms = _age_ms(self._frame_stamp_ns, stamp_ns)
        boxes = build_view_boxes(detections, source_size,
                                 (scaled.width(), scaled.height()),
                                 (scaled.width(), scaled.height()), age_ms)
        if not boxes:
            return
        painter = QPainter(scaled)
        try:
            font = painter.font()
            font.setPointSize(_OVERLAY_FONT_PT)
            painter.setFont(font)
            for box in boxes:
                fresh = box.freshness == FRESH
                color = QColor(*(_BOX_COLOR_FRESH if fresh else _BOX_COLOR_STALE))
                pen = QPen(color, _BOX_PEN_PX)
                if not fresh:
                    # 낡은 박스는 점선 — 실선으로 그리면 현재 위치로 오독된다.
                    pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                painter.drawRect(box.x, box.y, box.width, box.height)
                text_y = max(_OVERLAY_FONT_PT + 2, box.y - 2)
                painter.drawText(box.x + 1, text_y, box.label)
        finally:
            painter.end()

    def _refresh_header(self):
        if self._stale:
            self._header.setText(f"{self._title}    신호 없음")
            return
        self._header.setText(f"{self._title}    {self._fps:4.1f} fps")


class MainWindow(QMainWindow):
    """Top-level window: layout selector toolbar + camera grid."""

    # GUI render/drain rate (Hz) 기본값. Ingest can be far higher (6x30); frames not
    # rendered by the next tick are dropped, not queued — this bounds memory.
    #
    # ⚠ 이 값은 **상한**이지 실제 표시율이 아니다. 6대 그리드에서 한 틱의 렌더 비용이
    # 주기를 넘으면 타이머를 못 따라가 실측은 그보다 낮아진다.
    #
    # 기본 10 Hz 근거 — 2026-07-29 동일 조건 실측(카메라 6대 + 탐지기 + 뷰어 각 1):
    #   설정 30 Hz → GUI 142% CPU, 표시 12.0~13.8 fps, 카메라 28.9, 탐지 25.4 Hz
    #   설정 10 Hz → GUI  98.7% CPU, 표시  8.9~9.3 fps, 카메라 29.7, 탐지 29.3 Hz
    # 30 Hz 는 설정의 40~46% 에 그치면서 카메라·탐지기를 함께 끌어내린다. 10 Hz 는
    # 설정의 89~93% 로 **거의** 도달하고(인자 없이 재검증 7.6~9.3, 2시간 연속 8.1~10.1 로
    # 저하 없음), 회수한 43%p 가 검출률을 카메라당 4.2 → 4.9 Hz 로 올려
    # 박스 낡음(갱신 간격 238 → 204 ms)까지 줄인다.
    _RENDER_HZ = 10

    def __init__(self, camera_topics, initial_layout, frame_store, logger=None,
                 report_interval_sec=60.0, detection_store=None, overlay_on=False,
                 publisher_count_fn=None, render_hz=None):
        super().__init__()
        self.setWindowTitle("AMR VisionGuard")
        self._store = frame_store
        # 검출 저장소는 선택 — 없으면 AI 표시 기능만 비활성이고 감시는 그대로 동작한다.
        # (ai_msgs 빌드 실패가 CCTV 기동 실패가 되면 안 된다.)
        self._det_store = detection_store
        self._overlay_on = bool(overlay_on) and detection_store is not None
        # 검출 토픽 발행자 수 조회 콜러블(ROS 노드가 주입). 없으면 상태 판정을 낙관적으로 둔다.
        self._publisher_count_fn = publisher_count_fn
        self._topics = list(camera_topics)
        # 내구(soak) 관측용: 주기적으로 카메라별 표시 FPS·누적 프레임을 로그로 남긴다.
        # 로그가 없으면 24시간 중 어느 구간에서 화면이 멈췄는지 사후에 알 수 없다.
        self._logger = logger
        self._report_interval_sec = report_interval_sec
        self._last_report_frames = {}
        # topic -> CameraCell currently displaying it (rebuilt on layout change).
        self._cell_by_topic = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Toolbar: layout selector ---
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Layout:"))
        self._layout_combo = QComboBox()
        for label in LAYOUT_PRESETS:
            self._layout_combo.addItem(label)
        if initial_layout not in LAYOUT_PRESETS:
            initial_layout = smallest_layout_for(len(self._topics))
        self._layout_combo.setCurrentText(initial_layout)
        self._layout_combo.currentTextChanged.connect(self._apply_layout)
        toolbar.addWidget(self._layout_combo)
        self._status = QLabel("")
        toolbar.addWidget(self._status)

        # --- AI 표시 토글 ---
        self._ai_check = QCheckBox("AI 표시")
        self._ai_check.setChecked(self._overlay_on)
        self._ai_check.setEnabled(self._det_store is not None)
        if self._det_store is None:
            self._ai_check.setToolTip("검출 구독이 없습니다 (ai_msgs 미설치 또는 비활성)")
        self._ai_check.toggled.connect(self._on_toggle_overlay)
        toolbar.addWidget(self._ai_check)
        # 검출이 0건일 때 '사람 없음' 과 '탐지기 죽음' 이 같은 화면이 되지 않도록 상태를 노출한다.
        self._ai_status = QLabel("")
        self._ai_status.setStyleSheet("color: #8b98a5; padding-left: 6px;")
        toolbar.addWidget(self._ai_status)

        toolbar.addStretch(1)
        root.addLayout(toolbar)

        # --- Grid host ---
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(3)
        root.addWidget(self._grid_host, stretch=1)

        # Pull latest frames on a timer instead of receiving a queued signal
        # per frame — decouples render rate from the (much higher) ingest rate.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pump)
        self._render_hz = float(render_hz) if render_hz else float(self._RENDER_HZ)
        self._timer.start(max(1, int(1000 / self._render_hz)))

        self._report_timer = None
        if self._logger is not None and self._report_interval_sec > 0:
            self._report_timer = QTimer(self)
            self._report_timer.timeout.connect(self._report_display_stats)
            self._report_timer.start(int(self._report_interval_sec * 1000))

        self._ai_status_timer = QTimer(self)
        self._ai_status_timer.timeout.connect(self._refresh_ai_status)
        self._ai_status_timer.start(int(_AI_STATUS_PERIOD_S * 1000))

        self._apply_layout(initial_layout)
        self._refresh_ai_status()
        self.resize(1280, 720)

    def _report_display_stats(self):
        """카메라별 표시 FPS·구간 렌더 프레임 수를 로그로 남긴다(내구 관측)."""
        parts = []
        stalled = []
        for topic in self._topics:
            cell = self._cell_by_topic.get(topic)
            if cell is None:
                parts.append(f"{topic}=hidden")
                continue
            fps, frames = cell.stats()
            delta = frames - self._last_report_frames.get(topic, 0)
            self._last_report_frames[topic] = frames
            parts.append(f"{topic}={fps:.1f}fps/{delta}f")
            if delta == 0:
                stalled.append(topic)
        self._logger.info("display " + " ".join(parts))
        if stalled:
            self._logger.warn(
                f"no frames rendered in the last {self._report_interval_sec:.0f}s: "
                + ", ".join(stalled)
            )

    def _apply_layout(self, label):
        """Rebuild the grid for ``label`` and re-bind topics to cells in order."""
        try:
            rows, cols = parse_layout(label)
        except ValueError:
            return
        capacity = rows * cols

        # Clear existing cells.
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cell_by_topic.clear()
        # 새 셀은 `_frames_rendered = 0` 으로 시작하므로 누적 기준선도 함께 지워야 한다.
        # 지우지 않으면 `delta = 0 - 이전누적` 이 **음수**가 되어 `delta == 0` 정지 검사를
        # 통과하지 못하고, 레이아웃 변경 직후 카메라가 멈춰도 경고가 나가지 않는다
        # (2026-07-28 적대적 설계 검토 F9).
        self._last_report_frames.clear()

        shown = min(capacity, len(self._topics))
        for index in range(capacity):
            row, col = divmod(index, cols)
            if index < len(self._topics):
                topic = self._topics[index]
                cell = CameraCell(topic)
                self._cell_by_topic[topic] = cell
            else:
                cell = CameraCell("(empty)")
            self._grid.addWidget(cell, row, col)

        hidden = max(0, len(self._topics) - capacity)
        note = f"  ({hidden} camera(s) hidden - pick a larger layout)" if hidden else ""
        self._status.setText(f"{shown}/{len(self._topics)} cameras shown{note}")

        # 새로 만든 셀에 토글 상태와 현재 검출을 즉시 반영한다 — 안 하면 다음 검출 수신까지
        # (탐지기 정지 시 영원히) 박스가 비어 보인다.
        for cell in self._cell_by_topic.values():
            cell.set_overlay(self._overlay_on)
        self._push_detections()

    def _on_toggle_overlay(self, enabled):
        """AI 표시 토글. 상태는 MainWindow 가 단독 소유한다 — 셀에 두면 레이아웃 변경마다 초기화된다."""
        self._overlay_on = bool(enabled) and self._det_store is not None
        for cell in self._cell_by_topic.values():
            cell.set_overlay(self._overlay_on)
        # 정지한 카메라에서도 토글이 즉시 먹어야 한다 — `_pump` 은 프레임 구동이라 기다리면 안 된다.
        self._push_detections()
        self._refresh_ai_status()

    def _push_detections(self):
        """저장소의 최신 검출을 보이는 셀에 밀어 넣는다(비우지 않음)."""
        if self._det_store is None:
            return
        for topic, cell in self._cell_by_topic.items():
            cell.set_detections(self._det_store.peek(topic) if self._overlay_on else None)

    def _refresh_ai_status(self):
        """탐지기 생존 상태를 문구로 노출한다(F6/F11)."""
        if not self._overlay_on or self._det_store is None:
            self._ai_status.setText("")
            return
        # 감시 대상을 넘겨 **가장 낡은 카메라** 기준으로 판정한다 — 한 대만 죽어도 드러나야 한다.
        text, _ok = detector_status(self._detector_publisher_count(),
                                    self._det_store.seconds_since_last(self._topics),
                                    _DETECTION_PERIOD_S)
        self._ai_status.setText(text)

    def _detector_publisher_count(self):
        """검출 발행자 수. 주입되지 않았으면 1(=알 수 없음, 살아있다고 가정)."""
        if self._publisher_count_fn is None:
            return 1
        return self._publisher_count_fn()

    def _pump(self):
        """Drain the latest frame per topic and render it (GUI timer tick)."""
        for topic, payload in self._store.drain().items():
            cell = self._cell_by_topic.get(topic)
            if cell is None:
                continue  # camera not currently mapped to a visible cell
            frame, stamp_ns = payload
            cell.update_frame(bgr_to_pixmap(frame), stamp_ns)
        if self._overlay_on:
            self._push_detections()
        # 끊긴 카메라를 헤더에서 드러낸다 — 갱신이 없는 셀은 위 루프에 나타나지 않으므로
        # 여기서 따로 훑어야 한다(F6). 비교 연산뿐이라 틱 비용은 무시할 수 있다.
        now = time.monotonic()
        for cell in self._cell_by_topic.values():
            cell.check_stale(now)
