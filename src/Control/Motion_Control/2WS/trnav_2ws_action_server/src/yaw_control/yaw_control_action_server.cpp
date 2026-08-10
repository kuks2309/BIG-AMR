#include "trnav_2ws_action_server/yaw_control/yaw_control_action_server.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"

#include <chrono>
#include <cmath>
#include <functional>
#include <thread>

#include "trnav_2ws_core/math_utils.hpp"
#include "trnav_2ws_core/velocity_ramp.hpp"

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
    final_yaw_tol_deg_ = safeParam("yaw_control_final_yaw_tolerance_deg", 10.0);
    enable_final_yaw_check_ = safeParam("yaw_control_enable_final_yaw_check", true);
    max_timeout_sec_ = safeParam("yaw_control_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("yaw_control_enable_localization_watchdog", true);
    walk_accel_limit_ = safeParam("yaw_control_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("yaw_control_walk_decel_limit", 1.0);
    steer_rate_limit_ = safeParam("yaw_control_steer_rate_limit", 0.35);
    min_vx_ = safeParam("yaw_control_min_vx", 0.02);
    enable_heading_divergence_guard_ = safeParam("yaw_control_enable_heading_divergence_guard", true);
    heading_divergence_deg_ = safeParam("yaw_control_heading_divergence_deg", 5.0);
    heading_divergence_count_ = safeParam("yaw_control_heading_divergence_count", 10);
    gate_blocked_timeout_sec_ = safeParam("yaw_control_gate_blocked_timeout_sec", 5.0);

    // TransientGuard
    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    runtime_gate_threshold_deg_ = tg_params.runtime_gate_threshold;
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

            // ⚠ **검증과 반영을 분리한다(2단계).** 종전에는 검사를 통과하는 즉시 멤버에
            //   써 버리고 뒤의 키가 거부되면 `return` 했다 — 그러면 rclcpp 는 파라미터
            //   저장소에 아무것도 반영하지 않는데 **앞의 키는 이미 멤버에 적용돼 있어**
            //   `ros2 param get` 이 보고하는 값과 실제 거동이 영구히 어긋난다.
            //   (「거짓 성공」을 없애려다 「거짓 실패 + 은닉 적용」을 만든 셈이었다.)
            //   여기서는 전부 통과했을 때만 커밋한다.
            std::vector<std::function<void()>> commits;

            auto rng = [&](const rclcpp::Parameter &p, double lo, double hi,
                           std::atomic<double> &dst) {
                if (p.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE)
                {
                    result.successful = false;
                    result.reason = p.get_name() + " 는 double 이어야 한다(정수 리터럴은 int 로 읽힌다)";
                    return;
                }
                double v = p.as_double();
                if (v < lo || v > hi)
                {
                    result.successful = false;
                    result.reason = p.get_name() + " out of range [" + std::to_string(lo) + ", " +
                                    std::to_string(hi) + "]";
                    return;
                }
                commits.emplace_back([&dst, v]() { dst.store(v); });
            };
            auto flag = [&](const rclcpp::Parameter &p, std::atomic<bool> &dst) {
                if (p.get_type() != rclcpp::ParameterType::PARAMETER_BOOL)
                {
                    result.successful = false;
                    result.reason = p.get_name() + " 는 bool 이어야 한다";
                    return;
                }
                bool v = p.as_bool();
                commits.emplace_back([&dst, v]() { dst.store(v); });
            };

            for (const auto &p : params)
            {
                const std::string &n = p.get_name();
                if (n == "yaw_control_max_timeout_sec")
                    rng(p, 1.0, 600.0, max_timeout_sec_);
                else if (n == "yaw_control_min_vx")
                    rng(p, 0.0, 1.0, min_vx_);
                else if (n == "yaw_control_walk_accel_limit")
                    rng(p, 0.01, 10.0, walk_accel_limit_);
                else if (n == "yaw_control_walk_decel_limit")
                    rng(p, 0.01, 10.0, walk_decel_limit_);
                else if (n == "yaw_control_steer_rate_limit")
                    rng(p, 0.01, 10.0, steer_rate_limit_);
                else if (n == "yaw_control_heading_divergence_deg")
                    rng(p, 0.01, 90.0, heading_divergence_deg_);
                else if (n == "yaw_control_gate_blocked_timeout_sec")
                    rng(p, 0.05, 120.0, gate_blocked_timeout_sec_);
                else if (n == "yaw_control_heading_divergence_count")
                {
                    if (p.get_type() != rclcpp::ParameterType::PARAMETER_INTEGER)
                    {
                        result.successful = false;
                        result.reason = n + " 는 정수여야 한다";
                    }
                    else
                    {
                        int v = static_cast<int>(p.as_int());
                        if (v < 1 || v > 1000)
                        {
                            result.successful = false;
                            result.reason = n + " out of range [1, 1000]";
                        }
                        else
                            commits.emplace_back([this, v]() { heading_divergence_count_.store(v); });
                    }
                }
                else if (n == "yaw_control_enable_heading_divergence_guard")
                    flag(p, enable_heading_divergence_guard_);
                else if (n == "yaw_control_enable_localization_watchdog")
                    flag(p, enable_localization_watchdog_);
                else if (n.rfind("yaw_control_", 0) == 0 || n.rfind("transient_", 0) == 0)
                {
                    // 생성자에서만 읽히는 키 — 구독·가드·모니터가 그 시점에 만들어진다.
                    result.successful = false;
                    result.reason = n + " 는 생성자에서만 읽힌다 — yaml 을 고치고 노드를 재기동할 것";
                }
                if (!result.successful)
                    return result;   // 아무것도 커밋하지 않았다
            }

            for (auto &c : commits)
                c();
            return result;
        });

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
    // 헤딩 발산(−7) 판정에 쓸 맵 자세의 최대 나이. 측위 타임아웃(2.0 s)보다 훨씬 짧아야
    // 한다 — −7 은 10 cycle(50 Hz 기준 0.2 s)이면 발화하므로, 그보다 느슨하면 얼어붙은
    // 맵 자세로 IMU 를 탓하게 된다.
    constexpr double kHeadingPoseMaxAgeSec = 0.3;
    int heading_diverge_cnt = 0; // 조대 헤딩 발산 연속 카운터 — **서로 다른 pose 샘플**을 센다
    rclcpp::Time heading_last_stamp(0, 0, RCL_ROS_TIME); // 마지막으로 센 pose 의 stamp
    rclcpp::Time gate_blocked_since = node_->now(); // gate_blocked 연속 시작 시각
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
        rclcpp::Time map_stamp;
        if (loc_monitor_->lookupMapToBase(rx, ry, map_yaw_rad, map_stamp))
        {
            tf_fail_count = 0;
            // ⚠ `lookupMapToBase` 는 **신선도를 보지 않는다** — `pose_received_` 가 한 번
            //   참이 되면 영원히 참을 돌려주고 마지막 값을 준다. 그래서 종전의
            //   `map_yaw_fresh = true` 는 「이번 주기 유효」가 아니라 「언젠가 1회 수신」이었다.
            //   측위가 얼면 맵 yaw 만 고정되고 IMU 는 계속 도므로 괴리가 회전량만큼 커져
            //   **−7 이 0.2 s 만에 발화**하고 「측위는 멀쩡한데 IMU 가 어긋났다」고 오진한다
            //   (측위 타임아웃은 2.0 s 라 −4 보다 −7 이 먼저 뜬다). 실제로는 정반대다.
            //   판단 근거가 낡았으면 판단을 보류하고 카운터도 리셋한다.
            const double pose_age_sec = (node_->now() - map_stamp).seconds();
            map_yaw_fresh = (pose_age_sec <= kHeadingPoseMaxAgeSec);
            if (!map_yaw_fresh)
            {
                heading_diverge_cnt = 0;
            }
        }
        else
        {
            // 자세를 못 얻었으면 헤딩 발산 판정의 근거도 없다 — 카운터를 리셋해
            // 공백을 사이에 낀 누적이 「연속」으로 읽히지 않게 한다.
            heading_diverge_cnt = 0;
            heading_last_stamp = rclcpp::Time(0, 0, RCL_ROS_TIME);
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
            RCLCPP_WARN(node_->get_logger(), "YawControl global timeout (%.1f s), dist=%.3f m", max_timeout_sec_.load(),
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
        // ── 측위 워치독에 현재 지령속도를 알린다 ──
        // `checkLocalizationHealth` 는 `max_cmd_speed_ <= 0.01` 이면 **즉시 true 로 조기
        // 반환**한다(정지 중에는 측위가 낡아도 위험하지 않다는 설계). yaw 계열은 이 값을
        // **한 번도 설정하지 않아** 0 으로 고정돼 있었고, 그래서 status −4(측위 타임아웃)·
        // −5(점프)·−6(조회 실패)이 전부 발화할 수 없었다 — 위 380행의 검사가 항상 통과했다.
        // `translate_*`·`crab_linear`·`mpc*` 는 모두 이 배선을 갖고 있고 여기만 빠졌다.
        {
            loc_monitor_->setMaxCmdSpeed(vx_profile);
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

        // ── 조대 헤딩 발산 탐지 (제어에는 관여하지 않는다) ──
        // IMU 가 회전을 놓쳐도 알 방법이 없어 25° 틀어진 채 status 0 을 반환한 사례가 있다.
        // 측위 heading 은 정밀도가 낮아 보정에는 못 쓰지만 **고장 판별에는 충분**하다 —
        // 정상 괴리 0.09~0.25° 대 고장 25° 로 100배 차이라 임계를 그 사이 아무 곳에 둬도 된다.
        if (enable_heading_divergence_guard_ && map_yaw_fresh)
        {
            double diverge_deg =
                std::fabs(normalizeAngleDeg(current_yaw_deg - map_yaw_rad * 180.0 / M_PI));
            // ⚠ **제어 cycle 이 아니라 서로 다른 pose 샘플을 센다.** 제어 루프는 50 Hz 인데
            //   실차 `/robot_pose` 는 10 Hz 다(`seer_pose_publisher` 는 10 Hz 초과를 막는다).
            //   cycle 을 세면 같은 pose 가 5 회 재사용되어 「10 cycle 연속」이 실제로는
            //   **서로 다른 샘플 2개**에 불과하다 — pose 가 5 Hz 로 떨어지면 **튄 샘플 하나로**
            //   abort 한다. 순간 튐 오탐을 막겠다는 디바운스의 취지가 성립하지 않았다.
            const bool new_pose_sample = (map_stamp != heading_last_stamp);
            if (diverge_deg > heading_divergence_deg_)
            {
                if (new_pose_sample)
                {
                    heading_last_stamp = map_stamp;
                    ++heading_diverge_cnt;
                }
                if (heading_diverge_cnt >= heading_divergence_count_)
                {
                    RCLCPP_ERROR(node_->get_logger(),
                                 "YawControl heading divergence: |IMU기준 %.2f° − 맵 %.2f°| = %.2f° > %.2f° "
                                 "가 pose 샘플 %d개 연속 — IMU 가 회전을 놓쳤을 수 있다. abort(-7)",
                                 current_yaw_deg, map_yaw_rad * 180.0 / M_PI, diverge_deg,
                                 heading_divergence_deg_.load(), heading_divergence_count_.load());
                    finish_abort(-7, current_distance, current_yaw_deg,
                                 normalizeAngleDeg(goal->target_yaw_deg - current_yaw_deg), start_time);
                    return;
                }
            }
            else
            {
                heading_diverge_cnt = 0;
                heading_last_stamp = rclcpp::Time(0, 0, RCL_ROS_TIME);
            }
        }

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

        // ── 조향 미도달 지속 감시 ──
        // gate_blocked 는 조향이 설 때까지 구동을 막는 **정상** 안전 동작이다. 다만 조향축이
        // 비응답이면 영원히 풀리지 않는데, 종전에는 그 사실을 아무도 보고하지 않아 전역
        // 타임아웃(60 s)까지 조용히 대기했다(실측: 지령 −20.2°, 실제 0.00°, 거리 0.001 m).
        // 임계 `gate_blocked_timeout_sec`(5.0 s)는 **실측으로 정한 값**이다 —
        // 정상 조향 이동 시간(실기 0→31° 에 약 3 s)보다 길게 잡았다
        // (`issues_and_fixes.md` 2026-08-10 §조향 미도달 감시).
        // ⚠ 2026-08-10 되돌림: 한때 「진전이 없는 시간」을 재는 방식으로 바꿨었다. 근거는
        //   `max_steer_deg ≈ 82°` 부터 정상 기동이 5 s 를 넘긴다는 **계산**이었는데,
        //   그 계산의 「축 10.3 °/s」가 **틀렸다** — `0→31° 약 3 s` 를 축 이동으로 나눴는데,
        //   지령 자체가 20.05 °/s 로 램프되어 31° 지령에만 1.55 s 가 든다(램프+응답의 합을
        //   축 이동으로 착각). 큰 각 실측은 **호밍에 이미 있다**: 총 35.0 s 중 −리밋 탐색이
        //   31.7 s 이므로 137° 복귀는 ≤3.3 s ⇒ 축은 **≥41.5 °/s**(4배).
        //   축이 램프보다 빠르면 오차가 자라지 않아 `gate_blocked` 가 지속될 이유가 없다 —
        //   전제가 뒤집힌다. 실제 고장은 지령 −20.2° 대 실제 0.00°(오차 20.2° **고정**)였고
        //   이 고정 시한이 그것을 잡는다. 오탐을 **관측하면** 그때 근거를 갖고 바꾼다.
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
                             "YawControl 조향 미도달 %.1f s 지속 — 발행 F=%.2f°/R=%.2f° 대 실제 "
                             "F=%.2f°/R=%.2f°. 조향축이 지령을 실행하지 못한다. abort(-8)",
                             gate_blocked_timeout_sec_.load(), expected_steer_f * 180.0 / M_PI,
                             expected_steer_r * 180.0 / M_PI,
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

        // Wheel velocity from IK
        double vel_f = ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction * speed_scale;
        double vel_r = ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction * speed_scale;

        // Walk velocity profile (accel/decel limiter)
        {
            double acc_step = walk_accel_limit_ * dt;
            double dec_step = walk_decel_limit_ * dt;
            // 지역 람다를 폐기하고 공용 `rampToward` 를 쓴다.
            // ⚠ 전진판의 지역 구현은 **부호 있는 비교**여서 후진 goal(`vx_max < 0`, 액션이
            //   정식 허용)에서 가·감속 한계가 뒤바뀌었다 — 설계값의 2배로 가속하고 절반으로
            //   제동해 **제동거리가 2배**가 됐다. 후진판에만 크기 비교와 부호교차 분기가
            //   있었다. 같은 로직의 사본이 여러 서버에 흩어져 있어 하나로 모았다.
            vel_f = trnav_2ws_core::rampToward(prev_cmd_vel_f, vel_f, acc_step, dec_step);
            vel_r = trnav_2ws_core::rampToward(prev_cmd_vel_r, vel_r, acc_step, dec_step);
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

    // ── 최종 헤딩 오차 검사(status −9) ──
    // ⚠ **여기가 마지막 조용한 실패 경로였다.** 조향이 죽어 로봇이 직진만 하면 IMU 와 맵이
    //   **둘 다 「안 돌았다」로 일치**하므로 −7(헤딩 발산)이 뜨지 않고, 거리는 정상 누적되어
    //   `current_distance >= target_distance` 로 완주 판정이 난다. 그러면 헤딩이 25° 틀어진
    //   기동이 `status 0`(성공)으로 상위에 올라가고 다음 기동이 그 자세에서 출발한다.
    //   −7·−8 을 넣은 목적의 절반이 이 지점에서 샜다.
    //   임계는 **정확도 규격이 아니라 조용한 실패를 막는 가드**다 — 실기에서 검증된 기동을
    //   깨지 않도록 넉넉히 잡고(기본 10°), 규격 논의는 별도다.
    if (enable_final_yaw_check_ && std::fabs(final_err_deg) > final_yaw_tol_deg_)
    {
        RCLCPP_ERROR(node_->get_logger(),
                     "YawControl: 거리는 채웠으나 최종 헤딩 오차 %.2f° 가 허용 %.2f° 를 넘는다 — "
                     "조향이 지령을 따라가지 못했는가(can_relay·모터 점검). abort(-9)",
                     final_err_deg, final_yaw_tol_deg_.load());
        finish_abort(-9, current_distance, final_yaw_deg, final_err_deg, start_time);
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
