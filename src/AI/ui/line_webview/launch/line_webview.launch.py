"""line_webview 실행 런치.

  ros2 launch line_webview line_webview.launch.py
  ros2 launch line_webview line_webview.launch.py port:=8082 direction:=reverse

카메라 발행자(usb_cam_publisher)와 인식 노드(line_seg_node)가 먼저 떠 있어야 한다 —
이 뷰어는 장치를 열지 않고 추론도 하지 않는다. 표시만 한다.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument("port", default_value="8081",
                              description="HTTP 포트 (cctv_webview 8080 과 겹치지 않게 8081)"),
        DeclareLaunchArgument("bind", default_value="0.0.0.0",
                              description="바인드 주소"),
        DeclareLaunchArgument("direction", default_value="forward",
                              description="시작 방향 — forward=cam_f, reverse=cam_r"),
        DeclareLaunchArgument("forward_camera", default_value="cam_f",
                              description="전진 카메라 논리명"),
        DeclareLaunchArgument("reverse_camera", default_value="cam_r",
                              description="후진 카메라 논리명"),
        DeclareLaunchArgument("seg_node", default_value="/line_seg_node",
                              description="방향 전환을 요청할 인식 노드 이름"),
        DeclareLaunchArgument("control_row_ratio", default_value="0.8",
                              description="오차 기준행(화면 높이 비율) — 인식 노드와 같게"),
        DeclareLaunchArgument("stream_hz", default_value="15.0",
                              description="브라우저로 흘릴 프레임률 상한"),
    ]
    node = Node(
        package="line_webview",
        executable="line_webview",
        name="line_webview",
        output="screen",
        parameters=[{
            "port": LaunchConfiguration("port"),
            "bind": LaunchConfiguration("bind"),
            "direction": LaunchConfiguration("direction"),
            "forward_camera": LaunchConfiguration("forward_camera"),
            "reverse_camera": LaunchConfiguration("reverse_camera"),
            "seg_node": LaunchConfiguration("seg_node"),
            "control_row_ratio": LaunchConfiguration("control_row_ratio"),
            "stream_hz": LaunchConfiguration("stream_hz"),
        }],
    )
    return LaunchDescription(args + [node])
