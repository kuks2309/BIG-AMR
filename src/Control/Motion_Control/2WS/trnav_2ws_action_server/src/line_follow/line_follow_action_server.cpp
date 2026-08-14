#include "trnav_2ws_action_server/line_follow/line_follow_action_server.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>

#include "trnav_2ws_core/math_utils.hpp"
#include "trnav_2ws_core/recursive_moving_average.hpp"

namespace trnav_2ws_action_server::line_follow
{

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using BicycleModel = trnav::motion::two_ws::TwoWsBicycleModel;
using trnav::motion::two_ws::DualBicycleCommand;
using trnav::motion::two_ws::IKResult;
using trnav_2ws_core::LocalizationMonitor;
using trnav_2ws_core::RecursiveMovingAverage;
using trnav_2ws_core::TransientGuard;
using trnav::motion::two_ws::WheelPosition;

LineFollowActionServer::LineFollowActionServer(rclcpp::Node::SharedPtr node, ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<LineFollow>(node, std::move(action_mutex),
                                                              "amr_motion_line_follow_abstract",
                                                              "/motion/wheel_cmd/line_follow")
{
    // BicycleModel — 베이스와 같은 기하 파라미터를 쓴다(정본은 config/*_params.yaml).
    double w1_x = safeParam("w1_x", 0.6039);
    double w1_y = safeParam("w1_y", 0.0);
    double w2_x = safeParam("w2_x", -0.5961);
    double w2_y = safeParam("w2_y", 0.0);
    std::vector<WheelPosition> wheels = {{w1_x, w1_y}, {w2_x, w2_y}};
    bicycle_model_ = std::make_unique<BicycleModel>(wheels);

    max_timeout_sec_ = safeParam("line_follow_max_timeout_sec", 120.0);
    enable_localization_watchdog_ = safeParam("line_follow_enable_localization_watchdog", true);
    forward_camera_ = safeParam<std::string>("line_follow_forward_camera", std::string("cam_f"));
    reverse_camera_ = safeParam<std::string>("line_follow_reverse_camera", std::string("cam_r"));

    reloadTuning();

    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    guard_ = std::make_unique<TransientGuard>(tg_params);

    LocalizationMonitor::Params lm_params;
    lm_params.pose_topic = safeParam<std::string>("line_follow_pose_topic", std::string("/robot_pose"));
    lm_params.localization_timeout_sec = safeParam("line_follow_localization_timeout_sec", 2.0);
    lm_params.position_jump_threshold = safeParam("line_follow_position_jump_threshold", 0.3);
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    // 인식 계층(line_seg_node)이 RELIABLE depth 10 으로 발행한다 — 같은 프로파일로 구독한다.
    line_sub_ = node_->create_subscription<ai_msgs::msg::LineError>(
        "/line/error", rclcpp::QoS(10).reliable(),
        [this](const ai_msgs::msg::LineError::SharedPtr msg) { lineErrorCallback(msg); });

    motion_source_id_ = safeParam("line_follow_motion_source_id", 13);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    RCLCPP_INFO(node_->get_logger(), "LineFollowActionServer initialized (source_id=%d)", motion_source_id_);
}

void LineFollowActionServer::reloadTuning()
{
    // goal 실행 직전마다 호출한다 — `ros2 param set` 으로 주행 사이 게인 조정이 가능하도록.
    gains_.kp_offset = safeParam("line_follow_kp_offset", 1.2);
    gains_.kd_offset = safeParam("line_follow_kd_offset", 0.15);
    gains_.kp_angle = safeParam("line_follow_kp_angle", 0.6);
    gains_.max_steer_rad = safeParam("line_follow_max_steer_deg", 25.0) * M_PI / 180.0;
    gains_.slow_gain = safeParam("line_follow_slow_gain", 0.7);
    accel_ = safeParam("line_follow_accel", 0.3);
    coast_decel_ = safeParam("line_follow_coast_decel", 0.15);
    stop_decel_ = safeParam("line_follow_stop_decel", 0.5);
    conf_threshold_ = safeParam("line_follow_conf_threshold", 0.5);
    resume_max_offset_ = safeParam("line_follow_resume_max_offset", 0.9);
    wait_line_timeout_sec_ = safeParam("line_follow_wait_line_timeout_sec", 3.0);
    input_stale_timeout_sec_ = safeParam("line_follow_input_stale_timeout_sec", 0.5);
    offset_filter_window_ = static_cast<int>(safeParam("line_follow_offset_filter_window", 5));
    steer_rate_limit_ = safeParam("line_follow_steer_rate_limit", 0.35);
    walk_accel_limit_ = safeParam("line_follow_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("line_follow_walk_decel_limit", 1.0);
    gate_blocked_timeout_sec_ = safeParam("line_follow_gate_blocked_timeout_sec", 5.0);
}

void LineFollowActionServer::lineErrorCallback(const ai_msgs::msg::LineError::SharedPtr msg)
{
    std::lock_guard<std::mutex> lock(line_mutex_);
    line_snapshot_.msg = *msg;
    line_snapshot_.recv_time = node_->now();
    line_snapshot_.received = true;
}

LineFollowActionServer::LineSnapshot LineFollowActionServer::getLineSnapshot() const
{
    std::lock_guard<std::mutex> lock(line_mutex_);
    return line_snapshot_;
}

void LineFollowActionServer::resetLineSnapshot()
{
    // 캐시는 goal 사이에도 남는다. 비우지 않으면 **직전 goal 이 남긴 오차·카메라**로 이번
    // goal 의 첫 주기를 판단한다 — 방향을 바꾼 직후 전 카메라 이름이 그대로 남아 시작하자마자
    // 카메라 불일치(-11)로 죽었다(스모크 실측: 소실 시나리오가 t=0.0s 에 -11 로 종료).
    // 이번 goal 동안 도착한 데이터만 쓰게 하고, 아직 안 왔으면 WAIT_LINE 이 대기를 관리한다.
    std::lock_guard<std::mutex> lock(line_mutex_);
    line_snapshot_.received = false;
}

std::string LineFollowActionServer::expectedCamera(bool reverse) const
{
    return reverse ? reverse_camera_ : forward_camera_;
}

bool LineFollowActionServer::validateGoal(std::shared_ptr<const LineFollow::Goal> goal)
{
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow rejected: max_linear_speed <= 0 (크기로 준다 — 방향은 reverse)");
        return false;
    }
    if (goal->line_lost_coast_sec < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow rejected: line_lost_coast_sec < 0");
        return false;
    }
    if (goal->max_duration_sec < 0.0 || goal->max_distance < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow rejected: max_duration_sec/max_distance < 0");
        return false;
    }
    if (goal->max_duration_sec <= 0.0 && goal->max_distance <= 0.0)
    {
        // 둘 다 0 이면 cancel 외에는 멈출 조건이 없다. 무인 주행에서 그 상태는 사고다.
        RCLCPP_WARN(node_->get_logger(),
                    "LineFollow rejected: max_duration_sec 와 max_distance 가 모두 0 — 종료 조건이 없다");
        return false;
    }
    RCLCPP_INFO(node_->get_logger(),
                "LineFollow goal accepted: v=%.3f m/s %s, coast=%.1fs, duration=%.1fs, distance=%.2fm",
                goal->max_linear_speed, goal->reverse ? "(reverse)" : "(forward)", goal->line_lost_coast_sec,
                goal->max_duration_sec, goal->max_distance);
    return true;
}

void LineFollowActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                RCLCPP_WARN(node_->get_logger(), "LineFollow: SelectMotionSource(id=%d) failed: %s", motion_source_id_,
                            resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(), "LineFollow: mux active source → %d (line_follow)", motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(), "LineFollow: SelectMotionSource(id=%d) timeout 500ms", motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow: /select_motion_source service not ready — mux 전환 skip");
    }

    reloadTuning();       // 주행 사이 `ros2 param set` 튜닝을 이번 goal 부터 반영
    resetLineSnapshot();  // 직전 goal 이 남긴 오차·카메라를 이번 판단에서 배제

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<LineFollow::Feedback>();
    auto result = std::make_shared<LineFollow::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;
    const auto start_time = node_->now();
    const std::string want_camera = expectedCamera(goal->reverse);

    double traveled = 0.0;
    double abs_offset_sum = 0.0;
    uint64_t abs_offset_count = 0;
    double v_current = 0.0;
    double steer_cmd = 0.0; // 마지막 조향 지령(rad) — coast 가 유지하는 값

    auto finish = [&](int8_t status, bool cancelled) {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
        result->status = status;
        this->reportResult(status);
        result->traveled_distance = traveled;
        result->avg_abs_offset = (abs_offset_count > 0) ? abs_offset_sum / static_cast<double>(abs_offset_count) : 0.0;
        result->elapsed_time = (node_->now() - start_time).seconds();
        if (cancelled)
            goal_handle->canceled(result);
        else
            goal_handle->abort(result);
    };

    // 감속 정지 — 조향은 유지한 채 속도만 stop_decel 로 0 까지 내린다.
    auto rampToStop = [&]() {
        rclcpp::Rate stop_rate(control_rate_hz_);
        while (rclcpp::ok() && v_current > 1e-3)
        {
            v_current = line_follow::rampSpeed(v_current, 0.0, stop_decel_, dt);
            DualBicycleCommand cmd{goal->reverse ? -v_current : v_current, steer_cmd, -steer_cmd};
            IKResult ik_result = bicycle_model_->toIKResult(cmd, *ik_);
            publishWheelCmd(ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction,
                            ik_result.wheels[0].steer_rad,
                            ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction,
                            ik_result.wheels[1].steer_rad);
            stop_rate.sleep();
        }
        v_current = 0.0;
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
    };

    // ── 시작 자세 (거리 적산·측위 감시용) ──
    // max_distance 를 쓰면 측위가 **필수**다 — 없으면 종료 조건을 잴 수 없다.
    double rx = 0.0, ry = 0.0, ryaw = 0.0;
    bool have_pose = loc_monitor_->lookupMapToBase(rx, ry, ryaw);
    if (goal->max_distance > 0.0 && !have_pose)
    {
        RCLCPP_ERROR(node_->get_logger(), "LineFollow: max_distance 를 요구했는데 측위(map->base_link)가 없다. abort(-4)");
        finish(-4, false);
        return;
    }
    double prev_x = rx, prev_y = ry;

    guard_->reset();

    // ── Phase 0: 조향 정렬 (delta = 0) ──
    {
        feedback->phase = 0;
        auto phase0_start = node_->now();
        RCLCPP_INFO(node_->get_logger(), "LineFollow Phase 0: steer alignment to 0");

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "LineFollow cancelled during Phase 0");
                finish(-1, true);
                return;
            }

            publishWheelCmd(0.0, 0.0, 0.0, 0.0);

            feedback->offset = 0.0;
            feedback->angle = 0.0;
            feedback->confidence = 0.0;
            feedback->current_speed = 0.0;
            feedback->current_steer_deg = 0.0;
            feedback->traveled_distance = 0.0;
            feedback->camera = want_camera;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load()) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load()) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;

            if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "LineFollow Phase 0 steer timeout");
                finish(-3, false);
                return;
            }
            rate.sleep();
        }
    }

    // ── 제어 상태 ──
    line_follow::LostCoastFsm fsm(goal->line_lost_coast_sec, resume_max_offset_);
    RecursiveMovingAverage offset_filter(offset_filter_window_);
    double prev_offset_f = 0.0;
    bool have_prev_offset = false;
    double prev_cmd_steer_f = 0.0;
    double prev_cmd_steer_r = 0.0;
    double prev_cmd_vel_f = 0.0;
    double prev_cmd_vel_r = 0.0;
    bool gate_blocked_active = false;
    rclcpp::Time gate_blocked_since = node_->now();
    int tf_fail_count = 0;
    const int tf_fail_max = 50;
    bool camera_warned = false;

    // ── 주 루프 ──
    while (rclcpp::ok())
    {
        if (goal_handle->is_canceling())
        {
            RCLCPP_INFO(node_->get_logger(), "LineFollow cancelled at dist=%.3f m", traveled);
            rampToStop();
            finish(-1, true);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            RCLCPP_WARN(node_->get_logger(), "LineFollow global timeout (%.1f s)", max_timeout_sec_);
            rampToStop();
            finish(-3, false);
            return;
        }

        // ── 측위: 거리 적산 + health ──
        // 라인은 곡선이므로 시작방향 투영이 아니라 **경로장**(|Δp| 합)을 적산한다.
        if (loc_monitor_->lookupMapToBase(rx, ry, ryaw))
        {
            tf_fail_count = 0;
            if (have_pose)
                traveled += std::hypot(rx - prev_x, ry - prev_y);
            prev_x = rx;
            prev_y = ry;
            have_pose = true;
        }
        else if (goal->max_distance > 0.0)
        {
            if (++tf_fail_count >= tf_fail_max)
            {
                RCLCPP_ERROR(node_->get_logger(), "LineFollow: TF2 %d회 연속 실패 — abort(-6)", tf_fail_count);
                rampToStop();
                finish(-6, false);
                return;
            }
        }

        if (enable_localization_watchdog_ && goal->enable_localization_watchdog &&
            !loc_monitor_->checkLocalizationHealth())
        {
            auto reason = loc_monitor_->getLastFailReason();
            int8_t code = -4;
            const char *reason_str = "TIMEOUT";
            if (reason == LocalizationMonitor::HealthFailReason::JUMP)
            {
                code = -5;
                reason_str = "JUMP";
            }
            else if (reason == LocalizationMonitor::HealthFailReason::TF_LOOKUP_FAIL)
            {
                code = -6;
                reason_str = "TF_LOOKUP_FAIL";
            }
            RCLCPP_ERROR(node_->get_logger(), "LineFollow: localization health fail (%s, code=%d)", reason_str, code);
            rampToStop();
            finish(code, false);
            return;
        }

        // ── 라인 오차 스냅샷 ──
        auto snap = getLineSnapshot();
        const bool input_stale =
            !snap.received || (node_->now() - snap.recv_time).seconds() > input_stale_timeout_sec_;

        // 스트림 두절은 "눈 감김" — 소실(coast)과 달리 유예를 주지 않는다.
        // 단 WAIT_LINE(시작 대기) 중에는 인식 노드 기동 지연을 허용하고 wait_line_timeout 이 관리한다.
        if (input_stale && fsm.phase() != line_follow::Phase::WAIT_LINE)
        {
            RCLCPP_ERROR(node_->get_logger(), "LineFollow: /line/error 두절 (>%.1fs) — 즉시 정지·abort(-10)",
                         input_stale_timeout_sec_);
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            finish(-10, false);
            return;
        }

        // ── 진행 방향 ↔ 카메라 정합 ──
        // 뒤를 보며 앞으로 달리면 조향 부호가 반대라 라인에서 멀어진다. 조용히 달리느니 기동 실패가 낫다.
        if (!input_stale && !snap.msg.camera.empty() && snap.msg.camera != want_camera)
        {
            RCLCPP_ERROR(node_->get_logger(),
                         "LineFollow: 카메라 불일치 — 기대 '%s'(%s) 인데 '%s' 의 오차가 온다. "
                         "line_seg_node 의 direction 파라미터를 맞출 것. abort(-11)",
                         want_camera.c_str(), goal->reverse ? "reverse" : "forward", snap.msg.camera.c_str());
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            finish(-11, false);
            return;
        }
        if (!input_stale && snap.msg.camera.empty() && !camera_warned)
        {
            camera_warned = true;
            RCLCPP_WARN(node_->get_logger(),
                        "LineFollow: /line/error 의 camera 필드가 비어 있다 — 방향 정합을 검사할 수 없다");
        }

        // ── 소실 상태기계 ──
        const bool good = !input_stale && snap.msg.detected && snap.msg.confidence >= conf_threshold_;
        const line_follow::Phase phase = fsm.update(good, snap.msg.offset, node_->now().seconds());

        double v_target = 0.0;
        double steer_deg = 0.0;

        if (phase == line_follow::Phase::WAIT_LINE)
        {
            publishWheelCmd(0.0, 0.0, 0.0, 0.0);
            if ((node_->now() - start_time).seconds() > wait_line_timeout_sec_)
            {
                RCLCPP_ERROR(node_->get_logger(), "LineFollow: %.1fs 안에 라인을 못 찾았다 — abort(-9)",
                             wait_line_timeout_sec_);
                finish(-9, false);
                return;
            }
            feedback->phase = 0;
        }
        else if (phase == line_follow::Phase::STOPPING)
        {
            RCLCPP_WARN(node_->get_logger(), "LineFollow: 라인 소실 coast %.1fs 초과 — 감속 정지·abort(-9)",
                        goal->line_lost_coast_sec);
            rampToStop();
            finish(-9, false);
            return;
        }
        else
        {
            if (phase == line_follow::Phase::FOLLOWING)
            {
                if (fsm.resumed())
                {
                    // 재개: coast 공백이 만든 derivative kick 을 막는다
                    offset_filter.reset();
                    have_prev_offset = false;
                }
                const double offset_f = offset_filter.update(snap.msg.offset);
                const double offset_rate = have_prev_offset ? (offset_f - prev_offset_f) / dt : 0.0;
                prev_offset_f = offset_f;
                have_prev_offset = true;

                const auto cmd = line_follow::computeCommand(offset_f, offset_rate, snap.msg.angle,
                                                            goal->max_linear_speed, goal->reverse, gains_);
                steer_cmd = cmd.steer_rad;
                v_target = cmd.v_target;

                abs_offset_sum += std::abs(offset_f);
                ++abs_offset_count;
                feedback->phase = 1;
            }
            else // LOST_COAST — 조향 유지, 감속만(가속 금지)
            {
                v_target = 0.0;
                feedback->phase = 2;
            }

            const double decel = (phase == line_follow::Phase::LOST_COAST) ? coast_decel_ : accel_;
            v_current = line_follow::rampSpeed(v_current, v_target, decel, dt);
            steer_deg = steer_cmd * 180.0 / M_PI;

            // ── 자전거 모형 → IK ──
            const double vx_signed = goal->reverse ? -v_current : v_current;
            DualBicycleCommand dual_cmd{vx_signed, steer_cmd, -steer_cmd}; // counter-steer 고정
            IKResult ik_result = bicycle_model_->toIKResult(dual_cmd, *ik_);

            double steer_f = ik_result.wheels[0].steer_rad;
            double steer_r = ik_result.wheels[1].steer_rad;

            // 조향 변화율 제한
            {
                const double max_step = steer_rate_limit_ * dt;
                const double diff_f = steer_f - prev_cmd_steer_f;
                const double diff_r = steer_r - prev_cmd_steer_r;
                if (std::fabs(diff_f) > max_step)
                    steer_f = prev_cmd_steer_f + std::copysign(max_step, diff_f);
                if (std::fabs(diff_r) > max_step)
                    steer_r = prev_cmd_steer_r + std::copysign(max_step, diff_r);
                prev_cmd_steer_f = steer_f;
                prev_cmd_steer_r = steer_r;
            }

            // 조향 추종 오차 → TransientGuard
            const double steer_err_f = std::fabs(last_angle_front_.load() - steer_f) * 180.0 / M_PI;
            const double steer_err_r = std::fabs(last_angle_rear_.load() - steer_r) * 180.0 / M_PI;
            const double max_steer_err = std::max(steer_err_f, steer_err_r);

            const double wheelbase = bicycle_model_->wheelbase();
            double omega_est = 0.0;
            if (std::fabs(wheelbase) > 1e-6)
                omega_est = vx_signed * (std::tan(steer_cmd) - std::tan(-steer_cmd)) / wheelbase;

            TransientGuard::GuardInput guard_input;
            guard_input.vy_cmd = 0.0;
            guard_input.omega_cmd = omega_est;
            guard_input.steer_error_deg = max_steer_err;
            guard_input.is_phase0 = false;
            const auto guard_out = guard_->apply(guard_input);
            const double speed_scale = guard_out.gate_blocked ? 0.0 : guard_out.drive_scale;

            // ── 조향 미도달 지속 감시 ──
            // gate_blocked 자체는 정상 안전 동작이지만, 조향축이 비응답이면 영원히 풀리지 않는다.
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
                                 "LineFollow 조향 미도달 %.1f s 지속 — 지령 F=%.2f°/R=%.2f° 대 실제 "
                                 "F=%.2f°/R=%.2f°. abort(-8)",
                                 gate_blocked_timeout_sec_, steer_f * 180.0 / M_PI, steer_r * 180.0 / M_PI,
                                 last_angle_front_.load() * 180.0 / M_PI, last_angle_rear_.load() * 180.0 / M_PI);
                    rampToStop();
                    finish(-8, false);
                    return;
                }
            }
            else
            {
                gate_blocked_active = false;
            }

            double vel_f = ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction * speed_scale;
            double vel_r = ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction * speed_scale;

            // 구동 속도 변화율 제한 (yaw_control 과 같은 형태)
            {
                const double acc_step = walk_accel_limit_ * dt;
                const double dec_step = walk_decel_limit_ * dt;
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

            publishWheelCmd(vel_f, steer_f, vel_r, steer_r);
        }

        // ── 종료 조건 (성공) ──
        if (goal->max_duration_sec > 0.0 && (node_->now() - start_time).seconds() > goal->max_duration_sec)
        {
            RCLCPP_INFO(node_->get_logger(), "LineFollow: max_duration_sec 도달 — 감속 정지 후 성공");
            rampToStop();
            break;
        }
        if (goal->max_distance > 0.0 && traveled >= goal->max_distance)
        {
            RCLCPP_INFO(node_->get_logger(), "LineFollow: max_distance %.2f m 도달 — 감속 정지 후 성공",
                        goal->max_distance);
            rampToStop();
            break;
        }

        // ── Feedback ──
        feedback->offset = snap.msg.offset;
        feedback->angle = snap.msg.angle;
        feedback->confidence = snap.msg.confidence;
        feedback->current_speed = v_current;
        feedback->current_steer_deg = steer_deg;
        feedback->traveled_distance = traveled;
        feedback->camera = snap.msg.camera;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());

    // ── Phase 4: 조향 복귀 ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        const double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();
        RCLCPP_INFO(node_->get_logger(), "LineFollow Phase 4: steer return to %.1f deg", goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "LineFollow cancelled during Phase 4");
                finish(-1, true);
                return;
            }
            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);

            bool front_ok = std::abs(last_angle_front_.load() - exit_steer_rad) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - exit_steer_rad) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;
            if ((node_->now() - phase4_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "LineFollow Phase 4 steer timeout (non-critical)");
                break;
            }
            rate.sleep();
        }
    }

    // ── 성공 ──
    result->status = 0;
    this->reportResult(result->status);
    result->traveled_distance = traveled;
    result->avg_abs_offset = (abs_offset_count > 0) ? abs_offset_sum / static_cast<double>(abs_offset_count) : 0.0;
    result->elapsed_time = (node_->now() - start_time).seconds();
    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(), "LineFollow complete: dist=%.3f m, avg|offset|=%.3f, time=%.1f s",
                result->traveled_distance, result->avg_abs_offset, result->elapsed_time);
}

} // namespace trnav_2ws_action_server::line_follow
