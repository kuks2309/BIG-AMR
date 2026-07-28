#!/usr/bin/env python3
"""Tongyi 4축 AMR 구동 테스트 GUI — 실기 전용.

지시에 따라 단계적으로 만든다.
현재: 3열 그룹박스. 왼쪽 = 연결(판다 목록·USB·제어권) + 로그.
"""
from __future__ import annotations

import math
import os
import sys
import threading
import time

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
                             QMessageBox, QPushButton, QDoubleSpinBox,
                             QSlider, QSpinBox,
                             QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

# 판다 배선·제어권 (docking_field_kit 실측 관례)
SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE, CAN_KBPS, HEARTBEAT_S = 30, 250, 0.4
# 조향 스케일·홈 (config/tongyi_amr.yaml — debt-007 미판정 주의)
COUNTS_PER_DEG = 57344
STEER_HOME = {3: 7871815, 4: 7840086}
# Seer (무선망, 읽기 전용 status 폴링)
SEER_IP = "192.168.44.82"
SEER_GUI = "/home/nvidia/T-Robot_seer_gui"
# 구동 스케일 (docking_field_kit 실측: ±2445 = 0.1 m/s, VEL_MAX 4889 ≈ 0.2 m/s)
VEL_PER_MMPS, VEL_MAX_UNITS = 24.447, 4889
# 조향 가동범위 — 실측 검증 범위(기구 한계는 ±140°). 밖은 지령하지 않는다.
STEER_LIMIT_DEG = 90.0

# 조그 방향표 — (조향각°, 구동 raw 부호, 직접실측 여부)
#   직접 실측 2건만이 1차 근거다:
#     ① 조향 홈(0°) + raw 음수 → 전진(+x)
#     ② 조향 +90° + raw 양수 → 왼쪽(+y)  (IMU ay 실증)
#   나머지는 ①② 를 만족하는 모델 -sign(raw)x(cos0, -sin0) 에서 **도출**한 값이다.
JOG = {
    "전진":     (0.0,  -1, True),    # ①
    "후진":     (0.0,  +1, True),    # ① 의 raw 부호 반전
    "좌 크랩":  (90.0, +1, True),    # ②
    "우 크랩":  (90.0, -1, True),    # ② 의 raw 부호 반전
    "좌전 45°": (-45.0, -1, False),  # 도출
    "우전 45°": (45.0,  -1, False),  # 도출
    "좌후 45°": (45.0,  +1, False),  # 도출
    "우후 45°": (-45.0, +1, False),  # 도출
}

_KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docking_field_kit")


def _panda_class():
    """comma.ai panda 라이브러리 로드 (필드킷 동봉본)."""
    if _KIT not in sys.path:
        sys.path.insert(0, _KIT)
    from panda import Panda
    return Panda


class WheelView(QWidget):
    """차량 바퀴 상태 top-view. 조향각을 그대로 그림에 반영한다.

    기하(실측 정본, References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md §1):
      Front(node3) x=+0.604 m · Rear(node4) x=−0.596 m · 휠베이스 1.200 m · 휠반경 0.125 m
    좌표: +x 전방(화면 위) · +y 좌(화면 왼쪽)
    각도 규약: 조향 +각 = counts 증가 방향. 바퀴 지향 = (cos θ, −sin θ).
    """

    FRONT_X, REAR_X = 0.604, -0.596
    WHEEL_R = 0.125
    BODY_L, BODY_W = 1.60, 0.90        # 외형 근사치(시각화용, 실측 아님)

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

        # 차체
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

    def _draw_wheel(self, p: QPainter, ctr: QPointF, deg: float, s: float, name: str):
        th = math.radians(deg)
        ux, uy = math.cos(th), -math.sin(th)          # 차체좌표 지향
        ax, ay = -uy, -ux                              # 화면 성분(+x 위, +y 왼쪽)
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
        p.drawEllipse(ctr, 3.0, 3.0)
        p.drawText(QRectF(ctr.x() + 22, ctr.y() - 10, 120, 20),
                   Qt.AlignLeft | Qt.AlignVCenter, f"{name}  {deg:+.1f}°")


def _toggle(text: str, on_bg: str, on_border: str) -> QPushButton:
    """켜짐 상태를 색으로 드러내는 토글 버튼."""
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
    # 폴링 스레드 → GUI 스레드. Qt 위젯은 GUI 스레드에서만 만질 수 있다.
    motor_data = pyqtSignal(dict)
    seer_data = pyqtSignal(dict)
    seer_status = pyqtSignal(str, bool)
    seer_log_line = pyqtSignal(str)
    clear_done = pyqtSignal()
    alarm_counts = pyqtSignal(int, int)
    log_line = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.panda = None
        self._th = None
        self._run = False
        self._seer_run = True
        self._alarm_tick = 0
        self._alarm_seen = set()
        self._can_lock = threading.Lock()   # 폴링·조그가 버스를 공유한다
        self._jog_th = None
        self._jog_stop = False
        self._meas_deg = {3: None, 4: None}
        self.setWindowTitle("Tongyi 4축 AMR 구동 테스트 GUI")
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
        mid.addWidget(self._build_motors(), 0)   # 중간 — 판다에서 읽은 모터 값
        mid.addWidget(self._build_seer(), 0)     # 아래-위 — Seer 에서 읽은 값(비교용)
        mid.addWidget(self._build_settings(), 0) # 맨 아래 — 속도·각도·허용치 설정
        mid.addStretch(1)

        right = QVBoxLayout(self.box3)
        right.addWidget(self._build_wheel(), 1)      # 위 — 차량 그림
        right.addWidget(self._build_wheel_adj(), 0)  # 아래 — 앞뒤 바퀴 조정
        for box in (self.box1, self.box2, self.box3):
            row.addWidget(box, 1)
        root.addWidget(self._build_status(), 0)

        self.motor_data.connect(self._on_motor_data)
        self.seer_data.connect(self._on_seer_data)
        self.seer_status.connect(self._on_seer_status)
        self.seer_log_line.connect(self.seer_log)
        self.clear_done.connect(lambda: self.btn_clear_fatal.setEnabled(True))
        self.alarm_counts.connect(self._set_alarm_color)
        self.log_line.connect(self.log)
        threading.Thread(target=self._seer_loop, daemon=True, name='seer').start()
        self.log("GUI 기동 — 실기 전용")
        self.scan()

    def closeEvent(self, ev):
        """종료 시 제어권을 반드시 반환한다."""
        self._seer_run = False
        if self.btn_take.isChecked():
            self.btn_take.setChecked(False)
        if self.panda is not None:
            try:
                self.panda.close()
            except Exception:
                pass
        ev.accept()

    # ── 화면 ────────────────────────────────────────────────────────────
    def _build_connect(self) -> QGroupBox:
        g = QGroupBox("연결")
        v = QVBoxLayout(g)

        v.addWidget(QLabel("연결 가능한 판다"))
        pick = QHBoxLayout()
        self.cmb_panda = QComboBox()
        self.btn_scan = QPushButton("검색")
        self.btn_scan.setMinimumHeight(28)
        self.btn_scan.clicked.connect(self.scan)
        pick.addWidget(self.cmb_panda, 1)
        pick.addWidget(self.btn_scan, 0)
        v.addLayout(pick)

        # 둘 다 토글. 색 의미를 나눈다 —
        #   녹색 = 무해한 연결(USB 는 상태만 읽는다)
        #   앰버 = 주의(제어권 보유 = Seer 에게서 릴레이를 가져온 상태)
        self.btn_usb = _toggle("판다 USB 연결", "#1e8449", "#166437")
        self.btn_usb.toggled.connect(self._on_usb)
        v.addWidget(self.btn_usb)

        self.btn_take = _toggle("제어권 획득", "#b9770e", "#8a5a0a")
        self.btn_take.setEnabled(False)          # USB 연결 후에만
        self.btn_take.toggled.connect(self._on_take)
        v.addWidget(self.btn_take)
        return g

    def _build_jog(self) -> QGroupBox:
        """로봇 조그 — 3×3 방향 패드.

        방향 구성(사용자 지시): 4방위 = 직진·후진·좌크랩·우크랩, 대각선 = 45° 크랩.
        ⚠ 표시는 **직접 실측이 아니라 도출된 방향**이라는 뜻이다(저속 1회 육안 확인 후 사용).
          직접 실측: 조향 홈+raw 음수=전진 · 조향 +90°+raw 양수=좌(IMU ay 실증)
        """
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
        self.jog_buttons = {}
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
            self.jog_buttons[label] = b
        v.addLayout(grid)
        return g

    def _build_wheel_adj(self) -> QGroupBox:
        """앞뒤 바퀴 조향각 조정.

        폴링 중(제어권 보유)에는 그림이 **실측**을 따르므로 여기 값은 목표로만 남는다.
        폴링 전에는 그림이 이 값을 그대로 반영한다(각도 확인용).
        범위 ±90° — 기구 한계 ±140° 이나 실측 검증 범위가 ±90° 라 여기서 자른다.
        """
        g = QGroupBox("앞뒤 바퀴 조정")
        grid = QGridLayout(g)
        grid.setSpacing(6)
        self.sld_front = QSlider(Qt.Horizontal)
        self.sld_rear = QSlider(Qt.Horizontal)
        self.lab_front = QLabel("0°")
        self.lab_rear = QLabel("0°")
        for sld, lab in ((self.sld_front, self.lab_front), (self.sld_rear, self.lab_rear)):
            sld.setRange(-90, 90)
            sld.setValue(0)
            sld.setTickInterval(30)
            sld.setTickPosition(QSlider.TicksBelow)
            sld.valueChanged.connect(self._on_wheel_adj)
            lab.setMinimumWidth(46)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for r, (name, sld, lab) in enumerate((("앞바퀴 (N3)", self.sld_front, self.lab_front),
                                              ("뒷바퀴 (N4)", self.sld_rear, self.lab_rear))):
            grid.addWidget(QLabel(name), r, 0)
            grid.addWidget(sld, r, 1)
            grid.addWidget(lab, r, 2)
        grid.setColumnStretch(1, 1)
        return g

    def _on_wheel_adj(self):
        f, r = self.sld_front.value(), self.sld_rear.value()
        self.lab_front.setText(f"{f:+d}°")
        self.lab_rear.setText(f"{r:+d}°")
        self.log(f"바퀴 조정 목표 — 앞 {f:+d}° / 뒤 {r:+d}°")
        if not self._run:                 # 폴링 중이면 실측이 우선
            self.wheel.set_angles(f, r)

    def _build_settings(self) -> QGroupBox:
        """조그 설정 — 바퀴 속도 · 회전 각도 · 허용치.

        기본·상한 근거:
          속도 상한 200 mm/s = vmax 0.2 m/s (config/tongyi_amr.yaml). 기본 50 mm/s(저속).
          조향 ±90° — 기구 한계는 ±140° 이나 **실측 검증 범위가 ±90°** 라 여기서 자른다.
          정착 허용 3.0° = steer_settle_tol_deg (config).
        """
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
        self.spn_tol.setToolTip("정착 허용치 — 목표↔실측 편차가 이 값 이내여야 정착으로 본다.\n"
                                "config steer_settle_tol_deg 기본 3.0°.")

        for r, (lab, w) in enumerate((("바퀴 속도", self.spn_speed),
                                      ("정착 허용치", self.spn_tol),
)):
            grid.addWidget(QLabel(lab), r, 0)
            grid.addWidget(w, r, 1)
        grid.setColumnStretch(1, 1)
        return g

    def _build_motors(self) -> QGroupBox:
        """각 모터 값 — 각도·회전·전류만(사용자 지시).

        노드(실측 정본 §1): 1=FrontWalk 2=RearWalk 구동 · 3=FrontSteer 4=RearSteer 조향.
        각도는 조향축, 회전은 구동축에서 의미가 있어 해당 없는 칸은 '—' 로 둔다.
        """
        g = QGroupBox("모터 값")
        v = QVBoxLayout(g)
        self.tbl_motor = QTableWidget(4, 4)
        self.tbl_motor.setHorizontalHeaderLabels(["모터", "각도(°)", "회전(rpm)", "전류(A)"])
        self.tbl_motor.verticalHeader().setVisible(False)
        self.tbl_motor.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_motor.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_motor.verticalHeader().setDefaultSectionSize(26)
        self.tbl_motor.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r, name in enumerate(("1  F.W", "2  R.W", "3  F.S", "4  R.S")):
            self.tbl_motor.setItem(r, 0, QTableWidgetItem(name))
            for c in (1, 2, 3):
                it = QTableWidgetItem("—")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_motor.setItem(r, c, it)
        self.tbl_motor.setFixedHeight(26 * 4 + self.tbl_motor.horizontalHeader().height() + 8)
        self.tbl_motor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(self.tbl_motor)
        return g

    def set_motor_values(self, node: int, deg=None, rpm=None, amp=None):
        """노드(1~4) 행의 각도·회전·전류를 갱신한다. None 은 '—' 유지."""
        r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if r is None:
            return
        for c, val, fmt in ((1, deg, "{:+.1f}"), (2, rpm, "{:+.1f}"), (3, amp, "{:+.2f}")):
            if val is not None:
                self.tbl_motor.item(r, c).setText(fmt.format(val))

    def _build_status(self) -> QLabel:
        """맨 아래 상태 바 — Seer 접속 정보."""
        self.lab_status = QLabel(f"Seer {SEER_IP} · 접속 시도 중…")
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; color:#5d6d7e;")
        return self.lab_status

    def _on_seer_status(self, text: str, ok: bool):
        self.lab_status.setText(text)
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; "
            + ("color:#1e8449;" if ok else "color:#c0392b;"))

    def _build_seer(self) -> QGroupBox:
        """Seer 가 보고하는 같은 값 — 위 '모터 값'(판다 직접 읽기)과 비교용.

        출처: Seer API 1040 (network, 읽기 전용). position(rad)·speed·current(A).
        ⚠ 제어권 보유 중에는 freeze 펌웨어가 Seer 에게 정지 스냅샷을 돌려주므로
          Seer 값이 실제 움직임을 반영하지 않을 수 있다 — 그때는 비교가 성립하지 않는다.
        """
        g = QGroupBox("Seer 값 (비교)")
        v = QVBoxLayout(g)
        self.tbl_seer = QTableWidget(4, 4)
        self.tbl_seer.setHorizontalHeaderLabels(["모터", "각도(°)", "회전", "전류(A)"])
        self.tbl_seer.verticalHeader().setVisible(False)
        self.tbl_seer.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_seer.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_seer.verticalHeader().setDefaultSectionSize(26)
        self.tbl_seer.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_seer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for r, name in enumerate(("1  F.W", "2  R.W", "3  F.S", "4  R.S")):
            self.tbl_seer.setItem(r, 0, QTableWidgetItem(name))
            for c in (1, 2, 3):
                it = QTableWidgetItem("—")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_seer.setItem(r, c, it)
        self.tbl_seer.setFixedHeight(26 * 4 + self.tbl_seer.horizontalHeader().height() + 8)
        v.addWidget(self.tbl_seer)
        return g

    @staticmethod
    def _fmt_alarm(item) -> str:
        """1050 항목을 한 줄로. 구조가 확정되지 않아 방어적으로 처리한다."""
        if isinstance(item, dict):
            code = item.get("code", item.get("id", ""))
            desc = (item.get("desc") or item.get("description")
                    or item.get("msg") or item.get("message") or "")
            return f"{code} {desc}".strip() or str(item)
        return str(item)

    def _seer_loop(self):
        """Seer 1040(모터)·1050(알람) 폴링 — 네트워크 읽기 전용. 제어권과 무관하다."""
        try:
            if SEER_GUI not in sys.path:
                sys.path.insert(0, SEER_GUI)
            from seer_core.client import RobokitClient
            cli = RobokitClient(SEER_IP)
        except Exception as exc:
            self.log_line.emit(f"Seer 연결 불가: {type(exc).__name__}: {exc}")
            self.seer_status.emit(f"Seer {SEER_IP} · 연결 불가 ({type(exc).__name__})", False)
            return
        while self._seer_run:
            try:
                d = cli.call("status", 1040)
                ms = d.get("motor_info") or d.get("motors") or []
                self.seer_data.emit({int(m["can_id"]): m for m in ms if m.get("can_id")})
                self.seer_status.emit(
                    f"Seer {SEER_IP} · 연결됨 · 모터 {len(ms)}축 · 갱신 {time.strftime('%H:%M:%S')}",
                    True)
            except Exception as exc:       # 일시 실패는 상태 바에만 (제어 경로 아님)
                self.seer_status.emit(f"Seer {SEER_IP} · 폴링 실패 ({type(exc).__name__})", False)

            # 알람(1050)은 4 주기(=약 2 s)에 한 번. **신규만** 로그에 남긴다 —
            # Seer 는 해제되지 않은 오래된 항목도 계속 목록에 들고 있어서
            # 전량을 매번 찍으면 방금 난 것처럼 보인다(2026-07-27 오해 사례).
            self._alarm_tick += 1
            if self._alarm_tick % 4 == 0:
                try:
                    a = cli.call("status", 1050)
                    self.alarm_counts.emit(len(a.get("fatals") or []),
                                           len(a.get("errors") or []))
                    for lvl in ("fatals", "errors", "warnings", "notices"):
                        for item in (a.get(lvl) or []):
                            line = self._fmt_alarm(item)
                            key = f"{lvl}|{line}"
                            if key not in self._alarm_seen:
                                self._alarm_seen.add(key)
                                self.seer_log_line.emit(f"[{lvl}] {line}")
                except Exception:
                    pass
            time.sleep(0.5)

    def _on_seer_data(self, data: dict):
        for node, m in data.items():
            r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
            if r is None:
                continue
            pos = m.get("position")
            deg = None if pos is None else pos * 180.0 / math.pi
            for c, val, fmt in ((1, deg, "{:+.1f}"),
                                (2, m.get("speed"), "{:+.1f}"),
                                (3, m.get("current"), "{:+.2f}")):
                if val is not None:
                    self.tbl_seer.item(r, c).setText(fmt.format(val))

    def _build_wheel(self) -> QGroupBox:
        g = QGroupBox("차량 바퀴 상태")
        v = QVBoxLayout(g)
        self.wheel = WheelView()
        v.addWidget(self.wheel)
        return g

    def _build_log(self) -> QWidget:
        """로그 영역 — 위: GUI 동작 로그, 아래: Seer 알람 로그."""
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
            "Seer config API 4300 (robot_config_clearfatal_req) — Fatal 오류코드만 지운다.\n"
            "errors·warnings 는 대상이 아니다. [robotkit-netprotocol L 1.2.1 §5.2.5]")
        self.btn_clear_fatal.clicked.connect(self._on_clear_fatal)
        self._set_alarm_color(0, 0)
        v2.addWidget(self.btn_clear_fatal)
        v.addWidget(g2, 1)
        return w

    def seer_log(self, msg: str):
        self.txt_seer_log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {msg}")

    def _set_alarm_color(self, n_fatal: int, n_error: int):
        """오류가 있으면 붉은색, 없으면 초록색.

        ⚠ 버튼이 실제로 지우는 것은 **Fatal 뿐**이다(4300). error 만 있을 때도 붉은색이지만
          눌러도 error 는 사라지지 않는다 — 그래서 건수를 라벨에 함께 적어 오해를 막는다.
        """
        bad = (n_fatal + n_error) > 0
        self.btn_clear_fatal.setText(
            f"Fatal 오류 리셋   (fatal {n_fatal} / error {n_error})")
        on = "#c0392b" if bad else "#1e8449"
        edge = "#8f2b20" if bad else "#166437"
        self.btn_clear_fatal.setStyleSheet(
            f"QPushButton {{ background:{on}; color:white; font-weight:bold;"
            f" border:1px solid {edge}; border-radius:4px; }}"
            "QPushButton:disabled { background:#d5dbe1; color:#8894a2; border:1px solid #c3ccd4; }")

    def _on_clear_fatal(self):
        """Seer Fatal 오류코드 클리어 — config API 4300.

        근거: References/Seer-Driver/github_sdk/robotkit-netprotocol-l-1.2.1.txt §5.2.5
              요청 4300 (0x10CC) robot_config_clearfatal_req / 응답 14300, JSON 데이터 없음.
        ⚠ 이름 그대로 **Fatal 만** 지운다. errors·warnings 는 대상이 아니다(표시는 계속 유지).
        ⚠ 지금까지의 Seer 기능과 달리 이건 **로봇 상태를 바꾸는 쓰기 명령**이다.
        """
        self.btn_clear_fatal.setEnabled(False)

        def work():
            try:
                if SEER_GUI not in sys.path:
                    sys.path.insert(0, SEER_GUI)
                from seer_core.client import RobokitClient
                res = RobokitClient(SEER_IP).call("config", 4300)
                rc = res.get("ret_code") if isinstance(res, dict) else res
                self.seer_log_line.emit(f"Fatal 리셋 요청(4300) → ret_code={rc}")
                self._alarm_seen.clear()          # 재표시되게 중복필터 초기화
            except Exception as exc:
                self.seer_log_line.emit(f"Fatal 리셋 실패: {type(exc).__name__}: {exc}")
            finally:
                self.clear_done.emit()

        threading.Thread(target=work, daemon=True, name="clearfatal").start()

    # ── 동작 ────────────────────────────────────────────────────────────
    def log(self, msg: str):
        self.txt_log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {msg}")

    def scan(self):
        """연결 가능한 판다 열거 — USB 를 열지 않는다(목록만)."""
        self.cmb_panda.clear()
        try:
            serials = _panda_class().list()
        except Exception as exc:
            self.log(f"판다 검색 실패: {type(exc).__name__}: {exc}")
            self.btn_usb.setEnabled(False)
            return
        if serials:
            self.cmb_panda.addItems(serials)
            self.log(f"판다 {len(serials)}대 검출: {', '.join(serials)}")
        else:
            self.log("판다 없음 — USB 연결·udev 규칙 확인")
        self.btn_usb.setEnabled(bool(serials))

    def _on_usb(self, on: bool):
        """USB 열기/닫기. safety mode·릴레이를 건드리지 않으므로 모터에 영향 없다."""
        self.btn_usb.setText("판다 USB 해제" if on else "판다 USB 연결")
        if on:
            try:
                self.panda = _panda_class()()
                h = self.panda.health()
                self.log(f"USB 연결 — fw={self.panda.get_version()} "
                         f"safety={h['safety_mode']} harness={h['car_harness_status']}")
            except Exception as exc:
                self.log(f"USB 연결 실패: {type(exc).__name__}: {exc}")
                self.btn_usb.setChecked(False)
                return
        else:
            if self.btn_take.isChecked():
                self.btn_take.setChecked(False)      # 제어권부터 반환
            if self.panda is not None:
                try:
                    self.panda.close()
                except Exception:
                    pass
                self.panda = None
            self.log("USB 해제")
        self.btn_take.setEnabled(on)

    def _on_take(self, on: bool):
        """제어권 획득/반환. 획득하면 Seer 로부터 릴레이를 가져오고 폴링을 시작한다."""
        self.btn_take.setText("제어권 해제" if on else "제어권 획득")
        if self.panda is None:
            return
        P = _panda_class()
        try:
            if on:
                self.log("⚠ 제어권 획득 — 릴레이 intercept, Seer 에서 가져옴")
                self.panda.set_safety_mode(SEER_GATE, 0)
                for b in (SEER_BUS, MOTOR_BUS):
                    self.panda.set_can_speed_kbps(b, CAN_KBPS)
                    self.panda.set_can_enable(b, True)
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe9, 1, 0, b"")   # auth=PC
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe8, 1, 0, b"")   # intercept
                self._run = True
                self._th = threading.Thread(target=self._loop, daemon=True, name="poll")
                self._th.start()
                self.log("제어권 획득 완료 — 모터 값 폴링 시작")
            else:
                self._jog_stop = True
                try:
                    self._drive(0)          # 반환 전 반드시 정지
                except Exception:
                    pass
                self._run = False
                if self._th is not None:
                    self._th.join(timeout=1.0)
                    self._th = None
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe9, 0, 0, b"")   # auth=Seer
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xe8, 0, 0, b"")   # passthrough
                self.panda.set_safety_mode(0, 0)
                self.log("제어권 반환 — passthrough (USB 유지)")
        except Exception as exc:
            self.log(f"제어권 처리 실패: {type(exc).__name__}: {exc}")

    # ── 조그 실행 (crab: 조향 → 정착 확인 → 구동) ──────────────────────
    def _sdo_write(self, node: int, idx: int, val: int, size: int):
        """SDO expedited 쓰기. 폴링 스레드와 버스를 공유하므로 락으로 직렬화한다."""
        cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
        payload = (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
        data = bytes([cmd, idx & 0xFF, idx >> 8, 0]) + payload + b"\x00" * (4 - size)
        with self._can_lock:
            self.panda.can_send(0x600 + node, data[:8], MOTOR_BUS)

    def _drive(self, units: int):
        """구동 노드에 속도 지령(0x60FF). units=0 이면 정지."""
        for n in (1, 2):
            self._sdo_write(n, 0x60FF, units, 4)

    def _steer_to(self, deg: float) -> float:
        """조향 두 축에 절대위치 지령(0x607A) + 즉시 적용(0x6040=0x3F).

        **가동범위 밖은 보내지 않는다** — 실측 검증 범위 ±90° 로 자른다.
        (node4 가 범위 밖으로 밀려 물리적으로 갇힌 사고가 있었다: claude-mistake 2026-07-27-002)

        단계로 쪼개지 않는다. 실기 캡처상 Seer 도 최종 절대 목표를 그대로 반복 송신하고
        이동 프로파일은 드라이브가 수행한다(Log/homing_capture_220350.jsonl:
        node3 0x607A 6,464 회 송신 · 서로 다른 값은 4 개뿐).
        """
        deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
        for n in (3, 4):
            self._sdo_write(n, 0x607A, int(round(STEER_HOME[n] + deg * COUNTS_PER_DEG)), 4)
            self._sdo_write(n, 0x6040, 0x3F, 2)
        return deg

    def _jog(self, label: str):
        """조그 버튼. crab 이므로 **바퀴를 먼저 돌리고 정착을 확인한 뒤** 주행한다."""
        if not self._run:
            self.log("조그 불가 — 제어권을 먼저 획득하세요")
            return
        if label == "정지":
            self._jog_stop = True
            self._drive(0)
            self.log("정지 — 구동 0 (조향은 현 위치 유지)")
            return
        if self._jog_th is not None and self._jog_th.is_alive():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        steer_deg, raw_sign, _ = JOG[label]
        self._jog_stop = False
        self._jog_th = threading.Thread(target=self._jog_run, name="jog", daemon=True,
                                        args=(label, steer_deg, raw_sign))
        self._jog_th.start()

    def _jog_run(self, label: str, steer_deg: float, raw_sign: int):
        """crab 순서: 구동 0 → 조향 지령 → 정착 확인 → 구동."""
        try:
            tol = float(self.spn_tol.value())
            mmps = float(self.spn_speed.value())
            self._drive(0)                                  # 조향 전 반드시 구동 0
            tgt = self._steer_to(steer_deg)
            self.log_line.emit(f"조그 '{label}' — 조향 {tgt:+.0f}° 지령, 정착 대기")
            if not self._wait_settle(tgt, tol):
                self.log_line.emit(f"조향 정착 실패(실측 {self._meas_deg.get(3)}) — 구동 취소")
                self._drive(0)
                return
            if self._jog_stop:
                self._drive(0)
                return
            units = int(round(raw_sign * mmps * VEL_PER_MMPS))
            units = max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS, units))
            self._drive(units)
            self.log_line.emit(f"조향 정착 — 구동 raw={units:+d} ({mmps:.0f} mm/s)")
        except Exception as exc:
            self.log_line.emit(f"조그 중단: {type(exc).__name__}: {exc}")
            try:
                self._drive(0)
            except Exception:
                pass

    def _wait_settle(self, target: float, tol: float, timeout: float = 6.0) -> bool:
        """한 단계의 조향 정착 대기. 시간 초과면 False(= 추종 실패)."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._jog_stop:
                return False
            cur = self._meas_deg.get(3)
            if cur is not None and abs(target - cur) <= tol:
                return True
            time.sleep(0.05)
        return False

    # ── 폴링 (모터 값 읽기 전용 — 지령은 보내지 않는다) ────────────────
    def _loop(self):
        """0x6064(위치)·0x606C(속도)·0x6078(전류)를 SDO 로 읽어 화면에 올린다.

        ⚠ 읽기만 한다. 0x60FF(속도지령)·0x607A(위치지령)는 보내지 않는다.
        """
        P = _panda_class()
        while self._run:
            try:
                # heartbeat 0.4 s — 끊기면 펌웨어가 fail-safe 로 intercept 를 푼다.
                self.panda._handle.controlWrite(P.REQUEST_OUT, 0xf3, 0, 0, b"")
                with self._can_lock:
                    for n in (1, 2, 3, 4):
                        for idx in (0x6064, 0x606C, 0x6078):
                            self.panda.can_send(0x600 + n,
                                                bytes([0x40, idx & 0xFF, idx >> 8, 0, 0, 0, 0, 0]),
                                                MOTOR_BUS)
                time.sleep(0.08)
                out = {}
                for addr, _t, dat, bus in self.panda.can_recv():
                    if bus != MOTOR_BUS or not (0x581 <= addr <= 0x584) or len(dat) < 8:
                        continue
                    node = addr - 0x580
                    idx = dat[1] | (dat[2] << 8)
                    if dat[0] == 0x43:                       # 4 바이트 응답
                        val = int.from_bytes(dat[4:8], "little", signed=True)
                    elif dat[0] == 0x4B:                     # 2 바이트 응답
                        val = int.from_bytes(dat[4:6], "little", signed=True)
                    else:
                        continue
                    out.setdefault(node, {})[idx] = val
                if out:
                    self.motor_data.emit(out)
            except Exception as exc:
                self._run = False
                self.log_line.emit(f"폴링 중단: {type(exc).__name__}: {exc}")
                return
            time.sleep(0.12)

    def _on_motor_data(self, data: dict):
        """폴링 결과 → 표 + 바퀴 그림 (GUI 스레드)."""
        angles = {}
        for node, vals in data.items():
            deg = rpm = amp = None
            if 0x6064 in vals and node in STEER_HOME:
                deg = (vals[0x6064] - STEER_HOME[node]) / COUNTS_PER_DEG
                angles[node] = deg
                self._meas_deg[node] = deg
            if 0x606C in vals:
                rpm = vals[0x606C] / 10.0                    # 0.1 r/min
            if 0x6078 in vals:
                amp = vals[0x6078] / 100.0                   # 0.01 A
            self.set_motor_values(node, deg, rpm, amp)
        if angles:
            self.wheel.set_angles(angles.get(3, self.wheel.front_deg),
                                  angles.get(4, self.wheel.rear_deg))


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
