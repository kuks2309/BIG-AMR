#include "trnav_2ws_action_server/turn/turn_action_server.hpp"
#include "trnav_2ws_core/math_utils.hpp"  // normalizeAngleDeg — target_angle 입력 정규화
#include "trnav_msgs/srv/select_motion_source.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <thread>

namespace trnav_2ws_action_server::turn
{

TurnActionServer::TurnActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<Turn>(node, std::move(action_mutex), "amr_motion_turn_abstract",
                                                  "/motion/wheel_cmd/turn")
{
    // Turn precision parameters (safeParam handles declare-if-not-declared)
    min_speed_dps_ = safeParam("min_speed_dps", 2.0);
    fine_correction_threshold_deg_ = safeParam("fine_correction_threshold_deg", 0.3);
    pid_band_deg_ = safeParam("pid_band_deg", 5.0);
    kp_turn_ = safeParam("kp_turn", 0.6);
    kd_turn_ = safeParam("kd_turn", 0.1);
    settle_rate_dps_ = safeParam("settle_rate_dps", 0.5);
    settle_count_ = safeParam("settle_count", 5);
    start_yaw_window_ = safeParam("start_yaw_avg_samples", 10);

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

    // ── 계상 기준: **절대 목표 yaw** (델타 누적 폐기) ──
    // 종전에는 IMU yaw 델타를 누적(accumulated_angle)했고 그 누적기에 0 클램프가 있어
    // 음의 델타가 영구 소실 → 편향이 한 방향으로만 쌓일 수 있었다(debt-048).
    // 델타를 더하지 않으므로 드리프트·편향이 **원천 소거**된다.
    // 근거·설계: docs/adr/2026-08-09-turn-error-feedback.md D1
    //
    // start_yaw 는 **원형 이동평균**이다. 1회 샘플로 잡으면 그 순간의 IMU 잡음이 기준 전체를
    // 오프셋한다. yaw 는 ±π wrap 이므로 선형 평균은 ±180° 부근에서 오평균(179°,−179°→0°)
    // → 반드시 atan2(Σsin, Σcos). 이 구간은 Phase 0 직후로 구동 0 이라 무해하다.
    double sin_sum = 0.0, cos_sum = 0.0;
    for (int i = 0; i < start_yaw_window_ && rclcpp::ok(); ++i)
    {
        publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear); // 조향 유지(cmd 끊김 방지)
        double y = last_yaw_rad_.load();
        sin_sum += std::sin(y);
        cos_sum += std::cos(y);
        rate.sleep();
    }
    const double start_yaw = std::atan2(sin_sum, cos_sum);
    const double target_imu_yaw = start_yaw + sign * target_abs * M_PI / 180.0;

    // 부호 있는 **전역** 잔여 회전[deg]. + 면 CCW 로 더, − 면 CW 로 되돌려야 한다.
    // `sign * e` 가 「진행 방향 기준 잔여」로, 종전 `target_abs − accumulated_angle` 과 같은 의미다.
    auto remaining_signed_deg = [&](double cur_yaw) -> double {
        return trnav_2ws_core::normalizeAngle(target_imu_yaw - cur_yaw) * 180.0 / M_PI;
    };
    // 달성 회전량[deg] = 지령 − 잔여. **과회전도 정확히 반영**된다(e 가 반대부호가 되므로 커진다).
    // ⚠ spin 은 `sign*(target_abs − |e|)` 를 쓰는데 그 식은 과회전을 부족처럼 줄여 보고한다.
    //   여기서는 의도적으로 다르게 간다(spin 쪽은 별건).
    auto achieved_deg = [&](double e) -> double { return sign * target_abs - e; };

    const double dt = 1.0 / control_rate_hz_;

    // ── 지령 변환 (Stage 1·2 공용) ──
    // vx = sign · ω · R ,  ωz = ω   ⇒  |v/ω| = R 보존 → IK 조향각 **불변**.
    // ω 가 반대부호가 되면 vx 도 함께 뒤집혀 **같은 조향각 그대로 원호를 되짚는다** —
    // 조향은 Phase 0 이후 Phase 4 까지 움직이지 않는다.
    // ⚠ fine 에서 조향을 다시 세우는 것은 금지다(종전 computeSpin 전례 — 아래 Stop 주석 참조).
    double vx = 0.0;
    auto publish_arc = [&](double omega_rad_signed) {
        vx = sign * omega_rad_signed * turn_radius;
        auto ik_out = ik_->compute({vx, 0.0, omega_rad_signed});
        publishWheelCmd(ik_out.wheels[0].wheel_speed * ik_out.wheels[0].direction, ik_out.wheels[0].steer_rad,
                        ik_out.wheels[1].wheel_speed * ik_out.wheels[1].direction, ik_out.wheels[1].steer_rad);
        return ik_out;
    };

    // ── Stage 1 (coarse): Phase 1-3 사다리꼴 — |잔여| > pid_band 구간 ──
    // 프로파일은 그대로 두고 **입력만** 누적각 → 절대오차에서 도출한 진행량으로 바꿨다.
    trnav_2ws_core::TrapezoidalProfile profile(target_abs, max_omega_deg, accel_dps2);
    double error_deg = remaining_signed_deg(last_yaw_rad_.load());

    while (rclcpp::ok())
    {
        error_deg = remaining_signed_deg(last_yaw_rad_.load());
        double remaining_abs = std::fabs(error_deg);
        double progress_deg = target_abs - remaining_abs; // 0..target (프로파일 입력)
        if (progress_deg < 0.0)
            progress_deg = 0.0;

        auto prof_out = profile.getSpeed(progress_deg);

        // 인계: 남은 오차가 band 안으로 들어오면 Stage 2(PD)로 넘긴다.
        if (remaining_abs <= pid_band_deg_ || prof_out.phase == trnav_2ws_core::ProfilePhase::DONE)
            break;

        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = achieved_deg(error_deg);
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        double omega_dps = prof_out.speed;
        if (omega_dps < min_speed_dps_)
            omega_dps = min_speed_dps_; // coarse 전용 하한 (fine 에는 걸지 않는다)
        auto ik_out = publish_arc(sign * omega_dps * M_PI / 180.0);

        uint8_t phase_id;
        switch (prof_out.phase)
        {
        case trnav_2ws_core::ProfilePhase::ACCEL:
            phase_id = 1;
            break;
        case trnav_2ws_core::ProfilePhase::CRUISE:
            phase_id = 2;
            break;
        default:
            phase_id = 3;
            break;
        }
        feedback->phase = phase_id;
        feedback->current_angle = achieved_deg(error_deg);
        feedback->current_linear_speed = vx;
        feedback->current_angular_speed = sign * omega_dps;
        feedback->remaining_angle = sign * error_deg;
        feedback->w1_drive_rpm = ik_out.wheels[0].drive_rpm;
        feedback->w2_drive_rpm = ik_out.wheels[1].drive_rpm;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // ── Stage 2 (fine): **PD 오차 피드백** ──
    // ω = kp·e + kd·ė   (ė = (e − e_prev)/dt = −실측 yaw rate)
    // ki 는 두지 않는다 — 사용자 지시(2026-08-09):「ki 는 진동을 만들 수 있으므로 하지말고」.
    // |ω| 상한만 clamp하고 **하한 floor 는 걸지 않는다** — 목표 근처에서 ≥min 을 강제하면
    // 한계진동이 된다(spin 과 같은 규약).
    // 타임아웃은 파라미터가 아니라 기동 규모에 비례해 계산한다.
    const double fine_timeout_sec = std::max(2.0, 3.0 * target_abs / std::max(max_omega_deg, 1e-6));
    auto fine_start = node_->now();
    double prev_error = remaining_signed_deg(last_yaw_rad_.load());
    int settle_cnt = 0;

    while (rclcpp::ok())
    {
        error_deg = remaining_signed_deg(last_yaw_rad_.load());
        double derivative = (error_deg - prev_error) / dt; // = −(실측 회전율)[deg/s]
        prev_error = error_deg;

        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = achieved_deg(error_deg);
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        // ── 정착 게이트 ──
        // |오차| ≤ tol **AND** |실측 회전율| ≤ settle_rate 가 settle_count cycle 연속.
        // |오차|만 보고 끝내면 **아직 돌고 있는데 도달로 판정**해, 액션이 값을 읽은 뒤 차체가
        // 더 움직인다 — 2026-08-09 spin 에서 실측한 함정(자기보고 0.22° vs 2초 뒤 0.43°).
        if (std::fabs(error_deg) <= fine_correction_threshold_deg_ && std::fabs(derivative) <= settle_rate_dps_)
        {
            if (++settle_cnt >= settle_count_)
            {
                RCLCPP_INFO(node_->get_logger(),
                            "Turn fine(PD) settled (e=%.2f deg, |rate|=%.2f<=%.2f dps, %d cyc) — early stop",
                            error_deg, std::fabs(derivative), settle_rate_dps_, settle_count_);
                publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear);
                break;
            }
        }
        else
        {
            settle_cnt = 0;
        }

        if ((node_->now() - fine_start).seconds() > fine_timeout_sec)
        {
            RCLCPP_WARN(node_->get_logger(), "Turn fine(PD) timeout (%.1f s), error=%.2f deg", fine_timeout_sec,
                        error_deg);
            publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear);
            break;
        }

        double omega_dps = kp_turn_ * error_deg + kd_turn_ * derivative;
        omega_dps = std::max(-max_omega_deg, std::min(max_omega_deg, omega_dps));
        auto ik_out = publish_arc(omega_dps * M_PI / 180.0);

        feedback->phase = 3;
        feedback->current_angle = achieved_deg(error_deg);
        feedback->current_linear_speed = vx;
        feedback->current_angular_speed = omega_dps;
        feedback->remaining_angle = sign * error_deg;
        feedback->w1_drive_rpm = ik_out.wheels[0].drive_rpm;
        feedback->w2_drive_rpm = ik_out.wheels[1].drive_rpm;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // Stop driving — 원호 자세를 유지한 채 구동만 0.
    // 종전에는 computeSpin 으로 ±90° 를 실었고, 이 블록은 미세보정 if 밖이라
    // **보정이 발동하지 않아도 매 turn 마다** 조향을 스핀 자세로 돌렸다.
    // 2026-08-06 돌연변이 확인: 이 줄만 종전으로 되돌리면 같은 목표(45°, R=1.0 m)에서
    // 조향 최대가 31.13°/30.80° → **90.00°/90.00°** 로 되돌아온다(결과각·소요시간은 동일).
    publishWheelCmd(0.0, turn_steer_front, 0.0, turn_steer_rear);

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
                result->actual_angle = achieved_deg(error_deg);
                result->elapsed_time = (node_->now() - start_time).seconds();
                goal_handle->canceled(result);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);
            feedback->current_angle = achieved_deg(error_deg);
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
    result->actual_angle = achieved_deg(error_deg);
    result->elapsed_time = (node_->now() - start_time).seconds();
    goal_handle->succeed(result);
    double final_error = sign * error_deg; // 진행 방향 기준 잔여(+ 부족 / − 과회전)
    RCLCPP_INFO(node_->get_logger(),
                "Turn complete: target=%.1f° (normalized=%.1f°), actual=%.1f, error=%.2f deg, R=%.2f m, time=%.1f s",
                goal->target_angle, target_angle_deg, achieved_deg(error_deg), final_error, goal->turn_radius,
                result->elapsed_time);
    if (std::abs(final_error) > 2.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Turn precision warning: final error %.2f deg exceeds 2.0 deg threshold",
                    final_error);
    }
}

} // namespace trnav_2ws_action_server::turn
