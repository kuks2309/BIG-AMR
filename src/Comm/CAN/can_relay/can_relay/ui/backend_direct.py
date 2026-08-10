#!/usr/bin/env python3
"""판다 USB 직결 백엔드 — 원본 `Tools/amr_test_gui/gui.py` 와 **같은 경로·같은 바이트**.

설계 근거: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`.

## 이식 원칙 — 고쳐진 원본을 그대로 옮긴다

이 백엔드의 존재 이유는 **비교 기준**이다. 원본과 같은 프레임을 같은 순서로 내야 실기에서
「UI 는 같은데 백엔드만 다르다」가 성립한다.

⚠ **2026-08-04 갱신** — 원본의 결함 11건이 먼저 수정됐다(사용자 지시: 「먼저 원본을 고치고
나서 ros2 backend 연결하는 것이 정석」). 이제 이 백엔드는 **고쳐진 원본**을 반영한다:

| 원본 결함 (`docs/code_review/amr-test-gui/2026-08-03.md`) | 원본 | 여기 |
|---|---|---|
| High ① 정착 판정에 피드백 신선도 없음 | 수정 — `_set_meas` + `MEAS_TTL_S` | 반영 |
| High ② `heartbeat` 가 `_can_lock` 밖 | 수정 — 락 안으로 | 반영 |
| High ③ 구동 단발 송신 · 워치독 없음 | 수정 — 주기 재송신 + 응답 끊김 워치독 | 반영 |
| Medium ③ 판다 2대 이상 진행 가능 | 수정 — 차단 | 반영 |
| Medium ④ 반환 시 정지 실패 무고지 | 수정 — 로그 | 반영 |
| Low ① 정지↔구동 경합 창 | 수정 — RLock 단일 임계구역 | 반영 |
| Low ② `panda is None` 미검사 | 수정 — 진입부 가드 | 반영 |

`heartbeat` 락·신선도·재송신은 **CAN 프레임 바이트를 바꾸지 않는다**(타이밍·반복만 바뀐다) —
따라서 `test_backend_swap.py` 의 바이트 동일성 회귀는 그대로 유효하다.

바이트 조립은 `can_relay.protocol` 을 쓴다. 원본의 손조립과 **바이트 동일**함이 회귀로 고정돼 있다
(`test/test_port_equivalence.py`, `test/test_master_frame_match.py`).
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

# ── 원본 gui.py 와 같은 상수 (값 근거는 원본 주석·README) ─────────────────
SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE, CAN_KBPS = 30, 250
COUNTS_PER_DEG = 57344
_STEER_HOME_FALLBACK = {3: 7871815, 4: 7840086}
VEL_PER_MMPS, VEL_MAX_UNITS = 24.447, 4889
STEER_LIMIT_DEG = 90.0
DRIVE_NODES, STEER_NODES = (1, 2), (3, 4)

HOMING_SPEED = 2500         # 0x6099:00 — 0.1 r/min → 250 r/min
HOMING_TIMEOUT_S = 90.0
HOMING_START_S = 10.0
BIT15 = 1 << 15
MEAS_TTL_S = 1.0            # 이보다 오래된 실측은 없는 것으로 친다(원본 High ①). **기본값일 뿐이다** —
#                             인스턴스가 `meas_ttl_s` 로 들고 런타임에 바꿀 수 있다(리뷰 Low ③).
RX_TTL_S = 1.0              # 이보다 오래 응답이 없으면 구동을 0 으로(원본 High ③)

# ⚠ 깊이를 세지 않는다. `dirname` 6회로 적었다가 `.../src/Tools/...` 를 가리켜
#   `ModuleNotFoundError: No module named 'panda'` 가 났다(2026-08-04 오프스크린 스모크).
#   `link.py:_find_repo_root` 가 문서화해 둔 것과 같은 off-by-one 이므로 그 함수를 쓴다.
_KIT = os.path.join(_find_repo_root(__file__), "Tools", "docking_field_kit")


def _load_steer_home():
    """조향 0° counts 를 **정본 YAML 에서 읽는다**. 실패하면 사본으로 내려간다.

    원본 `Tools/amr_test_gui/gui.py` 의 `_load_steer_home` 과 같은 방식이다 — 두 구현이
    **같은 출처**를 봐야 `--backend` 를 바꿔도 같은 각도로 간다. 예전에는 이 파일만 리터럴이라
    정본이 바뀌면 direct 만 옛 값으로 남았다(2026-08-04 리뷰 Medium ②).

    반환 `(값, 출처 설명)`.
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
    """가동범위 클램프 후 조향 절대위치 counts. 원본 `gui.py:65-71` 과 같은 식."""
    deg = max(-STEER_LIMIT_DEG, min(STEER_LIMIT_DEG, deg))
    return deg, int(round(STEER_HOME[node] + deg * COUNTS_PER_DEG))


def drive_units(mmps: float, raw_sign: int) -> int:
    """구동 raw 환산 + 상한 클램프. 원본 `gui.py:74-77` 과 같은 식."""
    return max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS,
                                   int(round(raw_sign * mmps * VEL_PER_MMPS))))


def _panda_class():
    """comma.ai panda 라이브러리 로드(필드킷 동봉본). 원본 `gui.py:100-105` 과 같다."""
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
        # ⚠ TTL 을 **인스턴스 상태**로 든다. 예전에는 모듈 상수를 직접 읽어, ros2 백엔드는
        #   ROS 파라미터로 런타임 조정이 되는데 direct 백엔드만 안 되는 비대칭이 있었다
        #   (리뷰 Low ③). 같은 개념은 `--backend` 와 무관하게 같은 방식으로 조정돼야 한다.
        self.meas_ttl_s = float(meas_ttl_s)
        self._log = log or (lambda _m: None)
        self.panda = None
        self._cls = None
        self._run = False
        self._th = None
        self._can_lock = threading.RLock()  # 폴링·조그가 버스를 공유한다
        #   RLock 인 이유: 「정지 확인 → 구동 송신」을 한 임계구역에 넣어야 하는데 그 안에서
        #   `drive()` → `_send()` 가 같은 락을 다시 잡는다(원본 Low ①과 동일 조치).
        self._meas_deg = {}                 # node -> 실측 조향각(°)
        self._meas_at = {}                  # node -> 그 각도를 받은 시각(신선도 판정용)
        self._drive_units = 0               # 마지막 구동 지령(raw) — 폴 루프가 재송신한다
        self._steer_counts: dict = {}       # 마지막 조향 목표(counts) — 폴 루프가 재송신한다
        #   ⚠ 2026-08-05 신설. 예전에는 조향을 **축당 1회만** 보냈다 — 프레임 1장이 유실되면
        #     그 축은 지령을 통째로 못 받는다. 실제로 조그 첫 지령에서 N4 가 움직이지 않은
        #     사례가 있고(22:42:53, SDO 거부 없음), 마스터 Seer 는 **28 ms 주기로 연속
        #     재송신**한다(캡처 12,928회/180초). 구동은 이미 재송신하는데 조향만 빠져 있었다.
        self._rx_at = 0.0                   # 마지막으로 드라이브 응답을 받은 시각
        self._status_word = {}              # node -> 0x6041
        self._rows = {}                     # node -> (deg, rpm, amp)
        self._serials = []
        self._released = False
        self._homing = False

    # ── 수명주기 ──────────────────────────────────────────────────────
    def shutdown(self, reason: str = "") -> None:
        """원본 `safe_release` 와 같은 멱등 해제 — 제어권 반환 후 USB 닫기."""
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
        """**TTL 밖이면 None** — 폴링이 멈춘 뒤 남은 값을 실측인 척 쓰지 않는다(원본 High ①)."""
        node = int(node)
        deg = self._meas_deg.get(node)
        if deg is None:
            return None
        at = self._meas_at.get(node)
        if at is None or (time.monotonic() - at) > self.meas_ttl_s:
            return None
        return deg

    def _set_meas(self, node: int, deg: float) -> None:
        """실측 1건 반영 — **값과 시각을 함께** 남긴다(따로 쓸 수 있으면 언젠가 따로 쓰인다)."""
        self._meas_deg[node] = deg
        self._meas_at[node] = time.monotonic()

    def motor_rows(self) -> dict:
        return dict(self._rows)

    def link_status(self) -> tuple:
        """판다가 열려 있는가 — direct 백엔드에는 드라이버가 없다."""
        if self.panda is None:
            return (False, "판다 · ⚠ 미연결")
        ser = (self._serials[0] if getattr(self, "_serials", None) else "")
        return (True, f"판다 · 연결됨{(' ' + ser) if ser else ''}")

    def status(self) -> tuple:
        if self.panda is None:
            return "판다 USB 미연결", False, False
        if not self._run:
            return "USB 연결됨 · 제어권 미획득", True, False
        return "제어권 보유 — intercept · 폴링 중", True, True

    # ── 조작: 블로킹 ──────────────────────────────────────────────────
    def scan(self) -> tuple:
        """판다 열거 — **USB 를 열지 않는다.** 원본 `gui.py:748-771` 과 같은 판정."""
        try:
            self._serials = list(_panda_class().list())
        except Exception as exc:
            return False, f"판다 검색 실패: {type(exc).__name__}: {exc}"
        if not self._serials:
            return False, "판다 없음 — USB 연결·udev 규칙 확인"
        if len(self._serials) == 1:
            return True, f"판다 검출: {self._serials[0]}"
        # **차단한다** — 어느 장치에 지령이 갈지 모르는 채 진행할 수 없다(원본 Medium ③).
        # ⚠ 대수·시리얼을 **비우기 전에** 잡는다. 예전에는 `self._serials = []` 뒤에
        #   `len(self._serials) or '여러'` 를 써서 **항상 "여러대"** 가 되어 실제 대수가
        #   보고에서 사라졌다(2026-08-04 리뷰 Medium ①, 같은 날 조치가 만든 회귀).
        found = list(self._serials)
        self._serials = []
        return False, (f"⚠ 판다 {len(found)}대 검출({', '.join(found)}) — 1 PC 1대 원칙 위반. "
                       f"어느 장치에 지령이 갈지 알 수 없으므로 연결을 막습니다. "
                       f"한 대만 남기고 다시 검색하세요.")

    def set_usb(self, on: bool) -> tuple:
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
        """제어권 획득/반환. 원본 `gui.py:803-837` 의 순서 그대로.

        순서가 곧 사양이다: safety_mode → 버스속도 → 버스 enable → auth(0xe9) → intercept(0xe8).
        """
        if self.panda is None:
            return False, "USB 를 먼저 연결하세요"
        P_ = self._cls
        try:
            if on:
                self.panda.set_safety_mode(SEER_GATE, 0)
                for b in (SEER_BUS, MOTOR_BUS):
                    self.panda.set_can_speed_kbps(b, CAN_KBPS)
                    self.panda.set_can_enable(b, True)
                self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE9, 1, 0, b"")
                self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE8, 1, 0, b"")
                # ── 구동축 브링업 — 제어권 확인 후 · 폴 스레드 시작 **전** ──
                # `RelayBackend.start()` 가 같은 위치에서 보내는 것과 같은 시퀀스다.
                # 이것이 없으면 can_relay 프로세스 재시작 뒤 구동축이 `0x60FF` 를 받고도
                # 돌지 않는다 — 2026-08-08 실기에서 이 경로로 재현됐다
                # (node1 0.1 rpm / node2 78.2 rpm). 상세는 `backend.py:_write_bringup`.
                # ⚠ **조향축에는 보내지 않는다** — fault reset 이 조향 위치 카운터를 지워
                #   0° 기준이 무효가 된다(같은 날 실기 확인). 조향 기준 복구는 호밍 소관이다.
                self._write_bringup()
                self._run = True
                self._th = threading.Thread(target=self._loop, daemon=True, name="poll")
                self._th.start()
                return True, "제어권 획득 — 릴레이 intercept, Seer 에서 가져옴"
            try:
                self.drive(0.0)                 # 반환 전 반드시 정지(원본과 같음)
            except Exception as exc:
                # 삼키지 않는다 — 정지가 못 나간 채 auth·intercept 를 내리면 드라이브가
                # 마지막 속도를 문 채 Seer 로 넘어간다(원본 Medium ④).
                self._log(f"⚠ 제어권 반환 전 정지 송신 실패 — {type(exc).__name__}: {exc}. "
                          f"드라이브가 마지막 지령을 유지할 수 있습니다. E-STOP 을 확인하세요.")
            self._run = False
            if self._th is not None:
                self._th.join(timeout=1.0)
                self._th = None
            self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE9, 0, 0, b"")
            self.panda._handle.controlWrite(P_.REQUEST_OUT, 0xE8, 0, 0, b"")
            self.panda.set_safety_mode(0, 0)
            return True, "제어권 반환 — passthrough (USB 유지)"
        except Exception as exc:
            return False, f"제어권 처리 실패: {type(exc).__name__}: {exc}"

    def stop(self) -> tuple:
        """원본의 「정지」 — **구동만 0**. 조향은 현 위치를 유지한다(지령 없음).

        ⚠ 원본에 조향을 세우는 경로가 없다는 것은 실측으로 확인했다(2026-08-04):
        `grep -c halt_steer Tools/amr_test_gui/gui.py` → **0**,   # 2026-08-03 실행 기록
        (그 함수는 2026-08-05 `hold_steer_at_measured` 로 개명됐다 — 위 명령은 당시 그대로 남긴다)
        `grep -n 0x607A …` → 조향 목표를 쓰는 곳은 `_steer_axis`(:443) 하나뿐이고 정지 경로가 아니며,
        `gui.py:875-879` 의 「정지」는 `_drive(0)` + 로그 "조향은 현 위치 유지" 다.
        드라이버 경유(`ros2`)는 `stop_all` 로 조향까지 다루지만 **여기서는 옮기지 않는다** —
        옮기면 프레임 스트림이 달라져 비교가 성립하지 않는다.

        ⚠ 2026-08-05: 조향 목표 **재송신은 멈춘다.** 프레임을 새로 보내는 것이 아니라
        우리가 반복해 내던 것을 그치는 것이라 위 「지령 없음」과 어긋나지 않는다.
        멈추지 않으면 정지 후에도 우리 조향 목표가 계속 나간다.
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
        """조향 2축 호밍. 원본 `gui.py:946-995` 과 같은 3프레임 + 2상 판정.

        `0x6098`(homing method)은 **쓰지 않는다** — 드라이브 저장값을 덮어쓰면 리셋 모드가 꺼진다.
        구동 노드(1·2)는 기계적 원점이 없어 호밍 대상이 아니다.
        """
        if not self._run:
            return False, "제어권을 먼저 획득하세요"
        if self._homing:
            return False, "호밍 이미 진행 중"
        self._homing = True
        try:
            self.drive(0.0)                     # 호밍 전 구동은 반드시 0
            self._status_word.clear()           # 직전 상태워드를 완료로 오독하지 않도록
            for n in STEER_NODES:
                self._send([P.sdo_write(n, 0x6040, 0x86, 2, bus=MOTOR_BUS)])
                self._send([P.sdo_write(n, 0x6099, HOMING_SPEED, 4, bus=MOTOR_BUS)])
                self._send([P.sdo_write(n, 0x60FB, 1, 1, sub=4, bus=MOTOR_BUS)])
            self._log("호밍 개시 — 조향 2축. 완료까지 30초 이상 걸립니다.")
            return self._wait_homed()
        except Exception as exc:
            return False, f"호밍 중단: {type(exc).__name__}: {exc}"
        finally:
            self._homing = False

    def _wait_homed(self) -> tuple:
        """상태워드 bit15 **2상** 판정 — 먼저 0(진행 중)을 보고, 그 다음 1(완료)을 기다린다.

        bit15 가 1 인 것만 보면 안 된다 — 이전에 호밍을 마친 축은 시작 전부터 1 이다.
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
                return True, f"{time.time() - t0:.0f}초 소요. 조향 0° 복귀까지 확인하세요."
            time.sleep(0.1)
        return False, f"{HOMING_TIMEOUT_S:.0f}초 안에 완료 신호가 오지 않았습니다."

    # ── 조작: 즉시 반환 ───────────────────────────────────────────────
    def steer_axis(self, node: int, deg: float) -> None:
        """한 축에만 0x607A + 0x6040=0x3F. 원본 `_steer_axis` 와 같은 2프레임.

        지령을 **상태로 남겨** 폴 루프가 재송신한다(마스터와 같은 방식).
        """
        _applied, counts = steer_counts(int(node), float(deg))
        self._steer_counts[int(node)] = int(counts)
        self._send(P.steer_target_frames(int(node), counts, MOTOR_BUS))

    def steer_all(self, deg: float) -> None:
        for n in STEER_NODES:
            self.steer_axis(n, deg)

    def drive(self, mmps: float) -> None:
        """구동 2축 0x60FF. 지령을 **상태로 남겨** 폴 루프가 재송신한다(원본 High ③)."""
        units = drive_units(abs(float(mmps)), 1 if mmps >= 0 else -1)
        self._drive_units = units
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
        if self.panda is None:
            raise RuntimeError("판다 미연결 — USB 를 먼저 연결하세요")
        with self._can_lock:
            for f in frames:
                self.panda.can_send(f.can_id, f.data[:8], f.bus)

    def _loop(self) -> None:
        """폴링 스레드 — 원본 `gui.py:1014-1062` 과 같은 순서·같은 주기.

        heartbeat(0xf3)는 **락 안에서** 보낸다 — 밖에 있으면 조그·호밍 스레드가 락을 쥐고
        `can_send` 하는 동안 같은 USB 핸들에 심박이 겹친다(원본 High ②, 2026-08-04 수정).
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
                for addr, _t, dat, bus in self.panda.can_recv():
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
                # 워치독: 응답이 RX_TTL_S 넘게 없으면 버스 상태를 모르는 것이므로 0 으로 간다.
                if self._rx_at and (time.monotonic() - self._rx_at) > RX_TTL_S \
                        and self._drive_units != 0:
                    self._log(f"워치독 — {RX_TTL_S:.0f}초 넘게 드라이브 응답이 없어 구동을 0 으로")
                    self.drive(0.0)
                else:
                    self._send([P.drive_velocity_frame(n, self._drive_units, MOTOR_BUS)
                                for n in DRIVE_NODES])
                # 조향도 같은 이유로 재송신한다(마스터는 28 ms 주기 연속 송신).
                if self._steer_counts:
                    self._send([f for n, c in self._steer_counts.items()
                                for f in P.steer_target_frames(n, int(c), MOTOR_BUS)])
            except Exception as exc:
                self._run = False
                self._log(f"폴링 중단: {type(exc).__name__}: {exc}")
                return
            time.sleep(0.12)

    def _absorb(self, data: dict) -> None:
        """폴링 결과를 표·각도로. 원본 `_on_motor_data` 와 같은 환산·같은 게이트."""
        for node, vals in data.items():
            deg = rpm = amp = None
            if 0x6041 in vals:
                self._status_word[node] = vals[0x6041]
            # 호밍 중 0x6064 는 0 을 돌려주므로 그 구간은 각도를 갱신하지 않는다(원본과 동일).
            if 0x6064 in vals and node in STEER_HOME and not self._homing:
                deg = (vals[0x6064] - STEER_HOME[node]) / COUNTS_PER_DEG
                self._set_meas(node, deg)
            if 0x606C in vals:
                rpm = vals[0x606C] / 10.0
            if 0x6078 in vals:
                amp = vals[0x6078] / 100.0
            self._rows[node] = (deg, rpm, amp)
