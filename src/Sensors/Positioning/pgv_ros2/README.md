# pgv_ros2 — Pepperl+Fuchs PGV 읽기 헤드 드라이버

Pepperl+Fuchs **PGV…-F200/-F200A…-R4-V19** (Incident Light Positioning System, RS-485 판)
읽기 헤드의 ROS2 드라이버. 컬러 테이프/Data Matrix 코드 테이프 레인 추적과 Data Matrix
태그 그리드 측위 데이터를 폴링해 토픽으로 발행한다.

- 1차 source: [PGV Manual DOCT-3707D 2019-03](../../../../References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf)
  (로컬 보관 — `References/` 는 gitignore 대상이라 저장소에는 없음. 텍스트 추출본 `.txt` 동봉)
- 참고: 함께 보관된 `1833705u.zip` 은 Windows 전용 Vision Configurator 설치기
  (`VCSetup7.1.0+g93016ac.exe`) — 장치 파라미터라이징 PC 도구이며 이 드라이버와 무관.
- 설계 결정: [ADR 2026-08-24 — PGV 드라이버 신설](../../../../docs/adr/2026-08-24-pgv-driver.md)

## 패키지 구성

| 패키지 | 내용 |
| --- | --- |
| `pgv_interfaces` | `msg/PgvPosition` · `srv/SetDirection` · `srv/SetColor` |
| `pgv_driver` | `pgv_protocol`(ROS 무의존 텔레그램 인코딩/파싱, gtest 대상) + `pgv_driver_node` |

## 통신 사양 (매뉴얼 §2.2, §5.1)

- RS-485, **8-E-1** (8 데이터 비트 + 짝수 패리티 + 정지 1비트)
- 전송률: 38400 / 57600 / 76800 / 115200(**장치 preset**) / 230400 bit/s
  — ⚠ 76800 은 Linux termios 상수가 없어 본 드라이버는 미지원
- 요청 2바이트(둘째 = 첫째의 8비트 반전), 위치 응답 21바이트(마지막 바이트 = XOR),
  방향 결정 응답 3바이트, 색 선택 응답 2바이트

## 인터페이스

| 이름 | 종류 | 내용 |
| --- | --- | --- |
| `pgv/position` | pub `PgvPosition` | 위치 폴링 결과 (기본 20 Hz) |
| `pgv/set_direction` | srv `SetDirection` | 직진/좌/우/해제 (STRAIGHT=3, LEFT=2, RIGHT=1, NONE=0) |
| `pgv/set_color` | srv `SetColor` | 추종 레인 색 (BLUE=1, GREEN=2, RED=4) |

## 파라미터 (config/pgv_driver.yaml)

| 파라미터 | 기본 | 비고 |
| --- | --- | --- |
| `serial_port` | `/dev/ttyUSB0` | USB-RS485 어댑터. 고정 이름이 필요하면 udev alias 권장 |
| `baudrate` | 115200 | 장치 preset 과 동일 |
| `address` | 0 | 읽기 헤드 주소 0..3 (코드 카드 §6.1.2 로 설정) |
| `poll_rate_hz` | 20.0 | 위치 조회 주기 |
| `serial_timeout_ms` | 50 | 트랜잭션 수신 마감시한 |
| `position_resolution_mm` | 0.1 | ⚠ 장치 설정(§6.1.3: 0.1/1/10 mm)과 일치 필수 |
| `angle_resolution_deg` | 0.1 | ⚠ 장치 설정(§3.2: 0.1/0.2/0.5/1 °)과 일치 필수 |
| `frame_id` | `pgv_link` | 메시지 header |

## 기동

```bash
colcon build --packages-select pgv_interfaces pgv_driver
source install/setup.bash
ros2 launch pgv_driver pgv_driver.launch.py
# 방향 결정 (전원 인가 후 필요 — 아래 참조)
ros2 service call /pgv/set_direction pgv_interfaces/srv/SetDirection "{direction: 3}"
```

## 커미셔닝 주의 (매뉴얼 §4.1–4.2, §5.1.2)

- **전원 인가 후 방향 결정이 없으면 장치는 error code 5** 를 낸다.
  **드라이버가 기동 시 자동으로 보낸다**(`startup_direction`, 기본 3=직진; −1 이면 안 보냄).
  폴링 중 error 5 를 관측하면 `auto_recover_direction`(기본 참)이 마지막 방향을 재전송한다 —
  센서만 전원이 재인가된 경우를 덮는다. 수동 개입이 필요하면 `pgv/set_direction` 서비스를 쓴다.
- Data Matrix 코드 테이프/태그가 시야에 있으면 **컬러 레인보다 우선**한다 (§2.1).
- 레인 추적 중 X 는 무부호, 태그 위에서는 부호 있음 — 메시지의 `tag_detected` 로 구분.
- `error=true` 프레임에서는 위치 필드가 무효이고 `error_code`(2/5/6/>1000, Table 5.4)만
  유효하다. `x_position_mm` 은 이때 0 으로 채워진다.

## 검증 상태 (2026-08-24)

**✓ 실기 검증 완료** (실물 PGV @ /dev/ttyUSB0, FTDI FT232R USB-RS485):

- 위치 조회 → 21바이트 응답 수신, XOR 체크섬 유효
  (전원 인가 직후 프레임 `03 04 00 00 00 05 … 02` = ERR + error code 5, 매뉴얼 §4.1 그대로)
- 드라이버 20 Hz 발행 실측 (`ros2 topic hz` 19.8–20.1)
- `pgv/set_direction {direction: 3}` → `success=True, applied=3`, 이후 error 5 해소 확인
- 단위 테스트 10/10 PASS (매뉴얼 예제 벡터 + 합성 프레임)

**⚠ 미검증** (레인 테이프·태그 실물 필요):

- 실제 레인/태그 판독 (X·Y·각도 스케일 포함) — 위치/각도 해상도의 **공장 preset 은
  매뉴얼에 서술이 없으므로** 테이프 실장 시 장치 설정과 파라미터 일치를 확인할 것
- `pgv/set_color` 서비스 (현장 테이프 색 미정이라 실기 호출 보류)
- 컬러 테이프(레인) 모드의 상대각(-45°~+45°, 1° 해상도, §3.2)이 14bit ANG 필드에
  어떻게 인코딩되는지 매뉴얼이 명시하지 않음 — 실측으로 확정 필요. 현재 드라이버는
  무부호 그대로 `angle_raw` 에 싣고 `angle_deg = raw × angle_resolution_deg` 만 적용한다.
