# 함수표 · 변수표 — 루트 집계

> `coding.md:92` §6 후속갱신의 **이중 기록** 중 루트 집계본. 권위본은 각 모듈의
> `<패키지>/docs/function_table.md` 이며, 본 파일은 그 소재를 모으는 인덱스다.
> 내용을 여기서 복제하지 않는다 — 복제하면 두 벌이 갈라진다.

## 등재된 모듈

| 모듈 | 권위본 | 함수 | 상태 | 최종 갱신 |
| --- | --- | --- | --- | --- |
| `translate_sim_odom` (SIL 플랜트) | [src/Sim/translate_sim_odom/docs/function_table.md](../../src/Sim/translate_sim_odom/docs/function_table.md) | 4 (+이너 2) | 전수 | 2026-08-06 |
| `trnav_2ws_action_server` / **turn 한정** | [src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/function_table.md](../../src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/function_table.md) | 3 | **부분** — turn 만 | 2026-08-06 |
| `seer_pose_publisher` (Seer→/robot_pose) | [src/Navigation/seer_pose_publisher/docs/function_table.md](../../src/Navigation/seer_pose_publisher/docs/function_table.md) | 8 (+이너 0) | 전수 | 2026-08-06 |
| `mcl2d_core` | [src/Navigation/mcl2d_core/docs/function_table.md](../../src/Navigation/mcl2d_core/docs/function_table.md) | — | (별도 세션 작성) | — |

## ⚠ 미등재 — inventory-gate 가 빈 통과하는 범위

`coding.md:53` — 「표가 아예 없으면 **통과**가 기본값이다」. 따라서 아래는 수정 시
`coding/hooks/coding-inventory-gate.py` 가 **선독을 요구하지 않는다.** 표를 만들기 전까지
그 파일들에 대한 §2 강제력은 0 이다.

| 범위 | 규모 | 비고 |
| --- | --- | --- |
| `trnav_2ws_action_server` 의 나머지 8개 액션 | `translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`·`spin`·`crab_linear`·`yaw_control`·`yaw_control_reverse` | turn 과 같은 패키지 |
| `trnav_2ws_motion` (액션 베이스) | `qd_action_server_base.hpp` — `publishWheelCmd`·`guardSteer` 등 | 상류 조향 가드가 여기 있다 |
| `trnav_2ws_kinematics` | IK·dual bicycle·crab | |
| `trnav_motion_mux` · `amr_motor_cmd_translator` | 체인 중간 | |
| `can_relay` | `backend.py`·`driver_node.py`·`protocol.py`·`ui/` | |
| `QD/trnav_motion_action_server` 전체 | 액션 9개 | 검증된 상류 — 2WS 대조 기준 |

## 배포 제약 (미해결)

`docs/claude_guideline/**` **8개 번들이 전부 git 미추적**이라 워크트리에는 규칙 문서 자체가
없다. `coding.md:16` 이 「활성화 게이트: 본 파일이 그 경로에 없으면 본 룰 비활성」이라고
규정하므로, 워크트리 세션에서는 표를 갖춰도 룰이 규정상 비활성이다. 처리 방침은 사용자
결정 대기 —
[실수 기록 2026-08-06-003](../claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md)
§재발 방지.
