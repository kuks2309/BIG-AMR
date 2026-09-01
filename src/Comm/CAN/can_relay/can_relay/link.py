#!/usr/bin/env python3
"""판다 릴레이 전송 계층 — 주도권 획득·heartbeat·CAN 송수신.

## 왜 판다 경유인가

모터 버스에 접근하는 길은 두 가지이고 둘은 **안전 모델이 서로 배타적**이다:

| | socketcan 직결 | 판다 릴레이(본 모듈) |
|---|---|---|
| Seer | 물리 분리 필수 | 연결 필수 |
| 정지 근간 | guard RTR 20 Hz 중단 → 500 ms HALT | heartbeat 상실 → 펌웨어가 0x60FF=0 후 릴레이 개방 |
| RTR 송신 | 가능 | **불가**(판다 CAN 패킷 헤더에 RTR 비트가 없다) |

즉 판다 경유에서는 **PC 가 guard 를 끊어 정지시킬 수 없다.** 정지는 펌웨어 fail-safe 에
위임되며, 그것을 살려 두는 유일한 수단이 heartbeat 다.

## heartbeat 계약

`Panda.set_safety_mode()` 는 기본값 `disable_checks=True` 로 `0xf8`(heartbeat 검사 해제)을
보낸다. 그 상태에서는 펌웨어 fail-safe 블록 전체가 막혀 **동작하지 않는다** — PC 가 죽어도
릴레이가 intercept 로 남고 모터가 방치된다.

`0xf3` 을 보내면 검사가 되살아난다. 그 뒤로 심박이 끊기면 펌웨어가 구동 0 → 릴레이 개방 →
재engage 래치를 건다(해제는 `0xe9` 재전송뿐).

⚠ **임계는 점화 상태로 갈린다** — 펌웨어는 1 Hz 틱에서 `heartbeat_counter` 를 점화 on 이면
5, off 면 2 와 비교한다(`main.c` `HEARTBEAT_IGNITION_CNT_ON/OFF`). 즉 **off 1~2 s ·
on 4~5 s** 다. 아래 `HEARTBEAT_PERIOD_S`(0.2 s)는 둘 중 짧은 쪽에 대해서도 여유를 둔 값이다.

따라서 이 모듈은 heartbeat 를 켜고 유지하는 쪽을 택하며, 유지 실패는 숨기지 않고 올린다.

heartbeat 는 **송수신과 같은 스레드에서 인터리브**한다 — 별도 스레드에서 보내면 폴링과
USB 핸들을 경합한다.
"""
from __future__ import annotations

import os
import struct
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

HEARTBEAT_PERIOD_S = 0.2    # 펌웨어 임계(점화 off 1~2 s)의 5~10배 여유
HEARTBEAT_DEADLINE_S = 0.8  # 이 이상 못 보내면 fail-safe 가 임박한 것으로 본다

# ── per-bus CAN 에러 상태 (0xc3) ───────────────────────────────────────────
# REC(Receive Error Counter)·TEC(Transmit Error Counter)는 **uint8** 이다 — bxCAN ESR
# 레지스터의 카운터 폭이 8비트라 255 에서 포화한다(그 이상은 구분할 수 없다).
REQ_CAN_HEALTH = 0xC3
CAN_HEALTH_STRUCT = struct.Struct("<BBBBBBI")

# ── 펌웨어 호밍 시퀀서 (0xea 명령 / 0xeb 상태) ────────────────────────────
# 이 경로를 쓰는 이유는 **취소를 누가 보증하느냐**다. 취소 프레임 자체는 `0x60FB:04` 에 0 을
# 쓰는 SDO 하나라 직접 경로로도 낼 수 있으나, 그쪽 취소는 호스트 프로세스가 살아 있을 때만
# 성립한다. 펌웨어 시퀀서는 호스트가 죽거나 USB 가 끊겨도 권한·모드 상실을 감지해 스스로
# 취소를 낸다.
REQ_HOMING_CMD = 0xEA       # wValue: 0=취소 · ≠0=시작 / wIndex: 속도(0=기본값)
REQ_HOMING_STATUS = 0xEB    # 8바이트 상태

HOMING_SPEED_DEFAULT = 0    # 0 이면 펌웨어 기본값(2500 = 250 r/min)을 쓴다
HOMING_SPEED_MIN, HOMING_SPEED_MAX = 100, 3000   # 펌웨어가 받아 주는 범위

# 이름은 펌웨어 매크로 그대로 쓴다 — 상태 로그를 펌웨어와 대조할 수 있게.
HOMING_STATE = {
    0: "IDLE", 1: "ENABLE", 2: "SET_SPEED", 3: "START", 4: "WAIT", 5: "DONE",
    6: "ERR_TIMEOUT", 7: "ERR_ABORT", 8: "RESTORE", 9: "GOZERO",
    10: "ERR_GOZERO", 11: "GOZERO_W",
}
HOMING_TERMINAL = frozenset({0, 5, 6, 7, 10})   # 더 진행하지 않는 상태
HOMING_OK = frozenset({5})          # DONE 만 성공
HOMING_NODES = (3, 4)               # 호밍 대상 조향축


def decode_can_health(data: bytes) -> dict:
    """0xc3 응답을 dict 로 디코드한다. 순수 함수 — 하드웨어 없이 시험 가능하다.

    응답이 구조체 크기보다 짧으면 `LinkError`.
    """
    if len(data) < CAN_HEALTH_STRUCT.size:
        raise LinkError(f"can_health 응답이 짧다: {len(data)}B "
                        f"(기대 {CAN_HEALTH_STRUCT.size}B)")
    a = CAN_HEALTH_STRUCT.unpack(data[:CAN_HEALTH_STRUCT.size])
    return {
        "bus_off": a[0],
        "error_passive": a[1],
        "error_warning": a[2],
        "last_error_code": a[3],
        "rec": a[4],            # Receive Error Counter (uint8, 255 포화)
        "tec": a[5],            # Transmit Error Counter (uint8, 255 포화)
        "esr_reg": a[6],
    }


def decode_homing_status(data: bytes) -> dict:
    """0xeb 8바이트 응답을 상태·경과·리밋 입력 등의 dict 로 디코드한다.

    `terminal` 은 더 진행하지 않는 상태인가이고, 응답이 8B 미만이면 `LinkError`.
    """
    if len(data) < 8:
        raise LinkError(f"호밍 상태 응답이 짧다: {len(data)}B (기대 8B)")
    state = data[0]
    return {
        "state": state,
        "state_name": HOMING_STATE.get(state, f"UNKNOWN({state})"),
        "terminal": state in HOMING_TERMINAL,
        "done_mask": data[1],
        "seen_active": data[2],
        "elapsed_s": data[3] | (data[4] << 8),
        "digital_in": {3: data[5], 4: data[6]},
        "reached_mask": data[7],
    }


def _find_repo_root(start: str) -> str:
    """`Tools/docking_field_kit` 가 보이는 조상 디렉터리를 저장소 루트로 삼는다.

    깊이를 세지 않고 마커로 찾으므로 패키지가 다른 깊이로 옮겨가도 깨지지 않는다.
    마커를 못 찾으면 고정 6단계 상위로 되돌아간다 — 조용히 빈 문자열을 주지 않는다.
    """
    d = os.path.dirname(os.path.abspath(start))
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "Tools", "docking_field_kit")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    d = os.path.abspath(start)
    for _ in range(6):
        d = os.path.dirname(d)
    return d


_REPO = _find_repo_root(__file__)

# comma.ai panda 라이브러리 사본이 저장소에 둘 있다. 우선순위는 기능 기준이다.
#   ① Tools/docking_field_kit/panda        — `can_health()`(0xc3) 포함 = 상위집합
#   ② Tools/Can_Relay/panda-firmware/python — 펌웨어와 같은 트리, can_health 없음
# ②만 있으면 `can_health()` 를 쓸 수 없고, 그 사실은 `PandaLink.can_health` 가 LinkError 로 드러낸다.
_PANDA_SOURCES = (
    (os.path.join(_REPO, "Tools", "docking_field_kit"), "panda"),
    (os.path.join(_REPO, "Tools", "Can_Relay", "panda-firmware"), "python"),
)


def _panda_module():
    """comma.ai `Panda` 클래스를 로드한다. 사본 두 곳을 순서대로 시도한다.

    둘 다 실패하면 각각의 실패 사유를 모아 `LinkError` 로 올린다.
    """
    errors = []
    for root, modname in _PANDA_SOURCES:
        if not os.path.isdir(os.path.join(root, modname)):
            errors.append(f"{root}/{modname}: 없음")
            continue
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            mod = __import__(modname, fromlist=["Panda"])
            return mod.Panda
        except Exception as exc:                       # pragma: no cover - 환경 의존
            errors.append(f"{root}/{modname}: {type(exc).__name__}: {exc}")
    raise LinkError("panda 라이브러리를 찾지 못했다 — " + " / ".join(errors))


def panda_library_error() -> Optional[str]:
    """판다 파이썬 라이브러리를 지금 import 할 수 있는가. 문제 없으면 `None`, 있으면 사유.

    USB 는 열지 않는다 — 기동 시점 점검용이다. 이 라이브러리는 git 미추적이라 새
    worktree·클론에 딸려오지 않는데, 그 부재는 첫 `~/engage` 에서야 드러난다.
    """
    try:
        _panda_module()
        return None
    except LinkError as exc:
        return str(exc)


class LinkError(RuntimeError):
    """전송 계층 실패. 호출부는 이것을 받으면 정지 경로로 가야 한다."""


class BaseLink:
    """전송 계층 인터페이스. 구현체는 `PandaLink` 와 `MockLink` 둘이다."""

    def open(self) -> None:
        """전송로를 연다. 제어권은 잡지 않는다."""
        raise NotImplementedError

    def acquire(self) -> None:
        """제어권을 획득한다. 이 시점부터 PC 가 버스를 쓴다."""
        raise NotImplementedError

    def release(self) -> None:
        """제어권을 반환한다. 호출 전에 정지를 보내는 것은 호출부 책임이다."""
        raise NotImplementedError

    def send(self, frames: Iterable[P.Frame]) -> None:
        """프레임 묶음을 순서대로 보낸다."""
        raise NotImplementedError

    def recv(self) -> list[tuple[int, bytes, int]]:
        """받은 프레임을 `[(can_id, data, bus)]` 로 돌려준다."""
        raise NotImplementedError

    def heartbeat(self) -> None:
        """펌웨어 fail-safe 를 살려 두는 심박을 한 번 보낸다."""
        raise NotImplementedError

    def close(self) -> None:
        """전송로를 닫는다."""
        raise NotImplementedError

    @property
    def engaged(self) -> bool:
        """제어권을 쥐고 있는가."""
        raise NotImplementedError

    # ── per-bus CAN 에러 상태 (선택 기능 — 라이브러리 사본에 따라 부재 가능) ──
    def can_health(self, bus: int) -> dict:
        """그 버스의 CAN 에러 상태를 읽는다."""
        raise NotImplementedError

    # ── 펌웨어 호밍 시퀀서 ────────────────────────────────────────────────
    def homing_start(self, speed: int = HOMING_SPEED_DEFAULT) -> bool:
        """호밍 시작을 요청한다. 반환 `False` 는 거부(전제조건 미충족)."""
        raise NotImplementedError

    def homing_cancel(self) -> bool:
        """호밍 취소를 요청한다."""
        raise NotImplementedError

    def homing_status(self) -> dict:
        """호밍 시퀀서 상태를 읽는다."""
        raise NotImplementedError


class MockLink(BaseLink):
    """하드웨어 없는 대역. 보낸 프레임을 기록하고 미리 넣어 둔 응답을 돌려준다.

    실기 없이 안전 게이트·시퀀스·워치독을 전량 회귀 시험하기 위한 것이다.
    제어권 없이 보내려 하면 실기와 같이 `LinkError` 를 낸다.
    """

    def __init__(self):
        """빈 송신 기록·수신함과 IDLE 호밍 상태로 시작한다."""
        self.sent: list[P.Frame] = []
        self.inbox: list[tuple[int, bytes, int]] = []
        self.heartbeats = 0
        self.opened = False
        self._engaged = False
        self.log: list[str] = []
        self.health_fixture: Optional[dict] = None   # {bus: can_health dict}
        self.homing: dict = self.homing_state(0)
        # 시험용 상태 진행 대본. 비어 있지 않으면 `homing_status()` 가 앞에서부터 하나씩
        # 꺼내 쓰고(마지막 것은 유지) 실기 시퀀서의 상태 전이를 흉내낸다.
        self.homing_script: list = []

    @staticmethod
    def homing_state(state: int, **kw) -> dict:
        """상태 번호 하나로 0xeb 응답 형태의 dict 를 만든다(시험 편의)."""
        d = {"state": state, "state_name": HOMING_STATE.get(state, "UNKNOWN"),
             "terminal": state in HOMING_TERMINAL, "done_mask": 0,
             "seen_active": 0, "elapsed_s": 0,
             "digital_in": {3: 0, 4: 0}, "reached_mask": 0}
        d.update(kw)
        return d

    def open(self):
        """열림 표시만 세운다."""
        self.opened = True
        self.log.append("open")

    def acquire(self):
        """제어권 표시를 세운다. 열려 있지 않으면 실기와 같이 거부한다."""
        if not self.opened:
            raise LinkError("USB 미개방 상태에서 제어권을 요청했다")
        self._engaged = True
        self.log.append("acquire")

    def release(self):
        """제어권 표시를 내린다."""
        self._engaged = False
        self.log.append("release")

    def send(self, frames):
        """프레임을 `sent` 에 쌓는다. 제어권이 없으면 거부한다."""
        for f in frames:
            if not self._engaged:
                raise LinkError("제어권 없이 프레임을 보내려 했다")
            self.sent.append(f)

    def recv(self):
        """수신함을 통째로 꺼내 비운다."""
        out, self.inbox = self.inbox, []
        return out

    def heartbeat(self):
        """심박 횟수만 센다."""
        self.heartbeats += 1

    def close(self):
        """제어권·열림 표시를 모두 내린다."""
        self._engaged = False
        self.opened = False
        self.log.append("close")

    @property
    def engaged(self) -> bool:
        """제어권을 쥐고 있는가."""
        return self._engaged

    # ── 시험용 대역: 픽스처를 넣어 두면 그대로 돌려준다 ──────────────────
    def can_health(self, bus: int) -> dict:
        """픽스처에 넣어 둔 버스 상태를 돌려준다. 미설정이면 `LinkError`."""
        if self.health_fixture is None:
            raise LinkError("can_health 픽스처 미설정")
        return dict(self.health_fixture.get(bus, {}))

    def homing_start(self, speed: int = HOMING_SPEED_DEFAULT) -> bool:
        """펌웨어와 같은 조건으로 호밍 시작을 수리하거나 거부한다.

        제어권이 없으면 예외, 속도가 범위 밖이거나 이미 진행 중이면 `False` 다.
        대본이 걸려 있으면 그것이 진행을 결정하므로 상태를 덮어쓰지 않는다.
        """
        if not self._engaged:
            raise LinkError("제어권 없이 호밍을 요청했다")
        if speed != 0 and not (HOMING_SPEED_MIN <= speed <= HOMING_SPEED_MAX):
            return False
        if not self.homing.get("terminal", True):
            return False
        if not self.homing_script:
            self.homing = self.homing_state(1)          # ENABLE
        self.log.append(f"homing_start(speed={speed})")
        return True

    def homing_cancel(self) -> bool:
        """호밍 취소 — 펌웨어와 같이 **항상 수리된다**(terminal 이면 IDLE 로 정리)."""
        prev = self.homing.get("state", 0)
        self.homing_script = []
        self.homing = self.homing_state(7 if prev not in HOMING_TERMINAL else 0)
        self.log.append("homing_cancel")
        return True

    def homing_status(self) -> dict:
        """대본이 있으면 다음 상태를 꺼내 쓰고 현재 상태 사본을 돌려준다.

        마지막 항목은 남겨 둔다 — 종료 상태가 계속 관측되도록.
        """
        if self.homing_script:
            self.homing = (self.homing_script.pop(0) if len(self.homing_script) > 1
                           else self.homing_script[0])
        return dict(self.homing)


class PandaLink(BaseLink):
    """실제 comma.ai panda 를 통한 전송.

    수명주기를 3단계로 **분리**하는 것이 안전 장치다.
      1. `open()`    USB 만 연다. safety_mode 를 건드리지 않으므로 모터에 무영향.
      2. `acquire()` 제어권 획득. 여기서부터 Seer 대신 PC 가 버스를 쓴다.
      3. `release()` 반환. **반환 전에 호출부가 반드시 정지를 보내야 한다.**
    """

    def __init__(self, serial: Optional[str] = None,
                 log: Optional[Callable[[str], None]] = None):
        """`serial` 로 장치를 지정할 수 있고, `log` 는 한 줄 남기는 콜백이다.

        락이 RLock 인 이유는 이 락이 **USB 핸들 하나**를 지키기 때문이다. `_ctrl()` 이
        스스로 잠그므로 이미 잠근 구간에서 `_ctrl()` 을 부르면 일반 Lock 은 자기 자신에게 막힌다.
        """
        self._serial = serial
        self._log = log or (lambda _m: None)
        self._panda = None
        self._cls = None
        self._engaged = False
        self._lock = threading.RLock()
        self._last_hb = 0.0

    # ── 수명주기 ──────────────────────────────────────────────────────
    def open(self):
        """판다를 열거해 하나를 연다. safety_mode 는 건드리지 않는다.

        `serial` 없이 두 대 이상 보이면 어느 쪽에 지령이 갈지 알 수 없으므로 거부한다.
        """
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
        panda = None
        try:
            panda = self._cls(self._serial) if self._serial else self._cls()
            health = panda.health()
        except Exception as exc:
            # 부분 생성 핸들은 공표하지 않는다 — 닫고, `_panda` 는 None 그대로 둔다.
            if panda is not None:
                try:
                    panda.close()
                except Exception:                      # pragma: no cover - 실기 전용
                    pass
            raise LinkError(f"판다 개방 실패: {type(exc).__name__}: {exc}") from exc
        self._panda = panda
        self._log(f"판다 개방 — health={health}")

    def acquire(self):
        """제어권 획득. 순서가 곧 사양이다.

        safety_mode → 버스속도 → 버스 enable → auth → intercept → heartbeat.
        auth(0xe9)가 intercept(0xe8)보다 **먼저**여야 재engage 래치가 걸려 있을 때
        intercept 가 조용히 무시되지 않는다. 중간에 실패하면 어중간한 상태로 두지 않고
        롤백한 뒤 `LinkError` 를 올린다.

        마지막 심박은 펌웨어 fail-safe 를 켜는 것이다 — `set_safety_mode` 가
        `disable_checks=True` 로 그것을 꺼 두기 때문이다.
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
            # 마지막 심박까지가 획득이다 — 여기서 실패하면 intercept 를 무장한 채 두지 않는다.
            self._engaged = True
            self.heartbeat()
        except Exception as exc:
            self._log(f"제어권 획득 실패 — 롤백: {type(exc).__name__}: {exc}")
            self._rollback()
            self._engaged = False
            raise LinkError(f"제어권 획득 실패: {type(exc).__name__}: {exc}") from exc
        self._log("제어권 획득 — intercept, fail-safe 무장")

    def release(self):
        """제어권 반환. 호출부는 **이 함수 호출 전에 정지를 보내야 한다.**"""
        if self._panda is None:
            return
        self._rollback()
        self._engaged = False
        self._log("제어권 반환 — passthrough")

    def _rollback(self):
        """intercept → auth 를 내리고 safety_mode 를 SILENT 로 되돌린다.

        각 단계 실패는 로그만 남기고 계속한다 — 하나가 막혀도 나머지는 내려야 한다.
        """
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
        """USB 를 닫고 제어권 표시를 내린다. 닫기 실패는 삼킨다."""
        if self._panda is not None:
            try:
                self._panda.close()
            except Exception:                          # pragma: no cover - 실기 전용
                pass
        self._panda = None
        self._engaged = False

    # ── 입출력 ────────────────────────────────────────────────────────
    def _ctrl(self, P_, request: int, value: int):
        """USB 제어 전송 1회를 **락 안에서** 한다.

        이 락이 없으면 심박(제어 스레드)과 0xea/0xeb(서비스 콜백 스레드)가 같은 핸들에서
        겹친다 — 호밍 시퀀서가 들어오면서 USB 접근이 제어 스레드 하나라는 전제가 깨졌다.
        """
        with self._lock:
            self._panda._handle.controlWrite(P_.REQUEST_OUT, request, value, 0, b"")

    def heartbeat(self):
        """심박(0xf3)을 보내고 마지막 송신 시각을 남긴다."""
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 heartbeat")
        self._ctrl(self._cls, REQ_HEARTBEAT, 0)
        self._last_hb = time.monotonic()

    def heartbeat_overdue(self, now: Optional[float] = None) -> bool:
        """마지막 심박이 `HEARTBEAT_DEADLINE_S` 를 넘겼는가(fail-safe 임박 판정)."""
        now = time.monotonic() if now is None else now
        return (now - self._last_hb) > HEARTBEAT_DEADLINE_S

    def send(self, frames):
        """프레임 묶음을 락 안에서 순서대로 보낸다. 미개방·제어권 없음은 거부한다."""
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 송신")
        if not self._engaged:
            raise LinkError("제어권 없이 프레임을 보내려 했다")
        with self._lock:
            for f in frames:
                self._panda.can_send(f.can_id, f.data[:8], f.bus)

    def recv(self):
        """받은 프레임을 `[(can_id, data, bus)]` 로 돌려준다(타임스탬프는 버린다)."""
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 수신")
        with self._lock:
            raw = self._panda.can_recv()
        return [(addr, bytes(dat), bus) for addr, _ts, dat, bus in raw]

    @property
    def engaged(self) -> bool:
        """제어권을 쥐고 있는가."""
        return self._engaged

    # ── per-bus CAN 에러 상태 (0xc3) ──────────────────────────────────────
    def can_health(self, bus: int) -> dict:
        """버스별 bxCAN 에러 상태. 읽기 전용이라 제어 경로에 영향이 없다.

        라이브러리 사본에 헬퍼가 없어도 동작하도록 **직접 controlRead** 한다.
        """
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 can_health")
        with self._lock:
            raw = self._panda._handle.controlRead(
                self._cls.REQUEST_IN, REQ_CAN_HEALTH, int(bus), 0,
                CAN_HEALTH_STRUCT.size)
        return decode_can_health(bytes(raw))

    # ── 펌웨어 호밍 시퀀서 (0xea / 0xeb) ─────────────────────────────────
    def homing_start(self, speed: int = HOMING_SPEED_DEFAULT) -> bool:
        """호밍 시작 요청. 반환 `False` 는 **펌웨어가 거부**(전제조건 미충족)한 것이다.

        펌웨어 전제조건: PC 주도권 ∧ safety_mode 30 ∧ 현재 상태가 terminal ∧
        (speed 0 또는 `HOMING_SPEED_MIN`~`HOMING_SPEED_MAX`).
        범위 밖 속도는 보내기 전에 `LinkError` 로 막는다.
        """
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 호밍 요청")
        if speed != 0 and not (HOMING_SPEED_MIN <= speed <= HOMING_SPEED_MAX):
            raise LinkError(
                f"호밍 속도 {speed} 는 펌웨어 허용 범위 밖이다 "
                f"({HOMING_SPEED_MIN}~{HOMING_SPEED_MAX}, 0=기본값)")
        return self._homing_cmd(start=True, speed=speed)

    def homing_cancel(self) -> bool:
        """호밍 취소 — 펌웨어가 `0x60FB:04 = 0` 취소 프레임을 송신한다.

        **이것이 존재하는 것이 이 경로를 쓰는 이유다** — 호스트가 죽어도 취소가 성립한다.
        """
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 호밍 취소")
        return self._homing_cmd(start=False, speed=0)

    def _homing_cmd(self, start: bool, speed: int) -> bool:
        """0xea 를 보내고 펌웨어가 수리했는지(첫 바이트) 돌려준다."""
        with self._lock:
            raw = self._panda._handle.controlRead(
                self._cls.REQUEST_IN, REQ_HOMING_CMD, 1 if start else 0,
                int(speed), 1)
        return bool(raw and raw[0])

    def homing_status(self) -> dict:
        """0xeb 로 호밍 시퀀서 상태를 읽어 디코드한다."""
        if self._panda is None:
            raise LinkError("판다 미개방 상태의 호밍 상태 조회")
        with self._lock:
            raw = self._panda._handle.controlRead(
                self._cls.REQUEST_IN, REQ_HOMING_STATUS, 0, 0, 8)
        return decode_homing_status(bytes(raw))
