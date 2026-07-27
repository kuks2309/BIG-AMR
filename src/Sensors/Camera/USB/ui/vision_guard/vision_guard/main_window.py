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
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
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

# Exponential-moving-average weight for the displayed FPS readout.
_FPS_EMA_ALPHA = 0.1


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

    def put(self, topic, frame):
        """Store the newest frame for ``topic`` (ROS thread). Overwrites."""
        with self._lock:
            self._latest[topic] = frame

    def drain(self):
        """Return pending {topic: frame} and clear it (GUI thread)."""
        with self._lock:
            pending = self._latest
            self._latest = {}
        return pending


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

    def set_title(self, title):
        self._title = title
        self._refresh_header()

    def stats(self):
        """(표시 FPS, 누적 렌더 프레임 수) — 내구 로깅용 스냅샷."""
        return self._fps, self._frames_rendered

    def update_frame(self, pixmap):
        """Store the newest frame and update the measured display FPS."""
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
        self._frames_rendered += 1
        self._pixmap = pixmap
        self._render()
        self._refresh_header()

    def resizeEvent(self, event):  # noqa: N802 (Qt override name)
        self._render()
        super().resizeEvent(event)

    def _render(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._video.setPixmap(scaled)

    def _refresh_header(self):
        self._header.setText(f"{self._title}    {self._fps:4.1f} fps")


class MainWindow(QMainWindow):
    """Top-level window: layout selector toolbar + camera grid."""

    # GUI render/drain rate (Hz). Ingest can be far higher (5x30); frames not
    # rendered by the next tick are dropped, not queued — this bounds memory.
    _RENDER_HZ = 30

    def __init__(self, camera_topics, initial_layout, frame_store, logger=None,
                 report_interval_sec=60.0):
        super().__init__()
        self.setWindowTitle("AMR VisionGuard")
        self._store = frame_store
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
        self._timer.start(int(1000 / self._RENDER_HZ))

        self._report_timer = None
        if self._logger is not None and self._report_interval_sec > 0:
            self._report_timer = QTimer(self)
            self._report_timer.timeout.connect(self._report_display_stats)
            self._report_timer.start(int(self._report_interval_sec * 1000))

        self._apply_layout(initial_layout)
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

    def _pump(self):
        """Drain the latest frame per topic and render it (GUI timer tick)."""
        for topic, frame in self._store.drain().items():
            cell = self._cell_by_topic.get(topic)
            if cell is None:
                continue  # camera not currently mapped to a visible cell
            cell.update_frame(bgr_to_pixmap(frame))
