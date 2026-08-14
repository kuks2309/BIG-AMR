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
    require_motion_source_ = safeParam("line_follow_require_motion_source", true);

    // ── 값 범위 강제 ──
    // 파라미터는 런타임에 바뀔 수 있고 오타 하나가 제어를 못 쓰게 만든다. 특히 감속률이
    // 0 이하이면 감속 루프의 속도가 줄지 않아 **정지 자체가 끝나지 않고**, 그 사이 액션
    // 뮤텍스를 쥐고 있으므로 다른 지령도 전부 거부된다. 거부보다 하한 강제가 낫다 —
    // 주행 중 goal 을 잃는 것보다 보수적 값으로 계속 서는 편이 안전하다.
    auto floor_at = [this](double &v, double lo, const char *name) {
        if (!(v >= lo)) // NaN 도 이 분기로 들어온다
        {
            RCLCPP_WARN(node_->get_logger(), "LineFollow: %s=%.4f 는 허용 범위를 벗어나 %.4f 로 강제한다", name, v, lo);
            v = lo;
        }
    };
    floor_at(accel_, 0.01, "line_follow_accel");
    floor_at(coast_decel_, 0.01, "line_follow_coast_decel");
    floor_at(stop_decel_, 0.05, "line_follow_stop_decel");
    floor_at(steer_rate_limit_, 0.01, "line_follow_steer_rate_limit");
    floor_at(walk_accel_limit_, 0.01, "line_follow_walk_accel_limit");
    floor_at(walk_decel_limit_, 0.01, "line_follow_walk_decel_limit");
    floor_at(wait_line_timeout_sec_, 0.1, "line_follow_wait_line_timeout_sec");
    floor_at(input_stale_timeout_sec_, 0.05, "line_follow_input_stale_timeout_sec");
    floor_at(gate_blocked_timeout_sec_, 0.1, "line_follow_gate_blocked_timeout_sec");
    floor_at(max_timeout_sec_, 1.0, "line_follow_max_timeout_sec");
    floor_at(gains_.max_steer_rad, 1.0 * M_PI / 180.0, "line_follow_max_steer_deg");
    conf_threshold_ = std::min(1.0, std::max(0.0, conf_threshold_));
    resume_max_offset_ = std::min(1.0, std::max(0.0, resume_max_offset_));
    gains_.slow_gain = std::min(1.0, std::max(0.0, gains_.slow_gain));
    if (offset_filter_window_ < 1)
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow: offset_filter_window=%d 는 1 미만이라 1 로 강제한다",
                    offset_filter_window_);
        offset_filter_window_ = 1;
    }
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
    // 구독 캐시는 goal 경계를 넘어 남는다. 비우지 않으면 **직전 goal 이 남긴 오차·카메라**가
    // 이번 goal 의 첫 주기 판단에 쓰인다 — 방향을 바꾼 직후라면 이전 카메라 이름이 그대로
    // 읽혀 시작하자마자 카메라 불일치(-11)가 된다. 이번 goal 동안 도착한 데이터만 쓰게 하고,
    // 아직 아무것도 안 왔으면 WAIT_LINE 이 wait_line_timeout 으로 대기를 관리한다.
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
        // 둘 다 0 이면 **성공으로 끝날 조건이 없다** — cancel 하거나 전역 시한
        // (line_follow_max_timeout_sec)이 abort(-3) 로 끊을 때까지 달린다. 무인 주행에서
        // 그 상태는 사고이므로 goal 단계에서 막는다.
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

    reloadTuning();       // 주행 사이 `ros2 param set` 튜닝을 이번 goal 부터 반영
    resetLineSnapshot();  // 직전 goal 이 남긴 오차·카메라를 이번 판단에서 배제

    // ── mux active source 전환 ──
    // 전환에 실패하면 지령이 하류로 나가지 않는다. 라인 추종은 영상 폐루프라 바퀴가 멈춰
    // 있어도 오차는 계속 들어오므로, 경고만 하고 진행하면 **한 번도 안 움직이고 max_duration
    // 도달로 성공** 을 보고한다. 그래서 기본은 abort(-13) 다. mux 없이 도는 SIL·벤치에서는
    // line_follow_require_motion_source 를 false 로 내려 종전 동작(경고 후 진행)을 쓴다.
    {
        bool selected = false;
        std::string fail_reason = "/select_motion_source service not ready";
        if (select_source_client_ && select_source_client_->service_is_ready())
        {
            auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
            req->source_id = static_cast<uint8_t>(motion_source_id_);
            auto future = select_source_client_->async_send_request(req);
            if (future.wait_for(std::chrono::milliseconds(500)) == std::future_status::ready)
            {
                auto resp = future.get();
                selected = resp->success;
                if (!selected)
                    fail_reason = "SelectMotionSource rejected: " + resp->message;
            }
            else
            {
                fail_reason = "SelectMotionSource timeout 500ms";
            }
        }
        if (selected)
        {
            RCLCPP_INFO(node_->get_logger(), "LineFollow: mux active source → %d (line_follow)", motion_source_id_);
        }
        else if (require_motion_source_)
        {
            RCLCPP_ERROR(node_->get_logger(),
                         "LineFollow: mux 소스 전환 실패(id=%d) — %s. 지령이 바퀴에 도달하지 않으므로 "
                         "abort(-13). mux 없이 시험하려면 line_follow_require_motion_source:=false",
                         motion_source_id_, fail_reason.c_str());
            publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            auto res = std::make_shared<LineFollow::Result>();
            res->status = -13;
            this->reportResult(res->status);
            goal_handle->abort(res);
            return;
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(), "LineFollow: mux 소스 전환 실패(id=%d) — %s (require=false 로 진행)",
                        motion_source_id_, fail_reason.c_str());
        }
    }

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
    double v_current = 0.0;  // 속도 프로파일 상태 (게이트가 막으면 0 으로 되돌린다)
    double v_body_cmd = 0.0; // 실제로 발행한 몸체 속도 — 감속 정지의 기준
    double steer_cmd = 0.0;  // 이번 주기 조향 목표(rad, 율제한 전)
    double steer_hold = 0.0; // 실제로 발행한 조향(rad) — coast·정지가 유지하는 값

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
    //
    // 기준 속도는 **실제로 발행한 몸체 속도**(v_body_cmd)다. 프로파일 상태 v_current 를 쓰면
    // 안전 게이트가 구동을 0 으로 묶고 있는 동안에도 자란 값이 그대로 나가, 서 있던 기체를
    // 정지 루틴이 오히려 움직인다. 게이트가 막고 있으면 여기서도 0 에서 시작한다.
    //
    // 종료는 이중으로 보장한다 — 속도 하한 도달 또는 시간 상한. 감속률은 reloadTuning 이
    // 하한을 강제하지만, 그것과 무관하게 루프가 유한임을 이 자리에서도 확정한다.
    auto rampToStop = [&]() {
        rclcpp::Rate stop_rate(control_rate_hz_);
        const auto stop_start = node_->now();
        const double stop_budget_sec = 10.0;
        while (rclcpp::ok() && v_body_cmd > 1e-3)
        {
            if ((node_->now() - stop_start).seconds() > stop_budget_sec)
            {
                RCLCPP_ERROR(node_->get_logger(), "LineFollow: 감속 정지가 %.0fs 안에 끝나지 않아 즉시 0 을 낸다",
                             stop_budget_sec);
                break;
            }
            v_body_cmd = line_follow::rampSpeed(v_body_cmd, 0.0, stop_decel_, dt);
            DualBicycleCommand cmd{goal->reverse ? -v_body_cmd : v_body_cmd, steer_hold, -steer_hold};
            IKResult ik_result = bicycle_model_->toIKResult(cmd, *ik_);
            publishWheelCmd(ik_result.wheels[0].wheel_speed * ik_result.wheels[0].direction,
                            ik_result.wheels[0].steer_rad,
                            ik_result.wheels[1].wheel_speed * ik_result.wheels[1].direction,
                            ik_result.wheels[1].steer_rad);
            stop_rate.sleep();
        }
        v_current = 0.0;
        v_body_cmd = 0.0;
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

    // ── 라인 대기 시한의 기준 시각 ──
    // execute 진입 시각(start_time)을 쓰면 mux 전환과 Phase 0 조향 정렬이 먼저 먹어치운다.
    // 조향 이동은 실측 수 초가 걸리므로, 기본 3 s 대기는 라인이 보이기도 전에 소진된다.
    // 라인 대기는 **주 루프에 들어온 시점부터** 센다.
    const auto wait_line_start = node_->now();

    // ── 측정 갱신 추적 ──
    // 인식은 15~26 Hz 인데 제어는 50 Hz 다. 같은 측정을 매 주기 필터에 다시 넣으면 미분항이
    // 연속 감쇠가 아니라 프레임 도착 시점의 펄스가 된다. 그래서 **새 측정이 왔을 때만**
    // 필터·미분을 갱신하고, 분모도 고정 dt 가 아니라 실제 측정 간격을 쓴다.
    rclcpp::Time last_meas_stamp(0, 0, node_->get_clock()->get_clock_type());
    bool have_meas = false;
    double offset_f = 0.0;
    double offset_rate = 0.0;

    // 주 루프를 **성공 조건으로** 빠져나왔는지. rclcpp 종료(Ctrl-C·노드 shutdown)로 루프가
    // 끝난 경우까지 성공으로 보고하면, 중단된 주행이 완주로 기록된다.
    bool reached_goal = false;

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
        //
        // 수신 플래그를 지우는 것만으로는 **직전 goal 이 남긴 프레임**을 못 막는다. 리셋 직후
        // 도착한 옛 프레임은 새 recv_time 을 달고 통과하기 때문이다(방향을 바꾼 직후라면 그
        // 한 장이 카메라 불일치 -11 을 만든다). 그래서 **측정 시각(header.stamp)이 이번 goal
        // 시작 이후인지**를 함께 본다. stamp 가 비어 있는 발행자에게는 이 검사를 요구하지
        // 않는다(수신 시각만으로 판정).
        auto snap = getLineSnapshot();
        rclcpp::Time meas_stamp(snap.msg.header.stamp, node_->get_clock()->get_clock_type());
        const bool stamp_usable = snap.received && meas_stamp.nanoseconds() > 0;
        const bool from_previous_goal = stamp_usable && meas_stamp < start_time;
        const bool input_stale = !snap.received || from_previous_goal ||
                                 (node_->now() - snap.recv_time).seconds() > input_stale_timeout_sec_;

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
            if ((node_->now() - wait_line_start).seconds() > wait_line_timeout_sec_)
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
                    have_meas = false;
                }

                // 새 측정이 왔을 때만 필터·미분을 갱신한다. stamp 가 없는 발행자는 매 주기
                // 갱신으로 되돌아가되(종전 동작), 그 경우에도 분모는 실제 경과 시간을 쓴다.
                const bool new_measurement = !have_meas || !stamp_usable || meas_stamp > last_meas_stamp;
                if (new_measurement)
                {
                    const double meas_dt =
                        (have_meas && stamp_usable) ? (meas_stamp - last_meas_stamp).seconds() : dt;
                    const double safe_dt = std::max(dt, std::min(1.0, meas_dt)); // 0 나눗셈·과대 미분 방어
                    const double next_offset_f = offset_filter.update(snap.msg.offset);
                    offset_rate = have_prev_offset ? (next_offset_f - prev_offset_f) / safe_dt : 0.0;
                    offset_f = next_offset_f;
                    prev_offset_f = next_offset_f;
                    have_prev_offset = true;
                    last_meas_stamp = meas_stamp;
                    have_meas = true;

                    abs_offset_sum += std::abs(offset_f);
                    ++abs_offset_count;
                }

                const auto cmd = line_follow::computeCommand(offset_f, offset_rate, snap.msg.angle,
                                                            goal->max_linear_speed, goal->reverse, gains_);
                steer_cmd = cmd.steer_rad;
                v_target = cmd.v_target;
                feedback->phase = 1;
            }
            else // LOST_COAST — 조향 유지, 감속만(가속 금지)
            {
                // "유지"의 대상은 **실제로 발행한 조향**이다. 율제한 전 목표(steer_cmd)를 그대로
                // 두면 소실 직후에도 그 목표를 향해 계속 꺾인다 — 라인을 못 보는 구간에서
                // 곡률이 오히려 커진다. 마지막 발행값으로 고정해 자세를 얼린다.
                steer_cmd = steer_hold;
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
            // coast·정지가 유지할 자세 = 방금 실제로 낸 조향
            steer_hold = steer_f;

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

            // 게이트가 막는 동안 속도 프로파일 상태를 자라게 두면, 나중에 감속 정지가 그
            // 값을 기준으로 삼아 **서 있던 기체를 움직인다.** 막히면 프로파일도 0 으로 되돌린다.
            if (guard_out.gate_blocked)
            {
                v_current = 0.0;
            }
            v_body_cmd = v_current * speed_scale; // 실제로 낸 몸체 속도 — 감속 정지의 기준

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
            reached_goal = true;
            break;
        }
        if (goal->max_distance > 0.0 && traveled >= goal->max_distance)
        {
            RCLCPP_INFO(node_->get_logger(), "LineFollow: max_distance %.2f m 도달 — 감속 정지 후 성공",
                        goal->max_distance);
            rampToStop();
            reached_goal = true;
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

    // rclcpp 종료로 루프를 빠져나온 경우 — 완주하지 않았으므로 성공이 아니다.
    if (!reached_goal)
    {
        RCLCPP_WARN(node_->get_logger(), "LineFollow: 노드 종료로 주행이 중단됐다 — abort(-12)");
        finish(-12, false);
        return;
    }

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
