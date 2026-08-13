# line_vision Code Updates

2026-08-13 / (pending commit) / 추가: 신규 패키지 — 라인 추종 인식 계층 이식

- 출처: `kuks2309/TR_3D_Nav_ros2_ws` 의 `src/AI/YOLOv8/tr_line_vision`
  (작업 사본 `/home/nvidia/Project/kkw/TR-Nav3d_ros2_ws`). 인식 계층만 이식,
  제어 계층(2WD Twist 기반 액션 서버)은 범위 밖 — 2WS 재작성 필요
- ADR: `docs/adr/2026-08-13-line-following-ai-port.md`
- 신규 패키지 `src/AI/line_vision/` (ament_python)
  - `line_vision/centerline.py` — 원본 알고리즘 무변경 이식 (스캔라인 무게중심 +
    `cv2.fitLine(DIST_L2)`). ROS·ultralytics 무의존
  - `line_vision/line_seg_node.py` — YOLOv8-seg 추론 → `LineError` 발행
  - `config/line_seg_params.yaml` · `launch/line_seg.launch.py` · `test/test_centerline.py`
- `src/AI/ai_msgs/` 에 `msg/LineError.msg` 추가 (+`CMakeLists.txt` 1줄).
  원본의 전용 인터페이스 패키지 `tr_line_interfaces` 는 만들지 않았다
- 입력: `/<cam>/image_raw/compressed` (`sensor_msgs/CompressedImage`, SensorDataQoS)
- 출력: `/line/error` (`ai_msgs/LineError`, RELIABLE depth 10) ·
  `/line/debug_image` (구독자 존재 시)
- 파라미터: model_path · conf_threshold · control_row_ratio · publish_debug_image ·
  direction · forward_camera · reverse_camera · image_transport ·
  forward_flip_180 · reverse_flip_180
- 의존: rclpy, rcl_interfaces, sensor_msgs, ai_msgs, cv2, numpy, ultralytics
  (신규 설치 0 — 전부 `yolo_detector` 가 이미 쓰는 것과 동일 버전)

원본과 다르게 한 것 3가지:

1. **카메라 퍼블리셔를 이식하지 않았다** — 원본 `tr_camera` 는 `/dev/video0` 를 직접 열지만,
   이 저장소는 `usb_cam_publisher` 가 장치를 점유하고 로스터
   (`config/camera/camera_common.yaml`)가 카메라 이름의 단일 근원이다. 토픽만 구독한다
2. **`cv_bridge` 를 쓰지 않는다** — `CompressedImage` 는 `cv2.imdecode`, 발행은 `Image`
   메시지 직접 조립. 원본은 opencv 5.x ↔ cv_bridge 비호환(KeyError 16)으로 버전을
   고정해야 했는데, 그 결합 자체를 없앴다
3. **방향별 카메라 전환** — `direction` 파라미터(`forward`|`reverse`)로 `cam_f`|`cam_r`
   구독을 갈아탄다. 모델을 두 벌 GPU 에 올리지 않기 위해 노드는 1개다.
   전환 중 오차 발행이 잠시 끊기므로 **정지 상태에서만** 바꾼다

가중치 `/home/nvidia/models/line_seg_v1.pt` 는 원본 학습본을 복사한 것이다(md5 동일).
**타 기체(640×480 4:3, 다른 장착 자세, 58장 단일주행) 학습본이라 Big-AMR
(1280×720 16:9)에서 검출률은 보장되지 않는다** — 실사용 전 `dataset_collector` 로
재수집·재학습 필요.

검증: 단위테스트 17 passed · colcon 2패키지 빌드 성공 · 합성 프레임 end-to-end
(발행 140 → `/line/error` 104, 전부 detected, conf 최대 0.95, offset 부호 기대치 일치) ·
방향 전환 후 구 구독 파기 확인. 실카메라·실라인·실주행은 `[미검증]`.
상세: `docs/code_review/ai-line-vision/2026-08-13.md`
