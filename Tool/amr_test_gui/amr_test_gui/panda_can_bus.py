"""PandaCanBus — python-can 호환 어댑터. motor_control backend 를 판다 relay 경유로 구동한다.

승격 이력: 2026-07-27 세션 scratchpad 에서 git 으로 승격(소실 방지, ADR 2026-07-27-amr-test-gui §2).
원본 동작은 보존하고 진단 카운터·명시 로깅만 추가했다.

제어권 프로토콜(실측 확정):
  take    = safety_mode 30(SEER_GATE) + CAN0/2 enable(250 kbps) + 0xe9=1(auth=PC) + 0xe8=1(intercept)
            + heartbeat 0.4 s(0xf3)
  release = 0xe9=0(auth=Seer) + 0xe8=0(passthrough) + safety_mode 0

heartbeat 상실 시 실제 거동 (2026-07-27 펌웨어 소스 확인 후 정정 — 종전 서술은 틀렸다):
  펌웨어는 `SAFETY_SILENT` 로 되돌린다(`board/main.c` heartbeat 블록). "passthrough 안전모드로
  전환"되는 것이 아니다. 다만 하네스 릴레이가 부팅 기본으로 **물리 통과**이므로(`drivers/harness.h:91`
  "keep busses connected by default") Seer↔모터 버스 자체는 끊기지 않는다.
  2026-07-27 펌웨어 수정으로 같은 블록에 `set_intercept_relay(false)` + `pc_authority=false` 를
  추가해, 이상 상태에서 릴레이가 intercept 로 남지 않도록 했다(fail-open).
  ADR: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md

⚠ `set_can_speed_kbps(b, 250)` 는 펌웨어 기본값이 250 kbps 로 정정된 뒤에도 **계속 호출한다**
  (방어적 명시). 종전 펌웨어는 500 kbps 로 부팅해 250 kbps 버스를 파괴했고, 호스트가 이 호출을
  하기 때문에 그 결함이 가려져 있었다.

버스 배선: CAN0=Seer, CAN2=모터 (Tool/docking_field_kit/PINMAP.md).
send(): PC 원발 SDO → CAN2. recv(): CAN2 응답만 반환.
RTR(guard) 은 판다가 송신 불가라 skip — intercept 중 Seer guard 가 게이트로 forward 되어 모터
Node Guarding 을 유지한다는 가정에 의존한다(⚠ debt-006, 미검증).
"""
from __future__ import annotations

import os
import sys
import threading
import time
from types import SimpleNamespace

# panda 라이브러리 경로 — 레포 내장본 우선(재현성), 없으면 개발 PC 킷으로 폴백.
_REPO_KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "docking_field_kit")
_HOME_KIT = os.path.expanduser("~/Project/CAN-Relay/docking_field_kit")


def _panda_class():
    for kit in (os.path.normpath(_REPO_KIT), _HOME_KIT):
        if os.path.isdir(os.path.join(kit, "panda")):
            if kit not in sys.path:
                sys.path.insert(0, kit)
            from panda import Panda
            return Panda
    raise ImportError(f"panda 라이브러리를 찾지 못했습니다 (탐색: {_REPO_KIT}, {_HOME_KIT})")


MOTOR_BUS, SEER_BUS = 2, 0
SEER_GATE = 30
CAN_KBPS = 250
HEARTBEAT_S = 0.4


class PandaCanBus:
    """python-can Bus 호환: send(msg) / recv(timeout) / shutdown().

    생성자가 제어권을 취득한다(take). 예외 발생 시 부분 취득 상태를 남기지 않도록 release 후 재raise.
    """

    def __init__(self, logger=print):
        self.log = logger
        Panda = _panda_class()
        self._Panda = Panda
        self.p = Panda()
        self._running = True
        self._rxbuf: list = []
        self.tx_errors = 0
        self.rx_errors = 0
        self.hb_errors = 0
        self.controlling = False
        try:
            self._take()
        except Exception:
            self._running = False
            try:
                self.p.close()
            except Exception:
                pass
            raise
        self._hb = threading.Thread(target=self._heartbeat, daemon=True, name="panda-hb")
        self._hb.start()

    # ── 제어권 ──────────────────────────────────────────────────────────────
    def _take(self):
        p, Panda = self.p, self._Panda
        p.set_safety_mode(SEER_GATE, 0)
        for b in (SEER_BUS, MOTOR_BUS):
            p.set_can_speed_kbps(b, CAN_KBPS)
            p.set_can_enable(b, True)
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")   # auth=PC 먼저
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")   # intercept ON
        self.controlling = True
        self.log("[PandaCanBus] 제어권 획득 (safety=30 SEER_GATE, auth=PC, intercept). CAN2=모터.")

    def _heartbeat(self):
        Panda = self._Panda
        while self._running:
            try:
                self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")
            except Exception:
                self.hb_errors += 1
            time.sleep(HEARTBEAT_S)

    # ── python-can 호환 표면 ────────────────────────────────────────────────
    def send(self, msg):
        if getattr(msg, "is_remote_frame", False):
            return  # 판다 RTR 송신 불가 — Seer guard 가 forward 되어 모터 유지 (debt-006)
        try:
            self.p.can_send(msg.arbitration_id, bytes(msg.data), MOTOR_BUS)
        except Exception:
            self.tx_errors += 1

    def recv(self, timeout: float = 0.1):
        if not self._rxbuf:
            deadline = time.time() + timeout
            while time.time() < deadline and self._running:
                try:
                    for addr, _ts, dat, bus in self.p.can_recv():
                        if bus == MOTOR_BUS:
                            self._rxbuf.append(SimpleNamespace(
                                arbitration_id=addr, data=bytes(dat), is_remote_frame=False))
                except Exception:
                    self.rx_errors += 1
                if self._rxbuf:
                    break
                time.sleep(0.001)
        return self._rxbuf.pop(0) if self._rxbuf else None

    def shutdown(self):
        """release(제어권 반환) 후 close. 중복 호출 무해."""
        if not self._running and not self.controlling:
            return
        self._running = False
        Panda = self._Panda
        try:
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
            self.p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # passthrough
            self.p.set_safety_mode(0, 0)
        except Exception:
            self.log("[PandaCanBus] ⚠ release 제어전송 실패 — heartbeat 소실로 판다 fail-safe 복귀 예정")
        self.controlling = False
        time.sleep(0.2)
        try:
            self.p.close()
        except Exception:
            pass
        self.log("[PandaCanBus] release(제어권 반환, passthrough) + close.")
