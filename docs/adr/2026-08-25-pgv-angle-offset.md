# ADR: pgv_driver 에 angle_offset_deg 파라미터 추가

- 날짜: 2026-08-25 · 상태: 승인(사용자 지시 "그러면 설정을 0도로 바꾸어주세요")
- 배경: 매트릭스를 로봇 축과 평행하게 놓아도 PGV(Position Guided Vehicle) angle 이
  ~45° 로 읽힌다(08-24 44.4° · 08-25 03:42 44.6° · 08-25 11:10 45.3° — 고정 특성).
  장치 원생 보정은 Orientation O 가 90° 단위뿐이라(DOCT-3707D §5.1.2.2) 45° 를 못 지운다.
- 결정: 드라이버에 `angle_offset_deg`(double, 기본 0.0) 파라미터를 추가하고
  `angle_deg = wrap(angle_raw×angle_resolution_deg − angle_offset_deg)` 로 발행한다
  (범위 [−180, 180)). `angle_raw` 는 원본 그대로 유지 — 장치 판독 추적성 보존.
- 대안 기각: ① 장치 설정(90° 단위라 불가) ② 소비측 보정(소비자마다 중복, 기준 불일치 위험).
- 영향: 기본값 0.0 이라 기존 소비자 무변화. 검증은 실기 판독(오프셋 적용 후 ≈0°)로.

## 부록 (2026-08-25 후속) — frame_rotation_deg 추가

- 배경: 전후·좌우 실이동 대조로 장치 축 = 로봇 축 −90° 회전(장치 x=우측+, y=전방+) 확정.
- 결정: 발행 x/y 를 `p_robot = R(frame_rotation_deg)·p_dev` 로 회전(기본 0 = 무변화,
  운용 −90). raw 미적용, angle 은 angle_offset_deg 소관 유지. 사용자 승인
  ("물리 재배치는 현실적으로 힘들고 소프트웨어적으로 처리하는 것이 맞음").
