# 2WS ↔ can_relay 연동 접점 — 리뷰 타임라인

대상: 2WS 모션 스택(`src/Control/Motion_Control/2WS`) ↔ `can_relay`(`src/Comm/CAN/can_relay`) 를
잇는 접점 코드. 중간 노드 `trnav_motion_mux` · `amr_motor_cmd_translator`
(`src/Control/Motion_Control/Common`) 포함.

다중 패키지 횡단이라 **루트 정본만 기록**한다(SOP §기록 위치: 패키지 루트 특정 불가 시 병기 생략).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-05](2026-08-05.md) | `45d6a7b` (main) | REQUEST CHANGES | Critical 1 — 조향 원점 정규화 주체 부재(0° 지령이 홈−90° 로 지령됨). High 5 — 조향/구동 스케일 상류값 잔존, 액션 서버 기하 미정합, 크랩 ±115° vs 클램프 ±90°, 통합 런치 부재 |

## 관련 문서

- can_relay 단독 리뷰: [`../can_relay_ros2/`](../can_relay_ros2/) (2026-07-29 전수 · 2026-08-03 delta)
- can_relay UI 리뷰: [`../can_relay_ui/`](../can_relay_ui/)
- 구조 분석: [`../../sw_structure/can_relay_ros2/`](../../sw_structure/can_relay_ros2/)

## 재리뷰 필요 여부

`45d6a7b` 이후 접점 파일이 바뀌면 delta 리뷰를 추가한다. 확인:

```bash
git log --oneline 45d6a7b..HEAD -- \
  src/Control/Motion_Control/Common \
  src/Control/Motion_Control/2WS/trnav_2ws_motion \
  src/Control/Motion_Control/2WS/trnav_2ws_kinematics \
  src/Comm/CAN/can_relay/can_relay/backend.py \
  src/Comm/CAN/can_relay/can_relay/driver_node.py
```
