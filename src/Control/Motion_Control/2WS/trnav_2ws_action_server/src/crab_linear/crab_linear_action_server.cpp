// CrabLinear pilot — target_yaw 능동 유지 + start↔end world-frame 직선 closed-loop 추종.
//
// 알고리즘 (PathController + LocalizationMonitor):
//   매 cycle: theta_body = atan2(end-start) - robot_yaw  (path 진행 방향을 body frame 으로 사영)
//             omega_cmd  = PD(target_yaw - robot_yaw)
//             VelocityCommand = {vx_profile * cos(theta_body),
//                                vx_profile * sin(theta_body),
//                                omega_cmd}
//             → DualSteerIK.compute(...) → wheel cmd
//   PathController 는 projection / e_d / e_theta 측정용 (CTE feedback). δ_f/δ_r 출력은 무시.
//   heading abort: |target_yaw - robot_yaw| > crab_linear_heading_threshold_deg → status=-4.

#include "trnav_2ws_action_server/crab_linear/crab_linear_action_server.hpp"
#include "trnav_2ws_core/velocity_ramp.hpp"

#include <chrono>
#include <thread>

#include "geometry_msgs/msg/pose_stamped.hpp"

namespace trnav_2ws_action_server::crab_linear
{

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using trnav::motion::two_ws::ControlMode;
using trnav::motion::two_ws::IKResult;
using trnav_2ws_core::LocalizationMonitor;
using PathController = trnav::motion::two_ws::TwoWsPathController;
using trnav_2ws_core::ProfilePhase;
using trnav_2ws_core::TransientGuard;
using trnav_2ws_core::TrapezoidalProfile;
using trnav::motion::two_ws::VelocityCommand;

CrabLinearActionServer::CrabLinearActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<CrabLinear>(
          node, std::move(action_mutex), "amr_motion_crab_linear_abstract",
          "/motion/wheel_cmd/crab_linear")
{
    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 4);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    // ── crab_linear-specific parameters ──
    // 5 게인 (Kp/Kd/K_stanley/K_soft/max_delta) 은 멤버 캐시 — params 콜백 핫리로드 시 사용.
    Kp_heading_ = safeParam("crab_linear_Kp_heading", 1.0);
    Kd_heading_ = safeParam("crab_linear_Kd_heading", 0.3);
    K_stanley_ = safeParam("crab_linear_K_stanley", 2.0);
    K_soft_ = safeParam("crab_linear_K_soft", 1.0);
    heading_threshold_deg_ = safeParam("crab_linear_heading_threshold_deg", 45.0);
    double max_lateral_offset = safeParam("crab_linear_max_lateral_offset", 1.0);
    int heading_filter_window = safeParam("crab_linear_heading_filter_window", 5);
    int cte_filter_window = safeParam("crab_linear_cte_filter_window", 5);
    max_delta_ = safeParam("crab_linear_max_delta_deg", 45.0) * M_PI / 180.0;

    goal_reach_threshold_ = safeParam("crab_linear_goal_reach_threshold", 0.05);
    min_vx_ = safeParam("crab_linear_min_vx", 0.02);
    behind_start_speed_ = safeParam("crab_linear_behind_start_speed", 0.2);
    max_timeout_sec_ = safeParam("crab_linear_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("crab_linear_enable_localization_watchdog", true);
    steer_rate_static_ = safeParam("crab_linear_steer_rate_static", 0.140);
    steer_rate_dynamic_ = safeParam("crab_linear_steer_rate_dynamic", 0.350);
    steer_rate_vx_threshold_ = safeParam("crab_linear_steer_rate_vx_threshold", 0.05);
    walk_accel_limit_ = safeParam("crab_linear_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("crab_linear_walk_decel_limit", 1.0);
    steer_converge_err_low_deg_ = safeParam("crab_linear_steer_converge_err_low_deg", 3.0);
    steer_converge_err_high_deg_ = safeParam("crab_linear_steer_converge_err_high_deg", 30.0);
    steer_converge_min_scale_ = safeParam("crab_linear_steer_converge_min_scale", 0.3);

    // ── PathController (projection / e_d / e_theta 측정용. δ_f/δ_r 출력은 무시) ──
    PathController::Params pc_params;
    pc_params.Kp_heading = Kp_heading_;
    pc_params.Kd_heading = Kd_heading_;
    pc_params.K_stanley = K_stanley_;
    pc_params.K_soft = K_soft_;
    pc_params.heading_threshold = heading_threshold_deg_ * M_PI / 180.0;
    pc_params.max_lateral_offset = max_lateral_offset;
    pc_params.heading_filter_window = heading_filter_window;
    pc_params.cte_filter_window = cte_filter_window;
    pc_params.mode = ControlMode::BICYCLE;
    pc_params.max_delta = max_delta_;
    path_ctrl_ = std::make_unique<PathController>(pc_params);

    // ── Crab IK (DualSteerIK 의 ±90° normalize edge 회피 — 양 휠 동일 steer 직접 출력) ──
    {
        const auto &geom = this->geometry();
        crab_ik_ = std::make_unique<trnav::motion::two_ws::TwoWsCrabIK>(
            geom.num_wheels, geom.wheel_radius, geom.gear_walk);
    }

    // ── TransientGuard ──
    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    double gate_thresh_deg = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_gate_threshold = gate_thresh_deg;
    double err_max_deg = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.steer_error_max = err_max_deg;
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    double runtime_gate_deg = safeParam("transient_runtime_gate_threshold_deg", 90.0);
    tg_params.runtime_gate_threshold = runtime_gate_deg;
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // ── LocalizationMonitor (TF-only) ──
    double loc_timeout = safeParam("crab_linear_localization_timeout_sec", 2.0);
    double jump_threshold = safeParam("crab_linear_position_jump_threshold", 0.3);

    LocalizationMonitor::Params lm_params;
    lm_params.localization_timeout_sec = loc_timeout;
    lm_params.position_jump_threshold = jump_threshold;
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // ── Extra publishers ──
    path_viz_pub_ =
        node_->create_publisher<nav_msgs::msg::Path>("crab_linear_path", rclcpp::QoS(10).transient_local());
    debug_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>("crab_linear_debug", rclcpp::QoS(10));

    // Initialize wheel state time
    last_wheel_state_time_ = std::chrono::steady_clock::now();

    RCLCPP_INFO(node_->get_logger(),
                "CrabLinearActionServer initialized (loc_watchdog=%s, heading_threshold=%.1f deg)",
                enable_localization_watchdog_ ? "ON" : "OFF", heading_threshold_deg_);

    // ── Hot-reload param callback (PathController 5 게인 한정) ──
    // 화이트리스트: crab_linear_Kp_heading / Kd_heading / K_stanley / K_soft / max_delta_deg.
    // Kp/Kd 는 자체 omega PD 식 (omega = Kp*yaw_err + Kd*de_yaw) 에도 사용됨 — 멤버 갱신으로 동시 반영.
    params_cb_handle_ = node_->add_on_set_parameters_callback(
        [this](const std::vector<rclcpp::Parameter> &params) -> rcl_interfaces::msg::SetParametersResult {
            rcl_interfaces::msg::SetParametersResult result;
            result.successful = true;
            bool touched = false;
            for (const auto &p : params)
            {
                const std::string &name = p.get_name();
                if (p.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE)
                {
                    continue;
                }
                const double v = p.as_double();
                if (name == "crab_linear_Kp_heading")
                {
                    if (v < 0.0 || v > 5.0)
                    {
                        result.successful = false;
                        result.reason = "crab_linear_Kp_heading out of range [0, 5]";
                        return result;
                    }
                    Kp_heading_ = v;
                    touched = true;
                }
                else if (name == "crab_linear_Kd_heading")
                {
                    if (v < 0.0 || v > 2.0)
                    {
                        result.successful = false;
                        result.reason = "crab_linear_Kd_heading out of range [0, 2]";
                        return result;
                    }
                    Kd_heading_ = v;
                    touched = true;
                }
                else if (name == "crab_linear_K_stanley")
                {
                    if (v < 0.0 || v > 10.0)
                    {
                        result.successful = false;
                        result.reason = "crab_linear_K_stanley out of range [0, 10]";
                        return result;
                    }
                    K_stanley_ = v;
                    touched = true;
                }
                else if (name == "crab_linear_K_soft")
                {
                    if (v < 0.1 || v > 5.0)
                    {
                        result.successful = false;
                        result.reason = "crab_linear_K_soft out of range [0.1, 5]";
                        return result;
                    }
                    K_soft_ = v;
                    touched = true;
                }
                else if (name == "crab_linear_max_delta_deg")
                {
                    if (v < 10.0 || v > 90.0)
                    {
                        result.successful = false;
                        result.reason = "crab_linear_max_delta_deg out of range [10, 90]";
                        return result;
                    }
                    max_delta_ = v * M_PI / 180.0;
                    touched = true;
                }
            }
            if (touched && path_ctrl_)
            {
                path_ctrl_->setGains(Kp_heading_, Kd_heading_, K_stanley_, K_soft_, max_delta_);
                RCLCPP_INFO(node_->get_logger(),
                            "CrabLinear gains hot-reloaded: Kp_h=%.3f Kd_h=%.3f K_st=%.3f K_so=%.3f "
                            "max_delta=%.1f deg",
                            Kp_heading_, Kd_heading_, K_stanley_, K_soft_, max_delta_ * 180.0 / M_PI);
            }
            return result;
        });
}

// ════════════════════════════════════════════════════════
//  wheelStateCallback override: base + timestamp tracking
// ════════════════════════════════════════════════════════

void CrabLinearActionServer::wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg)
{
    trnav::motion::two_ws::TwoWsActionServerBase<CrabLinear>::wheelStateCallback(msg);
    wheel_state_received_.store(true);
    {
        std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
        last_wheel_state_time_ = std::chrono::steady_clock::now();
    }
}

bool CrabLinearActionServer::validateGoal(std::shared_ptr<const CrabLinear::Goal> goal)
{
    double dx = goal->end_x - goal->start_x;
    double dy = goal->end_y - goal->start_y;
    double dist = std::hypot(dx, dy);
    if (dist < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "CrabLinear rejected: start == end");
        return false;
    }
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "CrabLinear rejected: max_linear_speed <= 0");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "CrabLinear rejected: acceleration <= 0");
        return false;
    }
    if (goal->entry_speed < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "CrabLinear rejected: entry_speed < 0");
        return false;
    }
    if (!goal->hold_steer && (goal->exit_steer_angle < -90.0 || goal->exit_steer_angle > 90.0))
    {
        RCLCPP_WARN(node_->get_logger(), "CrabLinear rejected: exit_steer_angle out of [-90, +90]");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "CrabLinear goal accepted: (%.2f,%.2f)->(%.2f,%.2f), dist=%.3f m, target_yaw=%.1f deg, v_max=%.2f m/s",
                goal->start_x, goal->start_y, goal->end_x, goal->end_y, dist, goal->target_yaw_deg,
                goal->max_linear_speed);
    return true;
}

// ════════════════════════════════════════════════════════
//  Main execute loop
// ════════════════════════════════════════════════════════

void CrabLinearActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
{
    ActionMutexGuard mutex_guard(action_mutex_);

    // ── mux active source 전환 (정공법: action server 자체 책임) ──
    if (select_source_client_ && select_source_client_->service_is_ready())
    {
        auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
        req->source_id = static_cast<uint8_t>(motion_source_id_);
        auto future = select_source_client_->async_send_request(req);
        if (future.wait_for(std::chrono::milliseconds(500)) == std::future_status::ready)
        {
            auto resp = future.get();
            if (!resp->success)
                RCLCPP_WARN(node_->get_logger(),
                            "CrabLinear: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "CrabLinear: mux active source → %d (crab_linear)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "CrabLinear: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "CrabLinear: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<CrabLinear::Feedback>();
    auto result = std::make_shared<CrabLinear::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

    const double target_yaw_rad = goal->target_yaw_deg * M_PI / 180.0;
    const double heading_threshold_rad = heading_threshold_deg_ * M_PI / 180.0;

    // Helper: yaw error in [-π, π]
    auto wrap_pi = [](double a) {
        while (a > M_PI)
            a -= 2.0 * M_PI;
        while (a < -M_PI)
            a += 2.0 * M_PI;
        return a;
    };

    // Helper: abort/cancel with cleanup
    auto finish_abort = [&](int8_t status, double actual_dist, double lat_err, double head_err,
                            const rclcpp::Time &start_time) {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
        max_cmd_speed_.store(0.0);
        loc_monitor_->setMaxCmdSpeed(0.0);
        {
            nav_msgs::msg::Path empty;
            empty.header.frame_id = "map";
            empty.header.stamp = node_->now();
            path_viz_pub_->publish(empty);
        }
        result->status = status;
        this->reportResult(status); // 종료 코드 토픽 발행 (bag 기록용)
        result->actual_distance = actual_dist;
        result->final_lateral_error = lat_err;
        result->final_heading_error = head_err;
        result->elapsed_time = (node_->now() - start_time).seconds();
        if (status == -1)
        {
            goal_handle->canceled(result);
        }
        else
        {
            goal_handle->abort(result);
        }
    };

    auto start_time = node_->now();

    // ── Setup path ──
    if (goal->entry_speed <= 0.0)
    {
        path_ctrl_->reset();
        guard_->reset();
    }

    path_ctrl_->setMode(ControlMode::BICYCLE);
    path_ctrl_->setPath(goal->start_x, goal->start_y, goal->end_x, goal->end_y);

    double target_distance = path_ctrl_->targetDistance();
    const double path_yaw = path_ctrl_->pathAngle();

    RCLCPP_INFO(node_->get_logger(),
                "CrabLinear execute: path_angle=%.1f deg, target_dist=%.3f m, target_yaw=%.1f deg",
                path_yaw * 180.0 / M_PI, target_distance, goal->target_yaw_deg);

    // Publish path for visualization
    {
        nav_msgs::msg::Path path_msg;
        path_msg.header.frame_id = "map";
        path_msg.header.stamp = node_->now();
        geometry_msgs::msg::PoseStamped ps0, ps1;
        ps0.pose.position.x = goal->start_x;
        ps0.pose.position.y = goal->start_y;
        ps0.pose.orientation.w = 1.0;
        ps1.pose.position.x = goal->end_x;
        ps1.pose.position.y = goal->end_y;
        ps1.pose.orientation.w = 1.0;
        path_msg.poses = {ps0, ps1};
        path_viz_pub_->publish(path_msg);
    }

    // ── IMU receive check ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting crab_linear");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── Initial pose from tf2 map->base_link ──
    double robot_x = 0.0, robot_y = 0.0, robot_yaw = 0.0;
    if (!loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
    {
        RCLCPP_ERROR(node_->get_logger(), "/robot_pose 미수신 또는 낡음(신선도 초과) — TF 문제가 아니다. 측위 발행자와 pose_topic 결속을 확인하라. aborting crab_linear");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // 초기 heading 검사 — target_yaw 와 현재 yaw 차이가 임계 초과 시 즉시 abort
    {
        double init_yaw_err = wrap_pi(target_yaw_rad - robot_yaw);
        if (std::abs(init_yaw_err) > heading_threshold_rad)
        {
            RCLCPP_WARN(node_->get_logger(),
                        "CrabLinear initial heading error %.2f deg > threshold %.1f deg, abort",
                        init_yaw_err * 180.0 / M_PI, heading_threshold_deg_);
            finish_abort(-2, 0.0, 0.0, init_yaw_err * 180.0 / M_PI, start_time);
            return;
        }
    }

    // ── Phase 0: Steer Align (entry_speed <= 0.0 일 때만 실행) ──
    // target_yaw 유지 상태에서 path 진행 방향으로 steer 정렬.
    if (goal->entry_speed <= 0.0)
    {
        double theta_body0 = wrap_pi(path_yaw - robot_yaw);
        VelocityCommand align_cmd{std::cos(theta_body0) * 0.1, std::sin(theta_body0) * 0.1, 0.0};
        auto ik_align = ik_->compute(align_cmd);
        const double align_steer_f = ik_align.wheels[0].steer_rad;
        const double align_steer_r = ik_align.wheels[1].steer_rad;

        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(),
                    "CrabLinear Phase 0: steer alignment (theta_body=%.1f deg, F=%.1f R=%.1f deg)",
                    theta_body0 * 180.0 / M_PI, align_steer_f * 180.0 / M_PI, align_steer_r * 180.0 / M_PI);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "CrabLinear cancelled during Phase 0");
                finish_abort(-1, 0.0, 0.0, 0.0, start_time);
                return;
            }

            publishWheelCmd(0.0, align_steer_f, 0.0, align_steer_r);

            feedback->current_distance = 0.0;
            feedback->current_lateral_error = 0.0;
            feedback->current_heading_error = 0.0;
            feedback->current_vx = 0.0;
            feedback->current_vy = 0.0;
            feedback->current_omega = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - align_steer_f) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - align_steer_r) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
            {
                break;
            }

            if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "CrabLinear Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }

            rate.sleep();
        }

        RCLCPP_INFO(node_->get_logger(), "CrabLinear Phase 0 complete, starting trapezoidal profile");

        // ── state-aware: Phase 0 가 결정한 wheel steer + walk dir 를 TwoWsCrabIK 에 저장.
        // cruise (Phase 1-3) 의 crab_ik_->compute() 가 본 state 기준 ±25° clamp + dir 고정 →
        // Phase 0 의 부호 결정 그대로 유지. boundary wrap 충돌 회피.
        crab_ik_->setInitial(align_steer_f, ik_align.wheels[0].direction);
        RCLCPP_INFO(node_->get_logger(),
                    "CrabLinear Phase 0 → TwoWsCrabIK setInitial(steer=%.1f deg, dir=%d)",
                    align_steer_f * 180.0 / M_PI, ik_align.wheels[0].direction);
    }

    // Steer rate limiter state
    double prev_cmd_steer_f = last_angle_front_.load();
    double prev_cmd_steer_r = last_angle_rear_.load();

    double prev_cmd_vel_f = (goal->entry_speed > 0.0) ? goal->entry_speed : 0.0;
    double prev_cmd_vel_r = (goal->entry_speed > 0.0) ? goal->entry_speed : 0.0;

    // PD heading 상태 (rear-steer offset)
    double prev_yaw_err = wrap_pi(target_yaw_rad - robot_yaw);

    // ── Phase 1-3: Trapezoidal profile + PathController(CTE) + target_yaw PD + TransientGuard ──
    double exit_speed = goal->exit_speed;
    TrapezoidalProfile profile(target_distance, goal->max_linear_speed, goal->acceleration, exit_speed,
                               goal->entry_speed);

    bool reached = false;
    int tf_fail_count = 0;
    const int tf_fail_max = 50;

    while (rclcpp::ok() && !reached)
    {
        if (loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
        {
            tf_fail_count = 0;
        }
        else
        {
            tf_fail_count++;
            if (tf_fail_count >= tf_fail_max)
            {
                auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
                RCLCPP_ERROR(node_->get_logger(), "TF2 lookup failed %d consecutive times at dist=%.3f m",
                             tf_fail_count, pc_out.projection);
                finish_abort(-6, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
                return;
            }
        }

        if (goal_handle->is_canceling())
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            RCLCPP_INFO(node_->get_logger(), "CrabLinear cancelled at dist=%.3f m", pc_out.projection);
            finish_abort(-1, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            RCLCPP_WARN(node_->get_logger(), "CrabLinear global timeout (%.1f s), dist=%.3f m", max_timeout_sec_,
                        pc_out.projection);
            finish_abort(-3, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if (enable_localization_watchdog_ && !loc_monitor_->checkLocalizationHealth())
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            auto reason = loc_monitor_->getLastFailReason();
            int8_t code = -4;
            const char *reason_str = "TIMEOUT";
            if (reason == trnav_2ws_core::LocalizationMonitor::HealthFailReason::JUMP)
            {
                code = -5;
                reason_str = "JUMP";
            }
            else if (reason == trnav_2ws_core::LocalizationMonitor::HealthFailReason::TF_LOOKUP_FAIL)
            {
                code = -6;
                reason_str = "TF_LOOKUP_FAIL";
            }
            RCLCPP_ERROR(node_->get_logger(), "Localization health fail (%s, code=%d) at dist=%.3f m", reason_str, code,
                         pc_out.projection);
            finish_abort(code, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        // target_yaw heading abort 검사
        double yaw_err = wrap_pi(target_yaw_rad - robot_yaw);
        if (std::abs(yaw_err) > heading_threshold_rad)
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            RCLCPP_WARN(node_->get_logger(),
                        "CrabLinear heading abort: yaw_err=%.2f deg > threshold %.1f deg at dist=%.3f m",
                        yaw_err * 180.0 / M_PI, heading_threshold_deg_, pc_out.projection);
            finish_abort(-4, pc_out.projection, pc_out.e_d, yaw_err * 180.0 / M_PI, start_time);
            return;
        }

        double rx = robot_x - goal->start_x;
        double ry = robot_y - goal->start_y;
        double projection = rx * std::cos(path_yaw) + ry * std::sin(path_yaw);

        double remaining = target_distance - projection;
        double clamped_projection = std::max(0.0, projection);
        auto prof_out = profile.getSpeed(clamped_projection);
        double vx_profile = prof_out.speed;
        max_cmd_speed_.store(vx_profile);
        loc_monitor_->setMaxCmdSpeed(vx_profile);

        if (projection < 0.0)
        {
            vx_profile = behind_start_speed_;
        }
        else if (prof_out.phase == ProfilePhase::ACCEL && vx_profile < behind_start_speed_)
        {
            vx_profile = behind_start_speed_;
        }

        bool near_goal = (remaining < goal_reach_threshold_);
        if (prof_out.phase != ProfilePhase::DONE && !near_goal && vx_profile < min_vx_)
        {
            vx_profile = min_vx_;
        }

        if (prof_out.phase == ProfilePhase::DONE || projection >= target_distance)
        {
            reached = true;
            if (goal->exit_speed > 0.0)
            {
                RCLCPP_INFO(node_->get_logger(), "CrabLinear reached with velocity continuity (exit_speed=%.3f)",
                            goal->exit_speed);
            }
            else
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            }
            break;
        }

        // PathController update (CTE 측정용 — projection / e_d / e_theta 만 사용)
        auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, vx_profile, dt);

        // ── crab_linear 명령 계산 ──
        // theta_body = path 진행 방향 - robot_yaw (body frame 으로 사영)
        double theta_body = wrap_pi(path_yaw - robot_yaw);

        // CTE 보정 (Stanley):
        //   PathController.update() 의 e_d → δ_cte = atan2(K_stanley × e_d, K_soft + |vx|)
        double delta_cte = std::atan2(K_stanley_ * pc_out.e_d, K_soft_ + std::abs(vx_profile));

        // Heading 보정 (rear-steer offset, 2026-05-25):
        //   δ_heading = Kp × yaw_err + Kd × de_yaw, saturate ±15°
        //   TwoWsCrabIK 가 rear wheel 만 (-dir × δ_heading) offset 적용 → yaw 능동 보정
        double de_yaw = (yaw_err - prev_yaw_err) / dt;
        prev_yaw_err = yaw_err;
        double delta_heading_raw = Kp_heading_ * yaw_err + Kd_heading_ * de_yaw;
        const double heading_sat = 15.0 * M_PI / 180.0;
        double delta_heading = std::clamp(delta_heading_raw, -heading_sat, heading_sat);

        auto ik_expected = crab_ik_->compute(vx_profile, theta_body, delta_cte, delta_heading);

        double vy_for_guard = 0.0;
        double omega_for_guard = 0.0;
        double expected_steer_f = ik_expected.wheels[0].steer_rad;
        double expected_steer_r = ik_expected.wheels[1].steer_rad;

        // Steer rate limit
        double cmd_steer_f = expected_steer_f;
        double cmd_steer_r = expected_steer_r;
        {
            double active_rate =
                (std::fabs(vx_profile) > steer_rate_vx_threshold_) ? steer_rate_dynamic_ : steer_rate_static_;
            double max_step = active_rate * dt;
            double diff_f = expected_steer_f - prev_cmd_steer_f;
            double diff_r = expected_steer_r - prev_cmd_steer_r;
            if (std::fabs(diff_f) > max_step)
                cmd_steer_f = prev_cmd_steer_f + std::copysign(max_step, diff_f);
            if (std::fabs(diff_r) > max_step)
                cmd_steer_r = prev_cmd_steer_r + std::copysign(max_step, diff_r);
            prev_cmd_steer_f = cmd_steer_f;
            prev_cmd_steer_r = cmd_steer_r;
        }

        // Steer convergence velocity scaling
        double steer_converge_scale = 1.0;
        {
            double target_err_f = std::abs(last_angle_front_.load() - cmd_steer_f) * 180.0 / M_PI;
            double target_err_r = std::abs(last_angle_rear_.load() - cmd_steer_r) * 180.0 / M_PI;
            double max_target_err = std::max(target_err_f, target_err_r);
            if (max_target_err > steer_converge_err_high_deg_)
            {
                steer_converge_scale = steer_converge_min_scale_;
            }
            else if (max_target_err > steer_converge_err_low_deg_)
            {
                steer_converge_scale = 1.0 - (1.0 - steer_converge_min_scale_) *
                                                 (max_target_err - steer_converge_err_low_deg_) /
                                                 (steer_converge_err_high_deg_ - steer_converge_err_low_deg_);
            }
        }

        double steer_err_front = std::abs(last_angle_front_.load() - cmd_steer_f) * 180.0 / M_PI;
        double steer_err_rear = std::abs(last_angle_rear_.load() - cmd_steer_r) * 180.0 / M_PI;
        double max_steer_err = std::max(steer_err_front, steer_err_rear);

        TransientGuard::GuardInput guard_input;
        guard_input.vy_cmd = vy_for_guard;
        guard_input.omega_cmd = omega_for_guard;
        guard_input.steer_error_deg = max_steer_err;
        guard_input.is_phase0 = false;

        auto guard_out = guard_->apply(guard_input);

        double speed_scale = guard_out.gate_blocked ? 0.0 : guard_out.drive_scale;
        speed_scale *= steer_converge_scale;
        double cmd_vx = vx_profile * speed_scale;
        double cmd_vy = guard_out.vy_limited;
        double cmd_omega = guard_out.omega_limited;

        // ── Actual-steer-based IK for wheel speed ──
        IKResult ik_for_speed = ik_expected;
        {
            bool feedback_fresh = true;
            {
                std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
                double ws_age =
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - last_wheel_state_time_).count();
                if (!wheel_state_received_.load() || ws_age > 0.2)
                {
                    feedback_fresh = false;
                }
            }

            if (feedback_fresh)
            {
                // actual steer 기준 wheel speed 재계산 (translate 패턴과 동일 의도 — IK 출력 일관)
                ik_for_speed = crab_ik_->compute(vx_profile, theta_body, delta_cte, delta_heading);
            }
        }

        double vel_f = ik_for_speed.wheels[0].wheel_speed * ik_for_speed.wheels[0].direction * speed_scale;
        double vel_r = ik_for_speed.wheels[1].wheel_speed * ik_for_speed.wheels[1].direction * speed_scale;

        // Walk velocity profile
        {
            double acc_step = walk_accel_limit_ * dt;
            double dec_step = walk_decel_limit_ * dt;
            // 지역 사본을 폐기하고 공용 `trnav_2ws_core::rampToward` 를 쓴다.
            // 「가속」은 `tgt > cur` 이 아니라 `|tgt| > |cur|` 이다 — 부호 있는 비교는 음수
            // 지령 구간에서 가·감속 한계를 뒤바꾼다. 이 서버는 **후방 크랩**(θ_body 90~270°)에서
            // `direction = -1` 이 되어 램프 입력이 음수가 되므로 실제로 도달하는 경로였다
            // (cur=-3.15 → tgt=-4.15 에서 한 번에 1.0 = **감속한계로 가속**. 정상은 0.5).
            vel_f = trnav_2ws_core::rampToward(prev_cmd_vel_f, vel_f, acc_step, dec_step);
            vel_r = trnav_2ws_core::rampToward(prev_cmd_vel_r, vel_r, acc_step, dec_step);
            prev_cmd_vel_f = vel_f;
            prev_cmd_vel_r = vel_r;
        }

        double fb_w1_rpm = ik_for_speed.wheels[0].drive_rpm * speed_scale;
        double fb_w2_rpm = ik_for_speed.wheels[1].drive_rpm * speed_scale;

        publishWheelCmd(vel_f, cmd_steer_f, vel_r, cmd_steer_r);

        // Debug log (~10 Hz at 50Hz rate)
        static int dbg_cnt = 0;
        if (++dbg_cnt % 5 == 0)
        {
            RCLCPP_INFO(node_->get_logger(),
                        "[CrabLinear] steer: F=%.1f/%.1f° R=%.1f/%.1f° err=%.1f° %s | "
                        "vx=%.3f vy=%.3f omega=%.3f proj=%.3fm lat=%.3fm yaw_err=%.1f°",
                        last_angle_front_.load() * 180.0 / M_PI, cmd_steer_f * 180.0 / M_PI,
                        last_angle_rear_.load() * 180.0 / M_PI, cmd_steer_r * 180.0 / M_PI, max_steer_err,
                        guard_out.gate_blocked ? "BLOCKED" : "OK", cmd_vx, cmd_vy, cmd_omega, pc_out.projection,
                        pc_out.e_d, yaw_err * 180.0 / M_PI);
        }

        // Debug topic
        {
            std_msgs::msg::Float64MultiArray dbg_msg;
            dbg_msg.data = {pc_out.e_d,
                            pc_out.e_theta * 180.0 / M_PI,
                            pc_out.projection,
                            theta_body * 180.0 / M_PI,
                            yaw_err * 180.0 / M_PI,
                            cmd_vx,
                            cmd_vy,
                            cmd_omega,
                            last_angle_front_.load(),
                            last_angle_rear_.load(),
                            cmd_steer_f,
                            cmd_steer_r,
                            vel_f,
                            vel_r,
                            speed_scale,
                            steer_converge_scale};
            debug_pub_->publish(dbg_msg);
        }

        uint8_t phase_id;
        switch (prof_out.phase)
        {
        case ProfilePhase::ACCEL:
            phase_id = 1;
            break;
        case ProfilePhase::CRUISE:
            phase_id = 2;
            break;
        case ProfilePhase::DECEL:
            phase_id = 3;
            break;
        default:
            phase_id = 3;
            break;
        }
        feedback->phase = phase_id;
        feedback->current_distance = pc_out.projection;
        feedback->current_lateral_error = pc_out.e_d;
        feedback->current_heading_error = yaw_err * 180.0 / M_PI;
        feedback->current_vx = cmd_vx;
        feedback->current_vy = cmd_vy;
        feedback->current_omega = cmd_omega;
        feedback->w1_drive_rpm = fb_w1_rpm;
        feedback->w2_drive_rpm = fb_w2_rpm;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // Stop driving
    if (goal->exit_speed <= 0.0)
    {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
    }
    max_cmd_speed_.store(goal->exit_speed > 0.0 ? goal->exit_speed : 0.0);
    loc_monitor_->setMaxCmdSpeed(max_cmd_speed_.load());

    // Read final state
    loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw);
    auto final_pc = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
    double final_yaw_err = wrap_pi(target_yaw_rad - robot_yaw);

    RCLCPP_INFO(node_->get_logger(),
                "CrabLinear Phase 1-3 complete: dist=%.3f m, lat_err=%.4f m, yaw_err=%.2f deg",
                final_pc.projection, final_pc.e_d, final_yaw_err * 180.0 / M_PI);

    // Cancel check after Phase 1-3
    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "CrabLinear cancelled after Phase 1-3");
        finish_abort(-1, final_pc.projection, final_pc.e_d, final_yaw_err * 180.0 / M_PI, start_time);
        return;
    }

    // ── Phase 4: Steer Return (if !hold_steer) ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "CrabLinear Phase 4: steer return to %.1f deg", goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "CrabLinear cancelled during Phase 4");
                finish_abort(-1, final_pc.projection, final_pc.e_d, final_yaw_err * 180.0 / M_PI, start_time);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);

            feedback->current_distance = final_pc.projection;
            feedback->current_lateral_error = final_pc.e_d;
            feedback->current_heading_error = final_yaw_err * 180.0 / M_PI;
            feedback->current_vx = 0.0;
            feedback->current_vy = 0.0;
            feedback->current_omega = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - exit_steer_rad) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - exit_steer_rad) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
            {
                break;
            }

            if ((node_->now() - phase4_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "CrabLinear Phase 4 steer timeout (non-critical)");
                break;
            }

            rate.sleep();
        }
    }

    // Clear path visualization on completion
    {
        nav_msgs::msg::Path empty;
        empty.header.frame_id = "map";
        empty.header.stamp = node_->now();
        path_viz_pub_->publish(empty);
    }

    // ── Success ──
    result->status = 0;
    this->reportResult(0); // 종료 코드 토픽 발행 (bag 기록용)
    result->actual_distance = final_pc.projection;
    result->final_lateral_error = final_pc.e_d;
    result->final_heading_error = final_yaw_err * 180.0 / M_PI;
    result->elapsed_time = (node_->now() - start_time).seconds();

    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(),
                "CrabLinear complete: dist=%.3f/%.3f m, lat_err=%.4f m, yaw_err=%.2f deg, time=%.1f s",
                final_pc.projection, target_distance, final_pc.e_d, final_yaw_err * 180.0 / M_PI,
                result->elapsed_time);
}

} // namespace trnav_2ws_action_server::crab_linear
