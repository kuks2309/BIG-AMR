# 2026-08-24 — PGV 읽기 헤드 ROS2 드라이버 신설 (pgv_ros2)

- **무엇**: `src/Sensors/Positioning/pgv_ros2/` 신설 — `pgv_interfaces`(msg 1·srv 2) +
  `pgv_driver`(ROS 무의존 프로토콜 모듈 + termios 8-E-1 노드 + gtest 10건).
- **근거**: `References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf` (DOCT-3707D 2019-03) §5 RS-485
  프로토콜. ADR: `docs/adr/2026-08-24-pgv-driver.md`.
- **검증**: colcon build 2패키지 성공 · gtest 10/10 PASS(매뉴얼 예제 벡터) · **실기 검증** —
  실물 PGV(/dev/ttyUSB0)가 위치 응답 21바이트 XOR 유효 프레임 응답(전원 직후 error 5),
  20 Hz 발행 실측, `pgv/set_direction` STRAIGHT 적용 후 error 5 해소 확인.
- **미해결**: debt-125 (레인 실판독·해상도 preset·컬러 레인 각도 인코딩·set_color 실기).
- **상세**: `src/Sensors/Positioning/pgv_ros2/pgv_driver/docs/pgv_driver_code_updates.md` ·
  `…/pgv_interfaces/docs/pgv_interfaces_code_updates.md` (패키지 권위본).
- **부수**: `References/PGV/` → `References/pepperl-fuchs/pgv/` 정규화(external_reference §1,
  gitignore 대상이라 git 변화 없음). 루트 함수표에 `pgv_driver` 등재.
