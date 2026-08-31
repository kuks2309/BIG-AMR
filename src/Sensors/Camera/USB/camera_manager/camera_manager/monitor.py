# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""카메라 1대의 생존 판정 상태기계 — ROS 무의존 순수 로직.

판정 대상은 CCTV 경로(usb_cam_publisher → <cam>/image_raw/compressed)의 프레임
도착 여부다. 노드가 살아 있어도 프레임이 멈추면 장애로 본다 — 캡처 루프에는
재오픈 경로가 없어 프로세스 재시작만이 유일한 복구 수단이기 때문
(설계: docs/adr/2026-08-30-camera-management-mode.md).

자동 개입을 억제하는 3조건(같은 ADR §결정 4):
  ① depth 경로 활성 — 같은 물리 카메라를 OrbbecSDK 가 의도적으로 점유한 상태
  ② 장치 심링크 부재 — 재시작해도 exit 3 일 뿐, usb-cam@ 유닛의 5초 재시도
     루프가 이미 대기하고 있다
  ③ 유닛 inactive — 사용자의 의도적 정지를 자동으로 뒤집지 않는다
"""
from __future__ import annotations

from dataclasses import dataclass

# Decision.state 의 정의역. diagnostics·CLI 표시가 이 문자열을 그대로 쓴다.
STATE_OK = "ok"
STATE_STALL = "stall"
STATE_RESTARTING = "restarting"
STATE_NO_DEVICE = "no_device"
STATE_STOPPED = "stopped"
STATE_SUPPRESSED = "suppressed"
STATE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class MonitorConfig:
    """감시 임계 3종.

    stall_sec: 이 시간 넘게 프레임이 없으면 정체로 판정.
    restart_cooldown_sec: 자동 재시작 사이의 최소 간격(폭주 방지).
    startup_grace_sec: (재)기동 직후 판정 유예 — 노드 기동·장치 협상에 수 초가 든다.
    """

    stall_sec: float = 10.0
    restart_cooldown_sec: float = 30.0
    startup_grace_sec: float = 20.0


@dataclass(frozen=True)
class CameraInputs:
    """카메라 1대의 1틱 관측 입력.

    frame_age: 마지막 프레임 도착 후 경과(초). 한 번도 못 받았으면 None.
    unit_active: usb-cam@ 유닛 활성 여부. systemctl 조회 실패면 None(판정 불가).
    device_present: by-id 장치 심링크 실재 여부.
    depth_active: 같은 카메라의 depth 토픽에 퍼블리셔가 있는가(OrbbecSDK 점유 중).
    """

    frame_age: float | None
    unit_active: bool | None
    device_present: bool
    depth_active: bool


@dataclass(frozen=True)
class Decision:
    """1틱 판정 결과. restart 가 True 면 호출측이 유닛 재시작을 실행한다."""

    state: str
    restart: bool
    reason: str


class CameraMonitor:
    """카메라 1대의 판정자. 시각은 단조 시계(monotonic) 값을 주입받는다."""

    def __init__(self, name: str, config: MonitorConfig, now: float):
        self.name = name
        self._config = config
        # 기동 유예의 기준시각 — 감시자 생성 시각과 마지막 재시작 시각 중 나중 값.
        self._grace_ref = now
        self._last_restart: float | None = None
        self.consecutive_restarts = 0

    def note_external_restart(self, now: float) -> None:
        """외부(CLI 등)가 유닛을 재시작했음을 통보받는다.

        유예를 다시 열어, 방금 재시작된 유닛을 감시자가 겹쳐 재시작하는 일을
        막는다. 연속 재시작 카운터는 자동 개입만 세므로 건드리지 않는다.
        """
        self._grace_ref = now

    def evaluate(self, inputs: CameraInputs, now: float, auto_enabled: bool) -> Decision:
        """억제 조건 → 신선 판정 → 정체 처리 순으로 1틱을 판정한다.

        프레임 신선 판정이 유닛 상태보다 앞선다 — systemctl 조회는 캐시라
        낡을 수 있고, 프레임 도착이 카메라 생존의 근거 그 자체이기 때문.
        """
        cfg = self._config

        if inputs.depth_active:
            return Decision(STATE_SUPPRESSED, False, "depth 경로 사용 중(배타) — 자동 개입 억제")

        fresh = inputs.frame_age is not None and inputs.frame_age <= cfg.stall_sec
        if fresh:
            self.consecutive_restarts = 0
            return Decision(STATE_OK, False, "")

        if not inputs.device_present:
            return Decision(
                STATE_NO_DEVICE, False, "장치 심링크 부재 — usb-cam@ 재시도 루프가 대기 중")
        if inputs.unit_active is False:
            return Decision(STATE_STOPPED, False, "유닛 정지 상태(의도적 정지로 간주)")
        if inputs.unit_active is None:
            return Decision(STATE_UNKNOWN, False, "유닛 상태 판정 불가(systemctl 조회 실패)")

        # 여기부터는 정체: 유닛 활성 + 장치 실재 + 프레임 없음/낡음.
        grace_ref = self._grace_ref if self._last_restart is None else max(
            self._grace_ref, self._last_restart)
        if now - grace_ref < cfg.startup_grace_sec:
            return Decision(STATE_RESTARTING, False, "기동 유예 중")
        if not auto_enabled:
            return Decision(STATE_STALL, False, "정체 — 자동 재시작 꺼짐(camctl restart 필요)")
        if self._last_restart is not None and (
                now - self._last_restart < cfg.restart_cooldown_sec):
            return Decision(STATE_STALL, False, "정체 — 재시작 쿨다운 중")

        self._last_restart = now
        self.consecutive_restarts += 1
        return Decision(
            STATE_RESTARTING, True,
            f"정체 {inputs.frame_age if inputs.frame_age is not None else '∞'}s — "
            f"자동 재시작 {self.consecutive_restarts}회째")
