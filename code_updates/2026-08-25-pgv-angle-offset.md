# 2026-08-25 — pgv_driver angle_offset_deg 추가 (설치 고정각 0° 정렬)

- 요약: PGV 각도 판독의 설치 고정 오프셋(~45°)을 드라이버 파라미터로 보정.
  상세·검증은 패키지 권위본 `src/Sensors/Positioning/pgv_ros2/pgv_driver/docs/pgv_driver_code_updates.md`
  2026-08-25 절과 ADR `docs/adr/2026-08-25-pgv-angle-offset.md`.
- 실기: offset 45.3 적용 → angle_deg 0.0(raw 453 보존), x/y 불변.

## 추가 — frame_rotation_deg (같은 날 후속)

축 실측(−90° 관계) 후 발행 x/y 를 REP-103 로봇 프레임으로 회전하는 파라미터 추가.
상세는 패키지 권위본 같은 날짜 절. 운용: `angle_offset_deg:=45.3 frame_rotation_deg:=-90.0`.
