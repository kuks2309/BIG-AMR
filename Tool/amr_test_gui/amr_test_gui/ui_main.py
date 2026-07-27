"""PyQt5 메인 윈도우 — Tongyi 4축 AMR 구동 테스트 GUI.

안전 우선순위(위→아래): E-STOP → 정지 → HOME → 램프 → 모드.
E-STOP 은 UI 최상단 + Space 키 + 창 종료/예외 경로 어디서나 도달 가능해야 한다.
브링업(최대 ~2 s 블로킹)은 워커 스레드에서 수행해 그 동안에도 E-STOP 이 눌리도록 한다.
"""
from __future__ import annotations

import sys
import time

from PyQt5.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QListWidget, QMessageBox,
                             QPlainTextEdit, QPushButton, QShortcut, QSlider, QSpinBox,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

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

    def __init__(self, *, dry_run: bool, seer_ip: str):
        super().__init__()
        self.dry_run = dry_run
        self.controller = AmrTestController(logger=self._log)
        self.seer = SeerAlarmSource(ip=seer_ip, logger=self._log)
        self._thread: QThread | None = None
        self._fault_announced = False
        self.setWindowTitle("Tongyi 4축 AMR 구동 테스트 GUI"
                            + ("  [DRY-RUN 시뮬레이터]" if dry_run else "  [실기 relay]"))
        self.resize(1180, 780)
        self._build()
        self._install_shortcuts()
        # Space 소비 차단 — 버튼이 포커스를 가지면 Space 를 클릭으로 먹는다(#C1).
        for b in (*self.mode_buttons.values(), self.btn_home, self.btn_reset,
                  self.btn_connect, self.btn_disconnect, self.btn_estop):
            b.setFocusPolicy(Qt.NoFocus)
        self.log_line.connect(self._append_log)   # 스레드 경계를 넘는 유일한 로그 경로
        self.seer.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(int(1000 / CMD_HZ))
        self._log(f"[gui] 기동 — 모드: {'DRY-RUN(하드웨어 무접촉)' if dry_run else '실기 판다 relay'}")
        if not dry_run:
            self._log("[gui] ⚠ 실로봇 구동. E-stop 상비 · 이동구역 확보 · 저속부터.")

    # ── 레이아웃 ────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.addLayout(self._build_topbar())
        mid = QHBoxLayout()
        mid.addWidget(self._build_control(), 4)
        mid.addWidget(self._build_status(), 6)
        root.addLayout(mid, 5)
        root.addLayout(self._build_bottom(), 3)

    def _build_topbar(self):
        bar = QHBoxLayout()
        self.btn_estop = QPushButton("■  E-STOP  (Space)")
        self.btn_estop.setCheckable(True)
        self.btn_estop.setMinimumHeight(64)
        self.btn_estop.setStyleSheet(
            f"QPushButton {{ background:{RED}; color:white; font-size:20pt; font-weight:bold;"
            f" border-radius:6px; }}"
            f"QPushButton:checked {{ background:#7b241c; border:4px solid #f1c40f; }}")
        self.btn_estop.clicked.connect(self._on_estop)
        bar.addWidget(self.btn_estop, 5)

        col = QVBoxLayout()
        self.btn_connect = QPushButton("연결 (take · 제어권 획득)")
        self.btn_connect.setMinimumHeight(30)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect = QPushButton("해제 (release · 제어권 반환)")
        self.btn_disconnect.setMinimumHeight(30)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.chk_homing = QCheckBox("콜드 브링업 허용 (조향 물리 스윙 — 주변 확보 후)")
        self.chk_homing.setToolTip(
            "backend allow_homing_motion. 조향 실측이 홈에서 5° 이상 벗어난 상태(콜드)에서는\n"
            "브링업이 거부된다. 체크 시 홈 복귀 스윙을 허용한다 — 잭업/주변 확보 후에만.")
        col.addWidget(self.btn_connect)
        col.addWidget(self.btn_disconnect)
        col.addWidget(self.chk_homing)
        bar.addLayout(col, 3)

        st = QVBoxLayout()
        self.lab_conn = _box("미연결", GREY)
        self.lab_relay = _box("relay: —", GREY, size=9)
        st.addWidget(self.lab_conn)
        st.addWidget(self.lab_relay)
        bar.addLayout(st, 2)
        return bar

    def _build_control(self):
        g = QGroupBox("제어")
        v = QVBoxLayout(g)

        v.addWidget(QLabel("<b>속도 상한</b> (저속 기본 — 검증 전 상향 금지)"))
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

        v.addWidget(QLabel("<b>조향각</b> (±90° 하드 리밋 · 30° 단계 램프 · '조향만' 모드에서 적용)"))
        h2 = QHBoxLayout()
        self.sld_steer = QSlider(Qt.Horizontal)
        self.sld_steer.setRange(-90, 90)
        self.sld_steer.setValue(0)
        self.sld_steer.setTickInterval(30)
        self.sld_steer.setTickPosition(QSlider.TicksBelow)
        self.sld_steer.valueChanged.connect(self._on_steer_slider)
        self.lab_steer = QLabel("0°")
        self.lab_steer.setMinimumWidth(52)
        h2.addWidget(self.sld_steer, 5)
        h2.addWidget(self.lab_steer, 1)
        v.addLayout(h2)

        v.addWidget(QLabel("<b>주행 방향</b> (대각선 = 45° 크랩 · ⚠ = 도출·직접 실측 아님)"))
        grid = QGridLayout()
        grid.setSpacing(4)
        self.mode_buttons = {}
        for (r, c), key in M.PAD_LAYOUT.items():
            mode = M.BY_KEY[key]
            b = QPushButton(f"{mode.arrow}\n{mode.label}" + ("  ⚠" if not mode.verified else ""))
            b.setMinimumHeight(56)
            b.setToolTip(f"조향 {mode.steer_deg:+.0f}° · 구동 raw 부호 {mode.raw_sign:+d}\n"
                         f"근거: {mode.basis}"
                         + ("\n⚠ 직접 실측 아님(도출) — 저속 1회 육안 확인 후 사용" if not mode.verified else ""))
            if key == "stop":
                b.setStyleSheet("QPushButton { font-weight: bold; }")
            elif not mode.verified:
                b.setStyleSheet(f"QPushButton {{ color: {AMBER}; }}")
            b.clicked.connect(lambda _, k=key: self._on_mode(k))
            grid.addWidget(b, r, c)
            self.mode_buttons[key] = b
        v.addLayout(grid)

        row2 = QHBoxLayout()
        b_steer = QPushButton("조향만 (슬라이더 각도)")
        b_steer.setMinimumHeight(34)
        b_steer.setToolTip(M.STEER_ONLY.basis)
        b_steer.clicked.connect(lambda: self._on_mode("steer_only"))
        self.mode_buttons["steer_only"] = b_steer
        row2.addWidget(b_steer)
        self.btn_home = QPushButton("HOME (조향 0° + 정지)")
        self.btn_home.setMinimumHeight(34)
        # :disabled 를 함께 지정하지 않으면 커스텀 배경이 비활성 표시를 덮어써
        # '눌리는 버튼'처럼 보인다(미연결 상태 오해 유발) — 실제 관측된 결함이라 명시 처리.
        self.btn_home.setStyleSheet(
            f"QPushButton {{ background:{GREEN}; color:white; font-weight:bold; }}"
            f"QPushButton:disabled {{ background:#d5dbe1; color:#9aa5b1; }}")
        self.btn_home.clicked.connect(lambda: self._on_mode("home"))
        row2.addWidget(self.btn_home)
        v.addLayout(row2)

        self.btn_reset = QPushButton("램프 FAULT 해제 (운전자 확인)")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self._on_reset_fault)
        v.addWidget(self.btn_reset)
        v.addStretch(1)
        self._set_controls_enabled(False)
        return g

    def _build_status(self):
        g = QGroupBox("상태")
        v = QVBoxLayout(g)

        row = QHBoxLayout()
        self.lab_mode = _box("모드: —", GREY, size=10)
        self.lab_ramp = _box("램프: —", GREY, size=10)
        self.lab_drive = _box("구동: 금지", GREY, size=10)
        row.addWidget(self.lab_mode)
        row.addWidget(self.lab_ramp)
        row.addWidget(self.lab_drive)
        v.addLayout(row)

        self.lab_ramp_detail = QLabel("—")
        self.lab_ramp_detail.setWordWrap(True)
        v.addWidget(self.lab_ramp_detail)

        self.lab_raw = QLabel("송신 raw: —")
        f = QFont("monospace")
        f.setPointSize(11)
        f.setBold(True)
        self.lab_raw.setFont(f)
        v.addWidget(self.lab_raw)

        self.lab_basis = QLabel("근거: —")
        self.lab_basis.setWordWrap(True)
        self.lab_basis.setStyleSheet(f"color:{GREY};")
        v.addWidget(self.lab_basis)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        v.addWidget(sep)

        self.wheel_view = WheelView()
        v.addWidget(self.wheel_view, 3)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        v.addWidget(sep2)

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
        return g

    def _build_bottom(self):
        h = QHBoxLayout()

        gs = QGroupBox(f"Seer 알람 (1050 폴링 · 읽기 전용)")
        vs = QVBoxLayout(gs)
        self.lab_seer = _box("Seer: 미연결", GREY, size=9)
        self.lst_seer = QListWidget()
        vs.addWidget(self.lab_seer)
        vs.addWidget(self.lst_seer)
        h.addWidget(gs, 4)

        gl = QGroupBox("로그")
        vl = QVBoxLayout(gl)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(500)
        vl.addWidget(self.txt_log)
        h.addWidget(gl, 4)
        return h

    # ── 이벤트 ──────────────────────────────────────────────────────────────
    def _install_shortcuts(self):
        """E-STOP 키를 **애플리케이션 전역 단축키**로 건다.

        `keyPressEvent` 로 두면 포커스를 가진 QPushButton 이 Space 를 먼저 소비한다 —
        실측(QTest): 모드 버튼 포커스 상태에서 Space → E-STOP 미체결 + **직전 주행 지령 재발행**,
        E-STOP 버튼 포커스 상태에서 Space → **E-STOP 해제**. 긴급 시 포커스는 방금 누른 모드
        버튼에 있으므로 이 결함은 최악의 순간에 정확히 반대로 동작한다(리뷰 #C1).

        추가 방어: 모든 조작 버튼에 `NoFocus` 를 걸어 Space 소비 자체를 없애고, 키보드 경로는
        **체결 전용**으로 한다(해제는 마우스 클릭만 — 키 오타로 풀리지 않게).
        """
        sc = QShortcut(QKeySequence(Qt.Key_Space), self)
        sc.setContext(Qt.ApplicationShortcut)
        sc.activated.connect(self._estop_engage_only)
        self._sc_estop = sc
        sc2 = QShortcut(QKeySequence(Qt.Key_Escape), self)
        sc2.setContext(Qt.ApplicationShortcut)
        sc2.activated.connect(lambda: self._on_mode("stop"))
        self._sc_stop = sc2

    def _estop_engage_only(self):
        """키보드 경로 — 체결만 한다. 이미 체결이면 아무 일도 하지 않는다."""
        if self.btn_estop.isChecked():
            return
        self.btn_estop.setChecked(True)
        self._on_estop()

    def _on_estop(self):
        engaged = self.btn_estop.isChecked()
        self.controller.estop(engaged)
        if engaged:
            self.btn_estop.setText("■  E-STOP 작동 중 — 클릭하여 해제")
        else:
            self.btn_estop.setText("■  E-STOP  (Space)")

    def _on_connect(self):
        if self.controller.connected or self._thread is not None:
            return
        if not self.dry_run:
            ok = QMessageBox.question(
                self, "실기 연결 확인",
                "실로봇 CAN relay 제어권을 획득합니다.\n\n"
                "· 이동 구역이 비었습니까?\n"
                "· 하드 E-stop 이 손에 있습니까?\n"
                "· 조향은 홈 부근입니까?\n\n계속할까요?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ok != QMessageBox.Yes:
                return
        self.btn_connect.setEnabled(False)
        self.lab_conn.setText("연결 중…")
        self.lab_conn.setStyleSheet(f"color:white; background:{AMBER}; padding:4px 8px; border-radius:3px;")
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
        if self.dry_run:
            from .sim_bus import SimBus
            return SimBus(logger=self._log)
        from .panda_can_bus import PandaCanBus
        return PandaCanBus(logger=self._log)

    def _on_connected(self, ok: bool, msg: str):
        self.btn_connect.setEnabled(not ok)
        self.btn_disconnect.setEnabled(ok)
        self._set_controls_enabled(ok)
        if ok:
            self.sld_steer.setValue(0)
            self._log("[gui] 연결 완료 — 기본 모드 정지, 조향 홈.")
        else:
            self._log(f"[gui] ⚠ 연결 실패: {msg}")
            QMessageBox.critical(self, "연결 실패", msg)

    def _on_disconnect(self):
        self.controller.disconnect()
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self._set_controls_enabled(False)

    def _on_mode(self, key: str):
        if not self.controller.connected:
            return
        if self.btn_estop.isChecked() and key not in ("stop", "home"):
            self._log("[gui] E-STOP 작동 중 — 주행 모드 전환 거부. 먼저 E-STOP 을 해제하세요.")
            return
        self.controller.set_mode(key)

    def _on_steer_slider(self, val: int):
        self.lab_steer.setText(f"{val:+d}°")
        self.controller.set_steer_slider_deg(float(val))

    def _on_reset_fault(self):
        self.controller.reset_fault()
        self._fault_announced = False
        self.btn_reset.setEnabled(False)

    def _set_controls_enabled(self, on: bool):
        for b in self.mode_buttons.values():
            b.setEnabled(on)
        self.btn_home.setEnabled(on)
        self.sld_steer.setEnabled(on)

    # ── 주기 갱신 ───────────────────────────────────────────────────────────
    def _on_tick(self):
        st = self.controller.tick()
        self._update_conn(st)
        self._update_ramp(st)
        self.wheel_view.set_state(st)
        self._update_table(st)
        self._update_seer()

    def _update_conn(self, st):
        if st["connected"]:
            self.lab_conn.setText("연결됨" + ("  (DRY-RUN)" if self.dry_run else "  (실기)"))
            self.lab_conn.setStyleSheet(f"color:white; background:{GREEN}; padding:4px 8px; border-radius:3px;")
        else:
            self.lab_conn.setText("미연결")
            self.lab_conn.setStyleSheet(f"color:white; background:{GREY}; padding:4px 8px; border-radius:3px;")
        ctrl = st["bus_controlling"]
        if self.dry_run:
            relay = "relay: 시뮬레이터 (판다 무접촉)"
        elif ctrl:
            relay = "relay: intercept ON · auth=PC (Seer 응답은 freeze 펌웨어 소관 — GUI 직접 관측 불가)"
        else:
            relay = "relay: passthrough (Seer 주도)"
        self.lab_relay.setText(relay)

    def _update_ramp(self, st):
        mode = st["mode"]
        self.lab_mode.setText(f"모드: {mode.label}")
        state = st["ramp_state"]
        color = {"SETTLED": GREEN, "RAMPING": AMBER, "FAULT": RED}.get(state, GREY)
        self.lab_ramp.setText(f"램프: {state}  지령 {st['ramp_cmd_deg']:+.1f}° / 목표 {st['ramp_target_deg']:+.1f}°")
        self.lab_ramp.setStyleSheet(f"color:white; background:{color}; padding:4px 8px; border-radius:3px;")
        allowed = st["drive_allowed"] and not st["estop"]
        self.lab_drive.setText("구동: 허용" if allowed else "구동: 금지")
        self.lab_drive.setStyleSheet(
            f"color:white; background:{GREEN if allowed else GREY}; padding:4px 8px; border-radius:3px;")
        detail = st["ramp_detail"] or "—"
        if st["backend_settling"]:
            detail += "   |   backend 정착 게이트 작동(구동 0)"
        self.lab_ramp_detail.setText(detail)
        self.lab_raw.setText(
            f"송신 raw: {st['raw_units']:+6d} units (0.1 rpm)   ≈ {st['raw_mmps']:+.1f} mm/s")
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

    def closeEvent(self, ev):
        """종료 경로에서도 반드시 제어권을 반환한다.

        ⚠ 브링업 워커가 실행 중이면 그것을 먼저 기다려야 한다. 그러지 않으면 `disconnect()` 가
        `backend is None` 으로 조기 반환하고, 그 직후 워커가 브링업을 완주해 **UI 도 E-STOP 도
        없는 상태로 TX 루프가 계속 지령을 송신**한다(리뷰 #H2, 실증됨).
        """
        self._timer.stop()
        if self._thread is not None:
            self._log("[gui] 브링업 진행 중 — 완료를 기다린 뒤 제어권을 반환합니다…")
            self._thread.wait(8000)
            QApplication.processEvents()   # 워커 done 시그널을 소비해 backend 를 공표시킨다
        try:
            self.controller.estop(True)
        except Exception:
            pass
        try:
            self.controller.disconnect()
        except Exception as exc:
            print(f"[gui] ⚠ 종료 중 disconnect 예외: {exc}", flush=True)
        self.seer.stop()
        ev.accept()


def run(dry_run: bool = False, seer_ip: str = DEFAULT_IP) -> int:
    app = QApplication(sys.argv[:1])
    win = MainWindow(dry_run=dry_run, seer_ip=seer_ip)
    win.show()
    return app.exec_()
