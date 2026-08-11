#include "trnav_2ws_action_server/spin/spin_action_server.hpp"
#include "trnav_2ws_core/math_utils.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"

#include <algorithm>
#include <chrono>
#include <thread>

namespace trnav_2ws_action_server::spin
{

SpinActionServer::SpinActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<Spin>(node, std::move(action_mutex), "amr_motion_spin_abstract",
                                                  "/motion/wheel_cmd/spin")
{
    // Spin precision parameters (safeParam handles declare-if-not-declared)
    min_speed_dps_ = safeParam("min_speed_dps", 2.0);
    fine_correction_threshold_deg_ = safeParam("fine_correction_threshold_deg", 0.3);
    spin_max_timeout_sec_ = safeParam("spin_max_timeout_sec", 60.0);
    start_yaw_window_ = safeParam("start_yaw_avg_samples", 10);

    // 하이브리드 핸드오프 임계 + PID 회전 제어 게인 (SIL 검증 시드 — 실차 재튜닝)
    pid_band_deg_ = safeParam("pid_band_deg", 5.0);
    kp_spin_ = safeParam("kp_spin", 1.5);
    ki_spin_ = safeParam("ki_spin", 0.0);
    kd_spin_ = safeParam("kd_spin", 0.5);
    integral_limit_deg_ = safeParam("integral_limit_deg", 30.0);
    settle_rate_dps_ = safeParam("settle_rate_dps", 2.0);
    settle_count_ = safeParam("settle_count", 5);

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 3);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    // ── Hot-reload param 콜백 (HIL 게인 튜닝용; mpc/translate 선례 패턴) ──
    // 화이트리스트: kp_spin/ki_spin/kd_spin/pid_band_deg/min_speed_dps/integral_limit_deg/
    //               fine_correction_threshold_deg/control_rate_hz/spin_max_timeout_sec.
    //               범위 외 reject. ros2 param set 으로 실시간 반영(control_rate_hz 는 다음 goal 부터).
    params_cb_handle_ = node_->add_on_set_parameters_callback(
        [this](const std::vector<rclcpp::Parameter> &params) -> rcl_interfaces::msg::SetParametersResult {
            rcl_interfaces::msg::SetParametersResult result;
            result.successful = true;
            bool touched = false;
            auto chk = [&](const rclcpp::Parameter &p, double lo, double hi, double &dst) -> bool {
                double v = p.as_double();
                if (v < lo || v > hi)
                {
                    result.successful = false;
                    result.reason = p.get_name() + " out of range";
                    return false;
                }
                dst = v;
                touched = true;
                return true;
            };
            for (const auto &p : params)
            {
                if (p.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE)
                    continue;
                const std::string &n = p.get_name();
                bool ok = true;
                if (n == "kp_spin")
                    ok = chk(p, 0.0, 20.0, kp_spin_);
                else if (n == "ki_spin")
                    ok = chk(p, 0.0, 10.0, ki_spin_);
                else if (n == "kd_spin")
                    ok = chk(p, 0.0, 20.0, kd_spin_);
                else if (n == "pid_band_deg")
                    ok = chk(p, 0.5, 90.0, pid_band_deg_);
                else if (n == "min_speed_dps")
                    ok = chk(p, 0.0, 30.0, min_speed_dps_);
                else if (n == "integral_limit_deg")
                    ok = chk(p, 0.0, 360.0, integral_limit_deg_);
                else if (n == "fine_correction_threshold_deg")
                    ok = chk(p, 0.05, 5.0, fine_correction_threshold_deg_);
                else if (n == "control_rate_hz")
                    ok = chk(p, 5.0, 200.0, control_rate_hz_); // 다음 goal 부터 적용
                else if (n == "spin_max_timeout_sec")
                    ok = chk(p, 1.0, 300.0, spin_max_timeout_sec_);
                if (!ok)
                    return result;
            }
            if (touched)
                RCLCPP_INFO(node_->get_logger(),
                            "Spin gains hot-reloaded: kp=%.3f ki=%.3f kd=%.3f pid_band=%.1f min_spd=%.2f",
                            kp_spin_, ki_spin_, kd_spin_, pid_band_deg_, min_speed_dps_);
            return result;
        });

    RCLCPP_INFO(node_->get_logger(), "SpinActionServer initialized");
}

bool SpinActionServer::validateGoal(std::shared_ptr<const Spin::Goal> goal)
{
    if (std::abs(goal->target_angle) < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "Rejected: target_angle is 0");
        return false;
    }
    if (goal->max_angular_speed <= 0.0 || goal->angular_acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Rejected: invalid speed/acceleration");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(), "Spin goal accepted: %.1f deg", goal->target_angle);
    return true;
}

void SpinActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                            "Spin: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "Spin: mux active source → %d (spin)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "Spin: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "Spin: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    // 입력 정규화: |target_angle| > 180° 는 [-180,+180] 의 최단쪽 회전으로 자동 변환
    // (예: +270° → -90°, +540° → -180°, +360° → 0°).
    // 주의: std::remainder 는 round-half-even tie-break → +180.0 입력은 +180, -180.0 은 -180 유지
    // (이전 주석의 "−180 로 정착"은 오류). 180.0 vs 180.001 의 부호(방향) 반전은 아래 sign 경계
    // 결정화(kBoundaryEpsDeg)로 처리한다.
    const double target_angle_deg = trnav_2ws_core::normalizeAngleDeg(goal->target_angle);
    auto feedback = std::make_shared<Spin::Feedback>();
    auto result = std::make_shared<Spin::Result>();

    auto start_time = node_->now();

    // ── Early-Exit Gate: |target_angle_deg| < threshold 이면 모터 회전 없이 즉시 성공 ──
    if (std::abs(target_angle_deg) < fine_correction_threshold_deg_)
    {
        RCLCPP_INFO(node_->get_logger(),
                    "Spin early-exit: target=%.3f° (normalized=%.3f°) < threshold=%.3f deg (no motor motion)",
                    goal->target_angle, target_angle_deg, fine_correction_threshold_deg_);
        result->status = 0;
        this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
        result->actual_angle = 0.0;
        result->elapsed_time = (node_->now() - start_time).seconds();
        goal_handle->succeed(result);
        return;
    }

    rclcpp::Rate rate(control_rate_hz_);

    // Direction: + CCW, - CW. ±180° 경계 결정화 —
    // std::remainder 의 round-half-even tie-break 때문에 정확히 180.0 입력은 +180(CCW),
    // 180.001 입력은 -179.999(CW) 로 부호(회전방향)가 반전된다. |정규화|이 180° 근방이면
    // raw 입력 부호로 회전방향을 고정해 이 불연속을 제거한다 (shortest-path magnitude 는 유지).
    constexpr double kBoundaryEpsDeg = 0.5;
    const double target_abs = std::abs(target_angle_deg); // deg, 항상 ≤ 180
    const double sign = (target_abs > 180.0 - kBoundaryEpsDeg)
                            ? ((goal->target_angle >= 0.0) ? 1.0 : -1.0)  // 경계: raw 부호
                            : ((target_angle_deg >= 0.0) ? 1.0 : -1.0);   // 그 외: 정규화 부호 (최단)
    const double max_omega_dps = goal->max_angular_speed;   // deg/s
    const double accel_dps2 = goal->angular_acceleration;   // deg/s²

    // Compute spin steer angle using IK
    auto ik_result = ik_->computeSpin(sign * 0.1);
    const double spin_steer_front = ik_result.wheels[0].steer_rad;
    const double spin_steer_rear = ik_result.wheels[1].steer_rad;

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

        publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear);
        feedback->current_angle = 0.0;
        feedback->current_speed = 0.0;
        goal_handle->publish_feedback(feedback);

        bool front_ok = std::abs(last_angle_front_.load() - spin_steer_front) < steer_tolerance_rad_;
        bool rear_ok = std::abs(last_angle_rear_.load() - spin_steer_rear) < steer_tolerance_rad_;
        if (front_ok && rear_ok)
        {
            break;
        }

        if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "Phase 0 steer timeout");
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

    // ── IMU 수신 확인 ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting spin");
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
        result->status = -3;
        this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
        result->actual_angle = 0.0;
        result->elapsed_time = (node_->now() - start_time).seconds();
        goal_handle->abort(result);
        return;
    }

    // ── start_yaw 원형 이동평균 ──
    // 시작 1회 샘플의 IMU 노이즈가 절대 target 기준(target_imu_yaw) 전체를 오프셋하므로,
    // 차체 정지(Phase 0: 구동속도 0) 직후 N 샘플을 평균한다. yaw 는 ±π wrap 이므로 선형 평균은
    // ±180° 부근에서 오평균(179°,-179°→0°) → 반드시 원형평균 atan2(Σsin, Σcos).
    // 윈도우 = N / control_rate_hz (yaml control_rate_hz=50 → N=10 = 0.2s, 정지 구간이라 무해).
    double sin_sum = 0.0, cos_sum = 0.0;
    for (int i = 0; i < start_yaw_window_ && rclcpp::ok(); ++i)
    {
        publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear); // steer-hold 유지 (cmd 끊김 방지)
        double y = last_yaw_rad_.load();
        sin_sum += std::sin(y);
        cos_sum += std::cos(y);
        rate.sleep();
    }
    double start_yaw = std::atan2(sin_sum, cos_sum);
    // 절대 target 앵커는 결정화된 회전방향(sign·target_abs) 기준 — 경계에서 sign 이 정규화
    // 부호와 다를 수 있으므로 target_angle_deg 가 아니라 sign*target_abs 를 사용해야 일관.
    double spin_angle_rad = sign * target_abs * M_PI / 180.0;
    double target_imu_yaw = start_yaw + spin_angle_rad;

    const double dt = 1.0 / control_rate_hz_;
    const double eps_rad = kBoundaryEpsDeg * M_PI / 180.0;

    // 부호 포함 남은 오차[deg] (global, antipode-safe). +면 sign 방향으로 더 회전 필요, −면 overshoot.
    // 시작 antipode(|e|≈180°)는 부호 모호 → 결정화된 sign 으로 고정.
    auto remaining_signed_deg = [&](double cur_yaw) -> double {
        double e = trnav_2ws_core::normalizeAngle(target_imu_yaw - cur_yaw);
        if (std::fabs(std::fabs(e) - M_PI) < eps_rad)
            e = sign * std::fabs(e);
        return e * 180.0 / M_PI;
    };

    // ── Stage 1 (Coarse): 사다리꼴 프로파일 — 남은 오차 > pid_band 구간 ──
    // 종료: 남은 오차 ≤ pid_band → Stage 2(PID) 인계 (또는 profile DONE).
    trnav_2ws_core::TrapezoidalProfile profile(target_abs, max_omega_dps, accel_dps2);

    while (rclcpp::ok())
    {
        double current_yaw = last_yaw_rad_.load();
        double error_deg = remaining_signed_deg(current_yaw);
        double remaining_deg = std::fabs(error_deg);
        double progress_deg = target_abs - remaining_deg; // 0..target (profile 입력)
        if (progress_deg < 0.0)
            progress_deg = 0.0;

        auto prof_out = profile.getSpeed(progress_deg);

        if (remaining_deg <= pid_band_deg_ || prof_out.phase == trnav_2ws_core::ProfilePhase::DONE)
            break;

        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = sign * progress_deg;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        if ((node_->now() - start_time).seconds() > spin_max_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "Spin global timeout (%.1f s)", spin_max_timeout_sec_);
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -3;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = sign * progress_deg;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->abort(result);
            return;
        }

        double omega_dps = prof_out.speed;
        if (prof_out.phase != trnav_2ws_core::ProfilePhase::DONE && omega_dps < min_speed_dps_)
            omega_dps = min_speed_dps_;
        double omega_rad = sign * omega_dps * M_PI / 180.0;

        auto ik_out = ik_->computeSpin(omega_rad);
        publishWheelCmd(ik_out.wheels[0].wheel_speed * ik_out.wheels[0].direction, ik_out.wheels[0].steer_rad,
                        ik_out.wheels[1].wheel_speed * ik_out.wheels[1].direction, ik_out.wheels[1].steer_rad);

        uint8_t phase_id = (prof_out.phase == trnav_2ws_core::ProfilePhase::ACCEL)    ? 1
                           : (prof_out.phase == trnav_2ws_core::ProfilePhase::CRUISE) ? 2
                                                                                         : 3;
        feedback->phase = phase_id;
        feedback->current_angle = sign * progress_deg;
        feedback->current_speed = sign * omega_dps;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // ── Stage 2 (Fine, PID): 남은 오차 ≤ pid_band — bang-bang 대체 ──
    // omega_dps = Kp·e + Ki·∫e + Kd·de/dt,  e = 부호 포함 남은 오차[deg] (overshoot 시 부호 반전→역보정).
    // |omega| 상한 max_angular_speed 만 clamp — 하한 floor 없음(fine 은 0 으로 자연 정착), 방향 보존.
    // 종료: (|e| ≤ fine_correction_threshold_deg AND |회전율| ≤ settle_rate_dps) 가 settle_count cycle 연속, or fine timeout.
    double integral = 0.0;
    int settle_cnt = 0;   // settle 게이트: |오차|≤threshold AND |실측 회전율|≤settle_rate 연속 cycle 카운트
    double prev_error = remaining_signed_deg(last_yaw_rad_.load());
    double final_traveled_pid = sign * (target_abs - std::fabs(prev_error));
    // 적응형 fine 타임아웃 = 진행시간(target_abs / max_ω) × 3 (최소 2s).
    // 고정 타이머가 수렴 전에 0 강제 종료하던 문제 해결 — 기동 규모(각도·속도)에 비례.
    const double fine_timeout_sec = std::max(2.0, 3.0 * target_abs / std::max(1.0, max_omega_dps));
    auto fine_start = node_->now();

    while (rclcpp::ok())
    {
        double current_yaw = last_yaw_rad_.load();
        double error_deg = remaining_signed_deg(current_yaw);
        double remaining_deg = std::fabs(error_deg);
        final_traveled_pid = sign * (target_abs - remaining_deg);

        // (|e|≤threshold 즉시 종료 제거 — 순서 PID 는 setpoint 를 계속 제어해 정착시킨다.
        //  종료는 fine timeout 으로만. PID 가 e→0 이면 ω=Kp·e→0 으로 목표서 정지 유지.)

        if (goal_handle->is_canceling())
        {
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -1;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = final_traveled_pid;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->canceled(result);
            return;
        }

        if ((node_->now() - fine_start).seconds() > fine_timeout_sec)
        {
            RCLCPP_WARN(node_->get_logger(), "Spin fine(PID) timeout (%.1fs), error=%.2f deg", fine_timeout_sec,
                        error_deg);
            publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear);
            break;
        }
        if ((node_->now() - start_time).seconds() > spin_max_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "Spin global timeout (%.1f s)", spin_max_timeout_sec_);
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            result->status = -3;
            this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
            result->actual_angle = final_traveled_pid;
            result->elapsed_time = (node_->now() - start_time).seconds();
            goal_handle->abort(result);
            return;
        }

        // ── PID ──
        integral += error_deg * dt;
        integral = std::max(-integral_limit_deg_, std::min(integral_limit_deg_, integral)); // anti-windup
        double derivative = (error_deg - prev_error) / dt;   // = −(실측 yaw rate)[deg/s]
        prev_error = error_deg;

        // ── settle 게이트 조기종료 (과회전 안전): |오차|≤threshold AND |실측 회전율|≤settle_rate 가
        //    settle_count cycle 연속 → 정착 확인 후 종료. 옛 즉시종료(|e|≤thr 만)와 달리 실제 정지까지
        //    확인하므로 종료 시 잔여 회전속도 0 → coast 과회전 없음. fine_timeout 은 미수렴 안전망으로 유지.
        if (std::fabs(error_deg) <= fine_correction_threshold_deg_ && std::fabs(derivative) <= settle_rate_dps_)
        {
            if (++settle_cnt >= settle_count_)
            {
                RCLCPP_INFO(node_->get_logger(),
                            "Spin fine settled (e=%.2f deg, |rate|=%.2f<=%.2f dps, %d cyc) — early stop",
                            error_deg, std::fabs(derivative), settle_rate_dps_, settle_count_);
                publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear);
                break;
            }
        }
        else
        {
            settle_cnt = 0;
        }

        double omega_dps = kp_spin_ * error_deg + ki_spin_ * integral + kd_spin_ * derivative;

        // |omega| 상한 max_angular_speed 만 clamp — 하한 floor 제거.
        // (floor 를 fine 에 걸면 목표 근처서도 ≥min 강제 → 한계진동. yaw_control near_goal 패턴:
        //  floor 는 coarse 에만, fine 은 0 으로 자연 정착. 정지마찰 잔류는 ki 가 흡수.)
        double dir = (omega_dps >= 0.0) ? 1.0 : -1.0;
        double mag = std::min(max_omega_dps, std::fabs(omega_dps));
        omega_dps = dir * mag;

        auto ik_out = ik_->computeSpin(omega_dps * M_PI / 180.0);
        publishWheelCmd(ik_out.wheels[0].wheel_speed * ik_out.wheels[0].direction, ik_out.wheels[0].steer_rad,
                        ik_out.wheels[1].wheel_speed * ik_out.wheels[1].direction, ik_out.wheels[1].steer_rad);

        feedback->phase = 3;
        feedback->current_angle = final_traveled_pid;
        feedback->current_speed = omega_dps;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    // Stop driving (final stop after fine correction)
    publishWheelCmd(0.0, spin_steer_front, 0.0, spin_steer_rear);

    // ── Phase 4: Steer Return (if !hold_steer) ──
    double final_yaw = last_yaw_rad_.load();
    double final_traveled =
        sign * (target_abs - std::fabs(trnav_2ws_core::normalizeAngle(target_imu_yaw - final_yaw)) * 180.0 / M_PI);

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
                result->actual_angle = final_traveled;
                result->elapsed_time = (node_->now() - start_time).seconds();
                goal_handle->canceled(result);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);
            feedback->current_angle = final_traveled;
            feedback->current_speed = 0.0;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - exit_steer_rad) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - exit_steer_rad) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
            {
                break;
            }

            if ((node_->now() - phase4_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "Phase 4 steer timeout (non-critical)");
                break;
            }

            rate.sleep();
        }
    }

    // Success
    result->status = 0;
    this->reportResult(result->status); // 종료 코드 토픽 발행 (bag 기록용)
    result->actual_angle = final_traveled;
    result->elapsed_time = (node_->now() - start_time).seconds();
    goal_handle->succeed(result);

    double final_error = trnav_2ws_core::normalizeAngle(target_imu_yaw - last_yaw_rad_.load()) * 180.0 / M_PI;
    RCLCPP_INFO(node_->get_logger(),
                "Spin complete: target=%.1f° (normalized=%.1f°), actual=%.1f, error=%.2f deg, time=%.1f s",
                goal->target_angle, target_angle_deg, final_traveled, final_error, result->elapsed_time);
    if (std::abs(final_error) > 2.0)
    {
        RCLCPP_WARN(node_->get_logger(), "Spin precision warning: final error %.2f deg exceeds 2.0 deg threshold",
                    final_error);
    }
}

} // namespace trnav_2ws_action_server::spin
