#include "trnav_2ws_action_server/turn/turn_action_server.hpp"
#include "trnav_2ws_core/math_utils.hpp"  // normalizeAngleDeg — target_angle 입력 정규화
#include "trnav_msgs/srv/select_motion_source.hpp"

#include <chrono>
#include <thread>

namespace trnav_2ws_action_server::turn
{

TurnActionServer::TurnActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<Turn>(node, std::move(action_mutex), "amr_motion_turn_abstract",
                                                  "/motion/wheel_cmd/turn")
{
    // Turn precision parameters (safeParam handles declare-if-not-declared)
    double deadband_deg = safeParam("imu_deadband_deg", 0.05);
    imu_deadband_rad_ = deadband_deg * M_PI / 180.0;
    min_speed_dps_ = safeParam("min_speed_dps", 2.0);
    fine_correction_threshold_deg_ = safeParam("fine_correction_threshold_deg", 0.3);
    fine_correction_speed_dps_ = safeParam("fine_correction_speed_dps", 3.0);
    fine_correction_timeout_sec_ = safeParam("fine_correction_timeout_sec", 3.0);
    settling_delay_ms_ = safeParam("settling_delay_ms", 200);

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 5);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    RCLCPP_INFO(node_->get_logger(), "TurnActionServer initialized");
}

bool TurnActionServer::validateGoal(std::shared_ptr<const Turn::Goal> goal)
{
    if (std::abs(goal->target_angle) < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn rejected: target_angle is 0");
        return false;
    }
    if (goal->turn_radius <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn rejected: turn_radius <= 0");
        return false;
    }
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn rejected: max_linear_speed <= 0");
        return false;
    }
    if (goal->accel_angle <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn rejected: accel_angle <= 0");
        return false;
    }
    if (!goal->hold_steer && (goal->exit_steer_angle < -90.0 || goal->exit_steer_angle > 90.0))
    {
        RCLCPP_WARN(node_->get_logger(), "Turn rejected: exit_steer_angle out of [-90, +90]");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(), "Turn goal accepted: %.1f deg, R=%.2f m", goal->target_angle,
                goal->turn_radius);
    return true;
}

void TurnActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
{
    trnav_2ws_core::ActionMutexGuard mutex_guard(action_mutex_);

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
                            "Turn: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "Turn: mux active source → %d (turn)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "Turn: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "Turn: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    // 입력 정규화: |target_angle| > 180° 는 [-180,+180] 의 작은쪽 회전으로 자동 변환
    // (예: +270° → -90°, +540° → -180°). std::remainder 특성으로 ±180° 정확 입력 시 -180° 로 정착.
    const double target_angle_deg = trnav_2ws_core::normalizeAngleDeg(goal->target_angle);
    auto feedback = std::make_shared<Turn::Feedback>();
    auto result = std::make_shared<Turn::Result>();

    rclcpp::Rate rate(control_rate_hz_);

    // Direction: + CCW, - CW (정규화된 target_angle_deg 기준 → 항상 |target| ≤ 180°)
    const double sign = (target_angle_deg >= 0.0) ? 1.0 : -1.0;
    const double target_abs = std::abs(target_angle_deg);    // deg
    const double turn_radius = static_cast<double>(goal->turn_radius);
    const double max_v = static_cast<double>(goal->max_linear_speed);
    const double accel_angle = static_cast<double>(goal->accel_angle);

    const double max_omega_rad = max_v / turn_radius;
    const double max_omega_deg = max_omega_rad * 180.0 / M_PI;
    const double accel_dps2 = (max_omega_deg * max_omega_deg) / (2.0 * accel_angle);

    auto ik_steer = ik_->compute({max_v, 0.0, sign * max_omega_rad});
    const double turn_steer_front = ik_steer.wheels[0].steer_rad;
    const double turn_steer_rear = ik_steer.wheels[1].steer_rad;

    auto start_time = node_->now();
    double accumulated_angle = 0.0;

    // ── Phase 0: Steer Align ──
    feedback->phase = 0;
    auto phase0_start = node_->now();

    while (rclcpp::ok())
    {
        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = 0.0;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear);
        feedback->current_angle = 0.0;
        feedback->current_linear_speed = 0.0;
        feedback->current_angular_speed = 0.0;
        feedback->remaining_angle = target_abs;
        feedback->w1_drive_rpm = 0.0;
        feedback->w2_drive_rpm = 0.0;
        goal_handle->publish_feedback(feedback);

        bool front_ok = std::abs(last_angle_front_.load() - turn_steer_front) < steer_tolerance_rad_;
        bool rear_ok = std::abs(last_angle_rear_.load() - turn_steer_rear) < steer_tolerance_rad_;
        if (front_ok && rear_ok)
        {
            break;
        }

        if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "Turn Phase 0 steer timeout");
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -3;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = 0.0;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->abort(result);
            return;
        }

        rate.sleep();
    }

    // ── IMU receive check ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting turn");
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
        result->status = -3;
        this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
        result->actual_angle = 0.0;
        result->elapsed_time = (node_->now() - start_time).seconds();
        goal_handle->abort(result);
        return;
    }

    // ── Phase 1-3: Trapezoidal profile ──
    trnav_2ws_core::TrapezoidalProfile profile(target_abs, max_omega_deg, accel_dps2);

    double prev_yaw = last_yaw_rad_.load();

    while (rclcpp::ok() && !profile.isComplete(accumulated_angle))
    {
        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = sign * accumulated_angle;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        auto prof_out = profile.getSpeed(accumulated_angle);
        double omega_dps = prof_out.speed;
        if (prof_out.phase != trnav_2ws_core::ProfilePhase::DONE && omega_dps < min_speed_dps_)
        {
            omega_dps = min_speed_dps_;
        }
        double omega_rad = omega_dps * M_PI / 180.0;
        double v = omega_rad * turn_radius;

        auto ik_out = ik_->compute({v, 0.0, sign * omega_rad});
        double vel_f = ik_out.wheels[0].wheel_speed * ik_out.wheels[0].direction;
        double ang_f = ik_out.wheels[0].steer_rad;
        double vel_r = ik_out.wheels[1].wheel_speed * ik_out.wheels[1].direction;
        double ang_r = ik_out.wheels[1].steer_rad;

        publishWheelCmd(vel_f, ang_f, vel_r, ang_r);

        double current_yaw = last_yaw_rad_.load();
        double delta_yaw = current_yaw - prev_yaw;
        if (delta_yaw > M_PI)
            delta_yaw -= 2.0 * M_PI;
        else if (delta_yaw < -M_PI)
            delta_yaw += 2.0 * M_PI;
        if (std::abs(delta_yaw) < imu_deadband_rad_)
        {
            // Skip noise
        }
        else
        {
            accumulated_angle += std::abs(delta_yaw) * 180.0 / M_PI;
            prev_yaw = current_yaw;
        }

        uint8_t phase_id;
        switch (prof_out.phase)
        {
        case trnav_2ws_core::ProfilePhase::ACCEL:
            phase_id = 1;
            break;
        case trnav_2ws_core::ProfilePhase::CRUISE:
            phase_id = 2;
            break;
        case trnav_2ws_core::ProfilePhase::DECEL:
            phase_id = 3;
            break;
        default:
            phase_id = 3;
            break;
        }
        feedback->phase = phase_id;
        feedback->current_angle = sign * accumulated_angle;
        feedback->current_linear_speed = v;
        feedback->current_angular_speed = sign * omega_dps;
        feedback->remaining_angle = target_abs - accumulated_angle;
        feedback->w1_drive_rpm = ik_out.wheels[0].drive_rpm;
        feedback->w2_drive_rpm = ik_out.wheels[1].drive_rpm;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // ── Settling Delay ──
    publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear);
    rclcpp::sleep_for(std::chrono::milliseconds(settling_delay_ms_));

    // IMU update during settling
    {
        double current_yaw = last_yaw_rad_.load();
        double delta_yaw = current_yaw - prev_yaw;
        if (delta_yaw > M_PI)
            delta_yaw -= 2.0 * M_PI;
        else if (delta_yaw < -M_PI)
            delta_yaw += 2.0 * M_PI;
        if (std::abs(delta_yaw) >= imu_deadband_rad_)
        {
            double delta_deg = delta_yaw * 180.0 / M_PI;
            if (sign * delta_deg > 0.0)
            {
                accumulated_angle += std::abs(delta_deg);
            }
            else
            {
                accumulated_angle -= std::abs(delta_deg);
                if (accumulated_angle < 0.0)
                    accumulated_angle = 0.0;
            }
            prev_yaw = current_yaw;
        }
    }

    // ── Phase 3.5: Fine Correction ──
    double angle_error = target_abs - accumulated_angle;

    if (std::abs(angle_error) > fine_correction_threshold_deg_)
    {
        auto ik_spin = ik_->computeSpin(sign * 0.1);
        const double spin_steer_front = ik_spin.wheels[0].steer_rad;
        const double spin_steer_rear = ik_spin.wheels[1].steer_rad;

        // ── Steer re-align ──
        auto steer_align_start = node_->now();
        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
                result->status = -1;
                this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
                result->actual_angle = sign * accumulated_angle;
                result->elapsed_time = (node_->now() - start_time).seconds();
                goal_handle->canceled(result);
                return;
            }

            publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear);

            bool front_ok = std::abs(last_angle_front_.load() - spin_steer_front) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - spin_steer_rear) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
            {
                break;
            }

            if ((node_->now() - steer_align_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "Turn fine correction steer-align timeout");
                break;
            }

            rate.sleep();
        }

        // ── Fine correction loop ──
        auto fine_start = node_->now();
        double fine_omega_dps = fine_correction_speed_dps_;

        while (rclcpp::ok() && std::abs(angle_error) > fine_correction_threshold_deg_)
        {
            if (goal_handle->is_canceling())
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
                result->status = -1;
                this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
                result->actual_angle = sign * accumulated_angle;
                result->elapsed_time = (node_->now() - start_time).seconds();
                goal_handle->canceled(result);
                return;
            }

            if ((node_->now() - fine_start).seconds() > fine_correction_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "Turn fine correction timeout, error=%.2f deg", angle_error);
                break;
            }

            double correction_sign = (angle_error > 0.0) ? sign : -sign;
            double omega_rad = correction_sign * fine_omega_dps * M_PI / 180.0;
            auto ik_out = ik_->computeSpin(omega_rad);

            double vel_f = ik_out.wheels[0].wheel_speed * ik_out.wheels[0].direction;
            double ang_f = ik_out.wheels[0].steer_rad;
            double vel_r = ik_out.wheels[1].wheel_speed * ik_out.wheels[1].direction;
            double ang_r = ik_out.wheels[1].steer_rad;
            publishWheelCmd(vel_f, ang_f, vel_r, ang_r);

            double current_yaw = last_yaw_rad_.load();
            double delta_yaw = current_yaw - prev_yaw;
            if (delta_yaw > M_PI)
                delta_yaw -= 2.0 * M_PI;
            else if (delta_yaw < -M_PI)
                delta_yaw += 2.0 * M_PI;

            if (std::abs(delta_yaw) >= imu_deadband_rad_)
            {
                double delta_deg = delta_yaw * 180.0 / M_PI;
                if (sign * delta_deg > 0.0)
                {
                    accumulated_angle += std::abs(delta_deg);
                }
                else
                {
                    accumulated_angle -= std::abs(delta_deg);
                    if (accumulated_angle < 0.0)
                        accumulated_angle = 0.0;
                }
                prev_yaw = current_yaw;
            }

            angle_error = target_abs - accumulated_angle;

            feedback->phase = 3;
            feedback->current_angle = sign * accumulated_angle;
            feedback->current_linear_speed = 0.0;
            feedback->current_angular_speed = sign * fine_omega_dps * (angle_error > 0 ? 1.0 : -1.0);
            feedback->remaining_angle = angle_error;
            feedback->w1_drive_rpm = ik_out.wheels[0].drive_rpm;
            feedback->w2_drive_rpm = ik_out.wheels[1].drive_rpm;
            goal_handle->publish_feedback(feedback);

            rate.sleep();
        }
    }

    // Stop driving
    {
        auto ik_spin_stop = ik_->computeSpin(sign * 0.1);
        publishWheelCmd(0.0, ik_spin_stop.wheels[0].steer_rad, 0.0, ik_spin_stop.wheels[1].steer_rad);
    }

    // ── Phase 4: Steer Return (if !hold_steer) ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
                result->status = -1;
                this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
                result->actual_angle = sign * accumulated_angle;
                result->elapsed_time = (node_->now() - start_time).seconds();
                goal_handle->canceled(result);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);
            feedback->current_angle = sign * accumulated_angle;
            feedback->current_linear_speed = 0.0;
            feedback->current_angular_speed = 0.0;
            feedback->remaining_angle = 0.0;
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
                RCLCPP_WARN(node_->get_logger(), "Turn Phase 4 steer timeout (non-critical)");
                break;
            }

            rate.sleep();
        }
    }

    // Success
    result->status = 0;
    this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
    result->actual_angle = sign * accumulated_angle;
    result->elapsed_time = (node_->now() - start_time).seconds();
    goal_handle->succeed(result);
    double final_error = target_abs - accumulated_angle;
    RCLCPP_INFO(node_->get_logger(),
                "Turn complete: target=%.1f° (normalized=%.1f°), actual=%.1f, error=%.2f deg, R=%.2f m, time=%.1f s",
                goal->target_angle, target_angle_deg, sign * accumulated_angle, final_error, goal->turn_radius,
                result->elapsed_time);
    if (std::abs(final_error) > 2.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn precision warning: final error %.2f deg exceeds 2.0 deg threshold",
                    final_error);
    }
}

} // namespace trnav_2ws_action_server::turn
