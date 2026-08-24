# pgv_driver — 함수표 · 전역변수표 (모듈 권위본)

> 대상: `src/Sensors/Positioning/pgv_ros2/` 의 `pgv_driver`·`pgv_interfaces`.
> 근거 1차 source: [PGV…-F200/-F200A…-R4-V19 Manual DOCT-3707D 2019-03, §2.2 page 9 · §5 pages 37–47](../../../../../References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf) (로컬 보관, gitignore 대상)

## 함수표 — pgv_protocol (ROS 무의존 순수 모듈)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `xorChecksum` | `uint8_t xorChecksum(const uint8_t *buf, size_t n)` | 바이트열 XOR 누적(응답 무결성 검사, 매뉴얼 Table 5.1 Byte 21) | pgv_protocol.cpp:25 |
| `makePositionRequest` | `std::array<uint8_t,2> makePositionRequest(uint8_t addr)` | 위치 조회 요청 2바이트 생성 (addr0 → 0xC8 0x37) | pgv_protocol.cpp:35 |
| `makeDirectionRequest` | `std::array<uint8_t,2> makeDirectionRequest(Direction dir, uint8_t addr)` | 방향 결정 요청 생성 (직진 0xEC 0x13 / 좌 0xE8 0x17 / 우 0xE4 0x1B / 해제 0xE0 0x1F) | pgv_protocol.cpp:42 |
| `makeColorRequest` | `std::array<uint8_t,2> makeColorRequest(Color color, uint8_t addr)` | 색 선택 요청 생성 (청 0xC4 0x3B / 녹 0x88 0x77 / 적 0x90 0x6F) | pgv_protocol.cpp:53 |
| `parsePositionResponse` | `ParseResult parsePositionResponse(const uint8_t *buf, size_t len, PositionFrame &out)` | 21바이트 위치 응답 → 필드 분해(XOR·길이 검사, XP 24bit·YPS 14bit 부호확장·ANG·TAG·CC·WRN) | pgv_protocol.cpp:66 |
| `parseDirectionResponse` | `ParseResult parseDirectionResponse(const uint8_t *buf, size_t len, uint8_t &dir_bits)` | 3바이트 방향 응답 → LL/RL 비트(XOR 검사) | pgv_protocol.cpp:147 |
| `parseColorResponse` | `ParseResult parseColorResponse(const uint8_t *buf, size_t len, uint8_t &color_bits)` | 2바이트 색 응답 → R/G/B 비트(반복 바이트 일치 검사) | pgv_protocol.cpp:168 |
| (내부) `signExtend` | `int32_t signExtend(uint32_t v, unsigned bits)` | N비트 값 부호확장(매뉴얼 "fill missing upper bits with highest bit") | pgv_protocol.cpp:11 |

## 함수표 — pgv_driver_node (ROS2 노드)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `PgvDriver::PgvDriver` | `PgvDriver()` | 파라미터 선언·시리얼 개방·pub/srv/timer 구성 | pgv_driver_node.cpp:39 |
| `PgvDriver::serialOpen` | `bool serialOpen()` | termios 8-E-1 개방(보레이트 매핑, 미지원 값 거부) | pgv_driver_node.cpp:95 |
| `PgvDriver::transact` | `bool transact(const uint8_t *req, size_t req_len, uint8_t *rsp, size_t rsp_len)` | 입력 flush → 요청 write → 마감시한 내 rsp_len 수신 (mutex 직렬화), 실패 시 fd 폐기·차기 재개방 | pgv_driver_node.cpp:146 |
| `PgvDriver::pollTimer` | `void pollTimer()` | 위치 조회 폴링 → 파싱·주소 대조 → `pgv/position` 발행, 실패 카운트·스로틀 로그 | pgv_driver_node.cpp:197 |
| `PgvDriver::toMsg` | `pgv_interfaces::msg::PgvPosition toMsg(const pgv_protocol::PositionFrame &f)` | 프레임 → 메시지(해상도 파라미터 스케일 적용, ERR 시 위치 무효) | pgv_driver_node.cpp:230 |
| `PgvDriver::onSetDirection` | `void onSetDirection(req, rsp)` | `pgv/set_direction` 서비스 — 방향 텔레그램 송수신·적용값 반환 | pgv_driver_node.cpp:269 |
| `PgvDriver::onSetColor` | `void onSetColor(req, rsp)` | `pgv/set_color` 서비스 — 색 텔레그램 송수신·요청색 일치 확인 | pgv_driver_node.cpp:299 |
| `main` | `int main(int argc, char **argv)` | rclcpp 스핀 | pgv_driver_node.cpp:347 |

## 전역변수표

| 이름 | 타입 | 값/기본 | 위치 | 누가 바꾸나 |
| --- | --- | --- | --- | --- |
| `kPositionResponseLen` | `constexpr size_t` | 21 | pgv_protocol.hpp:16 | 불변(매뉴얼 §5.1.2) |
| `kDirectionResponseLen` | `constexpr size_t` | 3 | pgv_protocol.hpp:17 | 불변(매뉴얼 §5.1.3) |
| `kColorResponseLen` | `constexpr size_t` | 2 | pgv_protocol.hpp:18 | 불변(매뉴얼 §5.1.4) |
| `kMaxAddress` | `constexpr uint8_t` | 3 | pgv_protocol.hpp:20 | 불변(A1·A0 2비트) |
| `kBaudMap` | `const std::map<int, speed_t>` | 38400/57600/115200/230400 | pgv_driver_node.cpp:28 | 불변 — 76800 은 termios 미정의로 제외 |
| (파라미터) `serial_port` | string | `/dev/ttyUSB0` | pgv_driver_node.cpp | 런치/CLI |
| (파라미터) `baudrate` | int | 115200 (장치 preset) | pgv_driver_node.cpp | 런치/CLI — 38400/57600/115200/230400 만(76800 은 Linux termios 미정의) |
| (파라미터) `address` | int | 0 | pgv_driver_node.cpp | 런치/CLI (0..3) |
| (파라미터) `poll_rate_hz` | double | 20.0 | pgv_driver_node.cpp | 런치/CLI |
| (파라미터) `position_resolution_mm` | double | 0.1 | pgv_driver_node.cpp | 런치/CLI — ⚠ 장치 설정(코드 카드)과 일치 필수, 공장 preset 매뉴얼 서술 없음 |
| (파라미터) `angle_resolution_deg` | double | 0.1 | pgv_driver_node.cpp | 런치/CLI — DM 테이프 절대각 스케일 |
| (파라미터) `frame_id` | string | `pgv_link` | pgv_driver_node.cpp | 런치/CLI |

## 공개 인터페이스 (pgv_interfaces)

| 이름 | 종류 | 내용 |
| --- | --- | --- |
| `msg/PgvPosition` | msg | 모드 플래그(TAG/NL/NP/RP/LC)·위치(x/y/angle 스케일+raw)·태그번호·제어코드(O/S/번호)·방향선택 상태·WRN/ERR |
| `srv/SetDirection` | srv | 상수 NONE=0/RIGHT=1/LEFT=2/STRAIGHT=3 (LL<<1\|RL 비트 배치와 동일), 응답 success+applied |
| `srv/SetColor` | srv | 상수 BLUE=1/GREEN=2/RED=4 (B/G/R 비트 배치와 동일), 응답 success |

> 2026-08-24 구현 후 실제 줄번호로 정정 완료. 단위 테스트 10/10 PASS + 실기 검증
> (센서 /dev/ttyUSB0 응답: error 5 프레임 수신·20 Hz 발행·set_direction STRAIGHT 적용 확인).
