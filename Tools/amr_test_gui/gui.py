#!/usr/bin/env python3
"""Tongyi 4축 AMR 구동 테스트 GUI — 실기 전용.

지시에 따라 단계적으로 만든다.
현재: 3열 그룹박스. 왼쪽 = 연결(판다 목록·USB·제어권) + 로그.
"""
from __future__ import annotations

import atexit
import math
import os
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

# ── 상수 ───────────────────────────────────────────────────────────────────
# 값의 근거는 코드가 아니라 README.md §주요 상수 가 든다. 여기엔 의미만 적는다.
SEER_BUS, MOTOR_BUS = 0, 2          # 판다 버스 번호
SEER_GATE, CAN_KBPS = 30, 250       # safety_mode, 버스 속도
COUNTS_PER_DEG = 57344              # 조향 counts/도
# 조향 0° counts 의 **정본은 캘리브레이션 YAML 하나**이고 여기 값은 그 사본이다.
#   0° 는 Seer 각도로 역산한 값이다:  0° = CAN_0x6064 + Seer_deg × 57344
#   ⚠ 7882020 / 7859062 는 펌웨어 GOZERO 상수(호밍 후 정착 목표)이며 0° 가 아니다.
_STEER_HOME_FALLBACK = {3: 7871815, 4: 7840086}
_MACHINE_YAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "Comm", "CAN", "can_relay", "config", "machine", "foil_a082.yaml")


def _load_steer_home():
    """조향 0° counts 를 **정본 YAML 에서 읽는다**. 실패하면 사본으로 내려간다.

    사본이 정본과 어긋나면 조향이 통째로 어긋나므로 **읽어 오고, 어긋나면 시끄럽게 알린다.**

    반환 `(값, 출처 설명)`. 이 GUI 는 ROS 없이 단독 실행되므로 YAML 부재·PyYAML 부재는
    치명적이지 않다 — 사본으로 동작하되 그 사실을 남긴다.
    """
    try:
        import yaml
        with open(_MACHINE_YAML, encoding="utf-8") as fh:
            params = yaml.safe_load(fh)["/**"]["ros__parameters"]
        counts = [int(c) for c in params["steer_home_counts"]]
        nodes = [int(n) for n in params.get("steer_nodes", [3, 4])]
        home = dict(zip(nodes, counts))
        if home != _STEER_HOME_FALLBACK:
            return home, (f"정본 YAML (⚠ 코드 사본 {_STEER_HOME_FALLBACK} 와 다름 — "
                          f"정본을 따릅니다)")
        return home, "정본 YAML (코드 사본과 일치)"
    except Exception as exc:
        return dict(_STEER_HOME_FALLBACK), (
            f"⚠ 코드 사본 — 정본 YAML 을 읽지 못했습니다({type(exc).__name__}). "
            f"{_MACHINE_YAML}")


STEER_HOME, STEER_HOME_SOURCE = _load_steer_home()   # 조향 0° 기준 counts
SEER_IP = "192.168.44.82"
SEER_GUI = os.environ.get("SEER_GUI_PATH", "/home/nvidia/T-Robot_seer_gui")
#   ⚠ 절대경로 기본값은 이 PC 기준이다. 다른 계정·PC 에서는 `SEER_GUI_PATH` 로 덮는다 —
#   경로가 다르면 Seer 표·알람이 통째로 죽는다.
VEL_PER_MMPS, VEL_MAX_UNITS = 24.447, 4889   # 구동 raw 환산, 상한(≈0.2 m/s)
STEER_LIMIT_DEG = 90.0              # 조향 지령 허용 범위 ±90°
MEAS_TTL_S = 1.0                    # 이보다 오래된 실측은 없는 것으로 친다
STEER_NODES = (3, 4)                # 조향축(전/후). 구동축은 (1, 2)
DRIVE_NODES = (1, 2)                # 구동축

# CiA402 상태기계 — Handbook §6.6.1 Controlword(0x6040) 명령표
#   Bit0 Switch on · Bit1 Enable voltage · Bit2 Quick stop · Bit3 Enable Operation · Bit7 Fault Reset
CW_FAULT_RESET = 0x80               # bit7 **상승엣지**로 fault 를 지운다
DRIVE_ENABLE_SEQ = (0x06, 0x07, 0x0F)   # Shutdown → Switch On → Enable Operation
SW_OPERATION_ENABLED = 1 << 2       # 상태워드 bit2 — 0 이면 0x60FF 를 받아도 안 움직인다
SW_FAULT = 1 << 3                   # 상태워드 bit3
SEER_MATCH_TOL_DEG = 3.0            # CAN 실측 ↔ Seer 판독 허용 차(정착 허용치와 같은 스케일)
SEER_MATCH_STREAK = 5               # 이만큼 **연속** 어긋나야 경보 — 과도 표본으로 떠들지 않는다
SEER_MATCH_REWARN_S = 30.0          # 같은 축 재경보 최소 간격
SEER_RESTORE_TIMEOUT_S = 20.0       # 반환 전 조향 복원 대기 한도
RX_TTL_S = 1.0                      # 이보다 오래 응답이 없으면 버스가 죽은 것으로 보고 구동을 0 으로
#   폴링(≈0.2 s 주기)이 5회 연속 빠지면 만료다. 폴링 스레드가 죽어도 마지막 값이
#   남아 정착 판정을 통과시키는 것을 막는다.

# SDO abort 코드 — 드라이브가 쓰기를 거부한 사유. 진단 전용이며 동작에 관여하지 않는다.
_ABORT = {
    0x05040001: "명령 지정자 불량",
    0x06010002: "읽기 전용 객체에 쓰기",
    0x06020000: "객체 없음",
    0x06090011: "서브인덱스 없음",
    0x06090030: "값 범위 초과",
    0x06070010: "데이터 길이 불일치",
    0x08000020: "저장 불가",
    0x08000022: "현재 장치 상태에서 전송 불가",
}


# ── 순수 환산 (Qt·하드웨어 무의존 — 회귀 테스트가 여기를 고정한다) ──────────
def steer_counts(node: int, deg: float):
    """가동범위 클램프 후 조향 절대위치 counts 를 낸다. 반환 `(적용된 각도, counts)`.

    범위 밖 각도는 보내지 않고 ±90° 로 자른다.
    """
    deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
    return deg, int(round(STEER_HOME[node] + deg * COUNTS_PER_DEG))


def drive_units(mmps: float, raw_sign: int) -> int:
    """구동 속도 지령 raw(0x60FF) 환산 + 상한 클램프."""
    return max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS,
                                   int(round(raw_sign * mmps * VEL_PER_MMPS))))


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
    "좌전 45°": (-45.0, -1, True),  # 도출
    "우전 45°": (45.0,  -1, True),  # 도출
    "좌후 45°": (45.0,  +1, True),  # 도출
    "우후 45°": (-45.0, +1, True),  # 도출
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
        self._draw_arrow(p, ctr, ax, ay, L * 0.72)
        p.setPen(QPen(QColor("#22303c"), 1))
        p.setBrush(Qt.NoBrush)
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
    poll_died = pyqtSignal()        # 폴링 스레드 사망 — UI 상태를 되돌린다

    def __init__(self):
        super().__init__()
        self.panda = None
        self._th = None
        self._run = False
        self._seer_run = True
        # 해제 사슬을 이미 돌렸는지. 종료 경로가 4개(창 닫기·정지 신호·이벤트루프 종료·
        # 인터프리터 종료)라 같은 사슬이 여러 번 불린다 — `safe_release()` 멱등화 래치.
        self._released = False
        self._alarm_tick = 0
        self._alarm_seen = set()
        self._can_lock = threading.RLock()  # 폴링·조그가 버스를 공유한다
        #   RLock 인 이유: 「정지 여부 확인 → 구동 송신」을 한 임계구역에 넣어야 하는데
        #   그 안에서 `_drive()` → `_sdo_write()` 가 같은 락을 다시 잡는다.
        self._jog_th = None
        self._jog_stop = False
        self._meas_deg = {3: None, 4: None}
        self._meas_at = {}              # node -> 그 각도를 받은 시각(monotonic). 신선도 판정용
        self._seer_at_take: dict = {}   # 제어권 잡기 직전 Seer 조향각(반환 시 복원 기준)
        self._steer_commanded = False   # 이번 제어권 세션에서 조향을 보냈는가(대조 중단 조건)
        self._seer_mismatch_streak: dict = {}     # 축별 연속 불일치 횟수
        self._seer_mismatch_warned_at: dict = {}  # 축별 마지막 경보 시각(재경보 억제)
        self._drive_units = 0           # 마지막 구동 지령(raw). 폴 루프가 이 값을 재송신한다
        self._rx_at = 0.0               # 마지막으로 드라이브 응답을 받은 시각
        self._status = {}               # node -> 0x6041 상태워드 (호밍 완료 판정용)
        self._homing = False
        self._aborts = set()   # 이미 보고한 SDO 거부(같은 것 반복 방지)
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
        self.log_line.connect(self._append_log)
        self.homing_done.connect(lambda: self.btn_home.setEnabled(True))
        self.enable_done.connect(lambda: self.btn_enable.setEnabled(True))
        self.poll_died.connect(self._on_poll_died)
        threading.Thread(target=self._seer_loop, daemon=True, name='seer').start()
        self.log("GUI 기동 — 실기 전용")
        self.log(f"조향 0° 기준 {STEER_HOME} · 출처: {STEER_HOME_SOURCE}")
        self.scan()

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
        """로봇 조그 — 3×3 방향 패드.

        방향 구성: 4방위 = 직진·후진·좌크랩·우크랩, 대각선 = 45° 크랩.
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

        # 조향 원점 복귀. 방향 패드와 성격이 달라(준비 동작·큰 이동) 줄을 나눈다.
        self.btn_home = QPushButton("⌂  조향 원점 복귀 (호밍)")
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
        if not self._run:
            self.log("구동축 활성화 불가 — 제어권을 먼저 획득하세요")
            return
        ready, faults = self._drives_ready(), self._drive_faults()
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
            self._enable_drives()
        finally:
            self.enable_done.emit()

    def _build_wheel_adj(self) -> QGroupBox:
        """앞뒤 바퀴 조향각 조정.

        여기 값은 **목표**다. 그림은 실측(판다 또는 Seer)이 있으면 그쪽을 그리고,
        실측이 하나도 없을 때만 이 값을 미리보기로 그린다 (`gui.py:637` `_redraw_wheel`).
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
            sld.valueChanged.connect(lambda _val, n=node: self._on_wheel_changed(n))
            sld.sliderReleased.connect(lambda n=node: self._send_steer(n))
            v.addWidget(sld)
            v.addSpacing(4)
        return g

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
        if not self._run:
            self.log("조향 지령 불가 — 제어권을 먼저 획득하세요")
            return
        deg = (self.sld_front if node == 3 else self.sld_rear).value()
        sent = self._steer_axis(node, float(deg))
        self.log(f"조향 지령 N{node} → {sent:+.0f}°")

    def _steer_axis(self, node: int, deg: float) -> float:
        """한 축에만 절대위치 지령(0x607A) + 즉시 적용(0x6040=0x3F). 환산은 `steer_counts`."""
        deg, counts = steer_counts(node, deg)
        self._steer_commanded = True          # 이 시점부터 Seer 판독은 굳는다(대조 중단)
        self._sdo_write(node, 0x607A, counts, 4)
        self._sdo_write(node, 0x6040, 0x3F, 2)
        return deg

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
        """노드 행에 (각도, 회전, 전류) 를 써 넣는다. `None` 인 칸은 `—` 로 **덮어쓴다**.

        값이 없을 때 칸을 그대로 두면 직전 숫자가 화면에 남아, 폴링이 끊겼거나 호밍 중이라
        위치를 모르는 상황을 「그 값이 현재 값」으로 읽게 된다.
        """
        r = {1: 0, 2: 1, 3: 2, 4: 3}.get(node)
        if r is None:
            return
        for (c, fmt), val in zip(cls.CELL_FMT, values):
            table.item(r, c).setText("—" if val is None else fmt.format(val))

    def _build_motors(self) -> QGroupBox:
        """각 모터 값 — 각도·회전·전류만.

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
                if not self._seer_run:      # 대기 중 종료됐으면 위젯을 건드리지 않는다
                    return
                self.seer_data.emit({int(m["can_id"]): m for m in ms if m.get("can_id")})
                self.seer_status.emit(
                    f"Seer {SEER_IP} · 연결됨 · 모터 {len(ms)}축 · 갱신 {time.strftime('%H:%M:%S')}",
                    True)
            except RuntimeError:
                # 창이 이미 파괴됐다(종료 경로). 더 emit 하면 역추적만 남으므로 조용히 끝낸다.
                return
            except Exception as exc:       # 일시 실패는 상태 바에만 (제어 경로 아님)
                if not self._seer_run:
                    return
                try:
                    self.seer_status.emit(f"Seer {SEER_IP} · 폴링 실패 ({type(exc).__name__})",
                                          False)
                except RuntimeError:
                    return

            # 알람(1050)은 4 주기(=약 2 s)에 한 번. **신규만** 로그에 남긴다 —
            # Seer 는 해제되지 않은 오래된 항목도 계속 목록에 들고 있어서
            # 전량을 매번 찍으면 방금 난 것처럼 보인다.
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
                except RuntimeError:
                    return
                except Exception:
                    pass
            time.sleep(0.5)

    def _on_seer_data(self, data: dict):
        for node, m in data.items():
            pos = m.get("position")
            deg = None if pos is None else pos * 180.0 / math.pi
            self._fill_row(self.tbl_seer, node, (deg, m.get("speed"), m.get("current")))
            if node in (3, 4) and deg is not None:
                # ⚠ **우리 규약(CAN)으로 정규화해 담는다.** Seer 각도와 CAN counts 는
                #   **음의 상관**이다 — 정본 `config/machine/foil_a082.yaml` 의 0° 역산식
                #   `0° = CAN_0x6064 + Seer_deg x 57344` 가 그 뜻이고,
                #   Seer 원값을 그대로 담으면 제어권을 잡고 놓을 때마다 `_meas_angle` 의
                #   부호가 뒤집힌다(바퀴 그림·실측 라벨이 함께 뒤집힌다).
                #   ⚠ Seer **표**(`tbl_seer`)는 Seer 가 보고한 값을 그대로 보여야 하므로
                #     정규화하지 않는다 — 여기서만 바꾼다.
                self._seer_deg[node] = -deg
        self._redraw_wheel()

    def _set_meas(self, node: int, deg: float):
        """실측 각도 1건 반영 — **값과 시각을 함께** 남긴다.

        기록 지점을 하나로 두는 이유: 값만 넣고 시각을 빠뜨리면 그 값은 영원히 신선해 보이거나
        (시각 미갱신) 영원히 만료돼 보인다. 둘을 따로 쓸 수 있게 두면 언젠가 그렇게 된다.
        """
        self._meas_deg[node] = deg
        self._meas_at[node] = time.monotonic()
        if node in STEER_NODES:
            self._check_seer_agreement(node, deg)

    def _meas_angle(self, node: int):
        """그 축의 실측 조향각. 제어권이 있으면 판다 직독, 없으면 Seer. 없으면 None.

        **판다 직독 값은 `MEAS_TTL_S` 밖이면 없는 것으로 친다.**
        폴링 스레드가 죽으면 `_loop` 이 `self._run = False` 로 조용히 끝나고(`gui.py` §폴링)
        마지막 값이 `_meas_deg` 에 그대로 남는다. 그 값을 정착 판정에 쓰면 **멈춘 화면을 보고
        바퀴가 그 각도라고 믿은 채 구동에 들어간다.** 신선도가 그것을 막는 유일한 장치다.

        (Seer 값은 폴링 실패 시 `_on_seer_status` 가 `_seer_deg` 를 비우므로 별도 TTL 을 두지
        않는다 — 끊기면 값 자체가 사라진다.)
        """
        if not self._run:
            return self._seer_deg.get(node)
        deg = self._meas_deg.get(node)
        if deg is None:
            return None
        at = self._meas_at.get(node)
        if at is None or (time.monotonic() - at) > MEAS_TTL_S:
            return None
        return deg

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
            lab.setText(f"{sld.value():+d}°" +
                        ("" if meas is None else f"  (실측 {meas:+.1f}°)"))

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
        """어느 스레드에서 불러도 안전한 로그 — **항상 시그널을 거친다.**

        예전에는 GUI 스레드는 `log()`, 작업 스레드는 `log_line.emit()` 로 호출부가 매번
        골라야 했고, 잘못 고르면 스레드 위반이 됐다. 이제 고를 일이 없다.
        위젯을 실제로 만지는 것은 슬롯 `_append_log` 하나뿐이다.
        """
        self.log_line.emit(msg)

    def _append_log(self, msg: str):
        """로그 위젯을 만지는 **유일한 지점**(GUI 스레드 슬롯)."""
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        self.txt_log.appendPlainText(line)
        print(f"[gui] {line}", flush=True)      # 창 밖(로그 파일)에서도 보이도록

    def scan(self):
        """연결 가능한 판다 열거 — USB 를 열지 않는다(목록만).

        **1 PC = 판다 1대**가 원칙이므로 고르는 UI 를 두지 않는다. 2대 이상 검출되면
        원칙 위반이라 경고만 하고, 실제로 열리는 것은 라이브러리가 먼저 찾은 1대다.
        """
        try:
            serials = _panda_class().list()
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
            # **차단한다.** 예전에는 경고만 하고 USB 버튼을 열어 줬는데, 그러면 어느 로봇에
            # 지령이 갈지 모르는 채로 진행할 수 있었다.
            self.lab_panda.setText(f"⚠ {len(serials)}대 검출 — 진행 불가")
            self.log(f"⚠ 판다 {len(serials)}대 검출({', '.join(serials)}) — 1 PC 1대 원칙 위반. "
                     f"어느 장치에 지령이 갈지 알 수 없으므로 **USB 연결을 막습니다.** "
                     f"한 대만 남기고 다시 검색하세요.")
            self.btn_usb.setEnabled(False)
            return
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
                # ── 인수인계 ① : **잡기 직전 Seer 가 보던 조향각을 기억한다.**
                #   반환할 때 이 값으로 되돌려 놓고 넘긴다(아래 ②). 그냥 넘기면 Seer 가
                #   자기 판단으로 조향을 크게 움직인다.
                #   (사용자 운영 철학: 「제어권을 가지기 전에 seer 의 조향각을 읽어야 하고
                #    반환할 때도 seer 의 값을 주고 반환해야 한다」)
                self._steer_commanded = False   # 새 세션 — 대조를 다시 연다
                self._seer_at_take = {n: self._seer_deg.get(n) for n in STEER_NODES}
                have = {n: v for n, v in self._seer_at_take.items() if v is not None}
                self.log(f"인수인계 기준(Seer) — " +
                         (", ".join(f"N{n} {v:+.2f}°" for n, v in have.items()) if have
                          else "⚠ Seer 각도 없음 — 반환 시 복원할 기준이 없습니다"))
                self.log("제어권 획득 완료 — 모터 값 폴링 시작")
                self._ensure_drives_enabled()
            else:
                self._jog_stop = True
                try:
                    self._drive(0)          # 반환 전 반드시 정지
                except Exception as exc:
                    # 삼키지 않는다 — 정지 프레임이 못 나간 채 auth·intercept 를 내리면
                    # 드라이브가 **마지막 속도를 문 채** Seer 로 넘어간다.
                    self.log(f"⚠ 제어권 반환 전 정지 송신 실패 — "
                             f"{type(exc).__name__}: {exc}. 드라이브가 마지막 지령을 "
                             f"유지할 수 있습니다. 하드웨어 E-STOP 을 확인하세요.")
                # ── 인수인계 ② : **잡기 직전 Seer 값으로 조향을 되돌린 뒤** 넘긴다.
                #   폴링을 아직 끄지 않은 상태에서 해야 실측으로 정착을 확인할 수 있다.
                self._restore_steer_for_handover()
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


    # ── 인수인계 (Seer ↔ 우리) ─────────────────────────────────────────
    def _check_seer_agreement(self, node: int, deg: float):
        """CAN 실측과 Seer 판독이 같은 곳을 가리키는가 — **매 표본 연속 대조**한다.

        한 번만 보고 판정하지 않는다 — 획득 직후 첫 표본은 조향 지령 없이도 크게 튈 수 있어
        거짓 경보가 난다. 과도 표본은 `SEER_MATCH_STREAK` 연속 조건이 걸러 낸다.

        ⚠ **우리가 조향을 보낸 뒤에는 대조하지 않는다.** 제어권을 쥐면 Seer 는 버스에서
        끊겨 모터 실측을 더 못 본다 — 우리가 축을 움직이는 동안 Seer 판독은 **고정**돼
        있다가 반환한 뒤에야 다시 따라온다. 정지 상태의 값 일치는 유효성의 근거가 되지
        못한다 — 바퀴가 안 움직이면 「따라오는 것」과 「값이 굳은 것」이 구분되지 않는다.
        따라서 유효한 구간은 **획득 직후 ~ 첫 조향 지령 전**뿐이다.

        어긋나면 **알리기만 한다**(막지 않는다). 조향 0° 기준이 서로 다르다는 뜻이므로
        판단은 운용자 몫이고, 조용히 진행하는 것만 피한다.
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
                self.log_line.emit(
                    f"N{node} 조향 기준 회복 — Seer {ref:+.2f}° ↔ CAN {deg:+.2f}°")
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

    def _restore_steer_for_handover(self):
        """반환 직전, 조향을 **잡기 직전 Seer 값**으로 되돌린다.

        되돌리지 않고 넘기면 Seer 가 자기 판단으로 조향을 크게 움직인다.
        기준이 없거나 실측이 신선하지 않으면 **움직이지 않고** 알린다.
        """
        targets = {n: v for n, v in getattr(self, "_seer_at_take", {}).items() if v is not None}
        if not targets:
            self.log("⚠ 인수인계 복원 생략 — 잡기 직전 Seer 각도가 없습니다")
            return
        if any(self._meas_angle(n) is None for n in targets):
            self.log("⚠ 인수인계 복원 생략 — 조향 실측이 신선하지 않습니다(움직이지 않음)")
            return
        self.log("인수인계 복원 — " +
                 ", ".join(f"N{n} → {v:+.2f}°" for n, v in targets.items()))
        try:
            for n, v in targets.items():
                self._steer_axis(n, v)
        except Exception as exc:
            self.log(f"⚠ 인수인계 복원 지령 실패: {type(exc).__name__}: {exc}")
            return
        t0 = time.monotonic()
        while time.monotonic() - t0 < SEER_RESTORE_TIMEOUT_S:
            QApplication.processEvents()             # 반환 중에도 화면이 멈추지 않게
            cur = {n: self._meas_angle(n) for n in targets}
            if all(c is not None and abs(c - targets[n]) <= 1.0 for n, c in cur.items()):
                self.log(f"인수인계 복원 완료 ({time.monotonic() - t0:.1f}s)")
                return
            time.sleep(0.05)
        cur = {n: self._meas_angle(n) for n in targets}
        self.log(f"⚠ 인수인계 복원 미완료 ({SEER_RESTORE_TIMEOUT_S:.0f}s 초과) — 현재 {cur}. "
                 f"그대로 반환합니다")

    # ── 조그 실행 (crab: 조향 → 정착 확인 → 구동) ──────────────────────
    def _sdo_write(self, node: int, idx: int, val: int, size: int, sub: int = 0):
        """SDO expedited 쓰기. 폴링 스레드와 버스를 공유하므로 락으로 직렬화한다.

        `sub` 는 서브인덱스 — 호밍 트리거 `0x60FB:04` 처럼 0 이 아닌 것이 있다.
        """
        if self.panda is None:
            # 진입부 가드 — 없으면 상위 `except` 가 AttributeError 를 「조그 중단」으로
            # 뭉뚱그려 사유가 부정확해진다.
            raise RuntimeError("판다 미연결 — USB 를 먼저 연결하세요")
        cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
        payload = (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
        data = bytes([cmd, idx & 0xFF, idx >> 8, sub]) + payload + b"\x00" * (4 - size)
        with self._can_lock:
            self.panda.can_send(0x600 + node, data[:8], MOTOR_BUS)

    def _drive(self, units: int):
        """구동 노드에 속도 지령(0x60FF). units=0 이면 정지.

        지령을 **상태로 남긴다** — 폴 루프가 매 주기 같은 값을 재송신한다. 예전에는 여기서
        한 번 보내고 끝이라 프레임 하나가 유실되면 그대로 끝이었다.
        """
        units = int(units)
        self._drive_units = units
        for n in (1, 2):
            self._sdo_write(n, 0x60FF, units, 4)

    # ── 구동축 운전 상태 (CiA402) ────────────────────────────────────────
    FAULT_CLEAR_S = 2.0        # fault 가 걷히기를 기다리는 창

    def _drives_ready(self) -> dict:
        """구동축이 **운전 가능**(상태워드 bit2)인가. 반환 `{node: True/False/None}`.

        `None` 은 상태워드를 아직 못 받은 것이다. bit2 가 0 이면 `0x60FF` 를 아무리 보내도
        바퀴가 돌지 않는다 — 재송신도 소용없다(지령을 반복할 뿐 상태를 켜지 못한다).
        """
        return {n: (None if self._status.get(n) is None
                    else bool(self._status[n] & SW_OPERATION_ENABLED))
                for n in DRIVE_NODES}

    def _drive_faults(self) -> dict:
        """구동축 fault(상태워드 bit3) 여부. 반환 `{node: True/False/None}`."""
        return {n: (None if self._status.get(n) is None
                    else bool(self._status[n] & SW_FAULT))
                for n in DRIVE_NODES}

    def _enable_drives(self, timeout: float = 3.0) -> bool:
        """구동축을 운전 가능 상태로 만든다 — Handbook §6.6.1 상태기계.

        fault 가 서 있으면 **Fault Reset**(bit7 0→1 상승엣지)을 먼저 보내고, **fault 가
        걷힌 것을 확인한 뒤** Shutdown(0x06) → Switch On(0x07) → Enable Operation(0x0F).
        대기 없이 몰아 보내면 드라이브가 아직 Fault 에 있어 무시하고 `Switch On Disabled`
        (0x8050)에서 멈춘다.

        ⚠ **fault 의 원인을 제거하지 않으면 곧 재발한다.** 그 사례는 node1
        `0x603F=0x0080` Motor overload alarm 이었고 Handbook §6.6.4 는 "부하가 정격을
        넘는지 확인" 을 먼저 요구한다. 이 함수는 상태만 되돌린다.
        """
        faulted = [n for n in DRIVE_NODES
                   if self._status.get(n) is not None and (self._status[n] & SW_FAULT)]
        for n in faulted:
            self._sdo_write(n, 0x6040, 0x00, 2)              # bit7 를 내려 엣지를 만든다
            self._sdo_write(n, 0x6040, CW_FAULT_RESET, 2)    # Fault Reset
            self._sdo_write(n, 0x6040, 0x00, 2)
            self.log_line.emit(f"구동축 N{n} fault 해제 시도")
        if faulted:
            t_f = time.time()
            while time.time() - t_f < self.FAULT_CLEAR_S:
                if not any(self._status.get(n, 0) & SW_FAULT for n in faulted):
                    break
                time.sleep(0.05)
            still = [n for n in faulted if self._status.get(n, 0) & SW_FAULT]
            if still:
                self.log_line.emit(f"⚠ 구동축 {still} fault 가 걷히지 않습니다 — "
                                   "원인 제거가 먼저입니다.")
                return False
        for cw in DRIVE_ENABLE_SEQ:
            for n in DRIVE_NODES:
                self._sdo_write(n, 0x6040, cw, 2)
            time.sleep(0.05)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if all(v for v in self._drives_ready().values()):
                self.log_line.emit("구동축 운전 가능 — 양축 operation enabled")
                return True
            time.sleep(0.05)
        bad = [n for n, v in self._drives_ready().items() if not v]
        self.log_line.emit(f"⚠ 구동축 활성화 실패 — 노드 {bad} 가 운전 가능 상태가 아닙니다. "
                           f"fault {self._drive_faults()}")
        return False

    def _ensure_drives_enabled(self, delay: float = 0.8) -> None:
        """제어권 획득 직후 구동축 운전 상태를 확인하고, **fault 가 없으면** 되살린다.

        Seer 에게 제어권을 넘겼다 되찾으면 구동축이 `Switch On Disabled` 로 떨어져 있을 수
        있다. 그 상태로 조그하면 조향만 되고 구동이 취소된다. 제어권을 잡는 쪽이 필요한
        상태를 갖추는 것이 책임 분담이므로 여기서 갖춘다.

        **fault 가 서 있으면 자동으로 켜지 않는다** — 원인을 모른 채 재기동하면 과부하 등이
        재발하거나 모터를 상하게 한다. 그때는 운전자가 `구동축 활성화` 버튼으로 확인을 거친다.
        """
        def work():
            time.sleep(delay)                    # 상태워드가 한 번 들어올 틈
            ready, faults = self._drives_ready(), self._drive_faults()
            if all(v for v in ready.values()):
                return
            if any(faults.values()):
                self.log_line.emit(f"⚠ 구동축 fault {faults} — 자동 활성화하지 않습니다. "
                                   f"원인 확인 후 '구동축 활성화' 를 누르세요.")
                return
            self.log_line.emit(f"구동축이 운전 가능 상태가 아닙니다 {ready} — 자동 활성화합니다.")
            self._enable_drives()

        threading.Thread(target=work, daemon=True, name="ensure-enable").start()

    def _steer_to(self, deg: float) -> float:
        """조향 두 축에 절대위치 지령(0x607A) + 즉시 적용(0x6040=0x3F).

        범위 밖 각도는 보내지 않고 ±90° 로 자른다(`steer_counts`).
        **단계로 쪼개지 않는다** — 최종 절대 목표를 그대로 보내고 이동 프로파일은
        드라이브가 수행한다. 근거는 README.md §동작 규칙.
        """
        for n in (3, 4):
            deg = self._steer_axis(n, deg)
        return deg

    def _jog(self, label: str):
        """조그 버튼. crab 이므로 **바퀴를 먼저 돌리고 정착을 확인한 뒤** 주행한다."""
        if not self._run:
            self.log("조그 불가 — 제어권을 먼저 획득하세요")
            return
        if self._homing and label != "정지":
            self.log("호밍 진행 중 — 완료까지 기다리세요")
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
                self.log_line.emit(f"조향 정착 실패(실측 N3 {self._meas_angle(3)} / "
                                   f"N4 {self._meas_angle(4)}) — 구동 취소")
                self._drive(0)
                return
            ready = self._drives_ready()
            if not all(v for v in ready.values()):
                # 이 확인이 없으면 지령만 나가고 바퀴는 가만히 있어 원인을 알 수 없다.
                # 재송신도 소용없다 — 지령을 반복할 뿐 꺼진 축을 켜지 못한다.
                self.log_line.emit(
                    f"⚠ 구동 취소 — 구동축이 운전 가능 상태가 아닙니다 "
                    f"(operation enabled {ready}, fault {self._drive_faults()}). "
                    f"'구동축 활성화' 를 먼저 누르세요.")
                self._drive(0)
                return
            units = drive_units(mmps, raw_sign)
            # 확인과 송신을 **한 임계구역**에 넣는다 — 예전에는 확인 직후 정지 버튼이 눌리면
            # 정지(0)가 먼저 나가고 구동이 뒤에 나갔다. 정지 경로도 같은 락을
            # 지나므로(`_drive` → `_sdo_write`) 이 안에서는 끼어들 수 없다.
            with self._can_lock:
                if self._jog_stop:
                    units = 0
                self._drive(units)
            if units == 0:
                self.log_line.emit("정지 요청이 먼저 들어와 구동을 내보내지 않았습니다")
                return
            self.log_line.emit(f"조향 정착 — 구동 raw={units:+d} ({mmps:.0f} mm/s)")
        except Exception as exc:
            self.log_line.emit(f"조그 중단: {type(exc).__name__}: {exc}")
            try:
                self._drive(0)
            except Exception:
                pass

    # ── 조향 원점 복귀(호밍) ────────────────────────────────────────────
    HOMING_SPEED = 2500        # 0x6099:00, 0.1 r/min 단위 → 250 r/min
    HOMING_TIMEOUT_S = 90.0    # 실측 소요 약 31 s
    HOMING_START_S = 10.0      # 개시(bit15=0) 를 기다리는 창

    def _homing_clicked(self):
        """호밍 버튼. 실제로 로봇이 크게 움직이므로 한 번 확인을 받는다."""
        if not self._run:
            self.log("호밍 불가 — 제어권을 먼저 획득하세요")
            return
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
                "· 이 프로그램에는 취소 버튼이 없습니다 — 중단하려면 하드웨어 E-STOP 을 쓰십시오.\n"
                "  (취소 자체는 가능하나 이 GUI 에 미구현입니다)\n\n"
                "이동구역이 비어 있습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            self.log("호밍 취소")
            return
        self._homing = True
        self.btn_home.setEnabled(False)
        threading.Thread(target=self._homing_run, name="homing", daemon=True).start()

    def _homing_run(self):
        """조향 노드 3·4 호밍.

        구동 노드(1·2)는 기계적 원점이 없어 호밍하지 않는다 — 조향축에만 지령한다.
        `0x6098`(homing method)은 **쓰지 않는다**. 드라이브 저장값을 그대로 쓰며,
        덮어쓰면 리셋 모드가 꺼져 호밍 자체가 동작하지 않는다.
        """
        try:
            self._drive(0)                       # 호밍 전 구동은 반드시 0
            self._status.clear()                 # 직전 상태워드를 완료로 오독하지 않도록
            for n in (3, 4):
                self._sdo_write(n, 0x6040, 0x86, 2)                 # 축 준비
                self._sdo_write(n, 0x6099, self.HOMING_SPEED, 4)    # 호밍 속도
                self._sdo_write(n, 0x60FB, 1, 1, sub=4)             # 여기서 움직이기 시작한다
            self.log_line.emit("호밍 개시 — 조향 2축. 완료까지 30초 이상 걸립니다.")
            ok, why = self._wait_homed()
            self.log_line.emit(f"호밍 완료 — {why}" if ok else f"호밍 미확인 — {why}")
        except Exception as exc:
            self.log_line.emit(f"호밍 중단: {type(exc).__name__}: {exc}")
        finally:
            self._homing = False
            self.homing_done.emit()

    def _wait_homed(self):
        """상태워드(0x6041) bit15 로 완료를 판정한다. 반환 `(성공, 사유)`.

        **bit15 가 1 인 것만 보면 안 된다** — 이전에 호밍을 마친 축은 시작 전부터 1 이라
        곧바로 "완료"로 읽힌다. 그래서 먼저 두 축이 0(진행 중)이 되는 것을 확인하고,
        그 다음에 1 로 돌아오는 것을 기다린다. 0 을 한 번도 못 보면 성공이라고 하지 않는다.
        """
        BIT15 = 1 << 15
        t0 = time.time()
        started = set()
        while time.time() - t0 < self.HOMING_START_S:
            for n in (3, 4):
                st = self._status.get(n)
                if st is not None and not (st & BIT15):
                    started.add(n)
            if started >= {3, 4}:
                break
            time.sleep(0.1)
        if started < {3, 4}:
            missing = sorted({3, 4} - started)
            return False, (f"개시 신호(bit15=0)를 못 봤습니다 — 노드 {missing}. "
                           f"움직이지 않았는지 육안으로 확인하세요.")
        while time.time() - t0 < self.HOMING_TIMEOUT_S:
            if all((self._status.get(n) or 0) & BIT15 for n in (3, 4)):
                return True, f"{time.time() - t0:.0f}초 소요. 조향 0° 복귀까지 확인하세요."
            time.sleep(0.1)
        return False, f"{self.HOMING_TIMEOUT_S:.0f}초 안에 완료 신호가 오지 않았습니다."

    def _wait_settle(self, target: float, tol: float, timeout: float = 6.0) -> bool:
        """조향 정착 대기 — **두 축(N3·N4) 모두** 허용치 안에 들어와야 한다.

        crab 은 앞뒤가 같은 각이어야 성립하므로 한 축만 확인하면 뒷바퀴가 어긋난 채
        구동에 들어간다. 시간 초과면 False(= 추종 실패, 호출부가 구동을 취소한다).
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._jog_stop:
                return False
            cur = [self._meas_angle(n) for n in (3, 4)]   # ← 신선도 통과분만
            if all(c is not None and abs(target - c) <= tol for c in cur):
                return True
            time.sleep(0.05)
        return False

    # ── 폴링 (모터 값 읽기 전용 — 지령은 보내지 않는다) ────────────────
    def _loop(self):
        """0x6064(위치)·0x606C(속도)·0x6078(전류)·0x6041(상태워드)를 읽어 화면에 올린다.

        0x6041 은 화면에 띄우지 않고 호밍 완료 판정(bit15)에만 쓴다.

        ⚠ 0x607A(위치지령)는 보내지 않는다. **0x60FF(구동)는 재송신한다** —
          마지막 지령을 매 주기 다시 내보내 프레임 유실에 견딘다(High ③).
        """
        P = _panda_class()
        while self._run:
            try:
                # heartbeat(0xf3) 를 매 루프(≈0.2 s) 보낸다.
                # 끊기면 펌웨어가 fail-safe 로 intercept 를 푼다(임계는 초 단위).
                #
                # ⚠ **락 안에서 보낸다.** 예전에는 이 줄이 `with self._can_lock:` 밖이라,
                #   조그·호밍 스레드가 락을 쥐고 `can_send` 하는 동안 폴링 스레드가 같은 USB
                #   핸들에 심박을 낼 수 있었다. 심박이 실패하면 펌웨어 fail-safe 가 걸려
                #   **주행 중 예고 없이 정지**한다.
                with self._can_lock:
                    self.panda._handle.controlWrite(P.REQUEST_OUT, 0xf3, 0, 0, b"")
                    for n in (1, 2, 3, 4):
                        for idx in (0x6064, 0x606C, 0x6078, 0x6041):
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
                    if dat[0] == 0x43:                       # 4 바이트 읽기 응답
                        val = int.from_bytes(dat[4:8], "little", signed=True)
                    elif dat[0] == 0x4B:                     # 2 바이트 읽기 응답
                        val = int.from_bytes(dat[4:6], "little", signed=True)
                    elif dat[0] == 0x80:                     # SDO abort — 드라이브가 거부했다
                        code = int.from_bytes(dat[4:8], "little")
                        key = (node, idx, dat[3], code)
                        if key not in self._aborts:          # 같은 거부는 1회만 (버스가 반복한다)
                            self._aborts.add(key)
                            self.log_line.emit(
                                f"SDO 거부 N{node} 0x{idx:04X}:{dat[3]:02X} "
                                f"→ abort 0x{code:08X} ({_ABORT.get(code, '사유 미상')})")
                        continue
                    else:
                        continue
                    out.setdefault(node, {})[idx] = val
                if out:
                    self._rx_at = time.monotonic()
                    self.motor_data.emit(out)

                # ── 구동 재송신 + 피드백 워치독 ──
                # 재송신: 프레임 1장 유실이 곧 지령 소실이던 것을 막는다. 0 도 재송신한다 —
                #         정지야말로 유실되면 안 되기 때문이다.
                # 워치독: 응답이 RX_TTL_S 넘게 없으면 **버스 상태를 모르는 것**이므로 0 으로 간다.
                #         ⚠ 「지령 만료」 방식(상류가 주기 발행하지 않으면 정지)은 여기 쓰지 않는다 —
                #         이 GUI 는 지령원이 사람이라 조그가 스스로 멈춰 버린다.
                if self._rx_at and (time.monotonic() - self._rx_at) > RX_TTL_S \
                        and self._drive_units != 0:
                    self.log_line.emit(
                        f"워치독 — {RX_TTL_S:.0f}초 넘게 드라이브 응답이 없어 구동을 0 으로")
                    self._drive(0)
                else:
                    for n in (1, 2):
                        self._sdo_write(n, 0x60FF, self._drive_units, 4)
            except Exception as exc:
                self._run = False
                # 표시와 동작이 어긋나지 않게 한다 — 예전에는 폴링이 죽어도 버튼이
                # 「제어권 획득」 상태로 남아 조작이 되는 것처럼 보였다.
                self.log_line.emit(
                    f"⚠ 폴링 중단: {type(exc).__name__}: {exc} — 실측이 더 이상 갱신되지 "
                    f"않습니다. 제어권을 해제하고 다시 획득하세요.")
                self.poll_died.emit()
                return
            time.sleep(0.12)

    def _on_poll_died(self):
        """폴링이 죽었으면 **제어권 표시를 내린다** — 화면이 사실과 달라지지 않게."""
        if self.btn_take.isChecked():
            self.btn_take.setChecked(False)      # `_on_take(False)` 로 실제 반환까지 간다
        self.lab_status.setText("⚠ 폴링 중단 — 제어권을 해제했습니다")
        self.lab_status.setStyleSheet(
            "padding:4px 8px; border-top:1px solid #cfd8e0; color:#c0392b;")

    def _on_motor_data(self, data: dict):
        """폴링 결과 → 표 + 바퀴 그림 (GUI 스레드)."""
        angles = {}
        for node, vals in data.items():
            deg = rpm = amp = None
            if 0x6041 in vals:
                self._status[node] = vals[0x6041]
            # 호밍 중 0x6064 는 실위치가 아니라 0 을 돌려준다 — 그대로 쓰면 바퀴 그림이
            # 0° 로 튀어 실제 자세를 오해하게 만든다. 그 구간은 각도를 갱신하지 않는다.
            if 0x6064 in vals and node in STEER_HOME and not self._homing:
                deg = (vals[0x6064] - STEER_HOME[node]) / COUNTS_PER_DEG
                angles[node] = deg
                self._set_meas(node, deg)
            if 0x606C in vals:
                rpm = vals[0x606C] / 10.0                    # 0.1 r/min
            if 0x6078 in vals:
                amp = vals[0x6078] / 100.0                   # 0.01 A
            self.set_motor_values(node, deg, rpm, amp)
        if angles:
            self._redraw_wheel()


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

    타이머 유무에 따른 SIGTERM 거동:

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
