#!/usr/bin/env python3
"""Seer 컨트롤러가 보고하는 현재 자세를 읽어 ROS `/initialpose` 로 발행한다.

왜 필요한가: mcl2d 는 초기 자세를 모르면 (0,0,0) 부근에서 시작해 스캔이 맵에 얹히지 않는다.
로봇의 실제 위치는 Seer 가 이미 알고 있으므로(자체 측위), 그 값을 초기값으로 넘기면 된다.
RViz 의 "2D Pose Estimate" 를 손으로 찍는 것과 같은 토픽·같은 메시지를 쓴다.

⚠ **신뢰도 게이트** — Seer 가 측위를 잃으면 자세가 (0,0,0)·confidence 0 으로 나온다. 그 값을
   그대로 초기값으로 넣으면 로봇을 맵 원점에 있다고 선언하는 셈이라 더 나쁘다. 그래서 기본적으로
   confidence 가 임계 미만이면 **발행하지 않고 실패로 끝낸다**(--min-confidence, 기본 0.5).
   실제로 이 값이 0.337 → 0.000 으로 떨어졌다가 0.833 으로 회복하는 것을 관측했다.

사용:
  python3 seer_initialpose.py                    # 1회 발행
  python3 seer_initialpose.py --min-confidence 0.7
  SEER_IP=192.168.44.82 python3 seer_initialpose.py --dry-run
"""
import argparse
import json
import math
import os
import socket
import struct
import sys
import time

IP = os.environ.get("SEER_IP", "192.168.44.82")
PORT_STATE = 19204
REQ_LOC = 1004  # robot_status_loc_req → x, y, angle, confidence


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(min(65536, n - len(buf)))
        if not chunk:
            raise RuntimeError("연결이 끊겼다 (%d/%d 수신)" % (len(buf), n))
        buf += chunk
    return buf


def seer_request(req_type, timeout=12.0, tries=3):
    """Seer NetProtocol 요청. 무선 구간이라 순간 실패가 있어 재시도한다."""
    last = None
    for _ in range(tries):
        try:
            sock = socket.socket()
            sock.settimeout(timeout)
            sock.connect((IP, PORT_STATE))
            try:
                sock.sendall(struct.pack("!BBHLH6s", 0x5A, 1, 1, 0, req_type, b"\x00" * 6))
                head = _recvn(sock, 16)
                _, _, _, length, _ = struct.unpack("!BBHLH", head[:10])
                return json.loads(_recvn(sock, length)) if length else {}
            finally:
                sock.close()
        except OSError as exc:      # No route to host 등 — 무선에서 실제로 겪는다
            last = exc
            time.sleep(2)
    raise last


def main():
    ap = argparse.ArgumentParser(description="Seer 자세 → /initialpose")
    ap.add_argument("--min-confidence", type=float, default=0.5,
                    help="이 값 미만이면 발행하지 않는다 (기본 0.5)")
    ap.add_argument("--topic", default="/initialpose")
    ap.add_argument("--frame", default="map")
    ap.add_argument("--repeat", type=int, default=5, help="발행 횟수 (구독자 연결 여유)")
    ap.add_argument("--wait-subscriber", type=float, default=10.0,
                    help="구독자를 이 시간(초)까지 기다린 뒤 발행한다 (DDS 발견 지연 대비)")
    ap.add_argument("--dry-run", action="store_true", help="조회만 하고 발행하지 않는다")
    args = ap.parse_args()

    loc = seer_request(REQ_LOC)
    x, y = float(loc.get("x", 0.0)), float(loc.get("y", 0.0))
    yaw, conf = float(loc.get("angle", 0.0)), float(loc.get("confidence", 0.0))
    print("Seer 자세: x=%.4f y=%.4f yaw=%.4f rad (%.2f deg) confidence=%.4f"
          % (x, y, yaw, math.degrees(yaw), conf))

    if conf < args.min_confidence:
        print("[중단] confidence %.4f < 임계 %.2f — Seer 가 측위를 잃은 상태로 보인다.\n"
              "       이 값을 초기 자세로 넣으면 로봇 위치를 잘못 선언하게 된다.\n"
              "       Seer 가 재측위해 confidence 가 회복된 뒤 다시 실행하라."
              % (conf, args.min_confidence))
        return 2
    if args.dry_run:
        print("[dry-run] 발행하지 않음")
        return 0

    import rclpy                                   # ROS 없이도 조회는 되도록 늦게 import
    from geometry_msgs.msg import PoseWithCovarianceStamped

    rclpy.init()
    node = rclpy.create_node("seer_initialpose")
    pub = node.create_publisher(PoseWithCovarianceStamped, args.topic, 10)
    msg = PoseWithCovarianceStamped()
    msg.header.frame_id = args.frame
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
    msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
    # 공분산은 Seer 가 주지 않으므로 RViz 기본값과 같은 보수적 값을 쓴다(x·y 0.25 m², yaw 0.0685 rad²).
    msg.pose.covariance[0] = 0.25
    msg.pose.covariance[7] = 0.25
    msg.pose.covariance[35] = 0.0685

    # ⚠ 구독자를 기다린 뒤 발행한다. DDS 는 발견(discovery)에 시간이 걸리는데, 짧게 살았다 죽는
    #   발행자는 그 전에 보낸 메시지를 아무도 못 받는다 — 실제로 그래서 초기자세가 조용히 무시되고
    #   필터가 원점 부근에 머물렀다(2026-08-07). 토픽 통계상 "발행 성공" 이라 더 헷갈린다.
    deadline = time.time() + args.wait_subscriber
    while pub.get_subscription_count() == 0 and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.1)
    subs = pub.get_subscription_count()
    if subs == 0:
        print("[중단] %s 구독자가 %.0f초 안에 나타나지 않았다 — 측위 노드가 떠 있는지 확인하라"
              % (args.topic, args.wait_subscriber))
        rclpy.shutdown()
        return 3

    for _ in range(max(1, args.repeat)):
        msg.header.stamp = node.get_clock().now().to_msg()
        pub.publish(msg)
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.3)
    print("%s 발행 완료 (frame=%s, %d회, 구독자 %d)" % (args.topic, args.frame, args.repeat, subs))
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
