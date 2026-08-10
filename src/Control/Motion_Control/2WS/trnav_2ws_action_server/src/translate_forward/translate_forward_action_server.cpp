#include "trnav_2ws_action_server/translate_forward/translate_forward_action_server.hpp"
#include "trnav_2ws_core/velocity_ramp.hpp"

#include <algorithm>
#include <chrono>
#include <thread>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "trnav_2ws_core/math_utils.hpp"

namespace trnav_2ws_action_server::translate_forward
{

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using BicycleModel = trnav::motion::two_ws::TwoWsBicycleModel;
using trnav::motion::two_ws::ControlMode;
using trnav::motion::two_ws::DualBicycleCommand;
using trnav::motion::two_ws::IKResult;
using trnav_2ws_core::LocalizationMonitor;
using PathController = trnav::motion::two_ws::TwoWsPathController;
using trnav_2ws_core::ProfilePhase;
using trnav_2ws_core::TransientGuard;
using trnav_2ws_core::TrapezoidalProfile;
using trnav::motion::two_ws::WheelPosition;

TranslateForwardActionServer::TranslateForwardActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<Translate>(
          node, std::move(action_mutex), "amr_motion_translate_forward_abstract", "/motion/wheel_cmd/translate_forward")
{
    // ── IK parameters (needed for BicycleModel wheelbase) ──
    // ⚠ 기본값은 이 기체(Foil_A082, 인라인 듀얼스티어 · y=0) 기준. QD 대각 기본값
    //    (±0.330, ±0.135)이 남아 있어 params 없이 띄우면 조용히 QD 기하로 풀렸다
    //    (2026-08-08 실증: spin 이 ±90° 대신 −67.75° 를 세워 187 mm 병진). 정본은 config/*_params.yaml.
    double w1_x = safeParam("w1_x", 0.6039);
    double w1_y = safeParam("w1_y", 0.0);
    double w2_x = safeParam("w2_x", -0.5961);
    double w2_y = safeParam("w2_y", 0.0);

    // BicycleModel (uses wheel positions)
    std::vector<WheelPosition> wheels = {{w1_x, w1_y}, {w2_x, w2_y}};
    bicycle_model_ = std::make_unique<BicycleModel>(wheels);

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 1);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    // ── Translate-specific parameters ──
    // 5 게인 (Kp/Kd/K_stanley/K_soft/max_delta) 은 멤버 캐시 — params 콜백에서 핫리로드 시 사용.
    Kp_heading_ = safeParam("translate_Kp_heading", 1.0);
    Kd_heading_ = safeParam("translate_Kd_heading", 0.3);
    K_stanley_ = safeParam("translate_K_stanley", 2.0);
    K_soft_ = safeParam("translate_K_soft", 1.0);
    double heading_threshold_deg = safeParam("translate_heading_threshold_deg", 45.0);
    double max_lateral_offset = safeParam("translate_max_lateral_offset", 1.0);
    int heading_filter_window = safeParam("translate_heading_filter_window", 5);
    int cte_filter_window = safeParam("translate_cte_filter_window", 5);
    goal_reach_threshold_ = safeParam("translate_goal_reach_threshold", 0.05);
    min_vx_ = safeParam("translate_min_vx", 0.02);
    behind_start_speed_ = safeParam("translate_behind_start_speed", 0.2);
    vy_ramp_time_ = safeParam("translate_vy_ramp_time", 1.0);
    max_timeout_sec_ = safeParam("translate_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("translate_enable_localization_watchdog", true);
    // heading yaw 소스: 0=robot_pose(기본) / 1=IMU(시작 RMA10 으로 map-frame offset 잡고 고정).
    //   x,y(CTE)는 항상 robot_pose. 실험용 A/B 토글 (실차 검증 전 기본 0 유지).
    heading_source_ = safeParam("translate_heading_source", 0);
    steer_rate_static_ = safeParam("translate_steer_rate_static", 0.140);
    steer_rate_dynamic_ = safeParam("translate_steer_rate_dynamic", 0.350);
    steer_rate_vx_threshold_ = safeParam("translate_steer_rate_vx_threshold", 0.05);
    walk_accel_limit_ = safeParam("translate_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("translate_walk_decel_limit", 1.0);
    // 종단 fine-positioning (exit_speed<=0 최종 정지 한정 creep closed-loop)
    fine_enter_dist_ = safeParam("translate_fine_enter_dist", 0.08);
    fine_tol_pos_ = safeParam("translate_fine_tol_pos", 0.02);
    fine_kp_ = safeParam("translate_fine_kp", 0.5);
    fine_v_max_ = safeParam("translate_fine_v_max", 0.04);
    fine_v_min_ = safeParam("translate_fine_v_min", 0.015);
    fine_timeout_ = safeParam("translate_fine_timeout", 5.0);
    {
        // BICYCLE 고정. Mode 2/3 등은 후속 Wave 에서 확장.
        int mode_int = safeParam("translate_control_mode", 1);
        (void)mode_int;
        default_mode_ = ControlMode::BICYCLE;
    }
    max_delta_ = safeParam("translate_max_delta_deg", 45.0) * M_PI / 180.0;
    steer_converge_err_low_deg_ = safeParam("translate_steer_converge_err_low_deg", 3.0);
    steer_converge_err_high_deg_ = safeParam("translate_steer_converge_err_high_deg", 30.0);
    steer_converge_min_scale_ = safeParam("translate_steer_converge_min_scale", 0.3);

    // ── PathController (BICYCLE-only Params) ──
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
    double gate_thresh_deg = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_gate_threshold = gate_thresh_deg;
    double err_max_deg = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.steer_error_max = err_max_deg;
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    double runtime_gate_deg = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    tg_params.runtime_gate_threshold = runtime_gate_deg;
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // ── LocalizationMonitor (TF-only, topic 폐기 2026-05-18) ──
    double loc_timeout = safeParam("translate_localization_timeout_sec", 2.0);
    double jump_threshold = safeParam("translate_position_jump_threshold", 0.3);

    LocalizationMonitor::Params lm_params;
    lm_params.localization_timeout_sec = loc_timeout;
    lm_params.position_jump_threshold = jump_threshold;
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // ── Extra publishers ──
    path_viz_pub_ =
        node_->create_publisher<nav_msgs::msg::Path>("translate_forward_path", rclcpp::QoS(10).transient_local());
    debug_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>("translate_forward_debug", rclcpp::QoS(10));

    // Initialize wheel state time
    last_wheel_state_time_ = std::chrono::steady_clock::now();

    RCLCPP_INFO(node_->get_logger(),
                "TranslateForwardActionServer initialized (TF-only, loc_watchdog=%s, mode=BICYCLE)",
                enable_localization_watchdog_ ? "ON" : "OFF");

    // ── Hot-reload param callback (PathController 5 게인 한정) ──
    // 화이트리스트: translate_Kp_heading / Kd_heading / K_stanley / K_soft / max_delta_deg.
    // 범위 외 값은 reject. 그 외 키는 무관여 (set 허용, controller 미반영).
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
                            "Translate gains hot-reloaded: Kp_h=%.3f Kd_h=%.3f K_st=%.3f K_so=%.3f "
                            "max_delta=%.1f deg",
                            Kp_heading_, Kd_heading_, K_stanley_, K_soft_, max_delta_ * 180.0 / M_PI);
            }
            return result;
        });
}

// ════════════════════════════════════════════════════════
//  wheelStateCallback override: base + timestamp tracking
// ════════════════════════════════════════════════════════

void TranslateForwardActionServer::wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg)
{
    // Call base (updates last_angle_front_/rear_ atomics)
    trnav::motion::two_ws::TwoWsActionServerBase<Translate>::wheelStateCallback(msg);
    // Timestamp tracking for actual-steer-based speed
    wheel_state_received_.store(true);
    {
        std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
        last_wheel_state_time_ = std::chrono::steady_clock::now();
    }
}

bool TranslateForwardActionServer::validateGoal(std::shared_ptr<const Translate::Goal> goal)
{
    double dx = goal->end_x - goal->start_x;
    double dy = goal->end_y - goal->start_y;
    double dist = std::hypot(dx, dy);
    if (dist < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: start == end");
        return false;
    }
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: max_linear_speed <= 0");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: acceleration <= 0");
        return false;
    }
    if (goal->entry_speed < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: entry_speed < 0");
        return false;
    }
    if (!goal->hold_steer && (goal->exit_steer_angle < -90.0 || goal->exit_steer_angle > 90.0))
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: exit_steer_angle out of [-90, +90]");
        return false;
    }
    if (goal->control_mode != 0 && goal->control_mode != 1)
    {
        RCLCPP_WARN(node_->get_logger(), "TranslateForward rejected: control_mode=%u 미지원 (BICYCLE=1 만 지원)",
                    goal->control_mode);
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "TranslateForward goal accepted: (%.2f,%.2f)->(%.2f,%.2f), dist=%.3f m, v_max=%.2f m/s", goal->start_x,
                goal->start_y, goal->end_x, goal->end_y, dist, goal->max_linear_speed);
    return true;
}

// ════════════════════════════════════════════════════════
//  Main execute loop (BICYCLE mode, forward direction only)
// ════════════════════════════════════════════════════════

void TranslateForwardActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                            "TranslateForward: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "TranslateForward: mux active source → %d (translate_forward)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "TranslateForward: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "TranslateForward: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<Translate::Feedback>();
    auto result = std::make_shared<Translate::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

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

    // BICYCLE 고정 (validateGoal 에서 다른 모드 reject)
    ControlMode local_mode = ControlMode::BICYCLE;
    path_ctrl_->setMode(local_mode);

    RCLCPP_INFO(node_->get_logger(), "TranslateForward control_mode=BICYCLE (goal.control_mode=%u)",
                goal->control_mode);

    path_ctrl_->setPath(goal->start_x, goal->start_y, goal->end_x, goal->end_y);

    double target_distance = path_ctrl_->targetDistance();

    RCLCPP_INFO(node_->get_logger(), "TranslateForward execute: path_angle=%.1f deg, target_dist=%.3f m",
                path_ctrl_->pathAngle() * 180.0 / M_PI, target_distance);

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

    // ── IMU receive check (위치는 TF lookupMapToBase 가 처리) ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting translate_forward");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── Initial pose from tf2 map->base_link ──
    double robot_x = 0.0, robot_y = 0.0, robot_yaw = 0.0;
    if (!loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
    {
        RCLCPP_ERROR(node_->get_logger(), "/robot_pose 미수신 또는 낡음(신선도 초과) — TF 문제가 아니다. 측위 발행자와 pose_topic 결속을 확인하라. aborting translate_forward");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // skip_initial_pose_check(=acs_gui on_position_mismatch='none') 시 생략 — 경로 밖 시작 허용 (운영자 위치 책임, 2026-06-19).
    if (goal->skip_initial_pose_check)
    {
        RCLCPP_WARN(node_->get_logger(),
                    "TranslateForward: skip_initial_pose_check=true → validateInitialPose 생략 (경로 밖 시작 허용)");
    }
    else
    {
        int validate_result = path_ctrl_->validateInitialPose(robot_x, robot_y, robot_yaw);
        if (validate_result != 0)
        {
            RCLCPP_WARN(node_->get_logger(),
                        "TranslateForward initial pose validation failed (code=%d): robot=(%.2f,%.2f,%.1f deg)",
                        validate_result, robot_x, robot_y, robot_yaw * 180.0 / M_PI);
            finish_abort(-2, 0.0, 0.0, 0.0, start_time);
            return;
        }
    }

    // ── Phase 0: Steer Align (entry_speed <= 0.0 일 때만 실행) ──
    if (goal->entry_speed <= 0.0)
    {
        const double forward_steer_f = last_angle_front_.load();
        const double forward_steer_r = last_angle_rear_.load();

        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "TranslateForward Phase 0: steer alignment (target F=%.1f R=%.1f deg)",
                    forward_steer_f * 180.0 / M_PI, forward_steer_r * 180.0 / M_PI);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "TranslateForward cancelled during Phase 0");
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
                RCLCPP_WARN(node_->get_logger(), "TranslateForward Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }

            rate.sleep();
        }

        RCLCPP_INFO(node_->get_logger(), "TranslateForward Phase 0 complete, starting trapezoidal profile");
    }

    // Steer rate limiter state
    double prev_cmd_steer_f = last_angle_front_.load();
    double prev_cmd_steer_r = last_angle_rear_.load();

    double prev_cmd_vel_f = (goal->entry_speed > 0.0) ? goal->entry_speed : 0.0;
    double prev_cmd_vel_r = (goal->entry_speed > 0.0) ? goal->entry_speed : 0.0;

    // ── Phase 1-3: Trapezoidal profile + PathController + TransientGuard ──
    double exit_speed = goal->exit_speed;
    TrapezoidalProfile profile(target_distance, goal->max_linear_speed, goal->acceleration, exit_speed,
                               goal->entry_speed);

    bool reached = false;
    int tf_fail_count = 0;
    const int tf_fail_max = 50;

    // 종단 fine-positioning sentinel (exit_speed<=0 최종 정지 한정 creep)
    bool fine_active = false;
    rclcpp::Time fine_t0;

    // ── heading_source==1 (IMU): 시작 RMA10 으로 (pose_yaw - imu_yaw) offset 평균 후 고정 ──
    //   capture 중(첫 N 샘플)은 pose yaw 유지 → 시작 안전. 고정 후 robot_yaw = imu_yaw + offset.
    double imu_heading_offset = 0.0;
    double imu_offset_sum = 0.0;
    int imu_offset_n = 0;
    bool imu_offset_frozen = false;
    const int kImuOffsetRmaN = 10;

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

        // ── heading yaw 소스 치환 (translate_heading_source==1) ──
        //   robot_x, robot_y (CTE 입력) 는 pose 그대로. e_theta 용 robot_yaw 만 IMU 로 교체.
        if (heading_source_ == 1 && imu_received_.load())
        {
            const double imu_yaw = last_yaw_rad_.load();
            if (!imu_offset_frozen)
            {
                imu_offset_sum += trnav_2ws_core::normalizeAngle(robot_yaw - imu_yaw);
                imu_offset_n++;
                if (imu_offset_n >= kImuOffsetRmaN)
                {
                    imu_heading_offset = imu_offset_sum / static_cast<double>(imu_offset_n);
                    imu_offset_frozen = true;
                    RCLCPP_INFO(node_->get_logger(),
                                "TranslateForward heading=IMU: offset frozen=%.2f deg (RMA%d)",
                                imu_heading_offset * 180.0 / M_PI, kImuOffsetRmaN);
                }
                // capture 중 (첫 N 샘플) 은 pose yaw 유지 → 시작 안전
            }
            else
            {
                robot_yaw = trnav_2ws_core::normalizeAngle(imu_yaw + imu_heading_offset);
            }
        }

        if (goal_handle->is_canceling())
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            RCLCPP_INFO(node_->get_logger(), "TranslateForward cancelled at dist=%.3f m", pc_out.projection);
            finish_abort(-1, pc_out.projection, pc_out.e_d, pc_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);
            RCLCPP_WARN(node_->get_logger(), "TranslateForward global timeout (%.1f s), dist=%.3f m", max_timeout_sec_,
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
            else if (reason == trnav_2ws_core::LocalizationMonitor::HealthFailReason::STUCK)
            {
                // 값이 얼어 있다 — 「측위 갱신 없음」이므로 −4 계열이 맞다. 다만 stamp 는
                // 신선했으므로 로그 문자열로 구분한다(신선도 검사만 보고 오진하지 않게).
                code = -4;
                reason_str = "STUCK(값 동결 — stamp 는 신선)";
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

        // ── 종단 분기: exit_speed<=0 최종 정지 시 fine-positioning closed-loop creep ──
        // exit_speed>0 (체이닝/has_next) 은 기존 속도연속 reach 그대로 유지.
        bool use_fine =
            (goal->exit_speed <= 0.0) && (remaining < fine_enter_dist_ || prof_out.phase == ProfilePhase::DONE);

        if (!use_fine)
        {
            // coarse: 기존 사다리꼴 + min_vx_ floor 유지
            bool near_goal = (remaining < goal_reach_threshold_);
            if (prof_out.phase != ProfilePhase::DONE && !near_goal && vx_profile < min_vx_)
            {
                vx_profile = min_vx_;
            }

            if (prof_out.phase == ProfilePhase::DONE || projection >= target_distance)
            {
                // exit_speed>0 만 도달 (속도연속). exit_speed<=0 은 위 use_fine 로 분기됨.
                reached = true;
                RCLCPP_INFO(node_->get_logger(), "TranslateForward reached with velocity continuity (exit_speed=%.3f)",
                            goal->exit_speed);
                break;
            }
        }
        else
        {
            // fine: creep closed-loop. min_vx_ floor 미적용 (creep 가 더 낮아야 함).
            if (!fine_active)
            {
                fine_active = true;
                fine_t0 = node_->now();
            }

            if (remaining <= fine_tol_pos_)
            {
                reached = true;
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
                RCLCPP_INFO(node_->get_logger(), "TranslateForward fine-stop: remaining=%.3f m (tol=%.3f)", remaining,
                            fine_tol_pos_);
                break;
            }

            if ((node_->now() - fine_t0).seconds() > fine_timeout_)
            {
                reached = true;
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
                RCLCPP_WARN(node_->get_logger(), "TranslateForward fine timeout, remaining=%.3f", remaining);
                break;
            }

            vx_profile = std::clamp(fine_kp_ * remaining, fine_v_min_, fine_v_max_);
        }

        auto pc_out = path_ctrl_->update(robot_x, robot_y, robot_yaw, vx_profile, dt);

        IKResult ik_expected;
        double vy_for_guard, omega_for_guard;

        // BICYCLE forward dual-bicycle 경로
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

        double vel_f = ik_for_speed.wheels[0].wheel_speed * ik_for_speed.wheels[0].direction * speed_scale;
        double vel_r = ik_for_speed.wheels[1].wheel_speed * ik_for_speed.wheels[1].direction * speed_scale;

        // Walk velocity profile
        {
            double acc_step = walk_accel_limit_ * dt;
            double dec_step = walk_decel_limit_ * dt;
            // 지역 사본을 폐기하고 공용 `trnav_2ws_core::rampToward` 를 쓴다.
            // 이 서버의 램프 입력은 항상 ≥ 0 이라 **거동이 바뀌지 않는다**(양수 구간 전수
            // 비교 결과 차이 0.000e+00). 사본이 갈라져 한쪽만 고쳐지는 일을 막는 통일이다.
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
                        "[TranslateForward] S%d steer: F=%.1f/%.1f° R=%.1f/%.1f° err=%.1f° %s | "
                        "vx=%.3f vy=%.4f omega=%.4f proj=%.3fm lat=%.3fm hdg=%.1f°",
                        pc_out.control_stage, last_angle_front_.load() * 180.0 / M_PI, cmd_steer_f * 180.0 / M_PI,
                        last_angle_rear_.load() * 180.0 / M_PI, cmd_steer_r * 180.0 / M_PI, max_steer_err,
                        guard_out.gate_blocked ? "BLOCKED" : "OK", cmd_vx, pc_out.vy, pc_out.omega, pc_out.projection,
                        pc_out.e_d, pc_out.e_theta * 180.0 / M_PI);
        }

        // Debug topic
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

    // Read final state from tf2
    loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw);
    auto final_pc = path_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt);

    RCLCPP_INFO(node_->get_logger(),
                "TranslateForward Phase 1-3 complete: dist=%.3f m, lat_err=%.4f m, head_err=%.2f deg",
                final_pc.projection, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI);

    // Cancel check after Phase 1-3
    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "TranslateForward cancelled after Phase 1-3");
        finish_abort(-1, final_pc.projection, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI, start_time);
        return;
    }

    // ── Phase 4: Steer Return (if !hold_steer) ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "TranslateForward Phase 4: steer return to %.1f deg", goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "TranslateForward cancelled during Phase 4");
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
                RCLCPP_WARN(node_->get_logger(), "TranslateForward Phase 4 steer timeout (non-critical)");
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
    result->final_heading_error = final_pc.e_theta * 180.0 / M_PI;
    result->elapsed_time = (node_->now() - start_time).seconds();

    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(),
                "TranslateForward complete: dist=%.3f/%.3f m, lat_err=%.4f m, head_err=%.2f deg, time=%.1f s",
                final_pc.projection, target_distance, final_pc.e_d, final_pc.e_theta * 180.0 / M_PI,
                result->elapsed_time);
}

} // namespace trnav_2ws_action_server::translate_forward
