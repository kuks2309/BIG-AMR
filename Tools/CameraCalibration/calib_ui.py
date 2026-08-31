"""카메라 intrinsic 캘리브레이션 스테이션 UI (PyQt5) — 표시·입력 전용.

UI 분리 원칙(stack.md §3.1 / vision_guard 참조 정본)에 따라, 검출·수집·자동캡처·
캘리브레이션 로직은 UI-무관 CalibrationSession(calib_session.py) 이 소유한다. 본
모듈은 카메라 획득·프레임 표시·오버레이 렌더·사용자 입력 위젯만 담당한다.
"""
from __future__ import annotations

import glob
import os
import subprocess

import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from calib_session import CalibrationSession
from camera_config import load_camera_config

_ARUCO_DICTS = ["DICT_5X5_1000", "DICT_4X4_1000", "DICT_6X6_1000", "DICT_APRILTAG_36h11"]
# 콤보 표시명 → 세션 패턴 kind (표현↔도메인 매핑은 UI 몫).
_PATTERN_ITEMS = [
    ("체커보드", "checkerboard"),
    ("ChArUco", "charuco"),
    ("원형그리드(대칭)", "circles"),
    ("원형그리드(비대칭)", "acircles"),
]
# 콤보 표시명 → 세션 왜곡 모델. 첫 항목이 기본(plumb_bob).
_MODEL_ITEMS = [
    ("plumb_bob (5계수, 일반)", "plumb_bob"),
    ("rational_polynomial (8계수, 광각)", "rational_polynomial"),
    ("fisheye (4계수, 어안)", "fisheye"),
]
# 자동 모델 탐색 기본 후보 — 원근 렌즈 family(plumb_bob/rational)만. fisheye 는
# 계산이 무겁고(부트스트랩·이중 pruning) 원근 데이터에서 오선택 위험이 있어 기본
# 제외한다. 어안 렌즈는 수동 드롭다운으로 선택. k=3 폴드로 탐색 시간 단축.
_AUTO_SEARCH_MODELS = ["plumb_bob", "rational_polynomial"]
_AUTO_SEARCH_K_FOLDS = 3


class _BestModelWorker(QtCore.QThread):
    """calibrate_best 를 UI 스레드 밖에서 실행해 창 멈춤(응답없음)을 막는다.

    OpenCV 연산은 실행 중 GIL 을 풀어 Qt 이벤트 루프가 계속 돌므로 탐색(수십 초)
    동안에도 창이 응답 상태를 유지한다. 결과/오류는 시그널로 UI 스레드에 전달.
    """

    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, session, models, k_folds):
        super().__init__()
        self._session = session
        self._models = models
        self._k_folds = k_folds

    def run(self):
        try:
            report = self._session.calibrate_best(
                models=self._models, k_folds=self._k_folds
            )
        except Exception as exc:  # noqa: BLE001 — UI 스레드로 문자열만 전달
            self.failed.emit(str(exc))
            return
        self.done.emit(report)


def _button_style(bg, hover, fg="white"):
    """액션 버튼용 색상 스타일시트(hover·disabled 상태 포함)."""
    return (
        "QPushButton{background:%s;color:%s;border:none;border-radius:4px;"
        "padding:7px;font-weight:bold;}"
        "QPushButton:hover{background:%s;}"
        "QPushButton:disabled{background:#b8c0cc;color:#eef;}" % (bg, fg, hover)
    )


def list_capture_cameras():
    """v4l by-id 에서 캡처 노드(-video-index0)만 열거. 반환 [(serial, device_index)]."""
    cameras = []
    for link in sorted(glob.glob("/dev/v4l/by-id/*-video-index0")):
        real = os.path.realpath(link)  # /dev/videoN
        base = os.path.basename(real)
        if not base.startswith("video"):
            continue
        device_index = int(base[len("video"):])
        serial = os.path.basename(link).split("-video-index")[0].split("_")[-1]
        cameras.append((serial, device_index))
    return sorted(cameras, key=lambda c: c[1])


def _apply_v4l2_controls(device_index, power_line_frequency):
    """안티밴딩(전원주파수) 등 V4L2 제어 적용(best-effort, Linux 한정).

    OpenCV VideoCapture 는 power_line_frequency 프로퍼티가 없어 v4l2-ctl 로 설정한다.
    C++ 퍼블리셔와 동일 값(공용 config)을 적용해 밴딩을 방지한다.
    """
    try:
        subprocess.run(
            ["v4l2-ctl", "-d", "/dev/video%d" % device_index,
             "--set-ctrl", "power_line_frequency=%d" % power_line_frequency],
            check=False, timeout=3, capture_output=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def draw_overlay(frame, kind, detection):
    """검출 기하를 프레임 위에 렌더한다(표현 계층 담당)."""
    if kind == "charuco":
        r = detection.get("charuco")
        if r and r["marker_ids"] is not None:
            cv2.aruco.drawDetectedMarkers(frame, r["marker_corners"], r["marker_ids"])
        if r and r["charuco_ids"] is not None:
            cv2.aruco.drawDetectedCornersCharuco(
                frame, r["charuco_corners"], r["charuco_ids"], (0, 0, 255)
            )
    else:
        pts = detection.get("points")
        if pts is not None:
            size = detection.get("pattern_size")
            cv2.drawChessboardCorners(frame, size, pts, True)


class CalibrationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Intrinsic Calibration — Station")
        self.session = CalibrationSession()  # 모든 로직은 세션이 소유
        self.cam_cfg = load_camera_config()["capture"]  # 공용 config(캡처 설정)
        self.capture = None  # cv2.VideoCapture (카메라는 UI 소유)
        self.frame_count = 0
        self.last_detection = None  # 프리뷰 오버레이용(세션 검출 결과 캐시)
        self._best_worker = None  # 자동 모델 탐색 백그라운드 스레드 핸들

        self._build_ui()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._on_frame)
        self._sync_session()

    # ---- UI 구성 ----
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)

        self.view = QtWidgets.QLabel("카메라를 연결하세요")
        self.view.setMinimumSize(960, 540)
        self.view.setAlignment(QtCore.Qt.AlignCenter)
        self.view.setStyleSheet("background:#222;color:#aaa;")
        root.addWidget(self.view, 3)

        panel = QtWidgets.QVBoxLayout()
        root.addLayout(panel, 1)

        cam_row = QtWidgets.QHBoxLayout()
        cam_row.addWidget(QtWidgets.QLabel("카메라"))
        self.device_combo = QtWidgets.QComboBox()
        cam_row.addWidget(self.device_combo, 1)
        self.refresh_btn = QtWidgets.QPushButton("↻")
        self.refresh_btn.setFixedWidth(32)
        self.refresh_btn.clicked.connect(self._refresh_cameras)
        self.refresh_btn.setStyleSheet(_button_style("#6c757d", "#565e64"))  # 회색(보조)
        cam_row.addWidget(self.refresh_btn)
        panel.addLayout(cam_row)

        self.connect_btn = QtWidgets.QPushButton("연결")
        self.connect_btn.clicked.connect(self._toggle_camera)
        self.connect_btn.setStyleSheet(_button_style("#17a2b8", "#128298"))  # 청록(연결)
        panel.addWidget(self.connect_btn)

        pat_row = QtWidgets.QHBoxLayout()
        pat_row.addWidget(QtWidgets.QLabel("패턴"))
        self.pattern_combo = QtWidgets.QComboBox()
        self.pattern_combo.addItems([name for name, _ in _PATTERN_ITEMS])
        self.pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        pat_row.addWidget(self.pattern_combo, 1)
        panel.addLayout(pat_row)

        model_row = QtWidgets.QHBoxLayout()
        model_row.addWidget(QtWidgets.QLabel("왜곡모델"))
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.addItems([name for name, _ in _MODEL_ITEMS])
        self.model_combo.currentIndexChanged.connect(self._sync_session)
        model_row.addWidget(self.model_combo, 1)
        panel.addLayout(model_row)

        grid = QtWidgets.QGridLayout()
        self.cols_label = QtWidgets.QLabel("cols(내부)")
        grid.addWidget(self.cols_label, 0, 0)
        self.cols_spin = QtWidgets.QSpinBox()
        self.cols_spin.setRange(3, 30)
        self.cols_spin.setValue(5)  # 150mm ChArUco 보드 기본(5x5)
        grid.addWidget(self.cols_spin, 0, 1)
        self.rows_label = QtWidgets.QLabel("rows(내부)")
        grid.addWidget(self.rows_label, 1, 0)
        self.rows_spin = QtWidgets.QSpinBox()
        self.rows_spin.setRange(3, 30)
        self.rows_spin.setValue(5)  # 150mm ChArUco 보드 기본(5x5)
        grid.addWidget(self.rows_spin, 1, 1)
        self.square_label = QtWidgets.QLabel("square(mm)")
        grid.addWidget(self.square_label, 2, 0)
        self.square_spin = QtWidgets.QDoubleSpinBox()
        self.square_spin.setRange(1.0, 500.0)
        self.square_spin.setValue(30.0)  # 150mm 보드 square 30mm
        grid.addWidget(self.square_spin, 2, 1)
        self.marker_label = QtWidgets.QLabel("marker(mm)")
        grid.addWidget(self.marker_label, 3, 0)
        self.marker_spin = QtWidgets.QDoubleSpinBox()
        self.marker_spin.setRange(1.0, 500.0)
        self.marker_spin.setValue(21.6)
        grid.addWidget(self.marker_spin, 3, 1)
        self.dict_label = QtWidgets.QLabel("dict")
        grid.addWidget(self.dict_label, 4, 0)
        self.dict_combo = QtWidgets.QComboBox()
        self.dict_combo.addItems(_ARUCO_DICTS)
        grid.addWidget(self.dict_combo, 4, 1)
        panel.addLayout(grid)
        for w in (self.cols_spin, self.rows_spin, self.square_spin,
                  self.marker_spin):
            w.valueChanged.connect(self._sync_session)
        self.dict_combo.currentIndexChanged.connect(self._sync_session)

        self.detect_label = QtWidgets.QLabel("검출: -")
        self.detect_label.setStyleSheet("font-weight:bold;")
        panel.addWidget(self.detect_label)

        self.capture_btn = QtWidgets.QPushButton("캡처 (현재 프레임)")
        self.capture_btn.clicked.connect(self._manual_capture)
        self.capture_btn.setEnabled(False)
        self.capture_btn.setStyleSheet(_button_style("#1e6fff", "#1558cc"))  # 파랑
        panel.addWidget(self.capture_btn)

        auto_row = QtWidgets.QHBoxLayout()
        self.auto_chk = QtWidgets.QCheckBox("자동 캡처")
        auto_row.addWidget(self.auto_chk)
        auto_row.addWidget(QtWidgets.QLabel("목표"))
        self.target_spin = QtWidgets.QSpinBox()
        self.target_spin.setRange(5, 100)
        self.target_spin.setValue(50)
        self.target_spin.valueChanged.connect(self._sync_session)
        auto_row.addWidget(self.target_spin)
        panel.addLayout(auto_row)

        self.count_label = QtWidgets.QLabel("수집: 0 / 50 장")
        panel.addWidget(self.count_label)

        self.clear_btn = QtWidgets.QPushButton("수집 초기화")
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setStyleSheet(_button_style("#e0533d", "#c23b28"))  # 빨강(파괴적)
        panel.addWidget(self.clear_btn)

        self.calib_btn = QtWidgets.QPushButton("캘리브레이션 실행")
        self.calib_btn.clicked.connect(self._run_calibration)
        self.calib_btn.setStyleSheet(_button_style("#2ea44f", "#268a43"))  # 초록(주 실행)
        panel.addWidget(self.calib_btn)

        self.best_btn = QtWidgets.QPushButton("자동 모델 탐색 (교차검증)")
        self.best_btn.clicked.connect(self._run_best_model_search)
        self.best_btn.setStyleSheet(_button_style("#6f42c1", "#59359a"))  # 보라(자동 탐색)
        panel.addWidget(self.best_btn)

        self.result = QtWidgets.QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setMinimumHeight(150)
        # 하단을 채우도록 확장 고정(stretch=1) + addStretch 제거 → 텍스트 갱신 시
        # 내부 스크롤만 하고 다른 위젯을 밀지 않음(흔들림 방지).
        panel.addWidget(self.result, 1)

        # 자동 캡처 거부 사유는 **맨 아래(모든 버튼·로그 밑)**에 고정 높이로 둔다 —
        # word-wrap 로 1↔2줄이 바뀌어도 위쪽 버튼/위젯을 밀지 않아 레이아웃이 안정된다.
        self.auto_reason_label = QtWidgets.QLabel("")
        self.auto_reason_label.setWordWrap(True)
        self.auto_reason_label.setFixedHeight(40)
        self.auto_reason_label.setAlignment(QtCore.Qt.AlignTop)
        panel.addWidget(self.auto_reason_label)

        self._refresh_cameras()
        self.pattern_combo.setCurrentIndex(1)  # 기본 패턴 = ChArUco (150mm 5x5 보드)
        self._on_pattern_changed()

    # ---- 세션 동기화 (표현→도메인) ----
    def _kind(self):
        return _PATTERN_ITEMS[self.pattern_combo.currentIndex()][1]

    def _model(self):
        return _MODEL_ITEMS[self.model_combo.currentIndex()][1]

    def _sync_session(self, *_):
        self.session.auto_target = self.target_spin.value()
        self.session.model = self._model()
        changed = self.session.configure(
            self._kind(),
            self.cols_spin.value(),
            self.rows_spin.value(),
            self.square_spin.value(),
            self.marker_spin.value(),
            self.dict_combo.currentText(),
        )
        self._update_count()
        if changed:
            self.result.clear()

    def _on_pattern_changed(self, *_):
        kind = self._kind()
        charuco = kind == "charuco"
        for w in (self.marker_label, self.marker_spin, self.dict_label, self.dict_combo):
            w.setVisible(charuco)
        if charuco:
            self.cols_label.setText("squares_x")
            self.rows_label.setText("squares_y")
            self.square_label.setText("square(mm)")
        elif kind in ("circles", "acircles"):
            self.cols_label.setText("cols")
            self.rows_label.setText("rows")
            self.square_label.setText("spacing(mm)")
        else:
            self.cols_label.setText("cols(내부)")
            self.rows_label.setText("rows(내부)")
            self.square_label.setText("square(mm)")
        self._sync_session()

    def _update_count(self):
        self.count_label.setText(
            "수집: %d / %d 장" % (self.session.count, self.session.auto_target)
        )

    # ---- 카메라 (UI 소유) ----
    def _refresh_cameras(self):
        self.device_combo.clear()
        for serial, device_index in list_capture_cameras():
            self.device_combo.addItem("%s  (video%d)" % (serial, device_index), device_index)
        if self.device_combo.count() == 0:
            self.device_combo.addItem("카메라 없음", -1)

    def _toggle_camera(self):
        if self.capture is None:
            idx = self.device_combo.currentData()
            if idx is None or idx < 0:
                QtWidgets.QMessageBox.warning(self, "오류", "선택된 카메라 없음")
                return
            cfg = self.cam_cfg
            # 안티밴딩은 OpenCV 가 장치를 열기 전에(별도 fd) 적용 — 동시 fd 충돌 방지
            # (C++ 노드와 동일 순서).
            _apply_v4l2_controls(idx, int(cfg["power_line_frequency"]))
            # V4L2 백엔드 명시(중요): 기본 GStreamer 백엔드는 MJPG FOURCC 를 'unhandled
            # property' 로 무시하고 파이프라인이 'Internal data stream error' 로 깨져
            # 0x0·무프레임이 된다(로그 확인). C++ 퍼블리셔도 cv::CAP_V4L2 사용.
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                QtWidgets.QMessageBox.warning(self, "오류", "video%d 열기 실패" % idx)
                return
            # MJPG: USB 2.0 대역 절감(무압축 YUYV 회피).
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*str(cfg["pixel_format"])))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cfg["image_width"]))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cfg["image_height"]))
            cap.set(cv2.CAP_PROP_FPS, float(cfg["framerate"]))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, int(cfg["buffersize"]))
            for _ in range(3):  # 워밍업 — 파이프라인 안정화 후 정확한 해상도 리드백
                cap.read()
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print("camera video%d: %dx%d %s plf=%s"
                  % (idx, actual_w, actual_h, cfg["pixel_format"], cfg["power_line_frequency"]))
            self.capture = cap
            self.connect_btn.setText("연결 해제  (%dx%d)" % (actual_w, actual_h))
            self.device_combo.setEnabled(False)
            self.capture_btn.setEnabled(True)
            self.frame_count = 0
            self.last_detection = None
            self.timer.start(30)
        else:
            self._close_camera()

    def _close_camera(self):
        self.timer.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.connect_btn.setText("연결")
        self.device_combo.setEnabled(True)
        self.capture_btn.setEnabled(False)
        self.last_detection = None
        self.view.setText("카메라 연결 해제됨")

    # ---- 프레임 루프 (표시) ----
    def _on_frame(self):
        ok, frame = self.capture.read()
        if not ok:
            return
        h, w = frame.shape[:2]
        image_size = (w, h)
        self.frame_count += 1

        # 깨끗한 gray 를 1회만 계산 — 검출·캡처가 **동일한 비오염 프레임**을 쓰게 한다.
        # (오버레이를 먼저 그린 뒤 재검출하면 그림이 마커를 덮어 코너가 줄어든다 — 버그.)
        kind = self.session.kind
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 프리뷰 검출: 체커보드/원형은 3프레임마다(부하 완화), charuco 는 매 프레임.
        if kind == "charuco" or self.frame_count % 3 == 0:
            det = self.session.detect_preview(gray)
            det["pattern_size"] = self.session.pattern_size()
            self.last_detection = det
            self._show_status(det)

        # 자동 캡처 + 하단 사유는 현재 프레임 기준(오버레이 전 깨끗한 gray 사용).
        found = bool(self.last_detection and self.last_detection.get("found"))
        if not self.auto_chk.isChecked() or self.session.reached_target:
            self._show_auto_reason("")  # 자동 off / 완료 → 안내 없음
        elif not found:
            self._show_auto_reason("no_detect")  # 현재 프레임에 보드 없음
        else:
            ok_cap, reason = self.session.capture(gray, image_size, self.frame_count, auto=True)
            if ok_cap:
                self._update_count()
                self._show_auto_reason("captured")
                if self.session.reached_target:
                    self.auto_chk.setChecked(False)
                    self._run_calibration()
            else:
                self._show_auto_reason(reason)

        # 오버레이는 검출·캡처가 끝난 뒤 **표시용으로만** 그린다(검출 프레임 오염 방지).
        if self.last_detection is not None:
            draw_overlay(frame, kind, self.last_detection)
        self._show(frame)

    # 자동 캡처 거부 사유 → 사용자 안내(cooldown/captured 는 일시적이라 라벨 클리어).
    _AUTO_REASON_MSG = {
        "captured": ("", ""),
        "cooldown": ("", ""),
        "no_detect": ("보드가 안 보임 — 전체가 프레임 안에 들어오게", "orange"),
        "moving": ("움직이는 중 — 자세를 잡고 1초 정지 후 캡처됩니다", "red"),
        "not_novel": ("자세가 기존과 유사 — 위치를 옮기거나 더 기울여 주세요", "orange"),
        "blurry": ("흔들림/초점 흐림 — 정지 후 초점·조명 확인", "red"),
    }

    def _show_auto_reason(self, reason):
        msg, color = self._AUTO_REASON_MSG.get(reason, (reason, "gray"))
        self.auto_reason_label.setText(("⏸ " + msg) if msg else "")
        self.auto_reason_label.setStyleSheet(("color:%s;" % color) if msg else "")

    def _frame_is_good(self, det):
        """현재 프레임이 '문제 없음'(검출 양호 + 충분한 코너 + 정지)인지."""
        if not det.get("found"):
            return False
        mc = self.session.max_capture_motion
        if mc > 0 and det.get("motion", 1.0) > mc:  # 움직이는 중
            return False
        if det.get("kind") == "charuco":  # 캘리브레이션 가능 코너 >= 6
            r = det.get("charuco") or {}
            n = 0 if r.get("charuco_ids") is None else len(r["charuco_ids"])
            return n >= 6
        return True

    def _show_status(self, det):
        if not det.get("found"):
            self.detect_label.setText("검출: ❌ " + det.get("status", "없음"))
            self.detect_label.setStyleSheet("font-weight:bold;color:red;")
        elif self._frame_is_good(det):
            self.detect_label.setText("🟦 문제 없음 — " + det.get("status", ""))
            self.detect_label.setStyleSheet("font-weight:bold;color:#1e6fff;")
        else:
            self.detect_label.setText("검출: ✅ " + det.get("status", ""))
            self.detect_label.setStyleSheet("font-weight:bold;color:green;")

    def _show(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        img = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(img.copy()).scaled(
            self.view.width(), self.view.height(), QtCore.Qt.KeepAspectRatio
        )
        self.view.setPixmap(pix)

    # ---- 사용자 액션 → 세션 위임 ----
    def _manual_capture(self):
        if self.capture is None:
            return
        ok, frame = self.capture.read()
        if not ok:
            return
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ok_cap, reason = self.session.capture(gray, (w, h), self.frame_count, auto=False)
        if ok_cap:
            self._update_count()
        else:
            QtWidgets.QMessageBox.information(self, "캡처", "검출 실패 — 자세 조정 (%s)" % reason)

    def _clear(self):
        self.session.clear()
        self._update_count()
        self.result.clear()

    def _result_lines(self, res):
        """캘리 결과 dict 를 표시용 텍스트 라인 리스트로 만든다."""
        k = res["K"]
        lines = [
            "model : %s" % res["model"],
            "views : %d 사용" % res.get("used_views", self.session.count),
            "rms   : %.4f px" % res["rms"],
        ]
        dropped = res.get("dropped", 0)
        if dropped:
            lines.append(
                "  ↳ 아웃라이어 %d뷰 제거 (rms %.3f→%.3f)"
                % (dropped, res.get("rms_before", res["rms"]), res["rms"])
            )
        lines += [
            "fx=%.2f fy=%.2f" % (k[0, 0], k[1, 1]),
            "cx=%.2f cy=%.2f" % (k[0, 2], k[1, 2]),
            "D = %s" % np.array2string(res["D"], precision=5, suppress_small=True),
        ]
        return lines

    def _run_calibration(self):
        try:
            res = self.session.calibrate()
        except Exception as exc:  # noqa: BLE001 — 모달 대신 로그 박스에 표시(흔들림 방지)
            self.result.setPlainText("캘리브레이션 실패:\n%s" % exc)
            return
        self.result.setPlainText("\n".join(self._result_lines(res)))

    def _run_best_model_search(self):
        """자동 모델 탐색을 백그라운드 스레드에서 시작(UI 멈춤 방지)."""
        if self._best_worker is not None and self._best_worker.isRunning():
            return  # 이미 실행 중 — 중복 방지
        # 탐색 중 프레임 자동캡처가 session.collected 를 건드리지 않도록 타이머 정지.
        self.timer.stop()
        for btn in (self.best_btn, self.calib_btn, self.capture_btn, self.clear_btn):
            btn.setEnabled(False)
        self.result.setPlainText(
            "자동 모델 탐색 중… (모델·폴드별 캘리, 수십 초 소요)\n창은 응답 상태를 유지합니다."
        )
        worker = _BestModelWorker(
            self.session, _AUTO_SEARCH_MODELS, _AUTO_SEARCH_K_FOLDS
        )
        worker.done.connect(self._on_best_done)
        worker.failed.connect(self._on_best_failed)
        worker.finished.connect(self._on_best_finished)
        self._best_worker = worker
        worker.start()

    def _on_best_done(self, report):
        best = report["best_model"]
        lines = ["자동 모델 탐색 (교차검증 held-out RMS)",
                 "후보: %s" % ", ".join(_AUTO_SEARCH_MODELS),
                 "%-20s %9s %9s" % ("model", "full_rms", "cv_rms")]
        for r in report["report"]:
            if "error" in r:
                lines.append("%-20s   실패: %s" % (r["model"], r["error"][:30]))
                continue
            mark = "  ← 선택" if r["model"] == best else ""
            lines.append("%-20s %9.4f %9.4f%s"
                         % (r["model"], r["full_rms"], r["cv_error"], mark))
        lines.append("(선택 기준: cv_rms 최저. full_rms 는 참고 — 계수 많을수록 낮아짐)")
        lines.append("-" * 40)
        lines += self._result_lines(report["best"])
        self.result.setPlainText("\n".join(lines))
        # 드롭다운을 최적 모델로 동기화(세션은 이미 calibrate_best 에서 갱신됨).
        for i, (_, value) in enumerate(_MODEL_ITEMS):
            if value == best:
                self.model_combo.blockSignals(True)
                self.model_combo.setCurrentIndex(i)
                self.model_combo.blockSignals(False)
                break

    def _on_best_failed(self, msg):
        self.result.setPlainText("자동 모델 탐색 실패:\n%s" % msg)

    def _on_best_finished(self):
        """스레드 종료 후 UI 복구(성공/실패 공통)."""
        for btn in (self.best_btn, self.calib_btn, self.clear_btn):
            btn.setEnabled(True)
        self.capture_btn.setEnabled(self.capture is not None)
        if self.capture is not None:
            self.timer.start(30)  # 카메라 활성 시 프리뷰 재개
        self._best_worker = None

    def closeEvent(self, event):
        # 탐색 스레드가 돌면 완료까지 대기(QThread 파괴 경고·크래시 방지).
        if self._best_worker is not None and self._best_worker.isRunning():
            self._best_worker.wait()
        self._close_camera()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication([])
    win = CalibrationWindow()
    win.resize(1280, 680)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
