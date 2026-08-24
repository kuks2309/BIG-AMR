# pgv_driver — 수정 이력 (code updates)

## 2026-08-24 — 최초 작성

- 매뉴얼 [PGV…-F200/-F200A…-R4-V19 Manual DOCT-3707D 2019-03, §5.1, pages 37–47](../../../../../References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf)
  §5 프로토콜을 근거로 신규 구현 (ADR: docs/adr/2026-08-24-pgv-driver.md).
- `pgv_protocol.{hpp,cpp}` — ROS 무의존 텔레그램 인코딩/파싱: 위치 조회·방향 결정·색 선택
  요청 2바이트, 위치 응답 21바이트(XOR·bit7 프레이밍 검사, XP 24bit·YPS 14bit 부호확장,
  태그/레인 모드 분기), 방향 응답 3바이트, 색 응답 2바이트.
- `pgv_driver_node.cpp` — termios 8-E-1 시리얼(보레이트 4종 매핑, 76800 은 termios 미정의로
  거부), mutex 직렬화 transact(폴링·서비스 공용), 20 Hz 폴링 발행 `pgv/position`
  (SensorDataQoS().reliable() — iahrs 와 동일 근거), 서비스 `pgv/set_direction`·`pgv/set_color`,
  송수신 실패 시 fd 폐기 후 다음 트랜잭션에서 재개방.
- `test/test_pgv_protocol.cpp` — 매뉴얼 예제 벡터(0xC8/0x37, 방향 4종, 색 3종) + 합성 21바이트
  프레임(레인/태그/오류 모드, 길이·프레이밍·XOR 거부) 검증.
- 실기 검증 (같은 날): 실물 PGV(/dev/ttyUSB0, FTDI FT232R)가 위치 조회에 21바이트 XOR
  유효 프레임으로 응답(전원 직후 error code 5), 드라이버 20 Hz 발행 실측, set_direction
  STRAIGHT 적용(applied=3) 후 error 해소 확인. 남은 미검증: 레인/태그 실판독·해상도
  스케일·set_color·컬러 레인 상대각 인코딩 (README §검증 상태).
