# full_project — 전체 프로젝트 SW 구조 (타임라인 인덱스)

Big-AMR(Ford-CATL AMR retrofit) `src/` 전체의 코드 레벨 SW 구조 분석. SOP: `docs/claude_guideline/sw_structure/structure.md`.
산출물 = ① 파일 의존 그래프 · ② 클래스 관계도 · ③ 시퀀스 · ④ 연결 관계표 · ⑤ 구조 관찰 + `.drawio` 3종.
이중 기록: 루트 정본(본 폴더) + 각 패키지 루트 `docs/sw_structure/full_project/` 병기.

| 날짜(버전) | 제목 | 정본 | drawio |
|-----------|------|------|--------|
| 2026-07-26 | 전체 프로젝트 SW 구조 (코드 레벨 실측, ~~13 pkg + 4 stub~~ → **13 pkg 커버 / 24 pkg 중 11 미커버 · stub 6**) | [2026-07-26.md](2026-07-26.md) | [-file-graph](2026-07-26-file-graph.drawio) · [-class](2026-07-26-class.drawio) · [-sequence](2026-07-26-sequence.drawio) |

## 커버리지 요약 (2026-07-26)
- **코드 존재(실측)**: motor_control, trnav_msgs·trnav_interfaces·trnav_motion_core·trnav_qd_kinematics·trnav_motion_qd·trnav_motion_action_server(QD 6), iahrs_driver·interfaces(IMU), sick_safetyscanners2·dual_laser_merger·lidar_calibration_2d·seer_lidar_tf(Lidar 2D).
- **stub(빈 디렉토리, 코드 0)**: ~~Comm/CAN/can_relay, Control/Seer, Safety, Sensors/Lidar/3D, Control/Motion_Control/{2WS,4IS,DD}.~~
  → ⚠ **2026-07-27 감사 정정(반증됨)**: **2WS 는 stub 이 아니다** — 실측 `package.xml` **6**, 코드파일 **67**(생성 2026-07-26 17:51, 예 `trnav_2ws_core/src/localization_monitor.cpp`). 본 커버리지 요약에 **미포함(커버리지 공백)**일 뿐이다.
  실제 stub(파일 0 재실측 확인)은 **6개**: `Comm/CAN/can_relay`, `Control/Seer`, `Safety`, `Sensors/Lidar/3D`, `Control/Motion_Control/{4IS,DD}`.
  (원 stub 판정에 쓰인 `find -name '*.py|*.cpp|...'` 패턴은 무효였다 — 2026-07-26.md §'stub 5(+2) 구성' 정정 블록 참조.)

## ⚠ 커버리지 공백 (2026-07-27 감사)
본 2026-07-26 분석은 '`src/` 전체'가 아니다. 실측 `find src -name package.xml | wc -l` → **24** 중 **13 만 커버**했고,
아래 **11 패키지는 문서 작성 시각(2026-07-26 21:30) 이전에 이미 존재했는데도 ①~⑤·④ 표 어디에도 없다**:
- `Sensors/Camera/RGBD/OrbbecSDK_ROS2/{orbbec_camera, orbbec_camera_msgs, orbbec_description}` (2026-07-18 20:28)
- `Tools/USB_CCTV/{usb_cam_publisher, vision_guard}` (2026-07-21 15:02 / 15:08)
- `Control/Motion_Control/2WS/{trnav_2ws_core, trnav_2ws_msgs, trnav_2ws_action_server, trnav_2ws_kinematics, trnav_2ws_motion, trnav_2ws_interfaces}` (2026-07-26 17:51)

또한 **Black Panda relay 는 '미구현'이 아니다** — `Tools/Can_Relay/panda-firmware` 에 코드가 있고 구조는 `docs/sw_structure/panda-relay-firmware/2026-07-20.md` 에 실측 기록돼 있다. 2026-07-26 문서의 '미구현' 판정은 **`src/` ROS2 패키지 한정** 조건에서만 참이다.
