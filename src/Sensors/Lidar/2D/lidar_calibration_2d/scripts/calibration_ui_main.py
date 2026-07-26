#!/usr/bin/env python3

import sys
import os
# Required for ament_cmake package: all scripts are installed to lib/<pkg>/ via
# install(PROGRAMS ...) so sibling imports need explicit path registration.
# This is necessary because ament_cmake does not create a Python package with __init__.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess
import threading
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from PyQt5.QtWidgets import QApplication
from ros_scan_bridge import RosScanBridge
from calibration_ui_window import CalibrationUIWindow


class CalibrationUINode(Node):
    def __init__(self):
        super().__init__('lidar_calibration_2d_ui')


def main():
    rclpy.init()
    node = CalibrationUINode()

    app = QApplication(sys.argv)
    app.setApplicationName("2D LiDAR Calibration UI")

    # Create ROS bridge
    ros_bridge = RosScanBridge(node)

    # Create UI window
    window = CalibrationUIWindow(ros_bridge)
    window.show()

    # Spin ROS2 in background daemon thread
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # Run Qt event loop (blocks until window closed)
    exit_code = app.exec_()

    # Cleanup
    ros_bridge.destroy()

    # Terminate lidar_tf_publisher if running
    try:
        result = subprocess.run(
            ['ros2', 'node', 'list'],
            capture_output=True, text=True, timeout=3)
        if '/lidar_tf_publisher' in result.stdout:
            node.get_logger().info("lidar_tf_publisher 종료 요청 중...")
            subprocess.run(
                ['pkill', '-INT', '-f', 'lidar_tf_publisher'],
                timeout=3)
            node.get_logger().info("lidar_tf_publisher 종료 완료")
        else:
            node.get_logger().info("lidar_tf_publisher 미실행 — 스킵")
    except Exception as e:
        node.get_logger().warn(f"lidar_tf_publisher 종료 실패: {e}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
