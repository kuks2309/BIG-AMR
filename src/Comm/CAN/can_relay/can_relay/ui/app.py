#!/usr/bin/env python3
"""시험 GUI 화면 — 위젯 트리는 한 벌이고 백엔드만 갈아 끼운다.

## 화면 구성

| 열 | 내용 |
|---|---|
| 1 | 연결(판다 목록·검색 · USB · 제어권) + 로그 + Seer 로그·Fatal 리셋 |
| 2 | 조그 3×3 + 호밍 · 모터 값 표 · Seer 값 표 · 설정(속도·정착 허용치) |
| 3 | 차량 바퀴 그림 · 앞뒤 조향 슬라이더 |
| 하단 | 백엔드 연결 상태 · Seer 접속 상태 |

E-stop 버튼도 호밍 취소 버튼도 두지 않는다. 백엔드가 못 하는 기능의 버튼은 지우지 않고
비활성 + 사유 툴팁으로 남긴다 — 그래야 화면이 항상 같고 무엇이 다른지가 드러난다.

Seer 조회(1040·1050·4300)는 네트워크 전용이라 백엔드와 무관하며 이 화면이 직접 한다.
"""
from __future__ import annotations

import math
import threading
import time

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QTabWidget,
                             QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
                             QPushButton, QSlider, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .backend_base import CAP_HOME, CAP_SCAN, CAP_USB

STEER_NODES = (3, 4)
DRIVE_NODES = (1, 2)
STEER_LIMIT_DEG = 90

SEER_RESTORE_TIMEOUT_S = 20.0   # 제어권 반환 전 조향 복원을 기다리는 한도(초)
SEER_MATCH_TOL_DEG = 3.0        # CAN 실측 ↔ Seer 판독 허용 차(°)
SEER_JOG_DURATION_MS = 600      # Seer 개루프 운동(2010) 시한 — 재송신이 끊기면 이 안에 선다
SEER_JOG_PERIOD_S = 0.2         # 그 시한보다 짧게 다시 보내 속도를 유지한다
SEER_CONTROL_NICK = "can_relay_gui"  # Seer 제어권(4005) 획득 시 자기 식별 이름

# 조그 방향표 — {이름: (조향각°, 구동 raw 부호, 방향 실측 여부)}.
# 부호 규약: 조향 0° 에서 raw 음수가 전진(+x), 조향 +90° 에서 raw 양수가 좌 크랩.
JOG = {
    "전진":     (0.0,  -1, True),
    "후진":     (0.0,  +1, True),
    "좌 크랩":  (90.0, +1, True),
    "우 크랩":  (90.0, -1, True),
    "좌전 45°": (-45.0, -1, True),
    "우전 45°": (45.0,  -1, True),
    "좌후 45°": (45.0,  +1, True),
    "우후 45°": (-45.0, +1, True),
}


def wheel_axis(deg: float):
    """조향각(°) → 바퀴 길이축의 **화면** 단위벡터.

    기체 규약은 `+θ = 좌`(실기 앵커: 좌 크랩 θ=+90 → 좌측 이동)이고, 화면은 y 가
    아래로 증가한다. `WheelView._px` 가 기체 +x(전방)를 화면 위로, +y(좌)를 화면
    왼쪽으로 놓으므로 기체 방향 `(cos θ, sin θ)` 는 화면 `(−sin θ, −cos θ)` 가 된다.
    부호가 뒤집히면 그림만 좌우 반전되고 값·모션은 멀쩡해 발견이 늦다 — pose
    실측으로만 잡힌다. 이 규약은 `test_wheel_view.py` 가 고정한다.
    """
    th = math.radians(deg)
    return -math.sin(th), -math.cos(th)


class WheelView(QWidget):
    """차량 바퀴 top-view 위젯.

    차체 좌표는 +x 전방(화면 위) · +y 좌(화면 왼쪽)이고 바퀴 지향은 `(cos θ, −sin θ)` 다.
    치수는 m 단위이며 휠반경을 포함해 **시각화 전용 근사**다.
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
        """앞·뒤 조향각(°)을 반영하고 다시 그린다."""
        self.front_deg, self.rear_deg = float(front_deg), float(rear_deg)
        self.update()

    def _px(self, x_m: float, y_m: float, s: float) -> QPointF:
        """차체 좌표(m)를 배율 `s`(px/m)로 화면 좌표로 옮긴다."""
        c = self.rect().center()
        return QPointF(c.x() - y_m * s, c.y() - x_m * s)

    def paintEvent(self, _ev):
        """차체·전방 표시·바퀴 2개를 창 크기에 맞춘 배율로 그린다."""
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
        """바퀴 하나를 사각형 + 지향 화살표 + 각도 라벨로 그린다."""
        ax, ay = wheel_axis(deg)
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
        """바퀴 지향 화살표를 그린다. `(ax, ay)` 는 화면 좌표계 단위벡터다.

        사각형만으로는 +90° 와 −90° 가 똑같이 보이므로 방향을 화살촉으로 드러낸다.
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
    """켜짐을 색으로 드러내는 체크형 토글 버튼을 만든다."""
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
    """3열 배치의 시험 화면 한 벌. 차이는 어느 백엔드가 지령을 내보내는가뿐이다."""

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
        """위젯을 구성하고 시그널을 잇는다. `seer_enabled` 면 Seer 폴링 스레드도 띄운다."""
        super().__init__()
        self.be = backend
        self._seer_ip = seer_ip
        self._seer_gui_path = seer_gui_path
        self._seer_enabled = bool(seer_enabled)
        self._seer_run = bool(seer_enabled)
        self._seer_deg = {}
        self._seer_at_take = {}   # 제어권 잡기 직전 Seer 조향각(반환 시 복원 기준)
        self._steer_commanded = False   # 이번 세션에서 조향을 보냈는가(대조 중단 조건)
        self._seer_checked = set()      # 이번 세션에서 기준 대조를 마친 축
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
        """백엔드가 못 하는 기능의 버튼을 지우지 않고 비활성 + 사유 툴팁으로 만든다.

        USB 단계가 없는 백엔드에서는 제어권 버튼을 처음부터 누를 수 있어야 한다.
        """
        for cap, widgets in ((CAP_SCAN, [self.btn_scan]),
                             (CAP_USB, [self.btn_usb]),
                             (CAP_HOME, [self.btn_home])):
            if not self.be.can(cap):
                why = self.be.why_not(cap)
                for w in widgets:
                    w.setEnabled(False)
                    w.setToolTip(why)
        if not self.be.can(CAP_USB):
            self.btn_take.setEnabled(True)
            self.lab_panda.setText("드라이버가 소유")

    # ── 화면 ──────────────────────────────────────────────────────────
    def _build_connect(self) -> QGroupBox:
        """판다 목록·검색 버튼·USB 토글·제어권 토글을 담은 상자."""
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
        """3×3 방향 패드와 호밍 버튼을 담은 상자. 방향 미실측 항목에는 `⚠` 를 붙인다."""
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
        # 제어권을 쥐기 전에는 누를 수 없다. 이후 상태는 `_sync_home_button` 이 쥔다.
        self.btn_home.setEnabled(False)
        v.addWidget(self.btn_home)
        return g

    def _build_wheel_adj(self) -> QGroupBox:
        """앞·뒤 조향 슬라이더(±`STEER_LIMIT_DEG`°)를 담은 상자.

        드래그 중에는 보내지 않고 놓을 때 보낸다. 키보드·클릭 이동은 즉시 보낸다.
        """
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
        """바퀴 속도(0~200 mm/s)와 정착 허용치(0.5~10°) 입력을 담은 상자."""
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
        """4행(노드) × 4열(모터·각도·회전·전류) 읽기 전용 표를 만든다. 두 표가 공유한다."""
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
        """노드 행에 (각도, 회전, 전류)를 써 넣는다. `None` 인 칸은 `—` 로 덮어쓴다."""
        r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if r is None:
            return
        for (c, fmt), val in zip(cls.CELL_FMT, values):
            table.item(r, c).setText("—" if val is None else fmt.format(val))

    def _build_motors(self) -> QGroupBox:
        """백엔드가 읽어 온 모터 값 표를 담은 상자."""
        g = QGroupBox("모터 값")
        v = QVBoxLayout(g)
        self.tbl_motor = self._motor_table("회전(rpm)")
        v.addWidget(self.tbl_motor)
        return g

    def _build_seer(self) -> QGroupBox:
        """Seer 1040 이 보고한 값을 나란히 보여 주는 비교 표 상자."""
        g = QGroupBox("Seer 값 (비교)")
        v = QVBoxLayout(g)
        self.tbl_seer = self._motor_table("회전")
        v.addWidget(self.tbl_seer)
        return g

    def _build_wheel(self) -> QGroupBox:
        """`WheelView` 를 담은 상자."""
        g = QGroupBox("차량 바퀴 상태")
        v = QVBoxLayout(g)
        self.wheel = WheelView()
        v.addWidget(self.wheel)
        return g

    def _build_log(self) -> QWidget:
        """GUI 로그 창 + Seer 알람 로그 창 + Fatal 리셋 버튼을 세로로 담은 위젯."""
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

    def _build_status(self):
        """하단 상태 바 — **백엔드 연결**과 **Seer 접속**을 나란히 보인다.

        둘을 나눠 두면 드라이버가 죽은 것인지 로봇이 이상한 것인지 화면에서 구분할 수 있다.
        """
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.lab_link = QLabel("연결 확인 중…")
        self.lab_link.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; color:#5d6d7e;")
        self.lab_status = QLabel(f"Seer {self._seer_ip} · 접속 시도 중…")
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; color:#5d6d7e;")
        self.lab_sup = QLabel("감시 —")
        self.lab_sup.setStyleSheet(self._SUP_CSS % "#5d6d7e")
        lay.addWidget(self.lab_link, 1)
        lay.addWidget(self.lab_status, 1)
        lay.addWidget(self.lab_sup, 1)
        return box

    _SUP_CSS = ("padding:4px 8px; border-top:1px solid #cfd8e0; "
                "color:%s; font-weight:600;")
    # 감시 판정 색 — 초록 = 정상 부류, 호박 = 유예, 주홍 = 차단, 빨강 = 죽음/정체,
    # 파랑 = 복귀 중. 판정값은 감시자(`health.py`)의 7종 그대로다.
    _SUP_COLORS = {"RUNNING": "#1e8449", "IDLE": "#5d6d7e", "WAIT": "#b7950b",
                   "RESTORE": "#2471a3", "HOLD": "#ca6f1e",
                   "DEAD": "#c0392b", "ZOMBIE": "#c0392b"}
    _SUP_STALE_S = 5.0
    #   감시자 상태의 신선 한계(초). 발행은 틱(기본 2 Hz)마다이므로 5 s 면 확실한 두절이다.

    _LINK_OK_CSS = ("padding:4px 8px; border-top:1px solid #cfd8e0; "
                    "color:#1e8449; font-weight:600;")
    _LINK_BAD_CSS = ("padding:4px 8px; border-top:1px solid #cfd8e0; "
                     "color:#c0392b; font-weight:600;")

    def _refresh_link(self):
        """백엔드 연결 표시를 갱신한다 — 초록이 연결, 빨강이 끊김이다."""
        try:
            connected, text = self.be.link_status()
        except Exception as exc:                       # 백엔드가 아직 안 붙었을 때
            connected, text = False, f"연결 확인 실패: {type(exc).__name__}"
        self.lab_link.setText(text)
        self.lab_link.setStyleSheet(self._LINK_OK_CSS if connected else self._LINK_BAD_CSS)

    # ── 주기 갱신 ─────────────────────────────────────────────────────
    def _refresh(self):
        """100 ms 주기 갱신 — 모터 표·Seer 대조·바퀴 그림·연결 표시·제어권 버튼 상태."""
        rows = self.be.motor_rows()
        for node in DRIVE_NODES + STEER_NODES:
            self._fill_row(self.tbl_motor, node, rows.get(node, (None, None, None)))
        for node in STEER_NODES:
            deg = self.be.meas_angle(node)
            if deg is not None:
                self._check_seer_agreement(node, deg)
        self._redraw_wheel()

        self._refresh_link()
        self._refresh_supervisor()
        text, ok, engaged = self.be.status()
        if text != getattr(self, "_last_status", None):
            self._last_status = text
            self.log_line.emit(f"[{self.be.name}] {text}")
        if engaged != self.btn_take.isChecked():
            self.btn_take.blockSignals(True)
            self.btn_take.setChecked(engaged)
            self.btn_take.setText("제어권 해제" if engaged else "제어권 획득")
            self.btn_take.blockSignals(False)
        self._sync_home_button(engaged)

    def _refresh_supervisor(self):
        """감시자(relay_supervisor) 판정 표시 + 판정 전이를 로그로.

        감시자는 드라이버가 죽으면 자동 복귀(engage)까지 하므로, 사람이 누르지 않은
        제어권 변화가 화면에서 「감시 전이」로 설명되게 한다.
        """
        got = None
        try:
            got = self.be.supervisor_status()
        except Exception:
            pass
        if got is None:                       # 이 백엔드는 감시자를 볼 수 없다(직결 등)
            self.lab_sup.setText("감시 — (이 백엔드에서는 비표시)")
            self.lab_sup.setStyleSheet(self._SUP_CSS % "#5d6d7e")
            return
        verdict, msg, age = got
        if verdict is None:
            self.lab_sup.setText("감시자 미수신")
            self.lab_sup.setStyleSheet(self._SUP_CSS % "#b7950b")
            return
        if age is not None and age > self._SUP_STALE_S:
            self.lab_sup.setText(f"감시자 두절 {age:.0f}s (마지막: {verdict})")
            self.lab_sup.setStyleSheet(self._SUP_CSS % "#c0392b")
            return
        self.lab_sup.setText(f"감시 {msg}" if msg else f"감시 {verdict}")
        self.lab_sup.setStyleSheet(
            self._SUP_CSS % self._SUP_COLORS.get(verdict, "#b7950b"))
        if verdict != getattr(self, "_last_sup_verdict", None):
            self._last_sup_verdict = verdict
            self.log_line.emit(f"[감시] {msg or verdict}")

    def _sync_home_button(self, engaged: bool):
        """호밍 버튼은 **제어권을 쥐고 있을 때만** 누를 수 있다.

        호밍은 조향 드라이브의 내부 루틴(`0x60FB:04`)을 부르는 것이라 릴레이로 버스를
        쥐고 있어야 성립한다. 조그와 달리 **Seer 쪽 대체 경로가 없다** — Seer 로봇 API 의
        제어 명령(2000·2001·2002·2003·2010·2022~2025)에 조향 호밍이 없다.

        버튼이 제어권을 대신 잡아 주지는 않는다. 획득은 Seer 를 밀어내는 동작이라
        운용자가 그 버튼을 눌러 명시적으로 해야 한다.

        capability 로 이미 막힌 백엔드는 건드리지 않는다 — 그 사유 툴팁을 덮으면
        「왜 못 누르는가」가 바뀌어 버린다.
        """
        if not self.be.can(CAP_HOME):
            return
        allow = bool(engaged) and not self._homing
        if self.btn_home.isEnabled() != allow:
            self.btn_home.setEnabled(allow)
        self.btn_home.setToolTip(
            "" if allow else
            ("호밍 진행 중" if self._homing else
             "제어권을 먼저 획득하세요 — 호밍은 릴레이로 버스를 쥐고 있어야 하고 "
             "Seer 쪽 대체 경로가 없습니다"))

    def _meas_angle(self, node):
        """그 축의 실측 조향각(°). 백엔드 값이 없으면 Seer 판독으로 대신한다."""
        d = self.be.meas_angle(node)
        return d if d is not None else self._seer_deg.get(node)


    def _check_seer_agreement(self, node: int, deg: float):
        """CAN 실측과 Seer 판독이 같은 곳을 가리키는가 — **제어권 세션당 축별 1회**만 본다.

        **제어권을 쥐면 Seer 는 모터를 못 읽는다** — 릴레이가 intercept 로 넘어가 Seer 쪽
        판독이 굳는다. 그래서 대조가 유효한 값은 **잡기 직전에 읽어 둔 Seer 각도**
        (`_seer_at_take`) 하나뿐이고, 비교 상대는 **획득 후 처음 들어온 신선한 CAN 실측**이다.
        그 시점에는 아직 아무도 축을 움직이지 않았으므로 둘은 같은 자세를 가리켜야 한다.

        살아 있는 Seer 값(`_seer_deg`)과 매 표본 대조하면 **굳은 값과 비교하는 것**이라
        거짓 경보만 난다 — 실측 갱신 자체가 제어권 보유 중에만 도므로 그 대조에는 유효한
        창이 없다.

        어긋나면 알리기만 한다 — 판단은 운용자 몫이고 조용히 진행하는 것만 피한다.
        """
        if node in self._seer_checked:          # 이번 세션에서 이미 본 축
            return
        ref = (self._seer_at_take or {}).get(node)
        if ref is None:                          # 잡기 직전 기준이 없으면 판정하지 않는다
            return
        self._seer_checked.add(node)
        diff = deg - ref
        if abs(diff) <= SEER_MATCH_TOL_DEG:
            return
        self.log_line.emit(
            f"⚠ N{node} 조향 기준 불일치 — 잡기 직전 Seer {ref:+.2f}° 인데 획득 후 첫 "
            f"CAN 실측 {deg:+.2f}° (차 {diff:+.2f}°). 0° 기준이 서로 다릅니다 — "
            f"조작 전 확인하세요")

    def _redraw_wheel(self):
        """바퀴 그림과 슬라이더 라벨을 실측으로 갱신한다.

        **두 축 모두** 실측이 있어야 실측으로 그린다. 한 축이라도 없으면 양쪽 다 슬라이더
        값을 미리보기로 쓴다 — 한쪽만 실측으로 그리면 앞뒤가 다른 근거로 그려진다.
        슬라이더에는 되쓰지 않는다: 슬라이더는 목표를 넣는 명령 입력이라 되먹이면 방금
        넣은 값이 지워진다.
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
        """GUI 로그 창과 stdout 에 시각을 붙여 한 줄 남긴다(GUI 스레드 전용)."""
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        self.txt_log.appendPlainText(line)
        print(f"[gui] {line}", flush=True)

    def seer_log(self, msg: str):
        """Seer 로그 창에 시각을 붙여 한 줄 남긴다."""
        self.txt_seer_log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {msg}")

    def _run_op(self, name: str, fn, *args):
        """블로킹 백엔드 호출을 작업 스레드로 돌리고 결과를 `op_done` 으로 알린다."""
        def _op_work():
            """작업 스레드 본체 — 예외도 결과 문자열로 바꿔 넘긴다."""
            try:
                ok, why = fn(*args)
            except Exception as exc:
                ok, why = False, f"{type(exc).__name__}: {exc}"
            self.op_done.emit(name, bool(ok), str(why))
        threading.Thread(target=_op_work, daemon=True, name=name).start()

    def _on_op_done(self, name: str, ok: bool, why: str):
        """작업 결과를 로그에 남기고 그 작업에 딸린 버튼·라벨 상태를 되돌린다."""
        self.log(f"{name} — {why}" if ok else f"{name} 실패 — {why}")
        if name == "검색":
            # 알려진 접두사만 벗긴다. 콜론 쪼개기는 메시지에 콜론이 여럿이면 엉뚱한 조각을 올린다.
            PREFIX = "판다 검출: "
            label = why[len(PREFIX):] if why.startswith(PREFIX) else why
            self.lab_panda.setText((label if ok else "검색 실패")[:48])
            if self.be.can(CAP_USB):
                self.btn_usb.setEnabled(ok)
        elif name == "USB":
            self.btn_take.setEnabled(ok and self.btn_usb.isChecked())
        elif name == "호밍":
            # 버튼 상태는 `_sync_home_button` 하나가 쥔다 — 여기서도 켜면 제어권을 놓은
            # 뒤 호밍이 끝났을 때 눌 수 없어야 할 버튼이 켜진다.
            self._homing = False

    def _on_usb(self, on: bool):
        """USB 토글 — 버튼 문구를 바꾸고 개폐를 작업 스레드에 맡긴다."""
        self.btn_usb.setText("판다 USB 해제" if on else "판다 USB 연결")
        self._run_op("USB", self.be.set_usb, on)

    def _on_take(self, on: bool):
        """제어권 획득/반환. **인수인계는 Seer 기준으로 한다.**

        획득 전에 Seer 가 보던 조향각을 기억해 두고, 반환할 때 그 각도로 되돌려 놓고 넘긴다.
        되돌리지 않고 넘기면 Seer 가 자기 판단으로 조향을 크게 움직인다.
        """
        self.btn_take.setText("제어권 해제" if on else "제어권 획득")
        if on:
            self._steer_commanded = False   # 새 세션 — 대조를 다시 연다
            self._seer_checked = set()      # 기준 대조도 축별 1회씩 다시
            self._seer_at_take = {n: self._seer_deg.get(n) for n in STEER_NODES}
            have = {n: v for n, v in self._seer_at_take.items() if v is not None}
            self.log("인수인계 기준(Seer) — " +
                     (", ".join(f"N{n} {v:+.2f}°" for n, v in have.items()) if have
                      else "⚠ Seer 각도 없음 — 반환 시 복원할 기준이 없습니다"))
            self._run_op("제어권", self.be.set_engaged, True)
        else:
            self._run_op("제어권", self._release_with_handover)

    def _release_with_handover(self):
        """조향을 인수인계 기준으로 되돌린 뒤 제어권을 반환한다. 반환 `(성공, 메시지)`.

        **작업 스레드에서 실행되므로 위젯을 만지지 않는다** — 로그는 시그널로 보낸다.
        기준이 없거나 실측이 신선하지 않으면 복원을 생략하고 그 사실을 남긴다.
        """
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
        """슬라이더 값이 바뀌면 그림을 다시 그리고, 드래그 중이 아니면 즉시 보낸다."""
        self._redraw_wheel()
        sld = self.sld_front if node == 3 else self.sld_rear
        if not sld.isSliderDown():
            self._send_steer(node)

    def _send_steer(self, node: int):
        """그 축의 슬라이더 값을 조향 지령으로 보내고 로그에 남긴다."""
        deg = (self.sld_front if node == 3 else self.sld_rear).value()
        try:
            self._steer_commanded = True      # 이 시점부터 Seer 판독은 굳는다(대조 중단)
            self.be.steer_axis(node, float(deg))
            self.log(f"조향 지령 N{node} → {deg:+d}°")
        except Exception as exc:
            self.log(f"조향 지령 실패 N{node}: {type(exc).__name__}: {exc}")

    def _jog(self, label: str):
        """조그 진입 게이트. **제어권 보유 시 백엔드 경로, 미보유 시 Seer API 경로**로 갈린다.

        제어권이 없으면 버스는 Seer 가 쓴다. 우리가 프레임을 낼 수 없으므로 같은 조그를
        **Seer 개루프 운동(2010)** 으로 대신 보낸다. `정지` 는 즉시 처리하고 나머지는
        조그 스레드를 띄운다. 호밍 중이거나 이미 조그가 돌고 있으면 새 조그를 받지 않는다.
        """
        if self._homing and label != "정지":
            self.log("호밍 진행 중 — 완료까지 기다리세요")
            return
        if not self._engaged():
            self._jog_seer(label)
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

    def _engaged(self) -> bool:
        """제어권을 쥐고 있는가 — 백엔드 상태의 세 번째 값이 그 답이다."""
        try:
            return bool(self.be.status()[2])
        except Exception:
            return False

    @staticmethod
    def _seer_velocity(steer_deg: float, sign: int, mmps: float) -> tuple:
        """조그 표 한 항목을 Seer 차체 속도 `(vx, vy)`(m/s)로 옮긴다.

        `JOG` 는 CAN 경로용이라 (조향각, 구동 raw 부호)로 적혀 있다. 같은 운동을 차체
        속도로 쓰면 `v = −sign × (cos θ, −sin θ)` 다 — 표의 부호 규약 두 개가 그대로
        나온다: 조향 0°·raw 음수 → +x(전진), 조향 +90°·raw 양수 → +y(좌).
        `mmps` 는 GUI 속도 입력(mm/s)이고 Seer 는 m/s 를 받는다.
        """
        th = math.radians(steer_deg)
        v = float(mmps) / 1000.0
        return (-sign * math.cos(th) * v, -sign * -math.sin(th) * v)

    def _seer_ctrl_client(self):
        """Seer 제어용 클라이언트. 상태 폴링과 별개 연결이다(19205 는 배타 포트)."""
        import sys
        if self._seer_gui_path not in sys.path:
            sys.path.insert(0, self._seer_gui_path)
        from seer_core.client import RobokitClient
        return RobokitClient(self._seer_ip)

    def _jog_seer(self, label: str):
        """제어권이 없을 때의 조그 — Seer 개루프 운동(2010)으로 보낸다.

        `정지` 는 워커를 끊는다. 워커가 없을 때만 단발로 2000 을 시도한다 — 제어권이
        없으면 `ret_code=40020` 이 로그에 남는다.
        """
        if label == "정지":
            self._jog_stop = True
            if self._jog_th is None or not self._jog_th.is_alive():
                self._run_seer_ctrl("stop_motion")
            return
        if self._jog_th is not None and self._jog_th.is_alive():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        steer_deg, sign, _ = JOG[label]
        vx, vy = self._seer_velocity(steer_deg, sign, self.spn_speed.value())
        self._jog_stop = False
        self._jog_th = threading.Thread(target=self._jog_seer_run, name="jog-seer",
                                        daemon=True, args=(label, vx, vy))
        self._jog_th.start()

    def _run_seer_ctrl(self, method: str, *args):
        """Seer 제어 포트(19205) 호출 1회를 작업 스레드에서 한다. 결과는 로그로 남긴다."""
        def _work():
            try:
                res = getattr(self._seer_ctrl_client(), method)(*args)
                self.log_line.emit(f"Seer {method} → {res}")
            except Exception as exc:
                self.log_line.emit(f"Seer {method} 실패: {type(exc).__name__}: {exc}")
        threading.Thread(target=_work, daemon=True, name="seer-ctrl").start()

    def _jog_seer_run(self, label: str, vx: float, vy: float):
        """Seer 조그 워커 — 제어권 획득 → 2010 재송신 → 정지·반납.

        Seer 는 standalone 조작 전에 **제어권(4005)** 을 요구한다. 없으면 2010·2000 이
        `ret_code=40020`(control is preempted)으로 거부된다. 잡기 전에 현재 소유자를
        1060 으로 읽어 로그에 남긴다 — **이 획득은 그 소유자의 제어권을 뺏는다.**

        2010 의 `duration` 이 재송신 주기보다 길어야 사이가 끊기지 않고, 재송신이 멈추면
        그 시한 안에 로봇이 선다. 끝날 때는 2000 을 보내고 4006 으로 반납한다.
        """
        try:
            client = self._seer_ctrl_client()
        except Exception as exc:
            self.log_line.emit(f"Seer 연결 불가: {type(exc).__name__}: {exc}")
            return
        seized = False
        try:
            try:
                self.log_line.emit(f"Seer 제어권 현재 소유자 — {client.control_owner()}")
            except Exception as exc:
                self.log_line.emit(f"Seer 소유자 조회 실패: {type(exc).__name__}: {exc}")
            client.seize_control(SEER_CONTROL_NICK)
            seized = True
            self.log_line.emit(f"Seer 제어권 획득 — nick '{SEER_CONTROL_NICK}'")
            self.log_line.emit(f"Seer 조그 '{label}' — vx {vx:+.3f} / vy {vy:+.3f} m/s")
            while not self._jog_stop:
                client.open_loop(vx=vx, vy=vy, w=0.0,
                                 duration=int(SEER_JOG_DURATION_MS))
                time.sleep(SEER_JOG_PERIOD_S)
        except Exception as exc:
            self.log_line.emit(f"Seer 조그 중단: {type(exc).__name__}: {exc}")
        finally:
            if seized:
                try:
                    client.stop_motion()
                    self.log_line.emit("Seer 조그 종료 — 정지(2000) 송신")
                except Exception as exc:
                    self.log_line.emit(f"⚠ Seer 정지 송신 실패: {type(exc).__name__}: {exc}")
                try:
                    client.release_control()
                    self.log_line.emit("Seer 제어권 반납(4006)")
                except Exception as exc:
                    self.log_line.emit(f"⚠ Seer 제어권 반납 실패: {type(exc).__name__}: {exc}")

    def _jog_run(self, label: str, steer_deg: float, sign: int):
        """조그 스레드 본체 — 구동 0 → 조향 → 정착 확인 → 구동 순서로 진행한다.

        crab 이므로 두 축이 목표에 들어온 뒤에야 주행한다. 정착 대기는 6초까지이며 그동안
        1초마다 축별 실측을 로그에 남긴다 — 중도 정지로 끝나도 어느 축이 문제였는지 남는다.
        구동 직전에 정지 요청을 한 번 더 확인해 정지와 구동이 뒤바뀌는 창을 좁힌다.
        """
        try:
            tol = float(self.spn_tol.value())
            mmps = float(self.spn_speed.value())
            self.be.drive(0.0)
            self._steer_commanded = True   # 조그도 우리 조향 지령이다(대조 중단)
            self.be.steer_all(steer_deg)
            self.log_line.emit(f"조그 '{label}' — 조향 {steer_deg:+.0f}° 지령, 정착 대기")
            t0 = time.monotonic()
            next_note = t0 + 1.0
            while time.monotonic() - t0 < 6.0:
                if self._jog_stop:
                    self.be.drive(0.0)
                    self.log_line.emit(
                        f"조그 중단 — 정착 전 정지 (실측 "
                        + " · ".join(f"N{n} {self.be.meas_angle(n)}" for n in STEER_NODES)
                        + f" / 목표 {steer_deg:+.0f}°)")
                    return
                if self.be.settled(steer_deg, tol, STEER_NODES):
                    break
                now = time.monotonic()
                if now >= next_note:
                    next_note = now + 1.0
                    self.log_line.emit(
                        f"정착 대기 {now - t0:.0f}초 — "
                        + " · ".join(
                            f"N{n} {'—' if (a := self.be.meas_angle(n)) is None else f'{a:+.2f}°'}"
                            for n in STEER_NODES)
                        + f" (목표 {steer_deg:+.0f}°, 허용 {tol:.1f}°)")
                time.sleep(0.05)
            else:
                self.log_line.emit(
                    f"조향 정착 실패(실측 N3 {self.be.meas_angle(3)} / "
                    f"N4 {self.be.meas_angle(4)}) — 구동 취소")
                self.be.drive(0.0)
                return
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
        """호밍 버튼 — 확인 대화상자를 거쳐 호밍을 작업 스레드에 맡긴다.

        축이 크게 움직이므로 이동구역이 비었는지 한 번 확인을 받는다. 호밍 중이거나
        조그가 돌고 있으면 받지 않는다. 취소 버튼은 두지 않는다.
        """
        if self._homing:
            self.log("호밍 이미 진행 중")
            return
        if self._jog_th is not None and self._jog_th.is_alive():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        if not self._engaged():
            # 버튼이 이미 비활성이라 정상 경로로는 여기 오지 않는다. 그래도 막는다 —
            # 그냥 두면 백엔드의 내부 사정(「기동돼 있지 않다」)이 운용자에게 나간다.
            self.log("호밍 불가 — 제어권을 먼저 획득하세요")
            return
        if QMessageBox.question(
                self, "조향 원점 복귀",
                "조향 2축을 원점(리밋)으로 보낸 뒤 펌웨어 정착 위치로 되돌립니다.\n"
                "※ 그 위치는 조향 0° 가 아닙니다 — 0° 에서 +0.18° / +0.33° 떨어진 지점입니다.\n\n"
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

    # ── Seer (네트워크 — 백엔드 무관) ────────────────────────────────
    def _seer_loop(self):
        """Seer 폴링 스레드 — 상태 1040 을 0.5초마다, 알람 1050 을 4회마다 읽는다.

        `seer_gui_path` 에서 `RobokitClient` 를 import 한다. 연결하지 못하면 그 사실만
        남기고 스레드를 끝낸다 — 구동은 Seer 없이도 정상이다.
        새로 나타난 알람만 로그에 올린다.
        """
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
        """알람 항목 하나를 `코드 설명` 한 줄로 정규화한다(구조가 달라도 문자열은 나온다)."""
        if isinstance(item, dict):
            code = item.get("code", item.get("id", ""))
            desc = (item.get("desc") or item.get("description")
                    or item.get("msg") or item.get("message") or "")
            return f"{code} {desc}".strip() or str(item)
        return str(item)

    def _on_seer_data(self, data: dict):
        """Seer 비교 표를 채우고 조향축 각도를 내부 비교값으로 갈무리한다.

        표에는 Seer 가 보고한 값을 **그대로** 보인다. 반면 `_seer_deg` 에는 부호를 뒤집어
        담는다 — Seer 각도와 CAN counts 는 **음의 상관**이라(0° 역산식이 그 뜻이다) 뒤집지
        않으면 제어권을 잡고 놓을 때마다 실측 부호가 뒤바뀐다.
        `position` 은 rad 이므로 °로 환산한다.
        """
        for node, m in data.items():
            pos = m.get("position")
            deg = None if pos is None else pos * 180.0 / math.pi
            self._fill_row(self.tbl_seer, node, (deg, m.get("speed"), m.get("current")))
            if node in STEER_NODES and deg is not None:
                self._seer_deg[node] = -deg

    def _on_seer_status(self, text: str, ok: bool):
        """Seer 접속 상태 바를 갱신한다. 끊기면 마지막 각도를 실측인 척 쓰지 않도록 비운다."""
        self.lab_status.setText(text)
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; "
            + ("color:#1e8449;" if ok else "color:#c0392b;"))
        if not ok:
            self._seer_deg.clear()

    def _set_alarm_color(self, n_fatal: int, n_error: int):
        """Fatal 리셋 버튼에 건수를 적고 색으로 심각도를 드러낸다(붉음=있음)."""
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
        """Seer config 4300 으로 Fatal 오류코드를 지운다 — **로봇 상태를 바꾸는 쓰기 명령**이다.

        호출은 작업 스레드에서 하고 버튼은 잠깐 잠근다.
        """
        import sys
        self.btn_clear_fatal.setEnabled(False)
        path, ip = self._seer_gui_path, self._seer_ip

        def _clearfatal_work():
            """작업 스레드 본체 — 4300 을 부르고 결과를 Seer 로그에 남긴다."""
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
    def set_seer_polling(self, on: bool) -> None:
        """Seer 폴링을 켜고 끈다 — 탭 구성에서 보이는 창만 돌게 하려고 둔다.

        `seer_enabled=False` 로 만든 창은 이 호출로도 켜지지 않는다.
        """
        on = bool(on) and self._seer_enabled
        if on == self._seer_run:
            return
        self._seer_run = on
        if on:
            threading.Thread(target=self._seer_loop, daemon=True, name="seer").start()

    def holds_hardware(self) -> bool:
        """이 창이 판다를 붙들고 있는가(USB 개방 또는 제어권 보유).

        판다는 한 곳만 열 수 있어, 탭 구성에서 다른 탭을 잠글지 판정하는 데 쓴다.
        """
        return bool(self.btn_usb.isChecked() or self.btn_take.isChecked())

    def safe_release(self, reason: str = "") -> None:
        """모든 종료 경로가 공유하는 멱등 해제 — 폴링을 끄고 백엔드에 해제를 위임한다."""
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
        """창을 닫을 때 해제하고 닫힘을 수리한다."""
        self.safe_release("창 닫기")
        ev.accept()


class RelayTabs(QWidget):
    """한 프로그램에 탭 2개 — ROS2(운용) · 판다 직결(시험).

    **판다는 한 곳만 열 수 있다.** ros2 탭은 드라이버가, direct 탭은 이 창이 직접 연다.
    두 곳이 동시에 잡으면 USB 가 연속 실패하므로, 한 탭이 하드웨어를 붙들고 있으면
    다른 탭을 잠근다. Seer 폴링도 보이는 탭에서만 돈다.
    """

    LOCK_NOTE = "다른 탭이 판다를 붙들고 있습니다 — 그 탭에서 제어권·USB 를 먼저 해제하세요"

    def __init__(self, panels: dict):
        """`{탭이름: MainWindow}` 를 탭으로 붙이고 배타 잠금 감시 타이머를 건다."""
        super().__init__()
        self.setWindowTitle("Tongyi 4축 AMR 구동 테스트 GUI [탭: ros2 · direct]")
        self.resize(1240, 840)
        self._panels = panels
        self.tabs = QTabWidget(self)
        for name, panel in panels.items():
            self.tabs.addTab(panel, name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._guard = QTimer(self)
        self._guard.timeout.connect(self._apply_exclusive_lock)
        self._guard.start(200)
        self._on_tab_changed(self.tabs.currentIndex())

    # ── 탭 전환 ───────────────────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        """보이는 탭만 Seer 를 보게 하고 잠금 상태를 다시 계산한다."""
        for i, panel in enumerate(self._panels.values()):
            panel.set_seer_polling(i == idx)
        self._apply_exclusive_lock()

    # ── 배타 잠금 ─────────────────────────────────────────────────────
    def _apply_exclusive_lock(self):
        """하드웨어를 붙든 탭이 있으면 나머지 탭을 잠그고 그 사유를 한 번 로그에 남긴다."""
        holder = None
        for i, panel in enumerate(self._panels.values()):
            if panel.holds_hardware():
                holder = i
                break
        for i, panel in enumerate(self._panels.values()):
            locked = holder is not None and i != holder
            if self.tabs.isTabEnabled(i) == (not locked):
                continue
            self.tabs.setTabEnabled(i, not locked)
            if locked:
                panel.log(f"⚠ 탭 잠금 — {self.LOCK_NOTE}")

    # ── 종료 ─────────────────────────────────────────────────────────
    def safe_release(self, reason: str = "") -> None:
        """양쪽 패널을 모두 해제한다 — 종료 경로는 하나로 모은다."""
        for panel in self._panels.values():
            panel.safe_release(reason)

    def closeEvent(self, ev):
        """창을 닫을 때 두 패널을 해제하고 닫힘을 수리한다."""
        self.safe_release("창 닫기")
        ev.accept()
