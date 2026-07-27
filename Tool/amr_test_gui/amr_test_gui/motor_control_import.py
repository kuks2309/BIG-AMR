"""정본 `motor_control` 드라이버 import 셔임 — 프로토콜 재구현을 막는 단일 관문.

본 툴은 비-ROS(colcon 미빌드) 이므로 소스 트리에서 직접 import 한다.
`backend`·`kinematics`·`protocol` 은 rclpy·python-can 무의존 순수 파이썬이라 이것으로 충분하다
(`driver_node` 만 rclpy 를 필요로 하며 본 툴은 쓰지 않는다).

경로 우선순위: 환경변수 `MOTOR_CONTROL_PATH` → 레포 상대경로(Tool/amr_test_gui 기준 ../../src/Actuators/motor_control).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.normpath(os.path.join(_HERE, "..", "..", "..",
                                         "src", "Actuators", "motor_control"))
MOTOR_CONTROL_PATH = os.environ.get("MOTOR_CONTROL_PATH", _DEFAULT)

if not os.path.isdir(os.path.join(MOTOR_CONTROL_PATH, "motor_control")):
    raise ImportError(
        f"정본 motor_control 패키지를 찾지 못했습니다: {MOTOR_CONTROL_PATH}\n"
        f"환경변수 MOTOR_CONTROL_PATH 로 경로를 지정하세요.")

if MOTOR_CONTROL_PATH not in sys.path:
    sys.path.insert(0, MOTOR_CONTROL_PATH)

from motor_control import protocol                                    # noqa: E402
from motor_control.backend import (BringupRefused, ModuleConfig,      # noqa: E402
                                   NodeSilent, NodeState, TongyiSdoBackend)
from motor_control.kinematics import ModuleCommand                    # noqa: E402

__all__ = ["protocol", "TongyiSdoBackend", "ModuleConfig", "NodeState",
           "ModuleCommand", "BringupRefused", "NodeSilent", "MOTOR_CONTROL_PATH"]
