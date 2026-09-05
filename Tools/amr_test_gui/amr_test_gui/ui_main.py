"""PyQt5 메인 윈도우 — Tongyi 4축 AMR 구동 테스트 GUI.

정지 수단: **본체 하드웨어 E-STOP 이 비상정지의 정본**이다. 화면에는 소프트 E-STOP 을 두지
않는다(2026-07-27 사용자 결정) — 저속 테스트 도구에 물리 E-STOP 의 시각 언어를 빌린 버튼을
두면 "이걸 누르면 무조건 선다"는 잘못된 신뢰만 만든다. 화면 정지는 `정지` 모드(Space·Esc)다.

`controller.estop()` 래치는 **내부 메커니즘으로만** 남는다 — 호밍 중 backend 조향 setpoint
억제와 종료 경로에서 쓴다. 사용자에게 노출되지 않으므로 항상 코드가 해제 책임을 진다.
브링업(최대 ~2 s 블로킹)은 워커 스레드에서 수행해 그 동안에도 UI 가 살아있게 한다.
"""
from __future__ import annotations

import atexit
import signal
import sys
import time

from PyQt5.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QListWidget, QMessageBox,
                             QPlainTextEdit, QPushButton, QShortcut, QSlider, QSpinBox,
                             QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from . import modes as M
from .constants import CMD_HZ, DEFAULT_SPEED_MMPS, MAX_SPEED_MMPS
from .controller import AmrTestController
from .seer_source import DEFAULT_IP, SeerAlarmSource
from .wheel_view import WheelView

RED = "#c0392b"
GREEN = "#1e8449"
AMBER = "#b9770e"
GREY = "#5d6d7e"


def _box(text: str, color: str, bold=True, size=11) -> QLabel:
    lab = QLabel(text)
    lab.setStyleSheet(f"color: white; background: {color}; padding: 4px 8px; border-radius: 3px;")
    f = QFont()
    f.setBold(bold)
    f.setPointSize(size)
    lab.setFont(f)
    return lab


class ConnectWorker(QObject):
    """브링업을 별도 스레드에서 수행 — 그 동안 UI(특히 E-STOP)가 살아있도록."""

    done = pyqtSignal(bool, str)

    def __init__(self, controller, bus_factory, allow_homing):
        super().__init__()
        self.controller = controller
        self.bus_factory = bus_factory
        self.allow_homing = allow_homing

    def run(self):
        try:
            self.controller.connect(self.bus_factory, allow_homing_motion=self.allow_homing)
            self.done.emit(True, "연결 완료")
        except Exception as exc:
            self.done.emit(False, f"{type(exc).__name__}: {exc}")


class MainWindow(QWidget):
    # backend TX/RX·Seer 폴링 등 **비-GUI 스레드**에서도 로그가 들어온다.
    # Qt 위젯은 GUI 스레드에서만 만질 수 있으므로 반드시 시그널을 경유한다(직접 호출 시 코어 덤프).
    log_line = pyqtSignal(str)

    def __init__(self, *, seer_ip: str):
        super().__init__()
        self.controller = AmrTestController(logger=self._log)
        self.seer = SeerAlarmSource(ip=seer_ip, logger=self._log)
        # USB 연결과 제어권은 **완전히 분리**한다. PandaLink 는 USB 만 소유하고
        # safety mode·릴레이를 건드리지 않는다(사용자 지시 2026-07-27).
        from .panda_can_bus import PandaLink
        self.link = PandaLink(logger=self._log)
        self._usb_ok = False
        self._panda_poll = 0
        # 모달 대화상자는 이벤트 루프를 블로킹한다 — 자동 테스트에서는 꺼서 무한 대기를 막는다.
        # (끄더라도 거부·경고 **로직**은 그대로 동작하고 로그로 남는다.)
        self.dialogs_enabled = True
        self._thread: QThread | None = None
        self._fault_announced = False
        self.setWindowTitle("Tongyi 4축 AMR 구동 테스트 GUI")
        self._homing_active = False
        self._homing_poll = 0
        # 해제 사슬을 이미 돌렸는지. 종료 경로가 4개(창 닫기·정지 신호·이벤트루프 종료·
        # 인터프리터 종료)라 같은 사슬이 여러 번 불린다 — `safe_release()` 멱등화 래치.
        self._released = False
        # 제어 패널이 세로로 눌리면 방향 패드 버튼이 minimumHeight 를 지키느라 **서로 겹쳐**
        # 라벨(둘째 줄)이 가려진다(2026-07-28 측정: 행 pitch 29px < 버튼 56px). 기본 높이 확보.
        self.resize(1240, 980)
        self.setMinimumSize(1100, 900)
        self._build()
        self._install_shortcuts()
        # Space 소비 차단 — 버튼이 포커스를 가지면 Space 를 클릭으로 먹는다(#C1).
        for b in (*self.mode_buttons.values(), self.btn_home, self.btn_reset,
                  self.btn_connect, self.btn_disconnect,
                  self.btn_usb_on, self.btn_usb_off, self.btn_homing):
            b.setFocusPolicy(Qt.NoFocus)
        self.log_line.connect(self._append_log)   # 스레드 경계를 넘는 유일한 로그 경로
        self.seer.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(int(1000 / CMD_HZ))
        self._log("[gui] 기동 — 실기 판다 relay")
        self._log("[gui] ⚠ 실로봇 구동. 이동구역 확보 · 저속부터.")

    # ── 레이아웃 ────────────────────────────────────────────────────────────
    def _build(self):
        """연결부 · jog · 바퀴그림 3영역 + 상세는 탭으로 분리."""
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.addWidget(self._build_banner())          # ①②③④ 를 한눈에 (2026-07-28 재설계)
        root.addLayout(self._build_topbar())          # 연결부
        mid = QHBoxLayout()
        mid.addWidget(self._build_control(), 4)       # jog
        mid.addWidget(self._build_wheel(), 6)         # 바퀴 표시부
        root.addLayout(mid, 8)                        # 조작·관측에 세로 공간 우선 배분
        tabs = self._build_tabs()                     # Seer · 모터상세 · 로그
        # 탭은 **진단용 보조**다. stretch 로 두면 조작부의 세로를 뺏어 방향 패드가
        # 최소치 미만으로 눌리고 버튼이 겹친다(2026-07-28 측정: 제어 367px < 필요 523px).
        tabs.setMaximumHeight(220)
        root.addWidget(tabs, 0)

    def _build_banner(self):
        """상태 배너 — 운전자가 한눈에 답해야 하는 네 가지.

        ① 지금 움직이는가 ② 누가 제어권을 갖는가 ③ 왜 안 움직이는가 ④ 이상이 있는가.
        종전 레이아웃은 이 넷을 작은 배지로 흩어 놓고 상단 절반을 빈 공간으로 뒀다.
        (정지 수단은 본체 하드웨어 E-STOP 이 정본 — 화면에 소프트 버튼을 두지 않는 결정은
         파일 상단 docstring 참조. 여기서는 키보드 단축키만 안내한다.)
        """
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        box.setStyleSheet("QFrame { background:#eef2f6; border:1px solid #cfd8e0; border-radius:5px; }")
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(3)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.ban_motion = QLabel("● 정지")
        self.ban_auth = QLabel("제어권 없음")
        self.ban_drive = QLabel("구동 차단")
        for lab, stretch in ((self.ban_motion, 3), (self.ban_auth, 4), (self.ban_drive, 3)):
            f = QFont()
            f.setPointSize(15)
            f.setBold(True)
            lab.setFont(f)
            lab.setStyleSheet("border:none; background:transparent;")
            row.addWidget(lab, stretch)
        v.addLayout(row)

        sub = QHBoxLayout()
        self.ban_reason = QLabel("사유: 연결되지 않음")
        self.ban_reason.setStyleSheet(f"color:{GREY}; border:none; background:transparent;")
        hint = QLabel("정지: <b>Space</b> / <b>Esc</b>   ·   비상정지는 <b>본체 하드웨어 E-STOP</b>")
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hint.setStyleSheet(f"color:{GREY}; border:none; background:transparent;")
        sub.addWidget(self.ban_reason, 6)
        sub.addWidget(hint, 4)
        v.addLayout(sub)
        return box

    def _build_topbar(self):
        bar = QHBoxLayout()

        # ── 1단계: USB 연결 (무해 — 상태만 읽음, 제어권 없음) ────────────────
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("<b>1. 판다 USB</b>"))
        self.btn_usb_on = QPushButton("USB 연결")
        self.btn_usb_on.setMinimumHeight(30)
        self.btn_usb_on.setToolTip("판다를 USB 로 열고 펌웨어·safety_mode·CAN 상태만 읽는다.\n"
                                   "제어권을 가져가지 않으므로 릴레이·모터에 영향 없음.")
        self.btn_usb_on.clicked.connect(self._on_usb_connect)
        self.btn_usb_off = QPushButton("USB 해제")
        self.btn_usb_off.setMinimumHeight(30)
        self.btn_usb_off.setEnabled(False)
        self.btn_usb_off.clicked.connect(self._on_usb_disconnect)
        col1.addWidget(self.btn_usb_on)
        col1.addWidget(self.btn_usb_off)
        bar.addLayout(col1, 2)

        # ── 2단계: 제어권 (위험 — 릴레이 intercept) ──────────────────────────
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("<b>2. 제어권</b> <span style='color:#c0392b'>(릴레이 intercept)</span>"))
        self.btn_connect = QPushButton("제어권 획득 (take)")
        self.btn_connect.setMinimumHeight(30)
        self.btn_connect.setEnabled(False)          # USB 연결 후에만
        self.btn_connect.setToolTip("safety_mode 30 + CAN enable + auth=PC + intercept + heartbeat.\n"
                                    "⚠ Seer 로부터 릴레이를 가져오고 모터 브링업을 수행한다.")
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect = QPushButton("제어권 반환 (release)")
        self.btn_disconnect.setMinimumHeight(30)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.chk_homing = QCheckBox("콜드 브링업 허용 (조향 물리 스윙)")
        self.chk_homing.setToolTip(
            "backend allow_homing_motion. 조향 실측이 홈에서 5° 이상 벗어난 상태(콜드)에서는\n"
            "브링업이 거부된다. 체크 시 홈 복귀 스윙을 허용한다 — 잭업/주변 확보 후에만.")
        col2.addWidget(self.btn_connect)
        col2.addWidget(self.btn_disconnect)
        col2.addWidget(self.chk_homing)
        bar.addLayout(col2, 3)

        # 상태는 한 줄로 — USB → 제어권 → relay 는 순차 단계라 따로 볼 이유가 없다.
        st = QVBoxLayout()
        self.lab_stage = _box("① USB 미연결", GREY, size=10)
        self.lab_panda = QLabel("판다 상태: —")
        self.lab_panda.setStyleSheet(f"color:{GREY};")
        self.lab_panda.setWordWrap(True)
        st.addWidget(self.lab_stage)
        st.addWidget(self.lab_panda)
        bar.addLayout(st, 3)
        return bar

    def _build_control(self):
        g = QGroupBox("제어")
        v = QVBoxLayout(g)

        v.addWidget(QLabel("<b>속도 상한</b> <span style='color:#5d6d7e'>저속 기본 — 검증 전 상향 금지</span>"))
        h = QHBoxLayout()
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(0, int(MAX_SPEED_MMPS))
        self.sld_speed.setValue(int(DEFAULT_SPEED_MMPS))
        self.spn_speed = QSpinBox()
        self.spn_speed.setRange(0, int(MAX_SPEED_MMPS))
        self.spn_speed.setValue(int(DEFAULT_SPEED_MMPS))
        self.spn_speed.setSuffix(" mm/s")
        self.sld_speed.valueChanged.connect(self.spn_speed.setValue)
        self.spn_speed.valueChanged.connect(self.sld_speed.setValue)
        self.spn_speed.valueChanged.connect(self.controller.set_speed_mmps)
        h.addWidget(self.sld_speed, 4)
        h.addWidget(self.spn_speed, 1)
        v.addLayout(h)

        v.addWidget(QLabel("<b>조향각</b> <span style='color:#5d6d7e'>±90° 리밋 · 30° 단계 · '조향만' 전용</span>"))
        self.chk_sync = QCheckBox("전·후륜 동기")
        self.chk_sync.setChecked(True)
        self.chk_sync.setToolTip("해제하면 전륜(N3)·후륜(N4)을 따로 지령할 수 있다.\n"
                                 "⚠ 비대칭 조향은 8방위 주행 모드에서는 쓰이지 않는다"
                                 "(방향이 실측·도출로 확정된 양축 동일각 자세만 주행 허용).")
        v.addWidget(self.chk_sync)
        self.sld_steer = {}
        self.lab_steer = {}
        for node, name in ((3, "전륜 N3"), (4, "후륜 N4")):
            row = QHBoxLayout()
            lab = QLabel(name)
            lab.setMinimumWidth(58)
            sld = QSlider(Qt.Horizontal)
            sld.setRange(-90, 90)
            sld.setValue(0)
            sld.setTickInterval(30)
            sld.setTickPosition(QSlider.TicksBelow)
            sld.valueChanged.connect(lambda val, n=node: self._on_steer_slider(n, val))
            val_lab = QLabel("0°")
            val_lab.setMinimumWidth(46)
            row.addWidget(lab)
            row.addWidget(sld, 5)
            row.addWidget(val_lab, 1)
            v.addLayout(row)
            self.sld_steer[node] = sld
            self.lab_steer[node] = val_lab

        v.addWidget(QLabel("<b>주행 방향</b> <span style='color:#5d6d7e'>대각선 = 45° 크랩 · ⚠ 도출(직접 실측 아님)</span>"))
        grid = QGridLayout()
        grid.setSpacing(4)
        self.mode_buttons = {}
        for (r, c), key in M.PAD_LAYOUT.items():
            mode = M.BY_KEY[key]
            b = QPushButton(f"{mode.arrow}\n{mode.label}" + ("  ⚠" if not mode.verified else ""))
            b.setMinimumHeight(50)
            b.setToolTip(f"조향 {mode.steer_deg:+.0f}° · 구동 raw 부호 {mode.raw_sign:+d}\n"
                         f"근거: {mode.basis}"
                         + ("\n⚠ 직접 실측 아님(도출) — 저속 1회 육안 확인 후 사용" if not mode.verified else ""))
            # ⚠ 비활성 대비 — Fusion 기본 disabled 색은 배경과 거의 구분되지 않아
            #   전체 화면에서는 "↑\n전진" 의 라벨이 안 보이고 화살표만 있는 것처럼 읽힌다
            #   (2026-07-28 확인: 버튼 단독 grab 에서는 두 줄 다 렌더됨 — 문제는 레이아웃이 아니라 대비).
            #   미연결 상태에서도 어떤 버튼인지 읽을 수 있어야 한다.
            base = "QPushButton { padding: 2px; %s }" % (
                "font-weight: bold;" if key == "stop"
                else (f"color: {AMBER};" if not mode.verified else ""))
            b.setStyleSheet(base + " QPushButton:disabled { color: #8894a2; }")
            b.clicked.connect(lambda _, k=key: self._on_mode(k))
            grid.addWidget(b, r, c)
            self.mode_buttons[key] = b
        # stretch 를 줘야 세로가 눌릴 때 방향 패드가 우선 확보된다.
        # 종전에는 stretch 없이 addLayout 해서 화면이 좁으면 버튼이 ~30px 로 눌리고
        # "↖\n좌전 45°" 의 **둘째 줄(라벨)이 잘려 화살표만 보였다**(2026-07-28 실기 화면 확인).
        v.addLayout(grid, 5)

        row2 = QHBoxLayout()
        b_steer = QPushButton("조향만 (슬라이더 각도)")
        b_steer.setMinimumHeight(34)
        b_steer.setToolTip(M.STEER_ONLY.basis)
        b_steer.clicked.connect(lambda: self._on_mode("steer_only"))
        self.mode_buttons["steer_only"] = b_steer
        row2.addWidget(b_steer)
        self.btn_home = QPushButton("조향 0° 이동 + 정지")
        self.btn_home.setMinimumHeight(34)
        # :disabled 를 함께 지정하지 않으면 커스텀 배경이 비활성 표시를 덮어써
        # '눌리는 버튼'처럼 보인다(미연결 상태 오해 유발) — 실제 관측된 결함이라 명시 처리.
        self.btn_home.setStyleSheet(
            f"QPushButton {{ background:{GREEN}; color:white; font-weight:bold; }}"
            f"QPushButton:disabled {{ background:#d5dbe1; color:#9aa5b1; }}")
        self.btn_home.clicked.connect(lambda: self._on_mode("home"))
        row2.addWidget(self.btn_home)
        v.addLayout(row2)

        # 호밍 = 원점(리밋) 탐색 → 펌웨어 정착 위치 이동. 위 '조향 0° 이동'은 기준점을 새로 잡지 않는다.
        # ⚠ 정착 위치는 조향 0° 가 아니다 — 0° 에서 +0.18° / +0.33° 떨어져 있고, 펌웨어에는
        #   0° 로 보내는 동작이 없다(0° 복귀는 호스트가 별도로 지령해야 한다).
        self.btn_homing = QPushButton("호밍  (원점 탐색 → 정착 위치)")
        self.btn_homing.setMinimumHeight(34)
        self.btn_homing.setToolTip(
            "판다 펌웨어가 지휘한다(0xea). 조향축이 −리밋까지 이동해 원점을 잡고 정착 위치로 돌아온다.\n"
            "※ 정착 위치는 조향 0° 가 아니다 — 0° 에서 +0.18° / +0.33° 떨어진 지점이다.\n"
            "약 35초 소요. 진행 중에는 즉시 정지 래치를 걸어 backend 조향 지령을 억제한다.\n"
            "⚠ 조향축이 크게 움직인다 — 이동구역 확보 후 실행할 것.")
        self.btn_homing.clicked.connect(self._on_homing)
        v.addWidget(self.btn_homing)

        self.btn_reset = QPushButton("램프 FAULT 해제 (운전자 확인)")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self._on_reset_fault)
        v.addWidget(self.btn_reset)
        g.setMinimumHeight(540)   # 레이아웃 minimumSize 523 + 여유 (겹침 방지)
        self._set_controls_enabled(False)
        return g

    def _build_wheel(self):
        """바퀴 그림 + 주행에 직결된 상태만. 수치 상세는 '모터 상세' 탭으로 뺀다."""
        g = QGroupBox("주행 상태")
        v = QVBoxLayout(g)

        # 모드·램프상태·구동가부·차단사유는 상단 배너가 담당 — 여기서 반복하지 않는다.
        self.lab_raw = QLabel("송신 raw: —")
        f = QFont("monospace")
        f.setPointSize(11)
        f.setBold(True)
        self.lab_raw.setFont(f)
        v.addWidget(self.lab_raw)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        v.addWidget(sep)

        self.wheel_view = WheelView()
        v.addWidget(self.wheel_view, 5)
        return g

    def _build_motor_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.tbl = QTableWidget(4, 8)
        self.tbl.setHorizontalHeaderLabels(
            ["node", "역할", "pos(counts)", "각도°", "statusword", "error", "전류", "aborts"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setMaximumHeight(158)   # 4행 + 헤더가 스크롤 없이 보이는 높이
        self.tbl.verticalHeader().setDefaultSectionSize(26)
        v.addWidget(self.tbl, 0)

        self.lab_bus = QLabel("tx/rx: — · 버스 오류: —")
        self.lab_bus.setStyleSheet(f"color:{GREY};")
        v.addWidget(self.lab_bus)
        self.lab_basis = QLabel("근거: —")
        self.lab_basis.setWordWrap(True)
        self.lab_basis.setStyleSheet(f"color:{GREY};")
        v.addWidget(self.lab_basis)
        return w

    def _build_seer_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.lab_seer = _box("Seer: 미연결", GREY, size=9)
        self.lst_seer = QListWidget()
        v.addWidget(self.lab_seer)
        v.addWidget(self.lst_seer)
        return w

    def _build_log_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(500)
        v.addWidget(self.txt_log)
        return w

    def _build_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(self._build_motor_tab(), "모터 상세 (4축)")
        tabs.addTab(self._build_seer_tab(), "Seer 알람")
        tabs.addTab(self._build_log_tab(), "로그")
        return tabs

    # ── 이벤트 ──────────────────────────────────────────────────────────────
    def _install_shortcuts(self):
        """정지 키를 **애플리케이션 전역 단축키**로 건다.

        `keyPressEvent` 로 두면 포커스를 가진 QPushButton 이 Space 를 먼저 소비한다 —
        실측(QTest): 모드 버튼 포커스 상태에서 Space → 정지가 아니라 **직전 주행 지령 재발행**.
        긴급 시 포커스는 방금 누른 모드 버튼에 있으므로 최악의 순간에 정확히 반대로 동작한다(#C1).
        추가 방어로 모든 조작 버튼에 `NoFocus` 를 건다.
        """
        for key in (Qt.Key_Space, Qt.Key_Escape):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(lambda: self._on_mode("stop"))
            self._shortcuts = getattr(self, "_shortcuts", [])
            self._shortcuts.append(sc)

    # ── 1단계: USB 연결 (제어권과 완전 분리) ────────────────────────────────
    def _on_usb_connect(self):
        """판다를 USB 로 열기만 한다. safety mode·릴레이·모터에 영향 0."""
        try:
            st = self.link.open()
        except Exception as exc:
            self._log(f"[gui] ⚠ USB 연결 실패: {type(exc).__name__}: {exc}")
            self._critical("USB 연결 실패",
                           f"{type(exc).__name__}: {exc}\n\n"
                           "판다 USB 연결·udev 규칙·ModemManager 점유를 확인하세요.")
            return
        self._usb_ok = True
        self._log(f"[gui] USB 연결됨 — fw={st.get('version')} "
                  f"safety_mode={st.get('safety_mode')} harness={st.get('car_harness_status')}")
        self.btn_usb_on.setEnabled(False)
        self.btn_usb_off.setEnabled(True)
        self.btn_connect.setEnabled(True)       # 이제서야 제어권 획득이 가능해진다

    def _on_usb_disconnect(self):
        """USB 만 닫는다. 제어권을 쥔 상태면 거부 — 먼저 release 해야 한다."""
        if self.controller.connected:
            self._log("[gui] 제어권을 쥔 상태입니다 — 먼저 '제어권 반환(release)' 후 USB 를 해제하세요.")
            self._warn("USB 해제 거부",
                       "제어권을 보유한 채 USB 를 닫으면 릴레이가 intercept 로 남습니다.\n"
                       "먼저 '제어권 반환(release)' 을 수행하세요.")
            return
        self.link.close()
        self._usb_ok = False
        self.btn_usb_on.setEnabled(True)
        self.btn_usb_off.setEnabled(False)
        self.btn_connect.setEnabled(False)

    # ── 2단계: 제어권 획득 ──────────────────────────────────────────────────
    def _on_connect(self):
        if self.controller.connected or self._thread is not None:
            return
        if not self._usb_ok:
            self._log("[gui] USB 가 연결되지 않았습니다 — 1단계 'USB 연결' 을 먼저 수행하세요.")
            return
        if not self._confirm(
                "실기 연결 확인",
                "실로봇 CAN relay 제어권을 획득합니다.\n\n"
                "· 이동 구역이 비었습니까?\n"
                "· 조향은 홈 부근입니까?\n\n계속할까요?"):
            return
        self.btn_connect.setEnabled(False)
        self.lab_stage.setText("② 제어권 획득 중… (브링업)")
        self.lab_stage.setStyleSheet(f"color:white; background:{AMBER}; padding:4px 8px; border-radius:3px;")
        worker = ConnectWorker(self.controller, self._bus_factory, self.chk_homing.isChecked())
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_connected)
        worker.done.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._thread, self._worker = thread, worker
        thread.start()

    def _on_thread_finished(self):
        """워커 스레드 종료 정리. GUI 스레드를 블로킹하지 않는다(E-STOP 응답성 유지)."""
        self._thread = None

    def _bus_factory(self):
        from .panda_can_bus import PandaCanBus
        # 이미 열린 USB 연결(PandaLink)을 재사용한다 — release 후에도 USB 는 유지된다.
        return PandaCanBus(logger=self._log, link=self.link)

    def _on_connected(self, ok: bool, msg: str):
        self.btn_connect.setEnabled(self._usb_ok and not ok)
        self.btn_disconnect.setEnabled(ok)
        self.btn_usb_off.setEnabled(self._usb_ok and not ok)   # 제어권 보유 중엔 USB 해제 잠금
        self._set_controls_enabled(ok)
        if ok:
            for sld in self.sld_steer.values():
                sld.setValue(0)
            self._log("[gui] 연결 완료 — 기본 모드 정지, 조향 홈.")
        else:
            self._log(f"[gui] ⚠ 연결 실패: {msg}")
            self._critical("연결 실패", msg)

    def _on_disconnect(self):
        """제어권만 반환한다. USB 연결은 유지 — 판다 상태를 계속 볼 수 있어야 한다."""
        self.controller.disconnect()
        self.btn_connect.setEnabled(self._usb_ok)
        self.btn_disconnect.setEnabled(False)
        self.btn_usb_off.setEnabled(self._usb_ok)
        self._set_controls_enabled(False)

    def _on_mode(self, key: str):
        if not self.controller.connected:
            return
        if self._homing_active and key != "stop":
            self._log("[gui] 호밍 진행 중 — 모드 전환 거부. 완료를 기다리세요.")
            return
        self.controller.set_mode(key)

    def _on_steer_slider(self, node: int, val: int):
        self.lab_steer[node].setText(f"{val:+d}°")
        if self.chk_sync.isChecked():
            # 동기: 반대편 슬라이더도 같은 값으로(시그널 재진입 방지 위해 블록)
            for other, sld in self.sld_steer.items():
                if other != node and sld.value() != val:
                    sld.blockSignals(True)
                    sld.setValue(val)
                    sld.blockSignals(False)
                    self.lab_steer[other].setText(f"{val:+d}°")
            self.controller.set_steer_slider_deg(float(val))     # node=None → 양축
        else:
            self.controller.set_steer_slider_deg(float(val), node=node)

    def _on_homing(self):
        """펌웨어 조향 호밍 — 원점(리밋) 탐색 → 조향 0° 복귀.

        backend 는 50 Hz 로 조향 setpoint(0x607A+0x3F)를 계속 송신하므로 그대로 두면
        펌웨어 호밍과 지령이 충돌한다. E-STOP 래치를 걸면 backend 가 조향 setpoint 를
        억제하고 구동 0 을 유지한다(backend.py `_tx_loop` 의 `if estopped: continue`).
        """
        if not self.controller.connected or self._homing_active:
            return
        if not self._confirm(
                "호밍 실행",
                "조향축이 −리밋까지 이동한 뒤 펌웨어 정착 위치로 돌아옵니다 (약 35초).\n"
                "※ 그 위치는 조향 0° 가 아닙니다 — 0° 에서 +0.18° / +0.33° 떨어진 지점입니다.\n\n"
                "· 조향 이동 구역이 비었습니까?\n"
                "\n계속할까요?"):
            return
        # backend 조향 setpoint 억제(내부 래치). 아래 _poll_homing 이 종료 시 반드시 해제한다.
        self.controller.estop(True)
        if not self.link.homing_start():
            self.controller.estop(False)
            self._log("[gui] ⚠ 호밍 거부 — 펌웨어 인터록(제어권·safety_mode 30) 확인 필요.")
            self._warn("호밍 거부", "펌웨어가 개시를 거부했습니다.\n제어권을 보유했는지 확인하세요.")
            return
        self._homing_active = True
        self._homing_poll = 0
        self.btn_homing.setEnabled(False)
        self._log("[gui] 호밍 개시 — 원점 탐색 → 조향 0° 복귀 (약 35초).")

    def _poll_homing(self):
        h = self.link.homing_status()
        if not h:
            return
        self.lab_stage.setText(f"호밍: {h['text']}  ({h['elapsed_s']}s)")
        self.lab_stage.setStyleSheet(
            f"color:white; background:{AMBER}; padding:4px 8px; border-radius:3px;")
        if not h["terminal"]:
            return
        self._homing_active = False
        self._homing_poll = 0
        self.btn_homing.setEnabled(self.controller.connected)
        self.controller.estop(False)          # 내부 래치 해제 — 사용자에게 노출되지 않으므로 코드가 책임진다
        self.controller.set_mode("stop")
        if h["state"] == 5:
            for sld in self.sld_steer.values():
                sld.setValue(0)
            self._log(f"[gui] 호밍 완료 — 조향 0°. (DI3=0x{h['di3']:02x} DI4=0x{h['di4']:02x}) 모드: 정지")
        else:
            self._log(f"[gui] ⚠ 호밍 실패: {h['text']}  "
                      f"(원점마스크 0x{h['done_mask']:02x} 도달마스크 0x{h['reached_mask']:02x})")
            self._warn("호밍 실패", f"{h['text']}\n\n조향축이 리밋 근처에 남아 있을 수 있습니다.")

    def _on_reset_fault(self):
        self.controller.reset_fault()
        self._fault_announced = False
        self.btn_reset.setEnabled(False)

    def _set_controls_enabled(self, on: bool):
        for b in self.mode_buttons.values():
            b.setEnabled(on)
        self.btn_home.setEnabled(on)
        self.btn_homing.setEnabled(on and not self._homing_active)
        # 조향 슬라이더는 '조향만' 모드에서만 효력이 있으므로 그때만 활성화한다
        # (움직였는데 아무 일도 안 일어나는 혼동 제거).
        steer_mode = on and self.controller.connected and \
            getattr(self.controller._mode, 'key', '') == 'steer_only'
        for sld in self.sld_steer.values():
            sld.setEnabled(steer_mode)
        self.chk_sync.setEnabled(steer_mode)

    # ── 주기 갱신 ───────────────────────────────────────────────────────────
    def _update_banner(self, st):
        """상태 배너 — 큰 글씨 3칸 + 차단 사유 한 줄.

        색 규칙(전 화면 공통): 적=위험/이상 · 앰버=주의(제어권 보유·움직임) · 녹=정상/허용 · 회=비활성.
        """
        raw = st.get("raw_units") or 0
        mode = st.get("mode")
        # ① 지금 움직이는가 — 지령 raw 가 0 이 아니면 '주행 중'
        if raw:
            self.ban_motion.setText(f"▶ 주행 중  {st.get('raw_mmps', 0):+.0f} mm/s")
            self.ban_motion.setStyleSheet(f"color:{AMBER}; border:none; background:transparent;")
        else:
            self.ban_motion.setText("● 정지")
            self.ban_motion.setStyleSheet(f"color:{GREY}; border:none; background:transparent;")
        # ② 누가 제어권을 갖는가
        if st.get("connected"):
            self.ban_auth.setText("제어권 보유 (PC)")
            self.ban_auth.setStyleSheet(f"color:{AMBER}; border:none; background:transparent;")
        else:
            self.ban_auth.setText("제어권 없음 (Seer 주도)")
            self.ban_auth.setStyleSheet(f"color:{GREY}; border:none; background:transparent;")
        # ③④ 구동 가부 + 이상 여부
        if st.get("fault"):
            self.ban_drive.setText("⚠ FAULT")
            self.ban_drive.setStyleSheet(f"color:{RED}; border:none; background:transparent;")
        elif st.get("drive_allowed") and not st.get("estop"):
            self.ban_drive.setText("구동 허용")
            self.ban_drive.setStyleSheet(f"color:{GREEN}; border:none; background:transparent;")
        else:
            self.ban_drive.setText("구동 차단")
            self.ban_drive.setStyleSheet(f"color:{GREY}; border:none; background:transparent;")
        # 차단 사유 — 왜 안 움직이는지를 항상 한 줄로 노출한다(종전에는 램프 detail 에 묻혔다)
        if not st.get("connected"):
            reason = "연결되지 않음 — ① USB 연결 → ② 제어권 획득"
        elif st.get("ramp_detail"):
            reason = st["ramp_detail"]
        elif mode is not None and getattr(mode, "raw_sign", 0) == 0:
            reason = f"{getattr(mode, 'label', '정지')} 모드 — 구동 지령 없음"
        elif not raw:
            reason = "속도 상한 0"
        else:
            reason = f"{getattr(mode, 'label', '')} · {getattr(mode, 'basis', '')}"
        self.ban_reason.setText(f"사유: {reason}")

    def _on_tick(self):
        st = self.controller.tick()
        self._update_banner(st)
        self._update_conn(st)
        # 호밍 폴은 _update_conn **뒤에** 둔다 — 앞에 두면 진행상황이 단계표시로 덮여
        # 35초 내내 아무것도 안 보인다(2026-07-27 실기 확인).
        # 카운터는 _panda_poll 과 분리한다 — 공유하면 _update_conn 의 증가와 겹쳐 폴이 걸리지 않는다.
        if self._homing_active:
            self._homing_poll += 1
            if self._homing_poll % 10 == 1:      # 20 Hz tick → 약 2 Hz
                self._poll_homing()
        self._update_ramp(st)
        self.wheel_view.set_state(st)
        self._update_table(st)
        self._update_seer()

    def _update_conn(self, st):
        """연결 상태를 한 줄로 표시한다 — ① USB → ② 제어권 → ③ relay 는 순차 단계다.

        호밍 중에는 단계표시를 갱신하지 않는다(진행상황 표시를 덮지 않도록).
        """
        if self._homing_active:
            return
        if st["connected"]:
            stage, color = "③ 제어권 보유 · relay intercept (PC 주도)", AMBER
        elif self._usb_ok:
            stage, color = "② USB 연결됨 — 제어권 없음 (Seer 주도)", GREEN
        else:
            stage, color = "① USB 미연결", GREY
        self.lab_stage.setText(stage)
        self.lab_stage.setStyleSheet(
            f"color:white; background:{color}; padding:4px 8px; border-radius:3px;")
        # 판다 실상태 — USB 경유 health 는 1초에 한 번만 읽는다(20 Hz 폴링은 과부하)
        self._panda_poll += 1
        if self._usb_ok and self._panda_poll % int(CMD_HZ) == 0:
            h = self.link.status()
            if h.get("error"):
                self.lab_panda.setText(f"판다 상태: 읽기 실패 — {h['error']}")
            else:
                self.lab_panda.setText(
                    f"판다: fw={h.get('version')} · safety={h.get('safety_mode')} · "
                    f"harness={h.get('car_harness_status')} · uptime={h.get('uptime')}s · "
                    f"rx_err={h.get('can_rx_errs')} faults={h.get('faults')}")

    def _update_ramp(self, st):
        mode = st["mode"]
        # 조향 슬라이더는 '조향만' 모드에서만 효력이 있다 → 그때만 활성(무반응 혼동 제거).
        steer_mode = bool(st["connected"]) and mode.key == "steer_only"
        for sld in self.sld_steer.values():
            sld.setEnabled(steer_mode)
        self.chk_sync.setEnabled(steer_mode)
        self.lab_raw.setText(
            f"송신 raw: {st['raw_units']:+6d} units (0.1 rpm)   ≈ {st['raw_mmps']:+.1f} mm/s"
            f"   |   램프 {st['ramp_state']}  지령 {st['ramp_cmd_deg']:+.1f}° / 목표 {st['ramp_target_deg']:+.1f}°"
            + ("   |   backend 정착 게이트 작동(구동 0)" if st["backend_settling"] else ""))
        self.lab_basis.setText(f"근거: {mode.basis}"
                               + ("   ⚠ 방향 미검증(debt-004)" if not mode.verified else ""))
        if st["fault"]:
            self.btn_reset.setEnabled(True)
            if not self._fault_announced:
                self._fault_announced = True
                self._log(f"[gui] ⚠⚠ 램프 FAULT — {st['ramp_detail']}  → 조향 홈 강제·구동 금지")

    def _update_table(self, st):
        rows = st["nodes"]
        self.tbl.setRowCount(max(4, len(rows)))
        for i, r in enumerate(rows):
            vals = [str(r["node"]), r["role"],
                    "—" if r["pos"] is None else f"{r['pos']:,}",
                    "—" if r["deg"] is None else f"{r['deg']:+.2f}",
                    "—" if r["status"] is None else f"0x{r['status']:04X}",
                    "—" if r["error"] is None else f"0x{r['error']:04X}",
                    "—" if r["current"] is None else f"{r['current'] / 100.0:.2f} A",
                    str(r["aborts"])]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if c == 5 and r["error"]:
                    item.setBackground(QColor(RED))
                    item.setForeground(QColor("white"))
                if c == 7 and r["aborts"]:
                    item.setBackground(QColor(AMBER))
                self.tbl.setItem(i, c, item)
        self.tbl.resizeColumnsToContents()
        self.lab_bus.setText(
            f"tx/rx: {st['tx']} / {st['rx']}   ·   버스 오류 tx={st['bus_tx_errors']} rx={st['bus_rx_errors']}")

    def _update_seer(self):
        s = self.seer.latest()
        if s["available"]:
            n = len(s["can_hits"])
            self.lab_seer.setText(f"Seer: {s['reason']} · CAN계열 {n}건 · {s['age_s']}s 전")
            self.lab_seer.setStyleSheet(
                f"color:white; background:{RED if n else GREEN}; padding:4px 8px; border-radius:3px;")
        else:
            self.lab_seer.setText(f"Seer: 비활성 — {s['reason']}")
            self.lab_seer.setStyleSheet(f"color:white; background:{GREY}; padding:4px 8px; border-radius:3px;")
        lines = list(s["can_hits"])
        for lvl, items in s["alarms"].items():
            for code, desc in items.items():
                line = f"[{lvl}] {code} {desc}"
                if line not in lines:
                    lines.append(line)
        display = lines or (["(알람 없음)"] if s["available"] else ["(Seer 미연결 — 알람 감시 없음)"])
        if [self.lst_seer.item(i).text() for i in range(self.lst_seer.count())] != display:
            self.lst_seer.clear()
            self.lst_seer.addItems(display)

    # ── 대화상자 (테스트에서 끌 수 있게 경유) ──────────────────────────────
    def _confirm(self, title: str, text: str) -> bool:
        """운전자 확인. 대화상자를 끈 자동 실행에서는 승인으로 간주한다(로직·로그는 그대로)."""
        if not self.dialogs_enabled:
            self._log(f"[gui] (확인 생략) {title}")
            return True
        return QMessageBox.question(self, title, text,
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No) == QMessageBox.Yes

    def _warn(self, title: str, text: str):
        if self.dialogs_enabled:
            QMessageBox.warning(self, title, text)

    def _critical(self, title: str, text: str):
        if self.dialogs_enabled:
            QMessageBox.critical(self, title, text)

    # ── 로그·종료 ───────────────────────────────────────────────────────────
    def _log(self, msg: str):
        """어느 스레드에서 불려도 안전 — 위젯 갱신은 시그널로 GUI 스레드에 위임한다."""
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        try:
            self.log_line.emit(line)
        except RuntimeError:
            pass   # 창이 이미 파괴된 뒤 도착한 늦은 로그

    def _append_log(self, line: str):
        """GUI 스레드 전용 슬롯."""
        self.txt_log.appendPlainText(line)

    def safe_release(self, reason: str = "") -> None:
        """제어권을 반환하고 USB 를 해제한다. **모든 종료 경로가 이 함수를 공유한다.**

        창을 닫는 정상 종료만 안전하면 부족하다 — Ctrl+C·`kill`·처리되지 않은 예외로 죽으면
        릴레이가 intercept 로, USB 가 열린 채로 남는다. 그래서 `closeEvent` 안에 있던 해제
        사슬을 여기로 꺼내 4개 경로(창 닫기·정지 신호·이벤트루프 종료·인터프리터 종료)가
        같은 코드를 부르게 한다. `run()` 이 그 배선을 설치한다.

        **멱등이다** — 여러 경로가 연달아 불러도 두 번째 호출부터는 즉시 반환한다. 사슬의 각
        단계(`controller.disconnect` → `backend.shutdown` → `link.close`)도 각자 중복 호출이
        무해하도록 만들어져 있으나, 재진입으로 USB 제어전송이 겹치지 않도록 여기서 먼저 막는다.

        ⚠ 브링업 워커가 실행 중이면 그것을 먼저 기다려야 한다. 그러지 않으면 `disconnect()` 가
        `backend is None` 으로 조기 반환하고, 그 직후 워커가 브링업을 완주해 **UI 도 E-STOP 도
        없는 상태로 TX 루프가 계속 지령을 송신**한다(리뷰 #H2, 실증됨).

        Args:
            reason: 어느 경로로 들어왔는지(로그용). 사후 분석에서 "왜 해제됐나"를 가른다.
        """
        if self._released:
            return
        self._released = True
        if reason:
            print(f"[gui] 해제 시작 — {reason}", flush=True)
        # Qt 객체는 인터프리터 종료 시점에 이미 파괴됐을 수 있다(atexit 경로).
        try:
            self._timer.stop()
        except (RuntimeError, AttributeError):
            pass
        if self._thread is not None:
            self._log("[gui] 브링업 진행 중 — 완료를 기다린 뒤 제어권을 반환합니다…")
            self._thread.wait(8000)
            try:
                QApplication.processEvents()   # 워커 done 시그널을 소비해 backend 를 공표시킨다
            except RuntimeError:
                pass
        try:
            self.controller.estop(True)
        except Exception:
            pass
        try:
            self.controller.disconnect()
        except Exception as exc:
            print(f"[gui] ⚠ 종료 중 disconnect 예외: {exc}", flush=True)
        try:
            self.seer.stop()
        except Exception:
            pass
        if self.link is not None:
            try:
                self.link.close()      # 제어권 반환 후 USB 도 정리
            except Exception as exc:
                print(f"[gui] ⚠ 종료 중 USB close 예외: {exc}", flush=True)
        print("[gui] 해제 완료 — 제어권 반환 · USB 연결 해제", flush=True)

    def closeEvent(self, ev):
        """창 닫기 경로. 해제는 `safe_release()` 가 소유한다."""
        self.safe_release("창 닫기")
        ev.accept()


def run(seer_ip: str = DEFAULT_IP) -> int:
    """GUI 를 띄우고, **어떤 경로로 죽어도 제어권·USB 가 풀리도록** 배선한 뒤 이벤트 루프를 돈다.

    해제 배선 4경로 — 전부 `MainWindow.safe_release()`(멱등)로 수렴한다:

    | 경로 | 배선 | 비고 |
    | --- | --- | --- |
    | 창 닫기·Alt+F4 | `closeEvent` | 기존 경로 |
    | Ctrl+C(SIGINT)·`kill`(SIGTERM) | `signal.signal` → `app.quit()` | 핸들러는 **플래그·quit 만** |
    | 이벤트 루프 정상 종료 | `app.exec_()` 반환 직후 | quit 경로가 여기로 합류 |
    | 인터프리터 종료·예외 탈출 | `atexit` + `sys.excepthook` | 최후 그물 |

    **정지 신호 핸들러에서 USB 제어전송을 하지 않는다.** 신호 핸들러는 임의 시점에 끼어들어
    실행되므로 그 안에서 `libusb` 호출·`sleep` 을 하면 재진입 위험이 있다
    (`domains/concurrency-coding.md` §1: 핸들러는 최소 작업만). 따라서 핸들러는 `app.quit()` 로
    이벤트 루프만 끝내고, 실제 해제는 루프가 빠져나온 **정상 스택**에서 수행한다.

    ⚠ **신호 해제는 `MainWindow._timer` 에 의존한다 — 이 결합을 깨지 말 것.**
    Qt 의 C++ 이벤트 루프가 도는 동안에는 파이썬 바이트코드가 실행되지 않아 파이썬 신호
    핸들러가 전달되지 않는다. `_timer`(`CMD_HZ`)가 파이썬 슬롯(`_on_tick`)을 계속 돌려
    인터프리터가 주기적으로 제어를 되찾는 덕분에 핸들러가 즉시 실행된다.

    2026-07-28 실측(PyQt5, offscreen, 하드웨어 무관):

    | 조건 | SIGTERM 결과 |
    | --- | --- |
    | 타이머 있음(현행) | 0.036 s 내 핸들러 실행 → 해제 → exit 0 |
    | 타이머 없음 | **핸들러 미실행 · 프로세스 매달림 → SIGKILL(exit 137)** |

    따라서 `_timer` 를 조건부 기동(예: 연결 후에만 start)으로 바꾸면 **연결 전 Ctrl+C 가 먹지
    않는다.** `_timer` 는 `__init__` 에서 무조건 start 되어야 하며, 바꿔야 한다면 별도
    keep-alive 타이머를 함께 도입할 것.

    Args:
        seer_ip: Seer 알람 폴링 대상 IP(Internet Protocol) 주소.
    Returns:
        프로세스 종료 코드(Qt 이벤트 루프 반환값).
    """
    app = QApplication(sys.argv[:1])
    win = MainWindow(seer_ip=seer_ip)

    def _on_stop_signal(signum, _frame):
        # 핸들러 최소 작업: 로그 1줄 + 이벤트 루프 종료 요청. 해제는 루프 밖에서.
        print(f"[gui] 정지 신호({signal.Signals(signum).name}) 수신 — 해제 후 종료합니다.",
              flush=True)
        app.quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _on_stop_signal)

    # 예외로 죽는 경우에도 릴레이를 intercept 로 남기지 않는다.
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
