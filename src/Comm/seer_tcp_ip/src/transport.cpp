#include "seer_tcp_ip/transport.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <thread>

namespace seer_tcp_ip
{
namespace
{

void putU16(std::vector<char> &out, std::uint16_t v)
{
    out.push_back(static_cast<char>((v >> 8) & 0xFF));
    out.push_back(static_cast<char>(v & 0xFF));
}

void putU32(std::vector<char> &out, std::uint32_t v)
{
    out.push_back(static_cast<char>((v >> 24) & 0xFF));
    out.push_back(static_cast<char>((v >> 16) & 0xFF));
    out.push_back(static_cast<char>((v >> 8) & 0xFF));
    out.push_back(static_cast<char>(v & 0xFF));
}

std::uint16_t getU16(const char *p)
{
    return static_cast<std::uint16_t>((static_cast<unsigned char>(p[0]) << 8) |
                                      static_cast<unsigned char>(p[1]));
}

std::uint32_t getU32(const char *p)
{
    return (static_cast<std::uint32_t>(static_cast<unsigned char>(p[0])) << 24) |
           (static_cast<std::uint32_t>(static_cast<unsigned char>(p[1])) << 16) |
           (static_cast<std::uint32_t>(static_cast<unsigned char>(p[2])) << 8) |
           static_cast<std::uint32_t>(static_cast<unsigned char>(p[3]));
}

/// POSIX 소켓 구현.
class TcpStream : public IByteStream
{
  public:
    ~TcpStream() override { close(); }

    void connect(const std::string &ip, std::uint16_t port, double timeoutSec) override
    {
        close();
        fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (fd_ < 0)
        {
            throw TransportError(std::string("socket() 실패: ") + std::strerror(errno));
        }
        timeval tv{};
        tv.tv_sec = static_cast<time_t>(timeoutSec);
        tv.tv_usec = static_cast<suseconds_t>((timeoutSec - tv.tv_sec) * 1e6);
        ::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        ::setsockopt(fd_, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        if (::inet_pton(AF_INET, ip.c_str(), &addr.sin_addr) != 1)
        {
            close();
            throw TransportError("IP 형식 오류: " + ip);
        }
        if (::connect(fd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0)
        {
            const std::string why = std::strerror(errno);
            close();
            throw TransportError("connect " + ip + ":" + std::to_string(port) + " 실패: " + why);
        }
    }

    std::size_t read(char *buf, std::size_t n) override
    {
        const ssize_t got = ::recv(fd_, buf, n, 0);
        if (got < 0)
        {
            throw TransportError(std::string("recv 실패: ") + std::strerror(errno));
        }
        return static_cast<std::size_t>(got);
    }

    void writeAll(const char *buf, std::size_t n) override
    {
        std::size_t sent = 0;
        while (sent < n)
        {
            const ssize_t k = ::send(fd_, buf + sent, n - sent, MSG_NOSIGNAL);
            if (k <= 0)
            {
                throw TransportError(std::string("send 실패: ") + std::strerror(errno));
            }
            sent += static_cast<std::size_t>(k);
        }
    }

    void close() override
    {
        if (fd_ >= 0)
        {
            ::close(fd_);
            fd_ = -1;
        }
    }

    bool isOpen() const override { return fd_ >= 0; }

  private:
    int fd_ = -1;
};

}  // namespace

std::unique_ptr<IByteStream> makeTcpStream()
{
    return std::unique_ptr<IByteStream>(new TcpStream());
}

std::vector<char> pack(std::uint16_t seq, std::uint16_t apiType, const Json &msg)
{
    std::string body;
    // 빈 객체는 본문을 붙이지 않는다 — 공식 packMsg 와 바이트 동일해야 한다.
    if (!(msg.is_null() || (msg.is_object() && msg.empty())))
    {
        body = msg.dump();
    }
    std::vector<char> out;
    out.reserve(kHeadLen + body.size());
    out.push_back(static_cast<char>(kSync));
    out.push_back(static_cast<char>(kVersion));
    putU16(out, seq);
    putU32(out, static_cast<std::uint32_t>(body.size()));
    putU16(out, apiType);
    for (int i = 0; i < 6; ++i)
    {
        out.push_back(0);
    }
    out.insert(out.end(), body.begin(), body.end());
    return out;
}

std::vector<char> pack(std::uint16_t seq, std::uint16_t apiType)
{
    return pack(seq, apiType, Json::object());
}

Head unpackHead(const char *data, std::size_t len)
{
    if (len != kHeadLen)
    {
        throw ProtocolError("헤더 길이 " + std::to_string(len) + "B (기대 " +
                            std::to_string(kHeadLen) + "B)");
    }
    const auto sync = static_cast<unsigned char>(data[0]);
    if (sync != kSync)
    {
        char buf[64];
        std::snprintf(buf, sizeof(buf), "sync 불일치 0x%02X (기대 0x%02X)", sync, kSync);
        throw ProtocolError(buf);
    }
    Head h;
    h.seq = getU16(data + 2);
    h.jsonLen = getU32(data + 4);
    h.apiType = getU16(data + 8);
    return h;
}

Transport::Transport(std::string ip, std::uint16_t port, double timeoutSec, int minIntervalMs,
                     StreamFactory factory, ClockMs clock, SleepMs sleep)
    : ip_(std::move(ip)), port_(port), timeoutSec_(timeoutSec), minIntervalMs_(minIntervalMs),
      factory_(factory ? std::move(factory) : StreamFactory(&makeTcpStream)),
      clock_(clock ? std::move(clock)
                   : ClockMs([] {
                         return std::chrono::duration_cast<std::chrono::milliseconds>(
                                    std::chrono::steady_clock::now().time_since_epoch())
                             .count();
                     })),
      sleep_(sleep ? std::move(sleep)
                   : SleepMs([](std::int64_t ms) {
                         std::this_thread::sleep_for(std::chrono::milliseconds(ms));
                     }))
{
}

void Transport::connect()
{
    if (stream_)
    {
        return;
    }
    // 연결에 실패하면 stream_ 을 남기지 않는다. 남기면 다음 요청이 「이미 연결됨」으로 보고
    // 죽은 서술자에 send 를 걸어 `Bad file descriptor` 로 한 번 더 헛돈다.
    auto fresh = factory_();
    fresh->connect(ip_, port_, timeoutSec_);
    stream_ = std::move(fresh);
}

void Transport::close()
{
    if (stream_)
    {
        stream_->close();
        stream_.reset();
    }
}

bool Transport::isConnected() const
{
    return stream_ != nullptr;
}

void Transport::throttle()
{
    if (minIntervalMs_ <= 0 || lastRequestAt_ < 0)
    {
        return;
    }
    const std::int64_t wait = minIntervalMs_ - (clock_() - lastRequestAt_);
    if (wait > 0)
    {
        sleep_(wait);
    }
}

void Transport::recvExact(char *buf, std::size_t n)
{
    std::size_t got = 0;
    while (got < n)
    {
        const std::size_t k = stream_->read(buf + got, n - got);
        if (k == 0)
        {
            throw TransportError("수신 중 연결 종료 (" + std::to_string(got) + "/" +
                                 std::to_string(n) + "B)");
        }
        got += k;
    }
}

void Transport::raiseConnectionLimitIfThat(std::uint16_t respType, const std::vector<char> &body)
{
    // 서명: 편호가 포트 번호로 오고 본문 ret_code 가 61001.
    if (respType != port_ || body.empty())
    {
        return;
    }
    const Json obj = Json::parse(std::string(body.begin(), body.end()), nullptr, false);
    if (obj.is_discarded() || !obj.is_object())
    {
        return;
    }
    if (obj.value("ret_code", 0) != ports::kConnectionLimitRetCode)
    {
        return;
    }
    const auto it = ports::maxConnectionParam().find(port_);
    throw ConnectionLimitError(
        "포트 " + std::to_string(port_) + " 동시연결 한도 초과 (ret_code=" +
        std::to_string(ports::kConnectionLimitRetCode) + "): " +
        obj.value("err_msg", std::string()) + " — 기존 연결은 유지된다(거부형). 한도는 API 1400 `" +
        (it == ports::maxConnectionParam().end() ? std::string("?") : it->second) + "` 로 조회한다.");
}

std::pair<std::vector<char>, std::uint16_t> Transport::doRequest(std::uint16_t apiType,
                                                                 const Json *msg,
                                                                 std::uint16_t expectType)
{
    throttle();
    connect();
    seq_ = static_cast<std::uint16_t>(seq_ == 65535 ? 1 : seq_ + 1);
    const std::uint16_t seq = seq_;

    std::vector<char> body;
    std::uint16_t respType = 0;
    std::uint16_t respSeq = 0;
    try
    {
        const std::vector<char> frame = msg ? pack(seq, apiType, *msg) : pack(seq, apiType);
        stream_->writeAll(frame.data(), frame.size());
        char head[kHeadLen];
        recvExact(head, kHeadLen);
        const Head h = unpackHead(head, kHeadLen);
        respType = h.apiType;
        respSeq = h.seq;
        if (h.jsonLen > 0)
        {
            body.resize(h.jsonLen);
            recvExact(body.data(), body.size());
        }
    }
    catch (const TransportError &)
    {
        close();  // 끊긴 소켓을 남기지 않는다 — 다음 요청이 재연결한다
        lastRequestAt_ = clock_();
        throw;
    }
    lastRequestAt_ = clock_();

    const std::uint16_t want =
        expectType != 0 ? expectType
                        : static_cast<std::uint16_t>(apiType + ports::kResponseTypeOffset);
    if (respType != want)
    {
        raiseConnectionLimitIfThat(respType, body);
        throw ProtocolError("응답 편호 " + std::to_string(respType) + " (기대 " +
                            std::to_string(want) + ", 요청 " + std::to_string(apiType) + ")");
    }
    if (respSeq != seq)
    {
        throw ProtocolError("응답 seq " + std::to_string(respSeq) + " (기대 " +
                            std::to_string(seq) + ") — 응답 어긋남");
    }
    return {body, respType};
}

std::pair<std::vector<char>, std::uint16_t> Transport::requestRaw(std::uint16_t apiType,
                                                                  const Json &msg,
                                                                  std::uint16_t expectType)
{
    return doRequest(apiType, &msg, expectType);
}

Json Transport::request(std::uint16_t apiType, const Json &msg, std::uint16_t expectType)
{
    const auto [body, respType] = doRequest(apiType, &msg, expectType);
    const std::string text = body.empty() ? "{}" : std::string(body.begin(), body.end());
    const Json obj = Json::parse(text, nullptr, false);
    if (obj.is_discarded())
    {
        throw ProtocolError("응답 " + std::to_string(respType) + " JSON 파싱 실패");
    }
    return obj;
}

Json Transport::request(std::uint16_t apiType, std::uint16_t expectType)
{
    const auto [body, respType] = doRequest(apiType, nullptr, expectType);
    const std::string text = body.empty() ? "{}" : std::string(body.begin(), body.end());
    const Json obj = Json::parse(text, nullptr, false);
    if (obj.is_discarded())
    {
        throw ProtocolError("응답 " + std::to_string(respType) + " JSON 파싱 실패");
    }
    return obj;
}

}  // namespace seer_tcp_ip
