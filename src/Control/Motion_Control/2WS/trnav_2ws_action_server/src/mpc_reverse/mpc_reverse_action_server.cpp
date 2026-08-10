#include "trnav_2ws_action_server/mpc_reverse/mpc_reverse_action_server.hpp"
#include "trnav_2ws_core/velocity_ramp.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <thread>
#include <utility>
#include <vector>

#include "trnav_2ws_core/math_utils.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

namespace trnav_2ws_action_server::mpc_reverse
{

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using BicycleModel = trnav::motion::two_ws::TwoWsBicycleModel;
using trnav::motion::two_ws::DualBicycleCommand;
using trnav::motion::two_ws::IKResult;
using trnav_2ws_core::LocalizationMonitor;
using trnav_2ws_core::ProfilePhase;
using MpcController = trnav::motion::two_ws::TwoWsMpcController;
using trnav::motion::two_ws::MpcOutput;
using trnav::motion::two_ws::MpcPose;
using trnav_2ws_core::TransientGuard;
using trnav_2ws_core::TrapezoidalProfile;
using trnav::motion::two_ws::WheelPosition;

namespace
{
struct PathHelperResult
{
    double projection = 0.0;
    double lookahead_x = 0.0;
    double lookahead_y = 0.0;
    double remaining_x = 0.0;
    std::size_t closest_seg = 0;
};

PathHelperResult computePathHelper(
    const std::vector<MpcPose> &wp, double rx, double ry, double ryaw, double lookahead_distance)
{
    PathHelperResult r{};
    if (wp.size() < 2) return r;
    std::vector<double> seg_len;
    seg_len.reserve(wp.size() - 1);
    std::vector<double> seg_cum;
    seg_cum.reserve(wp.size());
    seg_cum.push_back(0.0);
    for (std::size_t i = 0; i + 1 < wp.size(); ++i) {
        double dx = wp[i+1].x - wp[i].x;
        double dy = wp[i+1].y - wp[i].y;
        double len = std::hypot(dx, dy);
        seg_len.push_back(len);
        seg_cum.push_back(seg_cum.back() + len);
    }
    std::size_t best_i = 0;
    double best_d2 = std::numeric_limits<double>::infinity();
    double best_proj = 0.0;
    for (std::size_t i = 0; i + 1 < wp.size(); ++i) {
        double ax = wp[i].x, ay = wp[i].y;
        double dx = wp[i+1].x - ax, dy = wp[i+1].y - ay;
        double sl = seg_len[i];
        if (sl < 1e-9) continue;
        double t = ((rx - ax) * dx + (ry - ay) * dy) / (sl * sl);
        t = std::clamp(t, 0.0, 1.0);
        double cx = ax + t * dx, cy = ay + t * dy;
        double d2 = (rx - cx) * (rx - cx) + (ry - cy) * (ry - cy);
        if (d2 < best_d2) { best_d2 = d2; best_i = i; best_proj = t * sl; }
    }
    r.closest_seg = best_i;
    r.projection = seg_cum[best_i] + best_proj;
    double remaining = lookahead_distance;
    std::size_t li = best_i;
    double lp = best_proj;
    r.lookahead_x = wp.back().x;
    r.lookahead_y = wp.back().y;
    while (li + 1 < wp.size()) {
        double sl = seg_len[li];
        double from_here = sl - lp;
        if (remaining <= from_here) {
            double t = (lp + remaining) / sl;
            double dx = wp[li+1].x - wp[li].x;
            double dy = wp[li+1].y - wp[li].y;
            r.lookahead_x = wp[li].x + t * dx;
            r.lookahead_y = wp[li].y + t * dy;
            break;
        }
        remaining -= from_here;
        ++li;
        lp = 0.0;
    }
    double last_dx = wp.back().x - rx;
    double last_dy = wp.back().y - ry;
    r.remaining_x = last_dx * std::cos(ryaw) + last_dy * std::sin(ryaw);
    return r;
}
}  // anonymous namespace

MpcReverseActionServer::MpcReverseActionServer(rclcpp::Node::SharedPtr node,
                                                               ActionMutex action_mutex)
    : trnav::motion::two_ws::TwoWsActionServerBase<MpcReverse>(node, std::move(action_mutex),
                                                                "amr_motion_mpc_reverse_abstract",
                                                                "/motion/wheel_cmd/mpc_reverse")
{
    // ⚠ 기본값은 이 기체(Foil_A082, 인라인 듀얼스티어 · y=0) 기준. QD 대각 기본값
    //    (±0.330, ±0.135)이 남아 있어 params 없이 띄우면 조용히 QD 기하로 풀렸다
    //    (2026-08-08 실증: spin 이 ±90° 대신 −67.75° 를 세워 187 mm 병진). 정본은 config/*_params.yaml.
    double w1_x = safeParam("w1_x", 0.6039);
    double w1_y = safeParam("w1_y", 0.0);
    double w2_x = safeParam("w2_x", -0.5961);
    double w2_y = safeParam("w2_y", 0.0);

    std::vector<WheelPosition> wheels = {{w1_x, w1_y}, {w2_x, w2_y}};
    bicycle_model_ = std::make_unique<BicycleModel>(wheels);
    wheelbase_ = std::fabs(w1_x - w2_x);

    lookahead_distance_ = safeParam("mpc_lookahead_distance", 0.6);
    double max_lateral_offset = safeParam("mpc_max_lateral_offset", 1.0);
    double heading_threshold_deg = safeParam("mpc_heading_threshold_deg", 45.0);
    int cte_filter_window = safeParam("mpc_cte_filter_window", 1);
    goal_reach_threshold_ = safeParam("mpc_goal_reach_threshold", 0.05);
    min_vx_ = safeParam("mpc_min_vx", 0.02);
    behind_start_speed_ = safeParam("mpc_behind_start_speed", 0.2);
    max_timeout_sec_ = safeParam("mpc_max_timeout_sec", 60.0);
    enable_localization_watchdog_ = safeParam("mpc_enable_localization_watchdog", true);
    steer_rate_static_ = safeParam("mpc_steer_rate_static", 0.140);
    steer_rate_dynamic_ = safeParam("mpc_steer_rate_dynamic", 0.350);
    steer_rate_vx_threshold_ = safeParam("mpc_steer_rate_vx_threshold", 0.05);
    walk_accel_limit_ = safeParam("mpc_walk_accel_limit", 0.5);
    walk_decel_limit_ = safeParam("mpc_walk_decel_limit", 1.0);
    max_delta_ = safeParam("mpc_max_delta_deg", 45.0) * M_PI / 180.0;
    steer_converge_err_low_deg_ = safeParam("mpc_steer_converge_err_low_deg", 3.0);
    steer_converge_err_high_deg_ = safeParam("mpc_steer_converge_err_high_deg", 30.0);
    steer_converge_min_scale_ = safeParam("mpc_steer_converge_min_scale", 0.3);

    MpcController::Params pp_params;
    pp_params.wheelbase = wheelbase_;
    pp_params.max_delta_rad = max_delta_;
    pp_params.max_lateral_offset = max_lateral_offset;
    pp_ctrl_ = std::make_unique<MpcController>(pp_params);
    (void)heading_threshold_deg;
    (void)cte_filter_window;

    TransientGuard::Params tg_params;
    tg_params.vy_rate_limit = safeParam("transient_vy_rate_limit", 0.3);
    tg_params.omega_rate_limit = safeParam("transient_omega_rate_limit", 0.5);
    tg_params.steer_gate_threshold = safeParam("transient_steer_gate_threshold_deg", 3.0);
    tg_params.steer_error_max = safeParam("transient_steer_error_max_deg", 10.0);
    tg_params.enable_proportional_decel = safeParam("transient_enable_proportional_decel", true);
    tg_params.runtime_gate_threshold = safeParam("transient_runtime_gate_threshold_deg", 15.0);
    guard_ = std::make_unique<TransientGuard>(tg_params);

    // ── LocalizationMonitor (TF-only, topic 폐기 2026-05-18) ──
    double loc_timeout = safeParam("mpc_localization_timeout_sec", 2.0);
    double jump_threshold = safeParam("mpc_position_jump_threshold", 0.3);

    LocalizationMonitor::Params lm_params;
    lm_params.localization_timeout_sec = loc_timeout;
    lm_params.position_jump_threshold = jump_threshold;
    lm_params.enable_watchdog = enable_localization_watchdog_;
    loc_monitor_ = std::make_unique<LocalizationMonitor>(node_, lm_params);

    path_viz_pub_ = node_->create_publisher<nav_msgs::msg::Path>(
        "mpc_reverse_path", rclcpp::QoS(10).transient_local());
    debug_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>(
        "mpc_reverse_debug", rclcpp::QoS(10));

    last_wheel_state_time_ = std::chrono::steady_clock::now();

    // mux active source — execute() 진입부에 select_motion_source service 호출 (정공법: action server 책임).
    motion_source_id_ = safeParam("motion_source_id", 9);
    select_source_client_ = node_->create_client<trnav_msgs::srv::SelectMotionSource>("/select_motion_source");

    RCLCPP_INFO(node_->get_logger(),
                "MpcReverseActionServer initialized (TF-only, loc_watchdog=%s, "
                "lookahead=%.2f m, wheelbase=%.3f m, max_delta=%.1f deg)",
                enable_localization_watchdog_ ? "ON" : "OFF",
                lookahead_distance_, wheelbase_, max_delta_ * 180.0 / M_PI);

    // ── Hot-reload param callback (forward 와 동일 정책, 같은 yaml 키 공유) ──
    params_cb_handle_ = node_->add_on_set_parameters_callback(
        [this](const std::vector<rclcpp::Parameter> &params) -> rcl_interfaces::msg::SetParametersResult {
            rcl_interfaces::msg::SetParametersResult result;
            result.successful = true;
            bool touched_la = false;
            bool touched_md = false;
            for (const auto &p : params)
            {
                const std::string &name = p.get_name();
                if (p.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE)
                {
                    continue;
                }
                const double v = p.as_double();
                if (name == "mpc_lookahead_distance")
                {
                    if (v < 0.1 || v > 5.0)
                    {
                        result.successful = false;
                        result.reason = "mpc_lookahead_distance out of range [0.1, 5]";
                        return result;
                    }
                    lookahead_distance_ = v;
                    touched_la = true;
                }
                else if (name == "mpc_max_delta_deg")
                {
                    if (v < 10.0 || v > 90.0)
                    {
                        result.successful = false;
                        result.reason = "mpc_max_delta_deg out of range [10, 90]";
                        return result;
                    }
                    max_delta_ = v * M_PI / 180.0;
                    touched_md = true;
                }
            }
            if ((touched_la || touched_md) && pp_ctrl_)
            {
                if (touched_la)
                {
                    // MpcController 미구현 — cpp lookahead_distance_ 만 갱신
                }
                if (touched_md)
                {
                    pp_ctrl_->setMaxDelta(max_delta_);
                }
                RCLCPP_INFO(node_->get_logger(),
                            "Mpc(reverse) gains hot-reloaded: lookahead=%.3f m, max_delta=%.1f deg",
                            lookahead_distance_, max_delta_ * 180.0 / M_PI);
            }
            return result;
        });
}

void MpcReverseActionServer::wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg)
{
    trnav::motion::two_ws::TwoWsActionServerBase<MpcReverse>::wheelStateCallback(msg);
    wheel_state_received_.store(true);
    {
        std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
        last_wheel_state_time_ = std::chrono::steady_clock::now();
    }
}

bool MpcReverseActionServer::validateGoal(std::shared_ptr<const MpcReverse::Goal> goal)
{
    if (goal->path.poses.size() < 2)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: path.poses.size()=%zu (<2)",
                    goal->path.poses.size());
        return false;
    }
    if (goal->path.header.frame_id != "map")
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: path.frame_id='%s' (must be 'map')",
                    goal->path.header.frame_id.c_str());
        return false;
    }
    if (goal->max_linear_speed <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: max_linear_speed <= 0");
        return false;
    }
    if (goal->acceleration <= 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: acceleration <= 0");
        return false;
    }
    if (goal->entry_speed < 0.0)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: entry_speed < 0");
        return false;
    }
    if (!goal->hold_steer && (goal->exit_steer_angle < -90.0 || goal->exit_steer_angle > 90.0))
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: exit_steer_angle out of [-90, +90]");
        return false;
    }
    if (goal->control_mode != 0 && goal->control_mode != 1)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: control_mode=%u 미지원 (BICYCLE=1 만 지원)",
                    goal->control_mode);
        return false;
    }

    double total_len = 0.0;
    for (std::size_t i = 0; i + 1 < goal->path.poses.size(); ++i)
    {
        double dx = goal->path.poses[i + 1].pose.position.x - goal->path.poses[i].pose.position.x;
        double dy = goal->path.poses[i + 1].pose.position.y - goal->path.poses[i].pose.position.y;
        total_len += std::hypot(dx, dy);
    }
    if (total_len < 1e-6)
    {
        RCLCPP_WARN(node_->get_logger(), "MpcReverse rejected: zero-length path");
        return false;
    }

    RCLCPP_INFO(node_->get_logger(),
                "MpcReverse goal accepted: poses=%zu, total_len=%.3f m, v_max=%.2f m/s (magnitude)",
                goal->path.poses.size(), total_len, goal->max_linear_speed);
    return true;
}

// ════════════════════════════════════════════════════════
//  execute: Phase 0 → 1-3 → 4
//  translate_reverse 패턴:
//    effective_yaw = robot_yaw + π  (lookupMapToBase 직후 적용)
//    wheel 출력 × kReverseDir (-1)
//    termination: remaining_x 제거 (effective_yaw 시 부호 반전) → DONE / projection 만 사용
// ════════════════════════════════════════════════════════
void MpcReverseActionServer::execute(std::shared_ptr<GoalHandle> goal_handle)
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
                            "MpcReverse: SelectMotionSource(id=%d) failed: %s",
                            motion_source_id_, resp->message.c_str());
            else
                RCLCPP_INFO(node_->get_logger(),
                            "MpcReverse: mux active source → %d (mpc_reverse)",
                            motion_source_id_);
        }
        else
        {
            RCLCPP_WARN(node_->get_logger(),
                        "MpcReverse: SelectMotionSource(id=%d) timeout 500ms",
                        motion_source_id_);
        }
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(),
                    "MpcReverse: /select_motion_source service not ready — mux 전환 skip");
    }

    const auto goal = goal_handle->get_goal();
    loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);
    auto feedback = std::make_shared<MpcReverse::Feedback>();
    auto result = std::make_shared<MpcReverse::Result>();

    rclcpp::Rate rate(control_rate_hz_);
    const double dt = 1.0 / control_rate_hz_;

    // reverse 출력 부호 반전 상수
    constexpr double kReverseDir = -1.0;

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
            goal_handle->canceled(result);
        else
            goal_handle->abort(result);
    };

    auto start_time = node_->now();

    // ── path → waypoints (MpcPose: x, y, yaw) 변환 — Phase A 정공법 (path orientation 직접 사용) ──
    std::vector<MpcPose> waypoints;
    waypoints.reserve(goal->path.poses.size() + 3);
    for (const auto &ps : goal->path.poses)
    {
        MpcPose mp;
        mp.x = ps.pose.position.x;
        mp.y = ps.pose.position.y;
        const auto &q = ps.pose.orientation;
        mp.yaw = std::atan2(2.0 * (q.w * q.z + q.x * q.y),
                            1.0 - 2.0 * (q.y * q.y + q.z * q.z));
        waypoints.push_back(mp);
    }

    // ── 종점 lookahead clamp 방지: 마지막 segment tangent 따라 path 를 lookahead+buffer 만큼 연장 ──
    // 원래 goal pose 와 원래 path 길이는 *연장 전* 보존 — 정지 판정/프로파일은 원래 값 기준.
    [[maybe_unused]] const double original_goal_x = waypoints.empty() ? 0.0 : waypoints.back().x;
    [[maybe_unused]] const double original_goal_y = waypoints.empty() ? 0.0 : waypoints.back().y;
    double original_target_distance = 0.0;
    for (size_t i = 1; i < waypoints.size(); ++i)
    {
        const double seg_dx = waypoints[i].x - waypoints[i - 1].x;
        const double seg_dy = waypoints[i].y - waypoints[i - 1].y;
        original_target_distance += std::hypot(seg_dx, seg_dy);
    }
    const double extension_distance = lookahead_distance_ + 0.2;  // lookahead + 0.2m buffer
    if (waypoints.size() >= 2 && extension_distance > 1e-6)
    {
        const auto p_last = waypoints.back();
        const auto p_prev = waypoints[waypoints.size() - 2];
        const double tan_dx = p_last.x - p_prev.x;
        const double tan_dy = p_last.y - p_prev.y;
        const double seg_len = std::hypot(tan_dx, tan_dy);
        if (seg_len > 1e-6)
        {
            const double tx = tan_dx / seg_len;
            const double ty = tan_dy / seg_len;
            const double extend_yaw = std::atan2(tan_dy, tan_dx);
            for (int i = 1; i <= 3; ++i)
            {
                const double s = extension_distance * static_cast<double>(i) / 3.0;
                MpcPose ep;
                ep.x = p_last.x + tx * s;
                ep.y = p_last.y + ty * s;
                ep.yaw = extend_yaw;
                waypoints.push_back(ep);
            }
        }
    }

    if (goal->entry_speed <= 0.0)
    {
        pp_ctrl_->reset();
        guard_->reset();
    }

    if (!pp_ctrl_->setPath(waypoints))
    {
        RCLCPP_ERROR(node_->get_logger(), "MpcReverse setPath failed");
        finish_abort(-2, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // target_distance 는 *원래 path 길이* — 연장 path 는 lookahead 추종용, 정지/프로파일은 원래 goal 기준.
    double target_distance = original_target_distance;
    RCLCPP_INFO(node_->get_logger(),
                "MpcReverse execute: waypoints=%zu (incl. %.2fm extension), "
                "target_dist=%.3f m (original), lookahead=%.2f m",
                waypoints.size(), extension_distance, target_distance, lookahead_distance_);

    {
        nav_msgs::msg::Path path_msg = goal->path;
        path_msg.header.stamp = node_->now();
        path_viz_pub_->publish(path_msg);
    }

    // ── IMU receive check (위치는 TF lookupMapToBase 가 처리) ──
    if (!imu_received_.load())
    {
        RCLCPP_ERROR(node_->get_logger(), "IMU data not received, aborting mpc_reverse");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }

    double robot_x = 0.0, robot_y = 0.0, robot_yaw = 0.0;
    if (!loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
    {
        RCLCPP_ERROR(node_->get_logger(), "/robot_pose 미수신 또는 낡음(신선도 초과) — TF 문제가 아니다. 측위 발행자와 pose_topic 결속을 확인하라. aborting mpc_reverse");
        finish_abort(-3, 0.0, 0.0, 0.0, start_time);
        return;
    }
    // reverse: effective_yaw = real_yaw + π
    robot_yaw = trnav_2ws_core::normalizeAngle(robot_yaw + M_PI);

    int validate_result = pp_ctrl_->validateInitialPose(robot_x, robot_y, robot_yaw);
    if (validate_result != 0)
    {
        RCLCPP_WARN(node_->get_logger(),
                    "MpcReverse initial pose validation failed (code=%d): "
                    "robot=(%.2f,%.2f, effective_yaw=%.1f deg)",
                    validate_result, robot_x, robot_y, robot_yaw * 180.0 / M_PI);
        finish_abort(-2, 0.0, 0.0, 0.0, start_time);
        return;
    }

    // ── Phase 0: Steer Align ──
    if (goal->entry_speed <= 0.0)
    {
        auto pp_first = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); auto helper_first = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
        // 후진 키네마틱: effective front = w2 (robot rear). Mpc 의 delta_f 는
        // effective frame 의 front steer → 실제 wheel 은 w2 (rear steering) 로 보내야 정상.
        const double align_steer_f = 0.0;
        const double align_steer_r = pp_first.delta_f;

        feedback->phase = 0;
        auto phase0_start = node_->now();

        RCLCPP_INFO(node_->get_logger(),
                    "MpcReverse Phase 0: steer alignment (target F=%.1f R=%.1f deg)",
                    align_steer_f * 180.0 / M_PI, align_steer_r * 180.0 / M_PI);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "MpcReverse cancelled during Phase 0");
                finish_abort(-1, 0.0, 0.0, 0.0, start_time);
                return;
            }

            publishWheelCmd(0.0, align_steer_f, 0.0, align_steer_r);

            feedback->current_distance = 0.0;
            feedback->current_lateral_error = 0.0;
            feedback->current_heading_error = 0.0;
            feedback->current_vx = 0.0;
            feedback->current_vy = 0.0;
            feedback->current_omega = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            feedback->lookahead_x = helper_first.lookahead_x;
            feedback->lookahead_y = helper_first.lookahead_y;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - align_steer_f) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - align_steer_r) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;

            if ((node_->now() - phase0_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "MpcReverse Phase 0 steer timeout");
                finish_abort(-3, 0.0, 0.0, 0.0, start_time);
                return;
            }
            rate.sleep();
        }
        RCLCPP_INFO(node_->get_logger(), "MpcReverse Phase 0 complete");
    }

    double prev_cmd_steer_f = last_angle_front_.load();
    double prev_cmd_steer_r = last_angle_rear_.load();
    // reverse: entry_speed 는 음수로 초기화
    double prev_cmd_vel_f = (goal->entry_speed > 0.0) ? -goal->entry_speed : 0.0;
    double prev_cmd_vel_r = (goal->entry_speed > 0.0) ? -goal->entry_speed : 0.0;

    // ── Phase 1-3 ──
    double exit_speed = goal->exit_speed;
    TrapezoidalProfile profile(target_distance, goal->max_linear_speed, goal->acceleration, exit_speed,
                               goal->entry_speed);

    bool reached = false;
    int tf_fail_count = 0;
    const int tf_fail_max = 50;

    MpcOutput pp_out{};
    PathHelperResult helper{};

    while (rclcpp::ok() && !reached)
    {
        if (loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw))
        {
            robot_yaw = trnav_2ws_core::normalizeAngle(robot_yaw + M_PI); // effective_yaw
            tf_fail_count = 0;
        }
        else
        {
            tf_fail_count++;
            if (tf_fail_count >= tf_fail_max)
            {
                pp_out = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
                RCLCPP_ERROR(node_->get_logger(), "TF2 lookup failed %d consecutive times at dist=%.3f m",
                             tf_fail_count, helper.projection);
                finish_abort(-6, helper.projection, pp_out.e_d, pp_out.e_theta * 180.0 / M_PI, start_time);
                return;
            }
        }

        if (goal_handle->is_canceling())
        {
            pp_out = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
            RCLCPP_INFO(node_->get_logger(), "MpcReverse cancelled at dist=%.3f m", helper.projection);
            finish_abort(-1, helper.projection, pp_out.e_d, pp_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if ((node_->now() - start_time).seconds() > max_timeout_sec_)
        {
            pp_out = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
            RCLCPP_WARN(node_->get_logger(), "MpcReverse global timeout (%.1f s), dist=%.3f m",
                        max_timeout_sec_, helper.projection);
            finish_abort(-3, helper.projection, pp_out.e_d, pp_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        if (enable_localization_watchdog_ && !loc_monitor_->checkLocalizationHealth())
        {
            pp_out = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
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
            RCLCPP_ERROR(node_->get_logger(), "Localization health fail (%s, code=%d) at dist=%.3f m", reason_str, code,
                         helper.projection);
            finish_abort(code, helper.projection, pp_out.e_d, pp_out.e_theta * 180.0 / M_PI, start_time);
            return;
        }

        pp_out = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);
        double projection = helper.projection;

        double clamped_projection = std::max(0.0, projection);
        auto prof_out = profile.getSpeed(clamped_projection);
        double vx_profile = prof_out.speed;
        max_cmd_speed_.store(vx_profile);
        loc_monitor_->setMaxCmdSpeed(vx_profile);

        if (projection < 0.0)
            vx_profile = behind_start_speed_;
        else if (prof_out.phase == ProfilePhase::ACCEL && vx_profile < behind_start_speed_)
            vx_profile = behind_start_speed_;

        double remaining = target_distance - projection;
        bool near_goal = (remaining < goal_reach_threshold_);
        if (prof_out.phase != ProfilePhase::DONE && !near_goal && vx_profile < min_vx_)
            vx_profile = min_vx_;

        // 종료 조건: remaining_x 제거 (effective_yaw 적용 시 부호 반전으로 오작동)
        if (prof_out.phase == ProfilePhase::DONE || projection >= target_distance)
        {
            reached = true;
            if (goal->exit_speed > 0.0)
            {
                RCLCPP_INFO(node_->get_logger(),
                            "MpcReverse reached with velocity continuity (exit_speed=%.3f)",
                            goal->exit_speed);
            }
            else
            {
                publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
            }
            break;
        }

        // BicycleModel: 후진 시 effective front = w2 → delta_f 를 delta_r 로 매핑
        IKResult ik_expected;
        double vy_for_guard, omega_for_guard;
        {
            DualBicycleCommand dual_cmd{vx_profile, 0.0, pp_out.delta_f};
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
            double active_rate = (std::fabs(vx_profile) > steer_rate_vx_threshold_) ? steer_rate_dynamic_
                                                                                      : steer_rate_static_;
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
                steer_converge_scale =
                    1.0 - (1.0 - steer_converge_min_scale_) *
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
        // reverse: cmd_vx 음수
        double cmd_vx = vx_profile * speed_scale * kReverseDir;
        double cmd_vy = guard_out.vy_limited * kReverseDir;
        double cmd_omega = guard_out.omega_limited * kReverseDir;

        // Actual-steer-based IK for wheel speed
        IKResult ik_for_speed = ik_expected;
        {
            bool feedback_fresh = true;
            {
                std::lock_guard<std::mutex> lock(wheel_state_time_mutex_);
                double ws_age =
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - last_wheel_state_time_)
                        .count();
                if (!wheel_state_received_.load() || ws_age > 0.2)
                    feedback_fresh = false;
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

        // Wheel output: forward-IK 결과 × speed_scale × kReverseDir (-1)
        double vel_f =
            ik_for_speed.wheels[0].wheel_speed * ik_for_speed.wheels[0].direction * speed_scale * kReverseDir;
        double vel_r =
            ik_for_speed.wheels[1].wheel_speed * ik_for_speed.wheels[1].direction * speed_scale * kReverseDir;

        // Walk velocity profile (magnitude-based — reverse 시 음수 tgt 처리)
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

        double fb_w1_rpm = ik_for_speed.wheels[0].drive_rpm * speed_scale * kReverseDir;
        double fb_w2_rpm = ik_for_speed.wheels[1].drive_rpm * speed_scale * kReverseDir;

        publishWheelCmd(vel_f, cmd_steer_f, vel_r, cmd_steer_r);

        static int dbg_cnt = 0;
        if (++dbg_cnt % 5 == 0)
        {
            RCLCPP_INFO(
                node_->get_logger(),
                "[MpcRev] seg=%d steer: F=%.1f/%.1f° R=%.1f/%.1f° err=%.1f° %s | "
                "vx=%.3f proj=%.3fm lat=%.3fm hdg=%.1f° L=(%.2f,%.2f)",
                helper.closest_seg, last_angle_front_.load() * 180.0 / M_PI, cmd_steer_f * 180.0 / M_PI,
                last_angle_rear_.load() * 180.0 / M_PI, cmd_steer_r * 180.0 / M_PI, max_steer_err,
                guard_out.gate_blocked ? "BLOCKED" : "OK", cmd_vx, helper.projection, pp_out.e_d,
                pp_out.e_theta * 180.0 / M_PI, helper.lookahead_x, helper.lookahead_y);
        }

        {
            std_msgs::msg::Float64MultiArray dbg_msg;
            dbg_msg.data = {pp_out.e_d,
                            pp_out.e_theta * 180.0 / M_PI,
                            helper.projection,
                            helper.remaining_x,
                            pp_out.delta_f * 180.0 / M_PI,
                            0.0 * 180.0 / M_PI,
                            cmd_vx,
                            last_angle_front_.load(),
                            last_angle_rear_.load(),
                            cmd_steer_f,
                            cmd_steer_r,
                            vel_f,
                            vel_r,
                            speed_scale,
                            steer_converge_scale,
                            helper.lookahead_x,
                            helper.lookahead_y,
                            static_cast<double>(helper.closest_seg)};
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
        feedback->current_distance = helper.projection;
        feedback->current_lateral_error = pp_out.e_d;
        feedback->current_heading_error = pp_out.e_theta * 180.0 / M_PI;
        feedback->current_vx = cmd_vx; // 음수
        feedback->current_vy = cmd_vy;
        feedback->current_omega = cmd_omega;
        feedback->w1_drive_rpm = fb_w1_rpm;
        feedback->w2_drive_rpm = fb_w2_rpm;
        feedback->lookahead_x = helper.lookahead_x;
        feedback->lookahead_y = helper.lookahead_y;
        goal_handle->publish_feedback(feedback);

        rate.sleep();
    }

    if (goal->exit_speed <= 0.0)
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
    max_cmd_speed_.store(goal->exit_speed > 0.0 ? goal->exit_speed : 0.0);
    loc_monitor_->setMaxCmdSpeed(max_cmd_speed_.load());

    loc_monitor_->lookupMapToBase(robot_x, robot_y, robot_yaw);
    robot_yaw = trnav_2ws_core::normalizeAngle(robot_yaw + M_PI); // effective_yaw
    auto final_pp = pp_ctrl_->update(robot_x, robot_y, robot_yaw, 0.0, dt); auto final_helper = computePathHelper(waypoints, robot_x, robot_y, robot_yaw, lookahead_distance_);

    RCLCPP_INFO(node_->get_logger(),
                "MpcReverse Phase 1-3 complete: dist=%.3f m, lat_err=%.4f m, head_err=%.2f deg",
                final_helper.projection, final_pp.e_d, final_pp.e_theta * 180.0 / M_PI);

    if (goal_handle->is_canceling())
    {
        RCLCPP_INFO(node_->get_logger(), "MpcReverse cancelled after Phase 1-3");
        finish_abort(-1, final_helper.projection, final_pp.e_d, final_pp.e_theta * 180.0 / M_PI, start_time);
        return;
    }

    // ── Phase 4: Steer Return ──
    if (!goal->hold_steer)
    {
        feedback->phase = 4;
        double exit_steer_rad = goal->exit_steer_angle * M_PI / 180.0;
        auto phase4_start = node_->now();

        RCLCPP_INFO(node_->get_logger(), "MpcReverse Phase 4: steer return to %.1f deg",
                    goal->exit_steer_angle);

        while (rclcpp::ok())
        {
            if (goal_handle->is_canceling())
            {
                RCLCPP_INFO(node_->get_logger(), "MpcReverse cancelled during Phase 4");
                finish_abort(-1, final_helper.projection, final_pp.e_d, final_pp.e_theta * 180.0 / M_PI,
                             start_time);
                return;
            }

            publishWheelCmd(0.0, exit_steer_rad, 0.0, exit_steer_rad);

            feedback->current_distance = final_helper.projection;
            feedback->current_lateral_error = final_pp.e_d;
            feedback->current_heading_error = final_pp.e_theta * 180.0 / M_PI;
            feedback->current_vx = 0.0;
            feedback->current_vy = 0.0;
            feedback->current_omega = 0.0;
            feedback->w1_drive_rpm = 0.0;
            feedback->w2_drive_rpm = 0.0;
            feedback->lookahead_x = final_helper.lookahead_x;
            feedback->lookahead_y = final_helper.lookahead_y;
            goal_handle->publish_feedback(feedback);

            bool front_ok = std::abs(last_angle_front_.load() - exit_steer_rad) < steer_tolerance_rad_;
            bool rear_ok = std::abs(last_angle_rear_.load() - exit_steer_rad) < steer_tolerance_rad_;
            if (front_ok && rear_ok)
                break;

            if ((node_->now() - phase4_start).seconds() > steer_timeout_sec_)
            {
                RCLCPP_WARN(node_->get_logger(), "MpcReverse Phase 4 steer timeout (non-critical)");
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
    result->actual_distance = final_helper.projection;
    result->final_lateral_error = final_pp.e_d;
    result->final_heading_error = final_pp.e_theta * 180.0 / M_PI;
    result->elapsed_time = (node_->now() - start_time).seconds();

    goal_handle->succeed(result);

    RCLCPP_INFO(node_->get_logger(),
                "MpcReverse complete: dist=%.3f/%.3f m, lat_err=%.4f m, head_err=%.2f deg, time=%.1f s",
                final_helper.projection, target_distance, final_pp.e_d, final_pp.e_theta * 180.0 / M_PI,
                result->elapsed_time);
}

} // namespace trnav_2ws_action_server::mpc_reverse
