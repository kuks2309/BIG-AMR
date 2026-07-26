#!/usr/bin/env python3
"""ROS2 scan subscription bridge for PyQt5 UI.

Emits raw cartesian points in each sensor's local frame.
The UI layer transforms to merged_scan frame for display/ICP.
"""

import math
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from tf_calculator import TFTransform2D, invert_tf, compose_tf


class RosScanBridge(QObject):
    """Bridges ROS2 LaserScan topics with Qt signals.

    Points are emitted in sensor-local frame.
    Use get_initial_tfs() to get transforms from config parameters.
    """

    front_scan_updated = pyqtSignal(object)  # numpy (N,2) in scan_front local
    rear_scan_updated = pyqtSignal(object)   # numpy (M,2) in scan_rear local
    connection_status_changed = pyqtSignal(bool, bool)
    scan_info_updated = pyqtSignal(int, int)

    def __init__(self, node: Node, parent=None):
        super().__init__(parent)
        self._node = node

        # Declare and read ROS2 parameters (matches calibration_ui_params.yaml)
        node.declare_parameter('scan_topic_front', 'scan_front')
        node.declare_parameter('scan_topic_rear', 'scan_rear')
        node.declare_parameter('min_range', 0.1)
        node.declare_parameter('max_range', 12.0)
        node.declare_parameter('enable_average_filter', True)
        node.declare_parameter('transform_tolerance', 0.1)

        # Sensor mounting parameters (from config yaml)
        node.declare_parameter('front_tx', 0.0)
        node.declare_parameter('front_ty', 0.0)
        node.declare_parameter('front_yaw', 0.0)
        node.declare_parameter('front_upside_down', False)
        node.declare_parameter('rear_tx', 0.0)
        node.declare_parameter('rear_ty', 0.0)
        node.declare_parameter('rear_yaw', 0.0)
        node.declare_parameter('rear_upside_down', False)

        self._scan_topic_front = node.get_parameter('scan_topic_front').get_parameter_value().string_value
        self._scan_topic_rear = node.get_parameter('scan_topic_rear').get_parameter_value().string_value
        self._min_range = node.get_parameter('min_range').get_parameter_value().double_value
        self._max_range = node.get_parameter('max_range').get_parameter_value().double_value
        self._enable_average_filter = node.get_parameter('enable_average_filter').get_parameter_value().bool_value
        self._transform_tolerance = node.get_parameter('transform_tolerance').get_parameter_value().double_value

        self._front_connected = False
        self._rear_connected = False
        self._last_front_count = 0
        self._last_rear_count = 0

        self._front_sub = self._node.create_subscription(
            LaserScan, self._scan_topic_front,
            self._on_front_scan, qos_profile_sensor_data)
        self._rear_sub = self._node.create_subscription(
            LaserScan, self._scan_topic_rear,
            self._on_rear_scan, qos_profile_sensor_data)

    def _on_front_scan(self, msg: LaserScan):
        if not self._front_connected:
            self._front_connected = True
            self.connection_status_changed.emit(
                self._front_connected, self._rear_connected)

        ranges = msg.ranges
        if self._enable_average_filter:
            ranges = self._apply_average_filter(msg)

        points_local = self._laser_scan_to_cartesian(msg, ranges)
        self._last_front_count = len(points_local)
        self.front_scan_updated.emit(points_local)
        self.scan_info_updated.emit(self._last_front_count, self._last_rear_count)

    def _on_rear_scan(self, msg: LaserScan):
        if not self._rear_connected:
            self._rear_connected = True
            self.connection_status_changed.emit(
                self._front_connected, self._rear_connected)

        ranges = msg.ranges
        if self._enable_average_filter:
            ranges = self._apply_average_filter(msg)

        points_local = self._laser_scan_to_cartesian(msg, ranges)
        self._last_rear_count = len(points_local)
        self.rear_scan_updated.emit(points_local)
        self.scan_info_updated.emit(self._last_front_count, self._last_rear_count)

    def _laser_scan_to_cartesian(self, scan_msg: LaserScan, ranges) -> np.ndarray:
        ranges_array = np.array(ranges, dtype=np.float32)
        angles = scan_msg.angle_min + np.arange(len(ranges_array)) * scan_msg.angle_increment

        valid = (np.isfinite(ranges_array) &
                (ranges_array >= self._min_range) &
                (ranges_array <= self._max_range))

        r_valid = ranges_array[valid]
        a_valid = angles[valid]

        if len(r_valid) == 0:
            return np.empty((0, 2), dtype=np.float32)

        return np.column_stack([
            r_valid * np.cos(a_valid),
            r_valid * np.sin(a_valid)
        ])

    def _apply_average_filter(self, scan_msg: LaserScan):
        ranges = scan_msg.ranges
        n = len(ranges)
        smoothed = [0.0] * n

        for i in range(n):
            sum_val = 0.0
            count = 0
            for k in [-1, 0, 1]:
                idx = i + k
                if idx < 0 or idx >= n:
                    continue
                r = ranges[idx]
                if math.isfinite(r) and scan_msg.range_min <= r <= scan_msg.range_max:
                    sum_val += r
                    count += 1
            smoothed[i] = (sum_val / count) if count > 0 else ranges[i]

        return smoothed

    def get_initial_tfs(self) -> dict:
        """
        Config 파라미터에서 초기 TF를 읽고 jog 변환을 계산.

        Returns:
            dict with keys:
              'merged_to_front': TFTransform2D (flipped 포함)
              'merged_to_rear':  TFTransform2D (flipped 포함)
              'tf_base_front':   TFTransform2D
              'tf_base_rear':    TFTransform2D
              'tf_front_rear':   TFTransform2D
            Returns None on failure.
        """
        try:
            node = self._node
            front_tx = node.get_parameter('front_tx').get_parameter_value().double_value
            front_ty = node.get_parameter('front_ty').get_parameter_value().double_value
            front_yaw = node.get_parameter('front_yaw').get_parameter_value().double_value
            front_upside_down = node.get_parameter('front_upside_down').get_parameter_value().bool_value

            rear_tx = node.get_parameter('rear_tx').get_parameter_value().double_value
            rear_ty = node.get_parameter('rear_ty').get_parameter_value().double_value
            rear_yaw = node.get_parameter('rear_yaw').get_parameter_value().double_value
            rear_upside_down = node.get_parameter('rear_upside_down').get_parameter_value().bool_value

            tf_base_front = TFTransform2D(
                tx=front_tx, ty=front_ty, yaw=front_yaw, flipped=front_upside_down)
            tf_base_rear = TFTransform2D(
                tx=rear_tx, ty=rear_ty, yaw=rear_yaw, flipped=rear_upside_down)

            tf_front_rear = compose_tf(invert_tf(tf_base_front), tf_base_rear)

            merged_to_front = tf_base_front
            merged_to_rear = tf_base_rear

            node.get_logger().info(
                f"Initial TFs from config:\n"
                f"  base->front: tx={front_tx:.4f} ty={front_ty:.4f} "
                f"yaw={front_yaw:.4f}rad ({math.degrees(front_yaw):.2f}deg) "
                f"flipped={front_upside_down}\n"
                f"  base->rear:  tx={rear_tx:.4f} ty={rear_ty:.4f} "
                f"yaw={rear_yaw:.4f}rad ({math.degrees(rear_yaw):.2f}deg) "
                f"flipped={rear_upside_down}"
            )

            return {
                'merged_to_front': merged_to_front,
                'merged_to_rear': merged_to_rear,
                'tf_base_front': tf_base_front,
                'tf_base_rear': tf_base_rear,
                'tf_front_rear': tf_front_rear,
            }

        except Exception as ex:
            self._node.get_logger().error(f"Config parameter read failed: {ex}")
            return None

    @staticmethod
    def transform_points_2d(points: np.ndarray, tf: TFTransform2D) -> np.ndarray:
        """Transform 2D points by TFTransform2D.

        If tf.flipped (upside-down, roll=π): negate Y before rotation.
          p' = R(yaw) * Rx(π) * p + [tx, ty]
          Rx(π) in 2D: (x, y) -> (x, -y)
        """
        if points is None or len(points) == 0:
            return points
        px = points[:, 0]
        py = points[:, 1]
        if tf.flipped:
            py = -py
        cos_y = math.cos(tf.yaw)
        sin_y = math.sin(tf.yaw)
        return np.column_stack([
            px * cos_y - py * sin_y + tf.tx,
            px * sin_y + py * cos_y + tf.ty
        ])

    @property
    def scan_topic_front(self) -> str:
        return self._scan_topic_front

    @scan_topic_front.setter
    def scan_topic_front(self, value: str):
        self._scan_topic_front = value

    @property
    def scan_topic_rear(self) -> str:
        return self._scan_topic_rear

    @scan_topic_rear.setter
    def scan_topic_rear(self, value: str):
        self._scan_topic_rear = value

    @property
    def min_range(self) -> float:
        return self._min_range

    @min_range.setter
    def min_range(self, value: float):
        self._min_range = value

    @property
    def max_range(self) -> float:
        return self._max_range

    @max_range.setter
    def max_range(self, value: float):
        self._max_range = value

    @property
    def enable_average_filter(self) -> bool:
        return self._enable_average_filter

    @enable_average_filter.setter
    def enable_average_filter(self, value: bool):
        self._enable_average_filter = value

    @property
    def transform_tolerance(self) -> float:
        return self._transform_tolerance

    @transform_tolerance.setter
    def transform_tolerance(self, value: float):
        self._transform_tolerance = value

    @property
    def is_front_connected(self) -> bool:
        return self._front_connected

    @property
    def is_rear_connected(self) -> bool:
        return self._rear_connected

    def destroy(self):
        self._node.destroy_subscription(self._front_sub)
        self._node.destroy_subscription(self._rear_sub)
