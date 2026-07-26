#!/usr/bin/env python3
"""SEER SRC 에서 라이다 장착 pose(install_info)를 조회해 출력한다.

재장착·재캘리브 시 이 스크립트로 최신 값을 읽어 seer_lidar_tf_launch.py 의
LIDARS 상수를 갱신한다(사용자 지시: 요청 시에만 변경).

프로토콜: SEER Robokit NetProtocol(TCP). 헤더 16B(5A 01 | num | len | type | resv[6]).
Robot Status API 포트 19204, 레이저 조회 API 1009 → 응답 11009.
출처: References/Seer-Driver/robokit_tcp_api_laser.md

사용: python3 seer_read_lidar_install.py [SEER_IP]
"""
import socket
import struct
import json
import sys

SEER = sys.argv[1] if len(sys.argv) > 1 else "192.168.44.82"
PORT = 19204
API_LASER_REQ = 1009


def query(api_type, body=b"", timeout=3.0):
    hdr = struct.pack(">BBHIH6s", 0x5A, 0x01, 1, len(body), api_type, b"\x00" * 6)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((SEER, PORT))
    s.sendall(hdr + body)
    rhdr = b""
    while len(rhdr) < 16:
        c = s.recv(16 - len(rhdr))
        if not c:
            break
        rhdr += c
    _, _, _, dlen, rtype, _ = struct.unpack(">BBHIH6s", rhdr)
    data = b""
    while len(data) < dlen:
        c = s.recv(dlen - len(data))
        if not c:
            break
        data += c
    s.close()
    return rtype, data


def main():
    rtype, data = query(API_LASER_REQ)
    j = json.loads(data.decode("utf-8", "replace"))
    if j.get("ret_code") != 0:
        print(f"[경고] ret_code={j.get('ret_code')} err_msg={j.get('err_msg')}")
    print(f"# SEER {SEER}:{PORT} API {API_LASER_REQ}->{rtype}  (ret_code={j.get('ret_code')})")
    print("# seer_lidar_tf_launch.py 의 LIDARS 에 반영할 값:")
    for laser in j.get("lasers", []):
        name = laser.get("device_info", {}).get("device_name", "?")
        ii = laser.get("install_info", {})
        child = "scan_front" if "front" in name.lower() else "scan_rear" if "rear" in name.lower() else name
        print(f'    ("{child}", {ii.get("x")}, {ii.get("y")}, 0.0, {ii.get("yaw")}),  # {name}')


if __name__ == "__main__":
    main()
