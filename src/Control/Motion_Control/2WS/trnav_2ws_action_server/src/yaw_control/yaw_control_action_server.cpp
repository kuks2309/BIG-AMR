#include "trnav_2ws_action_server/yaw_control/yaw_control_action_server.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"

#include <chrono>
#include <cmath>
#include <thread>

#include "trnav_2ws_core/math_utils.hpp"

namespace trnav_2ws_action_server::yaw_control
{

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using BicycleModel = trnav::motion::two_ws::TwoWsBicycleModel;
using trnav::motion::two_ws::DualBicycleCommand;
using trnav::motion::two_ws::IKResult;
using trnav_2ws_core::LocalizationMonitor;
using trnav_2ws_core::normalizeAngle;
using trnav_2ws_core::normalizeAngleDeg;
using trnav_2ws_core::ProfilePhase;
using trnav_2ws_core::TransientGuard;
using trnav_2ws_core::TrapezoidalProfile;
using trnav::motion::two_ws::WheelPosition;

YawControlActionServer::YawControlActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<YawControl>(node, std::move(action_mutex),
                                                        "amr_motion_yaw_control_abstract",
                                                        "/motion/wheel_cmd/yaw_control")
{
    // BicycleModel — wheel positions from base params
    // ⚠ 기본값은 이 기체(Foil_A082, 인라인 듀얼스티어 · y=0) 기준. QD 대각 기본값
    //    (±0.330, ±0.135)이 남아 있어 params 없이 띄우면 조용히 QD 기하로 풀렸다
    //    (2026-08-08 실증: spin 이 ±90° 대신 −67.75° 를 세워 187 mm 병진). 정본은 config/*_params.yaml.
    double w1_x = safeParam("w1_x", 0.6039);
    double w1_y = safeParam("w1_y", 0.0);
    double w2_x = safeParam("w2_x", -0.5961);
    double w2_y = safeParam("w2_y", 0.0);
    std::vector<WheelPosition> wheels = {{w1_x, w1_y}, {w2_x, w2_y}};
    bicycle_model_ = std::make_unique<BicycleModel>(wheels);

    // YawControl-specific parameters
    max_timeout_sec_ = safeParam("yaw_control_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("yaw_control_enable_localization_watchdog", true);
    walk_accel_limit_ = safeParam("yaw_control_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("yaw_control_walk_decel_limit", 1.0);
    steer_rate_limit_ = safeParam("yaw_control_steer_rate_limit", 0.35);
    min_vx_ = safeParam("yaw_control_min_vx", 0.02);

    // TransientGuard
    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // LocalizationMonitor — /robot_pose PoseStamped 토픽 구독 (2026-05-18 topic 기반).
    // Phase2(2026-06-09): pose_topic 파라미터화 — 기본 /robot_pose, 실차 fused 교체는 yaw_control_pose_topic 으로 redirect.
    LocalizationMonitor::Params lm_params;
    lm_params.pose_topic = safeParam<std::string>("yaw_control_pose_topic", std::string("/robot_pose"));
    lm_params.localization_timeout_sec = safeParam("yaw_control_localization_timeout_sec", 2.0);
    lm_params.position_jump_threshold = safeParam("yaw_control_position_jump_threshold", 0.3);
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 6);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    RCLCPP_INFO(node_->get_logger(), "YawControlActionServer initialized");
}

bool YawControlActionServer::validateGoal(std::shared_ptr<const YawControl::Goal> goal)
{
    if (goal->target_distance <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControl rejected: target_distance <= 0");
        return false;
    }
    if (std::fabs(goal->vx_max) < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControl rejected: vx_max == 0");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControl rejected: acceleration <= 0");
        return false;
    }
    if (goal->max_steer_deg <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControl rejected: max_steer_deg <= 0");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "YawControl goal accepted: target_yaw=%.1f deg, dist=%.3f m, vx=%.3f m/s, counter_steer=%s",
                goal->target_yaw_deg, goal->target_distance, goal->vx_max,
                goal->counter_steer ? "true" : "false");
    return true;
}

void YawControlActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                            "YawControl: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "YawControl: mux active source → %d (yaw_control)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "YawControl: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "YawControl: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<YawControl::Feedback>();
    auto result = std::make_shared<YawControl::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

    auto finish_abort = [&](int8_t status, double actual_dist, double final_yaw_deg, double final_err_deg,
                            const rclcpp::Time &start_time) {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
        result->status = status;
        this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
        result->actual_distance = actual_dist;
        result->final_yaw_deg = final_yaw_deg;
        result->final_error_deg = final_err_deg;
        result->elapsed_time = (node_->now() - start_time).seconds();
        if (status == -1)
            goal_handle->canceled(result);
        else
            goal_handle->abort(result);
    };

    auto start_time = node_->now();

    // ── Pre-check: IMU received (위치는 TF lookupMapToBase 가 처리) ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "YawControl: IMU data not received, aborting (-4)");
        finish_abort(-4, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── Acquire start pose from tf2 ──
    double start_x = 0.0, start_y = 0.0, start_yaw_map = 0.0;
    if (!loc_monitor_->lookupMapToBase(start_x, start_y, start_yaw_map))
    {
        RCLCPP_ERROR(node_->get_logger(), "YawControl: tf2 map->base_link not available, aborting (-4)");
        finish_abort(-4, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── yaw_offset calibration: 1 time at start ──
    double start_yaw_imu = last_yaw_rad_.load();
    double yaw_offset = normalizeAngle(start_yaw_map - start_yaw_imu);

    RCLCPP_INFO(node_->get_logger(),
                "YawControl yaw calibration: start_yaw_map=%.2f deg, start_yaw_imu=%.2f deg, offset=%.2f deg",
                start_yaw_map * 180.0 / M_PI, start_yaw_imu * 180.0 / M_PI, yaw_offset * 180.0 / M_PI);

    guard_->reset();

    // ── Phase 0: Steer Align (align to delta=0) ──
    {
        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "YawControl Phase 0: steer alignment to 0");

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "YawControl cancelled during Phase 0");
                finish_abort(-1, 0.0, 0.0, 0.0, start_time);
                return;
            }

            publishWheelCmd(0.0, 0.0, 0.0, 0.0);

            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            double current_err_deg = normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI);

            feedback->current_distance = 0.0;
            feedback->remaining_distance = goal->target_distance;
            feedback->current_yaw_deg = calibrated_yaw * 180.0 / M_PI;
            feedback->current_error_deg = current_err_deg;
            feedback->current_steer_deg = 0.0;
            feedback->current_vx = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load()) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load()) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;

            if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "YawControl Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }

            rate.sleep();
        }

        RCLCPP_INFO(node_->get_logger(), "YawControl Phase 0 complete, starting trapezoidal profile");
    }

    // ── PID state ──
    double pid_ierr = 0.0;
    double pid_prev_err = 0.0;

    // ── Steer rate limiter state ──
    double prev_cmd_steer_f = 0.0;
    double prev_cmd_steer_r = 0.0;

    // ── Walk velocity limiter state ──
    double prev_cmd_vel_f = 0.0;
    double prev_cmd_vel_r = 0.0;

    // ── Trapezoidal profile ──
    TrapezoidalProfile profile(goal->target_distance, std::fabs(goal->vx_max), goal->acceleration);

    bool reached = false;
    double current_distance = 0.0;
    double current_yaw_deg = 0.0;

    int tf_fail_count = 0;
    const int tf_fail_max = 50;

    double rx = start_x, ry = start_y;

    // ── Phase 1-3: Trapezoidal + PID heading ──
    while (rclcpp::ok() && !reached)
    {
        double dummy_yaw = 0.0;
        if (loc_monitor_->lookupMapToBase(rx, ry, dummy_yaw))
        {
            tf_fail_count = 0;
        }
        else
        {
            tf_fail_count++;
            if (tf_fail_count >= tf_fail_max)
            {
                RCLCPP_ERROR(node_->get_logger(), "YawControl: TF2 failed %d consecutive times, aborting", tf_fail_count);
                double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
                finish_abort(-6, current_distance, calibrated_yaw * 180.0 / M_PI,
                             normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
                return;
            }
        }

        if (goal_handle->is_canceling())
        {
            RCLCPP_INFO(node_->get_logger(), "YawControl cancelled at dist=%.3f m", current_distance);
            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            finish_abort(-1, current_distance, calibrated_yaw * 180.0 / M_PI,
                         normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "YawControl global timeout (%.1f s), dist=%.3f m", max_timeout_sec_,
                        current_distance);
            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            finish_abort(-3, current_distance, calibrated_yaw * 180.0 / M_PI,
                         normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
            return;
        }

        if (enable_localization_watchdog_ && !loc_monitor_->checkLocalizationHealth())
        {
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
            RCLCPP_ERROR(node_->get_logger(), "YawControl: localization health fail (%s, code=%d) at dist=%.3f m",
                         reason_str, code, current_distance);
            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            finish_abort(code, current_distance, calibrated_yaw * 180.0 / M_PI,
                         normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
            return;
        }

        // Distance via start_yaw projection
        double dx = rx - start_x;
        double dy = ry - start_y;
        double projection = dx * std::cos(start_yaw_map) + dy * std::sin(start_yaw_map);
        current_distance = std::fabs(projection);

        // Profile speed
        // Reverse(vx_max<0) 시 projection<0 이지만 progress 의미는 |projection| (current_distance 와 동일).
        // 따라서 trapezoidal 입력은 abs 로 통일 (translate_reverse 와는 다름 — yaw_control 은 path 개념 없음).
        double clamped_pos = std::fabs(projection);
        auto prof_out = profile.getSpeed(clamped_pos);
        double vx_profile = prof_out.speed; // always >= 0 from profile

        // Floor on vx_profile to prevent stuck-at-start (TrapezoidalProfile.getSpeed(0)==0).
        // translate_forward 동일 패턴 (translate_min_vx). near_goal 시에는 floor 미적용.
        bool near_goal = (current_distance + 0.05 >= goal->target_distance);
        if (prof_out.phase != ProfilePhase::DONE && !near_goal && vx_profile < min_vx_)
        {
            vx_profile = min_vx_;
        }

        if (prof_out.phase == ProfilePhase::DONE || current_distance >= goal->target_distance)
        {
            reached = true;
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            break;
        }

        // Calibrated yaw from IMU + fixed offset
        double calibrated_yaw_rad = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
        current_yaw_deg = calibrated_yaw_rad * 180.0 / M_PI;

        // PID error (deg)
        double err_deg = normalizeAngleDeg(goal->target_yaw_deg - current_yaw_deg);

        // Reverse: invert error sign (ROS1 convention)
        if (goal->vx_max < 0.0)
            err_deg = -err_deg;

        // PID
        pid_ierr += err_deg * dt;
        // I windup clamp (in deg)
        if (pid_ierr > goal->i_max_deg)
            pid_ierr = goal->i_max_deg;
        else if (pid_ierr < -goal->i_max_deg)
            pid_ierr = -goal->i_max_deg;

        double derr_deg = (err_deg - pid_prev_err) / dt;
        pid_prev_err = err_deg;

        double delta_deg = goal->kp * err_deg + goal->kd * derr_deg + goal->ki * pid_ierr;

        // Clamp to max_steer_deg
        if (delta_deg > goal->max_steer_deg)
            delta_deg = goal->max_steer_deg;
        else if (delta_deg < -goal->max_steer_deg)
            delta_deg = -goal->max_steer_deg;

        double delta_rad = delta_deg * M_PI / 180.0;

        // Front/rear steer distribution
        double delta_f, delta_r;
        if (goal->counter_steer)
        {
            delta_f = delta_rad;
            delta_r = -delta_rad;
        }
        else
        {
            delta_f = delta_rad;
            delta_r = 0.0;
        }

        // vx with sign (forward/reverse)
        double vx_signed = (goal->vx_max < 0.0) ? -vx_profile : vx_profile;

        // BicycleModel -> IK
        DualBicycleCommand dual_cmd{vx_signed, delta_f, delta_r};
        IKResult ik_result = bicycle_model_->toIKResult(dual_cmd, *ik_);

        double expected_steer_f = ik_result.wheels[0].steer_rad;
        double expected_steer_r = ik_result.wheels[1].steer_rad;

        // Steer rate limit
        {
            double max_step = steer_rate_limit_ * dt;
            double diff_f = expected_steer_f - prev_cmd_steer_f;
            double diff_r = expected_steer_r - prev_cmd_steer_r;
            if (std::fabs(diff_f) > max_step)
                expected_steer_f = prev_cmd_steer_f + std::copysign(max_step, diff_f);
            if (std::fabs(diff_r) > max_step)
                expected_steer_r = prev_cmd_steer_r + std::copysign(max_step, diff_r);
            prev_cmd_steer_f = expected_steer_f;
            prev_cmd_steer_r = expected_steer_r;
        }

        // Steer tracking error for TransientGuard
        double steer_err_f = std::fabs(last_angle_front_.load() - expected_steer_f) * 180.0 / M_PI;
        double steer_err_r = std::fabs(last_angle_rear_.load() - expected_steer_r) * 180.0 / M_PI;
        double max_steer_err = std::max(steer_err_f, steer_err_r);

        // omega for TransientGuard (bicycle: omega = vx*(tan(df)-tan(dr))/L)
        double wheelbase = bicycle_model_->wheelbase();
        double omega_est = 0.0;
        if (std::fabs(wheelbase) > 1e-6)
            omega_est = vx_signed * (std::tan(delta_f) - std::tan(delta_r)) / wheelbase;

        TransientGuard::GuardInput guard_input;
        guard_input.vy_cmd = 0.0;
        guard_input.omega_cmd = omega_est;
        guard_input.steer_error_deg = max_steer_err;
        guard_input.is_phase0 = false;

        auto guard_out = guard_->apply(guard_input);
        double speed_scale = guard_out.gate_blocked ? 0.0 : guard_out.drive_scale;

        // Wheel velocity from IK
        double vel_f = ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction * speed_scale;
        double vel_r = ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction * speed_scale;

        // Walk velocity profile (accel/decel limiter)
        {
            double acc_step = walk_accel_limit_ * dt;
            double dec_step = walk_decel_limit_ * dt;
            auto velProfile = [](double cur, double tgt, double a_step, double d_step) -> double {
                if (std::fabs(tgt) < 0.01)
                {
                    if (cur > d_step)
                        return cur - d_step;
                    if (cur < -d_step)
                        return cur + d_step;
                    return tgt;
                }
                if (tgt > cur)
                    return std::fmin(tgt, cur + a_step);
                if (tgt < cur)
                    return std::fmax(tgt, cur - d_step);
                return tgt;
            };
            vel_f = velProfile(prev_cmd_vel_f, vel_f, acc_step, dec_step);
            vel_r = velProfile(prev_cmd_vel_r, vel_r, acc_step, dec_step);
            prev_cmd_vel_f = vel_f;
            prev_cmd_vel_r = vel_r;
        }

        publishWheelCmd(vel_f, expected_steer_f, vel_r, expected_steer_r);

        // Debug log (~10 Hz)
        static int dbg_cnt = 0;
        if (++dbg_cnt % 5 == 0)
        {
            RCLCPP_INFO(node_->get_logger(),
                        "[YawControl] phase=%d dist=%.3f/%.3fm yaw=%.1f° err=%.2f° steer=%.1f° vx=%.3f %s",
                        static_cast<int>(prof_out.phase), current_distance, goal->target_distance, current_yaw_deg,
                        err_deg, delta_deg, vx_signed * speed_scale,
                        guard_out.gate_blocked ? "BLOCKED" : "OK");
        }

        // Feedback
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
        feedback->current_distance = current_distance;
        feedback->remaining_distance = std::max(0.0, goal->target_distance - current_distance);
        feedback->current_yaw_deg = current_yaw_deg;
        feedback->current_error_deg = err_deg;
        feedback->current_steer_deg = delta_deg;
        feedback->current_vx = vx_signed * speed_scale;
        feedback->w1_drive_rpm = ik_result.wheels[0].drive_rpm * speed_scale;
        feedback->w2_drive_rpm = ik_result.wheels[1].drive_rpm * speed_scale;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // Stop
    publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());

    // Final state
    double final_calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
    double final_yaw_deg = final_calibrated_yaw * 180.0 / M_PI;
    double final_err_deg = normalizeAngleDeg(goal->target_yaw_deg - final_yaw_deg);

    RCLCPP_INFO(node_->get_logger(),
                "YawControl Phase 1-3 complete: dist=%.3f m, yaw=%.1f deg, err=%.2f deg", current_distance,
                final_yaw_deg, final_err_deg);

    // Cancel check after Phase 1-3
    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "YawControl cancelled after Phase 1-3");
        finish_abort(-1, current_distance, final_yaw_deg, final_err_deg, start_time);
        return;
    }

    // ── Phase 4: Steer Return (if !hold_steer) ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "YawControl Phase 4: steer return to %.1f deg", goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "YawControl cancelled during Phase 4");
                finish_abort(-1, current_distance, final_yaw_deg, final_err_deg, start_time);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);

            feedback->current_distance = current_distance;
            feedback->remaining_distance = 0.0;
            feedback->current_yaw_deg = final_yaw_deg;
            feedback->current_error_deg = final_err_deg;
            feedback->current_steer_deg = goal->exit_steer_angle;
            feedback->current_vx = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - exit_steer_rad) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - exit_steer_rad) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;

            if ((node_->now() - phase4_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "YawControl Phase 4 steer timeout (non-critical)");
                break;
            }

            rate.sleep();
        }
    }

    // ── Success ──
    result->status = 0;
    this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
    result->actual_distance = current_distance;
    result->final_yaw_deg = final_yaw_deg;
    result->final_error_deg = final_err_deg;
    result->elapsed_time = (node_->now() - start_time).seconds();

    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(),
                "YawControl complete: dist=%.3f/%.3f m, yaw=%.1f deg, err=%.2f deg, time=%.1f s", current_distance,
                goal->target_distance, final_yaw_deg, final_err_deg, result->elapsed_time);
}

} // namespace trnav_2ws_action_server::yaw_control
