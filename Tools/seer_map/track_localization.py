#!/usr/bin/env python3
"""주행 중 mcl2d 추정과 Seer 실측 자세를 동시 기록해 위치추정 정확도를 남긴다.

왜 필요한가: 화면으로 "맞는 것 같다" 는 근거가 되지 않는다. 로봇을 밀면서 두 값을 같은 시각에
받아 적어야 (a) 정적일 때와 동적일 때가 다른지 (b) 특정 구간에서만 틀어지는지 (c) 오차가
누적인지 순간인지를 나중에 판별할 수 있다.

⚠ Seer 자세는 **기준이지 진값이 아니다**. Seer 도 스스로 측위하며 confidence 가 0 으로 떨어지는
   것을 관측했다. 그래서 confidence 를 함께 적고, 낮은 구간은 비교에서 빼고 볼 수 있게 한다.

기록: JSONL 한 줄 = 한 샘플. 사후 분석·그래프용.
사용:
  python3 track_localization.py --seconds 120 --out /tmp/track.jsonl
  python3 track_localization.py --summary /tmp/track.jsonl      # 기록 요약만
"""
import argparse
import json
import math
import os
import socket
import statistics
import struct
import sys
import time

IP = os.environ.get("SEER_IP", "192.168.44.82")
PORT_STATE = 19204
REQ_LOC = 1004


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(min(65536, n - len(buf)))
        if not chunk:
            raise RuntimeError("연결 끊김")
        buf += chunk
    return buf


def seer_pose(timeout=5.0):
    """실패해도 예외를 올리지 않는다 — 무선이 순간 끊겨도 기록은 계속돼야 한다."""
    try:
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect((IP, PORT_STATE))
        try:
            sock.sendall(struct.pack("!BBHLH6s", 0x5A, 1, 1, 0, REQ_LOC, b"\x00" * 6))
            head = _recvn(sock, 16)
            _, _, _, length, _ = struct.unpack("!BBHLH", head[:10])
            d = json.loads(_recvn(sock, length)) if length else {}
            return (float(d.get("x", 0.0)), float(d.get("y", 0.0)),
                    float(d.get("angle", 0.0)), float(d.get("confidence", 0.0)))
        finally:
            sock.close()
    except (OSError, RuntimeError, ValueError):
        return None


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def summarize(path, min_conf=0.5):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    usable = [r for r in rows if r.get("seer") and r["seer"][3] >= min_conf]
    print("샘플 %d개 (Seer confidence >= %.2f 인 %d개로 비교)" % (len(rows), min_conf, len(usable)))
    if not usable:
        print("  비교 가능한 샘플이 없다 — Seer 측위가 낮았거나 응답이 없었다")
        return
    moved = usable[-1]["odom_dist"] - usable[0]["odom_dist"]
    print("  주행 거리(오도 기준) %.2f m" % moved)

    skews = [r["skew"] for r in usable if "skew" in r]
    if skews:
        print("  표본 시각차(mcl↔Seer): 중앙값 %.3f 초 · 최대 %.3f 초" % (statistics.median(sorted(skews)), max(skews)))

    # ⚠ 정지와 이동을 **반드시 나눠서** 본다. 섞으면 이동 구간의 시각차(Seer 폴링 지연)가
    #    측위 오차로 오독된다 — 2026-08-07 실측에서 속도↔위치차 상관 r=0.969, 등가 지연 0.431 초.
    #    회전은 병진 거리가 늘지 않으므로 **병진만 보고 정지로 분류하면 안 된다**(같은 날 오분류).
    still, moving = [], []
    for a, b in zip(usable, usable[1:]):
        dt = b["t"] - a["t"]
        if dt <= 0:
            continue
        v = (b["odom_dist"] - a["odom_dist"]) / dt
        w = abs(wrap(b["mcl"][2] - a["mcl"][2])) / dt
        (still if (v < 0.02 and w < 0.01) else moving).append(b)

    def stat(label, rows_):
        if not rows_:
            print("  %-26s 표본 없음" % label)
            return
        dp = sorted(math.hypot(r["mcl"][0] - r["seer"][0], r["mcl"][1] - r["seer"][1]) for r in rows_)
        da = sorted(abs(math.degrees(wrap(r["mcl"][2] - r["seer"][2]))) for r in rows_)
        for name, arr, unit in (("위치차", dp, "m"), ("각도차", da, "deg")):
            print("  %-13s %-6s n=%3d  중앙값 %.3f %s · 90%%tile %.3f · 최대 %.3f"
                  % (label, name, len(arr), statistics.median(arr), unit,
                     arr[int(len(arr) * 0.9)], arr[-1]))

    stat("[정지]", still)
    stat("[이동]", moving)
    if moving:
        print("  ※ [이동] 값은 표본 시각차가 섞여 있다 — 측위 오차로 읽지 말 것.")


def main():
    ap = argparse.ArgumentParser(description="mcl2d vs Seer 자세 동시 기록")
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--rate", type=float, default=2.0, help="Seer 폴링 Hz (과빈번 금지 — 5~10Hz 상한)")
    ap.add_argument("--out", default="/tmp/track_localization.jsonl")
    ap.add_argument("--summary", help="기존 기록 파일을 요약만 하고 끝낸다")
    ap.add_argument("--min-confidence", type=float, default=0.5)
    args = ap.parse_args()

    if args.summary:
        summarize(args.summary, args.min_confidence)
        return 0

    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav_msgs.msg import Odometry
    from rclpy.qos import QoSProfile, ReliabilityPolicy

    rclpy.init()
    node = rclpy.create_node("track_localization")
    state = {"mcl": None, "odom": None, "odom_dist": 0.0, "prev": None, "seq": 0, "mcl_at": 0.0}

    def on_mcl(m):
        q = m.pose.pose.orientation
        state["mcl"] = (m.pose.pose.position.x, m.pose.pose.position.y,
                        math.atan2(2 * q.w * q.z, 1 - 2 * q.z * q.z))
        state["seq"] += 1                  # 새 메시지 도착 표시 (묵은 값 재기록 차단용)
        state["mcl_at"] = time.time()      # 수신 시각 — Seer 응답 시각과의 차를 기록에 남긴다

    def on_odom(m):
        p = m.pose.pose.position
        if state["prev"] is not None:
            state["odom_dist"] += math.hypot(p.x - state["prev"][0], p.y - state["prev"][1])
        state["prev"] = (p.x, p.y)

    be = QoSProfile(depth=10)
    be.reliability = ReliabilityPolicy.BEST_EFFORT
    node.create_subscription(PoseWithCovarianceStamped, "/mcl_pose", on_mcl, QoSProfile(depth=10))
    node.create_subscription(Odometry, "/odom", on_odom, be)

    print("기록 시작 — %.0f초, Seer 폴링 %.1f Hz → %s" % (args.seconds, args.rate, args.out))
    print("지금부터 로봇을 천천히 밀어 주세요. (Ctrl+C 로 조기 종료 가능)")
    n = 0
    with open(args.out, "w", encoding="utf-8") as f:
        t0 = time.time()
        try:
            while time.time() - t0 < args.seconds:
                # ⚠ 반드시 **새** /mcl_pose 를 기다렸다가 기록한다.
                #   예전 판(2026-08-07 이전)은 spin_once 를 한 번만 돌리고 곧바로 기록해서,
                #   그 0.05 초 창에 메시지가 안 오면 **직전 값을 그대로 다시 적었다.**
                #   2026-08-07 주행 시험에서 573건 중 **286건(50%)이 이런 묵은 샘플**이었고,
                #   제자리 회전(약 27°/s) 중 신선한 Seer 값과 짝지어져 **각도차 25.79°** 라는
                #   가짜 이상치를 만들었다. 묵은 샘플을 빼면 같은 구간 최대가 1.05° 다.
                seen = state["seq"]
                wait_until = time.time() + 1.0
                while state["seq"] == seen and time.time() < wait_until:
                    rclpy.spin_once(node, timeout_sec=0.05)
                if state["mcl"] is None or state["seq"] == seen:
                    continue                       # 새 값을 못 받았으면 이번 주기는 건너뛴다
                mcl_at = state["mcl_at"]
                mcl = state["mcl"]
                sp = seer_pose()
                # skew = mcl 수신 ~ Seer 응답 사이의 벽시계 간격. 이동 중 위치차의 주원인이며
                # (2026-08-07 실측: 속도↔위치차 r=0.969, 등가 지연 0.431 초) 사후 보정에 쓴다.
                rec = {"t": round(time.time() - t0, 3), "mcl": [round(v, 4) for v in mcl],
                       "seer": [round(v, 4) for v in sp] if sp else None,
                       "skew": round(time.time() - mcl_at, 4),
                       "odom_dist": round(state["odom_dist"], 4)}
                f.write(json.dumps(rec) + "\n")
                f.flush()
                n += 1
                if n % 10 == 0:
                    d = (math.hypot(rec["mcl"][0] - sp[0], rec["mcl"][1] - sp[1]) if sp else float("nan"))
                    print("  %5.1fs  주행 %.2f m  위치차 %.3f m  conf %.2f"
                          % (rec["t"], rec["odom_dist"], d, sp[3] if sp else 0.0))
                time.sleep(max(0.0, 1.0 / args.rate))
        except KeyboardInterrupt:
            print("\n중단 요청 — 기록 저장됨")
    rclpy.shutdown()
    print("샘플 %d개 저장: %s\n" % (n, args.out))
    summarize(args.out, args.min_confidence)
    return 0


if __name__ == "__main__":
    sys.exit(main())
