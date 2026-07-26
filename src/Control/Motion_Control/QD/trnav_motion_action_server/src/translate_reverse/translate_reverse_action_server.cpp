#include "trnav_motion_action_server/translate_reverse/translate_reverse_action_server.hpp"

#include <chrono>
#include <thread>

#include "trnav_motion_core/math_utils.hpp" // normalizeAngle (effective_yaw 보정)
#include "geometry_msgs/msg/pose_stamped.hpp"

namespace trnav_motion_action_server::translate_reverse
{

using trnav_motion_core::ActionMutex;
using trnav_motion_core::ActionMutexGuard;
using BicycleModel = trnav::motion::qd::QdBicycleModel;
using trnav::motion::qd::ControlMode;
using trnav::motion::qd::DualBicycleCommand;
using trnav::motion::qd::IKResult;
using trnav_motion_core::LocalizationMonitor;
using PathController = trnav::motion::qd::QdPathController;
using trnav_motion_core::ProfilePhase;
using trnav_motion_core::TransientGuard;
using trnav_motion_core::TrapezoidalProfile;
using trnav::motion::qd::TravelDirection;
using trnav::motion::qd::WheelPosition;

TranslateReverseActionServer::TranslateReverseActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::qd::QdActionServerBase<Translate>(
          node, std::move(action_mutex), "amr_motion_translate_reverse_abstract", "/motion/wheel_cmd/translate_reverse")
{
    // ── IK parameters (needed for BicycleModel wheelbase) ──
    double w1_x = safeParam("w1_x", 0.330);
    double w1_y = safeParam("w1_y", 0.135);
    double w2_x = safeParam("w2_x", -0.330);
    double w2_y = safeParam("w2_y", -0.135);

    std::vector<WheelPosition> wheels = {{w1_x, w1_y}, {w2_x, w2_y}};
    bicycle_model_ = std::make_unique<BicycleModel>(wheels);

    // mux active source — 부팅 시 supervisor 가 forward(=1) 로만 set. reverse 진입 시 자체 전환 필수.
    // execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임 — 어디서 호출하든 일관).
    motion_source_id_ = safeParam("motion_source_id", 2);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    // ── Translate-specific parameters (same yaml keys as forward) ──
    // 5 게인은 멤버 캐시 — params 콜백 핫리로드 시 사용.
    Kp_heading_ = safeParam("translate_Kp_heading", 1.0);
    Kd_heading_ = safeParam("translate_Kd_heading", 0.3);
    K_stanley_ = safeParam("translate_K_stanley", 2.0);
    K_soft_ = safeParam("translate_K_soft", 1.0);
    double heading_threshold_deg = safeParam("translate_heading_threshold_deg", 90.0);
    double max_lateral_offset = safeParam("translate_max_lateral_offset", 1.0);
    int heading_filter_window = safeParam("translate_heading_filter_window", 5);
    int cte_filter_window = safeParam("translate_cte_filter_window", 5);
    goal_reach_threshold_ = safeParam("translate_goal_reach_threshold", 0.05);
    min_vx_ = safeParam("translate_min_vx", 0.02);
    behind_start_speed_ = safeParam("translate_behind_start_speed", 0.2);
    vy_ramp_time_ = safeParam("translate_vy_ramp_time", 1.0);
    max_timeout_sec_ = safeParam("translate_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("translate_enable_localization_watchdog", true);
    steer_rate_static_ = safeParam("translate_steer_rate_static", 0.140);
    steer_rate_dynamic_ = safeParam("translate_steer_rate_dynamic", 0.350);
    steer_rate_vx_threshold_ = safeParam("translate_steer_rate_vx_threshold", 0.05);
    walk_accel_limit_ = safeParam("translate_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("translate_walk_decel_limit", 1.0);
    {
        int mode_int = safeParam("translate_control_mode", 1);
        (void)mode_int;
        default_mode_ = ControlMode::BICYCLE;
    }
    max_delta_ = safeParam("translate_max_delta_deg", 45.0) * M_PI / 180.0;
    steer_converge_err_low_deg_ = safeParam("translate_steer_converge_err_low_deg", 3.0);
    steer_converge_err_high_deg_ = safeParam("translate_steer_converge_err_high_deg", 30.0);
    steer_converge_min_scale_ = safeParam("translate_steer_converge_min_scale", 0.3);

    // ── PathController ──
    PathController::Params pc_params;
    pc_params.Kp_heading = Kp_heading_;
    pc_params.Kd_heading = Kd_heading_;
    pc_params.K_stanley = K_stanley_;
    pc_params.K_soft = K_soft_;
    pc_params.heading_threshold = heading_threshold_deg * M_PI / 180.0;
    pc_params.max_lateral_offset = max_lateral_offset;
    pc_params.heading_filter_window = heading_filter_window;
    pc_params.cte_filter_window = cte_filter_window;
    pc_params.mode = default_mode_;
    pc_params.max_delta = max_delta_;
    path_ctrl_ = std::make_unique<PathController>(pc_params);
    wheelbase_ = std::fabs(w1_x - w2_x);

    // ── TransientGuard ──
    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // ── LocalizationMonitor (TF-only, topic 폐기 2026-05-18) ──
    double loc_timeout = safeParam("translate_localization_timeout_sec", 2.0);
    double jump_threshold = safeParam("translate_position_jump_threshold", 0.3);

    LocalizationMonitor::Params lm_params;
    lm_params.localization_timeout_sec = loc_timeout;
    lm_params.position_jump_threshold = jump_threshold;
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // ── Extra publishers (reverse 전용 토픽) ──
    path_viz_pub_ =
        node_->create_publisher<nav_msgs::msg::Path>("translate_reverse_path", rclcpp::QoS(10).transient_local());
    debug_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>("translate_reverse_debug", rclcpp::QoS(10));

    last_wheel_state_time_ = std::chrono::steady_clock::now();

    RCLCPP_INFO(
        node_->get_logger(),
        "TranslateReverseActionServer initialized (TF-only, loc_watchdog=%s, mode=BICYCLE/REVERSE)",
        enable_localization_watchdog_ ? "ON" : "OFF");

    // ── Hot-reload param callback (PathController 5 게인, forward 와 동일 정책) ──
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
                if (name == "translate_Kp_heading")
                {
                    if (v < 0.0 || v > 5.0)
                    {
                        result.successful = false;
                        result.reason = "translate_Kp_heading out of range [0, 5]";
                        return result;
                    }
                    Kp_heading_ = v;
                    touched = true;
                }
                else if (name == "translate_Kd_heading")
                {
                    if (v < 0.0 || v > 2.0)
                    {
                        result.successful = false;
                        result.reason = "translate_Kd_heading out of range [0, 2]";
                        return result;
                    }
                    Kd_heading_ = v;
                    touched = true;
                }
                else if (name == "translate_K_stanley")
                {
                    if (v < 0.0 || v > 10.0)
                    {
                        result.successful = false;
                        result.reason = "translate_K_stanley out of range [0, 10]";
                        return result;
                    }
                    K_stanley_ = v;
                    touched = true;
                }
                else if (name == "translate_K_soft")
                {
                    if (v < 0.1 || v > 5.0)
                    {
                        result.successful = false;
                        result.reason = "translate_K_soft out of range [0.1, 5]";
                        return result;
                    }
                    K_soft_ = v;
                    touched = true;
                }
                else if (name == "translate_max_delta_deg")
                {
                    if (v < 10.0 || v > 90.0)
                    {
                        result.successful = false;
                        result.reason = "translate_max_delta_deg out of range [10, 90]";
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
                            "Translate(reverse) gains hot-reloaded: Kp_h=%.3f Kd_h=%.3f K_st=%.3f K_so=%.3f "
                            "max_delta=%.1f deg",
                            Kp_heading_, Kd_heading_, K_stanley_, K_soft_, max_delta_ * 180.0 / M_PI);
            }
            return result;
        });
}

// ════════════════════════════════════════════════════════
//  wheelStateCallback override
// ════════════════════════════════════════════════════════

void TranslateReverseActionServer::wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg)
{
    trnav::motion::qd::QdActionServerBase<Translate>::wheelStateCallback(msg);
    wheel_state_received_.store(true);
    {
        std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
        last_wheel_state_time_ = std::chrono::steady_clock::now();
    }
}

bool TranslateReverseActionServer::validateGoal(std::shared_ptr<const Translate::Goal> goal)
{
    double dx = goal->end_x - goal->start_x;
    double dy = goal->end_y - goal->start_y;
    double dist = std::hypot(dx, dy);
    if (dist < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: start == end");
        return false;
    }
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: max_linear_speed <= 0 (magnitude)");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: acceleration <= 0");
        return false;
    }
    if (goal->entry_speed < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: entry_speed < 0 (magnitude)");
        return false;
    }
    if (!goal->hold_steer && (goal->exit_steer_angle < -90.0 || goal->exit_steer_angle > 90.0))
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: exit_steer_angle out of [-90, +90]");
        return false;
    }
    if (goal->control_mode != 0 && goal->control_mode != 1)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateReverse rejected: control_mode=%u 미지원 (BICYCLE=1 만 지원)",
                    goal->control_mode);
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "TranslateReverse goal accepted: (%.2f,%.2f)->(%.2f,%.2f), dist=%.3f m, v_max=%.2f m/s (magnitude)",
                goal->start_x, goal->start_y, goal->end_x, goal->end_y, dist, goal->max_linear_speed);
    return true;
}

// ════════════════════════════════════════════════════════
//  Main execute loop (BICYCLE / REVERSE)
//  - effective_yaw = real_yaw + π (lookupMapToBase 직후 보정)
//  - PathController 호출 시 TravelDirection::REVERSE 명시
//  - DualBicycleCommand 입력 vx 는 양수 (forward kinematics)
//  - wheel velocity 출력 부호 반전 (vel_f *= -1, vel_r *= -1)
//  - feedback current_vx 부호 반전 (음수)
// ════════════════════════════════════════════════════════

void TranslateReverseActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
{
    ActionMutexGuard mutex_guard(action_mutex_);

    // ── mux active source 전환 (정공법: action server 자체 책임) ──
    // 부팅 시 supervisor 가 source=1(forward) 로만 set 했으므로, reverse 명령 통과시키려면
    // 본 노드가 자기 source_id=2 로 mux 를 전환해야 함. 어떤 클라이언트 (ACS GUI / script / 외부)
    // 가 호출하든 일관성 보장.
    if (select_source_client_ && select_source_client_->service_is_ready())
    {
        auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
        req->source_id = static_cast<uint8_t>(motion_source_id_);
        auto future = select_source_client_->async_send_request(req);
        if (future.wait_for(std::chrono::milliseconds(500)) == std::future_status::ready)
        {
            auto resp = future.get();
            if (!resp->success)
            {
                RCLCPP_WARN(node_->get_logger(),
                            "TranslateReverse: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            }
            else
            {
                RCLCPP_INFO(node_->get_logger(),
                            "TranslateReverse: mux active source → %d (translate_reverse)",
                            motion_source_id_);
            }
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "TranslateReverse: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "TranslateReverse: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<Translate::Feedback>();
    auto result = std::make_shared<Translate::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

    // reverse 시 출력 부호 반전 상수
    constexpr double kReverseDir = -1.0;
    constexpr TravelDirection kDir = TravelDirection::REVERSE;

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
        this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
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

    if (goal->entry_speed <= 0.0)
    {
        path_ctrl_->reset();
        guard_->reset();
    }

    ControlMode local_mode = ControlMode::BICYCLE;
    path_ctrl_->setMode(local_mode);

    RCLCPP_INFO(node_->get_logger(), "TranslateReverse control_mode=BICYCLE/REVERSE (goal.control_mode=%u)",
                goal->control_mode);

    path_ctrl_->setPath(goal->start_x, goal->start_y, goal->end_x, goal->end_y);

    double target_distance = path_ctrl_->targetDistance();

    RCLCPP_INFO(node_->get_logger(), "TranslateReverse execute: path_angle=%.1f deg, target_dist=%.3f m",
                path_ctrl_->pathAngle() * 180.0 / M_PI, target_distance);

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

    // ── IMU receive check (위치는 TF lookupMapToBase 가 처리) ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting translate_reverse");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    double robot_x = 0.0, robot_y = 0.0, robot_yaw = 0.0;
    if (!loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
    {
        RCLCPP_ERROR(node_->get_logger(), "TF2 map->base_link not available, aborting translate_reverse");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }
    // reverse: effective_yaw = real_yaw + π (PathController 가 forward 처럼 처리)
    robot_yaw = trnav_motion_core::normalizeAngle(robot_yaw + M_PI);

    // skip_initial_pose_check(=acs_gui on_position_mismatch='none') 시 생략 — 경로 밖 시작 허용 (운영자 위치 책임, 2026-06-19).
    if (goal->skip_initial_pose_check)
    {
        RCLCPP_WARN(node_->get_logger(),
                    "TranslateReverse: skip_initial_pose_check=true → validateInitialPose 생략");
    }
    else
    {
        int validate_result = path_ctrl_->validateInitialPose(robot_x, robot_y, robot_yaw);
        if (validate_result != 0)
        {
            RCLCPP_WARN(
                node_->get_logger(),
                "TranslateReverse initial pose validation failed (code=%d): robot=(%.2f,%.2f, effective_yaw=%.1f deg)",
                validate_result, robot_x, robot_y, robot_yaw * 180.0 / M_PI);
            finish_abort(-2, 0.0, 0.0, 0.0, start_time);
            return;
        }
    }

    // ── Phase 0: Steer Align ──
    if (goal->entry_speed <= 0.0)
    {
        const double forward_steer_f = last_angle_front_.load();
        const double forward_steer_r = last_angle_rear_.load();

        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "TranslateReverse Phase 0: steer alignment (target F=%.1f R=%.1f deg)",
                    forward_steer_f * 180.0 / M_PI, forward_steer_r * 180.0 / M_PI);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "TranslateReverse cancelled during Phase 0");
                finish_abort(-1, 0.0, 0.0, 0.0, start_time);
                return;
            }

            publishWheelCmd(0.0, forward_steer_f, 0.0, forward_steer_r);

            feedback->current_distance = 0.0;
            feedback->current_lateral_error = 0.0;
            feedback->current_heading_error = 0.0;
            feedback->current_vx = 0.0;
            feedback->current_vy = 0.0;
            feedback->current_omega = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - forward_steer_f) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - forward_steer_r) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
            {
                break;
            }

            if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "TranslateReverse Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }

            rate.sleep();
        }

        RCLCPP_INFO(node_->get_logger(), "TranslateReverse Phase 0 complete, starting trapezoidal profile");
    }

    double prev_cmd_steer_f = last_angle_front_.load();
    double prev_cmd_steer_r = last_angle_rear_.load();

    double prev_cmd_vel_f = (goal->entry_speed > 0.0) ? -goal->entry_speed : 0.0; // reverse 부호 반전
    double prev_cmd_vel_r = (goal->entry_speed > 0.0) ? -goal->entry_speed : 0.0;

    // ── Phase 1-3 ──
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
            robot_yaw = trnav_motion_core::normalizeAngle(robot_yaw + M_PI); // effective_yaw
            tf_fail_count = 0;
        }
        else
        {
            tf_fail_count++;
            if (tf_fail_count >= tf_fail_max)
            {
                auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt, kDir);
                RCLCPP_ERROR(node_->get_logger(), "TF2 lookup failed %d consecutive times at dist=%.3f m",
                             tf_fail_count, pc_out.projection);
                finish_abort(-6, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
                return;
            }
        }

        if (goal_handle->is_canceling())
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt, kDir);
            RCLCPP_INFO(node_->get_logger(), "TranslateReverse cancelled at dist=%.3f m", pc_out.projection);
            finish_abort(-1, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt, kDir);
            RCLCPP_WARN(node_->get_logger(), "TranslateReverse global timeout (%.1f s), dist=%.3f m", max_timeout_sec_,
                        pc_out.projection);
            finish_abort(-3, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if (enable_localization_watchdog_ && !loc_monitor_->checkLocalizationHealth())
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt, kDir);
            auto reason = loc_monitor_->getLastFailReason();
            int8_t code = -4;
            const char *reason_str = "TIMEOUT";
            if (reason == trnav_motion_core::LocalizationMonitor::HealthFailReason::JUMP)
            {
                code = -5;
                reason_str = "JUMP";
            }
            else if (reason == trnav_motion_core::LocalizationMonitor::HealthFailReason::TF_LOOKUP_FAIL)
            {
                code = -6;
                reason_str = "TF_LOOKUP_FAIL";
            }
            RCLCPP_ERROR(node_->get_logger(), "Localization health fail (%s, code=%d) at dist=%.3f m", reason_str, code,
                         pc_out.projection);
            finish_abort(code, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        double rx = robot_x - goal->start_x;
        double ry = robot_y - goal->start_y;
        double projection = rx * std::cos(path_ctrl_->pathAngle()) + ry * std::sin(path_ctrl_->pathAngle());

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
                RCLCPP_INFO(node_->get_logger(), "TranslateReverse reached with velocity continuity (exit_speed=%.3f)",
                            goal->exit_speed);
            }
            else
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            }
            break;
        }

        auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, vx_profile, dt, kDir);

        IKResult ik_expected;
        double vy_for_guard, omega_for_guard;

        // BICYCLE forward kinematics (양수 vx) — wheel 출력에서만 부호 반전
        {
            DualBicycleCommand dual_cmd{vx_profile, pc_out.delta_f, pc_out.delta_r};
            auto vel_cmd = bicycle_model_->toVelocityCommand(dual_cmd);
            double body_speed = std::hypot(vel_cmd.vx, vel_cmd.vy);
            if (body_speed > 1e-6)
            {
                double scale = vx_profile / body_speed;
                vel_cmd.vx *= scale;
                vel_cmd.vy *= scale;
                vel_cmd.omega *= scale;
            }
            vy_for_guard = vel_cmd.vy;
            omega_for_guard = vel_cmd.omega;
            ik_expected = ik_->compute(vel_cmd);
        }
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
        // feedback current_vx: reverse 시 음수 발행
        // Body-frame 부호 일관: 모두 kReverseDir(-1) 곱 → reverse 시 음수.
        // path-frame(forward kin 기준) → body-frame: vy/omega 도 vx 와 동일하게 반전.
        double cmd_vx = vx_profile * speed_scale * kReverseDir;
        double cmd_vy = guard_out.vy_limited * kReverseDir;
        double cmd_omega = guard_out.omega_limited * kReverseDir;

        // Actual-steer-based IK (forward kinematics)
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
                double actual_f = last_angle_front_.load();
                double actual_r = last_angle_rear_.load();
                DualBicycleCommand actual_cmd{vx_profile, actual_f, actual_r};
                auto actual_vel = bicycle_model_->toVelocityCommand(actual_cmd);
                double actual_body = std::hypot(actual_vel.vx, actual_vel.vy);
                if (actual_body > 1e-6)
                {
                    double s = vx_profile / actual_body;
                    actual_vel.vx *= s;
                    actual_vel.vy *= s;
                    actual_vel.omega *= s;
                }
                ik_for_speed = ik_->compute(actual_vel);
            }
        }

        // Wheel output: forward-IK 결과 * speed_scale * kReverseDir (-1)
        double vel_f =
            ik_for_speed.wheels[0].wheel_speed * ik_for_speed.wheels[0].direction * speed_scale * kReverseDir;
        double vel_r =
            ik_for_speed.wheels[1].wheel_speed * ik_for_speed.wheels[1].direction * speed_scale * kReverseDir;

        {
            double acc_step = walk_accel_limit_ * dt;
            double dec_step = walk_decel_limit_ * dt;
            // Magnitude-based: |tgt|>|cur| → accel (a_step), |tgt|<|cur| → decel (d_step).
            // 부호 비교(forward 전용) 는 reverse(tgt<0) 에서 a/d step 매핑이 뒤집혀
            // walk_accel ≠ walk_decel 이면 가·감속 비대칭이 발생.
            auto velProfile = [](double cur, double tgt, double a_step, double d_step) -> double {
                if (std::fabs(tgt) < 0.01)
                {
                    if (cur > d_step)
                        return cur - d_step;
                    if (cur < -d_step)
                        return cur + d_step;
                    return tgt;
                }
                if (tgt * cur < 0.0)
                {
                    // 부호 반전 — 일단 0 으로 감속
                    if (cur > d_step)
                        return cur - d_step;
                    if (cur < -d_step)
                        return cur + d_step;
                    return 0.0;
                }
                const double abs_cur = std::fabs(cur);
                const double abs_tgt = std::fabs(tgt);
                const double sign = (tgt >= 0.0) ? 1.0 : -1.0;
                if (abs_tgt > abs_cur)
                    return sign * std::fmin(abs_tgt, abs_cur + a_step);
                if (abs_tgt < abs_cur)
                    return sign * std::fmax(abs_tgt, abs_cur - d_step);
                return tgt;
            };
            vel_f = velProfile(prev_cmd_vel_f, vel_f, acc_step, dec_step);
            vel_r = velProfile(prev_cmd_vel_r, vel_r, acc_step, dec_step);
            prev_cmd_vel_f = vel_f;
            prev_cmd_vel_r = vel_r;
        }

        double fb_w1_rpm = ik_for_speed.wheels[0].drive_rpm * speed_scale * kReverseDir;
        double fb_w2_rpm = ik_for_speed.wheels[1].drive_rpm * speed_scale * kReverseDir;

        publishWheelCmd(vel_f, cmd_steer_f, vel_r, cmd_steer_r);

        static int dbg_cnt = 0;
        if (++dbg_cnt % 5 == 0)
        {
            RCLCPP_INFO(node_->get_logger(),
                        "[TranslateReverse] S%d steer: F=%.1f/%.1f° R=%.1f/%.1f° err=%.1f° %s | "
                        "vx=%.3f vy=%.4f omega=%.4f proj=%.3fm lat=%.3fm hdg=%.1f°",
                        pc_out.control_stage, last_angle_front_.load() * 180.0 / M_PI, cmd_steer_f * 180.0 / M_PI,
                        last_angle_rear_.load() * 180.0 / M_PI, cmd_steer_r * 180.0 / M_PI, max_steer_err,
                        guard_out.gate_blocked ? "BLOCKED" : "OK", cmd_vx, pc_out.vy, pc_out.omega, pc_out.projection,
                        pc_out.e_d, pc_out.e_theta * 180.0 / M_PI);
        }

        {
            std_msgs::msg::Float64MultiArray dbg_msg;
            dbg_msg.data = {pc_out.e_d,
                            pc_out.e_theta * 180.0 / M_PI,
                            pc_out.projection,
                            static_cast<double>(pc_out.control_stage),
                            pc_out.delta_f * 180.0 / M_PI,
                            pc_out.delta_r * 180.0 / M_PI,
                            cmd_vx,
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
        feedback->current_heading_error = pc_out.e_theta * 180.0 / M_PI;
        feedback->current_vx = cmd_vx; // reverse 시 음수
        feedback->current_vy = cmd_vy;
        feedback->current_omega = cmd_omega;
        feedback->w1_drive_rpm = fb_w1_rpm;
        feedback->w2_drive_rpm = fb_w2_rpm;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    if (goal->exit_speed <= 0.0)
    {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
    }
    max_cmd_speed_.store(goal->exit_speed > 0.0 ? goal->exit_speed : 0.0);
    loc_monitor_->setMaxCmdSpeed(max_cmd_speed_.load());

    loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw);
    robot_yaw = trnav_motion_core::normalizeAngle(robot_yaw + M_PI); // effective_yaw
    auto final_pc = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt, kDir);

    RCLCPP_INFO(node_->get_logger(),
                "TranslateReverse Phase 1-3 complete: dist=%.3f m, lat_err=%.4f m, head_err=%.2f deg",
                final_pc.projection, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI);

    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "TranslateReverse cancelled after Phase 1-3");
        finish_abort(-1, final_pc.projection, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI, start_time);
        return;
    }

    // ── Phase 4: Steer Return ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "TranslateReverse Phase 4: steer return to %.1f deg", goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "TranslateReverse cancelled during Phase 4");
                finish_abort(-1, final_pc.projection, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI, start_time);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);

            feedback->current_distance = final_pc.projection;
            feedback->current_lateral_error = final_pc.e_d;
            feedback->current_heading_error = final_pc.e_theta * 180.0 / M_PI;
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
                RCLCPP_WARN(node_->get_logger(), "TranslateReverse Phase 4 steer timeout (non-critical)");
                break;
            }

            rate.sleep();
        }
    }

    {
        nav_msgs::msg::Path empty;
        empty.header.frame_id = "map";
        empty.header.stamp = node_->now();
        path_viz_pub_->publish(empty);
    }

    result->status = 0;
    this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
    result->actual_distance = final_pc.projection;
    result->final_lateral_error = final_pc.e_d;
    result->final_heading_error = final_pc.e_theta * 180.0 / M_PI;
    result->elapsed_time = (node_->now() - start_time).seconds();

    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(),
                "TranslateReverse complete: dist=%.3f/%.3f m, lat_err=%.4f m, head_err=%.2f deg, time=%.1f s",
                final_pc.projection, target_distance, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI,
                result->elapsed_time);
}

} // namespace trnav_motion_action_server::translate_reverse
