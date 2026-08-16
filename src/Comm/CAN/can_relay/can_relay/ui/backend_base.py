#!/usr/bin/env python3
"""시험 GUI 백엔드 인터페이스 — UI 는 이 계약만 알고, 어느 경로로 나가는지는 모른다.

구현체는 둘이다. `Ros2Backend` 는 `can_relay_node` 의 토픽·서비스를 거치고,
`DirectBackend` 는 판다 USB 를 직접 연다. 위젯 트리는 한 벌이고 백엔드만 갈아 끼운다.

백엔드마다 할 수 있는 일이 다르므로 `capabilities` 로 선언한다. UI 는 못 하는 기능의
버튼을 지우지 않고 비활성 + 사유 툴팁으로 남긴다.
"""
from __future__ import annotations

from typing import Optional

# ── capability 이름 ───────────────────────────────────────────────────────
CAP_SCAN = "scan"               # 판다 열거 (CAN 프레임 없음)
CAP_USB = "usb"                 # USB 개폐 (CAN 프레임 없음)
CAP_ENGAGE = "engage"           # 제어권 획득/반환
CAP_STOP = "stop"               # 정지
CAP_HOME = "home"               # 조향 원점 복귀
CAP_STEER_AXIS = "steer_axis"   # 축별 조향
CAP_STEER_ALL = "steer_all"     # 전축 동일각(crab)
CAP_DRIVE = "drive"             # 구동 속도
CAP_MOTOR_TABLE = "motor_table"  # 모터 표(각도·회전·전류) 채우기


class BackendBase:
    """UI 가 기대하는 계약. 구현체는 `name`·`capabilities` 를 반드시 채운다.

    스레드 규약: `(bool, str)` 를 돌려주는 조작 메서드는 **블로킹**이므로 작업 스레드에서
    부른다. `steer_*`·`drive` 는 즉시 반환한다. 조회 메서드(`meas_angle`·`motor_rows`·
    `status`)는 락 안에서 사본을 만들어 돌려주므로 어느 스레드에서 불러도 된다.

    비상정지는 이 계층에 없다 — GUI 가 그 버튼을 두지 않는다. 하드웨어 차단이 권위이며,
    드라이버 쪽에는 별도 계약이 따로 있다.
    """

    name: str = "(미지정)"
    capabilities: frozenset = frozenset()

    # ── 수명주기 ──────────────────────────────────────────────────────
    def start(self) -> None:
        """백그라운드 자원(스레드·노드)을 띄운다. 하드웨어는 열지 않는다."""

    def shutdown(self, reason: str = "") -> None:
        """정지 → 제어권 반환 → 자원 해제. 종료 경로가 여럿이므로 멱등이어야 한다."""

    # ── 조회 (어느 스레드에서나) ──────────────────────────────────────
    def meas_angle(self, node: int) -> Optional[float]:
        """그 축의 실측 조향각(°). 신선하지 않으면 `None` 을 돌려준다.

        오래된 값을 실측인 척 돌려주면 정착 판정이 멈춘 화면을 보고 통과한다.
        """
        raise NotImplementedError

    def motor_rows(self) -> dict:
        """`{node: (각도°|None, 회전|None, 전류 A|None)}`. 모르는 칸은 `None` 으로 둔다."""
        return {}

    def status(self) -> tuple:
        """`(텍스트, 정상인가, 제어권 보유인가)` — 로봇 상태를 하단 상태 바에 표시한다."""
        raise NotImplementedError

    def link_status(self) -> tuple:
        """`(연결됨, 텍스트)` — 이 백엔드가 상대와 **말이 통하는가**.

        `status()` 와 다르다. `status()` 는 로봇이 정상인가이고 이것은 통신이 살아 있는가다.
        둘을 섞으면 드라이버가 죽은 것과 로봇이 이상한 것을 화면에서 구분할 수 없다.
        ros2 는 드라이버 진단의 신선도로, direct 는 판다 개방 여부로 판정한다.
        """
        raise NotImplementedError

    def settled(self, target_deg: float, tol_deg: float, nodes) -> bool:
        """**모든 조향축**이 목표 ±`tol_deg`(°) 안인가. 실측 없는 축은 정착으로 치지 않는다."""
        for n in nodes:
            cur = self.meas_angle(n)
            if cur is None or abs(target_deg - cur) > tol_deg:
                return False
        return True

    # ── 조작: 블로킹 (작업 스레드에서) ────────────────────────────────
    def scan(self) -> tuple:
        """판다를 열거한다. USB 는 열지 않는다. 반환 `(성공, 메시지)`."""
        return False, f"{self.name}: 검색 미지원"

    def set_usb(self, on: bool) -> tuple:
        """판다 USB 를 열거나 닫는다. 반환 `(성공, 메시지)`."""
        return False, f"{self.name}: USB 개폐 미지원"

    def set_engaged(self, on: bool) -> tuple:
        """제어권을 획득하거나 반환한다. 반환 `(성공, 메시지)`."""
        raise NotImplementedError

    def stop(self) -> tuple:
        """구동을 멈춘다. 반환 `(성공, 메시지)`."""
        raise NotImplementedError

    def home(self) -> tuple:
        """조향 원점 복귀. 반환 `(성공, 메시지)`.

        축이 100° 넘게 물리적으로 돈다 — 이동구역을 확인한 뒤 호출한다.
        취소 경로는 노출하지 않는다: 중간에 끊으면 축이 어중간한 위치에 남아 다시
        호밍해야 하므로 얻는 것이 없다.
        """
        raise NotImplementedError

    # ── 조작: 즉시 반환 ───────────────────────────────────────────────
    def steer_axis(self, node: int, deg: float) -> None:
        """그 축 하나의 조향 목표를 `deg`(°)로 세운다."""
        raise NotImplementedError

    def steer_all(self, deg: float) -> None:
        """모든 조향축을 같은 각 `deg`(°)로 세운다(crab)."""
        raise NotImplementedError

    def drive(self, mmps: float) -> None:
        """구동 속도를 `mmps`(mm/s)로 세운다. 부호가 전·후진 방향이다."""
        raise NotImplementedError

    # ── 편의 ─────────────────────────────────────────────────────────
    def can(self, cap: str) -> bool:
        """그 capability 를 이 백엔드가 지원하는가."""
        return cap in self.capabilities

    def why_not(self, cap: str) -> str:
        """그 기능을 못 쓰는 이유 한 줄 — 버튼 툴팁에 그대로 쓴다."""
        return f"{self.name} 백엔드에서는 이 기능을 쓰지 않습니다"

    def supervisor_status(self):
        """감시자(relay_supervisor) 판정 `(verdict, message, age_s)`.

        감시자를 볼 수 없는 백엔드(직결 등)는 `None` 을 돌려준다 — 화면은 그것을
        「미지원」으로, `(None, …)` 튜플은 「아직 미수신」으로 구분해 그린다.
        """
        return None
