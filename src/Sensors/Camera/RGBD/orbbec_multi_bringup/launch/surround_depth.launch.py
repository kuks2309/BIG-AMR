# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# Big-AMR surround depth bringup — Orbbec Gemini E 6대를 depth 전용으로 기동한다.
#
# 설계 근거: docs/adr/2026-07-31-surround-depth-occupancy.md
#
# 이 launch 가 하는 일:
#   1. RGB 스택과의 배타 운용을 강제한다 (ADR §D2) — /dev/video 점유자가 있으면 중단.
#   2. 로스터(config/camera/camera_common.yaml)의 시리얼 6개가 실제로 연결됐는지 확인한다.
#      하나라도 없으면 중단한다 — 조용한 축소 기동 금지.
#   3. 카메라마다 orbbec_camera 드라이버를 depth 전용으로 띄운다.
#   4. base_link → <camera>_link 정적 마운트 TF 6개를 발행한다.
#      그 아래 <camera>_link → <camera>_depth_optical_frame 체인은 드라이버가 발행한다.
#
# 배타 운용 해제 방법(매핑 전):
#   ros2 daemon stop 은 불필요. RGB 퍼블리셔를 내린다:
#     pkill -f usb_cam_publisher_node
#   Tools/camera_service 의 systemd 유닛이 설치돼 있으면 Restart=always 로 5초 뒤 부활하므로
#   먼저 `sudo systemctl stop usb-cam.target` 을 해야 한다.

import math
import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

# Orbbec USB 식별자. depth 인터페이스와 RGB 인터페이스가 서로 다른 PID 로 열거되며,
# 시리얼은 두 인터페이스가 동일하다.
ORBBEC_VENDOR_ID = "2bc5"
ORBBEC_DEPTH_PRODUCT_ID = "065c"

# 저장소 루트의 공용 설정 디렉터리. 비-ROS 도구(Tools/CameraCalibration, Tools/camera_service)도
# 같은 파일을 읽으므로 패키지 share 로 복사하지 않는다 (package.xml 주석 참조).
ROSTER_BASENAME = "camera_common.yaml"
EXTRINSICS_BASENAME = "extrinsics.yaml"

# RGB 스택을 내리는 방법을 오류 메시지로 안내할 때 쓴다.
# (위반 *판정*은 프로세스 이름이 아니라 /dev/video 점유로 한다 — _video_device_holders 참조.
#  vision_guard·yolo_detector 는 토픽 구독자라 장치를 잡지 않으므로 판정 대상이 아니다.)
RGB_PUBLISHER_PROCESS = "usb_cam_publisher_node"


def _find_repo_config(basename):
    """저장소 루트의 config/camera/<basename> 을 찾아 절대경로로 돌려준다.

    탐색 순서는 usb_cam_cctv.launch.py 의 _find_shared_config() 와 같다:
    환경변수 CAMERA_CONFIG_DIR → 이 파일 위치에서 상위로 거슬러 올라가며 탐색.

    Args:
        basename: 찾을 파일 이름 (예: "camera_common.yaml").

    Returns:
        찾은 파일의 절대경로 문자열.

    Raises:
        FileNotFoundError: 못 찾은 경우. **패키지 로컬 사본으로 대체하지 않는다** —
            usb_cam_cctv.launch.py 는 fallback 으로 4대짜리 구 설정을 쓰는 바람에
            6대 중 4대만 경고 없이 기동하는 결함이 있었다
            (docs/usb_cctv/performance/2026-07-28_six_camera_connectivity.md:30-31).
    """
    env_dir = os.environ.get("CAMERA_CONFIG_DIR")
    if env_dir:
        candidate = os.path.join(env_dir, basename)
        if os.path.exists(candidate):
            return candidate

    directory = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        candidate = os.path.join(directory, "config", "camera", basename)
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent

    raise FileNotFoundError(
        f"공용 설정 {basename} 을 찾지 못했다. 저장소 루트의 config/camera/{basename} 이 있어야 "
        f"한다. 다른 위치라면 CAMERA_CONFIG_DIR 환경변수로 디렉터리를 지정하라."
    )


def _load_yaml(path):
    """YAML 파일을 dict 로 읽는다."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _connected_depth_serials():
    """지금 연결된 Orbbec depth 인터페이스의 시리얼 집합을 sysfs 에서 읽는다.

    lsusb 나 SDK 를 거치지 않고 /sys 를 직접 읽는 이유: 드라이버가 장치를 열기 전에
    판정해야 하고, 여기서 장치를 열면 그 자체가 점유가 되기 때문이다.

    Returns:
        시리얼 문자열 set. sysfs 를 못 읽으면 빈 set (판정 불가 → 호출부가 경고 처리).
    """
    serials = set()
    usb_root = "/sys/bus/usb/devices"
    if not os.path.isdir(usb_root):
        return serials

    for entry in os.listdir(usb_root):
        device_dir = os.path.join(usb_root, entry)
        try:
            with open(os.path.join(device_dir, "idVendor"), encoding="utf-8") as handle:
                vendor = handle.read().strip()
            with open(os.path.join(device_dir, "idProduct"), encoding="utf-8") as handle:
                product = handle.read().strip()
        except OSError:
            continue  # 허브·루트허브 등 해당 속성이 없는 노드
        if vendor != ORBBEC_VENDOR_ID or product != ORBBEC_DEPTH_PRODUCT_ID:
            continue
        try:
            with open(os.path.join(device_dir, "serial"), encoding="utf-8") as handle:
                serials.add(handle.read().strip())
        except OSError:
            continue
    return serials


def _video_device_holders():
    """지금 /dev/video* 를 열고 있는 프로세스를 찾는다.

    프로세스 *이름* 대신 실제 파일 점유를 보는 이유: 이름 매칭(pgrep -f)은 명령줄에 그 문자열이
    들어간 무관한 셸까지 잡아 오탐을 낸다(실측 확인). 또 이름 매칭은 usb_cam_publisher 외의
    점유자 — 예: Tools/CameraCalibration/calib_ui.py 가 직접 여는 cv2.VideoCapture — 를 놓친다.

    Returns:
        (pid, comm, device) 튜플 리스트. 읽을 수 없는 프로세스는 조용히 건너뛴다
        (다른 사용자 소유 프로세스는 /proc/<pid>/fd 접근이 막힌다).
    """
    holders = []
    self_pid = str(os.getpid())
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or entry == self_pid:
            continue
        fd_dir = os.path.join("/proc", entry, "fd")
        try:
            descriptors = os.listdir(fd_dir)
        except OSError:
            continue  # 권한 없음 또는 이미 종료
        for descriptor in descriptors:
            try:
                target = os.readlink(os.path.join(fd_dir, descriptor))
            except OSError:
                continue
            if not target.startswith("/dev/video"):
                continue
            try:
                with open(os.path.join("/proc", entry, "comm"), encoding="utf-8") as handle:
                    comm = handle.read().strip()
            except OSError:
                comm = "?"
            holders.append((entry, comm, target))
            break  # 프로세스당 한 번만 보고
    return holders


def _assert_exclusive_mode(allow_rgb_conflict):
    """배타 운용을 강제한다 (ADR §D2).

    Raises:
        RuntimeError: /dev/video* 점유자가 있고 allow_rgb_conflict 가 False 인 경우.
    """
    holders = _video_device_holders()
    if not holders:
        return

    detail = ", ".join(f"{comm}(pid {pid}) → {dev}" for pid, comm, dev in holders)
    if allow_rgb_conflict:
        print(
            f"[surround_depth] 경고: /dev/video 점유 중 — {detail}"
            f" — allow_rgb_conflict:=true 라 강행한다."
        )
        return
    raise RuntimeError(
        f"배타 운용 위반: /dev/video 를 {len(holders)} 개 프로세스가 점유 중\n"
        f"  {detail}\n"
        f"  같은 물리 카메라의 RGB 인터페이스가 열려 있으면 depth 개방이 실패하거나"
        f" 프레임률이 급락한다(LIBUSB_ERROR_BUSY 실측:"
        f" docs/usb_cctv/performance/depth/2026-07-22_depth_640x480.md:43).\n"
        f"  먼저 RGB 스택을 내려라:  pkill -f {RGB_PUBLISHER_PROCESS}\n"
        f"  (Tools/camera_service systemd 유닛이 설치돼 있으면"
        f" sudo systemctl stop usb-cam.target 을 먼저 실행)\n"
        f"  진단 목적으로 강행하려면 allow_rgb_conflict:=true"
    )


def _assert_roster_connected(cameras, require_all_connected):
    """로스터의 시리얼이 전부 실제로 연결됐는지 확인한다.

    Raises:
        RuntimeError: 연결되지 않은 시리얼이 있고 require_all_connected 가 True 인 경우.
    """
    connected = _connected_depth_serials()
    if not connected:
        print(
            "[surround_depth] 경고: sysfs 에서 Orbbec depth 장치를 하나도 읽지 못했다 — "
            "연결 검사를 건너뛴다."
        )
        return

    missing = [cam for cam in cameras if cam["serial"] not in connected]
    if not missing:
        return

    lines = "\n".join(f"    {cam['name']}: {cam['serial']}" for cam in missing)
    message = (
        f"로스터의 카메라 {len(missing)}/{len(cameras)} 대가 연결돼 있지 않다:\n{lines}\n"
        f"  연결된 depth 시리얼: {sorted(connected)}\n"
        f"  방위각 60° 간격 6대 구성이라 한 대가 빠지면 그 방향 60° 섹터가 통째로 비고,"
        f" 겹침이 없어 다른 카메라가 메우지 못한다."
    )
    if require_all_connected:
        raise RuntimeError(
            message + "\n  일부만으로 기동하려면 require_all_connected:=false"
        )
    print(f"[surround_depth] 경고: {message}")


def _depth_params(defaults, driver, override):
    """카메라 1대의 드라이버 파라미터를 만든다.

    Args:
        defaults: surround_depth.yaml 의 depth 절 (전 카메라 공통 기본값).
        driver: surround_depth.yaml 의 driver 절.
        override: 해당 카메라의 per_camera 재정의 dict (없으면 빈 dict).

    Returns:
        드라이버에 넘길 파라미터 dict.
    """
    return {
        "enable_depth": True,
        "depth_width": int(override.get("width", defaults["width"])),
        "depth_height": int(override.get("height", defaults["height"])),
        "depth_fps": int(override.get("fps", defaults["fps"])),
        "depth_format": str(override.get("format", defaults["format"])),
        "depth_qos": str(override.get("qos", defaults["qos"])),
        "depth_camera_info_qos": str(override.get("qos", defaults["qos"])),
        "enable_color": bool(driver["enable_color"]),
        "enable_ir": bool(driver["enable_ir"]),
        "enable_point_cloud": bool(driver["enable_point_cloud"]),
        "enable_colored_point_cloud": False,
        "depth_registration": False,
        "enable_ldp": bool(driver["enable_ldp"]),
        "enable_soft_filter": bool(driver["enable_soft_filter"]),
        "connection_delay": int(driver["connection_delay"]),
        "log_level": str(driver["log_level"]),
        # 드라이버가 <camera>_link → <camera>_depth_optical_frame 을 발행한다.
        # base_link → <camera>_link 는 아래 _static_mount_tf 가 담당한다.
        "publish_tf": True,
        "tf_publish_rate": 0.0,
    }


def _camera_composable_node(camera_name, serial, params):
    """카메라 1대의 ComposableNode 서술을 만든다."""
    return ComposableNode(
        package="orbbec_camera",
        plugin="orbbec_camera::OBCameraNodeDriver",
        name=camera_name,
        namespace=camera_name,
        parameters=[
            dict(
                params,
                camera_name=camera_name,
                # 시리얼 선택은 usb_port·device_num 보다 우선한다
                # (ob_camera_node_driver.cpp:293-301). usb_port 는 재배선으로 바뀌므로 쓰지 않는다.
                serial_number=serial,
                vendor_id=f"0x{ORBBEC_VENDOR_ID}",
            )
        ],
    )


def _static_mount_tf(camera, parent_frame):
    """base_link → <camera>_link 정적 마운트 TF 노드를 만든다.

    Args:
        camera: extrinsics.yaml 의 카메라 항목 (x/y/z 는 m, *_deg 는 도).
        parent_frame: 부모 프레임 이름.
    """
    name = camera["name"]
    return Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name=f"static_tf_base_to_{name}",
        arguments=[
            "--x", str(camera["x"]),
            "--y", str(camera["y"]),
            "--z", str(camera["z"]),
            "--roll", str(math.radians(camera["roll_deg"])),
            "--pitch", str(math.radians(camera["pitch_deg"])),
            "--yaw", str(math.radians(camera["yaw_deg"])),
            "--frame-id", parent_frame,
            "--child-frame-id", f"{name}_link",
        ],
        output="screen",
    )


def _launch_setup(context, *args, **kwargs):
    """인자를 확정한 뒤 노드 목록을 만든다 (OpaqueFunction 진입점)."""
    del args, kwargs  # launch 규약상 받지만 쓰지 않는다

    def flag(argument_name):
        return LaunchConfiguration(argument_name).perform(context).lower() == "true"

    _assert_exclusive_mode(flag("allow_rgb_conflict"))

    roster_path = LaunchConfiguration("roster_file").perform(context)
    extrinsics_path = LaunchConfiguration("extrinsics_file").perform(context)
    stream_path = LaunchConfiguration("stream_config_file").perform(context)

    roster = _load_yaml(roster_path)
    extrinsics = _load_yaml(extrinsics_path)
    stream = _load_yaml(stream_path)

    cameras = roster["cameras"]
    mounts = {cam["name"]: cam for cam in extrinsics["cameras"]}

    # 로스터와 외부파라미터의 카메라 집합이 어긋나면 조용히 일부만 뜨는 대신 즉시 멈춘다.
    roster_names = {cam["name"] for cam in cameras}
    if roster_names != set(mounts):
        raise RuntimeError(
            f"로스터와 외부파라미터의 카메라 이름이 다르다.\n"
            f"  로스터({roster_path}): {sorted(roster_names)}\n"
            f"  외부파라미터({extrinsics_path}): {sorted(mounts)}"
        )

    _assert_roster_connected(cameras, flag("require_all_connected"))

    depth_defaults = stream["depth"]
    driver_defaults = stream["driver"]
    per_camera = stream.get("per_camera") or {}

    composables = []
    for cam in cameras:
        params = _depth_params(
            depth_defaults, driver_defaults, per_camera.get(cam["name"]) or {}
        )
        composables.append(_camera_composable_node(cam["name"], cam["serial"], params))

    if flag("use_single_container"):
        # 미검증 경로: 드라이버가 한 프로세스 안에서 다중 인스턴스를 견디는지 확인된 바 없다
        # (ADR §D4). 대역·CPU 비교 측정용으로만 연다.
        containers = [
            ComposableNodeContainer(
                name="surround_depth_container",
                namespace="",
                package="rclcpp_components",
                executable="component_container",
                composable_node_descriptions=composables,
                output="screen",
            )
        ]
    else:
        # 기본값: 카메라 1대 = 컨테이너 1개. 벤더 gemini_e.launch.py 가 검증한 형태.
        containers = [
            ComposableNodeContainer(
                name=f"{cam['name']}_container",
                namespace="",
                package="rclcpp_components",
                executable="component_container",
                composable_node_descriptions=[composable],
                output="screen",
            )
            for cam, composable in zip(cameras, composables)
        ]

    parent_frame = extrinsics["frame_id"]
    tf_nodes = [_static_mount_tf(mounts[cam["name"]], parent_frame) for cam in cameras]

    return containers + tf_nodes


def generate_launch_description():
    """launch 진입점 — 인자를 선언하고 실제 구성은 _launch_setup 에 맡긴다."""
    arguments = [
        DeclareLaunchArgument(
            "roster_file",
            default_value=_find_repo_config(ROSTER_BASENAME),
            description="카메라 시리얼 로스터 (config/camera/camera_common.yaml).",
        ),
        DeclareLaunchArgument(
            "extrinsics_file",
            default_value=_find_repo_config(EXTRINSICS_BASENAME),
            description="base_link 기준 마운트 값 (config/camera/extrinsics.yaml).",
        ),
        DeclareLaunchArgument(
            "stream_config_file",
            # 소스 트리(.../launch/)와 설치 트리(share/<pkg>/launch/) 둘 다에서
            # 형제 디렉터리 config/ 를 가리킨다.
            default_value=os.path.normpath(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..",
                    "config",
                    "surround_depth.yaml",
                )
            ),
            description="depth 스트림 구동점 (패키지 config/surround_depth.yaml).",
        ),
        DeclareLaunchArgument(
            "allow_rgb_conflict",
            default_value="false",
            description="true 면 RGB 퍼블리셔가 떠 있어도 강행한다(진단용). ADR §D2 위반.",
        ),
        DeclareLaunchArgument(
            "require_all_connected",
            default_value="true",
            description="true 면 로스터 6대가 전부 연결돼야 기동한다. false 면 경고만.",
        ),
        DeclareLaunchArgument(
            "use_single_container",
            default_value="false",
            description="true 면 6대를 한 컨테이너에 넣는다(미검증, ADR §D4).",
        ),
    ]
    return LaunchDescription(arguments + [OpaqueFunction(function=_launch_setup)])
