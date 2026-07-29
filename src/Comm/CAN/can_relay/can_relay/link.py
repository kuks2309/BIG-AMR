#!/usr/bin/env python3
"""판다 릴레이 전송 계층 — 주도권 획득·heartbeat·CAN 송수신.

## 왜 판다 경유인가

이 로봇에서 모터 버스에 접근하는 길은 두 가지이고, 둘은 **안전 모델이 서로
배타적**이다:

| | socketcan 직결 | 판다 릴레이(본 모듈) |
|---|---|---|
| Seer | 물리 분리 필수 | 연결 필수 |
| 정지 근간 | guard RTR 20 Hz 중단 → 500 ms HALT | heartbeat 상실 → 펌웨어가 0x60FF=0 후 릴레이 개방 |
| RTR 송신 | 가능 | **불가**(판다 CAN 패킷 헤더에 RTR 비트가 없다) |

즉 판다 경유에서는 **PC 가 guard 를 끊어 정지시킬 수 없다.** 정지는 펌웨어
fail-safe 에 위임되며, 그것을 살려 두는 유일한 수단이 heartbeat 다(아래).

## heartbeat 계약 (가장 중요)

`Panda.set_safety_mode()` 의 기본값은 `disable_checks=True` 이고, 이는 `0xf8`
(heartbeat 검사 해제)을 보낸다. 그 상태에서는 펌웨어 fail-safe 블록 전체가
`if (!heartbeat_disabled)` 에 막혀 **동작하지 않는다** — PC 가 죽어도 릴레이가
intercept 로 남고 모터가 방치된다.

`0xf3` 을 보내면 검사가 **되살아난다.** 그 뒤로는 1.0~2.0 s 안에 다음 심박이
반드시 도착해야 하며, 늦으면 펌웨어가 구동 0 → 릴레이 개방 → 재engage 래치를
건다(래치 해제는 `0xe9` 재전송뿐).

따라서 본 모듈은 **heartbeat 를 켜고 유지하는 쪽**을 택한다. 심박 유지 실패는
숨기지 않고 `on_fault` 로 올린다.

⚠ heartbeat 를 별도 스레드에서 보내면 폴링과 USB 핸들을 경합해 실패한 이력이
있다. 그래서 여기서는 **송수신과 같은 스레드에서 인터리브**한다(별도 스레드 없음).
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, Iterable, Optional

from . import protocol as P

# ── 판다 계약 상수 ────────────────────────────────────────────────────────
SEER_BUS = 0            # Seer 측
MOTOR_BUS = 2           # 드라이브 측
SAFETY_SEER_GATE = 30   # 유일하게 릴레이를 강제 전환하지 않는 safety_mode
CAN_KBPS = 250          # 부팅 기본값과 동일. ⚠ 500k 로 덮으면 버스가 죽는다

REQ_AUTHORITY = 0xE9    # wValue: 0=Seer 주도 · 1=PC 주도(재engage 래치도 해제)
REQ_INTERCEPT = 0xE8    # wValue: 0=passthrough · 1=intercept(+300 ms 전환 커버)
REQ_HEARTBEAT = 0xF3    # 보내면 fail-safe 검사가 되살아난다

HEARTBEAT_PERIOD_S = 0.2    # 펌웨어 임계 1.0~2.0 s 대비 5~10배 여유
HEARTBEAT_DEADLINE_S = 0.8  # 이 이상 못 보내면 fail-safe 가 임박한 것으로 본다

_KIT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))),
    "Tools", "docking_field_kit")


def _panda_module():
    """comma.ai panda 라이브러리(필드킷 동봉본) 로드."""
    if _KIT not in sys.path:
        sys.path.insert(0, _KIT)
    from panda import Panda  # noqa: WPS433 - 선택적 의존성
    return Panda


class LinkError(RuntimeError):
    """전송 계층 실패. 호출부는 이것을 받으면 정지 경로로 가야 한다."""


class BaseLink:
    """전송 계층 인터페이스. 구현체는 PandaLink 와 MockLink 둘이다."""

    def open(self) -> None:
        raise NotImplementedError

    def acquire(self) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError

    def send(self, frames: Iterable[P.Frame]) -> None:
        raise NotImplementedError

    def recv(self) -> list[tuple[int, bytes, int]]:
        raise NotImplementedError

    def heartbeat(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    @property
    def engaged(self) -> bool:
        raise NotImplementedError


class MockLink(BaseLink):
    """하드웨어 없는 대역. 보낸 프레임을 기록하고 미리 넣어 둔 응답을 돌려준다.

    실기 없이 안전 게이트·시퀀스·워치독을 전량 회귀 시험하기 위한 것이다.
    """

    def __init__(self):
        self.sent: list[P.Frame] = []
        self.inbox: list[tuple[int, bytes, int]] = []
        self.heartbeats = 0
        self.opened = False
        self._engaged = False
        self.log: list[str] = []

    def open(self):
        self.opened = True
        self.log.append("open")

    def acquire(self):
        if not self.opened:
            raise LinkError("USB 미개방 상태에서 제어권을 요청했다")
        self._engaged = True
        self.log.append("acquire")

    def release(self):
        self._engaged = False
        self.log.append("release")

    def send(self, frames):
        for f in frames:
            if not self._engaged:
                raise LinkError("제어권 없이 프레임을 보내려 했다")
            self.sent.append(f)

    def recv(self):
        out, self.inbox = self.inbox, []
        return out

    def heartbeat(self):
        self.heartbeats += 1

    def close(self):
        self._engaged = False
        self.opened = False
        self.log.append("close")

    @property
    def engaged(self) -> bool:
        return self._engaged


class PandaLink(BaseLink):
    """실제 comma.ai panda 를 통한 전송.

    수명주기는 3단계로 **분리**한다 — 이 분리가 안전 장치다.
      1. `open()`   USB 만 연다. safety_mode 를 건드리지 않으므로 모터에 무영향.
      2. `acquire()` 제어권 획득. 여기서부터 Seer 대신 PC 가 버스를 쓴다.
      3. `release()` 반환. **반환 전에 호출부가 반드시 정지를 보내야 한다.**
    """

    def __init__(self, serial: Optional[str] = None,
                 log: Optional[Callable[[str], None]] = None):
        self._serial = serial
        self._log = log or (lambda _m: None)
        self._panda = None
        self._cls = None
        self._engaged = False
        self._lock = threading.Lock()
        self._last_hb = 0.0

    # ── 수명주기 ──────────────────────────────────────────────────────
    def open(self):
        self._cls = _panda_module()
        try:
            serials = self._cls.list()
        except Exception as exc:                       # pragma: no cover - 실기 전용
            raise LinkError(f"판다 열거 실패: {type(exc).__name__}: {exc}") from exc
        if not serials:
            raise LinkError("판다를 찾지 못했다 (USB 연결·udev 규칙 확인)")
        if self._serial is None and len(serials) > 1:
            raise LinkError(
                f"판다가 {len(serials)}대 보인다 {serials} — serial 파라미터로 "
                f"명시하지 않으면 어느 쪽에 지령이 갈지 알 수 없다")
        try:
            self._panda = self._cls(self._serial) if self._serial else self._cls()
            health = self._panda.health()
        except Exception as exc:                       # pragma: no cover - 실기 전용
            raise LinkError(f"판다 개방 실패: {type(exc).__name__}: {exc}") from exc
        self._log(f"판다 개방 — health={health}")

    def acquire(self):
        """제어권 획득. `gui.py:796-806` 의 실기 검증 순서를 그대로 따른다.

        순서가 곧 사양이다: safety_mode → 버스속도 → 버스 enable → auth →
        intercept → heartbeat. auth(0xe9)가 intercept(0xe8)보다 **먼저**여야
        재engage 래치가 걸려 있을 때 intercept 가 조용히 무시되지 않는다.
        """
        if self._panda is None:
            raise LinkError("USB 미개방 상태에서 제어권을 요청했다")
        P_ = self._cls
        try:
            self._panda.set_safety_mode(SAFETY_SEER_GATE, 0)
            for bus in (SEER_BUS, MOTOR_BUS):
                self._panda.set_can_speed_kbps(bus, CAN_KBPS)
                self._panda.set_can_enable(bus, True)
            self._ctrl(P_, REQ_AUTHORITY, 1)
            self._ctrl(P_, REQ_INTERCEPT, 1)
        except Exception as exc:
            # 중간 실패 시 어중간한 상태(auth 만 선 상태 등)로 두지 않는다.
            self._log(f"제어권 획득 실패 — 롤백: {type(exc).__name__}: {exc}")
            self._rollback()
            raise LinkError(f"제어권 획득 실패: {type(exc).__name__}: {exc}") from exc
        self._engaged = True
        # 획득 직후 즉시 심박을 보내 펌웨어 fail-safe 를 켠다.
        # (set_safety_mode 가 disable_checks=True 로 0xf8 을 보내 꺼 두었다.)
        self.heartbeat()
        self._log("제어권 획득 — intercept, fail-safe 무장")

    def release(self):
        """제어권 반환. 호출부는 **이 함수 호출 전에 정지를 보내야 한다.**"""
        if self._panda is None:
            return
        self._rollback()
        self._engaged = False
        self._log("제어권 반환 — passthrough")

    def _rollback(self):
        P_ = self._cls
        for req, val in ((REQ_INTERCEPT, 0), (REQ_AUTHORITY, 0)):
            try:
                self._ctrl(P_, req, val)
            except Exception as exc:                   # pragma: no cover - 실기 전용
                self._log(f"롤백 중 0x{req:02x} 실패: {type(exc).__name__}: {exc}")
        try:
            self._panda.set_safety_mode(0, 0)          # SILENT
        except Exception as exc:                       # pragma: no cover - 실기 전용
            self._log(f"롤백 중 SILENT 실패: {type(exc).__name__}: {exc}")

    def close(self):
        if self._panda is not None:
            try:
                self._panda.close()
            except Exception:                          # pragma: no cover - 실기 전용
                pass
        self._panda = None
        self._engaged = False

    # ── 입출력 ────────────────────────────────────────────────────────
    def _ctrl(self, P_, request: int, value: int):
        self._panda._handle.controlWrite(P_.REQUEST_OUT, request, value, 0, b"")

    def heartbeat(self):
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 heartbeat")
        self._ctrl(self._cls, REQ_HEARTBEAT, 0)
        self._last_hb = time.monotonic()

    def heartbeat_overdue(self, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        return (now - self._last_hb) > HEARTBEAT_DEADLINE_S

    def send(self, frames):
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 송신")
        if not self._engaged:
            raise LinkError("제어권 없이 프레임을 보내려 했다")
        with self._lock:
            for f in frames:
                self._panda.can_send(f.can_id, f.data[:8], f.bus)

    def recv(self):
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 수신")
        with self._lock:
            raw = self._panda.can_recv()
        return [(addr, bytes(dat), bus) for addr, _ts, dat, bus in raw]

    @property
    def engaged(self) -> bool:
        return self._engaged
