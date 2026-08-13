#ifndef TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_CORE_HPP_
#define TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_CORE_HPP_

// LineFollow 순수 제어 코어 — ROS 비의존, 단위테스트 대상.
//
// 부호 규약: offset(+) = 라인이 **진행방향 기준** 오른쪽. 진행방향을 오른쪽으로 돌리려면
// 세계좌표 omega < 0 이 필요하고, counter-steer 자전거에서 omega = 2*vx*tan(delta_f)/L
// 이므로 전진(vx>0)이면 delta_f < 0, 후진(vx<0)이면 delta_f > 0 이다. 그래서 조향식에
// -sign(vx) 가 붙는다. angle(+) = 라인 위쪽이 오른쪽으로 기움 — offset 과 같은 방향.

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace trnav_2ws_action_server::line_follow
{

struct Gains
{
    double kp_offset{1.2};       // 횡오차 P (rad steer per unit offset)
    double kd_offset{0.15};      // 횡오차 D (rad steer per unit offset/s)
    double kp_angle{0.6};        // 라인 기울기 P (rad steer per rad)
    double max_steer_rad{0.44};  // 조향 포화 (약 25 deg)
    double slow_gain{0.7};       // 커브 감속: v = v_max*(1 - slow_gain*|offset|)
};

struct Command
{
    double steer_rad{0.0};  // 전륜 조향각 지령 (후륜은 counter-steer 로 부호 반전)
    double v_target{0.0};   // 목표 종속도 크기 (ramp 전, m/s, 항상 >= 0)
};

inline double clampAbs(double v, double limit)
{
    return std::max(-limit, std::min(limit, v));
}

/// 조향 PD + 커브 감속.
///
/// @param offset_f     필터된 횡오차 [-1,1]
/// @param offset_rate  필터된 오차 변화율 (1/s)
/// @param angle_rad    라인 기울기 (rad)
/// @param max_speed    goal 의 최대 종속도 크기 (m/s, > 0)
/// @param reverse      후진이면 true — 조향 부호가 뒤집힌다
/// @param g            게인
/// @return 조향각(포화 적용)과 목표속도 크기
inline Command computeCommand(double offset_f, double offset_rate, double angle_rad, double max_speed, bool reverse,
                              const Gains &g)
{
    Command out;
    const double dir = reverse ? -1.0 : 1.0;
    out.steer_rad =
        clampAbs(-dir * (g.kp_offset * offset_f + g.kd_offset * offset_rate + g.kp_angle * angle_rad), g.max_steer_rad);
    const double slow = 1.0 - g.slow_gain * std::min(1.0, std::abs(offset_f));
    out.v_target = std::max(0.0, max_speed * slow);
    return out;
}

/// 속도 ramp: current -> target, 변화율 상한 accel (m/s^2). 가감속 대칭.
inline double rampSpeed(double current, double target, double accel, double dt)
{
    const double max_delta = accel * dt;
    return current + clampAbs(target - current, max_delta);
}

// ── 라인 소실 coast 상태기계 ──
// FOLLOWING 중 소실 -> LOST_COAST(조향 유지·감속만) -> coast_timeout 초과 시 STOPPING.
// coast 중 양질 재검출(conf 통과 + |offset| < resume 임계) 시 FOLLOWING 복귀.
// 사람 운전의 '핸들 잡고 유지' 방식 — 원본 2WD 설계를 그대로 계승한다.
enum class Phase : uint8_t
{
    WAIT_LINE = 0,
    FOLLOWING = 1,
    LOST_COAST = 2,
    STOPPING = 3
};

class LostCoastFsm
{
  public:
    LostCoastFsm(double coast_timeout_s, double resume_max_offset)
        : coast_timeout_s_(coast_timeout_s), resume_max_offset_(resume_max_offset)
    {
    }

    /// 매 제어주기 호출. good = detected && conf 임계 통과.
    /// 반환: 현재 phase. 재개(coast->following) 직후 1회 resumed() 가 true.
    Phase update(bool good, double offset, double now_s)
    {
        resumed_ = false;
        switch (phase_)
        {
        case Phase::WAIT_LINE:
            if (good)
            {
                phase_ = Phase::FOLLOWING;
            }
            break;
        case Phase::FOLLOWING:
            if (!good)
            {
                phase_ = Phase::LOST_COAST;
                lost_at_s_ = now_s;
            }
            break;
        case Phase::LOST_COAST:
            if (good && std::abs(offset) < resume_max_offset_)
            {
                phase_ = Phase::FOLLOWING;
                resumed_ = true;
            }
            else if (now_s - lost_at_s_ > coast_timeout_s_)
            {
                phase_ = Phase::STOPPING;
            }
            break;
        case Phase::STOPPING:
            break; // 종단 상태 — execute 가 정지·abort 처리
        }
        return phase_;
    }

    Phase phase() const
    {
        return phase_;
    }
    bool resumed() const
    {
        return resumed_;
    }

  private:
    double coast_timeout_s_;
    double resume_max_offset_;
    Phase phase_{Phase::WAIT_LINE};
    double lost_at_s_{0.0};
    bool resumed_{false};
};

} // namespace trnav_2ws_action_server::line_follow

#endif // TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_CORE_HPP_
