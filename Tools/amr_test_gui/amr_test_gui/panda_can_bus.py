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

버스 배선: CAN0=Seer, CAN2=모터 (Tools/docking_field_kit/PINMAP.md).
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


class PandaLink:
    """판다 **USB 연결만** 담당한다 — 제어권은 절대 건드리지 않는다.

    분리 이유(사용자 지시 2026-07-27 "먼저 usb 로 판다 연결 메뉴가 있어야 함"):
    한 버튼이 'USB 열기'와 '제어권 탈취'를 동시에 하면, 운전자가 판다가 붙었는지·펌웨어가
    무엇인지·CAN 오류가 있는지 **보기도 전에 릴레이를 뺏게 된다.** 두 동작은 위험도가 전혀 다르다.

    안전 근거: `Panda.__init__` 은 `connect()` + `get_mcu_type()` 만 수행하고 safety mode 를
    바꾸지 않는다(Tools/docking_field_kit/panda/python/__init__.py:204-208
    `def __init__(self, serial=None, claim: bool = True): … self.connect(claim);
    self._mcu_type = self.get_mcu_type()` 로 확인 — 이 부분은 정확하다).
    따라서 본 클래스만으로는 릴레이·모터에 아무 영향이 없다.

    ⚠ 2026-07-27 정정 — 원문 ~~"`claim=False` 로 USB 인터페이스 점유도 최소화한다."~~ 는 반증됐다:
    본 클래스의 `open()` 기본값이 `claim: bool = True`(아래 :80)이고, 유일한 호출부
    ui_main.py:387 은 `st = self.link.open()` 로 인자 없이 호출한다 → 실제로는 **claim=True 로
    USB 인터페이스를 점유한다**. claim=False 최소점유는 **미적용** 상태다.
    (기본값 변경은 USB 점유 동작 변경이므로 별도 검증 후 결정 — 여기서는 서술만 정정한다.)
    """

    def __init__(self, logger=print):
        self.log = logger
        self.p = None
        self._Panda = None
        self.error = ""

    @property
    def is_open(self) -> bool:
        return self.p is not None

    def open(self, claim: bool = True) -> dict:
        """USB 연결 후 상태를 돌려준다. 실패 시 예외."""
        if self.p is not None:
            return self.status()
        self._Panda = _panda_class()
        self.p = self._Panda(claim=claim)
        self.error = ""
        st = self.status()
        self.log(f"[PandaLink] USB 연결 — fw={st.get('version')} "
                 f"safety_mode={st.get('safety_mode')} harness={st.get('car_harness_status')}")
        return st

    def status(self) -> dict:
        """health + version. 제어권 변경 없음. 미연결이면 빈 dict."""
        if self.p is None:
            return {}
        try:
            h = dict(self.p.health())
            try:
                h["version"] = str(self.p.get_version())
            except Exception:
                h["version"] = "?"
            return h
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            return {"error": self.error}

    def block_seer_homing(self, on: bool) -> bool:
        """Seer 의 호밍 트리거(0x60FB.4=1 · 0x6098) 차단 on/off — 펌웨어 0xec.

        제어권을 반환하면 Seer 가 자기 초기화로 호밍을 걸어 조향축이 137° 왕복한다.
        테스트 도구를 쓰는 동안에는 이걸 막는다. 호밍은 '호밍' 버튼으로만 명시적으로 한다.
        ⚠ 가짜 ack 를 주므로 Seer 는 호밍이 된 줄 안다 — 도구 종료 시 반드시 해제한다.
        """
        if self.p is None:
            return False
        try:
            r = self.p._handle.controlRead(self._Panda.REQUEST_IN, 0xec, 1 if on else 0, 0, 1)
            got = bool(r and r[0] == 1)
            self.log(f"[PandaLink] Seer 호밍 트리거 차단 {'ON' if got else 'OFF'}")
            return got
        except Exception as exc:
            self.log(f"[PandaLink] ⚠ 0xec 실패(구 펌웨어?): {type(exc).__name__}: {exc}")
            return False

    # ── 펌웨어 조향 호밍 (0xea 개시/중단 · 0xeb 상태) ──────────────────────
    # 호밍은 **펌웨어가 지휘**한다(board/safety/safety_seer_gate.h 의 시퀀서).
    # 호밍 = 원점(리밋) 탐색 → 조향 0° 복귀까지. 원점에 머무는 것이 아니다.
    # 펌웨어 인터록: pc_authority(0xe9=1) + safety_mode 30 이어야 개시가 수락된다.
    HOMING_STATE = {0: "대기", 1: "enable", 2: "속도설정", 3: "개시", 4: "원점 탐색 중",
                    5: "완료 (조향 0°)", 6: "실패: 탐색 타임아웃", 7: "실패: 중단",
                    8: "프로파일 복원", 9: "0° 지령", 10: "실패: 0° 복귀 불가", 11: "0° 복귀 중"}
    HOMING_TERMINAL = (0, 5, 6, 7, 10)

    def homing_start(self, speed: int = 0) -> bool:
        """호밍 개시. 반환 False = 펌웨어가 거부(권한 없음·이미 진행중)."""
        if self.p is None:
            return False
        r = self.p._handle.controlRead(self._Panda.REQUEST_IN, 0xea, 1, int(speed), 1)
        return bool(r and r[0] == 1)

    def homing_abort(self) -> None:
        if self.p is None:
            return
        self.p._handle.controlRead(self._Panda.REQUEST_IN, 0xea, 0, 0, 1)

    def homing_status(self) -> dict:
        """{state, text, done_mask, reached_mask, elapsed_s, di3, di4, terminal}."""
        if self.p is None:
            return {}
        r = self.p._handle.controlRead(self._Panda.REQUEST_IN, 0xeb, 0, 0, 8)
        if not r or len(r) < 8:
            return {}
        st = r[0]
        return {"state": st, "text": self.HOMING_STATE.get(st, f"?({st})"),
                "done_mask": r[1], "seen_active": r[2],
                "elapsed_s": r[3] | (r[4] << 8),
                "di3": r[5], "di4": r[6], "reached_mask": r[7],
                "terminal": st in self.HOMING_TERMINAL}

    def close(self):
        p, self.p = self.p, None
        if p is None:
            return
        try:
            p.close()
        except Exception:
            pass
        self.log("[PandaLink] USB 연결 해제.")


class PandaCanBus:
    """python-can Bus 호환: send(msg) / recv(timeout) / shutdown().

    생성자가 제어권을 취득한다(take). 예외 발생 시 부분 취득 상태를 남기지 않도록 release 후 재raise.
    `link` 를 주면 그 USB 연결을 재사용하고 **USB 핸들은 닫지 않는다**(link 소유) —
    제어권을 반환한 뒤에도 판다 상태를 계속 볼 수 있어야 하기 때문.
    """

    def __init__(self, logger=print, link: "PandaLink | None" = None):
        self.log = logger
        self._link = link
        if link is not None and link.is_open:
            self._Panda = link._Panda
            self.p = link.p
            self._owns_usb = False
        else:
            self._Panda = _panda_class()
            self.p = self._Panda()
            self._owns_usb = True
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
            # take 실패 시에도 **USB 연결은 link 소유면 살려 둔다** — 운전자가 판다 상태를
            # 계속 보며 원인을 판단해야 한다. 우리가 연 경우에만 닫는다.
            if self._owns_usb:
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
        if self._owns_usb:
            try:
                self.p.close()
            except Exception:
                pass
            self.log("[PandaCanBus] release(제어권 반환, passthrough) + USB close.")
        else:
            # USB 는 PandaLink 소유 — 제어권만 반환하고 연결은 유지한다(상태 계속 관측).
            self.log("[PandaCanBus] release(제어권 반환, passthrough). USB 연결은 유지.")
