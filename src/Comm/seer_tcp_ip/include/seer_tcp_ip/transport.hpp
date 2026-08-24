// Seer(SRC) Robokit NetProtocol 전송 계층 — 16B 헤더 + JSON, TCP 1문1답.
//
// rclcpp 에 의존하지 않는다 — 단독 실행파일·시험에서 그대로 쓸 수 있어야 한다.
// 상위 의미(어떤 편호가 무엇을 뜻하는가)는 api.hpp 가 갖는다.
//
// 헤더 (big-endian, 16B):
//   [0]     0x5A     sync
//   [1]     0x01     version
//   [2-3]   u16      seq (응답이 같은 값을 반향)
//   [4-7]   u32      JSON 바이트 길이 (무파라미터 = 0)
//   [8-9]   u16      API 편호
//   [10-15] 6B       0x00 예약 (생략 불가)
#ifndef SEER_TCP_IP_TRANSPORT_HPP_
#define SEER_TCP_IP_TRANSPORT_HPP_

#include <cstdint>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "seer_tcp_ip/ports.hpp"

namespace seer_tcp_ip
{

using Json = nlohmann::json;

/// 헤더·편호·ret_code 등 프로토콜 수준 오류.
class ProtocolError : public std::runtime_error
{
  public:
    using std::runtime_error::runtime_error;
};

/// 지령·설정 포트를 broker 없이 직결하려 했다.
/// 단발 도구는 allowGuarded=true 를 명시해 그 사용을 기록으로 남긴다.
class GuardedPortError : public std::runtime_error
{
  public:
    using std::runtime_error::runtime_error;
};

/// 로봇의 동시연결 한도에 걸려 거부됐다(ret_code 61001).
/// 거부 응답은 편호 규칙(요청+10000)을 따르지 않고 포트 번호를 편호로 보낸다 —
/// 그래서 일반 편호 대조에 걸리면 "응답 편호 불일치"라는 엉뚱한 진단이 나온다.
/// 기존 연결은 끊기지 않는다(거부형).
class ConnectionLimitError : public ProtocolError
{
  public:
    using ProtocolError::ProtocolError;
};

/// 수신 중 상대가 연결을 닫았거나 소켓 오류.
class TransportError : public std::runtime_error
{
  public:
    using std::runtime_error::runtime_error;
};

inline constexpr std::uint8_t kSync = 0x5A;
inline constexpr std::uint8_t kVersion = 0x01;
inline constexpr std::size_t kHeadLen = 16;

/// 요청 프레임(16B 헤더 + JSON)을 만든다.
/// 빈 메시지는 body 를 붙이지 않고 length=0 — 공식 packMsg 의 `if(msg != {})` 분기와 같다.
std::vector<char> pack(std::uint16_t seq, std::uint16_t apiType, const Json &msg);

/// 본문 없는 요청.
std::vector<char> pack(std::uint16_t seq, std::uint16_t apiType);

struct Head
{
    std::uint16_t seq = 0;
    std::uint32_t jsonLen = 0;
    std::uint16_t apiType = 0;
};

/// 응답 헤더 16B 해석. 길이 부족·sync 불일치는 ProtocolError.
Head unpackHead(const char *data, std::size_t len);

/// 바이트 스트림 추상 — 시험이 소켓 없이 전 계층을 지나갈 수 있게 한다.
class IByteStream
{
  public:
    virtual ~IByteStream() = default;
    virtual void connect(const std::string &ip, std::uint16_t port, double timeoutSec) = 0;
    /// 최대 n 바이트. 0 = 상대가 닫음.
    virtual std::size_t read(char *buf, std::size_t n) = 0;
    virtual void writeAll(const char *buf, std::size_t n) = 0;
    virtual void close() = 0;
    virtual bool isOpen() const = 0;
};

/// POSIX TCP 소켓 구현.
std::unique_ptr<IByteStream> makeTcpStream();

using StreamFactory = std::function<std::unique_ptr<IByteStream>()>;
using ClockMs = std::function<std::int64_t()>;   // 단조 ms
using SleepMs = std::function<void(std::int64_t)>;

/// 한 포트에 대한 TCP 1문1답 연결.
/// 한 연결에서 이전 응답을 받기 전 다음 요청을 보내지 않는다(프로토콜 제약).
/// 스레드 안전하지 않다 — 포트당 소유자 하나가 원칙이다.
class Transport
{
  public:
    Transport(std::string ip, std::uint16_t port, double timeoutSec = 5.0,
              int minIntervalMs = ports::kMinRequestIntervalMs,
              StreamFactory factory = nullptr, ClockMs clock = nullptr, SleepMs sleep = nullptr);

    void connect();
    void close();
    bool isConnected() const;
    std::uint16_t port() const { return port_; }

    /// 편호 요청 → 응답 JSON. expectType=0 이면 요청+10000 을 기대한다.
    Json request(std::uint16_t apiType, const Json &msg, std::uint16_t expectType = 0);
    Json request(std::uint16_t apiType, std::uint16_t expectType = 0);

    /// 맵 다운로드처럼 본문 바이트 무결성(md5)이 필요한 경우를 위해 파싱 전 바이트를 노출한다.
    std::pair<std::vector<char>, std::uint16_t> requestRaw(std::uint16_t apiType, const Json &msg,
                                                           std::uint16_t expectType = 0);

  private:
    void throttle();
    void recvExact(char *buf, std::size_t n);
    void raiseConnectionLimitIfThat(std::uint16_t respType, const std::vector<char> &body);
    std::pair<std::vector<char>, std::uint16_t> doRequest(std::uint16_t apiType, const Json *msg,
                                                          std::uint16_t expectType);

    std::string ip_;
    std::uint16_t port_;
    double timeoutSec_;
    int minIntervalMs_;
    StreamFactory factory_;
    ClockMs clock_;
    SleepMs sleep_;
    std::unique_ptr<IByteStream> stream_;
    std::uint16_t seq_ = 0;
    std::int64_t lastRequestAt_ = -1;
};

}  // namespace seer_tcp_ip

#endif  // SEER_TCP_IP_TRANSPORT_HPP_
