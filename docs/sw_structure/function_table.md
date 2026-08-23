# 함수표 · 변수표 — 루트 집계

> `coding.md:92` §6 후속갱신의 **이중 기록** 중 루트 집계본. 권위본은 각 모듈의
> `<패키지>/docs/function_table.md` 이며, 본 파일은 그 소재를 모으는 인덱스다.
> 내용을 여기서 복제하지 않는다 — 복제하면 두 벌이 갈라진다.

## 등재된 모듈

| 모듈 | 권위본 | 함수 | 상태 | 최종 갱신 |
| --- | --- | --- | --- | --- |
| `translate_sim_odom` (SIL 플랜트) | [src/Sim/translate_sim_odom/docs/function_table.md](../../src/Sim/translate_sim_odom/docs/function_table.md) | 4 (+이너 2) | 전수 | 2026-08-06 |
| `trnav_2ws_action_server` / **turn · turn_reverse 한정** | [src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/function_table.md](../../src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/function_table.md) | 6 | **부분** — turn · turn_reverse 만 | 2026-08-09 |
| `seer_pose_publisher` (Seer→/robot_pose) | [src/Navigation/seer_pose_publisher/docs/function_table.md](../../src/Navigation/seer_pose_publisher/docs/function_table.md) | 8 (+이너 0) | 전수 | 2026-08-06 |
| `mcl2d_core` | [src/Navigation/mcl2d_core/docs/function_table.md](../../src/Navigation/mcl2d_core/docs/function_table.md) | — | (별도 세션 작성) | — |
| `mcl2d_ros2` (측위 ROS2 어댑터) | [src/Navigation/mcl2d_ros2/docs/code_review/mcl2d-ros2/2026-08-16.md](../../src/Navigation/mcl2d_ros2/docs/code_review/mcl2d-ros2/2026-08-16.md) | 23 (+멤버변수표) | 전수 | 2026-08-17 |
| `odom_imu_ekf` (오도·IMU 융합 EKF) | [src/Navigation/odom_imu_ekf/docs/function_table.md](../../src/Navigation/odom_imu_ekf/docs/function_table.md) | 9 (+멤버변수표) | 전수 | 2026-08-17 |
| `line_vision` (YOLOv8-seg 라인 인식) | [src/AI/line_vision/docs/code_review/ai-line-vision/2026-08-13.md](../../src/AI/line_vision/docs/code_review/ai-line-vision/2026-08-13.md) | 17 (+dataclass 1·상수 8) | 전수 | 2026-08-13 |
| `trnav_2ws_action_server` / **line_follow 한정** | [src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/code_review/line-follow/2026-08-14.md](../../src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/code_review/line-follow/2026-08-14.md) | 13 (+struct 2·enum 1·클래스 2) | **부분** — line_follow 만 | 2026-08-14 |
| `telegram_notifier` (CAN 경보 텔레그램 통보) | [src/Safety/telegram_notifier/docs/code_review/telegram-notifier/2026-08-23.md](../../src/Safety/telegram_notifier/docs/code_review/telegram-notifier/2026-08-23.md) | 13 (+헬퍼 5·상수 5) | 전수 | 2026-08-23 |
| `wall_localizer_core` (벽 3면 정밀 측위 코어) | [src/Navigation/wall_localizer_core/docs/code_review/wall-localizer/2026-08-19.md](../../src/Navigation/wall_localizer_core/docs/code_review/wall-localizer/2026-08-19.md) | 14 (+struct 10·내부 4) | 전수 | 2026-08-19 |
| `wall_localizer_ros2` (벽 측위 ROS2 어댑터) | [src/Navigation/wall_localizer_ros2/docs/code_review/wall-localizer/2026-08-19.md](../../src/Navigation/wall_localizer_ros2/docs/code_review/wall-localizer/2026-08-19.md) | 7 | 전수 | 2026-08-19 |

## ⚠ 미등재 — inventory-gate 가 빈 통과하는 범위

`coding.md:53` — 「표가 아예 없으면 **통과**가 기본값이다」. 따라서 아래는 수정 시
`coding/hooks/coding-inventory-gate.py` 가 **선독을 요구하지 않는다.** 표를 만들기 전까지
그 파일들에 대한 §2 강제력은 0 이다.

| 범위 | 규모 | 비고 |
| --- | --- | --- |
| `trnav_2ws_action_server` 의 나머지 8개 액션 | `translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`·`spin`·`crab_linear`·`yaw_control`·`yaw_control_reverse` | turn·turn_reverse 와 같은 패키지 |
| `trnav_2ws_motion` (액션 베이스) | `qd_action_server_base.hpp` — `publishWheelCmd`·`guardSteer` 등 | 상류 조향 가드가 여기 있다 |
| `trnav_2ws_kinematics` | IK·dual bicycle·crab | |
| `trnav_motion_mux` · `amr_motor_cmd_translator` | 체인 중간 | |
| `can_relay` | `backend.py`·`driver_node.py`·`protocol.py`·`ui/` | |
| `QD/trnav_motion_action_server` 전체 | 액션 9개 | 검증된 상류 — 2WS 대조 기준 |

## ⚠ 2026-08-09 변경분 중 **표가 없어 등재하지 못한 것**

아래는 오늘 실제로 수정했으나 해당 모듈에 함수표가 없어 §6 이중 기록을 못 했다.
표를 만들기 전까지 이 파일들의 §2 선독 강제력은 0 이다(위 「미등재」와 같은 사유).

| 파일 | 오늘 변경 내용 | 커밋 |
| --- | --- | --- |
| `trnav_2ws_kinematics/src/qd_inverse_kinematics.cpp` | `computeSpin` 을 범용 IK 경유 → **±90° 강제**로 전환. `isInline()` 신설 | `6d91297` |
| `trnav_2ws_motion/include/…/qd_action_server_base.hpp` | 기하 기본값 QD 대각 잔재 정정(±0.330/±0.135 → 0.6039/0.0 등) · **인라인 전제 가드**(위반 시 FATAL 기동 실패) 추가 | `6d91297` |
| `trnav_2ws_action_server/src/spin/spin_action_server.cpp` | 죽은 파라미터 3종 제거(`fine_correction_timeout_sec`·`fine_correction_speed_dps`·`settling_delay_ms`) + 화이트리스트 분기 제거 | `4c03c76` |
| `can_relay/can_relay/backend.py` | `set_motor_cmds` 의 호밍 판정을 `homed_effective()` 로 통일 · `_write_bringup` 을 **구동축 전용**으로 축소 | `0b38966` · `a7420a6` |

## 배포 제약 (미해결)

`docs/claude_guideline/**` **8개 번들이 전부 git 미추적**이라 워크트리에는 규칙 문서 자체가
없다. `coding.md:16` 이 「활성화 게이트: 본 파일이 그 경로에 없으면 본 룰 비활성」이라고
규정하므로, 워크트리 세션에서는 표를 갖춰도 룰이 규정상 비활성이다. 처리 방침은 사용자
결정 대기 —
[실수 기록 2026-08-06-003](../claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md)
§재발 방지.
