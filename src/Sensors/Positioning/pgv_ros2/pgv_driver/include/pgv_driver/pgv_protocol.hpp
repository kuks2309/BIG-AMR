// Pepperl+Fuchs PGV...-F200/-F200A...-R4-V19 RS-485 텔레그램 인코딩/파싱.
// ROS 무의존 순수 모듈 — 프레임 바이트열만 다루며 I/O·스케일 변환은 호출자 소관.
// 근거: [PGV Manual DOCT-3707D 2019-03, §5.1, pages 37-47]
//       (References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf — 로컬 보관)
#ifndef PGV_DRIVER__PGV_PROTOCOL_HPP_
#define PGV_DRIVER__PGV_PROTOCOL_HPP_

#include <array>
#include <cstddef>
#include <cstdint>

namespace pgv_protocol
{

// 응답 프레임 길이 (매뉴얼 §5.1.2 / §5.1.3 / §5.1.4)
constexpr std::size_t kPositionResponseLen = 21;
constexpr std::size_t kDirectionResponseLen = 3;
constexpr std::size_t kColorResponseLen = 2;
constexpr std::size_t kRequestLen = 2;
constexpr std::uint8_t kMaxAddress = 3;  // A1·A0 2비트

// 방향 결정 — 값 = 응답 byte 2 의 (LL << 1 | RL) 비트 배치 (Table 5.6)
enum class Direction : std::uint8_t
{
    kNone = 0,      // 선택 해제 → 장치는 error code 5
    kRight = 1,     // RL
    kLeft = 2,      // LL
    kStraight = 3,  // LL+RL
};

// 색 선택 — 값 = 응답 바이트의 (R << 2 | G << 1 | B) 비트 배치 (§5.1.4)
enum class Color : std::uint8_t
{
    kBlue = 1,
    kGreen = 2,
    kRed = 4,
};

enum class ParseResult
{
    kOk,
    kBadLength,    // 기대 길이와 다름
    kBadFraming,   // 응답 바이트의 bit7 은 항상 0 이어야 함 (Table 5.1)
    kBadChecksum,  // XOR(직전 바이트들) 불일치 / 색 응답의 반복 바이트 불일치
};

// 위치 응답 21바이트의 원시 필드 (스케일 미적용)
struct PositionFrame
{
    std::uint8_t address;  // A1·A0

    // byte 1 플래그
    bool cc1;
    bool cc2;
    bool warning;
    bool no_position;
    bool error;

    // byte 2 플래그
    bool tag_detected;
    std::uint8_t lane_count;  // 0..3 (3 = 3개 이상)
    bool repair_tape;
    bool no_lane;
    bool lane_left;   // LL
    bool lane_right;  // RL

    // 위치 — 레인 추적: x 무부호 / 태그 위: x 부호확장 (§5.1.2 Note "Sign")
    std::int32_t x;            // error 시 무효 (error_code 참조)
    std::uint32_t error_code;  // error 시 XP 필드에 실린 코드 (Table 5.4)
    std::int32_t y;            // YPS 14bit 부호확장
    std::uint16_t angle;       // ANG 14bit 무부호

    // 레인 모드 (tag_detected == false)
    std::uint16_t control_code1;  // 001..999
    std::uint16_t control_code2;
    std::uint8_t orientation1;  // 0..3 = 0/90/180/270° 시계방향 (§5.1.2.2)
    std::uint8_t orientation2;
    std::uint8_t side1;  // 0=없음 1=우측 2=좌측 3=판별불가 (§5.1.2.3)
    std::uint8_t side2;

    // 태그 모드 (tag_detected == true)
    std::uint32_t tag_number;  // TAG_00..27 (28bit)

    std::uint16_t warning_bits;  // WRN00..13 (Table 5.5)
};

std::uint8_t xorChecksum(const std::uint8_t *buf, std::size_t n);

// 요청 텔레그램 2바이트 — byte 2 = ~byte 1 (§5.1.1). addr 은 0..3 (초과분은 하위 2비트만 사용).
std::array<std::uint8_t, 2> makePositionRequest(std::uint8_t addr);
std::array<std::uint8_t, 2> makeDirectionRequest(Direction dir, std::uint8_t addr);
std::array<std::uint8_t, 2> makeColorRequest(Color color, std::uint8_t addr);

ParseResult parsePositionResponse(const std::uint8_t *buf, std::size_t len, PositionFrame &out);
// dir_bits = (LL << 1 | RL) — Direction 값과 동일 배치
ParseResult parseDirectionResponse(const std::uint8_t *buf, std::size_t len, std::uint8_t &dir_bits);
// color_bits = (R << 2 | G << 1 | B) — Color 값과 동일 배치
ParseResult parseColorResponse(const std::uint8_t *buf, std::size_t len, std::uint8_t &color_bits);

}  // namespace pgv_protocol

#endif  // PGV_DRIVER__PGV_PROTOCOL_HPP_
