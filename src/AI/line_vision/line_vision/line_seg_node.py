#!/usr/bin/env python3
"""라인 세그멘테이션 추론 노드.

카메라 영상 → YOLOv8-seg → 최고 신뢰도 마스크 → 중심선 피팅 → `/line/error`
(`ai_msgs/LineError`) 발행. 디버그 오버레이(`/line/debug_image`)는 구독자가 있을 때만.

카메라 장치를 직접 열지 않는다 — `usb_cam_publisher` 가 발행하는 토픽만 구독한다
(카메라 HAL 규약. `dataset_collector`·`yolo_detector` 와 동일).

직진 중에는 전방 카메라, 후진 중에는 후방 카메라를 본다. `direction` 파라미터로
런타임 전환하며, 전환 중에는 오차 발행이 잠시 끊기므로 **정지 상태에서만** 바꾼다.

미검출 프레임도 `detected=False` 로 발행한다 — 제어기가 라인 소실을 즉시 감지해야
하므로 침묵은 정지 신호가 될 수 없다.
"""

import cv2
import numpy as np
import rclpy
from ai_msgs.msg import LineError
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import CompressedImage, Image

from line_vision.centerline import (fit_centerline, line_error,
                                   line_x_at_row, select_line_in_roi)

# 가중치 기본 위치 — yolo_detector 와 같은 `/home/nvidia/models/` 관례를 따른다.
DEFAULT_MODEL_PATH = "/home/nvidia/models/line_seg_v1.pt"
# 로스터(config/camera/camera_common.yaml)의 위치 논리명. 런치가 로스터에서 유도해
# 덮어쓴다 — 여기 값은 런치 없이 단독 실행할 때의 폴백이다.
DEFAULT_FORWARD_CAMERA = "cam_f"
DEFAULT_REVERSE_CAMERA = "cam_r"
# 최신 프레임만 쓴다. 큐를 늘리면 밀린 프레임을 추론하느라 지연만 커진다.
SUBSCRIPTION_DEPTH = 1
# 이 프레임 수만큼 연속으로 놓치면 라인 연관을 버린다(20 Hz 기준 약 1 초).
MISS_FRAMES_TO_RESET = 20

# 디버그 오버레이 색 (BGR)
_MASK_COLOR = (0, 255, 255)
_LINE_COLOR = (0, 255, 0)
_POINT_COLOR = (0, 0, 255)


def sensor_qos() -> QoSProfile:
    """카메라 발행자(SensorDataQoS)와 호환되는 구독 프로파일.

    RELIABLE 로 구독하면 호환되지 않아 메시지가 0 이 된다.
    """
    return QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                      history=QoSHistoryPolicy.KEEP_LAST,
                      depth=SUBSCRIPTION_DEPTH)


def camera_for_direction(direction: str, forward: str, reverse: str) -> str:
    """진행 방향에 대응하는 카메라 논리명.

    Args:
        direction: "forward" 또는 "reverse" (대소문자 무시).
        forward: 전진용 카메라 논리명.
        reverse: 후진용 카메라 논리명.
    Returns:
        구독할 카메라 논리명. 모르는 값이면 전진용으로 폴백한다 — 오타 하나로
        카메라를 잃는 것보다 전방을 보는 편이 안전하다.
    """
    return reverse if str(direction).strip().lower() == "reverse" else forward


class LineSegNode(Node):
    """YOLOv8-seg 추론 → 중심선 → LineError 발행 노드."""

    def __init__(self):
        super().__init__("line_seg_node")
        self.declare_parameter("model_path", DEFAULT_MODEL_PATH)
        self.declare_parameter("conf_threshold", 0.5)
        self.declare_parameter("control_row_ratio", 0.8)
        # 기준행 ROI 의 반폭(화면 반폭 대비). 피팅된 **직선**이 이 범위 안에서 기준행을
        # 지나야 후보로 인정한다. 1.0 이면 화면 전체.
        self.declare_parameter("roi_half_width_ratio", 0.9)
        self.declare_parameter("publish_debug_image", True)
        self.declare_parameter("direction", "forward")
        self.declare_parameter("forward_camera", DEFAULT_FORWARD_CAMERA)
        self.declare_parameter("reverse_camera", DEFAULT_REVERSE_CAMERA)
        self.declare_parameter("image_transport", "compressed")
        # 카메라가 뒤집혀 장착됐을 때만 true. 상하만 뒤집으면 좌우 거울상이 남아
        # offset 부호가 물리 좌우와 반대가 되므로 180° 회전(상하+좌우)으로 보정한다.
        self.declare_parameter("forward_flip_180", False)
        self.declare_parameter("reverse_flip_180", False)

        self._conf_threshold = float(self.get_parameter("conf_threshold").value)
        self._control_row_ratio = float(self.get_parameter("control_row_ratio").value)
        self._roi_half_width_ratio = float(self.get_parameter("roi_half_width_ratio").value)
        self._publish_debug = bool(self.get_parameter("publish_debug_image").value)
        self._forward_camera = str(self.get_parameter("forward_camera").value)
        self._reverse_camera = str(self.get_parameter("reverse_camera").value)
        self._transport = str(self.get_parameter("image_transport").value)
        self._camera = ""
        self._flip_180 = False
        # 프레임 간 라인 연관용 — 직전에 고른 기준행 x(px). 소실이 이어지면 비운다.
        self._prefer_x = None
        self._miss_frames = 0
        self._sub = None

        # ultralytics import 는 무겁다(torch 로드 수 초) — 모듈 단순 import(테스트
        # 수집 등)에 부담을 주지 않도록 노드 생성 시점에 지연 로드한다.
        from ultralytics import YOLO
        model_path = str(self.get_parameter("model_path").value)
        self._model = YOLO(model_path)
        self.get_logger().info(f"model loaded: {model_path}")

        self._pub_error = self.create_publisher(LineError, "/line/error", 10)
        self._pub_debug = self.create_publisher(Image, "/line/debug_image", sensor_qos())

        self._subscribe_camera(str(self.get_parameter("direction").value))
        self.add_on_set_parameters_callback(self._on_param_change)

    def _subscribe_camera(self, direction: str) -> None:
        """현재 방향의 카메라로 구독을 (재)생성한다."""
        camera = camera_for_direction(direction, self._forward_camera, self._reverse_camera)
        if self._sub is not None:
            self.destroy_subscription(self._sub)
            self._sub = None
        base = f"/{camera}/image_raw"
        if self._transport == "compressed":
            self._sub = self.create_subscription(
                CompressedImage, base + "/compressed", self._on_image, sensor_qos())
        else:
            self._sub = self.create_subscription(
                Image, base, self._on_image, sensor_qos())
        self._camera = camera
        self._flip_180 = bool(self.get_parameter(
            "reverse_flip_180" if camera == self._reverse_camera else "forward_flip_180").value)
        self.get_logger().info(f"subscribed: {camera} (direction={direction})")

    def _on_param_change(self, params) -> SetParametersResult:
        """`direction` 이 바뀌면 구독을 갈아탄다."""
        for param in params:
            if param.name != "direction":
                continue
            new_camera = camera_for_direction(
                param.value, self._forward_camera, self._reverse_camera)
            if new_camera != self._camera:
                self._subscribe_camera(param.value)
        return SetParametersResult(successful=True)

    def _decode(self, msg) -> np.ndarray:
        """수신 메시지를 BGR ndarray 로 만든다. 장착 보정(`flip_180`)을 여기서 적용한다.

        Returns:
            BGR 이미지. 디코드 실패 시 None.
        """
        if isinstance(msg, CompressedImage):
            frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        else:
            frame = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, -1)
        if frame is None:
            return None
        return cv2.flip(frame, -1) if self._flip_180 else frame

    def _infer_instances(self, frame: np.ndarray):
        """인스턴스별 (마스크 uint8, conf) 목록. 검출 없으면 빈 목록.

        신뢰도가 가장 높은 인스턴스 하나만 쓰면 안 된다 — 신뢰도는 「어느 라인을 따라가야
        하는가」와 무관하다. 바닥에 라인이 여럿이면 엉뚱한 선을 고른다(2026-08-16 실기:
        conf 0.692 인 화면 끝 선을 골라 0.653 인 진짜 라인을 버렸다). 선택은 기하가 한다.
        """
        result = self._model.predict(
            frame, device=0, conf=self._conf_threshold, verbose=False)[0]
        if result.masks is None or len(result.masks) == 0:
            return []
        confs = result.boxes.conf.cpu().numpy()
        height, width = frame.shape[:2]
        out = []
        for inst, conf in zip(result.masks.data.cpu().numpy(), confs):
            m = cv2.resize((inst * 255).astype(np.uint8), (width, height),
                           interpolation=cv2.INTER_NEAREST)
            out.append((m, float(conf)))
        return out

    def _on_image(self, msg) -> None:
        """구독 콜백: 디코드 → 추론 → 중심선 → LineError·디버그 발행."""
        frame = self._decode(msg)
        if frame is None:
            self.get_logger().warn("frame decode failed", throttle_duration_sec=5.0)
            return
        height, width = frame.shape[:2]

        # 인스턴스마다 직선을 뽑고, **그 직선이 기준행 ROI 를 지나는지**로 고른다.
        # 픽셀 유무가 아니라 직선으로 판정하므로 라인이 기준행에서 끊겨도 이어진다.
        # 직전 프레임 위치를 prefer_x 로 넘겨 따라가던 라인을 유지한다(오래 끊기면 중앙 복귀).
        instances = self._infer_instances(frame)
        candidates, confs = [], []
        for m, c in instances:
            ln = fit_centerline(m)
            if ln.valid:
                candidates.append(ln)
                confs.append(c)
        line = select_line_in_roi(candidates, width, height, self._control_row_ratio,
                                  roi_half_width_ratio=self._roi_half_width_ratio,
                                  prefer_x=self._prefer_x)
        conf = float(confs[candidates.index(line)]) if line is not None else 0.0
        mask = None
        if instances:
            mask = np.zeros((height, width), dtype=np.uint8)
            for m, _ in instances:
                mask |= m

        out = LineError()
        out.header = msg.header
        out.camera = self._camera
        if line is not None and line.valid:
            offset, angle = line_error(line, width, height, self._control_row_ratio)
            out.detected = True
            out.offset = offset
            out.angle = angle
            out.confidence = conf
            self._prefer_x = width / 2.0 + offset * (width / 2.0)
            self._miss_frames = 0
        else:
            out.detected = False
            out.offset = 0.0
            out.angle = 0.0
            out.confidence = 0.0
            # 잠깐 끊긴 것과 완전히 놓친 것을 구분한다 — 짧은 소실은 직전 라인을 계속
            # 겨냥하고, 오래 끊기면 연관을 버려 화면 중앙 기준으로 새로 찾는다.
            self._miss_frames += 1
            if self._miss_frames > MISS_FRAMES_TO_RESET:
                self._prefer_x = None
        self._pub_error.publish(out)

        if self._publish_debug and self._pub_debug.get_subscription_count() > 0:
            self._publish_debug_image(frame, mask, line, out, msg.header)

    def _publish_debug_image(self, frame, mask, line, err: LineError, header) -> None:
        """마스크·중심선·제어점 오버레이 이미지를 발행한다."""
        dbg = frame.copy()
        height, width = dbg.shape[:2]
        if mask is not None:
            overlay = dbg.copy()
            overlay[mask > 127] = _MASK_COLOR
            dbg = cv2.addWeighted(overlay, 0.4, dbg, 0.6, 0)
        if line is not None and line.valid:
            p1 = (int(line.p1[0]), int(line.p1[1]))
            p2 = (int(line.p2[0]), int(line.p2[1]))
            cv2.line(dbg, p1, p2, _LINE_COLOR, 2)
            control_y = int(height * self._control_row_ratio)
            control_x = int(width / 2 + err.offset * width / 2)
            cv2.circle(dbg, (control_x, control_y), 6, _POINT_COLOR, -1)
            cv2.putText(
                dbg,
                f"{self._camera} off {err.offset:+.2f} ang {err.angle:+.2f} "
                f"conf {err.confidence:.2f}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, _LINE_COLOR, 2)
        else:
            cv2.putText(dbg, f"{self._camera} NO LINE", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, _POINT_COLOR, 2)
        out = Image()
        out.header = header
        out.height, out.width = dbg.shape[:2]
        out.encoding = "bgr8"
        out.is_bigendian = 0
        out.step = out.width * 3
        out.data = dbg.tobytes()
        self._pub_debug.publish(out)


def main(args=None):
    """노드 수명주기."""
    rclpy.init(args=args)
    node = LineSegNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
