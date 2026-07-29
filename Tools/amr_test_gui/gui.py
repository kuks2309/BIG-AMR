#!/usr/bin/env python3
"""Tongyi 4축 AMR 구동 테스트 GUI — 실기 전용. 화면(위젯 배치와 시그널 배선)만 담당한다.

세 계층으로 나뉜다. **증상이 보이면 어느 파일을 볼지 여기서 갈린다** —

| 파일 | 책임 | Qt |
| --- | --- | --- |
| `tongyi_can.py` | SDO 인코딩·조향/구동 지령·호밍·폴링 | 무의존 |
| `seer_status.py` | Seer 1040/1050 폴링·알람·Fatal 리셋 | 무의존 |
| `gui.py` (본 파일) | 위젯 배치·시그널 배선·종료 사슬 | 전담 |

하위 두 계층은 결과를 **콜백**으로 낸다. 이 파일이 그 콜백에 Qt 시그널 emit 을 꽂아
스레드 경계를 넘기므로, 위젯은 언제나 GUI 스레드에서만 만져진다.
"""
from __future__ import annotations

import atexit
import math
import signal
import sys
import threading
import time

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (QApplication, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
                             QMessageBox, QPushButton, QDoubleSpinBox,
                             QSlider, QSpinBox,
                             QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from seer_status import SEER_IP, SeerStatus
from tongyi_can import JOG, STEER_HOME, TongyiCan

# 상수·환산은 `tongyi_can`(CAN)·`seer_status`(네트워크)가 소유한다 — 이 파일은 화면에
# 필요한 것만 가져다 쓴다. 값의 근거는 코드가 아니라 README.md §주요 상수 가 든다.


class WheelView(QWidget):
    """차량 바퀴 상태 top-view. 조향각을 그대로 그림에 반영한다.

    기하(EasyDRIVE config 값 — 본 기체 직접 실측은 아니다. 시각화 전용):
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
    homing_done = pyqtSignal()
    enable_done = pyqtSignal()

    def __init__(self):
        super().__init__()
        # CAN 계층. 결과는 콜백으로 받는데, 전부 Qt 시그널 emit 이라 폴링·조그·호밍
        # 스레드에서 불려도 위젯은 GUI 스레드에서만 만져진다.
        self.can = TongyiCan(log=self.log_line.emit,
                             on_frames=self.motor_data.emit,
                             on_homing_done=self.homing_done.emit)
        # Seer 폴링(네트워크 읽기 전용). 콜백은 폴링 스레드에서 불리므로 전부 시그널이다.
        self.seer = SeerStatus(on_motors=self.seer_data.emit,
                               on_status=self.seer_status.emit,
                               on_log=self.seer_log_line.emit,
                               on_alarm_counts=self.alarm_counts.emit)
        # 해제 사슬을 이미 돌렸는지. 종료 경로가 4개(창 닫기·정지 신호·이벤트루프 종료·
        # 인터프리터 종료)라 같은 사슬이 여러 번 불린다 — `safe_release()` 멱등화 래치.
        self._released = False
        self._seer_deg: dict = {}       # Seer 1040 이 보는 조향각(제어권 없을 때 그림 출처)
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
        mid.addWidget(self._build_settings(), 0) # 맨 아래 — 속도·허용치 설정
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
        self.homing_done.connect(lambda: self.btn_home.setEnabled(True))
        self.enable_done.connect(lambda: self.btn_enable.setEnabled(True))
        self.seer.start()
        self.log("GUI 기동 — 실기 전용")
        self.scan()

    # ── 종료 계약 ────────────────────────────────────────────────────────
    # `safe_release()` 가 만지는 세 이름. 실제 자원은 하위 계층이 들고 있고
    # (`panda`·`_jog_stop` → `TongyiCan`, `_seer_run` → `SeerStatus`) 여기서는 이름만
    # 빌려준다. 종료 4경로가 전부 이 표면으로 들어오므로 계층을 나눈 뒤에도 해제 사슬의
    # 모양을 바꾸지 않는다 — `test_safe_release.py` 가 그 모양을 고정한다.
    @property
    def panda(self):
        return self.can.panda

    @panda.setter
    def panda(self, value):
        self.can.panda = value

    @property
    def _jog_stop(self) -> bool:
        return self.can._jog_stop

    @_jog_stop.setter
    def _jog_stop(self, value: bool):
        self.can._jog_stop = value

    @property
    def _seer_run(self) -> bool:
        return self.seer.running

    @_seer_run.setter
    def _seer_run(self, value: bool):
        self.seer.running = value

    def safe_release(self, reason: str = "") -> None:
        """제어권을 반환하고 USB 를 해제한다. **모든 종료 경로가 이 함수를 공유한다.**

        창을 닫는 정상 종료만 안전하면 부족하다 — Ctrl+C·`kill`·처리되지 않은 예외로 죽으면
        릴레이가 intercept 로, USB 가 열린 채로 남아 Seer 가 로봇을 되찾지 못한다. `main()` 이
        4경로(창 닫기·정지 신호·이벤트루프 종료·인터프리터 종료)를 여기로 모은다.

        **`btn_take.setChecked(False)` 에 의존하지 않는다.** 그것은 Qt 시그널 전달을 거쳐
        `_on_take(False)` 를 부르는 경로인데, `atexit` 시점에는 이벤트 루프가 이미 끝나고 C++
        객체가 파괴돼 있을 수 있어 **해제가 조용히 누락된다.** 그래서 `_on_take(False)` 를
        직접 호출한다. 종료 중이므로 버튼의 시각 상태는 의미가 없다.

        **멱등이다** — 여러 경로가 연달아 불러도 두 번째부터는 즉시 반환한다.

        Args:
            reason: 어느 경로로 들어왔는지(로그용). 사후 분석에서 원인을 가른다.
        """
        if self._released:
            return
        self._released = True
        print(f"[gui] 해제 시작 — {reason}", flush=True)
        self._seer_run = False
        self._jog_stop = True
        if self.panda is not None:
            try:
                # 제어권 보유 여부와 무관하게 반환을 시도한다 — 보유하지 않은 상태에서의
                # 중복 반환은 무해하지만, 보유 중인데 건너뛰면 릴레이가 intercept 로 남는다.
                self._on_take(False)
            except Exception as exc:
                print(f"[gui] ⚠ 종료 중 제어권 반환 예외: {exc}", flush=True)
            try:
                self.panda.close()
            except Exception as exc:
                print(f"[gui] ⚠ 종료 중 USB close 예외: {exc}", flush=True)
            self.panda = None
        print("[gui] 해제 완료 — 제어권 반환 · USB 연결 해제", flush=True)

    def closeEvent(self, ev):
        """창 닫기 경로. 해제는 `safe_release()` 가 소유한다."""
        self.safe_release("창 닫기")
        ev.accept()

    # ── 화면 ────────────────────────────────────────────────────────────
    def _build_connect(self) -> QGroupBox:
        g = QGroupBox("연결")
        v = QVBoxLayout(g)

        v.addWidget(QLabel("연결 가능한 판다"))
        pick = QHBoxLayout()
        # 1 PC = 판다 1대가 이 시스템의 원칙이라 고를 것이 없다 — 표시만 한다.
        self.lab_panda = QLabel("검색 전")
        self.lab_panda.setStyleSheet(
            "padding:5px 8px; border:1px solid #cfd8e0; border-radius:3px; color:#5d6d7e;")
        self.btn_scan = QPushButton("검색")
        self.btn_scan.setMinimumHeight(28)
        self.btn_scan.clicked.connect(self.scan)
        pick.addWidget(self.lab_panda, 1)
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
        """로봇 조그 — 3×3 방향 패드 + 호밍 버튼.

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

        # 호밍 + 조향 0°. 방향 패드와 성격이 달라(준비 동작·큰 이동) 줄을 나눈다.
        # 이름에 두 동작을 다 적는다 — 호밍만 하고 끝나는 것으로 읽히면 안 된다.
        self.btn_home = QPushButton("⌂  호밍 후 조향 0°")
        self.btn_home.setMinimumHeight(38)
        self.btn_home.setStyleSheet(
            "QPushButton { background:#5b6b7c; color:white; font-weight:bold;"
            " border:1px solid #44515e; border-radius:4px; margin-top:6px; }"
            "QPushButton:disabled { background:#e8edf2; color:#8894a2; }")
        self.btn_home.clicked.connect(self._homing_clicked)
        v.addWidget(self.btn_home)

        # 구동축 운전 가능 복구. 조향과 달리 구동은 지령(0x60FF)만으로 켜지지 않아,
        # fault 나 disable 로 떨어지면 이 버튼 말고는 되살릴 방법이 없다.
        self.btn_enable = QPushButton("⚡  구동축 활성화 (FAULT 해제)")
        self.btn_enable.setMinimumHeight(32)
        self.btn_enable.setStyleSheet(
            "QPushButton { background:#7d6608; color:white; font-weight:bold;"
            " border:1px solid #5e4d06; border-radius:4px; margin-top:4px; }"
            "QPushButton:disabled { background:#e8edf2; color:#8894a2; }")
        self.btn_enable.clicked.connect(self._enable_drives_clicked)
        v.addWidget(self.btn_enable)
        return g

    def _enable_drives_clicked(self):
        """구동축을 운전 가능 상태로 되돌린다 (CiA402 — Handbook §6.6.1).

        fault 원인을 지우는 것이 아니라 **상태만** 되돌린다. 과부하로 떨어진 것이면
        원인을 두고 다시 켤 때 재발하거나 모터를 상하게 할 수 있어 확인을 받는다.
        """
        if not self.can.running:
            self.log("구동축 활성화 불가 — 제어권을 먼저 획득하세요")
            return
        faults = self.can.drive_faults()
        ready = self.can.drives_ready()
        if QMessageBox.question(
                self, "구동축 활성화",
                f"구동축을 운전 가능 상태로 되돌립니다.\n\n"
                f"· 현재 operation enabled: {ready}\n"
                f"· 현재 fault: {faults}\n\n"
                "⚠ 이 조작은 **상태만** 되돌립니다. FAULT 의 원인(과부하·물림 등)이\n"
                "  남아 있으면 곧 재발하거나 모터를 상하게 할 수 있습니다.\n"
                "  부하·기구 상태를 먼저 확인하셨습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            self.log("구동축 활성화 취소")
            return
        self.btn_enable.setEnabled(False)
        threading.Thread(target=self._enable_drives_run, name="enable",
                         daemon=True).start()

    def _enable_drives_run(self):
        try:
            self.can.enable_drives()
        finally:
            self.enable_done.emit()

    def _build_wheel_adj(self) -> QGroupBox:
        """앞뒤 바퀴 조향각 조정.

        여기 값은 **목표**다. 그림은 실측(판다 또는 Seer)이 있으면 그쪽을 그리고,
        실측이 하나도 없을 때만 이 값을 미리보기로 그린다 — `_redraw_wheel` 참조.
        슬라이더 range 자체가 ±90° 라 범위 밖은 만들 수 없다.
        """
        g = QGroupBox("앞뒤 바퀴 조정")
        v = QVBoxLayout(g)
        v.setSpacing(2)
        self.sld_front = QSlider(Qt.Horizontal)
        self.sld_rear = QSlider(Qt.Horizontal)
        self.lab_front = QLabel("+0°")
        self.lab_rear = QLabel("+0°")

        # **슬라이더는 자기 줄을 통째로 쓴다.** 이름·값과 한 줄에 나란히 놓았더니 폭이
        # 78 px 밖에 남지 않아(±90° = 181 단계) 1 px 이 2.3° 였고 핸들을 잡을 수 없었다.
        for node, name, sld, lab in ((3, "앞바퀴 (N3)", self.sld_front, self.lab_front),
                                     (4, "뒷바퀴 (N4)", self.sld_rear, self.lab_rear)):
            head = QHBoxLayout()
            head.addWidget(QLabel(name))
            head.addStretch(1)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            head.addWidget(lab)
            v.addLayout(head)

            sld.setRange(-90, 90)
            sld.setValue(0)
            sld.setTickInterval(30)
            sld.setTickPosition(QSlider.TicksBelow)
            sld.setMinimumHeight(30)          # 잡기 쉬운 높이
            sld.setPageStep(5)                # 홈을 클릭하면 5°씩
            sld.setEnabled(False)             # 제어권을 쥐기 전에는 잠근다
            sld.valueChanged.connect(lambda _val, n=node: self._on_wheel_changed(n))
            sld.sliderReleased.connect(lambda n=node: self._send_steer(n))
            v.addWidget(sld)
            v.addSpacing(4)
        self._sync_steer_enabled()
        return g

    def _sync_steer_enabled(self):
        """조향 슬라이더는 **제어권을 쥐고 있을 때만** 움직인다.

        전에는 항상 움직이고 지령 단계에서 로그로만 거부했다 — 눈금은 옮겨졌는데 바퀴는
        가만히 있으니 화면이 실제와 어긋났다. 잡히지 않으면 애초에 옮길 수 없게 한다.
        """
        on = self.can.running
        for sld in (self.sld_front, self.sld_rear):
            sld.setEnabled(on)
            sld.setToolTip("" if on else "제어권을 획득해야 조향할 수 있습니다.")

    def _on_wheel_changed(self, node: int):
        """슬라이더 값이 바뀌었다.

        마우스로 **끄는 중**이면 아직 보내지 않는다 — 매 틱 보내면 버스가 지령으로 찬다.
        손을 떼면 `sliderReleased` 가 1 회 보낸다. 반대로 키보드·홈 클릭처럼 한 번에
        값이 뛰는 조작은 `sliderReleased` 가 오지 않으므로 **여기서** 보낸다.
        """
        self._redraw_wheel()
        sld = self.sld_front if node == 3 else self.sld_rear
        if not sld.isSliderDown():
            self._send_steer(node)

    def _send_steer(self, node: int):
        """그 축에만 조향 지령을 보낸다."""
        if not self.can.running:
            self.log("조향 지령 불가 — 제어권을 먼저 획득하세요")
            return
        deg = (self.sld_front if node == 3 else self.sld_rear).value()
        sent = self.can.steer_axis(node, float(deg))
        self.log(f"조향 지령 N{node} → {sent:+.0f}°")

    def _build_settings(self) -> QGroupBox:
        """조그 설정 — 바퀴 속도, 정착 허용치. 위젯은 이 둘뿐이다.

        속도 상한 200 mm/s(= 0.2 m/s), 기본 50 mm/s. 정착 허용 기본 3.0°.
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

    ROWS = ("1  F.W", "2  R.W", "3  F.S", "4  R.S")   # 표 행 = 노드 1~4
    CELL_FMT = ((1, "{:+.1f}"), (2, "{:+.1f}"), (3, "{:+.2f}"))   # 각도·회전·전류

    @staticmethod
    def _motor_table(rpm_header: str) -> QTableWidget:
        """4행 4열 모터 표를 만든다. '모터 값'과 'Seer 값' 두 표가 이걸 공유한다."""
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
    def _fill_row(cls, table: QTableWidget, node: int, values):
        """노드 행에 (각도, 회전, 전류) 를 써 넣는다. None 인 칸은 '—' 로 남는다."""
        r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if r is None:
            return
        for (c, fmt), val in zip(cls.CELL_FMT, values):
            if val is not None:
                table.item(r, c).setText(fmt.format(val))

    def _build_motors(self) -> QGroupBox:
        """각 모터 값 — 각도·회전·전류만(사용자 지시).

        노드: 1=FrontWalk 2=RearWalk 구동 · 3=FrontSteer 4=RearSteer 조향.
        각도는 조향축에서만 의미가 있어 구동축 각도 칸은 '—' 로 남는다.
        회전(rpm)·전류는 네 축 모두 채운다.
        """
        g = QGroupBox("모터 값")
        v = QVBoxLayout(g)
        self.tbl_motor = self._motor_table("회전(rpm)")
        v.addWidget(self.tbl_motor)
        return g

    def set_motor_values(self, node: int, deg=None, rpm=None, amp=None):
        """노드(1~4) 행의 각도·회전·전류를 갱신한다. None 은 '—' 유지."""
        self._fill_row(self.tbl_motor, node, (deg, rpm, amp))

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
        if not ok:
            # 폴링이 끊기면 마지막 값을 실측인 척 계속 그리지 않는다.
            self._seer_deg.clear()
            self._redraw_wheel()

    def _build_seer(self) -> QGroupBox:
        """Seer 가 보고하는 같은 값 — 위 '모터 값'(판다 직접 읽기)과 비교용.

        출처: Seer API 1040 (network, 읽기 전용). position(rad)·speed·current(A).
        ⚠ 제어권 보유 중에는 freeze 펌웨어가 Seer 에게 정지 스냅샷을 돌려주므로
          Seer 값이 실제 움직임을 반영하지 않을 수 있다 — 그때는 비교가 성립하지 않는다.
        """
        g = QGroupBox("Seer 값 (비교)")
        v = QVBoxLayout(g)
        self.tbl_seer = self._motor_table("회전")
        v.addWidget(self.tbl_seer)
        return g

    def _on_seer_data(self, data: dict):
        for node, m in data.items():
            pos = m.get("position")
            deg = None if pos is None else pos * 180.0 / math.pi
            self._fill_row(self.tbl_seer, node, (deg, m.get("speed"), m.get("current")))
            if node in (3, 4) and deg is not None:
                self._seer_deg[node] = deg
        self._redraw_wheel()

    def _meas_angle(self, node: int):
        """그 축의 실측 조향각. 제어권이 있으면 판다 직독, 없으면 Seer. 없으면 None."""
        return (self.can.meas_angle(node) if self.can.running
                else self._seer_deg.get(node))

    def _redraw_wheel(self):
        """바퀴 그림을 실측으로 그린다. 실측이 없을 때만 슬라이더 값을 미리보기로 쓴다.

        **슬라이더에는 절대 되쓰지 않는다.** 슬라이더는 사용자가 목표를 넣는 *명령* 입력이라
        실측을 되먹이면 방금 넣은 목표가 지워진다(실제로 그렇게 만들어 슬라이더가 먹통이 됐다).
        목표와 실측의 차이는 슬라이더 옆 라벨이 나란히 보여준다.
        """
        f, r = self._meas_angle(3), self._meas_angle(4)
        if f is None or r is None:
            f, r = self.sld_front.value(), self.sld_rear.value()   # 실측 없음 → 미리보기
        self.wheel.set_angles(f, r)
        self._update_wheel_labels()

    def _update_wheel_labels(self):
        """`목표°  (실측 …°)` — 슬라이더를 건드리지 않고 둘을 나란히 보여준다."""
        for node, sld, lab in ((3, self.sld_front, self.lab_front),
                               (4, self.sld_rear, self.lab_rear)):
            meas = self._meas_angle(node)
            if self.can.homing and not self.can.meas_fresh(node):
                tail = "  (실측 탐색 중)"      # 드라이브가 위치를 안 주는 구간
            elif meas is None:
                tail = ""
            else:
                tail = f"  (실측 {meas:+.1f}°)"
            lab.setText(f"{sld.value():+d}°" + tail)

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
        """Fatal 리셋 버튼. 요청은 `SeerStatus.clear_fatal` 이 별도 스레드로 보낸다."""
        self.btn_clear_fatal.setEnabled(False)
        self.seer.clear_fatal(done=self.clear_done.emit)

    # ── 동작 ────────────────────────────────────────────────────────────
    def log(self, msg: str):
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        self.txt_log.appendPlainText(line)
        print(f"[gui] {line}", flush=True)      # 창 밖(로그 파일)에서도 보이도록

    def scan(self):
        """연결 가능한 판다 열거 — USB 를 열지 않는다(목록만).

        **1 PC = 판다 1대**가 원칙이므로 고르는 UI 를 두지 않는다. 2대 이상 검출되면
        원칙 위반이라 경고만 하고, 실제로 열리는 것은 라이브러리가 먼저 찾은 1대다.
        """
        try:
            serials = self.can.list_pandas()
        except Exception as exc:
            self.lab_panda.setText("검색 실패")
            self.log(f"판다 검색 실패: {type(exc).__name__}: {exc}")
            self.btn_usb.setEnabled(False)
            return
        if not serials:
            self.lab_panda.setText("판다 없음")
            self.log("판다 없음 — USB 연결·udev 규칙 확인")
        elif len(serials) == 1:
            self.lab_panda.setText(serials[0])
            self.log(f"판다 검출: {serials[0]}")
        else:
            self.lab_panda.setText(f"⚠ {len(serials)}대 검출")
            self.log(f"⚠ 판다 {len(serials)}대 검출({', '.join(serials)}) — 1 PC 1대 원칙 위반. "
                     f"여는 것은 그중 1대뿐이다.")
        self.btn_usb.setEnabled(bool(serials))

    def _on_usb(self, on: bool):
        """USB 열기/닫기.

        **연결(on)** 은 장치를 열어 상태만 읽으므로 모터에 영향이 없다.
        **해제(off)** 는 제어권이 잡혀 있으면 먼저 반환시킨다 — 그 경로에서 auth·intercept 를
        내리고 safety mode 를 0 으로 되돌리므로 릴레이 상태가 바뀐다.
        """
        self.btn_usb.setText("판다 USB 해제" if on else "판다 USB 연결")
        if on:
            try:
                h = self.can.open_usb()
                self.log(f"USB 연결 — fw={self.can.panda.get_version()} "
                         f"safety={h['safety_mode']} harness={h['car_harness_status']}")
            except Exception as exc:
                self.log(f"USB 연결 실패: {type(exc).__name__}: {exc}")
                self.btn_usb.setChecked(False)
                return
        else:
            if self.btn_take.isChecked():
                self.btn_take.setChecked(False)      # 제어권부터 반환
            self.can.close_usb()
            self.log("USB 해제")
        self.btn_take.setEnabled(on)

    def _on_take(self, on: bool):
        """제어권 획득/반환 버튼. 릴레이·폴링 조작은 `TongyiCan.take` 가 수행한다."""
        self.btn_take.setText("제어권 해제" if on else "제어권 획득")
        try:
            self.can.take(on)
        except Exception as exc:
            self.log(f"제어권 처리 실패: {type(exc).__name__}: {exc}")
        # 실제로 잡혔는지(`running`)를 보고 잠금을 맞춘다 — 버튼이 눌린 것과 별개다.
        self._sync_steer_enabled()

    # ── 조그 (crab: 조향 → 정착 확인 → 구동 — 순서는 `TongyiCan` 이 지킨다) ──
    def _jog(self, label: str):
        """조그 버튼. 속도·허용치를 읽어 CAN 계층에 넘기고, 인터록만 여기서 본다."""
        if not self.can.running:
            self.log("조그 불가 — 제어권을 먼저 획득하세요")
            return
        if self.can.homing and label != "정지":
            self.log("호밍 진행 중 — 완료까지 기다리세요")
            return
        if label == "정지":
            self.can.stop_drive()
            self.log("정지 — 구동 0 (조향은 현 위치 유지)")
            return
        if self.can.jog_busy():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        steer_deg, raw_sign, _ = JOG[label]
        # 스핀박스는 위젯이라 GUI 스레드에서 읽어 값으로 넘긴다.
        self.can.start_jog(label, steer_deg, raw_sign,
                           float(self.spn_speed.value()), float(self.spn_tol.value()))

    # ── 조향 원점 복귀(호밍) ────────────────────────────────────────────
    def _homing_clicked(self):
        """호밍 버튼. 실제로 로봇이 크게 움직이므로 한 번 확인을 받는다."""
        if not self.can.running:
            self.log("호밍 불가 — 제어권을 먼저 획득하세요")
            return
        if self.can.homing:
            self.log("호밍 이미 진행 중")
            return
        if self.can.jog_busy():
            self.log("조그 진행 중 — 먼저 정지하세요")
            return
        if QMessageBox.question(
                self, "호밍 후 조향 0°",
                "조향 2축을 리밋까지 보내 원점을 확립한 뒤(호밍),\n"
                "이어서 조향 0° 를 지령합니다.\n\n"
                "· 바퀴가 두 번 크게 돕니다 — 리밋까지, 그리고 0° 로.\n"
                "  각각 100° 를 넘습니다.\n"
                "· 35 초 이상 걸립니다(호밍 약 31~34 s + 조향 0° 약 3 s).\n"
                "· 호밍은 시작한 뒤 이 프로그램이 멈출 수 없습니다\n"
                "  (드라이브 내부 루틴이라 중단은 하드웨어 E-STOP 뿐입니다).\n\n"
                "이동구역이 비어 있습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            self.log("호밍 취소")
            return
        self.btn_home.setEnabled(False)
        self.can.start_homing(float(self.spn_tol.value()))

    def _on_motor_data(self, data: dict):
        """폴링 결과 → 표 + 바퀴 그림 (GUI 스레드). 환산은 `TongyiCan.decode_frames`."""
        rows, angles_changed = self.can.decode_frames(data)
        for node, (deg, rpm, amp) in rows.items():
            self.set_motor_values(node, deg, rpm, amp)
            if deg is None and node in STEER_HOME and not self.can.meas_fresh(node):
                # 실측이 끊긴 구간은 직전 각도를 남겨 두지 않는다 — 멈춘 값을 현재값으로
                # 오해하게 만든다. 회전(rpm) 칸은 계속 살아 있어 움직임은 그쪽으로 보인다.
                self._set_angle_text(node, "탐색 중" if self.can.homing else "—")
        if angles_changed:
            self._redraw_wheel()

    def _set_angle_text(self, node: int, text: str):
        """모터 값 표의 각도 칸에 상태 문구를 직접 쓴다(숫자가 없는 구간용)."""
        row = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if row is not None:
            self.tbl_motor.item(row, 1).setText(text)


#: 정지 신호를 파이썬으로 되돌려받기 위한 keep-alive 주기(ms). §main 의 주석 참조.
SIGNAL_PUMP_MS = 50


def main() -> int:
    """GUI 를 띄우고, **어떤 경로로 죽어도 제어권·USB 가 풀리도록** 배선한 뒤 이벤트 루프를 돈다.

    해제 배선 4경로 — 전부 `MainWindow.safe_release()`(멱등)로 수렴한다:

    | 경로 | 배선 |
    | --- | --- |
    | 창 닫기·Alt+F4 | `closeEvent` |
    | Ctrl+C(SIGINT)·`kill`(SIGTERM) | `signal.signal` → `app.quit()` |
    | 이벤트 루프 정상 종료 | `app.exec_()` 반환 직후 |
    | 인터프리터 종료·미처리 예외 | `atexit` + `sys.excepthook` |

    **정지 신호 핸들러에서 USB 제어전송을 하지 않는다.** 핸들러는 임의 시점에 끼어들어 실행되므로
    그 안에서 `libusb` 호출·`sleep` 을 하면 재진입 위험이 있다. 핸들러는 `app.quit()` 로 루프만
    끝내고, 실제 해제는 루프를 빠져나온 정상 스택에서 수행한다.

    ⚠ **`pump` 타이머가 없으면 정지 신호가 아예 전달되지 않는다.** Qt 의 C++ 이벤트 루프가 도는
    동안에는 파이썬 바이트코드가 실행되지 않아 파이썬 신호 핸들러가 대기 상태로 남는다. 본 GUI 의
    모터 폴링은 **별도 스레드**라 메인 스레드에 파이썬 실행 기회를 주지 않으므로, 주기적으로
    인터프리터에 제어를 돌려주는 타이머가 반드시 필요하다.

    2026-07-28 실측(PyQt5, offscreen, 하드웨어 무관):

    | 조건 | SIGTERM 결과 |
    | --- | --- |
    | 파이썬 타이머 있음 | 0.036 s 내 핸들러 실행 → 해제 → exit 0 |
    | 타이머 없음 | **핸들러 미실행 · 프로세스 매달림 → SIGKILL(exit 137)** |

    Returns:
        프로세스 종료 코드(Qt 이벤트 루프 반환값).
    """
    app = QApplication(sys.argv)
    win = MainWindow()

    def _on_stop_signal(signum, _frame):
        # 핸들러 최소 작업: 로그 1줄 + 루프 종료 요청. 해제는 루프 밖에서.
        print(f"[gui] 정지 신호({signal.Signals(signum).name}) 수신 — 해제 후 종료합니다.",
              flush=True)
        app.quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _on_stop_signal)

    # 신호 전달용 pump — 참조를 유지해야 GC 되지 않는다.
    pump = QTimer()
    pump.timeout.connect(lambda: None)
    pump.start(SIGNAL_PUMP_MS)

    _default_excepthook = sys.excepthook

    def _excepthook(exc_type, exc, tb):
        try:
            win.safe_release("처리되지 않은 예외")
        finally:
            _default_excepthook(exc_type, exc, tb)

    sys.excepthook = _excepthook
    # 최후 그물 — 위 경로가 모두 빗나가도 인터프리터 종료 시 반드시 한 번은 돈다.
    atexit.register(win.safe_release, "인터프리터 종료")

    win.show()
    rc = app.exec_()
    win.safe_release("이벤트 루프 종료")
    return rc


if __name__ == "__main__":
    sys.exit(main())
