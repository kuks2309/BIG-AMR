#!/usr/bin/env python3
"""CAN 트랜스포트 추상화 — 백엔드(socketcan/pcan/mock/panda)를 단일 계약 뒤로 숨긴다.

GUI/PCAN 하드코딩 제거의 핵심(ADR 2026-07-28). DirectDriver·authority 는 이 CanTransport
계약만 알고 백엔드를 모른다. 안전배리어 2종을 계약에 강제:
  · arm()/is_armed — 비무장 상태 send() 는 TransportNotArmed 로 차단(정렬 확정 전 실버스 TX 봉인).
  · preflight()   — lib import·채널·비트레이트 검증(arm 전 LOUD FAIL).
프레임 정본형은 can_protocol.CanFrame(stdlib). python-can 은 백엔드 open() 시점에 lazy import.

⚠ 실로봇: 기본 백엔드는 mock(무-하드웨어). 실 하드웨어 arm 은 caller 의 명시 동작.
"""
import abc
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from can_protocol import CanFrame


class CanTransportError(RuntimeError):
    """백엔드 예외 래핑."""


class TransportNotArmed(RuntimeError):
    """비무장 상태에서 send() 호출 — 안전배리어."""


@dataclass
class PreflightReport:
    ok: bool
    checks: List[Tuple[str, bool, str]] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok

    def summary(self) -> str:
        return "; ".join(f"{n}={'OK' if ok else 'FAIL'}({d})" for n, ok, d in self.checks)


class CanTransport(abc.ABC):
    """CAN 백엔드 공통 계약. 소비자(DirectDriver/authority)는 이 인터페이스만 의존한다.

    수명주기: open() → preflight() → arm() → send()/recv() … → disarm() → shutdown().
    send() 는 arm 게이트를 강제하므로, 정렬 확정 전 실버스 TX 를 런타임에서 차단한다.
    """

    name: str = "abstract"
    supports_rtr: bool = True
    owns_authority: bool = False   # panda 처럼 트랜스포트가 권한을 소유하면 True

    def __init__(self):
        self._armed = False
        self._tap: Optional[Callable[[str, CanFrame], None]] = None

    @property
    def is_armed(self) -> bool:
        return self._armed

    # ── 백엔드가 구현 ──
    @abc.abstractmethod
    def _open(self) -> None: ...

    @abc.abstractmethod
    def _do_send(self, frame: CanFrame) -> None: ...

    @abc.abstractmethod
    def recv(self, timeout: float = 0.1) -> Optional[CanFrame]: ...

    @abc.abstractmethod
    def _shutdown(self) -> None: ...

    # ── 공통 (템플릿) ──
    def open(self) -> "CanTransport":
        self._open()
        return self

    def preflight(self) -> PreflightReport:
        return PreflightReport(True, [("preflight", True, "기본(검사 없음)")])

    def arm(self) -> None:
        """물리-TX 배리어 개방. 실 백엔드는 오버라이드(panda=take). mock 은 로그만."""
        self._armed = True

    def disarm(self) -> None:
        """안전상태 복귀. 실 백엔드는 오버라이드(panda=release/safety_mode 0)."""
        self._armed = False

    def shutdown(self) -> None:
        self._shutdown()

    def send(self, frame: CanFrame) -> None:
        if not self._armed:
            raise TransportNotArmed(f"{self.name}: 비무장 상태 send 차단 (arm() 먼저)")
        if self._tap is not None:
            self._tap(self.name, frame)
        self._do_send(frame)

    def set_frame_tap(self, fn: Optional[Callable[[str, CanFrame], None]]) -> None:
        """선택 훅 — 모든 송신 프레임을 관측(로깅/검증). None 이면 해제."""
        self._tap = fn

    def __enter__(self) -> "CanTransport":
        return self.open()

    def __exit__(self, *exc) -> bool:
        self.disarm()
        self.shutdown()
        return False


class MockTransport(CanTransport):
    """무-하드웨어 정본 검증 트랜스포트 (stdlib). tegra 에서 DirectDriver 전체 결정론 검증.

    send→sent[] 기록(+frame-tap). recv→프로그래밍된 SDO 응답 큐(2단계 정렬용 0x6064 주입).
    arm() 은 로그만(물리 부작용 0). '정렬 확정 전 vel≠0 송출 금지' 회귀테스트의 관측 지점.
    """

    name = "mock"

    def __init__(self, supports_rtr: bool = True, log: Optional[Callable] = None):
        super().__init__()
        self.supports_rtr = supports_rtr
        self.log = log or (lambda *_: None)
        self.sent: List[CanFrame] = []
        self._resp = {}                  # (node,index,sub) -> list[CanFrame]
        self._pending_read: Optional[Tuple[int, int, int]] = None
        self._opened = False

    def _open(self) -> None:
        self._opened = True

    def _shutdown(self) -> None:
        self._opened = False

    def arm(self) -> None:
        self._armed = True
        self.log("[mock] arm (물리 부작용 없음)")

    def _do_send(self, frame: CanFrame) -> None:
        self.sent.append(frame)
        d = frame.data
        # SDO upload 요청(0x40) 이면 이후 recv 가 응답할 대상으로 기록
        if 0x600 <= frame.arb_id <= 0x67F and len(d) >= 4 and d[0] == 0x40:
            self._pending_read = (frame.arb_id - 0x600, d[1] | (d[2] << 8), d[3])

    def recv(self, timeout: float = 0.1) -> Optional[CanFrame]:
        pr = self._pending_read
        if pr is not None:
            self._pending_read = None
            q = self._resp.get(pr)
            if q:
                return q.pop(0)
        time.sleep(min(timeout, 0.005))  # L1: sdo_read 폴 busy-spin 완화 (테스트 CPU 부하↓)
        return None

    def program_sdo_read(self, node: int, index: int, value: int, sub: int = 0) -> None:
        """SDO upload 응답(0x43=4바이트)을 큐잉 — 다음 sdo_read(node,index,sub) 가 이 값을 받는다."""
        data = bytes([0x43, index & 0xFF, (index >> 8) & 0xFF, sub]) + (value & 0xFFFFFFFF).to_bytes(4, "little")
        self._resp.setdefault((node, index, sub), []).append(CanFrame(arb_id=0x580 + node, data=data))

    # ── 검증 편의 ──
    def sent_ids(self):
        return sorted({f.arb_id for f in self.sent})

    def drive_velocity_frames(self):
        """구동 속도(0x60FF) 송신 프레임의 (node, value) 목록 — 정렬 전 vel≠0 단언용."""
        out = []
        for f in self.sent:
            d = f.data
            if 0x601 <= f.arb_id <= 0x602 and len(d) >= 8 and d[0] == 0x23 and d[1] == 0xFF and d[2] == 0x60:
                out.append((f.arb_id - 0x600, int.from_bytes(d[4:8], "little", signed=True)))
        return out


class PythonCanTransport(CanTransport):
    """python-can 백엔드 공통 (socketcan/pcan/virtual). open() 시점 lazy import 로 tegra 미설치 흡수.

    CanFrame↔can.Message 변환은 원본 인코딩과 바이트 동일(dlc/RTR/is_extended 라운드트립 보존).
    arm() 은 socketcan/pcan 에 물리 TX 배리어가 없으므로 플래그만 세운다(preflight 가 채널 가드).
    """

    def __init__(self, interface: str, channel: str, bitrate: int = 250000,
                 receive_own_messages: bool = False):
        super().__init__()
        self.name = interface
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate
        self._rom = receive_own_messages
        self._bus = None
        self._can = None

    def _open(self) -> None:
        try:
            import can
        except Exception as e:
            raise CanTransportError(f"python-can import 실패({self.interface}): {e}")
        self._can = can
        try:
            self._bus = can.Bus(channel=self.channel, interface=self.interface,
                                receive_own_messages=self._rom)
        except Exception as e:
            raise CanTransportError(f"{self.interface}:{self.channel} open 실패: {e}")

    def _to_msg(self, frame: CanFrame):
        return self._can.Message(arbitration_id=frame.arb_id, data=frame.data,
                                 is_remote_frame=frame.is_remote, is_extended_id=frame.is_extended,
                                 dlc=frame.effective_dlc())

    @staticmethod
    def _from_msg(m) -> CanFrame:
        return CanFrame(arb_id=m.arbitration_id, data=bytes(m.data),
                        is_remote=getattr(m, "is_remote_frame", False),
                        is_extended=m.is_extended_id, dlc=m.dlc)

    def _do_send(self, frame: CanFrame) -> None:
        try:
            self._bus.send(self._to_msg(frame))
        except Exception as e:
            raise CanTransportError(f"{self.name} send 실패: {e}")

    def recv(self, timeout: float = 0.1) -> Optional[CanFrame]:
        m = self._bus.recv(timeout=timeout)
        return self._from_msg(m) if m is not None else None

    def _shutdown(self) -> None:
        if self._bus is not None:
            try:
                self._bus.shutdown()
            finally:
                self._bus = None

    def preflight(self) -> PreflightReport:
        checks: List[Tuple[str, bool, str]] = []
        try:
            import can
            checks.append(("python-can", True, getattr(can, "__version__", "설치됨")))
        except Exception as e:
            checks.append(("python-can", False, str(e)))
            return PreflightReport(False, checks)
        if self.interface == "socketcan":
            import os
            up = os.path.isdir(f"/sys/class/net/{self.channel}")
            checks.append((f"iface {self.channel}", up, "존재" if up else "없음(ip link 확인)"))
        checks.append(("bitrate", self.bitrate == 250000, str(self.bitrate)))  # 판다 부팅 250k 정정 이력
        return PreflightReport(all(ok for _, ok, _ in checks), checks)


def open_transport(spec: str, **kw) -> CanTransport:
    """트랜스포트 팩토리. spec 예: 'mock' · 'socketcan:can1' · 'pcan:PCAN_USBBUS1'.

    panda 백엔드는 Phase 6-9(별도 승인·HIL) — 여기서는 미지원(명시 에러).
    """
    kind, _, arg = spec.partition(":")
    if kind == "mock":
        return MockTransport(**kw)
    if kind == "socketcan":
        return PythonCanTransport("socketcan", arg or "can1", **kw)
    if kind == "pcan":
        return PythonCanTransport("pcan", arg or "PCAN_USBBUS1", **kw)
    if kind == "panda":
        raise CanTransportError("panda 백엔드는 Phase 6-9(HIL 승인 게이트) — 아직 미배선")
    raise CanTransportError(f"알 수 없는 트랜스포트 spec: {spec!r}")


if __name__ == "__main__":
    # 무-하드웨어 스모크: mock 왕복 + arm 게이트
    t = open_transport("mock").open()
    from can_protocol import sdo_write, sdo_read
    try:
        t.send(sdo_write(1, 0x60FF, 0))
        print("FAIL: 비무장 send 가 통과함")
    except TransportNotArmed:
        print("OK: 비무장 send 차단")
    t.arm()
    t.send(sdo_write(1, 0x60FF, 0))
    t.program_sdo_read(3, 0x6064, 7871815)
    print("sdo_read(mock) =", sdo_read(t, 3, 0x6064))
    print("sent ids =", [hex(i) for i in t.sent_ids()])
