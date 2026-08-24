#include "pgv_driver/pgv_protocol.hpp"

namespace pgv_protocol
{

namespace
{

// N비트 값 부호확장 — 매뉴얼 §5.1.2 Note "fill in the missing upper bits with the
// highest bit of the response telegram"
std::int32_t signExtend(std::uint32_t v, unsigned bits)
{
    const std::uint32_t sign = 1u << (bits - 1);
    return static_cast<std::int32_t>((v ^ sign) - sign);
}

// 응답 바이트는 하위 7비트만 데이터 (bit7 = 0). 두 바이트 → 14bit.
std::uint32_t bits14(std::uint8_t hi, std::uint8_t lo)
{
    return (static_cast<std::uint32_t>(hi & 0x7F) << 7) | (lo & 0x7F);
}

}  // namespace

std::uint8_t xorChecksum(const std::uint8_t *buf, std::size_t n)
{
    std::uint8_t x = 0;
    for (std::size_t i = 0; i < n; ++i)
    {
        x ^= buf[i];
    }
    return x;
}

std::array<std::uint8_t, 2> makePositionRequest(std::uint8_t addr)
{
    // 위치 조회: R/W=1, Req bit4..0 = 10010 → addr0 에서 0xC8 0x37 (§5.1.1)
    const std::uint8_t b = 0xC8 | (addr & kMaxAddress);
    return {b, static_cast<std::uint8_t>(~b)};
}

std::array<std::uint8_t, 2> makeDirectionRequest(Direction dir, std::uint8_t addr)
{
    // 방향 결정: 상위 111, bit3=LL, bit2=RL (§5.1.3) — 직진 0xEC / 좌 0xE8 / 우 0xE4 / 해제 0xE0
    const auto d = static_cast<std::uint8_t>(dir);
    const std::uint8_t ll = (d >> 1) & 1u;
    const std::uint8_t rl = d & 1u;
    const std::uint8_t b =
        static_cast<std::uint8_t>(0xE0 | (ll << 3) | (rl << 2) | (addr & kMaxAddress));
    return {b, static_cast<std::uint8_t>(~b)};
}

std::array<std::uint8_t, 2> makeColorRequest(Color color, std::uint8_t addr)
{
    // 색 선택 (§5.1.4): bit4=R, bit3=G, bit2=B. 청색만 bit6=1 —
    // 매뉴얼 예제 (청 0xC4 / 녹 0x88 / 적 0x90, addr0) 와 일치.
    const auto c = static_cast<std::uint8_t>(color);
    const std::uint8_t r = (c >> 2) & 1u;
    const std::uint8_t g = (c >> 1) & 1u;
    const std::uint8_t bl = c & 1u;
    const std::uint8_t b = static_cast<std::uint8_t>(
        0x80 | (bl ? 0x40 : 0x00) | (r << 4) | (g << 3) | (bl << 2) | (addr & kMaxAddress));
    return {b, static_cast<std::uint8_t>(~b)};
}

ParseResult parsePositionResponse(const std::uint8_t *buf, std::size_t len, PositionFrame &out)
{
    if (len != kPositionResponseLen)
    {
        return ParseResult::kBadLength;
    }
    for (std::size_t i = 0; i < kPositionResponseLen; ++i)
    {
        if (buf[i] & 0x80)
        {
            return ParseResult::kBadFraming;
        }
    }
    if (xorChecksum(buf, kPositionResponseLen - 1) != buf[kPositionResponseLen - 1])
    {
        return ParseResult::kBadChecksum;
    }

    // Byte 1: CC2 A1 A0 CC1 WRN NP ERR (Table 5.1)
    out.cc2 = (buf[0] >> 6) & 1u;
    out.address = (buf[0] >> 4) & 0x03;
    out.cc1 = (buf[0] >> 3) & 1u;
    out.warning = (buf[0] >> 2) & 1u;
    out.no_position = (buf[0] >> 1) & 1u;
    out.error = buf[0] & 1u;

    // Byte 2: TAG LC1 LC0 RP NL LL RL
    out.tag_detected = (buf[1] >> 6) & 1u;
    out.lane_count = (buf[1] >> 4) & 0x03;
    out.repair_tape = (buf[1] >> 3) & 1u;
    out.no_lane = (buf[1] >> 2) & 1u;
    out.lane_left = (buf[1] >> 1) & 1u;
    out.lane_right = buf[1] & 1u;

    // X: bytes 3..6 → 24bit. 레인 추적 무부호 / 태그 위 부호 있음 (Note "Sign").
    const std::uint32_t x_raw = (static_cast<std::uint32_t>(buf[2] & 0x07) << 21) |
                                (static_cast<std::uint32_t>(buf[3] & 0x7F) << 14) |
                                (static_cast<std::uint32_t>(buf[4] & 0x7F) << 7) | (buf[5] & 0x7F);
    out.error_code = out.error ? x_raw : 0;  // ERR 시 XP 필드가 오류 코드 (Table 5.3)
    out.x = out.tag_detected ? signExtend(x_raw, 24) : static_cast<std::int32_t>(x_raw);

    // Y: bytes 7..8 → 14bit 부호 있음
    out.y = signExtend(bits14(buf[6], buf[7]), 14);

    // ANG: bytes 11..12 → 14bit 무부호
    out.angle = static_cast<std::uint16_t>(bits14(buf[10], buf[11]));

    // Bytes 15..18 — 태그 모드: TAG_27..00 / 레인 모드: O·S·CC 2조 (Tables 5.1/5.2)
    if (out.tag_detected)
    {
        out.tag_number = (static_cast<std::uint32_t>(buf[14] & 0x7F) << 21) |
                         (static_cast<std::uint32_t>(buf[15] & 0x7F) << 14) |
                         (static_cast<std::uint32_t>(buf[16] & 0x7F) << 7) | (buf[17] & 0x7F);
        out.control_code1 = 0;
        out.control_code2 = 0;
        out.orientation1 = 0;
        out.orientation2 = 0;
        out.side1 = 0;
        out.side2 = 0;
    }
    else
    {
        out.tag_number = 0;
        out.orientation1 = (buf[14] >> 5) & 0x03;
        out.side1 = (buf[14] >> 3) & 0x03;
        out.control_code1 =
            static_cast<std::uint16_t>((static_cast<std::uint16_t>(buf[14] & 0x07) << 7) |
                                       (buf[15] & 0x7F));
        out.orientation2 = (buf[16] >> 5) & 0x03;
        out.side2 = (buf[16] >> 3) & 0x03;
        out.control_code2 =
            static_cast<std::uint16_t>((static_cast<std::uint16_t>(buf[16] & 0x07) << 7) |
                                       (buf[17] & 0x7F));
    }

    // WRN: bytes 19..20 → 14bit
    out.warning_bits = static_cast<std::uint16_t>(bits14(buf[18], buf[19]));

    return ParseResult::kOk;
}

ParseResult parseDirectionResponse(const std::uint8_t *buf, std::size_t len, std::uint8_t &dir_bits)
{
    if (len != kDirectionResponseLen)
    {
        return ParseResult::kBadLength;
    }
    for (std::size_t i = 0; i < kDirectionResponseLen; ++i)
    {
        if (buf[i] & 0x80)
        {
            return ParseResult::kBadFraming;
        }
    }
    if (xorChecksum(buf, kDirectionResponseLen - 1) != buf[kDirectionResponseLen - 1])
    {
        return ParseResult::kBadChecksum;
    }
    dir_bits = buf[1] & 0x03;  // byte 2 bit1..0 = LL RL (§5.1.3)
    return ParseResult::kOk;
}

ParseResult parseColorResponse(const std::uint8_t *buf, std::size_t len, std::uint8_t &color_bits)
{
    if (len != kColorResponseLen)
    {
        return ParseResult::kBadLength;
    }
    if ((buf[0] & 0x80) || (buf[1] & 0x80))
    {
        return ParseResult::kBadFraming;
    }
    if (buf[0] != buf[1])  // 응답은 동일 바이트 2회 (§5.1.4)
    {
        return ParseResult::kBadChecksum;
    }
    color_bits = buf[0] & 0x07;  // bit2..0 = R G B
    return ParseResult::kOk;
}

}  // namespace pgv_protocol
