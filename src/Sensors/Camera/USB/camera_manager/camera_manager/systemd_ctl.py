# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""usb-cam@ systemd 유닛 제어 래퍼 — ROS 무의존.

상태 조회(is-active)는 무권한, 제어(start/stop/restart)는 sudo -n 을 쓴다.
sudoers 허용은 Tools/camera_service/install.sh 가 /etc/sudoers.d/camera-manager
로 설치하며, usb-cam@ 유닛 3동사만 무암호다(전 명령 아님).
"""
from __future__ import annotations

import subprocess

_SYSTEMCTL = "/usr/bin/systemctl"
_SUDO = "/usr/bin/sudo"

# sudoers 미설치 환경에서 sudo -n 이 거부될 때 사용자에게 낼 안내문.
_SUDO_HINT = (
    "sudo 무암호 허용이 없다 — 설치: cd Tools/camera_service && sudo ./install.sh"
)


def unit_name(cam: str) -> str:
    """논리 이름 → systemd 인스턴스 유닛명."""
    return f"usb-cam@{cam}.service"


class SystemdControl:
    """systemctl 호출 래퍼. runner 주입으로 단위 테스트에서 실호출을 대체한다."""

    def __init__(self, runner=subprocess.run):
        self._run = runner

    def is_active(self, cam: str) -> bool | None:
        """유닛 활성 여부 — active→True, inactive/failed→False, 조회 실패→None."""
        try:
            result = self._run(
                [_SYSTEMCTL, "is-active", unit_name(cam)],
                capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        state = (result.stdout or "").strip()
        if state == "active":
            return True
        if state in ("inactive", "failed", "activating", "deactivating"):
            # activating 은 아직 프레임이 없을 수 있으나 유닛 관점에선 비활성이
            # 아니다 — 다만 판정은 프레임 신선도가 우선하므로 False 로 뭉치지
            # 않고 activating/deactivating 도 False 로 둔다(정지 취급: 자동
            # 개입 억제 쪽이 보수적이다).
            return False
        return None

    def control(self, verb: str, cam: str) -> tuple[bool, str]:
        """start|stop|restart 실행. (성공 여부, 메시지) 반환 — 예외를 던지지 않는다."""
        if verb not in ("start", "stop", "restart"):
            return False, f"허용되지 않는 동사: {verb}"
        try:
            result = self._run(
                [_SUDO, "-n", _SYSTEMCTL, verb, unit_name(cam)],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, f"{verb} {cam} 실행 실패: {error}"
        if result.returncode == 0:
            return True, f"{verb} {cam} 완료"
        stderr = (result.stderr or "").strip()
        if "password is required" in stderr or "a password is required" in stderr:
            return False, f"{verb} {cam} 거부 — {_SUDO_HINT}"
        return False, f"{verb} {cam} 실패(rc={result.returncode}): {stderr}"
