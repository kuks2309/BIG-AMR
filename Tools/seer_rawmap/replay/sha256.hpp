// sha256 — FIPS 180-4 SHA-256, 헤더 온리, 표준 라이브러리만.
//
// 왜 자체 구현인가: 점군 파일의 지문을 **원본 구동 오라클과 우리 재생본이 똑같은 방식으로** 내야 한다.
//   OpenSSL 을 쓰면 두 도구가 서로 다른 라이브러리 버전에 묶이고, 이 저장소의 비-ROS 도구는
//   `python3` 즉시 실행 / 표준 도구만으로 돌아가는 게 규약이다.
//   출력은 `sha256sum(1)` 과 바이트 단위로 같다 — README 의 검증 절차로 대조한다.
#ifndef SEER_RAWMAP_REPLAY_SHA256_HPP
#define SEER_RAWMAP_REPLAY_SHA256_HPP

#include <cstddef>
#include <cstdint>
#include <string>

namespace sha256
{

/// 스트리밍 해시 계산기. `update()` 를 여러 번 부른 뒤 `hexDigest()` 로 마무리한다.
class Hasher
{
  public:
    /// 다이제스트 길이 (바이트). SHA-256 = 256 bit.
    static constexpr std::size_t kDigestBytes = 32;
    /// 압축 블록 길이 (바이트).
    static constexpr std::size_t kBlockBytes = 64;

    /// 바이트열을 해시에 더한다.
    ///
    /// @param data 입력 버퍼 시작 주소 (널이면 `len` 은 0 이어야 한다).
    /// @param len  입력 길이 (바이트).
    void update(const void *data, std::size_t len)
    {
        const auto *p = static_cast<const std::uint8_t *>(data);
        total_bits_ += static_cast<std::uint64_t>(len) * 8u;
        while (len > 0)
        {
            const std::size_t room = kBlockBytes - buffer_len_;
            const std::size_t take = len < room ? len : room;
            for (std::size_t i = 0; i < take; ++i)
            {
                buffer_[buffer_len_ + i] = p[i];
            }
            buffer_len_ += take;
            p += take;
            len -= take;
            if (buffer_len_ == kBlockBytes)
            {
                compress(buffer_);
                buffer_len_ = 0;
            }
        }
    }

    /// 문자열을 해시에 더한다(널 종단 문자는 포함하지 않는다).
    void update(const std::string &s)
    {
        update(s.data(), s.size());
    }

    /// 패딩을 붙여 마무리하고 소문자 16진 64자 다이제스트를 돌려준다.
    /// 호출 후 이 객체를 다시 쓰지 말 것(상태가 종료된다).
    std::string hexDigest()
    {
        const std::uint64_t bits = total_bits_;
        const std::uint8_t one = 0x80u;
        update(&one, 1);
        const std::uint8_t zero = 0x00u;
        // 길이 8바이트가 들어갈 자리(56 mod 64)까지 0 으로 채운다.
        while (buffer_len_ != kBlockBytes - sizeof(std::uint64_t))
        {
            update(&zero, 1);
        }
        std::uint8_t len_be[sizeof(std::uint64_t)];
        for (int i = 0; i < 8; ++i)
        {
            len_be[i] = static_cast<std::uint8_t>((bits >> (56 - 8 * i)) & 0xFFu);
        }
        // 길이 필드 자체는 비트 수에 더하면 안 되므로 compress 를 직접 부른다.
        for (std::size_t i = 0; i < sizeof(len_be); ++i)
        {
            buffer_[buffer_len_ + i] = len_be[i];
        }
        compress(buffer_);
        buffer_len_ = 0;

        static const char kHex[] = "0123456789abcdef";
        std::string out;
        out.reserve(kDigestBytes * 2);
        for (int i = 0; i < 8; ++i)
        {
            for (int b = 3; b >= 0; --b)
            {
                const std::uint8_t byte =
                    static_cast<std::uint8_t>((state_[i] >> (8 * b)) & 0xFFu);
                out.push_back(kHex[byte >> 4]);
                out.push_back(kHex[byte & 0x0Fu]);
            }
        }
        return out;
    }

  private:
    static std::uint32_t rotr(std::uint32_t x, int n)
    {
        return (x >> n) | (x << (32 - n));
    }

    void compress(const std::uint8_t block[kBlockBytes])
    {
        static const std::uint32_t k[64] = {
            0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u,
            0x923f82a4u, 0xab1c5ed5u, 0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
            0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u, 0xe49b69c1u, 0xefbe4786u,
            0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
            0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u,
            0x06ca6351u, 0x14292967u, 0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
            0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u, 0xa2bfe8a1u, 0xa81a664bu,
            0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
            0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au,
            0x5b9cca4fu, 0x682e6ff3u, 0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
            0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};

        std::uint32_t w[64];
        for (int i = 0; i < 16; ++i)
        {
            w[i] = (static_cast<std::uint32_t>(block[4 * i]) << 24) |
                   (static_cast<std::uint32_t>(block[4 * i + 1]) << 16) |
                   (static_cast<std::uint32_t>(block[4 * i + 2]) << 8) |
                   static_cast<std::uint32_t>(block[4 * i + 3]);
        }
        for (int i = 16; i < 64; ++i)
        {
            const std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            const std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }

        std::uint32_t a = state_[0];
        std::uint32_t b = state_[1];
        std::uint32_t c = state_[2];
        std::uint32_t d = state_[3];
        std::uint32_t e = state_[4];
        std::uint32_t f = state_[5];
        std::uint32_t g = state_[6];
        std::uint32_t h = state_[7];

        for (int i = 0; i < 64; ++i)
        {
            const std::uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            const std::uint32_t ch = (e & f) ^ ((~e) & g);
            const std::uint32_t temp1 = h + S1 + ch + k[i] + w[i];
            const std::uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            const std::uint32_t temp2 = S0 + maj;
            h = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }

        state_[0] += a;
        state_[1] += b;
        state_[2] += c;
        state_[3] += d;
        state_[4] += e;
        state_[5] += f;
        state_[6] += g;
        state_[7] += h;
    }

    std::uint32_t state_[8] = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
                               0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};
    std::uint8_t buffer_[kBlockBytes] = {};
    std::size_t buffer_len_ = 0;
    std::uint64_t total_bits_ = 0;
};

/// 문자열 전체의 SHA-256 16진 다이제스트 (편의 함수).
inline std::string hex(const std::string &data)
{
    Hasher h;
    h.update(data);
    return h.hexDigest();
}

} // namespace sha256

#endif // SEER_RAWMAP_REPLAY_SHA256_HPP
