#!/usr/bin/env python3
"""CAN relay 판다 펌웨어 플래시 GUI (뷰 계층) — DFU/앱 자동 감지, 검증본 플래시.

UI 분리: 감지·경로·argv 구성 로직은 `flash_backend.py`, 이 파일은 위젯·상호작용만.
플래시 로직은 재구현 없이 검증된 스크립트를 subprocess(QProcess)로 호출·스트리밍한다.

어느 폴더에서든 실행 가능(경로는 `__file__` 기준 절대):
    python3 /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/Can_Relay/ui/flash_gui.py
"""
import os
import sys

from PyQt5.QtGui import QFont
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QFileDialog, QMessageBox, QProgressBar,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))          # flash_backend 임포트용
import flash_backend as fb                                              # noqa: E402 (경로 주입 후)


class FlashGui(QWidget):
    def __init__(self):
        super().__init__()
        self.proc = None
        self.mode = "none"
        self.setWindowTitle("CAN relay 펌웨어 플래시")
        self.resize(680, 460)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)

        # 상태 줄
        row = QHBoxLayout()
        self.status = QLabel("감지 중…")
        f = self.status.font(); f.setBold(True); f.setPointSize(f.pointSize() + 1)
        self.status.setFont(f)
        self.btn_refresh = QPushButton("↻ 다시 감지")
        self.btn_refresh.clicked.connect(self.refresh)
        row.addWidget(self.status, 1)
        row.addWidget(self.btn_refresh)
        root.addLayout(row)

        self.detail = QLabel("")
        self.detail.setStyleSheet("color:#555")
        root.addWidget(self.detail)

        # 펌웨어 파일
        fwrow = QHBoxLayout()
        fwrow.addWidget(QLabel("펌웨어:"))
        self.fw = QLineEdit(fb.DEFAULT_FW)
        self.btn_browse = QPushButton("찾아보기…")
        self.btn_browse.clicked.connect(self._browse)
        fwrow.addWidget(self.fw, 1)
        fwrow.addWidget(self.btn_browse)
        root.addLayout(fwrow)

        # 동작 버튼
        brow = QHBoxLayout()
        self.btn_flash = QPushButton("플래시")
        self.btn_flash.clicked.connect(self._flash)
        self.btn_recover = QPushButton("DFU 복구 (부트스텁 갇힘)")
        self.btn_recover.clicked.connect(self._recover)
        brow.addWidget(self.btn_flash, 2)
        brow.addWidget(self.btn_recover, 1)
        root.addLayout(brow)

        # 진행 막대 — 불확정(busy): 실행 중 좌우로 이동, 유휴 0% / 완료 100%
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)

        # 로그
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("monospace", 9))
        root.addWidget(self.log, 1)

    # ---- 상태 ----
    def refresh(self):
        self.mode, detail = fb.detect()
        text, color = fb.MODE_TEXT.get(self.mode, ("?", "#000"))
        self.status.setText(f"감지: {text}")
        self.status.setStyleSheet(f"color:{color}")
        self.detail.setText(detail)
        busy = self.proc is not None
        self.btn_flash.setEnabled(self.mode in ("dfu", "app") and not busy)
        self.btn_recover.setEnabled(not busy)
        self.btn_refresh.setEnabled(not busy)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "펌웨어 선택", os.path.dirname(self.fw.text()) or fb.ROOT,
            "signed bin (*.signed *.bin);;모든 파일 (*)")
        if path:
            self.fw.setText(path)

    # ---- 실행 ----
    def _flash(self):
        fw = self.fw.text().strip()
        if not os.path.isfile(fw):
            QMessageBox.warning(self, "펌웨어 없음", f"파일이 없다:\n{fw}")
            return
        warn = ""
        if self.mode == "app":
            warn = ("\n\n⚠ 이미 앱으로 부팅 중인 보드다. DFU 강제핀이 SET 된 보드라면 통상 "
                    "flash 가 부트스텁에 가둘 수 있다 — 그 경우 'DFU 복구' 후 다시 시도.")
        if QMessageBox.question(
                self, "플래시 확인",
                f"모드: {fb.MODE_TEXT[self.mode][0]}\n펌웨어: {fw}\n\n플래시할까?{warn}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._run(fb.flash_argv(fw))

    def _recover(self):
        if QMessageBox.question(
                self, "DFU 복구", "판다를 DFU(부트스텁)로 밀어넣는다. 계속?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._run(fb.recover_argv())

    def _run(self, argv):
        if self.proc is not None:
            return
        self.log.appendPlainText(f"$ {' '.join(argv)}\n")
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.setWorkingDirectory(fb.ROOT)
        self.proc.readyReadStandardOutput.connect(self._on_output)
        self.proc.finished.connect(self._on_done)
        self.progress.setRange(0, 0)            # 불확정(busy) — 실행 중 이동
        self.refresh()                          # 버튼 잠금
        self.proc.start(argv[0], argv[1:])

    def _on_output(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(data)
        self.log.moveCursor(self.log.textCursor().End)

    def _on_done(self, code, _status):
        self.log.appendPlainText(f"\n[종료 코드 {code}]  "
                                 + ("성공" if code == 0 else "실패/재확인") + "\n")
        self.proc = None
        self.progress.setRange(0, 1)            # 정지 — 완료(100%) / 유휴(0%)
        self.progress.setValue(1 if code == 0 else 0)
        self.refresh()


def main():
    app = QApplication(sys.argv)
    gui = FlashGui()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
