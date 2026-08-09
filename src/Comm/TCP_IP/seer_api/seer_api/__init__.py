"""Seer(SRC) Robokit TCP/IP API 클라이언트.

전송(transport) / 포트 정책(ports) / 편호 바인딩(api) 3층.
HAL 경계는 이 패키지가 아니라 ROS 인터페이스에 있다 — 상위 알고리즘 패키지는
이 패키지를 직접 import 하지 않는다(ADR docs/adr/2026-08-07-seer-api-tcp-hal.md).
"""
from .api import SeerApi
from .ports import (
    API_PORT_CONFIG,
    API_PORT_CTRL,
    API_PORT_OTHER,
    API_PORT_PUSH,
    API_PORT_STATE,
    API_PORT_TASK,
    is_guarded,
    observed_max_connections,
)
from .transport import (
    SeerConnectionLimitError,
    SeerGuardedPortError,
    SeerProtocolError,
    SeerTransport,
    pack,
    unpack_head,
)

__all__ = [
    "SeerApi",
    "SeerTransport",
    "SeerProtocolError",
    "SeerGuardedPortError",
    "SeerConnectionLimitError",
    "pack",
    "unpack_head",
    "is_guarded",
    "observed_max_connections",
    "API_PORT_STATE",
    "API_PORT_CTRL",
    "API_PORT_TASK",
    "API_PORT_CONFIG",
    "API_PORT_OTHER",
    "API_PORT_PUSH",
]
