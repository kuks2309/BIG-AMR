#!/usr/bin/env python3
"""판다 USB 직결 백엔드 — 드라이버를 거치지 않고 SDO 를 만들어 직접 보낸다.

바이트 조립은 `can_relay.protocol` 을 쓴다. 조향·구동 프레임이 원본
`Tools/amr_test_gui/gui.py` 의 손조립과 바이트 동일함을 회귀가 고정한다
(`test/test_port_equivalence.py`, `test/test_master_frame_match.py`).

호밍 경로는 원본과 다르다 — 원본은 SDO 를 직접 쓰고 드라이버 쪽은 펌웨어 시퀀서를 쓴다.
폴 루프의 조향 재송신도 이 백엔드에만 있다.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, Optional

from .. import protocol as P
from ..link import _find_repo_root
from .backend_base import (CAP_DRIVE, CAP_ENGAGE, CAP_HOME, CAP_MOTOR_TABLE,
                           CAP_SCAN, CAP_STEER_ALL, CAP_STEER_AXIS, CAP_STOP,
                           CAP_USB, BackendBase)

# ── 하드웨어·환산 상수 ────────────────────────────────────────────────────
SEER_BUS, MOTOR_BUS = 0, 2      # 판다 버스 번호 — 0=Seer 측, 2=모터 측
SEER_GATE, CAN_KBPS = 30, 250   # 릴레이 safety_mode 번호, 버스 속도(kbps)
COUNTS_PER_DEG = 57344          # 조향 counts/°
_STEER_HOME_FALLBACK = {3: 7871815, 4: 7840086}
VEL_PER_MMPS, VEL_MAX_UNITS = 24.447, 4889   # 구동 raw/(mm/s), raw 상한
STEER_LIMIT_DEG = 90.0          # 조향 가동범위(±)
DRIVE_NODES, STEER_NODES = (1, 2), (3, 4)

HOMING_SPEED = 2500         # 0x6099:00 — 0.1 r/min → 250 r/min
HOMING_TIMEOUT_S = 90.0
HOMING_START_S = 10.0
BIT15 = 1 << 15
STEER_ZERO_TOL_DEG = 0.1    # 호밍 후 0° 도달 판정 허용치
STEER_ZERO_TIMEOUT_S = 10.0  # 그 도달을 기다리는 상한
MEAS_TTL_S = 1.0            # 이보다 오래된 실측은 없는 것으로 친다(원본 High ①). **기본값일 뿐이다** —
#                             인스턴스가 `meas_ttl_s` 로 들고 런타임에 바꿀 수 있다(리뷰 Low ③).
RX_TTL_S = 1.0              # 이보다 오래 응답이 없으면 구동을 0 으로(원본 High ③)
# 지령 TTL — 이보다 오래 새 지령이 없으면 구동을 0 으로 수렴시킨다.
# `RelayBackend` 는 `cmd_timeout_s=0.3` 으로 같은 일을 한다(모듈 설계규칙 2). DirectBackend
# 에는 **RX 워치독뿐**이라, 드라이브가 응답을 잘 주는 한 `_drive_units` 는 갱신이 끊겨도
# 영구히 재송신됐다 — 조그 스레드가 예외로 죽거나 Qt 메인 스레드가 블록되면 아무도 새
# 지령을 내지 않는데 **로봇은 계속 주행한다.** 남는 정지 수단이 하드웨어 E-STOP 뿐이었다.
# 재송신하는 **값**만 바꾸므로 「원본 gui.py 와 같은 프레임 형식」 원칙은 깨지 않는다.
CMD_TTL_S = 0.5

# ⚠ 깊이를 세지 않는다. `dirname` 6회로 적었다가 `.../src/Tools/...` 를 가리켜
#   `ModuleNotFoundError: No module named 'panda'` 가 났다(2026-08-04 오프스크린 스모크).
#   `link.py:_find_repo_root` 가 문서화해 둔 것과 같은 off-by-one 이므로 그 함수를 쓴다.
_KIT = os.path.join(_find_repo_root(__file__), "Tools", "docking_field_kit")


def _load_steer_home():
    """조향 0° counts 를 정본 YAML 에서 읽는다. 실패하면 코드 사본으로 내려간다.

    원본 GUI 와 **같은 출처**를 봐야 백엔드를 바꿔도 같은 각도로 간다.
    반환 `({node: counts}, 출처 설명)` — 사본으로 내려간 사실은 설명 문자열로 드러낸다.
    """
    path = os.path.join(_find_repo_root(__file__), "src", "Comm", "CAN", "can_relay",
                        "config", "machine", "foil_a082.yaml")
    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            params = yaml.safe_load(fh)["/**"]["ros__parameters"]
        counts = [int(c) for c in params["steer_home_counts"]]
        nodes = [int(n) for n in params.get("steer_nodes", [3, 4])]
        home = dict(zip(nodes, counts))
        if home != _STEER_HOME_FALLBACK:
            return home, f"정본 YAML (⚠ 코드 사본 {_STEER_HOME_FALLBACK} 와 다름 — 정본을 따름)"
        return home, "정본 YAML (코드 사본과 일치)"
    except Exception as exc:
        return dict(_STEER_HOME_FALLBACK), (
            f"⚠ 코드 사본 — 정본 YAML 을 읽지 못했습니다({type(exc).__name__}): {path}")


STEER_HOME, STEER_HOME_SOURCE = _load_steer_home()


def steer_counts(node: int, deg: float):
    """조향 절대위치 counts. ±`STEER_LIMIT_DEG` 로 클램프한 뒤 영점 + `deg` × 57344.

    반환 `(적용된 각(°), counts)` — 클램프됐는지는 첫 값으로 알 수 있다.
    """
    deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
    return deg, int(round(STEER_HOME[node] + deg * COUNTS_PER_DEG))


def drive_units(mmps: float, raw_sign: int) -> int:
    """구동 raw. `mmps` × 24.447 에 부호를 붙이고 ±`VEL_MAX_UNITS` 로 클램프한다."""
    return max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS,
                                   int(round(raw_sign * mmps * VEL_PER_MMPS))))


def _panda_class():
    """필드킷에 동봉된 comma.ai `Panda` 클래스를 로드한다(`sys.path` 를 변형한다)."""
    if _KIT not in sys.path:
        sys.path.insert(0, _KIT)
    from panda import Panda
    return Panda


class DirectBackend(BackendBase):
    """판다를 직접 열고 SDO 를 만들어 보낸다."""

    name = "direct"
    capabilities = frozenset({CAP_SCAN, CAP_USB, CAP_ENGAGE, CAP_STOP, CAP_HOME,
                              CAP_STEER_AXIS, CAP_STEER_ALL, CAP_DRIVE,
                              CAP_MOTOR_TABLE})

    def __init__(self, log: Optional[Callable[[str], None]] = None,
                 meas_ttl_s: float = MEAS_TTL_S):
        """`log` 는 화면에 한 줄 남기는 콜백, `meas_ttl_s` 는 실측 신선도 한도(초)다.

        TTL 을 인스턴스 상태로 드는 이유는 ros2 백엔드가 ROS 파라미터로 런타임 조정되는
        것과 같은 방식을 여기서도 제공하기 위해서다.
        """
        self.meas_ttl_s = float(meas_ttl_s)
        self._log = log or (lambda _m: None)
        self.panda = None
        self._cls = None
        self._run = False
        self._th = None
        # 폴링·조그가 같은 버스를 공유한다. RLock 인 이유는 「정지 확인 → 구동 송신」을 한
        # 임계구역에 넣어야 하는데 그 안에서 `drive()` → `_send()` 가 같은 락을 다시 잡기 때문이다.
        self._can_lock = threading.RLock()
        self._meas_deg = {}                 # node -> 실측 조향각(°)
        self._meas_at = {}                  # node -> 그 각도를 받은 시각(신선도 판정용)
        self._drive_units = 0               # 마지막 구동 지령(raw) — 폴 루프가 재송신한다
        self._steer_counts: dict = {}       # 마지막 조향 목표(counts) — 폴 루프가 재송신한다
        self._rx_at = 0.0                   # 마지막으로 드라이브 응답을 받은 시각
        self._cmd_at = 0.0                  # 마지막으로 **새 지령**을 받은 시각
        self._status_word = {}              # node -> 0x6041
        self._rows = {}                     # node -> (deg, rpm, amp)
        self._serials = []
        self._released = False
        self._homing = False

    # ── 수명주기 ──────────────────────────────────────────────────────
    def shutdown(self, reason: str = "") -> None:
        """제어권을 반환하고 USB 를 닫는다. 종료 경로가 여럿이므로 멱등이다."""
        if self._released:
            return
        self._released = True
        self._log(f"해제 시작 — {reason}")
        if self.panda is not None:
            try:
                self.set_engaged(False)
            except Exception as exc:
                self._log(f"⚠ 종료 중 제어권 반환 예외: {type(exc).__name__}: {exc}")
            try:
                self.panda.close()
            except Exception as exc:
                self._log(f"⚠ 종료 중 USB close 예외: {type(exc).__name__}: {exc}")
            self.panda = None
        self._log("해제 완료 — 제어권 반환 · USB 연결 해제")

    # ── 조회 ──────────────────────────────────────────────────────────
    def meas_angle(self, node: int) -> Optional[float]:
        """그 축의 실측 조향각(°). `meas_ttl_s` 밖이면 `None`.

        폴링 스레드가 죽으면 마지막 값이 남는다 — 그 값을 정착 판정에 쓰면 멈춘 화면을
        보고 바퀴가 그 각도라고 믿은 채 구동에 들어간다. 신선도가 그것을 막는다.
        """
        node = int(node)
        deg = self._meas_deg.get(node)
        if deg is None:
            return None
        at = self._meas_at.get(node)
        if at is None or (time.monotonic() - at) > self.meas_ttl_s:
            return None
        return deg

    def _set_meas(self, node: int, deg: float) -> None:
        """실측 1건을 값과 수신 시각을 함께 남긴다(따로 쓸 수 있으면 언젠가 따로 쓰인다)."""
        self._meas_deg[node] = deg
        self._meas_at[node] = time.monotonic()

    def motor_rows(self) -> dict:
        """`{node: (각도°|None, rpm|None, 전류 A|None)}` 사본."""
        return dict(self._rows)

    def link_status(self) -> tuple:
        """판다가 열려 있는가 — 이 백엔드에는 드라이버가 없어 USB 개방 여부가 곧 연결이다."""
        if self.panda is None:
            return (False, "판다 · ⚠ 미연결")
        ser = (self._serials[0] if getattr(self, "_serials", None) else "")
        return (True, f"판다 · 연결됨{(' ' + ser) if ser else ''}")

    def status(self) -> tuple:
        """USB·제어권·폴링 상태를 한 줄로. 반환 `(텍스트, 정상인가, 제어권 보유인가)`."""
        if self.panda is None:
            return "판다 USB 미연결", False, False
        if not self._run:
            return "USB 연결됨 · 제어권 미획득", True, False
        return "제어권 보유 — intercept · 폴링 중", True, True

    # ── 조작: 블로킹 ──────────────────────────────────────────────────
    def scan(self) -> tuple:
        """판다를 열거한다. USB 는 열지 않는다. 반환 `(성공, 메시지)`.

        2대 이상이면 **막는다** — 어느 장치에 지령이 갈지 모르는 채 진행할 수 없다.
        대수·시리얼은 목록을 비우기 전에 잡아 메시지에 싣는다.
        """
        try:
            self._serials = list(_panda_class().list())
        except Exception as exc:
            return False, f"판다 검색 실패: {type(exc).__name__}: {exc}"
        if not self._serials:
            return False, "판다 없음 — USB 연결·udev 규칙 확인"
        if len(self._serials) == 1:
            return True, f"판다 검출: {self._serials[0]}"
        found = list(self._serials)
        self._serials = []
        return False, (f"⚠ 판다 {len(found)}대 검출({', '.join(found)}) — 1 PC 1대 원칙 위반. "
                       f"어느 장치에 지령이 갈지 알 수 없으므로 연결을 막습니다. "
                       f"한 대만 남기고 다시 검색하세요.")

    def set_usb(self, on: bool) -> tuple:
        """판다 USB 를 연다/닫는다. 닫을 때 제어권이 남아 있으면 먼저 반환한다."""
        if on:
            try:
                self._cls = _panda_class()
                self.panda = self._cls()
                h = self.panda.health()
                return True, (f"USB 연결 — fw={self.panda.get_version()} "
                              f"safety={h['safety_mode']} harness={h['car_harness_status']}")
            except Exception as exc:
                self.panda = None
                return False, f"USB 연결 실패: {type(exc).__name__}: {exc}"
        if self._run:
            self.set_engaged(False)
        if self.panda is not None:
            try:
                self.panda.close()
            except Exception:
                pass
            self.panda = None
        return True, "USB 해제"

    def set_engaged(self, on: bool) -> tuple:
        """제어권 획득/반환. 획득하면 폴링 스레드가 뜬다.

        순서가 곧 사양이다: safety_mode → 버스속도 → 버스 enable → auth(0xe9) → intercept(0xe8).
        반환할 때는 **먼저 구동을 0 으로** 보낸다 — 정지가 못 나간 채 auth·intercept 를
        내리면 드라이브가 마지막 속도를 문 채 Seer 로 넘어가므로, 실패해도 삼키지 않고 알린다.
        """
        if self.panda is None:
            return False, "USB 를 먼저 연결하세요"
        # ── 멱등 가드 ──
        # `RelayBackend.start()` 는 「두 번 부르면 버스 writer 가 둘이 된다」며 막는다.
        # 여기에는 그 검사가 없어, UI 가 빠르게 토글하면 워커가 겹치고 `self._th` 가 덮여
        # **이전 폴 스레드 핸들이 유실**된다(그 스레드는 join 대상에서 사라진다).
        # 두 번째 획득은 브링업도 다시 보내 **주행 중일 수 있는 구동축에 fault reset** 을 건다.
        if on and self._run:
            return True, "이미 제어권을 보유하고 있습니다"
        if not on and not self._run:
            return True, "이미 제어권이 반환된 상태입니다"
        # ── 상태 초기화 ──
        # 획득·반환 **양쪽에서** 마지막 지령을 버린다. 종전에는 반환해도 `_steer_counts`·
        # `_drive_units` 가 살아남아, 재획득하면 폴 루프 첫 바퀴에서 그 값이 그대로 나갔다 —
        # 「제어권 획득」 버튼 하나로 **조작 없이 조향·주행이 시작**된다. 그 사이 사람이
        # 바퀴를 만졌거나 Seer 가 조향을 돌렸다면 옛 목표는 다른 각도를 뜻한다.
        self._drive_units = 0
        self._steer_counts = {}
        P_ = self._cls
        try:
            if on:
                self.panda.set_safety_mode(SEER_GATE, 0)
                for b in (SEER_BUS, MOTOR_BUS):
                    self.panda.set_can_speed_kbps(b, CAN_KBPS)
                    self.panda.set_can_enable(b, True)
                self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE9, 1, 0, b"")
                self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE8, 1, 0, b"")
                # ── fail-safe 를 **먼저** 무장한다 ──
                # `set_safety_mode` 가 `disable_checks=True` 로 `0xf8` 을 보내 심박 검사를
                # 꺼 둔 상태다. 이 구간에서 예외가 나면 「Seer 차단 + 릴레이 intercept +
                # 심박 영구 미송신」이 남아 **아무도 로봇을 세울 수 없다.** `link.acquire()`
                # 는 같은 이유로 intercept 직후 즉시 심박을 보낸다 — 여기도 맞춘다.
                # 브링업보다 먼저 와야 한다. 브링업이 실패해도 fail-safe 는 살아 있어야 한다.
                self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xF3, 0, 0, b"")
                # ── 구동축 브링업 — 제어권 확인 후 · 폴 스레드 시작 **전** ──
                # `RelayBackend.start()` 가 같은 위치에서 보내는 것과 같은 시퀀스다.
                # 이것이 없으면 can_relay 프로세스 재시작 뒤 구동축이 `0x60FF` 를 받고도
                # 돌지 않는다 — 2026-08-08 실기에서 이 경로로 재현됐다
                # (node1 0.1 rpm / node2 78.2 rpm). 상세는 `backend.py:_write_bringup`.
                # ⚠ **조향축에는 보내지 않는다** — fault reset 이 조향 위치 카운터를 지워
                #   0° 기준이 무효가 된다(같은 날 실기 확인). 조향 기준 복구는 호밍 소관이다.
                self._write_bringup()
                # ⚠ `_rx_at = 0.0` 은 falsy 라 아래 RX 워치독의 첫 항이 계속 거짓이 된다 —
                #   응답을 **한 번도 못 받으면 워치독이 영원히 무장되지 않고** 구동 지령만
                #   계속 나갔다(송신은 되고 수신만 죽은 경우: USB rx 큐 오버플로, bus2 수신
                #   배선 불량, 응답 ID 오배선). 지금 시각으로 무장해 첫 TTL 안에 응답이
                #   없으면 즉시 0 으로 수렴하게 한다.
                self._rx_at = time.monotonic()
                self._cmd_at = time.monotonic()
                self._run = True
                self._th = threading.Thread(target=self._loop, daemon=True, name="poll")
                self._th.start()
                return True, "제어권 획득 — 릴레이 intercept, Seer 에서 가져옴"
            try:
                self.drive(0.0)
            except Exception as exc:
                self._log(f"⚠ 제어권 반환 전 정지 송신 실패 — {type(exc).__name__}: {exc}. "
                          f"드라이브가 마지막 지령을 유지할 수 있습니다. E-STOP 을 확인하세요.")
            self._run = False
            if self._th is not None:
                self._th.join(timeout=1.0)
                self._th = None
            # ⚠ 세 단계를 **각각** 시도한다. 하나로 묶으면 중간 실패에서 릴레이가 열리지
            #   않은 채 남아 Seer 도 PC 도 로봇을 제어하지 못한다. 순서·개별 예외 처리는
            #   `link._rollback()` 과 같게 맞췄다(intercept → authority → SILENT).
            self._release_steps()
            return True, "제어권 반환 — passthrough (USB 유지)"
        except Exception as exc:
            if on:
                # 획득 도중 실패 — 어중간한 상태로 두지 않는다. `link.acquire()` 와 같다.
                self._log(f"제어권 획득 실패 — 롤백: {type(exc).__name__}: {exc}")
                self._run = False
                self._release_steps()
            return False, f"제어권 처리 실패: {type(exc).__name__}: {exc}"

    def _release_steps(self) -> None:
        """릴레이·권한·safety mode 를 **각각** 되돌린다(한 단계 실패가 나머지를 막지 않는다)."""
        for what, fn in (
            ("intercept(0xE8)", lambda: self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE8, 0, 0, b"")),
            ("authority(0xE9)", lambda: self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE9, 0, 0, b"")),
            ("safety_mode(0)", lambda: self.panda.set_safety_mode(0, 0)),
        ):
            try:
                fn()
            except Exception as exc:
                self._log(f"⚠ 제어권 반환 {what} 실패 — {type(exc).__name__}: {exc}. "
                          f"릴레이가 열리지 않았을 수 있습니다 — E-STOP 을 확인하세요.")

    def stop(self) -> tuple:
        """정지 — **구동만 0** 으로 보내고 조향은 현 위치에 그대로 둔다.

        조향을 세우는 프레임은 새로 보내지 않고, 폴 루프가 반복해 내던 **조향 목표
        재송신을 그친다**. 멈추지 않으면 정지 후에도 우리 조향 목표가 계속 나간다.
        """
        self._steer_counts = {}
        if not self._run:
            return False, "제어권을 먼저 획득하세요"
        try:
            self.drive(0.0)
            return True, "정지 — 구동 0 (조향은 현 위치 유지)"
        except Exception as exc:
            return False, f"정지 송신 실패: {type(exc).__name__}: {exc}"

    def home(self) -> tuple:
        """조향 2축(N3·N4) 호밍 + 0° 복귀. 반환 `(성공, 사유)`.

        축당 `0x6040=0x86` → `0x6099`(속도) → `0x60FB:04=1`(개시) 3프레임을 보내고
        상태워드로 완료를 판정한 뒤 0° 를 지령한다.

        `0x6098`(homing method)은 쓰지 않는다 — 드라이브 저장값을 덮어쓰면 리셋 모드가 꺼진다.
        구동 노드(1·2)는 기계적 원점이 없어 호밍 대상이 아니다.
        `0x60FB:04` 호밍은 원점(리밋)을 잡을 뿐이라 완료 시점의 위치는 0° 가 아니므로
        0° 복귀가 따로 필요하고, 그 복귀 실패는 전체를 실패로 보고한다 — 「원점은 잡았는데
        축이 어디 서 있는지 모른다」를 성공으로 적으면 그 다음 구동이 열린다.
        """
        if not self._run:
            return False, "제어권을 먼저 획득하세요"
        if self._homing:
            return False, "호밍 이미 진행 중"
        self._homing = True
        try:
            self.drive(0.0)                     # 호밍 전 구동은 반드시 0
            # 재영점 **전** 좌표계의 조향 목표를 들고 있는 것 자체가 위험하다 —
            # 호밍이 끝나면 카운터 원점이 바뀌므로 그 값은 다른 각도를 뜻하게 된다.
            self._steer_counts = {}
            self._status_word.clear()           # 직전 상태워드를 완료로 오독하지 않도록
            for n in STEER_NODES:
                self._send([P.sdo_write(n, 0x6040, 0x86, 2, bus=MOTOR_BUS)])
                self._send([P.sdo_write(n, 0x6099, HOMING_SPEED, 4, bus=MOTOR_BUS)])
                self._send([P.sdo_write(n, 0x60FB, 1, 1, sub=4, bus=MOTOR_BUS)])
            self._log("호밍 개시 — 조향 2축. 완료까지 30초 이상 걸립니다.")
            ok, why = self._wait_homed()
            if not ok:
                return ok, why
            self._log(f"원점 확인 — {why}")
            # 0° 복귀는 실측으로 정착을 판정한다. `_absorb` 는 호밍 중 0x6064 를 각도로
            # 반영하지 않으므로 — 그 구간의 값은 실위치가 아니라 0 이다 — 플래그를 쥔 채
            # 판정하면 실측이 영원히 없어 항상 미확인으로 떨어진다.
            self._homing = False
            zok, zwhy = self._steer_zero_return()
            return zok, f"{why} · {zwhy}"
        except Exception as exc:
            return False, f"호밍 중단: {type(exc).__name__}: {exc}"
        finally:
            self._homing = False

    def _wait_homed(self) -> tuple:
        """상태워드 bit15 로 완료를 판정한다. 반환 `(성공, 사유)`.

        **2상 판정**이다 — 먼저 두 축이 0(진행 중)이 되는 것을 보고, 그 다음 1(완료)을
        기다린다. 1 만 보면 이전에 호밍을 마친 축이 시작 전부터 1 이라 즉시 완료로 읽힌다.
        개시 관측 창은 `HOMING_START_S`, 완료 대기는 `HOMING_TIMEOUT_S` 다.
        """
        t0 = time.time()
        started = set()
        while time.time() - t0 < HOMING_START_S:
            for n in STEER_NODES:
                st = self._status_word.get(n)
                if st is not None and not (st & BIT15):
                    started.add(n)
            if started >= set(STEER_NODES):
                break
            time.sleep(0.1)
        if started < set(STEER_NODES):
            missing = sorted(set(STEER_NODES) - started)
            return False, (f"개시 신호(bit15=0)를 못 봤습니다 — 노드 {missing}. "
                           f"움직이지 않았는지 육안으로 확인하세요.")
        while time.time() - t0 < HOMING_TIMEOUT_S:
            if all((self._status_word.get(n) or 0) & BIT15 for n in STEER_NODES):
                return True, f"원점 신호 확인({time.time() - t0:.0f}초 소요)."
            time.sleep(0.1)
        return False, f"{HOMING_TIMEOUT_S:.0f}초 안에 완료 신호가 오지 않았습니다."

    def _steer_zero_return(self, timeout_s: Optional[float] = None) -> tuple:
        """조향 0° 를 지령하고 `STEER_ZERO_TOL_DEG` 안에 들어올 때까지 기다린다.

        0° 는 `STEER_HOME`(정본 YAML `steer_home_counts`)에서 나온다 — `steer_all(0.0)` 이
        그 값을 그대로 내므로 이 함수는 새 상수를 만들지 않는다. 펌웨어 시퀀서의 `GOZERO`
        목표는 호밍 후 정착값이라 0° 에서 +0.178° / +0.331° 떨어져 있고, 그 편차는 펌웨어
        도달 허용오차 1.0° 안이라 펌웨어가 검출하지 못한다 — 그래서 호스트가 다시 지령한다.

        판정에 `settled()` 를 쓰므로 신선하지 않은 실측은 도달로 치지 않는다.
        반환 `(성공, 사유)` — 실패 사유에는 축별 실측을 싣는다.
        """
        limit = float(STEER_ZERO_TIMEOUT_S if timeout_s is None else timeout_s)
        self.steer_all(0.0)
        t0 = time.monotonic()
        while time.monotonic() - t0 < limit:
            if self.settled(0.0, STEER_ZERO_TOL_DEG, STEER_NODES):
                return True, f"조향 0° 복귀 완료(±{STEER_ZERO_TOL_DEG}° 안)."
            time.sleep(0.05)
        shown = " · ".join(
            f"N{n} " + ("실측없음" if (c := self.meas_angle(n)) is None else f"{c:+.3f}°")
            for n in STEER_NODES)
        return False, (f"조향 0° 복귀 미확인 — {limit:.0f}초 안에 ±{STEER_ZERO_TOL_DEG}° 안에 "
                       f"들어오지 않았습니다 ({shown}). "
                       f"목표는 걸려 있으므로 축이 계속 움직이는 중일 수 있습니다.")

    # ── 조작: 즉시 반환 ───────────────────────────────────────────────
    def steer_axis(self, node: int, deg: float) -> None:
        """그 축에 조향 목표 2프레임(`0x607A` 위치 + `0x6040=0x3F` 적용)을 보낸다.

        목표를 상태로 남겨 폴 루프가 재송신한다 — 프레임 한 장이 유실돼도 지령이 살아남는다.
        """
        _applied, counts = steer_counts(int(node), float(deg))
        self._steer_counts[int(node)] = int(counts)
        self._send(P.steer_target_frames(int(node), counts, MOTOR_BUS))

    def steer_all(self, deg: float) -> None:
        """조향 2축을 같은 각으로 보낸다(crab)."""
        for n in STEER_NODES:
            self.steer_axis(n, deg)

    def drive(self, mmps: float) -> None:
        """구동 2축에 `0x60FF` 속도를 보낸다. 지령을 상태로 남겨 폴 루프가 재송신한다."""
        units = drive_units(abs(float(mmps)), 1 if mmps >= 0 else -1)
        self._drive_units = units
        self._cmd_at = time.monotonic()
        self._send([P.drive_velocity_frame(n, units, MOTOR_BUS) for n in DRIVE_NODES])

    # ── 내부 ─────────────────────────────────────────────────────────
    def _write_bringup(self) -> None:
        """구동축 브링업 — **구동축만**. `RelayBackend._write_bringup` 과 같은 프레임.

        두 백엔드가 같은 바이트를 내야 「UI 는 같은데 백엔드만 다르다」가 성립한다
        (이 백엔드의 존재 이유가 비교 기준이다). 조건 없이 보낸다 — ROS 경로는
        `allow_bringup` 플래그를 두지만 배포 yaml 이 true 라 실질 동작이 같고,
        여기에 쓰이지 않는 손잡이를 새로 만들지 않는다.
        """
        frames = []
        for n in DRIVE_NODES:
            frames.extend(P.drive_init_frames(n, MOTOR_BUS))
        self._send(frames)
        self._log(f"구동축 브링업 {len(frames)} 프레임 송신 "
                  f"(조향축 제외 — fault reset 이 조향 0° 기준을 지운다)")

    def _send(self, frames) -> None:
        """프레임 묶음을 락 안에서 순서대로 판다에 넘긴다. 미연결이면 예외를 던진다."""
        if self.panda is None:
            raise RuntimeError("판다 미연결 — USB 를 먼저 연결하세요")
        with self._can_lock:
            for f in frames:
                self.panda.can_send(f.can_id, f.data[:8], f.bus)

    def _loop(self) -> None:
        """폴링 스레드 — heartbeat · 4객체 폴 · 응답 파싱 · 지령 재송신을 한 주기로 돈다.

        읽는 객체는 `0x6064`(위치)·`0x606C`(속도)·`0x6078`(전류)·`0x6041`(상태워드)다.
        heartbeat(0xf3)는 **락 안에서** 보낸다 — 밖에 있으면 조그·호밍 스레드가 락을 쥐고
        `can_send` 하는 동안 같은 USB 핸들에 심박이 겹친다.

        구동은 매 주기 재송신해 프레임 유실에 견디고, 응답이 `RX_TTL_S` 넘게 없으면 버스
        상태를 모르는 것이므로 0 으로 간다. 조향 목표도 걸려 있으면 같은 이유로 재송신한다.
        예외가 나면 `_run` 을 내리고 스레드를 끝낸다.
        """
        P_ = self._cls
        while self._run:
            try:
                with self._can_lock:
                    self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xF3, 0, 0, b"")
                    for n in DRIVE_NODES + STEER_NODES:
                        for idx in (0x6064, 0x606C, 0x6078, 0x6041):
                            self.panda.can_send(
                                0x600 + n,
                                bytes([0x40, idx & 0xFF, idx >> 8, 0, 0, 0, 0, 0]),
                                MOTOR_BUS)
                time.sleep(0.08)
                out = {}
                # ⚠ 가장 긴 USB 트랜잭션이므로 **락 안에서** 한다. 밖에 두면 조그·슬라이더·
                #   호밍 스레드의 `can_send` 와 같은 핸들에서 겹친다 — `link.py` 가 회귀까지
                #   붙여 막아 둔 조건(「심박이 실패한 이력」)과 같고, `link.recv()` 도 락 안이다.
                with self._can_lock:
                    rx = self.panda.can_recv()
                for addr, _t, dat, bus in rx:
                    if bus != MOTOR_BUS or not (0x581 <= addr <= 0x584) or len(dat) < 8:
                        continue
                    node = addr - 0x580
                    idx = dat[1] | (dat[2] << 8)
                    if dat[0] == 0x43:
                        val = int.from_bytes(dat[4:8], "little", signed=True)
                    elif dat[0] == 0x4B:
                        val = int.from_bytes(dat[4:6], "little", signed=True)
                    elif dat[0] == 0x80:
                        code = int.from_bytes(dat[4:8], "little")
                        self._log(f"SDO 거부 N{node} 0x{idx:04X}:{dat[3]:02X} "
                                  f"→ abort 0x{code:08X} ({P.abort_text(code)})")
                        continue
                    else:
                        continue
                    out.setdefault(node, {})[idx] = val
                if out:
                    self._rx_at = time.monotonic()
                self._absorb(out)

                # ── 구동 재송신 + 응답 끊김 워치독 (원본 High ③과 같은 조치) ──
                # 재송신: 프레임 1장 유실이 곧 지령 소실이던 것을 막는다. 0 도 재송신한다.
                # 지령 워치독: 새 지령이 CMD_TTL_S 넘게 없으면 0 으로 수렴시킨다.
                # 상위(UI·조그)가 죽어도 로봇이 계속 가지 않게 하는 유일한 장치다.
                if self._drive_units != 0 and self._cmd_at \
                        and (time.monotonic() - self._cmd_at) > CMD_TTL_S:
                    self._log(f"지령 워치독 — {CMD_TTL_S:.1f}초 넘게 새 지령이 없어 구동을 0 으로")
                    self._drive_units = 0

                # 워치독: 응답이 RX_TTL_S 넘게 없으면 버스 상태를 모르는 것이므로 0 으로 간다.
                if self._rx_at and (time.monotonic() - self._rx_at) > RX_TTL_S \
                        and self._drive_units != 0:
                    self._log(f"워치독 — {RX_TTL_S:.0f}초 넘게 드라이브 응답이 없어 구동을 0 으로")
                    self.drive(0.0)
                else:
                    self._send([P.drive_velocity_frame(n, self._drive_units, MOTOR_BUS)
                                for n in DRIVE_NODES])
                # 조향도 같은 이유로 재송신한다(마스터는 28 ms 주기 연속 송신).
                # ⚠ **호밍 중에는 보내지 않는다.** 드라이브가 내부 호밍 루틴으로 −리밋을
                #   탐색하는 동안 외부 PP setpoint 를 밀어넣으면 같은 축을 두 주체가 다툰다.
                #   `RelayBackend._loop` 은 같은 자리를 `not self._homing and not self._estop`
                #   으로 막고 있었고 여기만 빠져 있었다.
                if self._steer_counts and not self._homing:
                    self._send([f for n, c in self._steer_counts.items()
                                for f in P.steer_target_frames(n, int(c), MOTOR_BUS)])
            except Exception as exc:
                self._run = False
                self._log(f"폴링 중단: {type(exc).__name__}: {exc}")
                return
            time.sleep(0.12)

    def _absorb(self, data: dict) -> None:
        """폴링 응답을 모터 표와 조향 실측으로 환산한다.

        위치는 `(0x6064 − 영점) / 57344` 로 °, 속도는 0.1 r/min 이라 ÷10, 전류는 0.01 A 라 ÷100.
        호밍 중에는 `0x6064` 가 실위치가 아니라 0 을 돌려주므로 그 구간의 각도는 갱신하지 않는다.
        """
        for node, vals in data.items():
            deg = rpm = amp = None
            if 0x6041 in vals:
                self._status_word[node] = vals[0x6041]
            if 0x6064 in vals and node in STEER_HOME and not self._homing:
                deg = (vals[0x6064] - STEER_HOME[node]) / COUNTS_PER_DEG
                self._set_meas(node, deg)
            if 0x606C in vals:
                rpm = vals[0x606C] / 10.0
            if 0x6078 in vals:
                amp = vals[0x6078] / 100.0
            self._rows[node] = (deg, rpm, amp)
