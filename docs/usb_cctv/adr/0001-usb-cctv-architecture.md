# ADR 0001 — USB 카메라 CCTV 감시 시스템 아키텍처

- **Status**: Accepted
- **Date**: 2026-07-21
- **Deciders**: 사용자(프로젝트 오너), Claude
- **Context tag**: coding SOP §3 사전승인 (신규 공개 API + 의존성)

## 1. Context (배경)

AMR 주변을 CCTV 처럼 감시하기 위해 **최대 6대**의 USB RGB 카메라(현재 Orbbec Gemini E RGB 3대)를
실시간으로 확인해야 한다. 동시에 본 프로젝트는 **USB 카메라 성능 테스트**가 1차 목적이다.

- 하드웨어: Orbbec Gemini E RGB 3대, `/dev/v4l/by-id/usb-...Orbbec_Gemini_E_RGB_Camera_<SERIAL>-video-index0`
  (시리얼 HL / H0 / NR). MJPG 포맷, 최대 1920x1080@30fps. 모두 USB 2.0(480Mbps) 버스 공유.
- 소프트웨어: ROS2 Humble, OpenCV 4.10, cv_bridge, image_transport 설치 확인.

## 2. Decision (결정)

**분리형 파이프라인: V4L2 캡처(C++) → ROS2 토픽 → PyQt5 뷰어(Python).**

```
[usb_cam_publisher] (rclcpp, 카메라당 1노드)         [cctv_viewer] (PyQt5 + rclpy)
 V4L2/OpenCV MJPG 캡처                    ──ROS2──▶   image_transport 구독
 → sensor_msgs/Image 퍼블리시 (bgr8)                  → 1x1/1x3/2x3... 그리드 렌더
 → 캡처 계층에서 FPS/지연 측정·로그                    → 셀당 표시 FPS 오버레이
```

- **퍼블리셔 언어**: C++ (rclcpp) — 고FPS·저CPU. 카메라당 1노드(격리: 1대 실패가 타 카메라에 무영향).
- **스트림**: RGB(컬러)만. Depth 미대상.
- **카메라 식별**: `/dev/v4l/by-id/...-video-index0` (시리얼 기반 안정 경로) — 재장착/리부트에 불변.
- **전송(transport)**: image_transport 로 raw + compressed 동시 제공. 6대 확장 시 대역폭을 위해
  뷰어 기본 구독은 `compressed`(선택 param).
- **성능 측정 지점**: **퍼블리셔의 캡처 계층**(V4L2 프레임 획득 시각) — ROS2 직렬화 지연이 원 USB
  수치를 왜곡하지 않도록 뷰어가 아닌 캡처 지점에서 FPS/드롭을 측정.

### 공개 표면 (Public API)

- **ROS2 토픽** (카메라당): `/<camera_name>/image_raw` (`sensor_msgs/msg/Image`, encoding `bgr8`)
  및 image_transport 파생 `/<camera_name>/image_raw/compressed`.
- **노드 파라미터** (usb_cam_publisher): `video_device`, `camera_name`, `frame_id`,
  `image_width`, `image_height`, `framerate`, `pixel_format`(기본 MJPG), `fps_report_interval_sec`.
- **뷰어 파라미터** (cctv_viewer): `camera_topics`(list), `image_transport`(raw|compressed),
  `layout`(예 "2x3").

## 3. Alternatives (대안)

1. **단순형 직접 캡처 뷰어**(ROS2 없음): 지연 최소·구현 최단이나 프레임을 타 노드와 공유 불가 →
   AMR CCTV(녹화·감지·원격)에서 결국 퍼블리셔 재작성 필요. **기각**.
2. **퍼블리셔 Python(rclpy)**: 구현 단순하나 6대 고FPS에서 CPU/GIL 부담. **기각**(C++ 채택).

## 4. Consequences (영향)

- (+) 1 캡처 → N 소비자. 뷰어 크래시가 캡처를 멈추지 않음. 원격 뷰어 가능.
- (+) ROS2 생태계 일관성(OrbbecSDK_ROS2 와 동일 스택).
- (−) DDS 직렬화 오버헤드 → **성능 수치는 캡처 계층에서 측정**으로 완화.
- (−) 노드 6개 동시 실행 시 loopback 대역폭 부담 → compressed transport 기본.

## 5. Dependencies (§3 의존성 3필드)

| 패키지 | License | 취약점 | 대안 |
| --- | --- | --- | --- |
| rclcpp / sensor_msgs / cv_bridge / image_transport (ROS2 Humble) | Apache-2.0 | ROS2 Humble LTS 유지 | 없음(표준) |
| OpenCV 4.10 | Apache-2.0 | 기설치 | libv4l 직접(복잡) |
| PyQt5 5.15.3 | GPL-v3 / 상용 | 내부 테스트 도구 → GPL 무해 | PySide2(LGPL) 대안 |

## 6. Rollback Plan

- 신규 격리 패키지(`usb_cam_publisher`, `cctv_viewer`)로만 추가 — 기존 코드 무변경.
- 롤백: `src/Sensors/Camera/USB_CCTV/` 삭제 + `colcon build` 재수행. 영속 상태·스키마 변경 없음.
