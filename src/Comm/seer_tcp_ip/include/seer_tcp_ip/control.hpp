// 제어권 세션과 dead-man jog — 편호 래퍼가 아니라 동작이라 별 파일에 둔다.
//
// Seer 는 지령 계열 API 를 받기 전에 제어권(4005)을 요구하고, 없으면 ret_code 40020 으로 거부한다.
// 제어권은 뺏고 뺏기는 자원이라 획득과 반납이 반드시 짝이어야 한다 — 반납하지 않고 죽으면 다음
// 클라이언트가 40020 으로 막히고, 그 원인이 로봇 쪽에 남지 않는다.
//
// 스레드를 만들지 않는다. 호출자의 타이머·루프가 tick() 을 부른다 — 단일 스레드 executor 에
// 그대로 얹히고, 시험에서 시계를 주입할 수 있다.
#ifndef SEER_TCP_IP_CONTROL_HPP_
#define SEER_TCP_IP_CONTROL_HPP_

#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>

#include "seer_tcp_ip/api.hpp"

namespace seer_tcp_ip
{

/// 제어권 상태가 요구와 맞지 않아 진행할 수 없다.
class ControlError : public std::runtime_error
{
  public:
    using std::runtime_error::runtime_error;
};

/// 제어권을 잡고 쓰고 반납하는 RAII 소유자.
///
/// 생성 시 이전 소유자를 조회해 previousOwner() 에 남기고 4005 로 획득한다.
/// 소멸 시 정지(2000) 를 먼저 보낸 뒤 4006 으로 반납한다 — 예외로 빠져나가도 마찬가지다.
/// 정지가 실패해도 반납은 시도한다(제어권을 쥔 채 죽는 것이 더 나쁘다).
///
/// 지령 포트를 쓰므로 allowGuarded=true 로 만든 SeerApi 가 필요하다.
class ControlSession
{
  public:
    /// @param nickName 로봇이 소유자로 표시할 이름. 어느 프로세스가 잡았는지 알아볼 수 있게 짓는다.
    /// @param stopOnExit 반납 전 정지(2000) 를 보낼지. 끄면 관성으로 계속 갈 수 있다.
    ControlSession(SeerApi &api, std::string nickName, bool stopOnExit = true);
    ~ControlSession();

    ControlSession(const ControlSession &) = delete;
    ControlSession &operator=(const ControlSession &) = delete;

    /// 이전 소유자를 기록하고 제어권을 획득한다. 이미 쥐고 있으면 ControlError.
    /// 1060 조회가 실패하면 previousOwner 는 빈 객체가 되고 획득은 그대로 시도한다.
    const Json &acquire();

    /// 정지 후 반납한다. 쥐고 있지 않으면 아무것도 하지 않는다.
    void release();

    bool held() const { return held_; }
    const Json &previousOwner() const { return previousOwner_; }

  private:
    SeerApi &api_;
    std::string nickName_;
    bool stopOnExit_;
    bool held_ = false;
    Json previousOwner_ = Json::object();
};

/// dead-man 이 걸린 개루프 주행 — duration 보다 짧은 주기로 2010 을 재송신한다.
///
/// durationMs 안에 새 지령이 없으면 로봇이 스스로 선다. 그래서 재송신 주기가 duration 보다
/// 짧아야 연속 주행이 되고, 보내는 쪽이 죽으면 duration 안에 로봇이 멈춘다. 그 성질이 이
/// 클래스의 존재 이유다 — 주기가 duration 이상이면 매 주기 섰다 갔다 하므로 생성 시 거부한다.
///
/// 스레드를 만들지 않는다. 호출자가 tick() 을 자주 부르면 되고, 보낼 시점이 아니면 아무 일도
/// 하지 않는다(과송신은 로봇이 연결을 정리하는 사유가 된다).
class JogKeepalive
{
  public:
    JogKeepalive(SeerApi &api, double vx, double vy, double w, int durationMs, int intervalMs,
                 ClockMs clock = nullptr);
    ~JogKeepalive();

    JogKeepalive(const JogKeepalive &) = delete;
    JogKeepalive &operator=(const JogKeepalive &) = delete;

    /// 다음 tick 부터 실을 속도를 바꾼다. 즉시 보내지는 않는다.
    void setVelocity(double vx, double vy, double w);

    /// 지금 재송신할 시점인가. 첫 호출은 항상 true.
    bool due() const;

    /// 시점이면 2010 을 한 번 보낸다. 실제로 보냈으면 true.
    bool tick();

    /// 즉시 정지(2000) 를 보내고 재송신 상태를 지운다.
    Json stop();

    long sentCount() const { return sentCount_; }
    double vx() const { return vx_; }
    double vy() const { return vy_; }
    double w() const { return w_; }

  private:
    SeerApi &api_;
    double vx_, vy_, w_;
    int durationMs_;
    int intervalMs_;
    ClockMs clock_;
    std::int64_t lastSentAt_ = -1;
    long sentCount_ = 0;
};

/// 재측위 상태(1021 `reloc_status`).
namespace reloc
{
/// 측위가 확정됐다. **이 값만이 성공이다.**
inline constexpr int kSuccess = 1;
/// 재측위 진행 중.
inline constexpr int kRelocing = 2;
/// 계산은 끝났으나 **확정되지 않았다** — 2003 을 보내야 1 로 넘어간다.
/// 구형 Robokit(3.4.6.1800 미만)에서만 나온다. 이 기체는 rbk 3.4.5.22 라 해당한다.
inline constexpr int kCompleted = 3;
}  // namespace reloc

/// 재측위를 **성공까지** 수행한다 — 2002 발신 → 1021 폴링 → 필요 시 2003 확정.
///
/// 「2002 를 보냈다」는 성공이 아니다. 로봇은 지령을 수리했을 뿐이고, 측위가 맞았는지는
/// `reloc_status` 가 1 이 되어야 안다. 상태 3(계산 완료·미확정)이 보이면 2003 을 보낸다.
///
/// params 가 비면 2002 를 보내지 않고 **현재 측위가 확정되기를 기다리기만** 한다.
///
/// @param timeoutMs 이 시간 안에 1 이 되지 않으면 ControlError.
/// @param pollIntervalMs 1021 폴링 주기.
/// @param log 진행 로그(선택). 널이면 조용히 돈다.
/// @throws ControlError 시간 안에 확정되지 않음.
void relocateAndConfirm(SeerApi &api, const Json &params, int timeoutMs = 120000,
                        int pollIntervalMs = 500, ClockMs clock = nullptr,
                        SleepMs sleep = nullptr,
                        std::function<void(const std::string &)> log = nullptr);

/// 예외가 「제어권이 없어서 거부됨」인가 — 4005 를 먼저 잡으라는 신호.
bool preemptedByControl(const std::exception &e);

/// 1060 응답을 한 줄로 요약한다. 로그·진단용.
std::string describeOwner(SeerApi &api);

}  // namespace seer_tcp_ip

#endif  // SEER_TCP_IP_CONTROL_HPP_
