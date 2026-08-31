# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""camctl — 카메라 관리 모드 CLI.

  camctl status               # 장치·유닛·프레임 수신율·depth 점유 한눈에
  camctl restart cam_f        # 한 대 재시작 (all = 전체)
  camctl start cam_f | stop cam_f
  camctl auto on|off          # 관리자 노드의 자동 재시작 토글

제어는 sudo -n systemctl 을 쓴다 — 무암호 허용(/etc/sudoers.d/camera-manager)은
Tools/camera_service/install.sh 가 설치한다. 상태 조회는 무권한이다.
"""
from __future__ import annotations

import argparse
import sys
import time

from camera_manager.roster import Camera, find_shared_config, load_roster
from camera_manager.systemd_ctl import SystemdControl

_MEASURE_SEC_DEFAULT = 2.0


def _load_cameras(args) -> list[Camera]:
    path = args.config or find_shared_config()
    if not path:
        raise SystemExit(
            "공용 카메라 설정을 찾지 못했다 — --config 또는 CAMERA_CONFIG 로 "
            "config/camera/camera_common.yaml 을 지정하라")
    return load_roster(path)


def _select(cameras: list[Camera], target: str) -> list[Camera]:
    if target == "all":
        return cameras
    matched = [cam for cam in cameras if cam.name == target]
    if not matched:
        names = ", ".join(cam.name for cam in cameras)
        raise SystemExit(f"로스터에 없는 카메라: {target} (등록: {names}, all)")
    return matched


def _measure_frames(cameras: list[Camera], window_sec: float):
    """window_sec 동안 압축 토픽을 구독해 카메라별 수신 프레임 수와
    depth 퍼블리셔 존재를 잰다. (rclpy 는 상태 측정 때만 쓴다.)"""
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CompressedImage

    rclpy.init()
    node = rclpy.create_node("camctl_status")
    counts = {cam.name: 0 for cam in cameras}

    def _make_cb(name):
        def _cb(_msg):
            counts[name] += 1
        return _cb

    subs = [
        node.create_subscription(
            CompressedImage, f"{cam.name}/image_raw/compressed",
            _make_cb(cam.name), qos_profile_sensor_data)
        for cam in cameras
    ]
    deadline = time.monotonic() + window_sec
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    depth_active = {
        cam.name: node.count_publishers(f"{cam.name}/depth/image_raw") > 0
        for cam in cameras
    }
    del subs
    node.destroy_node()
    rclpy.shutdown()
    return counts, depth_active


def cmd_status(args) -> int:
    """로스터 전 카메라의 장치·유닛·프레임 상태 표."""
    import os

    cameras = _load_cameras(args)
    systemd = SystemdControl()
    if args.no_measure:
        counts, depth_active = None, {}
    else:
        counts, depth_active = _measure_frames(cameras, args.measure_sec)

    unit_label = {True: "active", False: "inactive", None: "?"}
    print(f"{'카메라':<8} {'장치':<4} {'유닛':<9} {'프레임':<12} depth점유")
    for cam in cameras:
        device = "✓" if os.path.exists(cam.device) else "—"
        unit = unit_label[systemd.is_active(cam.name)]
        if counts is None:
            frames = "(미측정)"
        elif counts[cam.name] > 0:
            frames = f"{counts[cam.name] / args.measure_sec:.1f} Hz"
        else:
            frames = "수신 0"
        depth = "depth" if depth_active.get(cam.name) else "—"
        print(f"{cam.name:<8} {device:<4} {unit:<9} {frames:<12} {depth}")
    return 0


def cmd_control(args) -> int:
    """start|stop|restart — sudo -n systemctl 로 유닛 제어."""
    cameras = _select(_load_cameras(args), args.camera)
    systemd = SystemdControl()
    failed = 0
    for cam in cameras:
        ok, message = systemd.control(args.verb, cam.name)
        print(message)
        failed += 0 if ok else 1
    return 1 if failed else 0


def cmd_auto(args) -> int:
    """관리자 노드의 자동 재시작 토글(std_srvs/SetBool)."""
    import rclpy
    from std_srvs.srv import SetBool

    rclpy.init()
    node = rclpy.create_node("camctl_auto")
    client = node.create_client(SetBool, "/camera_manager/set_auto")
    try:
        if not client.wait_for_service(timeout_sec=2.0):
            print("camera_manager 노드가 떠 있지 않다 — "
                  "sudo systemctl start amr-camera-manager", file=sys.stderr)
            return 1
        request = SetBool.Request()
        request.data = args.mode == "on"
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
        response = future.result()
        if response is None:
            print("서비스 응답 없음(타임아웃)", file=sys.stderr)
            return 1
        print(response.message)
        return 0 if response.success else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="camctl", description="카메라 관리 모드 CLI (usb-cam@ 유닛 + camera_manager)")
    parser.add_argument("--config", default="", help="camera_common.yaml 경로(기본: 자동 탐색)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="장치·유닛·프레임 상태 표")
    p_status.add_argument("--measure-sec", type=float, default=_MEASURE_SEC_DEFAULT,
                          dest="measure_sec", help="프레임 측정 창(초, 기본 2)")
    p_status.add_argument("--no-measure", action="store_true", dest="no_measure",
                          help="토픽 측정 생략(장치·유닛만)")
    p_status.set_defaults(func=cmd_status)

    for verb in ("start", "stop", "restart"):
        p_verb = sub.add_parser(verb, help=f"카메라 유닛 {verb}")
        p_verb.add_argument("camera", help="카메라 이름 또는 all")
        p_verb.set_defaults(func=cmd_control, verb=verb)

    p_auto = sub.add_parser("auto", help="자동 재시작 켜기/끄기")
    p_auto.add_argument("mode", choices=("on", "off"))
    p_auto.set_defaults(func=cmd_auto)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
