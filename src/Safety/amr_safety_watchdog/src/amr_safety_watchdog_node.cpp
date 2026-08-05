/**
 * @file amr_safety_watchdog_node.cpp
 * @brief Central safety arbitration — publisher of /safe_to_move
 *
 * Role: Subscribe to N safety sources (config-driven), AND them, publish
 *       /safe_to_move (std_msgs/Bool) at 10Hz as a dead man's switch.
 *
 * This is the SINGLE publisher of /safe_to_move. Consumers (action servers,
 * motor drivers) subscribe to this topic with RELIABLE + TRANSIENT_LOCAL.
 *
 * NOT related to trnav_motion_supervisor. trnav_motion_supervisor is the
 * trnav_motion_mux source activator in src/Control-Abstract/trnav_motion_supervisor/.
 *
 * See:
 *   - src/Control-Abstract/docs/amr_safety_watchdog_architecture.md
 *   - src/Control-Abstract/docs/trnav_motion_mux_architecture.md
 */

#include "amr_safety_watchdog/amr_safety_watchdog_node.hpp"
#include <rclcpp/qos.hpp>

namespace amr_safety_watchdog
{

SafetyWatchdogNode::SafetyWatchdogNode() : Node("amr_safety_watchdog")
{
    // ── 파라미터 선언 ──
    this->declare_parameter<std::string>("output_topic", "/safe_to_move");
    this->declare_parameter<double>("publish_rate_hz", 10.0);
    this->declare_parameter<bool>("failsafe_on_boot", true);

    const auto output_topic = this->get_parameter("output_topic").as_string();
    const double rate_hz = this->get_parameter("publish_rate_hz").as_double();
    failsafe_on_boot_ = this->get_parameter("failsafe_on_boot").as_bool();

    // ── Publisher: RELIABLE + TRANSIENT_LOCAL, KeepLast(1) ──
    rclcpp::QoS qos(rclcpp::KeepLast(1));
    qos.reliable();
    qos.transient_local();
    pub_ = this->create_publisher<std_msgs::msg::Bool>(output_topic, qos);

    // ── Sources 로드 ──
    loadSources();

    // ── Timer ──
    const auto period_ms = std::chrono::milliseconds(static_cast<int64_t>(1000.0 / rate_hz));
    timer_ = this->create_wall_timer(period_ms, std::bind(&SafetyWatchdogNode::publishLoop, this));

    RCLCPP_INFO(this->get_logger(), "amr_safety_watchdog started: %zu source(s), rate=%.1f Hz, failsafe_on_boot=%s",
                sources_.size(), rate_hz, failsafe_on_boot_ ? "true" : "false");
}

void SafetyWatchdogNode::loadSources()
{
    // source_names 리스트로 탐색, 각 이름을 접두사로 per-name 파라미터 로드
    // (YAML list-of-dict는 ROS2 파라미터 시스템에서 직접 로드 불가)
    auto names = this->declare_parameter<std::vector<std::string>>("source_names", std::vector<std::string>{});

    for (const auto &name : names)
    {
        const std::string prefix = name + ".";

        auto topic = this->declare_parameter<std::string>(prefix + "topic", "");
        auto type = this->declare_parameter<std::string>(prefix + "type", "");
        auto enabled = this->declare_parameter<bool>(prefix + "enabled", false);
        auto invert = this->declare_parameter<bool>(prefix + "invert", false);
        auto timeout = this->declare_parameter<int>(prefix + "timeout_ms", 500);

        if (topic.empty() || type.empty())
        {
            RCLCPP_WARN(this->get_logger(), "Skipping incomplete source '%s' (topic or type missing)", name.c_str());
            continue;
        }

        auto s = std::make_unique<SafetySource>();
        s->name = name;
        s->topic = topic;
        s->type = type;
        s->enabled = enabled;
        s->invert = invert;
        s->timeout = std::chrono::milliseconds(timeout);
        // F1 수정: 초기값은 항상 false(unsafe). 최초 수신 전은 무조건 unsafe
        s->last_safe.store(false);
        s->last_stamp = rclcpp::Time(0, 0, this->get_clock()->get_clock_type());

        if (!enabled)
        {
            RCLCPP_INFO(this->get_logger(), "source '%s' disabled, skip subscription", name.c_str());
            sources_.push_back(std::move(s));
            continue;
        }

        if (type == "bool")
        {
            makeBoolSource(s);
        }
        else if (type == "safety_status")
        {
            makeSafetyStatusSource(s);
        }
        else
        {
            RCLCPP_ERROR(this->get_logger(), "source '%s' unknown type '%s', skip", name.c_str(), type.c_str());
            continue;
        }

        RCLCPP_INFO(this->get_logger(), "Registered source name=%s topic=%s type=%s enabled=%d timeout=%ldms invert=%s",
                    name.c_str(), topic.c_str(), type.c_str(), enabled, static_cast<long>(timeout),
                    invert ? "true" : "false");

        sources_.push_back(std::move(s));
    }

    RCLCPP_INFO(this->get_logger(), "Loaded %zu safety source(s).", sources_.size());
}

void SafetyWatchdogNode::makeBoolSource(std::unique_ptr<SafetySource> &s)
{
    // 원시 포인터로 캡처 (소유권은 sources_ 벡터가 가짐)
    SafetySource *raw = s.get();

    auto sub = this->create_subscription<std_msgs::msg::Bool>(s->topic, rclcpp::QoS(10),
                                                              [this, raw](const std_msgs::msg::Bool::SharedPtr msg) {
                                                                  // bool source: data==true 이면 E-stop 활성 → unsafe
                                                                  //              data==false 이면 정상 → safe
                                                                  // invert 플래그로 반전 가능
                                                                  bool safe = (msg->data == false);
                                                                  if (raw->invert)
                                                                  {
                                                                      safe = !safe;
                                                                  }
                                                                  raw->last_safe.store(safe);
                                                                  std::lock_guard<std::mutex> lk(raw->stamp_mutex);
                                                                  raw->last_stamp = this->now();
                                                              });

    s->sub = sub;
}

void SafetyWatchdogNode::makeSafetyStatusSource(std::unique_ptr<SafetySource> &s)
{
    SafetySource *raw = s.get();

    auto sub = this->create_subscription<trnav_msgs::msg::SafetyStatus>(
        s->topic, rclcpp::QoS(10), [this, raw](const trnav_msgs::msg::SafetyStatus::SharedPtr msg) {
            // field_data_safety_st: 0=SAFE, 1=WARNING, 2=DANGEROUS
            bool safe = (msg->field_data_safety_st == 0);
            if (raw->invert)
            {
                safe = !safe;
            }
            raw->last_safe.store(safe);
            std::lock_guard<std::mutex> lk(raw->stamp_mutex);
            raw->last_stamp = this->now();
        });

    s->sub = sub;
}

void SafetyWatchdogNode::publishLoop()
{
    const auto now = this->now();
    bool all_safe = true;

    for (const auto &s : sources_)
    {
        if (!s->enabled)
        {
            continue;
        }

        // timeout 확인
        bool timed_out = false;
        {
            std::lock_guard<std::mutex> lk(s->stamp_mutex);
            if (s->last_stamp.nanoseconds() == 0)
            {
                // 최초 수신 전 — failsafe_on_boot 무관, 항상 unsafe (표준 failsafe)
                timed_out = true;
            }
            else
            {
                const auto elapsed_ms =
                    std::chrono::milliseconds(static_cast<int64_t>((now - s->last_stamp).nanoseconds() / 1e6));
                timed_out = (elapsed_ms > s->timeout);
            }
        }

        if (timed_out)
        {
            RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "source '%s' timed out → unsafe",
                                 s->name.c_str());
            all_safe = false;
            continue;
        }

        if (!s->last_safe.load())
        {
            all_safe = false;
        }
    }

    std_msgs::msg::Bool out;
    out.data = all_safe;
    pub_->publish(out);
}

} // namespace amr_safety_watchdog

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<amr_safety_watchdog::SafetyWatchdogNode>());
    rclcpp::shutdown();
    return 0;
}
