// 시험용 바이트 스트림 대역 — 소켓 없이 전 계층을 지나가게 한다.
#ifndef SEER_TCP_IP_TEST_FAKE_STREAM_HPP_
#define SEER_TCP_IP_TEST_FAKE_STREAM_HPP_

#include <cstring>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "seer_tcp_ip/transport.hpp"

namespace fake
{

/// 프로그램된 바이트를 조금씩 흘려주는 스트림.
/// read 를 작은 조각으로 쪼개 돌려주어 부분 수신 경로를 반드시 지나게 한다.
class Stream : public seer_tcp_ip::IByteStream
{
  public:
    std::string response;                 ///< 다음에 흘려보낼 바이트
    std::size_t chunk = 3;                ///< 한 번에 내주는 최대 바이트
    std::vector<char> sent;               ///< 보낸 바이트 누적
    bool closed = false;
    bool opened = false;
    std::string connectedIp;
    std::uint16_t connectedPort = 0;
    /// 프레임을 보낼 때마다 불린다 — 응답을 seq 에 맞춰 만들 때 쓴다.
    std::function<void(Stream &, const std::vector<char> &)> onWrite;

    void connect(const std::string &ip, std::uint16_t port, double) override
    {
        connectedIp = ip;
        connectedPort = port;
        opened = true;
        closed = false;
    }

    std::size_t read(char *buf, std::size_t n) override
    {
        const std::size_t left = response.size() - pos_;
        const std::size_t take = std::min({n, chunk, left});
        if (take == 0)
        {
            return 0;
        }
        std::memcpy(buf, response.data() + pos_, take);
        pos_ += take;
        return take;
    }

    void writeAll(const char *buf, std::size_t n) override
    {
        sent.insert(sent.end(), buf, buf + n);
        if (onWrite)
        {
            onWrite(*this, std::vector<char>(buf, buf + n));
        }
    }

    void close() override
    {
        closed = true;
        opened = false;
    }

    bool isOpen() const override { return opened; }

    void reset(const std::string &body)
    {
        response = body;
        pos_ = 0;
    }

  private:
    std::size_t pos_ = 0;
};

/// Transport 가 소유권을 갖되 실체는 공유하도록 감싼다.
class Wrapper : public seer_tcp_ip::IByteStream
{
  public:
    explicit Wrapper(Stream *s) : s_(s) {}
    void connect(const std::string &ip, std::uint16_t port, double t) override
    {
        s_->connect(ip, port, t);
    }
    std::size_t read(char *b, std::size_t n) override { return s_->read(b, n); }
    void writeAll(const char *b, std::size_t n) override { s_->writeAll(b, n); }
    void close() override { s_->close(); }
    bool isOpen() const override { return s_->isOpen(); }

  private:
    Stream *s_;
};

/// 같은 Stream 을 계속 돌려주는 팩토리 (포트 하나짜리 시험용).
inline seer_tcp_ip::StreamFactory factoryFor(Stream *s)
{
    return [s] {
        return std::unique_ptr<seer_tcp_ip::IByteStream>(new Wrapper(s));
    };
}

/// 응답 프레임을 만든다(16B 헤더 + 본문).
inline std::string makeResponse(std::uint16_t seq, std::uint16_t apiType,
                                const std::string &jsonBody,
                                std::uint8_t sync = seer_tcp_ip::kSync)
{
    std::string out;
    out.push_back(static_cast<char>(sync));
    out.push_back(static_cast<char>(seer_tcp_ip::kVersion));
    out.push_back(static_cast<char>((seq >> 8) & 0xFF));
    out.push_back(static_cast<char>(seq & 0xFF));
    const std::uint32_t n = static_cast<std::uint32_t>(jsonBody.size());
    out.push_back(static_cast<char>((n >> 24) & 0xFF));
    out.push_back(static_cast<char>((n >> 16) & 0xFF));
    out.push_back(static_cast<char>((n >> 8) & 0xFF));
    out.push_back(static_cast<char>(n & 0xFF));
    out.push_back(static_cast<char>((apiType >> 8) & 0xFF));
    out.push_back(static_cast<char>(apiType & 0xFF));
    out.append(6, '\0');
    out += jsonBody;
    return out;
}

}  // namespace fake

#endif  // SEER_TCP_IP_TEST_FAKE_STREAM_HPP_
