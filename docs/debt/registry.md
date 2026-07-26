# 부채 registry (Debt Registry)

기술·이해·의도 부채의 등록·추적. **항목은 append, 해결도 기록(덮어쓰기 금지).** 코드 마커는 여기 `id` 를 참조한다 (`# TODO(debt-001): ...`).

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| debt-001 | 기술 | (예시) src/foo.py:42 | 임시 하드코딩 상수 | 2026-01-01 | 미해결 | 설정 파일로 이전 |
| debt-002 | 기술 | src/Sensors/IMU/iahrs_driver_ros2/iahrs_driver/launch/iahrs_driver.py:44 | base_link→imu_link static TF 마운트값 (-0.37, 0, 0.29)이 TR-AMR 실측값 — Big-AMR 차체와 다름. 이식 시 원본 그대로 가져옴(bit-identical) | 2026-07-26 | 미해결 | Big-AMR 실제 IMU 장착 위치 실측 후 arguments(--x/--y/--z, 필요시 회전) 갱신. 사용자 나중에 입력 예정 |

<!-- 새 부채는 위 표에 행 추가. 유형: 기술 / 이해 / 의도. 상태: 미해결 / 해결(해결일·커밋 병기). -->
