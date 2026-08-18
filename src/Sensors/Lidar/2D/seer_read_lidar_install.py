#!/usr/bin/env python3
"""SEER SRC 에서 라이다 장착 pose(install_info)를 조회해 출력한다.

재장착·재캘리브 시 이 스크립트로 최신 값을 읽어 seer_lidar_tf_launch.py 의
LIDARS 상수를 갱신한다(사용자 지시: 요청 시에만 변경).

프로토콜 구현은 여기 있지 않다 — `src/Comm/seer_tcp_ip` 가 저장소에서 Seer 와 TCP 로
말하는 유일한 지점이다(ADR docs/adr/2026-08-07-seer-api-tcp-hal.md).
Robot Status API 포트 19204, 레이저 조회 API 1009 → 응답 11009.

사용: python3 seer_read_lidar_install.py [SEER_IP]
"""
import os
import sys

try:
    from seer_tcp_ip import API_PORT_STATE, SeerApi
except ImportError:  # colcon install 미소싱 환경 — 소스 트리에서 직접 집는다
    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../Comm/seer_tcp_ip")
    )
    from seer_tcp_ip import API_PORT_STATE, SeerApi

SEER = sys.argv[1] if len(sys.argv) > 1 else "192.168.44.82"


def main():
    with SeerApi(SEER, timeout=3.0) as client:
        lasers = client.get_lasers()
    print(f"# SEER {SEER}:{API_PORT_STATE} API 1009 (install_info)")
    print("# seer_lidar_tf_launch.py 의 LIDARS 에 반영할 값:")
    for laser in lasers:
        name = laser.get("device_info", {}).get("device_name", "?")
        ii = laser.get("install_info", {})
        low = name.lower()
        child = "scan_front" if "front" in low else "scan_rear" if "rear" in low else name
        print(f'    ("{child}", {ii.get("x")}, {ii.get("y")}, 0.0, {ii.get("yaw")}),  # {name}')


if __name__ == "__main__":
    main()
