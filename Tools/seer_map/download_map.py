#!/usr/bin/env python3
"""Seer 컨트롤러에서 현재 로드된 맵을 조회·다운로드한다 (읽기 전용).

프로토콜: Robokit NetProtocol — 16바이트 헤더(0x5A, ver, seq, len, type, rsv6) + JSON.
  1300 @19204 robot_status_map_req         → current_map / current_map_md5 / maps[]
  4011 @19207 robot_config_downloadmap_req → 데이터부가 .smap JSON 원문
근거: References/Seer-Driver/robokit_tcp_api.md, kuks2309/T-Robot_seer_gui 019 문서.
"""
import hashlib
import json
import os
import socket
import struct
import sys

# Big-AMR 의 Seer 컨트롤러. 다른 기체를 볼 때는 SEER_IP 로 덮어쓴다.
# 접근은 무선(wlan0) 전용 — docs/network/seer_network_access.md 참조.
IP = os.environ.get("SEER_IP", "192.168.44.82")
PORT_STATE, PORT_CFG = 19204, 19207
REQ_MAP_STATUS, REQ_DOWNLOAD_MAP = 1300, 4011


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(min(65536, n - len(buf)))
        if not chunk:
            raise RuntimeError("연결이 끊겼다 (%d/%d 수신)" % (len(buf), n))
        buf += chunk
    return buf


def request(port, req_type, payload=None, timeout=30):
    body = b"" if payload is None else json.dumps(payload).encode()
    head = struct.pack("!BBHLH6s", 0x5A, 1, 1, len(body), req_type, b"\x00" * 6)
    sock = socket.socket()
    sock.settimeout(timeout)
    sock.connect((IP, port))
    try:
        sock.sendall(head + body)
        resp_head = _recvn(sock, 16)
        _, _, _, length, resp_type = struct.unpack("!BBHLH", resp_head[:10])
        return resp_type, (_recvn(sock, length) if length else b"")
    finally:
        sock.close()


def main():
    outdir = sys.argv[1]
    _, raw = request(PORT_STATE, REQ_MAP_STATUS)
    status = json.loads(raw)
    cur, md5_expected = status.get("current_map"), status.get("current_map_md5")
    print("현재 로드된 맵 : %s" % cur)
    print("로봇 보고 md5  : %s" % md5_expected)
    print("저장된 맵 개수 : %d" % len(status.get("maps", [])))
    if not cur:
        print("[FAIL] current_map 이 비어 있다 — 맵 미로드 상태")
        return 1

    _, data = request(PORT_CFG, REQ_DOWNLOAD_MAP, {"map_name": cur})
    try:
        obj = json.loads(data)
    except ValueError:
        obj = None
    if isinstance(obj, dict) and "header" not in obj:
        print("[FAIL] 다운로드 오류 응답: %s" % obj)
        return 1

    md5_actual = hashlib.md5(data).hexdigest()
    path = os.path.join(outdir, cur + ".smap")
    with open(path, "wb") as f:
        f.write(data)

    ok = md5_actual == md5_expected
    print("받은 바이트    : %d" % len(data))
    print("계산 md5       : %s  %s" % (md5_actual, "일치 ✅" if ok else "❌ 불일치"))
    print("저장           : %s" % path)

    hdr = obj.get("header", {})
    print("---- 맵 내용 ----")
    print("이름/버전      : %s (v%s)" % (hdr.get("mapName"), hdr.get("version")))
    print("해상도         : %s m/cell" % hdr.get("resolution"))
    mn, mx = hdr.get("minPos", {}), hdr.get("maxPos", {})
    print("범위           : x[%.2f, %.2f] y[%.2f, %.2f]"
          % (mn.get("x", 0), mx.get("x", 0), mn.get("y", 0), mx.get("y", 0)))
    for key in ("normalPosList", "advancedPointList", "advancedCurveList", "rssiPosList"):
        if key in obj:
            print("%-18s: %d" % (key, len(obj[key])))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
