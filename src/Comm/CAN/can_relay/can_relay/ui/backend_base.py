#!/usr/bin/env python3
"""시험 GUI 백엔드 인터페이스 — UI 는 이 계약만 알고, 어느 경로로 나가는지는 모른다.

설계 근거: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`.

## 왜 이렇게 나눴나

UI 가 2벌이면 실기에서 차이가 나와도 **백엔드 차이인지 UI 차이인지 가릴 수 없다.**
그래서 위젯 트리는 1벌로 고정하고, 아래 계약을 만족하는 백엔드를 갈아 끼운다:

- `Ros2Backend`   — `can_relay_node` 경유(토픽·서비스)
- `DirectBackend` — 판다 USB 직결(원본 `Tools/amr_test_gui/gui.py` 와 같은 경로)

## capability

백엔드마다 **할 수 있는 일이 다르다.** UI 는 못 하는 기능의 버튼을 지우지 않고
**비활성 + 사유 툴팁**으로 남긴다 — 그래야 화면이 항상 같고, 무엇이 다른지가 드러난다.

## 스레드 규약

`CAP_*` 조작 메서드 중 **`(bool, str)` 를 돌려주는 것은 블로킹**이다 — UI 스레드에서 부르지 말고
작업 스레드에서 부른다. 나머지(`steer_*`·`drive`·`estop`)는 즉시 반환한다.
조회 메서드(`meas_angle`·`motor_rows`·`status`)는 **락 안에서 사본을 만들어** 돌려주므로
어느 스레드에서 불러도 된다.
"""
from __future__ import annotations

from typing import Optional

# ── capability 이름 ───────────────────────────────────────────────────────
CAP_SCAN = "scan"               # 판다 열거 (CAN 프레임 없음)
CAP_USB = "usb"                 # USB 개폐 (CAN 프레임 없음)
CAP_ENGAGE = "engage"           # 제어권 획득/반환
CAP_ESTOP = "estop"             # 소프트 E-stop 래치
CAP_STOP = "stop"               # 정지
CAP_HOME = "home"               # 조향 원점 복귀
CAP_STEER_AXIS = "steer_axis"   # 축별 조향
CAP_STEER_ALL = "steer_all"     # 전축 동일각(crab)
CAP_DRIVE = "drive"             # 구동 속도
CAP_MOTOR_TABLE = "motor_table"  # 모터 표(각도·회전·전류) 채우기

#: 호밍 **취소**는 capability 목록에 두지 않는다 — 드라이버에는 서비스가 있으나
#: UI 는 노출하지 않기로 했다. 취소해도 축이 어중간한 위치에 남아 어차피 다시 호밍해야 하므로
#: 얻는 것이 없다(ADR 2026-08-04 §Decision ②, 사용자 결정).


class BackendBase:
    """UI 가 기대하는 계약. 구현체는 `name`·`capabilities` 를 반드시 채운다."""

    name: str = "(미지정)"
    capabilities: frozenset = frozenset()

    # ── 수명주기 ──────────────────────────────────────────────────────
    def start(self) -> None:
        """백그라운드 자원(스레드·노드) 기동. 하드웨어를 열지 않는다."""

    def shutdown(self, reason: str = "") -> None:
        """정지 → 제어권 반환 → 자원 해제. **멱등이어야 한다** — 종료 경로가 여럿이다."""

    # ── 조회 (어느 스레드에서나) ──────────────────────────────────────
    def meas_angle(self, node: int) -> Optional[float]:
        """그 축의 실측 조향각(°). **신선하지 않으면 None** — 오래된 값을 실측인 척하지 않는다."""
        raise NotImplementedError

    def motor_rows(self) -> dict:
        """`{node: (각도°|None, 회전|None, 전류A|None)}`. 모르는 칸은 None 으로 둔다."""
        return {}

    def status(self) -> tuple:
        """`(텍스트, 정상인가, 제어권 보유인가)` — 하단 상태 바용."""
        raise NotImplementedError

    def settled(self, target_deg: float, tol_deg: float, nodes) -> bool:
        """**모든 조향축**이 허용치 안인가. 실측 없는 축은 정착으로 치지 않는다."""
        for n in nodes:
            cur = self.meas_angle(n)
            if cur is None or abs(target_deg - cur) > tol_deg:
                return False
        return True

    # ── 조작: 블로킹 (작업 스레드에서) ────────────────────────────────
    def scan(self) -> tuple:
        """판다 열거. 반환 `(성공, 메시지)`."""
        return False, f"{self.name}: 검색 미지원"

    def set_usb(self, on: bool) -> tuple:
        return False, f"{self.name}: USB 개폐 미지원"

    def set_engaged(self, on: bool) -> tuple:
        raise NotImplementedError

    def stop(self) -> tuple:
        raise NotImplementedError

    def home(self) -> tuple:
        """조향 원점 복귀. ⚠ **물리 스윙 100°+**. 취소 경로는 노출하지 않는다."""
        raise NotImplementedError

    # ── 조작: 즉시 반환 ───────────────────────────────────────────────
    def estop(self, on: bool) -> None:
        raise NotImplementedError

    def steer_axis(self, node: int, deg: float) -> None:
        raise NotImplementedError

    def steer_all(self, deg: float) -> None:
        raise NotImplementedError

    def drive(self, mmps: float) -> None:
        raise NotImplementedError

    # ── 편의 ─────────────────────────────────────────────────────────
    def can(self, cap: str) -> bool:
        return cap in self.capabilities

    def why_not(self, cap: str) -> str:
        """그 기능을 못 쓰는 이유 1줄 — 버튼 툴팁에 그대로 쓴다."""
        return f"{self.name} 백엔드에서는 이 기능을 쓰지 않습니다"
