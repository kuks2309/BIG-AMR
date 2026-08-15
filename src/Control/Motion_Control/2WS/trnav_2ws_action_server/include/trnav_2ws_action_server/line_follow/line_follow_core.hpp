#ifndef TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_CORE_HPP_
#define TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_CORE_HPP_

// LineFollow 순수 제어 코어 — ROS 비의존, 단위테스트 대상.
//
// ── 제어 구조: 공통분 / 차이분 2입력 ──
// 인라인 듀얼스티어는 앞뒤 조향을 두 성분으로 나눠 쓸 수 있다.
//   공통분(양 바퀴 같은 각) → 진행 **방향**을 돌린다. 차체는 돌지 않는다.
//   차이분(앞뒤 차)         → 차체 **heading** 을 돌린다.
// 그래서 「heading 유지」는 별도 모드가 아니라 차이분의 목표를 무엇으로 두느냐의 문제다.
// 출력은 TwoWsCrabIK 의 (theta_body, delta_cte, delta_heading) 에 그대로 대응한다.
//
// ── 부호 규약 ──
// offset(+) = 라인이 진행방향 기준 오른쪽 · angle(+) = 라인 먼 쪽이 오른쪽으로 기움.
// 세 입력 모두 **전진·후진에 같은 식**을 쓴다.
//   공통분: 진행 프레임에서의 회전각이라 IK 의 vx 부호가 진행 방향을 담당한다.
//   차이분: IK 가 「진행 기준 뒷바퀴」에 −delta_heading 을 주므로, 후진에서는 offset 을
//           받는 물리 바퀴가 바뀐다. 그래서 yaw rate 부호는 진행 방향과 무관하게
//           delta_heading 부호를 따른다 — 여기서 방향 계수를 곱하면 후진이 양의 되먹임이 된다.
//
// ── 곡선 편향 ──
// 전방주시 방식은 곡선에서 **완벽히 추종해도** offset 이 0 이 아니다. 주시점이 원호에서
// d²/2R 만큼 벗어나기 때문이다(d=주시거리, R=반경). 이를 오차로 보고 없애려 들면 과조향한다.
// 같은 상태에서 angle ≈ −κ·d 이므로 편향은 angle 에 비례한다:
//   offset_bias = angle · d/(2·half_width)
// 이 계수를 알면 빼낼 수 있고, 곡선을 따라가는 조향은 angle 항이 담당한다.
// 그 angle 항의 기하학적 정답은 kp_angle = L/(2·d) 이다(L=휠베이스).

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace trnav_2ws_action_server::line_follow
{

/// 차이분(heading)의 목표를 무엇으로 둘지. 값은 action 의 heading_mode 와 같다.
enum class HeadingMode : uint8_t
{
    FOLLOW_LINE = 0, ///< 라인 접선을 따라간다 (기본 — 종전 counter-steer 거동)
    HOLD = 1,        ///< goal 수락 시점의 yaw 를 유지한다
    ABSOLUTE = 2     ///< 지정한 절대 yaw 를 유지한다
};

struct Gains
{
    double kp_offset{1.2};   // 횡오차 P (rad per unit offset)
    double kd_offset{0.15};  // 횡오차 D (rad per unit offset/s)
    double kp_angle{0.6};    // 라인 기울기 P — 기하 정답은 L/(2·lookahead)
    // 곡선 추종 feedforward — 기하 정답은 L/lookahead (= 2·kp_angle). 되먹임 게인이 아니라
    // 「이 곡률을 돌려면 앞뒤 차가 얼마여야 하는가」의 환산 계수다.
    double k_curve_heading{1.2};
    double kp_heading{1.0};  // heading 되먹임 P (HOLD·ABSOLUTE 전용, rad 차이분 per rad 오차)
    double kd_heading{0.1};  // heading 되먹임 D (HOLD·ABSOLUTE 전용)
    // 바퀴각 하나의 포화 (약 25 deg). **차이분에는 이 값의 2배**가 걸린다 — 차이분은
    // 바퀴각 두 개의 차라서 각각이 한계에 있어도 차는 2배까지 정당하다.
    double max_steer_rad{0.44};
    double slow_gain{0.7};        // 커브 감속: v = v_max*(1 - slow_gain*|offset|)
    double curve_bias_gain{0.0};  // 곡선 편향 계수 d/(2·half_width). 0 = 보상 없음
};

/// TwoWsCrabIK 에 그대로 넘길 조향 입력 3개 + 목표 속도.
struct SteerInputs
{
    double theta_body{0.0};    ///< 진행 방향을 라인 접선에 정렬 (rad)
    double delta_cte{0.0};     ///< 횡오차 보정 (rad) — 공통분에 더해진다
    double delta_heading{0.0}; ///< 앞뒤 차이 (rad) — 차체 heading 을 돌린다
    double v_target{0.0};      ///< 목표 종속도 크기 (m/s, 항상 >= 0)
    double offset_used{0.0};   ///< 편향 보상 후 실제로 제어에 쓴 횡오차 (진단용)
};

inline double clampAbs(double v, double limit)
{
    return std::max(-limit, std::min(limit, v));
}

/// 곡선 편향을 뺀 횡오차. `bias_gain` 이 0 이면 입력을 그대로 돌려준다.
///
/// @param offset     측정 횡오차 [-1,1]
/// @param angle_rad  라인 기울기 [rad]
/// @param bias_gain  lookahead / (2 · half_width). 카메라 기하에서 정해진다
inline double correctCurveBias(double offset, double angle_rad, double bias_gain)
{
    return offset - bias_gain * angle_rad;
}

/// FOLLOW_LINE 모드의 heading 오차 — 차체를 라인 접선에 맞추는 데 필요한 회전각.
///
/// angle(+) = 라인 먼 쪽이 오른쪽 기움 = 접선이 차체보다 시계방향 → 차체는 시계방향
/// (음의 CCW)으로 돌아야 한다.
inline double headingErrorFollowLine(double angle_rad)
{
    return -angle_rad;
}

/// 조향 입력 3개와 목표 속도를 만든다.
///
/// @param offset_f        필터된 횡오차 [-1,1] (편향 보상 **전**)
/// @param offset_rate     필터된 오차 변화율 (1/s)
/// @param angle_rad       라인 기울기 (rad)
/// @param heading_err_rad 차체 heading 오차 (rad, + = CCW 로 더 돌아야 함)
/// @param heading_err_rate heading 오차 변화율 (rad/s)
/// @param max_speed       goal 의 최대 종속도 크기 (m/s, > 0)
/// @param mode            차이분을 무엇이 구동할지 — FOLLOW_LINE 은 곡률 feedforward,
///                        HOLD·ABSOLUTE 는 yaw 오차 되먹임
/// @param g               게인
///
/// 진행 방향(reverse)을 받지 않는다 — 위 부호 규약대로 세 입력 모두 방향 불변이다.
inline SteerInputs computeSteer(double offset_f, double offset_rate, double angle_rad,
                                double heading_err_rad, double heading_err_rate, double max_speed,
                                HeadingMode mode, const Gains &g)
{
    SteerInputs out;
    const double offset_used = correctCurveBias(offset_f, angle_rad, g.curve_bias_gain);
    out.offset_used = offset_used;

    // 공통분 — 진행 프레임 기준이라 전진·후진 같은 식.
    //   라인 접선 정렬: theta_body = -angle
    //   횡오차 보정  : 라인이 오른쪽(+)이면 진행 방향을 오른쪽(음의 CCW)으로 돌린다
    out.theta_body = clampAbs(-g.kp_angle * angle_rad, g.max_steer_rad);
    out.delta_cte =
        clampAbs(-(g.kp_offset * offset_used + g.kd_offset * offset_rate), g.max_steer_rad);

    // 차이분 — heading 오차(+ = CCW 로 더 돌아야 함). yaw rate 는 delta_heading 부호를
    // 따르며 진행 방향에 의존하지 않는다(위 부호 규약).
    //
    // FOLLOW_LINE 의 오차는 「없애야 할 편차」가 아니라 **곡률 그 자체**다(라인을 정확히
    // 타고 있어도 angle = −κ·d 로 남는다). 그래서 되먹임 게인이 아니라 기하 환산으로 낸다:
    //   필요 앞뒤 차 = κ·L,  κ = −angle/d  →  delta_heading = (L/d)·(−angle)
    // 이 값이 theta_body(= L/2d·(−angle))의 정확히 2배라, 곡선에서 crab 성분 없이 순수
    // counter-steer 가 된다. D 항은 두지 않는다 — feedforward 라 미분할 대상이 아니다.
    //
    // 포화는 `max_steer_rad` 의 **2배**다. 차이분은 바퀴각 두 개의 차이므로, 앞이 +25°·
    // 뒤가 −25° 인 순간에도 물리적으로 성립한다. 여기에 1배를 걸면 R=2.7 m 보다 조인
    // 곡선에서 필요 조향(2·atan(κL/2))이 낼 수 없는 값이 되어 곡선을 놓친다.
    // 실제 바퀴 한계는 하류의 `TwoWsCrabIK` 가 Phase 0 기준 ±25° 로 건다.
    const double diff_limit = 2.0 * g.max_steer_rad;
    if (mode == HeadingMode::FOLLOW_LINE)
    {
        out.delta_heading = clampAbs(g.k_curve_heading * heading_err_rad, diff_limit);
    }
    else
    {
        out.delta_heading =
            clampAbs(g.kp_heading * heading_err_rad + g.kd_heading * heading_err_rate, diff_limit);
    }

    // 커브 감속은 **보상 전** 측정값으로 판단한다 — 편향이 큰 곡선일수록 실제로 느려야 한다.
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
// coast 중 양질 재검출(conf ok + |offset| < resume 임계) 시 FOLLOWING 복귀.
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
