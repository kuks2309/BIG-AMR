#include "trnav_2ws_action_server/yaw_control_reverse/yaw_control_reverse_action_server.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"

#include <chrono>
#include <cmath>
#include <thread>

#include "trnav_2ws_core/math_utils.hpp"

namespace trnav_2ws_action_server::yaw_control_reverse
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

YawControlReverseActionServer::YawControlReverseActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<YawControlReverse>(node, std::move(action_mutex),
                                                               "amr_motion_yaw_control_reverse_abstract",
                                                               "/motion/wheel_cmd/yaw_control_reverse")
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

    // YawControlReverse-specific parameters (yaw_control_reverse_* prefix)
    max_timeout_sec_ = safeParam("yaw_control_reverse_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("yaw_control_reverse_enable_localization_watchdog", true);
    walk_accel_limit_ = safeParam("yaw_control_reverse_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("yaw_control_reverse_walk_decel_limit", 1.0);
    steer_rate_limit_ = safeParam("yaw_control_reverse_steer_rate_limit", 0.35);
    min_vx_ = safeParam("yaw_control_reverse_min_vx", 0.02);
    enable_heading_divergence_guard_ = safeParam("yaw_control_reverse_enable_heading_divergence_guard", true);
    heading_divergence_deg_ = safeParam("yaw_control_reverse_heading_divergence_deg", 5.0);
    heading_divergence_count_ = safeParam("yaw_control_reverse_heading_divergence_count", 10);
    gate_blocked_timeout_sec_ = safeParam("yaw_control_reverse_gate_blocked_timeout_sec", 5.0);

    // TransientGuard
    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // LocalizationMonitor (TF-only, topic 폐기 2026-05-18)
    LocalizationMonitor::Params lm_params;
    lm_params.localization_timeout_sec = safeParam("yaw_control_reverse_localization_timeout_sec", 2.0);
    lm_params.position_jump_threshold = safeParam("yaw_control_reverse_position_jump_threshold", 0.3);
    lm_params.enable_watchdog = enable_localization_watchdog_;
    // pose 토픽 파라미터화 — 전진판과 같은 규약. 종전에는 이 줄이 없어 yaml 의
    // `yaw_control_reverse_pose_topic` 이 **읽히지 않는 죽은 키**였고, 그 값이 실재하지 않는
    // 토픽을 가리켜 「이 액션은 pose 를 못 받는다」는 오진을 낳았다(실제로는 기본값 /robot_pose 사용).
    lm_params.pose_topic = safeParam<std::string>("yaw_control_reverse_pose_topic", std::string("/robot_pose"));
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 7);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    // ── Hot-reload param 콜백 ──
    // 종전에는 콜백이 없어 `ros2 param set` 이 **성공을 반환하면서 거동을 바꾸지 않았다**
    // (2026-08-10 실측: 발산 임계를 set 으로 낮췄으나 가드가 발화하지 않았다).
    // 화이트리스트만 반영하고 **자기 네임스페이스의 나머지 키는 명시적으로 거부**한다 —
    // 조용히 성공하는 것보다 시끄럽게 실패하는 편이 낫다. 값이 안 먹는 것을 즉시 알 수 있다.
    // ⚠ 다른 네임스페이스(기하·플랫폼 등 베이스 소관)는 건드리지 않는다 — 판단 근거가 없다.
    // 근거·설계: docs/adr/2026-08-10-yaw-control-param-callback.md
    params_cb_handle_ = node_->add_on_set_parameters_callback(
        [this](const std::vector<rclcpp::Parameter> &params) -> rcl_interfaces::msg::SetParametersResult {
            rcl_interfaces::msg::SetParametersResult result;
            result.successful = true;
            auto rng = [&](const rclcpp::Parameter &p, double lo, double hi, double &dst) {
                double v = p.as_double();
                if (v < lo || v > hi)
                {
                    result.successful = false;
                    result.reason = p.get_name() + " out of range [" + std::to_string(lo) + ", " +
                                    std::to_string(hi) + "]";
                    return;
                }
                dst = v;
            };
            for (const auto &p : params)
            {
                const std::string &n = p.get_name();
                if (n == "yaw_control_reverse_max_timeout_sec")
                    rng(p, 1.0, 600.0, max_timeout_sec_);
                else if (n == "yaw_control_reverse_min_vx")
                    rng(p, 0.0, 1.0, min_vx_);
                else if (n == "yaw_control_reverse_walk_accel_limit")
                    rng(p, 0.01, 10.0, walk_accel_limit_);
                else if (n == "yaw_control_reverse_walk_decel_limit")
                    rng(p, 0.01, 10.0, walk_decel_limit_);
                else if (n == "yaw_control_reverse_steer_rate_limit")
                    rng(p, 0.01, 10.0, steer_rate_limit_);
                else if (n == "yaw_control_reverse_heading_divergence_deg")
                    rng(p, 0.01, 90.0, heading_divergence_deg_);
                else if (n == "yaw_control_reverse_gate_blocked_timeout_sec")
                    rng(p, 0.05, 120.0, gate_blocked_timeout_sec_);
                else if (n == "yaw_control_reverse_heading_divergence_count")
                {
                    int v = static_cast<int>(p.as_int());
                    if (v < 1 || v > 1000)
                    {
                        result.successful = false;
                        result.reason = n + " out of range [1, 1000]";
                    }
                    else
                        heading_divergence_count_ = v;
                }
                else if (n == "yaw_control_reverse_enable_heading_divergence_guard")
                    enable_heading_divergence_guard_ = p.as_bool();
                else if (n == "yaw_control_reverse_enable_localization_watchdog")
                    enable_localization_watchdog_ = p.as_bool(); // 다음 goal 부터 적용
                else if (n.rfind("yaw_control_reverse_", 0) == 0 || n.rfind("transient_", 0) == 0)
                {
                    // 생성자에서만 읽히는 키 — 구독·가드·모니터가 그 시점에 만들어진다.
                    result.successful = false;
                    result.reason = n + " 는 생성자에서만 읽힌다 — yaml 을 고치고 노드를 재기동할 것";
                }
                if (!result.successful)
                    return result;
            }
            return result;
        });

    RCLCPP_INFO(node_->get_logger(), "YawControlReverseActionServer initialized (REVERSE direction only)");
}

bool YawControlReverseActionServer::validateGoal(std::shared_ptr<const YawControlReverse::Goal> goal)
{
    if (goal->target_distance <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControlReverse rejected: target_distance <= 0");
        return false;
    }
    // vx_max 는 magnitude 만 허용 (>0). 부호는 내부에서 항상 반전.
    if (goal->vx_max <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControlReverse rejected: vx_max <= 0 (magnitude only)");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControlReverse rejected: acceleration <= 0");
        return false;
    }
    if (goal->max_steer_deg <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "YawControlReverse rejected: max_steer_deg <= 0");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "YawControlReverse goal accepted: target_yaw=%.1f deg, dist=%.3f m, |vx|=%.3f m/s, counter_steer=%s",
                goal->target_yaw_deg, goal->target_distance, goal->vx_max,
                goal->counter_steer ? "true" : "false");
    return true;
}

void YawControlReverseActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                            "YawControlReverse: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "YawControlReverse: mux active source → %d (yaw_control_reverse)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "YawControlReverse: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "YawControlReverse: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<YawControlReverse::Feedback>();
    auto result = std::make_shared<YawControlReverse::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

    // 부호 정책 (yaw_control 패턴 = IK 가 vx_signed<0 으로 wheel direction 자동 반전):
    //   vx_signed = -vx_profile
    //   IK 입력에 vx_signed 직접 사용 → wheel_speed*direction 이 이미 음수
    //   → wheel cmd 추가 부호 곱하기 *없음*. translate_reverse 의 kReverseDir 패턴은
    //     PathController(forward 전용) 재사용 trick 의 부산물이라 yaw_control_reverse 엔
    //     적용하지 않는다. (SIL R1 1차에서 이중 부호 반전으로 발견 후 정정)

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
        RCLCPP_ERROR(node_->get_logger(), "YawControlReverse: IMU data not received, aborting (-4)");
        finish_abort(-4, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── Acquire start pose from tf2 ──
    double start_x = 0.0, start_y = 0.0, start_yaw_map = 0.0;
    if (!loc_monitor_->lookupMapToBase(start_x, start_y, start_yaw_map))
    {
        RCLCPP_ERROR(node_->get_logger(), "YawControlReverse: tf2 map->base_link not available, aborting (-4)");
        finish_abort(-4, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── yaw_offset calibration: 1 time at start (map yaw absolute 그대로 사용) ──
    // effective_yaw 보정은 적용하지 않음 — IMU yaw 직접 PID 추종.
    double start_yaw_imu = last_yaw_rad_.load();
    double yaw_offset = normalizeAngle(start_yaw_map - start_yaw_imu);

    RCLCPP_INFO(
        node_->get_logger(),
        "YawControlReverse yaw calibration: start_yaw_map=%.2f deg, start_yaw_imu=%.2f deg, offset=%.2f deg",
        start_yaw_map * 180.0 / M_PI, start_yaw_imu * 180.0 / M_PI, yaw_offset * 180.0 / M_PI);

    guard_->reset();

    // ── Phase 0: Steer Align (align to delta=0) ──
    {
        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "YawControlReverse Phase 0: steer alignment to 0");

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "YawControlReverse cancelled during Phase 0");
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
                RCLCPP_WARN(node_->get_logger(), "YawControlReverse Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }

            rate.sleep();
        }

        RCLCPP_INFO(node_->get_logger(), "YawControlReverse Phase 0 complete, starting trapezoidal profile");
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

    // ── Trapezoidal profile (vx_max 는 magnitude 입력) ──
    TrapezoidalProfile profile(goal->target_distance, goal->vx_max, goal->acceleration);

    bool reached = false;
    int heading_diverge_cnt = 0; // 조대 헤딩 발산 연속 카운터
    rclcpp::Time gate_blocked_since = node_->now();
    bool gate_blocked_active = false;
    double current_distance = 0.0;
    double current_yaw_deg = 0.0;

    int tf_fail_count = 0;
    const int tf_fail_max = 50;

    double rx = start_x, ry = start_y;

    // ── Phase 1-3: Trapezoidal + PID heading ──
    while (rclcpp::ok() && !reached)
    {
        double map_yaw_rad = 0.0;
        bool map_yaw_fresh = false;
        if (loc_monitor_->lookupMapToBase(rx, ry, map_yaw_rad))
        {
            tf_fail_count = 0;
            map_yaw_fresh = true; // 이번 주기 맵 heading 유효 — 발산 탐지에 쓴다
        }
        else
        {
            tf_fail_count++;
            if (tf_fail_count >= tf_fail_max)
            {
                RCLCPP_ERROR(node_->get_logger(), "YawControlReverse: TF2 failed %d consecutive times, aborting",
                             tf_fail_count);
                double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
                finish_abort(-6, current_distance, calibrated_yaw * 180.0 / M_PI,
                             normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
                return;
            }
        }

        if (goal_handle->is_canceling())
        {
            RCLCPP_INFO(node_->get_logger(), "YawControlReverse cancelled at dist=%.3f m", current_distance);
            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            finish_abort(-1, current_distance, calibrated_yaw * 180.0 / M_PI,
                         normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "YawControlReverse global timeout (%.1f s), dist=%.3f m",
                        max_timeout_sec_, current_distance);
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
            RCLCPP_ERROR(node_->get_logger(), "YawControlReverse: localization health fail (%s, code=%d) at dist=%.3f m",
                         reason_str, code, current_distance);
            double calibrated_yaw = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
            finish_abort(code, current_distance, calibrated_yaw * 180.0 / M_PI,
                         normalizeAngleDeg(goal->target_yaw_deg - calibrated_yaw * 180.0 / M_PI), start_time);
            return;
        }

        // Distance via start_yaw projection — reverse 진행 시 projection<0,
        // progress 의미는 |projection| (yaw_control 동일 패턴)
        double dx = rx - start_x;
        double dy = ry - start_y;
        double projection = dx * std::cos(start_yaw_map) + dy * std::sin(start_yaw_map);
        current_distance = std::fabs(projection);

        // Profile speed (magnitude)
        double clamped_pos = std::fabs(projection);
        auto prof_out = profile.getSpeed(clamped_pos);
        double vx_profile = prof_out.speed; // always >= 0 from profile

        // Floor on vx_profile to prevent stuck-at-start (TrapezoidalProfile.getSpeed(0)==0).
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

        // Calibrated yaw from IMU + fixed offset (map yaw absolute 그대로)
        double calibrated_yaw_rad = normalizeAngle(last_yaw_rad_.load() + yaw_offset);
        current_yaw_deg = calibrated_yaw_rad * 180.0 / M_PI;

        // ── 조대 헤딩 발산 탐지 (제어에는 관여하지 않는다) ──
        if (enable_heading_divergence_guard_ && map_yaw_fresh)
        {
            double diverge_deg =
                std::fabs(normalizeAngleDeg(current_yaw_deg - map_yaw_rad * 180.0 / M_PI));
            if (diverge_deg > heading_divergence_deg_)
            {
                if (++heading_diverge_cnt >= heading_divergence_count_)
                {
                    RCLCPP_ERROR(node_->get_logger(),
                                 "YawControlReverse heading divergence: |IMU기준 %.2f° − 맵 %.2f°| = %.2f° > %.2f° "
                                 "가 %d cycle 연속 — IMU 가 회전을 놓쳤을 수 있다. abort(-7)",
                                 current_yaw_deg, map_yaw_rad * 180.0 / M_PI, diverge_deg,
                                 heading_divergence_deg_, heading_divergence_count_);
                    finish_abort(-7, current_distance, current_yaw_deg,
                                 normalizeAngleDeg(goal->target_yaw_deg - current_yaw_deg), start_time);
                    return;
                }
            }
            else
            {
                heading_diverge_cnt = 0;
            }
        }

        // PID error (deg) — reverse: 항상 부호 반전 (forward 분기 제거)
        double err_deg = normalizeAngleDeg(goal->target_yaw_deg - current_yaw_deg);
        err_deg = -err_deg;

        // PID
        pid_ierr += err_deg * dt;
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

        // vx 항상 음수 (reverse 전용)
        double vx_signed = -vx_profile;

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

        // ── 조향 미도달 지속 감시 ──
        if (guard_out.gate_blocked)
        {
            if (!gate_blocked_active)
            {
                gate_blocked_active = true;
                gate_blocked_since = node_->now();
            }
            else if ((node_->now() - gate_blocked_since).seconds() > gate_blocked_timeout_sec_)
            {
                RCLCPP_ERROR(node_->get_logger(),
                             "YawControlReverse 조향 미도달 %.1f s 지속 — 지령 F=%.2f°/R=%.2f° 대 실제 "
                             "F=%.2f°/R=%.2f°. 조향축이 지령을 실행하지 못한다. abort(-8)",
                             gate_blocked_timeout_sec_, delta_f * 180.0 / M_PI, delta_r * 180.0 / M_PI,
                             last_angle_front_.load() * 180.0 / M_PI, last_angle_rear_.load() * 180.0 / M_PI);
                finish_abort(-8, current_distance, current_yaw_deg,
                             normalizeAngleDeg(goal->target_yaw_deg - current_yaw_deg), start_time);
                return;
            }
        }
        else
        {
            gate_blocked_active = false;
        }

        // Wheel velocity from IK — vx_signed<0 입력으로 IK 가 wheel direction 자동 처리.
        // 출력단에 추가 부호 곱하기 없음 (yaw_control 동일 패턴, R1 SIL 1차 정정).
        double vel_f = ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction * speed_scale;
        double vel_r = ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction * speed_scale;

        // Walk velocity profile (accel/decel limiter) — reverse 시 cur/tgt 모두 음수.
        // translate_reverse 와 동일하게 magnitude 기반 비교로 가·감속 비대칭 방지.
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

        publishWheelCmd(vel_f, expected_steer_f, vel_r, expected_steer_r);

        // Debug log (~10 Hz)
        static int dbg_cnt = 0;
        if (++dbg_cnt % 5 == 0)
        {
            RCLCPP_INFO(node_->get_logger(),
                        "[YawControlReverse] phase=%d dist=%.3f/%.3fm yaw=%.1f° err=%.2f° steer=%.1f° vx=%.3f %s",
                        static_cast<int>(prof_out.phase), current_distance, goal->target_distance, current_yaw_deg,
                        err_deg, delta_deg, vx_signed * speed_scale,
                        guard_out.gate_blocked ? "BLOCKED" : "OK");
        }

        // Feedback (current_vx 항상 음수)
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
        feedback->current_vx = vx_signed * speed_scale; // 항상 ≤ 0
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
                "YawControlReverse Phase 1-3 complete: dist=%.3f m, yaw=%.1f deg, err=%.2f deg", current_distance,
                final_yaw_deg, final_err_deg);

    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "YawControlReverse cancelled after Phase 1-3");
        finish_abort(-1, current_distance, final_yaw_deg, final_err_deg, start_time);
        return;
    }

    // ── Phase 4: Steer Return (if !hold_steer) ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "YawControlReverse Phase 4: steer return to %.1f deg",
                    goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "YawControlReverse cancelled during Phase 4");
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
                RCLCPP_WARN(node_->get_logger(), "YawControlReverse Phase 4 steer timeout (non-critical)");
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
                "YawControlReverse complete: dist=%.3f/%.3f m, yaw=%.1f deg, err=%.2f deg, time=%.1f s",
                current_distance, goal->target_distance, final_yaw_deg, final_err_deg, result->elapsed_time);
}

} // namespace trnav_2ws_action_server::yaw_control_reverse
