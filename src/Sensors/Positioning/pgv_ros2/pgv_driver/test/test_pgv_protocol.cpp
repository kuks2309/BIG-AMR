// pgv_protocol 단위 테스트 — 검증 벡터는 매뉴얼 DOCT-3707D 의 예제·비트표에서 도출
// (§5.1.1 요청, §5.1.2 위치 응답, §5.1.3 방향 예제, §5.1.4 색 예제).
#include <gtest/gtest.h>

#include <array>
#include <cstdint>

#include "pgv_driver/pgv_protocol.hpp"

using namespace pgv_protocol;

namespace
{

// 위치 응답 21바이트 프레임 조립 도우미 — 각 바이트는 하위 7비트만 사용,
// 마지막 바이트는 앞 20바이트의 XOR (Table 5.1).
struct FrameBuilder
{
    std::array<std::uint8_t, kPositionResponseLen> buf{};

    FrameBuilder &set(std::size_t idx, std::uint8_t v)
    {
        buf[idx] = static_cast<std::uint8_t>(v & 0x7F);
        return *this;
    }

    FrameBuilder &setX(std::uint32_t x24)
    {
        set(2, (x24 >> 21) & 0x07);
        set(3, (x24 >> 14) & 0x7F);
        set(4, (x24 >> 7) & 0x7F);
        set(5, x24 & 0x7F);
        return *this;
    }

    FrameBuilder &setY(std::uint32_t y14)
    {
        set(6, (y14 >> 7) & 0x7F);
        set(7, y14 & 0x7F);
        return *this;
    }

    FrameBuilder &setAngle(std::uint32_t a14)
    {
        set(10, (a14 >> 7) & 0x7F);
        set(11, a14 & 0x7F);
        return *this;
    }

    const std::array<std::uint8_t, kPositionResponseLen> &seal()
    {
        buf[20] = xorChecksum(buf.data(), 20);
        return buf;
    }
};

}  // namespace

// --- 요청 텔레그램: 매뉴얼 예제 값과 비트 대조 ---

TEST(Request, PositionAddr0MatchesManualExample)
{
    const auto t = makePositionRequest(0);  // §5.1.1
    EXPECT_EQ(t[0], 0xC8);
    EXPECT_EQ(t[1], 0x37);
}

TEST(Request, PositionAddressInLowBits)
{
    for (std::uint8_t a = 0; a <= kMaxAddress; ++a)
    {
        const auto t = makePositionRequest(a);
        EXPECT_EQ(t[0], 0xC8 | a);
        EXPECT_EQ(t[1], static_cast<std::uint8_t>(~t[0]));
    }
}

TEST(Request, DirectionMatchesManualExamples)
{
    // §5.1.3 예제 (addr 0): 좌 0xE8 0x17 / 우 0xE4 0x1B / 직진 0xEC 0x13 / 해제 0xE0 0x1F
    EXPECT_EQ(makeDirectionRequest(Direction::kLeft, 0), (std::array<std::uint8_t, 2>{0xE8, 0x17}));
    EXPECT_EQ(makeDirectionRequest(Direction::kRight, 0),
              (std::array<std::uint8_t, 2>{0xE4, 0x1B}));
    EXPECT_EQ(makeDirectionRequest(Direction::kStraight, 0),
              (std::array<std::uint8_t, 2>{0xEC, 0x13}));
    EXPECT_EQ(makeDirectionRequest(Direction::kNone, 0), (std::array<std::uint8_t, 2>{0xE0, 0x1F}));
}

TEST(Request, ColorMatchesManualExamples)
{
    // §5.1.4 예제 (addr 0): 청 0xC4 0x3B / 녹 0x88 0x77 / 적 0x90 0x6F
    EXPECT_EQ(makeColorRequest(Color::kBlue, 0), (std::array<std::uint8_t, 2>{0xC4, 0x3B}));
    EXPECT_EQ(makeColorRequest(Color::kGreen, 0), (std::array<std::uint8_t, 2>{0x88, 0x77}));
    EXPECT_EQ(makeColorRequest(Color::kRed, 0), (std::array<std::uint8_t, 2>{0x90, 0x6F}));
}

// --- 위치 응답 파싱 ---

TEST(PositionResponse, LaneModeFields)
{
    FrameBuilder fb;
    // byte1: CC1=1, addr=2 → bit3 | (2<<4)
    fb.set(0, (2u << 4) | (1u << 3));
    // byte2: LC=1, LL=1 (레인 모드: TAG=0)
    fb.set(1, (1u << 4) | (1u << 1));
    fb.setX(1000000);  // 0.1 mm 해상도에서 100 m
    fb.setY((-3) & 0x3FFF);
    fb.setAngle(3599);
    // byte15/16: O1=1, S1=2, CC1 번호 = 12
    fb.set(14, (1u << 5) | (2u << 3) | ((12u >> 7) & 0x07));
    fb.set(15, 12u & 0x7F);
    const auto &buf = fb.seal();

    PositionFrame f{};
    ASSERT_EQ(parsePositionResponse(buf.data(), buf.size(), f), ParseResult::kOk);
    EXPECT_EQ(f.address, 2);
    EXPECT_TRUE(f.cc1);
    EXPECT_FALSE(f.error);
    EXPECT_FALSE(f.tag_detected);
    EXPECT_EQ(f.lane_count, 1);
    EXPECT_TRUE(f.lane_left);
    EXPECT_FALSE(f.lane_right);
    EXPECT_EQ(f.x, 1000000);  // 레인 모드: 무부호 그대로
    EXPECT_EQ(f.y, -3);       // 14bit 부호확장
    EXPECT_EQ(f.angle, 3599);
    EXPECT_EQ(f.orientation1, 1);
    EXPECT_EQ(f.side1, 2);
    EXPECT_EQ(f.control_code1, 12);
    EXPECT_EQ(f.warning_bits, 0);
}

TEST(PositionResponse, TagModeSignedXAndTagNumber)
{
    FrameBuilder fb;
    fb.set(1, 1u << 6);              // TAG=1
    fb.setX((-50) & 0x00FFFFFF);     // 태그 모드: 24bit 부호 있음
    fb.setY(0);
    // TAG 번호 = 123456 (28bit, 7bit x 4)
    const std::uint32_t tag = 123456;
    fb.set(14, (tag >> 21) & 0x7F);
    fb.set(15, (tag >> 14) & 0x7F);
    fb.set(16, (tag >> 7) & 0x7F);
    fb.set(17, tag & 0x7F);
    const auto &buf = fb.seal();

    PositionFrame f{};
    ASSERT_EQ(parsePositionResponse(buf.data(), buf.size(), f), ParseResult::kOk);
    EXPECT_TRUE(f.tag_detected);
    EXPECT_EQ(f.x, -50);
    EXPECT_EQ(f.tag_number, tag);
    EXPECT_EQ(f.control_code1, 0);  // 태그 모드에서는 CC 필드 미사용
}

TEST(PositionResponse, ErrorCodeInXpField)
{
    FrameBuilder fb;
    fb.set(0, 1u);  // ERR=1
    fb.setX(5);     // Table 5.4: code 5 = 방향 결정 없음
    const auto &buf = fb.seal();

    PositionFrame f{};
    ASSERT_EQ(parsePositionResponse(buf.data(), buf.size(), f), ParseResult::kOk);
    EXPECT_TRUE(f.error);
    EXPECT_EQ(f.error_code, 5u);
}

TEST(PositionResponse, RejectsBadLengthFramingChecksum)
{
    FrameBuilder fb;
    fb.set(1, 1u << 4);  // LC=1
    auto buf = fb.seal();

    PositionFrame f{};
    EXPECT_EQ(parsePositionResponse(buf.data(), buf.size() - 1, f), ParseResult::kBadLength);

    auto corrupt_xor = buf;
    corrupt_xor[5] ^= 0x01;  // 데이터 변조 → XOR 불일치
    EXPECT_EQ(parsePositionResponse(corrupt_xor.data(), corrupt_xor.size(), f),
              ParseResult::kBadChecksum);

    auto corrupt_frame = buf;
    corrupt_frame[3] |= 0x80;  // 응답 바이트 bit7 은 항상 0
    EXPECT_EQ(parsePositionResponse(corrupt_frame.data(), corrupt_frame.size(), f),
              ParseResult::kBadFraming);
}

// --- 방향/색 응답 파싱 ---

TEST(DirectionResponse, ParsesLlRlBits)
{
    // §5.1.3 예제: 좌측 레인 응답 byte2 = 0x02
    std::array<std::uint8_t, kDirectionResponseLen> buf{0x00, 0x02, 0x00};
    buf[2] = xorChecksum(buf.data(), 2);

    std::uint8_t dir = 0xFF;
    ASSERT_EQ(parseDirectionResponse(buf.data(), buf.size(), dir), ParseResult::kOk);
    EXPECT_EQ(dir, 0x02);

    buf[2] ^= 0x01;
    EXPECT_EQ(parseDirectionResponse(buf.data(), buf.size(), dir), ParseResult::kBadChecksum);
}

TEST(ColorResponse, ParsesRepeatedByte)
{
    // §5.1.4 예제: 녹색 응답 0x02 0x02
    std::array<std::uint8_t, kColorResponseLen> buf{0x02, 0x02};
    std::uint8_t color = 0;
    ASSERT_EQ(parseColorResponse(buf.data(), buf.size(), color), ParseResult::kOk);
    EXPECT_EQ(color, 0x02);

    buf[1] = 0x04;  // 반복 바이트 불일치
    EXPECT_EQ(parseColorResponse(buf.data(), buf.size(), color), ParseResult::kBadChecksum);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
