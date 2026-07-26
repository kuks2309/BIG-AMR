# full_project — 전체 프로젝트 SW 구조 (타임라인 인덱스)

Big-AMR(Ford-CATL AMR retrofit) `src/` 전체의 코드 레벨 SW 구조 분석. SOP: `docs/claude_guideline/sw_structure/structure.md`.
산출물 = ① 파일 의존 그래프 · ② 클래스 관계도 · ③ 시퀀스 · ④ 연결 관계표 · ⑤ 구조 관찰 + `.drawio` 3종.
이중 기록: 루트 정본(본 폴더) + 각 패키지 루트 `docs/sw_structure/full_project/` 병기.

| 날짜(버전) | 제목 | 정본 | drawio |
|-----------|------|------|--------|
| 2026-07-26 | 전체 프로젝트 SW 구조 (코드 레벨 실측, 13 pkg + 4 stub) | [2026-07-26.md](2026-07-26.md) | [-file-graph](2026-07-26-file-graph.drawio) · [-class](2026-07-26-class.drawio) · [-sequence](2026-07-26-sequence.drawio) |

## 커버리지 요약 (2026-07-26)
- **코드 존재(실측)**: motor_control, trnav_msgs·trnav_interfaces·trnav_motion_core·trnav_qd_kinematics·trnav_motion_qd·trnav_motion_action_server(QD 6), iahrs_driver·interfaces(IMU), sick_safetyscanners2·dual_laser_merger·lidar_calibration_2d·seer_lidar_tf(Lidar 2D).
- **stub(빈 디렉토리, 코드 0)**: Comm/CAN/can_relay, Control/Seer, Safety, Sensors/Lidar/3D, Control/Motion_Control/{2WS,4IS,DD}.
