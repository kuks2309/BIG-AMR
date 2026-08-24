# ADR 2026-08-24 — Pepperl+Fuchs PGV 읽기 헤드 ROS2 드라이버 신설

- **Status**: Accepted — 2026-08-24 (단위 테스트 10/10 PASS + **실기 부분 검증**: /dev/ttyUSB0 의 실물 PGV 가 위치 응답 21바이트·XOR 유효 프레임으로 응답, 20 Hz 발행, set_direction STRAIGHT 적용 후 error 5 해소 확인. 레인 판독·색 선택·해상도 스케일은 테이프 부재로 미검증)

## Context

- 사용자가 `References/PGV`(현 `References/pepperl-fuchs/pgv/`)의 1차 자료를 근거로 `src/Sensors/` 아래 PGV 구현 패키지 설치를 요청했다.
- 1차 자료 실사 결과:
  - `tdoct3707d_eng.pdf` = [PGV…-F200/-F200A…-R4-V19 Incident Light Positioning System Manual, DOCT-3707D, 2019-03] — RS-485 판 읽기 헤드 매뉴얼(63쪽). 통신 프로토콜 전체가 §5 에 있다: 요청 2바이트(둘째 바이트 = 첫째 바이트 반전), 위치 응답 21바이트 + XOR 체크섬, 방향 결정 응답 3바이트, 색 선택 응답 2바이트. 시리얼은 **8-E-1**, 전송률 38400/57600/76800/115200(preset)/230400 bit/s ([manual §2.2, page 9](../../References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf)).
  - `1833705u.zip` = `VCSetup7.1.0+g93016ac.exe` — Windows 전용 Vision Configurator 설치기. **Linux 런타임 구현에는 사용 불가**(파라미터라이징 도구일 뿐). 따라서 "설치 파일 참조 설치"는 exe 설치가 아니라 **매뉴얼 §5 프로토콜 기반 드라이버 신규 작성**으로 해석한다.
- 저장소에 PGV 관련 기존 코드 0건(grep 확인). 기존 시리얼 센서 드라이버 선례는 `src/Sensors/IMU/iahrs_driver_ros2/`(C++ · termios · 드라이버+interfaces 2패키지 구성).
- 이 기체는 라인 트래킹 주행 스택(`trnav_2ws_action_server` line_follow, `src/AI/line_vision`)을 이미 갖고 있고, PGV 의 Y 편차·각도 출력은 그 계열의 센서 입력 후보다.

## Decision

- `src/Sensors/Positioning/pgv_ros2/` 에 2패키지를 신설한다 (iahrs 선례와 동일 구성):
  - **`pgv_interfaces`** — `msg/PgvPosition.msg`, `srv/SetDirection.srv`, `srv/SetColor.srv`
  - **`pgv_driver`** — C++17. 프로토콜 인코딩/파싱을 ROS 무의존 순수 모듈(`pgv_protocol.{hpp,cpp}`)로 분리해 gtest 단위 테스트로 검증하고, 노드(`pgv_driver_node.cpp`)는 termios 8-E-1 시리얼 + 폴링 타이머 + 서비스 2종만 담당한다.
- 인터페이스(공개표면):
  - 발행 `pgv/position` (`PgvPosition`) — 위치 조회 텔레그램 폴링 결과(기본 20 Hz, 파라미터).
  - 서비스 `pgv/set_direction`(직진/좌/우/해제), `pgv/set_color`(적/녹/청).
- 스케일은 장치 설정값이므로 코드 상수로 단정하지 않는다 — `position_resolution_mm`(기본 0.1)·`angle_resolution_deg`(기본 0.1)를 파라미터로 두고, 매뉴얼에 공장 preset 서술이 없음을 README 에 ⚠ 로 명시한다(코드 카드/Vision Configurator 설정과 일치시켜야 함).
- 외부 OSS 드라이버 이식이 아니라 매뉴얼 직접 구현을 택한다 — 프로토콜이 2~21바이트 고정 프레임으로 얇아 이식 대비 검증 비용이 낮고, 저장소 밖 코드의 라이선스·품질 감사를 생략할 수 있다.

## Alternatives

- **외부 OSS ROS 드라이버 이식** — 기각: 대상 선정·라이선스 확인·ROS1→ROS2 변환 감사가 필요하고, 그 코드도 결국 같은 매뉴얼의 재구현이다.
- **Python(pyserial) 구현** — 기각: Sensors 계열 기존 선례(iahrs C++·termios)와 일관성 유지, 20 Hz 폴링 + 8E1 저수준 제어에 추가 의존성 불요.

## Consequences

- 이득: 라인 트래킹/태그 측위 센서 입력이 표준 토픽으로 확보된다. 프로토콜 모듈이 순수 함수라 실기 없이 매뉴얼 예제 벡터(0xC8/0x37, 0xE8/0x17 등)로 회귀 가능.
- 의존성 추가: 없음(rclcpp·rosidl·ament_cmake_gtest — 전부 기존 사용 중). License: 자작 코드 Apache-2.0(`telegram_notifier` 선례). 취약점 표면: 시리얼 로컬 장치뿐, 네트워크 없음.
- 남는 위험: **실기 미검증** — ⚠ 8E1 패리티·응답 타이밍·컬러 레인 모드의 ANG 부호 표현(매뉴얼이 -45°~45° 라 하나 14bit 인코딩 방식 미서술)은 센서 연결 후 실측으로 확정해야 한다. 미확정 항목은 README 와 debt 로 추적.

## Rollback

N/A (가역) — `src/Sensors/Positioning/pgv_ros2/` 삭제 + 루트 함수표 등재 행 제거로 원복. 영속 상태·스키마·펌웨어 접촉 없음.
