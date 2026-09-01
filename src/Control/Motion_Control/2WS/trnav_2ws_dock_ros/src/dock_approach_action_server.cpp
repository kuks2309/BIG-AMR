// AMRMotionDockApproach 액션 서버 — 벽 3면 측위(/wall_pose) 기준 정밀 도킹 접근.
//
// 제어는 이식 코어(trnav_2ws_dock_control)의 순수 함수만 쓴다 — 이 파일은 조립이다:
// 관측(/wall_pose) → wallPoseToDockObs → 페이즈 로직 → composePhase4Wheels →
// WheelSetArray(/motion/wheel_cmd/dock, mux source 40).
//
// 안전 규약: 어떤 종료 경로(성공·중단·취소·예외)든 «정지 지령 → mux 원복» 순서.
// 관측이 낡으면 유예 동안 steer-hold 정지(눈 감고 대기), 초과 시 OBS_LOST 중단.
// yaw runaway 는 /wall_pose yaw 누적(imuAccumStep 재사용)으로 감시한다.

#include <algorithm>
#include <cmath>
#include <memory>
#include <mutex>
#include <deque>
#include <optional>
#include <string>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "trnav_2ws_interfaces/action/amr_motion_dock_approach.hpp"
#include <atomic>

#include "trnav_msgs/msg/wheel_set_array.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"

#include "dock_control/dock_core.hpp"
#include "dock_control/dock_obs.hpp"

namespace
{
constexpr double kDegToRad = M_PI / 180.0;

using DockAction = trnav_2ws_interfaces::action::AMRMotionDockApproach;
using GoalHandle = rclcpp_action::ServerGoalHandle<DockAction>;

enum Phase : int8_t
{
    kPreAlign = 0,
    kApproach = 1,
    kVerify = 2,
    kReapproach = 3,
    kPreYaw = 4,
};

}  // namespace

class DockApproachServer : public rclcpp::Node
{
  public:
    DockApproachServer() : Node("dock_approach_server")
    {
        declareParams();

        cmd_pub_ = create_publisher<trnav_msgs::msg::WheelSetArray>(
            "/motion/wheel_cmd/dock", rclcpp::QoS(10).reliable());
        // mux 최종 출력의 실측 지령속도 — armed 인수 순간 슬루 시작점으로 써서
        // 주행 속도가 goal 상한보다 높아도 지령이 계단 없이 이어진다
        bus_cmd_sub_ = create_subscription<trnav_msgs::msg::WheelSetArray>(
            "/motor/wheel_cmd", rclcpp::QoS(10),
            [this](trnav_msgs::msg::WheelSetArray::SharedPtr m) {
                double v = 0.0;
                for (const auto &w : m->wheels)
                {
                    v = std::max(v, std::fabs(w.velocity));
                }
                last_bus_speed_.store(v);
            });
        pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
            "/wall_pose", 10, [this](geometry_msgs::msg::PoseStamped::SharedPtr m) {
                std::lock_guard<std::mutex> lk(pose_mtx_);
                last_pose_ = *m;
                last_pose_time_ = now();
            });
        select_client_ =
            create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

        action_server_ = rclcpp_action::create_server<DockAction>(
            this, "amr_motion_dock_approach",
            [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const DockAction::Goal> g) {
                return onGoal(*g);
            },
            [this](const std::shared_ptr<GoalHandle> &) {
                return rclcpp_action::CancelResponse::ACCEPT;
            },
            [this](const std::shared_ptr<GoalHandle> &gh) { onAccepted(gh); });

        timer_ = create_wall_timer(
            std::chrono::duration<double>(1.0 / control_rate_hz_), [this]() { onTick(); });

        RCLCPP_INFO(get_logger(), "dock_approach_server 준비 — mux source %d, arm=%.4f m",
                    static_cast<int>(mux_source_id_), arm_m_);
    }

  private:
    // ── 파라미터 (게인·한계는 전부 주입 — 코어의 리터럴 금지 규약 승계) ──────────
    void declareParams()
    {
        control_rate_hz_ = declare_parameter<double>("control_rate_hz", 30.0);
        obs_max_age_s_ = declare_parameter<double>("obs_max_age_s", 0.2);
        obs_grace_s_ = declare_parameter<double>("obs_grace_s", 1.0);
        default_timeout_s_ = declare_parameter<double>("default_timeout_s", 60.0);
        runaway_yaw_deg_ = declare_parameter<double>("runaway_yaw_deg", 15.0);
        mux_source_id_ = static_cast<uint8_t>(declare_parameter<int64_t>("mux_source_id", 40));
        mux_restore_id_ = static_cast<uint8_t>(declare_parameter<int64_t>("mux_restore_id", 0));

        dist_gains_.kp = declare_parameter<double>("dist_kp", 0.8);
        dist_gains_.ki = declare_parameter<double>("dist_ki", 0.0);
        dist_gains_.kd = declare_parameter<double>("dist_kd", 0.0);
        dist_limits_.i_band = declare_parameter<double>("dist_i_band_m", 0.05);
        dist_limits_.i_clamp = declare_parameter<double>("dist_i_clamp", 0.05);
        dist_limits_.lpf_a = declare_parameter<double>("dist_lpf_a", 0.6);

        delta_max_rad_ = declare_parameter<double>("delta_max_deg", 25.0) * kDegToRad;
        entry_bias_rad_ = declare_parameter<double>("entry_bias_deg", 0.0) * kDegToRad;
        // 자세 채널 — 전/후 조향 분할(δf=steer+δh, δr=steer−δh). 속도차 yaw(코어
        // composePhase4Wheels 의 w_deg)는 조향 ≈ ±90°(측면 crab)에서만 유효하고 전방
        // 접근(조향≈0)에서는 sin(조향)≈0 이라 무권한·부호 불안정(SIL 실측: +17° 폭주).
        // ω ≈ v·δh·cos(steer)/arm 이므로 δh 부호는 진행 방향(v 부호)에 따라 뒤집는다.
        yaw_split_kp_deg_per_deg_ = declare_parameter<double>("yaw_split_kp_deg_per_deg", 0.3);
        yaw_split_max_deg_ = declare_parameter<double>("yaw_split_max_deg", 5.0);

        // PRE_YAW — 접근 전 제자리 회전으로 초기 yaw 소거. 접근 중 조향 분할은 v→0 에서
        // 권한이 사라지므로(ω ∝ v) 큰 초기 yaw 는 여기서 지운다. 조향 ±90° 전환은
        // settle-then-drive — 정착 전 구동하면 바퀴가 원치 않는 방향으로 쓸린다.
        spin_kp_dps_per_deg_ = declare_parameter<double>("spin_kp_dps_per_deg", 1.0);
        spin_w_max_dps_ = declare_parameter<double>("spin_w_max_dps", 5.0);
        spin_w_min_dps_ = declare_parameter<double>("spin_w_min_dps", 0.8);
        settle_s_ = declare_parameter<double>("steer_settle_s", 2.0);
        // 무정지 전환(주행 체이닝) — yaw 공차 내 + 스핀 미경유로 진입하면 settle 을
        // 생략하고 즉시 접근한다. 직진 주행 직후는 조향이 접근축에 정착해 있어 쓸림이
        // 없고 속도 연속(출구속도=진입 PID 지령)이 유지된다. 미정렬·스핀 경유 진입은
        // settle-then-drive 경로를 탄다.
        skip_settle_if_aligned_ = declare_parameter<bool>("skip_settle_if_aligned", false);
        // 접근 속도 슬루 한계(m/s²) — 무정지 진입 시 지령을 goal 속도에서 시작해
        // 이 감속률로만 낮춘다(속도 절벽 제거). 0 = 미적용(즉시 목표 속도).
        approach_decel_mps2_ = declare_parameter<double>("approach_decel_mps2", 0.0);
        // 사전 대기(armed) 인수 거리(m) — >0 이면 goal 을 수락해도 mux 를 바로 뺏지
        // 않고, wall 관측 잔거리 |e_d| 가 이 값 이내로 들어온 순간 인수한다(주행
        // 액션과의 무공백 전환). 0 = 수락 즉시 인수. goal 수락 시점 값으로 재독.
        arm_engage_dist_m_ = declare_parameter<double>("arm_engage_dist_m", 0.0);
        // 접근 중 d·lat 만 수렴하고 yaw 미달이 지속되면 행 방지로 VERIFY 로 넘긴다
        approach_stuck_cycles_ =
            static_cast<int>(declare_parameter<int64_t>("approach_stuck_cycles", 60));

        near_zone_m_ = declare_parameter<double>("near_zone_m", 0.30);
        v_near_mps_ = declare_parameter<double>("v_near_mps", 0.03);
        prealign_kp_ = declare_parameter<double>("prealign_kp", 0.5);
        prealign_v_max_ = declare_parameter<double>("prealign_v_max_mps", 0.05);
        reapproach_dist_m_ = declare_parameter<double>("reapproach_dist_m", 0.15);
        reapproach_v_mps_ = declare_parameter<double>("reapproach_v_mps", 0.05);
        max_reapproach_ = static_cast<int>(declare_parameter<int64_t>("max_reapproach", 1));
        verify_cycles_ = static_cast<int>(declare_parameter<int64_t>("verify_cycles", 30));
        // VERIFY 진입 판정의 d 는 최근 N 주기 이동평균 — 순간 판독 트리거는 관측 잡음이
        // 아래로 출렁이는 순간 조기 종료를 만든다(공차+잡음폭 만큼의 종방향 잔차 실측).
        // 1 이면 종전 순간 판정과 동일.
        trigger_avg_cycles_ = static_cast<int>(declare_parameter<int64_t>("trigger_avg_cycles", 5));
        // 검증 잔차가 횡·각은 공차 안인데 d 만 남는 경우, 후퇴(reapproach) 대신
        // 제자리에서 잔차만큼 저속 재접근(크립)한다 — 공차-트리거가 남기는 종방향
        // 잔차를 측정 잡음 바닥까지 조이는 단계. 후진 방향 크립(过도달)도 지원.
        creep_enable_ = declare_parameter<bool>("creep_enable", true);
        creep_tol_mm_ = declare_parameter<double>("creep_tol_mm", 2.0);
        creep_v_mps_ = declare_parameter<double>("creep_v_mps", 0.015);
        creep_max_mm_ = declare_parameter<double>("creep_max_mm", 80.0);
        creep_attempts_ = static_cast<int>(declare_parameter<int64_t>("creep_attempts", 2));

        arm_m_ = declare_parameter<double>("arm_m", 0.6039);
    }

    // ── 액션 수락 ───────────────────────────────────────────────────────────────
    rclcpp_action::GoalResponse onGoal(const DockAction::Goal &g)
    {
        if (active_goal_)
        {
            RCLCPP_WARN(get_logger(), "이미 도킹 진행 중 — goal 거부");
            return rclcpp_action::GoalResponse::REJECT;
        }
        if (!(g.max_speed_mps > 0.0) || !(g.tol_d_mm > 0.0) || !(g.tol_lat_mm > 0.0) ||
            !(g.tol_yaw_deg > 0.0))
        {
            RCLCPP_ERROR(get_logger(), "goal 파라미터 무효(속도·허용오차는 양수)");
            return rclcpp_action::GoalResponse::REJECT;
        }
        if (!select_client_->service_is_ready())
        {
            RCLCPP_ERROR(get_logger(), "/select_motion_source 미가용 — goal 거부");
            return rclcpp_action::GoalResponse::REJECT;
        }
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }

    void onAccepted(const std::shared_ptr<GoalHandle> &gh)
    {
        active_goal_ = gh;
        const auto &g = *gh->get_goal();
        target_ = {g.target_x_m, g.target_y_m, g.target_yaw_deg * kDegToRad};
        approach_axis_rad_ = g.approach_axis_deg * kDegToRad;
        timeout_s_ = (g.timeout_s > 0.0) ? g.timeout_s : default_timeout_s_;

        phase_ = kPreYaw;
        settle_until_.reset();
        spin_ready_ = false;
        // 슬루 필터 초기값 — 무정지 진입 계약(출구속도=goal 속도)에 맞춰 goal 속도에서
        // 시작해야 이어받는 첫 지령이 연속이다. settle 경로로 빠지면 정지 시작이므로 0.
        v_slew_ = skip_settle_if_aligned_ ? g.max_speed_mps : 0.0;
        yaw_stuck_ = 0;
        reapproach_count_ = 0;
        verify_left_ = 0;
        verify_acc_ = {};
        dist_state_ = {};
        e_d_prev_.reset();
        d_trig_hist_.clear();
        creep_mode_ = false;
        creep_count_ = 0;
        yaw_accum_ = {};
        stale_since_.reset();
        have_steer_ = false;
        start_time_ = now();

        // 사전 대기(armed) — 게이트 도달까지 mux 를 뺏지 않는다. 0 이면 즉시 인수.
        arm_engage_dist_m_ = get_parameter("arm_engage_dist_m").as_double();
        armed_ = arm_engage_dist_m_ > 0.0;
        mux_ok_ = false;
        if (!armed_)
        {
            requestMux();
        }
        else
        {
            RCLCPP_INFO(get_logger(), "armed — 잔거리 %.2f m 이내에서 mux 인수 예정",
                        arm_engage_dist_m_);
        }
        RCLCPP_INFO(get_logger(),
                    "도킹 시작 — 목표 (%.3f, %.3f, %.1f°) 접근축 %.0f° 허용 (%.0f/%.0f mm, %.1f°)",
                    target_.x_m, target_.y_m, target_.yaw_rad / kDegToRad,
                    approach_axis_rad_ / kDegToRad, g.tol_d_mm, g.tol_lat_mm, g.tol_yaw_deg);
    }

    // ── 제어 루프 ───────────────────────────────────────────────────────────────
    void onTick()
    {
        if (!active_goal_)
        {
            return;
        }
        const auto gh = active_goal_;
        const auto &g = *gh->get_goal();

        if (gh->is_canceling())
        {
            finish(4 /*PREEMPT*/, false, "취소");
            return;
        }
        const double elapsed = (now() - start_time_).seconds();
        if (elapsed > timeout_s_)
        {
            finish(1 /*TIMEOUT*/, false, "시간 초과");
            return;
        }

        // 사전 대기(armed) — 주행 액션이 몰고 오는 동안 관측만 보다가 게이트 진입
        // 순간 mux 를 인수한다. 대기 중에는 지령·정지 아무것도 내지 않는다.
        if (armed_)
        {
            geometry_msgs::msg::PoseStamped ap;
            rclcpp::Time at;
            {
                std::lock_guard<std::mutex> lk(pose_mtx_);
                if (!last_pose_)
                {
                    return;
                }
                ap = *last_pose_;
                at = last_pose_time_;
            }
            if ((now() - at).seconds() > obs_max_age_s_)
            {
                return;
            }
            const double ayaw = 2.0 * std::atan2(ap.pose.orientation.z, ap.pose.orientation.w);
            const dock_control::StationPose acur{ap.pose.position.x, ap.pose.position.y, ayaw};
            const auto aobs = dock_control::wallPoseToDockObs(acur, target_, approach_axis_rad_);
            // 인수 거리는 설정값과 «실측 진입속도의 제동거리+여유» 중 큰 쪽 — 게이트가
            // 짧아도 목표를 지나치지 않는 지점에서 이어받는다 (v²/2a + 0.2 m)
            double engage = arm_engage_dist_m_;
            if (approach_decel_mps2_ > 0.0)
            {
                const double vb = last_bus_speed_.load();
                engage = std::max(engage, vb * vb / (2.0 * approach_decel_mps2_) + 0.2);
            }
            if (!aobs.valid || std::fabs(aobs.e_d_m) > engage)
            {
                return;
            }
            armed_ = false;
            requestMux();
            // 슬루 시작점 = 인수 직전 버스 실측 지령속도(주행 순항이 goal 상한보다
            // 높으면 그 값부터 0.3 m/s² 로 내려온다)
            v_slew_ = std::max(g.max_speed_mps, last_bus_speed_.load());
            RCLCPP_INFO(get_logger(), "게이트 진입(잔거리 %.3f m, 버스 %.2f m/s) — mux 인수",
                        aobs.e_d_m, last_bus_speed_.load());
        }

        // mux 승인 확인 — 승인 전에는 지령을 내지 않는다(다른 소스가 활성일 수 있다)
        if (!mux_ok_)
        {
            if (mux_future_.valid() &&
                mux_future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
            {
                const auto res = mux_future_.get();
                if (!res->success)
                {
                    RCLCPP_ERROR(get_logger(), "mux 전환 거부: %s", res->message.c_str());
                    finish(5 /*MUX_DENIED*/, false, res->message);
                    return;
                }
                mux_ok_ = true;
            }
            else if ((now() - mux_req_time_).seconds() > 2.0)
            {
                finish(5 /*MUX_DENIED*/, false, "mux 응답 없음");
                return;
            }
            else
            {
                return;
            }
        }

        // 관측 취득 + 신선도 게이트
        geometry_msgs::msg::PoseStamped pose;
        rclcpp::Time pose_time;
        {
            std::lock_guard<std::mutex> lk(pose_mtx_);
            if (!last_pose_)
            {
                holdStill();
                return;
            }
            pose = *last_pose_;
            pose_time = last_pose_time_;
        }
        const double age = (now() - pose_time).seconds();
        if (age > obs_max_age_s_)
        {
            // 유예 동안 steer-hold 정지 — 관측 복귀를 기다린다 (returnHomeAbort 의 대기 규약)
            if (!stale_since_)
            {
                stale_since_ = now();
            }
            if ((now() - *stale_since_).seconds() > obs_grace_s_)
            {
                finish(2 /*OBS_LOST*/, false, "관측 유실");
                return;
            }
            holdStill();
            return;
        }
        stale_since_.reset();

        const double yaw = 2.0 * std::atan2(pose.pose.orientation.z, pose.pose.orientation.w);
        const dock_control::StationPose cur{pose.pose.position.x, pose.pose.position.y, yaw};
        const auto obs = dock_control::wallPoseToDockObs(cur, target_, approach_axis_rad_);
        if (!obs.valid)
        {
            holdStill();
            return;
        }

        // yaw runaway — 시작 이후 누적 회전이 상한을 넘으면 무조건 정지 (최후 방어선)
        dock_control::imuAccumStep(yaw_accum_, yaw);
        if (dock_control::imuRunaway(yaw_accum_, runaway_yaw_deg_))
        {
            finish(3 /*YAW_RUNAWAY*/, false, "yaw 폭주");
            return;
        }

        const double tol_d = g.tol_d_mm * 1e-3;
        const double tol_lat = g.tol_lat_mm * 1e-3;
        const double dt = 1.0 / control_rate_hz_;
        dock_control::DockWheelCommand cmd;  // 기본 0 — holdSteer 로 채운다

        // 전방 전이(kPreYaw→kPreAlign→kApproach)는 같은 틱 안에서 재실행해 지령을
        // 이어간다 — 전이 틱마다 기본 0 이 나가면 무정지 전환에 지령 공백이 생긴다.
        bool rerun = true;
        while (rerun)
        {
        rerun = false;
        switch (phase_)
        {
        case kPreYaw:
        {
            if (std::fabs(obs.e_yaw_deg) <= 0.7 * g.tol_yaw_deg)
            {
                if (skip_settle_if_aligned_ && !spin_ready_)
                {
                    // 무정지 전환: 스핀을 거치지 않은 정렬 진입 — 조향이 이미
                    // 접근축이므로 정착 대기 없이 바로 접근한다 (스핀 경유 시
                    // 조향이 ±90° 라 이 분기에 들어오지 않는다)
                    phase_ = kPreAlign;
                    rerun = true;
                    break;
                }
                // 접근 조향으로 되돌리며 정착 — 정착 전 전진하면 ±90° 잔류 조향이 쓸린다
                if (!settle_until_)
                {
                    settle_until_ = now() + rclcpp::Duration::from_seconds(settle_s_);
                }
                cmd.af = dock_control::wrapPm180(approach_axis_rad_ / kDegToRad) * kDegToRad;
                cmd.ar = cmd.af;
                if (now() >= *settle_until_)
                {
                    settle_until_.reset();
                    phase_ = kPreAlign;
                }
                break;
            }
            if (!spin_ready_)
            {
                // 스핀 자세(±90°) 정착 대기 — settle-then-drive
                if (!settle_until_)
                {
                    settle_until_ = now() + rclcpp::Duration::from_seconds(settle_s_);
                }
                cmd.af = M_PI / 2.0;
                cmd.ar = -M_PI / 2.0;
                if (now() >= *settle_until_)
                {
                    settle_until_.reset();
                    spin_ready_ = true;
                }
                break;
            }
            // 제자리 회전: 전 +90°/후 −90°, 같은 부호 속도 = ω·arm (플랜트 순기구학 역)
            double w_dps = std::clamp(spin_kp_dps_per_deg_ * obs.e_yaw_deg, -spin_w_max_dps_,
                                      spin_w_max_dps_);
            if (std::fabs(w_dps) < spin_w_min_dps_)
            {
                w_dps = std::copysign(spin_w_min_dps_, w_dps);
            }
            const double v_wheel = w_dps * kDegToRad * arm_m_;
            cmd.af = M_PI / 2.0;
            cmd.ar = -M_PI / 2.0;
            cmd.vf = v_wheel;
            cmd.vr = v_wheel;
            break;
        }
        case kPreAlign:
        {
            const double need = dock_control::geomEntryTranslateNeed(
                obs.e_lat_m, obs.e_d_m, delta_max_rad_, tol_lat);
            if (need <= 0.0)
            {
                phase_ = kApproach;
                rerun = true;
                break;
            }
            // 도크면과 평행(접근축 직교) crab — 접근 여유를 잠식하지 않고 수평만 줄인다
            const double steer =
                dock_control::wrapPm180((approach_axis_rad_ / kDegToRad) +
                                        std::copysign(90.0, obs.e_lat_m)) *
                kDegToRad;
            const double v = std::min(prealign_kp_ * std::fabs(obs.e_lat_m), prealign_v_max_);
            cmd = dock_control::composePhase4Wheels(v, steer, 0.0, 1.0, arm_m_);
            break;
        }
        case kApproach:
        {
            // 트리거 판정용 d 이동평균 — 제어(PID)는 순간값, 종료 판정만 평균값
            d_trig_hist_.push_back(obs.e_d_m);
            while (static_cast<int>(d_trig_hist_.size()) > std::max(1, trigger_avg_cycles_))
            {
                d_trig_hist_.pop_front();
            }
            double d_trig = 0.0;
            for (double v : d_trig_hist_)
            {
                d_trig += v;
            }
            d_trig /= static_cast<double>(d_trig_hist_.size());
            // 크립 중에는 내부 목표를 좁혀 잔차를 더 조인다 (성공 판정은 goal 공차 그대로)
            const double tol_d_eff = creep_mode_ ? creep_tol_mm_ * 1e-3 : tol_d;
            // 완료 후보 → VERIFY 진입
            if (std::fabs(d_trig) <= tol_d_eff && std::fabs(obs.e_lat_m) <= tol_lat &&
                std::fabs(obs.e_yaw_deg) <= g.tol_yaw_deg)
            {
                phase_ = kVerify;
                verify_left_ = verify_cycles_;
                verify_acc_ = {};
                break;
            }
            // 행 방지 — d·lat 만 수렴하고 yaw 미달이 지속되면 VERIFY 로 넘겨 정직하게
            // 판정한다(yaw 권한은 v 에 비례하므로 정지 근방에서는 더 기다려도 안 좋아진다)
            if (std::fabs(d_trig) <= tol_d_eff && std::fabs(obs.e_lat_m) <= tol_lat)
            {
                if (++yaw_stuck_ >= approach_stuck_cycles_)
                {
                    RCLCPP_WARN(get_logger(), "yaw 만 미달(%.2f°) 지속 — VERIFY 로 판정 이관",
                                obs.e_yaw_deg);
                    phase_ = kVerify;
                    verify_left_ = verify_cycles_;
                    verify_acc_ = {};
                    yaw_stuck_ = 0;
                    break;
                }
            }
            else
            {
                yaw_stuck_ = 0;
            }
            const double e_prev_val = e_d_prev_.value_or(0.0);
            const auto pid = dock_control::distPidStep(
                obs.e_d_m, e_d_prev_ ? &e_prev_val : nullptr, obs.e_d_m, dt, dist_state_,
                dist_gains_, g.max_speed_mps, dist_limits_);
            e_d_prev_ = obs.e_d_m;
            double v =
                dock_control::phase4Vcap(pid.u, obs.e_d_m, near_zone_m_, v_near_mps_);
            if (creep_mode_)
            {
                v = std::clamp(v, -creep_v_mps_, creep_v_mps_);
            }
            if (approach_decel_mps2_ > 0.0)
            {
                // 속도 절벽 방지 — 지령 감소를 감속률로 제한 (증가·역전은 즉시 허용:
                // near-zone 진입·크립 전환도 이 슬루를 타고 내려간다)
                v = std::max(v, v_slew_ - approach_decel_mps2_ * dt);
            }
            v_slew_ = v;
            const double delta = dock_control::geomEntryDeltaBiased(
                obs.e_lat_m, obs.e_d_m, delta_max_rad_, entry_bias_rad_);
            const double steer = dock_control::wrapPm180(
                                     (approach_axis_rad_ + delta) / kDegToRad) *
                                 kDegToRad;
            cmd = dock_control::composePhase4Wheels(v, steer, 0.0, 1.0, arm_m_);
            // 자세 채널: 전/후 조향 분할 — ω ≈ v·δh·cos(steer)/arm. 후진 시 부호 반전.
            const double dh = std::clamp(yaw_split_kp_deg_per_deg_ * obs.e_yaw_deg,
                                         -yaw_split_max_deg_, yaw_split_max_deg_) *
                              kDegToRad * (v >= 0.0 ? 1.0 : -1.0);
            cmd.af += dh;
            cmd.ar -= dh;
            break;
        }
        case kVerify:
        {
            holdStill();  // 정지 유지하며 평균
            verify_acc_.d += obs.e_d_m;
            verify_acc_.lat += obs.e_lat_m;
            verify_acc_.yaw += obs.e_yaw_deg;
            ++verify_acc_.n;
            if (--verify_left_ > 0)
            {
                publishFeedback(obs, 0.0);
                return;
            }
            const double md = verify_acc_.d / verify_acc_.n;
            const double ml = verify_acc_.lat / verify_acc_.n;
            const double my = verify_acc_.yaw / verify_acc_.n;
            if (std::fabs(md) <= tol_d && std::fabs(ml) <= tol_lat &&
                std::fabs(my) <= g.tol_yaw_deg)
            {
                finish(0 /*OK*/, true, "완료");
                return;
            }
            // 횡·각은 공차 안이고 d 잔차만 소폭 남음 → 후퇴 없이 정밀 크립 재접근
            if (creep_enable_ && std::fabs(ml) <= tol_lat &&
                std::fabs(my) <= g.tol_yaw_deg &&
                std::fabs(md) <= creep_max_mm_ * 1e-3 && creep_count_ < creep_attempts_)
            {
                ++creep_count_;
                creep_mode_ = true;
                phase_ = kApproach;
                dist_state_ = {};
                e_d_prev_.reset();
                d_trig_hist_.clear();
                RCLCPP_INFO(get_logger(), "검증 잔차 d=%.1f mm — 정밀 크립 %d회차",
                            1e3 * md, creep_count_);
                break;
            }
            if (reapproach_count_ < max_reapproach_)
            {
                ++reapproach_count_;
                phase_ = kReapproach;
                RCLCPP_WARN(get_logger(),
                            "검증 미달(평균 d=%.1f lat=%.1f mm yaw=%.2f°) — 재접근 %d회차",
                            1e3 * md, 1e3 * ml, my, reapproach_count_);
                break;
            }
            finish(6 /*VERIFY_FAIL*/, false, "검증 미달");
            return;
        }
        case kReapproach:
        {
            // 접근축 후방으로 물러나 재진입 여유를 만든다
            if (obs.e_d_m >= reapproach_dist_m_)
            {
                phase_ = kApproach;
                dist_state_ = {};
                e_d_prev_.reset();
                d_trig_hist_.clear();
                creep_mode_ = false;  // 전체 재접근은 통상 속도·공차로
                break;
            }
            const double steer = dock_control::wrapPm180(approach_axis_rad_ / kDegToRad) *
                                 kDegToRad;
            cmd = dock_control::composePhase4Wheels(-reapproach_v_mps_, steer, 0.0, 1.0,
                                                    arm_m_);
            break;
        }
        }
        }

        publishCmd(cmd);
        publishFeedback(obs, cmd.vf);
    }

    // mux 인수 요청 — 응답은 onTick 의 승인 확인 블록이 mux_req_time_ 기준으로 본다
    void requestMux()
    {
        auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
        req->source_id = mux_source_id_;
        mux_future_ = select_client_->async_send_request(req).future.share();
        mux_req_time_ = now();
    }

    // ── 지령·정지·종료 ─────────────────────────────────────────────────────────
    void publishCmd(const dock_control::DockWheelCommand &c)
    {
        trnav_msgs::msg::WheelSetArray msg;
        msg.header.stamp = now();
        msg.wheels.resize(2);
        msg.wheels[0].velocity = c.vf;
        msg.wheels[0].steering = c.af;
        msg.wheels[1].velocity = c.vr;
        msg.wheels[1].steering = c.ar;
        cmd_pub_->publish(msg);
        last_af_ = c.af;
        last_ar_ = c.ar;
        have_steer_ = true;
    }

    /// steer-hold 정지 — 마지막 조향을 유지한 채 속도 0. 조향 0 복귀 금지(코어 규약).
    void holdStill()
    {
        dock_control::DockWheelCommand c;
        if (have_steer_)
        {
            c.af = last_af_;
            c.ar = last_ar_;
        }
        publishCmd(c);
    }

    void publishFeedback(const dock_control::DockObservation &obs, double v)
    {
        auto fb = std::make_shared<DockAction::Feedback>();
        fb->phase = static_cast<int8_t>(phase_);
        fb->e_d_mm = 1e3 * obs.e_d_m;
        fb->e_lat_mm = 1e3 * obs.e_lat_m;
        fb->e_yaw_deg = obs.e_yaw_deg;
        fb->cmd_speed_mps = v;
        active_goal_->publish_feedback(fb);
    }

    void finish(int8_t reason, bool success, const std::string &why)
    {
        // 규약: 정지 지령 → mux 원복 → 액션 종결. 원복 실패는 로그만(정지는 이미 냈다).
        holdStill();
        auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
        req->source_id = mux_restore_id_;
        select_client_->async_send_request(req);

        auto res = std::make_shared<DockAction::Result>();
        res->success = success;
        res->stop_reason = reason;
        res->elapsed_s = (now() - start_time_).seconds();
        {
            std::lock_guard<std::mutex> lk(pose_mtx_);
            if (last_pose_)
            {
                const double yaw = 2.0 * std::atan2(last_pose_->pose.orientation.z,
                                                    last_pose_->pose.orientation.w);
                const auto obs = dock_control::wallPoseToDockObs(
                    {last_pose_->pose.position.x, last_pose_->pose.position.y, yaw}, target_,
                    approach_axis_rad_);
                res->final_e_d_mm = 1e3 * obs.e_d_m;
                res->final_e_lat_mm = 1e3 * obs.e_lat_m;
                res->final_e_yaw_deg = obs.e_yaw_deg;
            }
        }
        if (success)
        {
            active_goal_->succeed(res);
            RCLCPP_INFO(get_logger(), "도킹 완료 (%.1fs) — d=%.1f lat=%.1f mm yaw=%.2f°",
                        res->elapsed_s, res->final_e_d_mm, res->final_e_lat_mm,
                        res->final_e_yaw_deg);
        }
        else if (active_goal_->is_canceling())
        {
            active_goal_->canceled(res);
            RCLCPP_WARN(get_logger(), "도킹 취소: %s", why.c_str());
        }
        else
        {
            active_goal_->abort(res);
            RCLCPP_ERROR(get_logger(), "도킹 중단(%d): %s", reason, why.c_str());
        }
        active_goal_.reset();
    }

    // ── 상태 ────────────────────────────────────────────────────────────────────
    struct VerifyAcc
    {
        double d{0.0}, lat{0.0}, yaw{0.0};
        int n{0};
    };

    double control_rate_hz_{30.0}, obs_max_age_s_{0.2}, obs_grace_s_{1.0};
    double default_timeout_s_{60.0}, runaway_yaw_deg_{15.0};
    uint8_t mux_source_id_{40}, mux_restore_id_{0};
    dock_control::PidGains dist_gains_;
    dock_control::PidLimits dist_limits_;
    double delta_max_rad_{0.0}, entry_bias_rad_{0.0};
    double yaw_split_kp_deg_per_deg_{0.3}, yaw_split_max_deg_{5.0};
    double spin_kp_dps_per_deg_{1.0}, spin_w_max_dps_{5.0}, spin_w_min_dps_{0.8};
    double settle_s_{2.0};
    bool skip_settle_if_aligned_{false};
    double approach_decel_mps2_{0.0};
    double v_slew_{0.0};
    double arm_engage_dist_m_{0.0};
    bool armed_{false};
    rclcpp::Time mux_req_time_;
    rclcpp::Subscription<trnav_msgs::msg::WheelSetArray>::SharedPtr bus_cmd_sub_;
    std::atomic<double> last_bus_speed_{0.0};
    int approach_stuck_cycles_{60};
    std::optional<rclcpp::Time> settle_until_;
    bool spin_ready_{false};
    int yaw_stuck_{0};
    double near_zone_m_{0.3}, v_near_mps_{0.03};
    double prealign_kp_{0.5}, prealign_v_max_{0.05};
    double reapproach_dist_m_{0.15}, reapproach_v_mps_{0.05};
    int max_reapproach_{1}, verify_cycles_{30};
    double arm_m_{0.6039};

    std::shared_ptr<GoalHandle> active_goal_;
    dock_control::DockTargetPose target_;
    double approach_axis_rad_{0.0}, timeout_s_{60.0};
    Phase phase_{kPreAlign};
    int reapproach_count_{0}, verify_left_{0};
    VerifyAcc verify_acc_;
    dock_control::PidState dist_state_;
    std::optional<double> e_d_prev_;
    int trigger_avg_cycles_{5};
    std::deque<double> d_trig_hist_;
    bool creep_enable_{true}, creep_mode_{false};
    double creep_tol_mm_{2.0}, creep_v_mps_{0.015}, creep_max_mm_{80.0};
    int creep_attempts_{2}, creep_count_{0};
    dock_control::ImuAccum yaw_accum_;
    std::optional<rclcpp::Time> stale_since_;
    rclcpp::Time start_time_;
    bool mux_ok_{false};
    std::shared_future<trnav_msgs::srv::SelectMotionSource::Response::SharedPtr> mux_future_;
    double last_af_{0.0}, last_ar_{0.0};
    bool have_steer_{false};

    std::mutex pose_mtx_;
    std::optional<geometry_msgs::msg::PoseStamped> last_pose_;
    rclcpp::Time last_pose_time_;

    rclcpp::Publisher<trnav_msgs::msg::WheelSetArray>::SharedPtr cmd_pub_;
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_client_;
    rclcpp_action::Server<DockAction>::SharedPtr action_server_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<DockApproachServer>());
    rclcpp::shutdown();
    return 0;
}
