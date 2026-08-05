#!/usr/bin/env python3
"""시험 GUI — 위젯 트리는 원본 `Tools/amr_test_gui/gui.py` 와 **동일**, 백엔드만 갈아 끼운다.

설계 근거: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`.

## 화면 구성 (원본과 1:1)

| 열 | 내용 |
|---|---|
| 1 | 연결(판다 목록·검색 · USB · 제어권) + 로그 + Seer 로그·Fatal 리셋 |
| 2 | 조그 3×3 + 호밍 · 모터 값 표 · Seer 값 표 · 설정(속도·정착 허용치) |
| 3 | 차량 바퀴 그림 · 앞뒤 조향 슬라이더 |
| 하단 | Seer 접속 상태 바 |

**추가 버튼이 없다** — E-stop 도, 호밍 취소도 원본에 없으므로 여기에도 없다
(취소 미노출 근거: ADR §Decision ②).

## 백엔드가 못 하는 기능

버튼을 **지우지 않고 비활성 + 사유 툴팁**으로 남긴다. 그래야 화면이 항상 같고 무엇이 다른지가
드러난다 — 실기 비교에서 「UI 는 같다」를 눈으로 확인할 수 있어야 하기 때문이다.

## Seer

Seer 조회(1040·1050·4300)는 **네트워크 전용이라 백엔드와 무관**하다. 원본과 같이 앱이 직접 한다.
"""
from __future__ import annotations

import math
import threading
import time

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
                             QPushButton, QSlider, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .backend_base import CAP_HOME, CAP_SCAN, CAP_USB

STEER_NODES = (3, 4)
DRIVE_NODES = (1, 2)
STEER_LIMIT_DEG = 90

# 조그 방향표 — 원본 `gui.py:85-94` 와 **같은 값**(직접 실측 2건 + 도출 6건).
#   ① 조향 홈(0°) + raw 음수 → 전진(+x)   ② 조향 +90° + raw 양수 → 좌(IMU 실증)
SEER_RESTORE_TIMEOUT_S = 20.0   # 반환 전 조향 복원 대기 한도
SEER_MATCH_TOL_DEG = 3.0        # CAN 실측 ↔ Seer 판독 허용 차
SEER_MATCH_STREAK = 5           # 이만큼 **연속** 어긋나야 경보 — 과도 표본으로 떠들지 않는다
SEER_MATCH_REWARN_S = 30.0      # 같은 축 재경보 최소 간격

JOG = {
    "전진":     (0.0,  -1, True),
    "후진":     (0.0,  +1, True),
    "좌 크랩":  (90.0, +1, True),
    "우 크랩":  (90.0, -1, True),
    "좌전 45°": (-45.0, -1, False),
    "우전 45°": (45.0,  -1, False),
    "좌후 45°": (45.0,  +1, False),
    "우후 45°": (-45.0, +1, False),
}


class WheelView(QWidget):
    """차량 바퀴 top-view — 원본 `gui.py:108-180` 과 같은 기하·같은 각도 규약.

    Front(node3) x=+0.604 m · Rear(node4) x=−0.596 m · 휠반경 0.125 m (시각화 전용 근사).
    좌표 +x 전방(화면 위) · +y 좌(화면 왼쪽). 바퀴 지향 = (cos θ, −sin θ).
    """

    FRONT_X, REAR_X = 0.604, -0.596
    WHEEL_R = 0.125
    BODY_L, BODY_W = 1.60, 0.90

    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 320)
        self.front_deg = 0.0
        self.rear_deg = 0.0

    def set_angles(self, front_deg: float, rear_deg: float):
        self.front_deg, self.rear_deg = float(front_deg), float(rear_deg)
        self.update()

    def _px(self, x_m: float, y_m: float, s: float) -> QPointF:
        c = self.rect().center()
        return QPointF(c.x() - y_m * s, c.y() - x_m * s)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#ffffff"))
        s = max(20.0, min((self.height() - 70) / (self.BODY_L * 1.1),
                          (self.width() - 70) / (self.BODY_W * 1.1)))
        tl = self._px(self.BODY_L / 2, self.BODY_W / 2, s)
        br = self._px(-self.BODY_L / 2, -self.BODY_W / 2, s)
        body = QRectF(tl, br).normalized()
        p.setPen(QPen(QColor("#8c9aa8"), 2))
        p.setBrush(QBrush(QColor("#eef2f6")))
        p.drawRoundedRect(body, 10, 10)
        f = QFont()
        f.setPointSize(8)
        p.setFont(f)
        p.setPen(QPen(QColor("#7b8794"), 1))
        p.drawText(QRectF(body.left(), body.top() - 20, body.width(), 18),
                   Qt.AlignHCenter, "▲ 전방")
        for x_m, deg, name in ((self.FRONT_X, self.front_deg, "Front"),
                               (self.REAR_X, self.rear_deg, "Rear")):
            self._draw_wheel(p, self._px(x_m, -0.0014, s), deg, s, name)
        p.end()

    def _draw_wheel(self, p, ctr, deg, s, name):
        th = math.radians(deg)
        ux, uy = math.cos(th), -math.sin(th)
        ax, ay = -uy, -ux
        bx, by = -ay, ax
        L = self.WHEEL_R * 2.0 * s
        W = max(8.0, self.WHEEL_R * 0.62 * s)
        pts = [QPointF(ctr.x() + ax * L / 2 + bx * W / 2, ctr.y() + ay * L / 2 + by * W / 2),
               QPointF(ctr.x() + ax * L / 2 - bx * W / 2, ctr.y() + ay * L / 2 - by * W / 2),
               QPointF(ctr.x() - ax * L / 2 - bx * W / 2, ctr.y() - ay * L / 2 - by * W / 2),
               QPointF(ctr.x() - ax * L / 2 + bx * W / 2, ctr.y() - ay * L / 2 + by * W / 2)]
        p.setPen(QPen(QColor("#1e8449"), 2.4))
        p.setBrush(QBrush(QColor(30, 132, 73, 60)))
        p.drawPolygon(QPolygonF(pts))
        p.setPen(QPen(QColor("#22303c"), 1))
        p.setBrush(Qt.NoBrush)
        self._draw_arrow(p, ctr, ax, ay, L * 0.72)
        p.drawEllipse(ctr, 3.0, 3.0)
        p.drawText(QRectF(ctr.x() + 22, ctr.y() - 10, 120, 20),
                   Qt.AlignLeft | Qt.AlignVCenter, f"{name}  {deg:+.1f}°")

    def _draw_arrow(self, p: QPainter, ctr: QPointF, ax: float, ay: float, length: float):
        """바퀴 지향 화살표. **사각형만으로는 +90° 와 −90° 가 똑같이 보인다** — 방향을 드러낸다.

        `(ax, ay)` 는 이미 화면 좌표계로 변환된 지향 단위벡터다(+각 방향).
        """
        tip = QPointF(ctr.x() + ax * length, ctr.y() + ay * length)
        p.setPen(QPen(QColor("#c0392b"), 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawLine(ctr, tip)
        head = max(6.0, length * 0.28)
        for sign in (+1, -1):                       # 화살촉 두 날개(지향 기준 ±150°)
            a = math.atan2(ay, ax) + sign * math.radians(150.0)
            p.drawLine(tip, QPointF(tip.x() + math.cos(a) * head,
                                    tip.y() + math.sin(a) * head))


def _toggle(text: str, on_bg: str, on_border: str) -> QPushButton:
    b = QPushButton(text)
    b.setCheckable(True)
    b.setMinimumHeight(34)
    b.setStyleSheet(
        "QPushButton { background:#e8edf2; font-weight:bold; border:1px solid #b7c2cc;"
        " border-radius:4px; }"
        "QPushButton:disabled { background:#f0f2f5; color:#8894a2; }"
        f"QPushButton:checked {{ background:{on_bg}; color:white; border:1px solid {on_border}; }}")
    return b


class MainWindow(QWidget):
    """원본과 같은 3열 배치. 차이는 **어느 백엔드가 지령을 내보내는가**뿐이다."""

    log_line = pyqtSignal(str)
    seer_log_line = pyqtSignal(str)
    seer_data = pyqtSignal(dict)
    seer_status = pyqtSignal(str, bool)
    alarm_counts = pyqtSignal(int, int)
    op_done = pyqtSignal(str, bool, str)      # (작업이름, 성공, 메시지)

    ROWS = ("1  F.W", "2  R.W", "3  F.S", "4  R.S")
    CELL_FMT = ((1, "{:+.1f}"), (2, "{:+.1f}"), (3, "{:+.2f}"))

    def __init__(self, backend, seer_ip="192.168.44.82",
                 seer_gui_path="/home/nvidia/T-Robot_seer_gui", seer_enabled=True):
        super().__init__()
        self.be = backend
        self._seer_ip = seer_ip
        self._seer_gui_path = seer_gui_path
        self._seer_run = bool(seer_enabled)
        self._seer_deg = {}
        self._seer_at_take = {}   # 제어권 잡기 직전 Seer 조향각(반환 시 복원 기준)
        self._steer_commanded = False   # 이번 세션에서 조향을 보냈는가(대조 중단 조건)
        self._seer_mismatch_streak = {}
        self._seer_mismatch_warned_at = {}
        self._alarm_tick = 0
        self._alarm_seen = set()
        self._jog_th = None
        self._jog_stop = False
        self._homing = False
        self._released = False

        self.setWindowTitle(f"Tongyi 4축 AMR 구동 테스트 GUI [{self.be.name}]")
        self.resize(1200, 800)

        root = QVBoxLayout(self)
        row = QHBoxLayout()
        root.addLayout(row, 1)
        self.box1 = QGroupBox("CAN-Relay 연결")
        self.box2 = QGroupBox("2")
        self.box3 = QGroupBox("3")

        left = QVBoxLayout(self.box1)
        left.addWidget(self._build_connect(), 0)
        left.addWidget(self._build_log(), 1)

        mid = QVBoxLayout(self.box2)
        mid.addWidget(self._build_jog(), 0)
        mid.addWidget(self._build_motors(), 0)
        mid.addWidget(self._build_seer(), 0)
        mid.addWidget(self._build_settings(), 0)
        mid.addStretch(1)

        right = QVBoxLayout(self.box3)
        right.addWidget(self._build_wheel(), 1)
        right.addWidget(self._build_wheel_adj(), 0)
        for box in (self.box1, self.box2, self.box3):
            row.addWidget(box, 1)
        root.addWidget(self._build_status(), 0)

        self.log_line.connect(self.log)
        self.seer_log_line.connect(self.seer_log)
        self.seer_data.connect(self._on_seer_data)
        self.seer_status.connect(self._on_seer_status)
        self.alarm_counts.connect(self._set_alarm_color)
        self.op_done.connect(self._on_op_done)

        self._apply_capabilities()
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._refresh)
        self._ui_timer.start(100)

        if self._seer_run:
            threading.Thread(target=self._seer_loop, daemon=True, name="seer").start()
        self.log(f"GUI 기동 — 백엔드 '{self.be.name}'")
        if self.be.can(CAP_SCAN):
            self._run_op("검색", self.be.scan)

    # ── capability 반영 ───────────────────────────────────────────────
    def _apply_capabilities(self):
        """못 쓰는 버튼은 **지우지 않고** 비활성 + 사유 툴팁."""
        for cap, widgets in ((CAP_SCAN, [self.btn_scan]),
                             (CAP_USB, [self.btn_usb]),
                             (CAP_HOME, [self.btn_home])):
            if not self.be.can(cap):
                why = self.be.why_not(cap)
                for w in widgets:
                    w.setEnabled(False)
                    w.setToolTip(why)
        if not self.be.can(CAP_USB):
            # USB 단계가 없으면 제어권은 처음부터 누를 수 있어야 한다.
            self.btn_take.setEnabled(True)
            self.lab_panda.setText("드라이버가 소유")

    # ── 화면 ──────────────────────────────────────────────────────────
    def _build_connect(self) -> QGroupBox:
        g = QGroupBox("연결")
        v = QVBoxLayout(g)
        v.addWidget(QLabel("연결 가능한 판다"))
        pick = QHBoxLayout()
        self.lab_panda = QLabel("검색 전")
        self.lab_panda.setStyleSheet(
            "padding:5px 8px; border:1px solid #cfd8e0; border-radius:3px; color:#5d6d7e;")
        self.btn_scan = QPushButton("검색")
        self.btn_scan.setMinimumHeight(28)
        self.btn_scan.clicked.connect(lambda: self._run_op("검색", self.be.scan))
        pick.addWidget(self.lab_panda, 1)
        pick.addWidget(self.btn_scan, 0)
        v.addLayout(pick)

        self.btn_usb = _toggle("판다 USB 연결", "#1e8449", "#166437")
        self.btn_usb.toggled.connect(self._on_usb)
        v.addWidget(self.btn_usb)

        self.btn_take = _toggle("제어권 획득", "#b9770e", "#8a5a0a")
        self.btn_take.setEnabled(False)
        self.btn_take.toggled.connect(self._on_take)
        v.addWidget(self.btn_take)
        return g

    def _build_jog(self) -> QGroupBox:
        g = QGroupBox("로봇 조그")
        v = QVBoxLayout(g)
        grid = QGridLayout()
        grid.setSpacing(4)
        pad = {
            (0, 0): ("↖", "좌전 45°", False), (0, 1): ("↑", "전진", True),
            (0, 2): ("↗", "우전 45°", False),
            (1, 0): ("←", "좌 크랩", True), (1, 1): ("■", "정지", True),
            (1, 2): ("→", "우 크랩", True),
            (2, 0): ("↙", "좌후 45°", False), (2, 1): ("↓", "후진", True),
            (2, 2): ("↘", "우후 45°", False),
        }
        for (r, c), (arrow, label, verified) in pad.items():
            b = QPushButton(f"{arrow}\n{label}" + ("" if verified else "  ⚠"))
            b.setMinimumHeight(52)
            b.setStyleSheet(
                "QPushButton { padding:2px; %s }"
                "QPushButton:disabled { color:#8894a2; }"
                % ("font-weight:bold;" if label == "정지" else
                   ("color:#b9770e;" if not verified else "")))
            b.clicked.connect(lambda _=False, t=label: self._jog(t))
            grid.addWidget(b, r, c)
        v.addLayout(grid)

        self.btn_home = QPushButton("⌂  조향 원점 복귀 (호밍)")
        self.btn_home.setMinimumHeight(38)
        self.btn_home.setStyleSheet(
            "QPushButton { background:#5b6b7c; color:white; font-weight:bold;"
            " border:1px solid #44515e; border-radius:4px; margin-top:6px; }"
            "QPushButton:disabled { background:#e8edf2; color:#8894a2; }")
        self.btn_home.clicked.connect(self._homing_clicked)
        v.addWidget(self.btn_home)
        return g

    def _build_wheel_adj(self) -> QGroupBox:
        g = QGroupBox("앞뒤 바퀴 조정")
        v = QVBoxLayout(g)
        v.setSpacing(2)
        self.sld_front = QSlider(Qt.Horizontal)
        self.sld_rear = QSlider(Qt.Horizontal)
        self.lab_front = QLabel("+0°")
        self.lab_rear = QLabel("+0°")
        for node, name, sld, lab in ((3, "앞바퀴 (N3)", self.sld_front, self.lab_front),
                                     (4, "뒷바퀴 (N4)", self.sld_rear, self.lab_rear)):
            head = QHBoxLayout()
            head.addWidget(QLabel(name))
            head.addStretch(1)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            head.addWidget(lab)
            v.addLayout(head)
            sld.setRange(-STEER_LIMIT_DEG, STEER_LIMIT_DEG)
            sld.setValue(0)
            sld.setTickInterval(30)
            sld.setTickPosition(QSlider.TicksBelow)
            sld.setMinimumHeight(30)
            sld.setPageStep(5)
            sld.valueChanged.connect(lambda _v, n=node: self._on_wheel_changed(n))
            sld.sliderReleased.connect(lambda n=node: self._send_steer(n))
            v.addWidget(sld)
            v.addSpacing(4)
        return g

    def _build_settings(self) -> QGroupBox:
        g = QGroupBox("설정")
        grid = QGridLayout(g)
        grid.setSpacing(6)
        self.spn_speed = QSpinBox()
        self.spn_speed.setRange(0, 200)
        self.spn_speed.setValue(50)
        self.spn_speed.setSuffix(" mm/s")
        self.spn_speed.setToolTip("바퀴 속도. 상한 200 mm/s = vmax 0.2 m/s(config).\n"
                                  "검증 전에는 저속을 유지할 것.")
        self.spn_tol = QDoubleSpinBox()
        self.spn_tol.setRange(0.5, 10.0)
        self.spn_tol.setSingleStep(0.5)
        self.spn_tol.setValue(3.0)
        self.spn_tol.setSuffix(" °")
        self.spn_tol.setToolTip("정착 허용치 — 목표↔실측 편차가 이 값 이내여야 정착으로 본다.")
        for r, (lab, w) in enumerate((("바퀴 속도", self.spn_speed),
                                      ("정착 허용치", self.spn_tol))):
            grid.addWidget(QLabel(lab), r, 0)
            grid.addWidget(w, r, 1)
        grid.setColumnStretch(1, 1)
        return g

    @staticmethod
    def _motor_table(rpm_header: str) -> QTableWidget:
        t = QTableWidget(4, 4)
        t.setHorizontalHeaderLabels(["모터", "각도(°)", rpm_header, "전류(A)"])
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionMode(QTableWidget.NoSelection)
        t.verticalHeader().setDefaultSectionSize(26)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for r, name in enumerate(MainWindow.ROWS):
            t.setItem(r, 0, QTableWidgetItem(name))
            for c in (1, 2, 3):
                it = QTableWidgetItem("—")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(r, c, it)
        t.setFixedHeight(26 * 4 + t.horizontalHeader().height() + 8)
        return t

    @classmethod
    def _fill_row(cls, table, node, values):
        r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if r is None:
            return
        for (c, fmt), val in zip(cls.CELL_FMT, values):
            table.item(r, c).setText("—" if val is None else fmt.format(val))

    def _build_motors(self) -> QGroupBox:
        g = QGroupBox("모터 값")
        v = QVBoxLayout(g)
        self.tbl_motor = self._motor_table("회전(rpm)")
        v.addWidget(self.tbl_motor)
        return g

    def _build_seer(self) -> QGroupBox:
        g = QGroupBox("Seer 값 (비교)")
        v = QVBoxLayout(g)
        self.tbl_seer = self._motor_table("회전")
        v.addWidget(self.tbl_seer)
        return g

    def _build_wheel(self) -> QGroupBox:
        g = QGroupBox("차량 바퀴 상태")
        v = QVBoxLayout(g)
        self.wheel = WheelView()
        v.addWidget(self.wheel)
        return g

    def _build_log(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        g1 = QGroupBox("로그")
        v1 = QVBoxLayout(g1)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(2000)
        v1.addWidget(self.txt_log)
        v.addWidget(g1, 1)

        g2 = QGroupBox("Seer 로그")
        v2 = QVBoxLayout(g2)
        self.txt_seer_log = QPlainTextEdit()
        self.txt_seer_log.setReadOnly(True)
        self.txt_seer_log.setMaximumBlockCount(2000)
        v2.addWidget(self.txt_seer_log)
        self.btn_clear_fatal = QPushButton("Fatal 오류 리셋")
        self.btn_clear_fatal.setMinimumHeight(30)
        self.btn_clear_fatal.setToolTip(
            "Seer config API 4300 (robot_config_clearfatal_req) — Fatal 오류코드만 지운다.")
        self.btn_clear_fatal.clicked.connect(self._on_clear_fatal)
        self._set_alarm_color(0, 0)
        v2.addWidget(self.btn_clear_fatal)
        v.addWidget(g2, 1)
        return w

    def _build_status(self) -> QLabel:
        """하단 상태 바 — 원본과 같이 **Seer 접속 정보**를 보인다."""
        self.lab_status = QLabel(f"Seer {self._seer_ip} · 접속 시도 중…")
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; color:#5d6d7e;")
        return self.lab_status

    # ── 주기 갱신 ─────────────────────────────────────────────────────
    def _refresh(self):
        rows = self.be.motor_rows()
        for node in DRIVE_NODES + STEER_NODES:
            self._fill_row(self.tbl_motor, node, rows.get(node, (None, None, None)))
        for node in STEER_NODES:                      # CAN ↔ Seer 연속 대조(원본과 같은 절차)
            deg = self.be.meas_angle(node)
            if deg is not None:
                self._check_seer_agreement(node, deg)
        self._redraw_wheel()

        text, ok, engaged = self.be.status()
        if text != getattr(self, "_last_status", None):
            self._last_status = text
            self.log_line.emit(f"[{self.be.name}] {text}")
        if engaged != self.btn_take.isChecked():
            self.btn_take.blockSignals(True)
            self.btn_take.setChecked(engaged)
            self.btn_take.setText("제어권 해제" if engaged else "제어권 획득")
            self.btn_take.blockSignals(False)

    def _meas_angle(self, node):
        d = self.be.meas_angle(node)
        return d if d is not None else self._seer_deg.get(node)


    def _check_seer_agreement(self, node: int, deg: float):
        """CAN 실측과 Seer 판독이 같은 곳을 가리키는가 — **매 갱신 연속 대조**(원본 `gui.py` 와 동일).

        한 번 읽고 판정하지 않는다. 2026-08-05 실기에서 획득 직후 첫 표본이 +0.00° 로 읽혔다가
        곧 +15.807° 가 됐다(그 사이 조향 지령 없음). 과도 표본은 연속 조건이 걸러 낸다.
        ⚠ **우리가 조향을 보낸 뒤에는 대조하지 않는다.** 제어권을 쥐면 Seer 는 모터 실측을
        더 못 본다 — 2026-08-05 **API 1040 직접 호출**로 확인: 우리가 +20.000° 로 움직여도
        API 는 -15.807° 에 고정, 반환 후에야 갱신된다. 그 상태로 대조하면 정상 조작마다
        거짓 경보가 난다.
        어긋나면 **알리기만 한다** — 판단은 운용자 몫이고, 조용히 진행하는 것만 피한다.
        """
        if self._steer_commanded:      # 우리가 움직인 뒤 — Seer 값은 굳어 있어 비교 의미 없음
            return
        ref = self._seer_deg.get(node)
        if ref is None:
            self._seer_mismatch_streak[node] = 0
            return
        diff = deg - ref
        if abs(diff) <= SEER_MATCH_TOL_DEG:
            if self._seer_mismatch_streak.get(node, 0) >= SEER_MATCH_STREAK:
                self.log_line.emit(f"N{node} 조향 기준 회복 — Seer {ref:+.2f}° ↔ CAN {deg:+.2f}°")
            self._seer_mismatch_streak[node] = 0
            return
        n = self._seer_mismatch_streak.get(node, 0) + 1
        self._seer_mismatch_streak[node] = n
        if n < SEER_MATCH_STREAK:
            return
        now = time.monotonic()
        if now - self._seer_mismatch_warned_at.get(node, 0.0) < SEER_MATCH_REWARN_S:
            return
        self._seer_mismatch_warned_at[node] = now
        self.log_line.emit(
            f"⚠ N{node} 조향 기준 불일치 {n}회 연속 — Seer {ref:+.2f}° 인데 CAN 실측 "
            f"{deg:+.2f}° (차 {diff:+.2f}°). 0° 기준이 서로 다릅니다 — 조작 전 확인하세요")

    def _redraw_wheel(self):
        """실측 우선. 실측이 없을 때만 슬라이더를 미리보기로 쓴다.

        **슬라이더에는 되쓰지 않는다** — 되먹이면 방금 넣은 목표가 지워진다(원본 이력).
        """
        f, r = self._meas_angle(3), self._meas_angle(4)
        if f is None or r is None:
            f, r = self.sld_front.value(), self.sld_rear.value()
        self.wheel.set_angles(f, r)
        for node, sld, lab in ((3, self.sld_front, self.lab_front),
                               (4, self.sld_rear, self.lab_rear)):
            meas = self._meas_angle(node)
            lab.setText(f"{sld.value():+d}°" +
                        ("" if meas is None else f"  (실측 {meas:+.1f}°)"))

    # ── 조작 ──────────────────────────────────────────────────────────
    def log(self, msg: str):
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        self.txt_log.appendPlainText(line)
        print(f"[gui] {line}", flush=True)

    def seer_log(self, msg: str):
        self.txt_seer_log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {msg}")

    def _run_op(self, name: str, fn, *args):
        """블로킹 백엔드 호출을 작업 스레드로 돌린다 — UI 를 잡지 않는다."""
        def _op_work():
            try:
                ok, why = fn(*args)
            except Exception as exc:
                ok, why = False, f"{type(exc).__name__}: {exc}"
            self.op_done.emit(name, bool(ok), str(why))
        threading.Thread(target=_op_work, daemon=True, name=name).start()

    def _on_op_done(self, name: str, ok: bool, why: str):
        self.log(f"{name} — {why}" if ok else f"{name} 실패 — {why}")
        if name == "검색":
            # 콜론 쪼개기(`why.split(":")[-1]`)는 메시지에 콜론이 여럿이면 엉뚱한 조각을
            # 라벨에 올린다(2026-08-04 리뷰 Low ①). 알려진 접두사만 벗긴다.
            PREFIX = "판다 검출: "
            label = why[len(PREFIX):] if why.startswith(PREFIX) else why
            self.lab_panda.setText((label if ok else "검색 실패")[:48])
            if self.be.can(CAP_USB):
                self.btn_usb.setEnabled(ok)
        elif name == "USB":
            self.btn_take.setEnabled(ok and self.btn_usb.isChecked())
        elif name == "호밍":
            self._homing = False
            self.btn_home.setEnabled(True)

    def _on_usb(self, on: bool):
        self.btn_usb.setText("판다 USB 해제" if on else "판다 USB 연결")
        self._run_op("USB", self.be.set_usb, on)

    def _on_take(self, on: bool):
        """제어권 획득/반환. **인수인계는 Seer 기준으로 한다**(원본 `gui.py` 와 같은 절차).

        획득 전에 Seer 가 보던 조향각을 기억하고, 반환 전에 그 각도로 되돌려 놓고 넘긴다.
        되돌리지 않고 넘기면 Seer 가 자기 판단으로 조향을 움직인다 —
        2026-08-04 실기에서 반환 후 90° 까지 돌았다.
        """
        self.btn_take.setText("제어권 해제" if on else "제어권 획득")
        if on:
            self._steer_commanded = False   # 새 세션 — 대조를 다시 연다
            self._seer_at_take = {n: self._seer_deg.get(n) for n in STEER_NODES}
            have = {n: v for n, v in self._seer_at_take.items() if v is not None}
            self.log("인수인계 기준(Seer) — " +
                     (", ".join(f"N{n} {v:+.2f}°" for n, v in have.items()) if have
                      else "⚠ Seer 각도 없음 — 반환 시 복원할 기준이 없습니다"))
            self._run_op("제어권", self.be.set_engaged, True)
        else:
            self._run_op("제어권", self._release_with_handover)

    def _release_with_handover(self):
        """**작업 스레드에서** 실행: 조향 복원 → 제어권 반환. 위젯을 만지지 않는다."""
        targets = {n: v for n, v in getattr(self, "_seer_at_take", {}).items() if v is not None}
        if not targets:
            self.log_line.emit("⚠ 인수인계 복원 생략 — 잡기 직전 Seer 각도가 없습니다")
        elif any(self.be.meas_angle(n) is None for n in targets):
            self.log_line.emit("⚠ 인수인계 복원 생략 — 조향 실측이 신선하지 않습니다(움직이지 않음)")
        else:
            self.log_line.emit("인수인계 복원 — " +
                               ", ".join(f"N{n} → {v:+.2f}°" for n, v in targets.items()))
            try:
                self._steer_commanded = True   # 복원도 우리 조향 지령이다(대조 중단)
                for n, v in targets.items():
                    self.be.steer_axis(n, v)
                t0 = time.monotonic()
                while time.monotonic() - t0 < SEER_RESTORE_TIMEOUT_S:
                    cur = {n: self.be.meas_angle(n) for n in targets}
                    if all(c is not None and abs(c - targets[n]) <= 1.0 for n, c in cur.items()):
                        self.log_line.emit(f"인수인계 복원 완료 ({time.monotonic() - t0:.1f}s)")
                        break
                    time.sleep(0.05)
                else:
                    self.log_line.emit(
                        f"⚠ 인수인계 복원 미완료 ({SEER_RESTORE_TIMEOUT_S:.0f}s 초과) — 그대로 반환합니다")
            except Exception as exc:
                self.log_line.emit(f"⚠ 인수인계 복원 실패: {type(exc).__name__}: {exc}")
        return self.be.set_engaged(False)

    def _on_wheel_changed(self, node: int):
        self._redraw_wheel()
        sld = self.sld_front if node == 3 else self.sld_rear
        if not sld.isSliderDown():
            self._send_steer(node)

    def _send_steer(self, node: int):
        deg = (self.sld_front if node == 3 else self.sld_rear).value()
        try:
            self._steer_commanded = True      # 이 시점부터 Seer 판독은 굳는다(대조 중단)
            self.be.steer_axis(node, float(deg))
            self.log(f"조향 지령 N{node} → {deg:+d}°")
        except Exception as exc:
            self.log(f"조향 지령 실패 N{node}: {type(exc).__name__}: {exc}")

    def _jog(self, label: str):
        """조그 — crab 이므로 **바퀴를 먼저 돌리고 정착을 확인한 뒤** 주행한다."""
        if self._homing and label != "정지":
            self.log("호밍 진행 중 — 완료까지 기다리세요")
            return
        if label == "정지":
            self._jog_stop = True
            self._run_op("정지", self.be.stop)
            return
        if self._jog_th is not None and self._jog_th.is_alive():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        steer_deg, sign, _ = JOG[label]
        self._jog_stop = False
        self._jog_th = threading.Thread(target=self._jog_run, name="jog", daemon=True,
                                        args=(label, steer_deg, sign))
        self._jog_th.start()

    def _jog_run(self, label: str, steer_deg: float, sign: int):
        try:
            tol = float(self.spn_tol.value())
            mmps = float(self.spn_speed.value())
            self.be.drive(0.0)
            self._steer_commanded = True   # 조그도 우리 조향 지령이다(대조 중단)
            self.be.steer_all(steer_deg)
            self.log_line.emit(f"조그 '{label}' — 조향 {steer_deg:+.0f}° 지령, 정착 대기")
            t0 = time.monotonic()
            while time.monotonic() - t0 < 6.0:
                if self._jog_stop:
                    self.be.drive(0.0)
                    return
                if self.be.settled(steer_deg, tol, STEER_NODES):
                    break
                time.sleep(0.05)
            else:
                self.log_line.emit(
                    f"조향 정착 실패(실측 N3 {self.be.meas_angle(3)} / "
                    f"N4 {self.be.meas_angle(4)}) — 구동 취소")
                self.be.drive(0.0)
                return
            # 확인과 송신 사이의 창을 좁힌다 — 확인 직후 정지가 눌리면 정지(0)가 먼저 나가고
            # 구동이 뒤에 나갈 수 있다(원본 Low ①과 같은 성질). 백엔드가 직렬화를 소유하므로
            # 여기서는 **확인을 송신 직전으로 붙이고** 결과를 로그로 남긴다.
            if self._jog_stop:
                self.be.drive(0.0)
                self.log_line.emit("정지 요청이 먼저 들어와 구동을 내보내지 않았습니다")
                return
            self.be.drive(sign * mmps)
            self.log_line.emit(f"조향 정착 — 구동 {sign * mmps:+.0f} mm/s")
        except Exception as exc:
            self.log_line.emit(f"조그 중단: {type(exc).__name__}: {exc}")
            try:
                self.be.drive(0.0)
            except Exception:
                pass

    def _homing_clicked(self):
        """호밍 — 실제로 크게 움직이므로 한 번 확인을 받는다.

        **취소 버튼은 없다**(양쪽 백엔드 공통). 중간에 끊으면 축이 어중간한 위치에 남아
        어차피 다시 호밍해야 하므로 얻는 것이 없다(ADR 2026-08-04 §Decision ②).
        """
        if self._homing:
            self.log("호밍 이미 진행 중")
            return
        if self._jog_th is not None and self._jog_th.is_alive():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        if QMessageBox.question(
                self, "조향 원점 복귀",
                "조향 2축을 원점(리밋)으로 보낸 뒤 0° 로 복귀시킵니다.\n\n"
                "· 바퀴가 크게 돕니다 — 복귀 스윙이 100° 를 넘습니다.\n"
                "· 약 35 초 걸립니다(10회 실측 35.0 초, 편차 0.2 초).\n"
                "· 이 프로그램에는 취소 버튼이 없습니다 — 중단하려면 하드웨어 E-STOP 을 쓰십시오.\n\n"
                "이동구역이 비어 있습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            self.log("호밍 취소")
            return
        self._homing = True
        self.btn_home.setEnabled(False)
        self._run_op("호밍", self.be.home)

    # ── Seer (네트워크 — 백엔드 무관, 원본 그대로) ──────────────────
    def _seer_loop(self):
        import sys
        try:
            if self._seer_gui_path not in sys.path:
                sys.path.insert(0, self._seer_gui_path)
            from seer_core.client import RobokitClient
            client = RobokitClient(self._seer_ip)
        except Exception as exc:
            self.seer_log_line.emit(f"Seer 연결 불가: {type(exc).__name__}: {exc}")
            self.seer_status.emit(
                f"Seer {self._seer_ip} · 연결 불가 ({type(exc).__name__})", False)
            return
        while self._seer_run:
            try:
                d = client.call("status", 1040)
                ms = d.get("motor_info") or d.get("motors") or []
                if not self._seer_run:
                    return
                self.seer_data.emit({int(m["can_id"]): m for m in ms if m.get("can_id")})
                self.seer_status.emit(
                    f"Seer {self._seer_ip} · 연결됨 · 모터 {len(ms)}축 · "
                    f"갱신 {time.strftime('%H:%M:%S')}", True)
            except RuntimeError:
                return
            except Exception as exc:
                if not self._seer_run:
                    return
                try:
                    self.seer_status.emit(
                        f"Seer {self._seer_ip} · 폴링 실패 ({type(exc).__name__})", False)
                except RuntimeError:
                    return
            self._alarm_tick += 1
            if self._alarm_tick % 4 == 0:
                try:
                    a = client.call("status", 1050)
                    self.alarm_counts.emit(len(a.get("fatals") or []),
                                           len(a.get("errors") or []))
                    for lvl in ("fatals", "errors", "warnings", "notices"):
                        for item in (a.get(lvl) or []):
                            line = self._fmt_alarm(item)
                            key = f"{lvl}|{line}"
                            if key not in self._alarm_seen:
                                self._alarm_seen.add(key)
                                self.seer_log_line.emit(f"[{lvl}] {line}")
                except RuntimeError:
                    return
                except Exception:
                    pass
            time.sleep(0.5)

    @staticmethod
    def _fmt_alarm(item) -> str:
        if isinstance(item, dict):
            code = item.get("code", item.get("id", ""))
            desc = (item.get("desc") or item.get("description")
                    or item.get("msg") or item.get("message") or "")
            return f"{code} {desc}".strip() or str(item)
        return str(item)

    def _on_seer_data(self, data: dict):
        for node, m in data.items():
            pos = m.get("position")
            deg = None if pos is None else pos * 180.0 / math.pi
            self._fill_row(self.tbl_seer, node, (deg, m.get("speed"), m.get("current")))
            if node in STEER_NODES and deg is not None:
                # ⚠ **우리 규약(CAN)으로 정규화해 담는다.** Seer 각도와 CAN counts 는
                #   **음의 상관**이다 — 정본 `config/machine/foil_a082.yaml` 의 0° 역산식
                #   `0° = CAN_0x6064 + Seer_deg x 57344` 가 그 뜻이고,
                #   실측 2026-08-04 20:34 도 같다: CAN +90.133°/+89.865° <-> Seer -90.1°/-89.9°.
                #   예전에는 Seer 원값을 그대로 담아, 제어권을 잡고 놓을 때마다 `_meas_angle`
                #   의 부호가 뒤집혔다(바퀴 그림·실측 라벨이 함께 뒤집힘).
                #   ⚠ Seer **표**(`tbl_seer`)는 Seer 가 보고한 값을 그대로 보여야 하므로
                #     정규화하지 않는다 — 여기서만 바꾼다.
                self._seer_deg[node] = -deg

    def _on_seer_status(self, text: str, ok: bool):
        self.lab_status.setText(text)
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; "
            + ("color:#1e8449;" if ok else "color:#c0392b;"))
        if not ok:
            self._seer_deg.clear()      # 끊기면 마지막 값을 실측인 척 쓰지 않는다

    def _set_alarm_color(self, n_fatal: int, n_error: int):
        bad = (n_fatal + n_error) > 0
        self.btn_clear_fatal.setText(
            f"Fatal 오류 리셋   (fatal {n_fatal} / error {n_error})")
        on = "#c0392b" if bad else "#1e8449"
        edge = "#8f2b20" if bad else "#166437"
        self.btn_clear_fatal.setStyleSheet(
            f"QPushButton {{ background:{on}; color:white; font-weight:bold;"
            f" border:1px solid {edge}; border-radius:4px; }}"
            "QPushButton:disabled { background:#d5dbe1; color:#8894a2;"
            " border:1px solid #c3ccd4; }")

    def _on_clear_fatal(self):
        """Seer Fatal 클리어 — config 4300. ⚠ **로봇 상태를 바꾸는 쓰기 명령**이다."""
        import sys
        self.btn_clear_fatal.setEnabled(False)
        path, ip = self._seer_gui_path, self._seer_ip

        def _clearfatal_work():
            try:
                if path not in sys.path:
                    sys.path.insert(0, path)
                from seer_core.client import RobokitClient
                res = RobokitClient(ip).call("config", 4300)
                rc = res.get("ret_code") if isinstance(res, dict) else res
                self.seer_log_line.emit(f"Fatal 리셋 요청(4300) → ret_code={rc}")
                self._alarm_seen.clear()
            except Exception as exc:
                self.seer_log_line.emit(f"Fatal 리셋 실패: {type(exc).__name__}: {exc}")

        threading.Thread(target=_clearfatal_work, daemon=True, name="clearfatal").start()
        QTimer.singleShot(1500, lambda: self.btn_clear_fatal.setEnabled(True))

    # ── 종료 ──────────────────────────────────────────────────────────
    def safe_release(self, reason: str = "") -> None:
        """모든 종료 경로가 공유하는 멱등 해제 — 백엔드에 위임한다."""
        if self._released:
            return
        self._released = True
        self._seer_run = False
        self._jog_stop = True
        try:
            self.be.shutdown(reason)
        except Exception as exc:
            print(f"[gui] ⚠ 종료 중 예외: {type(exc).__name__}: {exc}", flush=True)

    def closeEvent(self, ev):
        self.safe_release("창 닫기")
        ev.accept()
