#include "trnav_motion_mux/trnav_motion_mux_node.hpp"
#include <rclcpp/executors/multi_threaded_executor.hpp>
#include <stdexcept>

namespace trnav_motion_mux
{

namespace
{
// Reserved Source ID → name 매핑 SSOT mirror.
// SSOT: docs/abstraction/motion_source_id_contract.md (2026-05-16)
// 매핑 또는 짝 패턴 변경 시: SSOT 갱신 → 본 표 갱신 → trnav_motion_mux.yaml 동기.
// rule_id 는 stderr 에서 launch_test 가 match 하는 식별자 (예: "V-01" in stderr).
struct ReservedRule
{
    uint8_t id;
    const char *name;
    const char *rule_id;
};

static const std::vector<ReservedRule> kReservedRules = {
    {0, "joystick", "V-01"},
    {1, "translate_forward", "V-02"},
    {2, "translate_reverse", "V-04"},        // V-03 영구예약 폐지 후 재배정 (2026-04-27)
    {3, "spin", "V-12"},
    {4, "crab_linear", "V-13"},
    {5, "turn", "V-14"},
    {6, "yaw_control", "V-15"},
    {7, "yaw_control_reverse", "V-11"},      // V-11 의 의미 변경 (2026-05-16): 옛 7→pure_pursuit → 신 7→yaw_control_reverse
    {8, "mpc", "V-16"},                      // 2026-05-28: PurePursuit 폐기, kinematic bicycle MPC 교체
    {9, "mpc_reverse", "V-17"},
    {10, "stanley", "V-18"},                 // 예약 (미구현)
    {11, "stanley_reverse", "V-19"},         // 예약 (미구현)
};
} // namespace


MotionMuxNode::MotionMuxNode() : Node("trnav_motion_mux")
{
    // Declare and read output topic
    this->declare_parameter<std::string>("output_topic", "/motor/wheel_cmd");

    const std::string output_topic = this->get_parameter("output_topic").as_string();

    // Publisher: RELIABLE, KeepLast(10), VOLATILE
    rclcpp::QoS qos(rclcpp::KeepLast(10));
    qos.reliable();
    qos.durability_volatile();

    pub_ = this->create_publisher<trnav_msgs::msg::WheelSetArray>(output_topic, qos);

    // Service: select active motion source
    select_srv_ = this->create_service<trnav_msgs::srv::SelectMotionSource>(
        "/select_motion_source",
        [this](const std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Request> req,
               std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Response> res) { onSelectSource(req, res); });

    // Declare default_source_id before loading so it can be passed to validateSources
    auto default_id = this->declare_parameter<int>("default_source_id", 0);

    loadSources();
    validateSources(default_id);

    // Apply default source id after sources are loaded and validated
    active_id_.store(static_cast<uint8_t>(default_id));

    RCLCPP_INFO(this->get_logger(), "MotionMuxNode started. output=%s, default_id=%d", output_topic.c_str(),
                static_cast<int>(default_id));
}

void MotionMuxNode::loadSources()
{
    auto ids = this->declare_parameter<std::vector<int64_t>>("source_ids", std::vector<int64_t>{});
    for (auto id_i64 : ids)
    {
        uint8_t id = static_cast<uint8_t>(id_i64);
        std::string prefix = "source_" + std::to_string(id);

        auto name = this->declare_parameter<std::string>(prefix + ".name", "");
        auto topic = this->declare_parameter<std::string>(prefix + ".topic", "");
        auto timeout = this->declare_parameter<int>(prefix + ".timeout_ms", 200);

        // V-07 check moved here from validateSources — empty name/topic caused
        // create_subscription to fail before validateSources could run. Enforce
        // FATAL at load time so error source is clear in io_contract §11 V-07 terms.
        if (name.empty() || topic.empty())
        {
            RCLCPP_FATAL(get_logger(), "V-07: source id=%d missing required field (name or topic)", id);
            rclcpp::shutdown();
            throw std::runtime_error("V-07: missing required field");
        }

        auto entry = std::make_unique<SourceEntry>();
        entry->id = id;
        entry->name = name;
        entry->topic = topic;
        entry->timeout = std::chrono::milliseconds(timeout);
        entry->latest = nullptr;
        entry->last_stamp = this->now();

        // 콜백 (active 체크 후 즉시 pass-through)
        entry->sub = this->create_subscription<trnav_msgs::msg::WheelSetArray>(
            topic, rclcpp::QoS(10), [this, id](trnav_msgs::msg::WheelSetArray::SharedPtr msg) {
                if (active_id_.load() == id)
                {
                    pub_->publish(*msg);
                }
            });

        RCLCPP_INFO(get_logger(), "Registered source id=%d name=%s topic=%s", id, name.c_str(), topic.c_str());
        sources_[id] = std::move(entry);
    }
    RCLCPP_INFO(get_logger(), "Loaded %zu motion source(s).", sources_.size());
}

void MotionMuxNode::validateSources(int default_source_id)
{
    // V-07: handled in loadSources (empty name/topic causes create_subscription
    //       to fail, so V-07 must FATAL at load time — cannot be reached here).
    //
    // 검증 순서 (2026-05-16 재정렬):
    //   Pass 1: generic schema (V-05 name 중복 / V-06 topic 중복 / V-10 topic 패턴)
    //   Pass 2: V-08 default_source_id 존재
    //   Pass 3: Reserved name (V-01/V-02/V-04/V-11/V-12~V-19 — kReservedRules)
    // generic schema 를 Reserved name 검증보다 먼저 수행하여, fixture 의 의도된 V-XX 마커가
    // Reserved name reject 보다 먼저 stderr 에 노출되도록 보장 (launch_test 호환).

    // ── Pass 1: generic schema ──
    std::set<std::string> names, topics;
    for (const auto &kv : sources_)
    {
        const uint8_t id = kv.first;
        const auto &src = kv.second;

        // V-04: id 중복 — sources_ 가 std::unordered_map<uint8_t,...> 이라 자동 unique (생략)

        // V-05: name 중복
        if (!names.insert(src->name).second)
        {
            RCLCPP_FATAL(get_logger(), "V-05: duplicate source name='%s'", src->name.c_str());
            rclcpp::shutdown();
            throw std::runtime_error("V-05: duplicate name");
        }

        // V-06: topic 중복
        if (!topics.insert(src->topic).second)
        {
            RCLCPP_FATAL(get_logger(), "V-06: duplicate source topic='%s'", src->topic.c_str());
            rclcpp::shutdown();
            throw std::runtime_error("V-06: duplicate topic");
        }

        // V-09: uint8_t 이라 자동 non-negative (생략)

        // V-10: topic 패턴 권고 (WARN only)
        if (src->topic.find("/motion/wheel_cmd/") != 0)
        {
            RCLCPP_WARN(get_logger(),
                        "V-10: source id=%d topic '%s' does not follow /motion/wheel_cmd/<name> convention", id,
                        src->topic.c_str());
        }
    }

    // ── Pass 2: V-08 default_source_id 존재 확인 ──
    if (sources_.find(static_cast<uint8_t>(default_source_id)) == sources_.end())
    {
        RCLCPP_FATAL(get_logger(), "V-08: default_source_id=%d not found in sources", default_source_id);
        rclcpp::shutdown();
        throw std::runtime_error("V-08: default_source_id not in sources");
    }

    // ── Pass 3: Reserved Source ID → name 검증 ──
    // SSOT: kReservedRules / docs/abstraction/motion_source_id_contract.md
    // V-03 (폐지, 2026-04-27): id=2 영구 예약 정책 폐기 — translate_reverse 에 재배정 (kReservedRules id=2 참조).
    for (const auto &kv : sources_)
    {
        const uint8_t id = kv.first;
        const auto &src = kv.second;
        for (const auto &rule : kReservedRules)
        {
            if (id == rule.id && src->name != rule.name)
            {
                RCLCPP_FATAL(get_logger(), "%s: Reserved id=%d must have name='%s', got '%s'", rule.rule_id, id,
                             rule.name, src->name.c_str());
                rclcpp::shutdown();
                throw std::runtime_error(std::string(rule.rule_id) + ": id=" + std::to_string(id) + " must be '" +
                                         rule.name + "'");
            }
        }
    }

    RCLCPP_INFO(get_logger(), "Config validation passed. %zu sources registered.", sources_.size());
}

void MotionMuxNode::onSelectSource(const std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Request> req,
                                   std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Response> res)
{
    uint8_t id = req->source_id;

    // id=0도 일반 id처럼 취급. 특수 케이스 없음.
    auto it = sources_.find(id);
    if (it == sources_.end())
    {
        res->success = false;
        res->message = "Unknown source_id: " + std::to_string(id);
        RCLCPP_WARN(get_logger(), "%s", res->message.c_str());
        return;
    }

    active_id_.store(id);
    res->success = true;
    res->message = "Active source set to: " + it->second->name;
    RCLCPP_INFO(get_logger(), "%s", res->message.c_str());
}

} // namespace trnav_motion_mux

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<trnav_motion_mux::MotionMuxNode>();
    rclcpp::executors::MultiThreadedExecutor executor;
    executor.add_node(node);
    executor.spin();
    rclcpp::shutdown();
    return 0;
}
