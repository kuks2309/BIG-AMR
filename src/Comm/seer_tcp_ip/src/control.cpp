#include "seer_tcp_ip/control.hpp"

#include <chrono>
#include <cstring>
#include <thread>

namespace seer_tcp_ip
{
namespace
{

ClockMs defaultClock()
{
    return [] {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::steady_clock::now().time_since_epoch())
            .count();
    };
}

bool blank(const std::string &s)
{
    for (char c : s)
    {
        if (!std::isspace(static_cast<unsigned char>(c)))
        {
            return false;
        }
    }
    return true;
}

}  // namespace

ControlSession::ControlSession(SeerApi &api, std::string nickName, bool stopOnExit)
    : api_(api), nickName_(std::move(nickName)), stopOnExit_(stopOnExit)
{
    if (blank(nickName_))
    {
        throw std::invalid_argument(
            "nickName 은 비어 있을 수 없다 — 로봇 화면에서 소유자를 식별해야 한다");
    }
    acquire();
}

ControlSession::~ControlSession()
{
    try
    {
        release();
    }
    catch (...)
    {
        // 소멸자에서 던지지 않는다. 반납 실패는 호출자가 release() 를 직접 불러야 볼 수 있다.
    }
}

const Json &ControlSession::acquire()
{
    if (held_)
    {
        throw ControlError("이미 제어권을 쥐고 있다 — 이중 획득은 반납 짝을 깨뜨린다");
    }
    try
    {
        previousOwner_ = api_.getControlOwner();
    }
    catch (const std::exception &)
    {
        previousOwner_ = Json::object();
    }
    api_.seizeControl(nickName_);
    held_ = true;
    return previousOwner_;
}

void ControlSession::release()
{
    if (!held_)
    {
        return;
    }
    try
    {
        if (stopOnExit_)
        {
            api_.stop();
        }
    }
    catch (...)
    {
        held_ = false;
        api_.releaseControl();  // 정지가 실패해도 반납은 시도한다
        throw;
    }
    held_ = false;
    api_.releaseControl();
}

JogKeepalive::JogKeepalive(SeerApi &api, double vx, double vy, double w, int durationMs,
                           int intervalMs, ClockMs clock)
    : api_(api), vx_(vx), vy_(vy), w_(w), durationMs_(durationMs), intervalMs_(intervalMs),
      clock_(clock ? std::move(clock) : defaultClock())
{
    if (durationMs_ <= 0)
    {
        throw std::invalid_argument(
            "durationMs 는 양수여야 한다 — 0 은 무한이라 dead-man 이 없어진다");
    }
    if (intervalMs_ <= 0)
    {
        throw std::invalid_argument("intervalMs 는 양수여야 한다");
    }
    if (intervalMs_ >= durationMs_)
    {
        throw std::invalid_argument(
            "intervalMs(" + std::to_string(intervalMs_) + "ms) 가 durationMs(" +
            std::to_string(durationMs_) +
            "ms) 이상이다 — 이러면 매 주기 dead-man 이 먼저 만료돼 로봇이 섰다 갔다 한다");
    }
}

JogKeepalive::~JogKeepalive()
{
    try
    {
        stop();
    }
    catch (...)
    {
    }
}

void JogKeepalive::setVelocity(double vx, double vy, double w)
{
    vx_ = vx;
    vy_ = vy;
    w_ = w;
}

bool JogKeepalive::due() const
{
    if (lastSentAt_ < 0)
    {
        return true;
    }
    return (clock_() - lastSentAt_) >= intervalMs_;
}

bool JogKeepalive::tick()
{
    if (!due())
    {
        return false;
    }
    api_.openLoopMove(vx_, vy_, w_, durationMs_);
    lastSentAt_ = clock_();
    ++sentCount_;
    return true;
}

Json JogKeepalive::stop()
{
    lastSentAt_ = -1;
    vx_ = vy_ = w_ = 0.0;
    return api_.stop();
}

void relocateAndConfirm(SeerApi &api, const Json &params, int timeoutMs, int pollIntervalMs,
                        ClockMs clock, SleepMs sleep,
                        std::function<void(const std::string &)> log)
{
    if (timeoutMs <= 0 || pollIntervalMs <= 0)
    {
        throw std::invalid_argument("timeoutMs·pollIntervalMs 는 양수여야 한다");
    }
    ClockMs now = clock ? std::move(clock) : defaultClock();
    SleepMs nap = sleep ? std::move(sleep) : SleepMs([](std::int64_t ms) {
        std::this_thread::sleep_for(std::chrono::milliseconds(ms));
    });
    const auto say = [&log](const std::string &m) {
        if (log)
        {
            log(m);
        }
    };

    const bool sendCommand = !(params.is_null() || (params.is_object() && params.empty()));
    if (sendCommand)
    {
        api.relocateWith(params);
        say("재측위 지령(2002) 수리됨 — 아직 성공이 아니다");
    }

    const std::int64_t deadline = now() + timeoutMs;
    int last = -1;
    while (now() < deadline)
    {
        const int status = api.getRelocStatusCode();
        if (status == reloc::kSuccess)
        {
            say("측위 확정(reloc_status=1)");
            return;
        }
        if (status == reloc::kCompleted)
        {
            say("계산 완료·미확정 — 2003 으로 확정한다");
            api.confirmLocation();
        }
        else if (status != last)
        {
            say("reloc_status=" + std::to_string(status));
        }
        last = status;
        nap(pollIntervalMs);
    }
    throw ControlError("재측위가 " + std::to_string(timeoutMs) +
                       "ms 안에 확정되지 않았다 (마지막 reloc_status=" + std::to_string(last) +
                       ") — 「2002 를 보냈다」는 성공이 아니다");
}

bool preemptedByControl(const std::exception &e)
{
    const std::string needle = "ret_code=" + std::to_string(ports::kControlPreemptedRetCode);
    return std::string(e.what()).find(needle) != std::string::npos;
}

std::string describeOwner(SeerApi &api)
{
    const Json owner = api.getControlOwner();
    if (!owner.value("locked", false))
    {
        return "제어권 비어 있음";
    }
    return "제어권 보유: nick_name='" + owner.value("nick_name", std::string()) +
           "' ip=" + owner.value("ip", std::string()) + " (port " +
           std::to_string(ports::kConfig) + " 로 4005 를 걸면 뺏는다)";
}

}  // namespace seer_tcp_ip
