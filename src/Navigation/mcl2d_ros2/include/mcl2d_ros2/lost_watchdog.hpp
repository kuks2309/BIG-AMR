// 입력 두절 워치독 — 원본 MCLoc 의 ScanLostTimeThresh·OdoLostTimeThresh 대응.
//
// **게이트가 아니라 워치독이다.** 원본은 스캔이 끊겨도 위치추정을 멈추지 않는다 — 발행 중단·
// 상태 강등·재위치추정 유발 중 어느 것도 하지 않고, 로그 1회와 에러코드 게시만 한다.
// 근거는 원본 실측 대조표 docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md §8.
//
// ROS 의존이 없다 — 시각은 호출자가 ns 로 준다. 그래야 시계 없이 시험할 수 있다.
#ifndef MCL2D_ROS2_LOST_WATCHDOG_HPP
#define MCL2D_ROS2_LOST_WATCHDOG_HPP

#include <algorithm>
#include <cstdint>

namespace mcl2d_ros2
{

// 원본 rbk::ErrorCodes 번호를 그대로 보존한다.  comment-check: ignore
//   우리에겐 그 에러 버스가 없어 /diagnostics 로
//   내보내지만, 번호를 남겨야 원본 로그·문서와 대조할 수 있다.
inline constexpr int kErrorScanLost = 52102; // "localization module cannot get laser data"
inline constexpr int kErrorOdoLost = 52106;  // "odo data lost"

// 원본 loadParam<int> 의 기본값·범위. 이 키는 원본의 어떤 설정 파일에도 없다 —
//   300 은 바이너리 기본값이고 배포는 그 값으로 돈다.
inline constexpr std::int64_t kDefaultLostThreshMs = 300;
inline constexpr std::int64_t kMinLostThreshMs = 0;
inline constexpr std::int64_t kMaxLostThreshMs = 10000;

// 입력 스트림 하나의 두절 여부를 판정한다. 스캔·오도에 각각 한 대씩 둔다.
class LostWatchdog
{
  public:
    explicit LostWatchdog(std::int64_t thresh_ms = kDefaultLostThreshMs)
    {
        setThresholdMs(thresh_ms);
    }

    // 범위 밖 값은 원본과 같이 잘라 낸다.
    void setThresholdMs(std::int64_t thresh_ms)
    {
        thresh_ms_ = std::max(kMinLostThreshMs, std::min(kMaxLostThreshMs, thresh_ms));
    }

    std::int64_t thresholdMs() const
    {
        return thresh_ms_;
    }

    // 계측을 시작한다(활성화 시점). 이 기준선이 있어야 **한 건도 오지 않는** 경우도 두절로 잡힌다.
    //   원본이 그 시각 슬롯을 언제 세우는지는 실측 기록에 없다 — 여기서는 활성화 시각으로 잡는다.
    void start(std::int64_t now_ns)
    {
        last_rx_ns_ = now_ns;
        started_ = true;
        received_ = false;
        lost_ = false;
        just_lost_ = false;
        just_recovered_ = false;
    }

    void markReceived(std::int64_t now_ns)
    {
        last_rx_ns_ = now_ns;
        started_ = true;
        received_ = true;
    }

    // 한 주기 판정. 두절이면 참. 원본 판정식은 `thresh_ns >= elapsed_ns` 일 때 정상이므로,
    //   두절은 **초과**(strictly greater)에서만 성립한다.
    bool update(std::int64_t now_ns)
    {
        just_lost_ = false;
        just_recovered_ = false;
        if (!started_)
            return false;

        const std::int64_t elapsed_ns = now_ns - last_rx_ns_;
        const bool lost = elapsed_ns > thresh_ms_ * 1000000;
        if (lost && !lost_)
            just_lost_ = true;
        else if (!lost && lost_)
            just_recovered_ = true;
        lost_ = lost;
        return lost_;
    }

    bool lost() const
    {
        return lost_;
    }
    // 이번 update() 에서 두절로 **진입**했는가 — 로그를 1회로 제한하는 데 쓴다
    //   (원본의 정적 err_reported 플래그에 대응).
    bool justLost() const
    {
        return just_lost_;
    }
    // 이번 update() 에서 회복했는가 — 원본의 clearError 지점에 대응.
    bool justRecovered() const
    {
        return just_recovered_;
    }
    // 입력을 한 건이라도 받은 적이 있는가. 두절 원인이 「끊김」인지 「처음부터 없음」인지 가른다.
    bool everReceived() const
    {
        return received_;
    }

    std::int64_t elapsedMs(std::int64_t now_ns) const
    {
        if (!started_)
            return 0;
        return (now_ns - last_rx_ns_) / 1000000;
    }

  private:
    std::int64_t thresh_ms_ = kDefaultLostThreshMs;
    std::int64_t last_rx_ns_ = 0;
    bool started_ = false;
    bool received_ = false;
    bool lost_ = false;
    bool just_lost_ = false;
    bool just_recovered_ = false;
};

} // namespace mcl2d_ros2

#endif // MCL2D_ROS2_LOST_WATCHDOG_HPP
