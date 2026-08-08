#!/usr/bin/env python3
"""스캔이 참 자세에서 맵과 맞는지 잰다 — 측위 입력 배선을 가리는 도구.

Seer 가 보고하는 자세를 참으로 놓고, 스캔점을 map 프레임에 얹어 맵 장애물과의 최근접
거리 중앙값을 낸다. 맞는 배선만 맵 해상도(0.02 m) 수준이 나온다. 로봇을 움직이지 않는다.

2026-08-08 이 도구가 가린 것:

    /scan_merged + mounts [0,0,0]        0.017 m   ← 정답
    /scan_front  + mounts(front −45°)    1.859 m
    /scan_rear   + mounts(rear 135.29°)  1.445 m
    /scan_front  + 항등 마운트            2.000 m

`dual_laser_merger` 가 두 라이다를 **차체 기준으로 합쳐** `/scan_merged` 를 내므로
(`base_link→scan_merged` TF 가 항등), 그 입력에는 마운트가 항등이어야 한다.
원본 `/scan_front`·`/scan_rear` 에 마운트를 적용하는 것은 이 파이프라인의 경로가 아니다.

⚠ Seer 자세를 참으로 쓴다 — Seer 측위가 틀렸다면 이 판정도 함께 틀린다.
⚠ 스캔 구독은 **BEST_EFFORT** 여야 한다. 기본 RELIABLE 로는 한 건도 받지 못한다.

"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def load_map_points(smap: Path):
    d = json.loads(smap.read_text(encoding="utf-8"))
    # Seer JSON 은 값이 0 인 필드를 생략한다.
    return [(float(p.get("x", 0.0)), float(p.get("y", 0.0))) for p in d.get("normalPosList", [])]


def scan_to_map(scan, mount, pose):
    """스캔 빔을 map 프레임 점으로. mount=(mx,my,myaw) 차체기준, pose=(px,py,pth) map 기준."""
    mx, my, myaw = mount
    px, py, pth = pose
    out = []
    a = scan["angle_min"]
    for r in scan["ranges"]:
        ang = a
        a += scan["angle_increment"]
        if not (scan["range_min"] < r < scan["range_max"]) or not math.isfinite(r):
            continue
        # 라이다 좌표 → 차체 좌표
        lx, ly = r * math.cos(ang), r * math.sin(ang)
        bx = mx + lx * math.cos(myaw) - ly * math.sin(myaw)
        by = my + lx * math.sin(myaw) + ly * math.cos(myaw)
        # 차체 → map
        out.append((px + bx * math.cos(pth) - by * math.sin(pth),
                    py + bx * math.sin(pth) + by * math.cos(pth)))
    return out


def score(points, tree):
    """맵 점군까지의 최근접 거리 중앙값(m). KD-tree 로 **실제** 최근접을 구한다.

    격자 근사는 탐색 반경 밖을 상수로 뭉개 「안 맞음」과 「반경 부족」을 구분하지 못한다.
    """
    if not points:
        return float("inf")
    import numpy as np
    d, _ = tree.query(np.asarray(points), k=1)
    return float(np.median(d))


def main() -> int:
    ap = argparse.ArgumentParser(description="라이다 마운트 후보 정합 점수")
    ap.add_argument("--smap", required=True, type=Path)
    ap.add_argument("--host", default="192.168.44.82")
    a = ap.parse_args()

    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/MES/csm"))
    from csm.seer_client import SeerStatusClient

    with SeerStatusClient(a.host, timeout=5.0) as c:
        r = c.request(1004)
    pose = (r["x"], r["y"], r["angle"])
    print(f"참 자세(Seer)  x={pose[0]:.4f} y={pose[1]:.4f} theta={pose[2]:.4f} rad "
          f"({math.degrees(pose[2]):.2f}°)  conf={r.get('confidence')}\n")

    rclpy.init()
    n = Node("mount_check")
    got = {}

    def mk(key):
        def cb(m):
            if key not in got:
                got[key] = {"angle_min": m.angle_min, "angle_increment": m.angle_increment,
                            "range_min": m.range_min, "range_max": m.range_max,
                            "ranges": list(m.ranges)}
        return cb

    # ⚠ BEST_EFFORT — 기본 RELIABLE 로는 라이다 토픽을 한 건도 받지 못한다.
    from rclpy.qos import qos_profile_sensor_data as SQ
    for topic, key in (("/scan_merged", "merged"), ("/scan_front", "front"), ("/scan_rear", "rear")):
        n.create_subscription(LaserScan, topic, mk(key), SQ)
    for _ in range(400):
        rclpy.spin_once(n, timeout_sec=0.05)
        if len(got) == 3:
            break
    n.destroy_node()
    rclpy.shutdown()
    if not got:
        print("스캔 수신 0", file=sys.stderr)
        return 2

    import numpy as np
    from scipy.spatial import cKDTree
    pts = load_map_points(a.smap)
    tree = cKDTree(np.asarray(pts))
    print(f"맵 장애물 {len(pts)}점 · KD-tree 최근접\n")

    F = (0.881676, -0.578664, -math.pi / 4)      # kFoilA082Mounts front
    R = (-0.857, 0.5971, 135.29 * math.pi / 180.0)  # kFoilA082Mounts rear
    I = (0.0, 0.0, 0.0)                              # 합친 스캔용 항등

    cands = [
        ("merged + 항등 (정본 배선)", "merged", I, None, None),
        ("front + 마운트", "front", F, None, None),
        ("rear + 마운트", "rear", R, None, None),
        ("front + 항등 (대조)", "front", I, None, None),
        ("rear + 항등 (대조)", "rear", I, None, None),
    ]

    print(f"  {'구성':<34} {'중앙값':>10}")
    print("  " + "-" * 46)
    rows = []
    for name, key, mount, _a, _b in cands:
        if key not in got:
            print(f"  {name:<34} {'(미수신)':>10}")
            continue
        v = score(scan_to_map(got[key], mount, pose), tree)
        rows.append((v, name))
        print(f"  {name:<34} {v:9.3f}m")

    if rows:
        rows.sort()
        print(f"\n  최적: **{rows[0][1]}** ({rows[0][0]:.3f} m)")
        print("  ※ 맵 해상도 0.02 m 수준이면 배선이 맞다. 1 m 대는 입력 경로가 틀린 것이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
