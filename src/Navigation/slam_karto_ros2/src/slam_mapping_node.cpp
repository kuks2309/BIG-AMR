// slam_karto_ros2 — Seer SLAM 매핑 ROS2 노드.
//
//   구독: /scan_merged (sensor_msgs/LaserScan, SensorDataQoS=BEST_EFFORT)
//         /odom        (nav_msgs/Odometry,   BEST_EFFORT — icp_odometry 가 BEST_EFFORT 로 낸다)
//   발행: /map         (nav_msgs/OccupancyGrid, transient_local)
//   서비스: ~/start_mapping ~/stop_mapping ~/save_map ~/mapping_status (std_srvs/Trigger)
//   원본 대응: 6100(매핑 시작) / 6101(매핑 종료) / 4010(맵 저장)
//
// ⚠ 이 노드는 **TF 를 발행하지 않는다.** map→odom 은 mcl2d 가 소유한다
//   (docs/code_review/mcl2d-localization-chain/2026-08-07.md H1 — 부모 중복이 TF 트리를 깬다).
//   매핑 중에는 mcl2d 를 띄우지 말 것. README 참조.
//
// 스레딩: 무거운 처리(스캔매칭 + 루프클로저 + g2o 최적화)는 **워커 스레드**에서 돈다.
//   콜백 스레드에서 processRecord 를 직접 부르면 executor 가 수백 ms 막혀 구독이 밀린다.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "nav_msgs/msg/occupancy_grid.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "std_srvs/srv/trigger.hpp"
#include "tf2/utils.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

#include "mcl2d_map/smap.hpp"
#include "slam_karto_core/seer_slam_mapper.hpp"

namespace
{

// ── 명명 상수 (매직넘버 금지) ────────────────────────────────────────────────

/// .smap 격자 해상도 기본값 (m/cell). 근거: 회수한 실맵 헤더가 전부 이 값이다 —
/// `map/260709_test.smap` · `References/seer/slam_mapping/maps/*.smap` 의 `"resolution":0.02`.
constexpr double kSeerMapResolutionM = 0.02;

/// OccupancyGrid 셀 값. 점유셀만 100 으로 찍고 나머지는 미지(-1)로 둔다.
/// free space 라이캐스팅은 하지 않는다 — 원본 산출물이 점군이고, 자유공간 판정의 근거가 아직 없다.
constexpr std::int8_t kOccupiedCellValue = 100;
constexpr std::int8_t kUnknownCellValue = -1;

/// 점군 경계 바깥으로 두는 여유 (cell). 경계 점이 격자 끝에 딱 붙는 것을 피한다.
constexpr int kMapMarginCells = 1;

/// 격자 셀 수 상한 기본값 (cell). 0.02 m 에서 5000x5000 = 100 m x 100 m.
/// OccupancyGrid.data 는 셀당 1 byte 라 이 값이 곧 메시지 크기(바이트)다.
constexpr std::int64_t kDefaultMaxMapCells = 25000000;

/// 스캔 처리 큐 기본 길이 (개).
constexpr int kDefaultQueueSize = 50;

/// 스캔 시각과 오도 시각의 허용 최대 차 (s). 이보다 벌어지면 그 스캔은 버린다.
/// 병합 스캔 주기가 0.067 s(dual_sick_merger.launch.py `scan_time`)이므로 그 절반 수준.
constexpr double kDefaultOdomMatchMaxDtSec = 0.035;

/// 오도 링버퍼 길이 (개). 34 Hz 기준 약 6 초분.
constexpr std::size_t kOdomBufferSize = 200;

/// /map 재산출·발행 주기 기본값 (s). buildMap 은 전 스캔을 훑으므로 스캔 주기로 돌리면 안 된다.
constexpr double kDefaultMapPublishPeriodSec = 2.0;

/// g2o LM 반복 상한 기본값. 코어 기본값과 동일(slam_karto_core/src/g2o_solver.cpp:84 `max_iterations_`).
/// LM 반복 상한 — **원본 실측값 50** (`0xebb20 mov $0x32,%esi` → `optimize(50,false)`).
constexpr int kDefaultG2oMaxIterations = 50;

/// 라이다 거리 유효구간 기본값 (m). SICK microScan3 의 실사용 구간.
/// **원본 실측값 0.001** — `KartoSLAM` 생성자가 `SetMinimumRange(0.001)` 로 하드코딩한다(KartoSLAM.cpp:32).
constexpr double kDefaultMinRangeM = 0.001;
constexpr double kDefaultMaxRangeM = 30.0;

/// rssi(반사강도) 임계 기본값. 이 값을 **초과**하는 빔만 반사판 점군에 들어간다.
/// ⚠ 원본 `RssiThres` 런타임값은 미확정이다(코어 헤더 seer_slam_mapper.hpp:72-73).
/// **원본 실측값 150.0** — `SlaMapping::run()` 이 `RssiThres` 에 넣는 리터럴(SlaMapping.cpp:91 @0x7048b).
///   교차 확인: 위치추정 쪽 `robot.param` 의 `MCLoc.ReflectorRSSI` 도 150.0.
constexpr double kDefaultRssiThreshold = 150.0;

/// 워커가 큐 대기에서 깨어나는 최대 간격 (ms). 큐가 비어도 맵 발행 주기를 지키기 위해 필요하다.
constexpr int kWorkerIdleWaitMs = 50;

/// 반복 로그 억제 간격 (ms).
constexpr int kLogThrottleMs = 5000;

/// .smap 헤더에 쓸 포맷 버전 기본값. 근거: 회수 실맵 `map/260709_test.smap` 의 `"version":"1.0.6"`.
constexpr const char *kDefaultSmapVersion = "1.0.6";

/// .smap 헤더 mapType. 회수 실맵 전부 이 값이다.
constexpr const char *kSmapMapType = "2D-Map";

/// 큐 포화 정책 문자열.
constexpr const char *kPolicyKeepLatest = "keep_latest"; ///< 가장 오래된 것을 버리고 새 것을 넣는다
constexpr const char *kPolicyDropNewest = "drop_newest"; ///< 새로 온 것을 버린다

/// 한 시점의 오도메트리 표본. yaw 단위 rad, 위치 단위 m.
struct OdomSample
{
    rclcpp::Time stamp;
    double x = 0.0;
    double y = 0.0;
    double yaw = 0.0;
};

} // namespace

class SlamMappingNode : public rclcpp::Node
{
  public:
    SlamMappingNode() : rclcpp::Node("slam_mapping")
    {
        // ── 파라미터 ─────────────────────────────────────────────────────────
        const std::string scan_topic = declare_parameter<std::string>("scan_topic", "/scan_merged");
        const std::string odom_topic = declare_parameter<std::string>("odom_topic", "/odom");
        const std::string map_topic = declare_parameter<std::string>("map_topic", "/map");
        map_frame_ = declare_parameter<std::string>("map_frame", "map");

        // 라이다 장착 [x, y, yaw] (m, m, rad) — **스캔 토픽의 프레임 기준 로봇좌표계 오프셋**.
        //   기본값이 0 인 이유: 기본 입력 /scan_merged 는 frame_id `scan_merged` 이고, 그 프레임은
        //   base_link 와 동일 위치로 static TF 가 걸린다
        //   (dual_laser_merger/launch/dual_sick_merger.launch.py:41-43 → arguments 전부 0).
        //   병합기가 두 센서 빔을 이미 이 프레임으로 옮겨 놓으므로 여기서 또 오프셋을 주면 이중 적용이다.
        //   ※ 원시 단일 라이다(/scan_front·/scan_rear)를 직접 물릴 때는 그 센서의 실측 장착값을
        //     넣어야 한다 — Foil_A082 정값은 mcl2d_ros2/config/mcl2d.yaml:26-27 참조
        //     (FrontLiDAR 0.881676, -0.578664, -0.785398 / RearLiDAR -0.857, 0.5971, 2.361256).
        laser_offset_x_ = declare_parameter<double>("laser_offset_x", 0.0);
        laser_offset_y_ = declare_parameter<double>("laser_offset_y", 0.0);
        laser_offset_yaw_ = declare_parameter<double>("laser_offset_yaw", 0.0);

        min_range_ = declare_parameter<double>("min_range", kDefaultMinRangeM);
        max_range_ = declare_parameter<double>("max_range", kDefaultMaxRangeM);
        map_resolution_ = declare_parameter<double>("map_resolution", kSeerMapResolutionM);
        max_map_cells_ = declare_parameter<int>("max_map_cells", static_cast<int>(kDefaultMaxMapCells));
        rssi_threshold_ = declare_parameter<double>("rssi_threshold", kDefaultRssiThreshold);
        g2o_max_iterations_ = declare_parameter<int>("g2o_max_iterations", kDefaultG2oMaxIterations);
        queue_size_ = static_cast<std::size_t>(declare_parameter<int>("queue_size", kDefaultQueueSize));
        queue_policy_ = declare_parameter<std::string>("queue_full_policy", kPolicyKeepLatest);
        odom_match_max_dt_ = declare_parameter<double>("odom_match_max_dt", kDefaultOdomMatchMaxDtSec);
        map_publish_period_ = declare_parameter<double>("map_publish_period", kDefaultMapPublishPeriodSec);
        auto_start_ = declare_parameter<bool>("auto_start", true);
        save_path_ = declare_parameter<std::string>("save_path", "");
        map_name_ = declare_parameter<std::string>("map_name", "slam_map");
        smap_version_ = declare_parameter<std::string>("smap_version", kDefaultSmapVersion);

        validateParams();

        mapper_ = makeMapper();
        accepting_ = auto_start_;

        // ── 통신 ─────────────────────────────────────────────────────────────
        // /map 은 늦게 붙는 소비자(rviz)가 마지막 맵을 받도록 transient_local 로 낸다.
        rclcpp::QoS map_qos(1);
        map_qos.transient_local().reliable();
        map_pub_ = create_publisher<nav_msgs::msg::OccupancyGrid>(map_topic, map_qos);

        // 라이다는 SensorDataQoS(BEST_EFFORT)로 발행된다 — RELIABLE 로 구독하면 QoS 불일치로
        //   한 건도 오지 않는다(mcl2d 노드 주석의 /odom 사례와 같은 함정).
        scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
            scan_topic, rclcpp::SensorDataQoS(),
            [this](sensor_msgs::msg::LaserScan::SharedPtr m) { onScan(*m); });

        // /odom 도 BEST_EFFORT 로 구독한다. icp_odometry(rtabmap_odom)가 BEST_EFFORT 로 발행하므로
        //   RELIABLE 구독은 연결되지 않는다(mcl2d_localization_node.cpp 동일 주석 근거).
        //   BEST_EFFORT 구독자는 RELIABLE 발행자와도 연결되므로 이쪽이 항상 넓다.
        rclcpp::QoS odom_qos(static_cast<std::size_t>(kOdomBufferSize));
        odom_qos.best_effort();
        odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
            odom_topic, odom_qos, [this](nav_msgs::msg::Odometry::SharedPtr m) { onOdom(*m); });

        start_srv_ = create_service<std_srvs::srv::Trigger>(
            "~/start_mapping",
            [this](const std::shared_ptr<std_srvs::srv::Trigger::Request> req,
                   std::shared_ptr<std_srvs::srv::Trigger::Response> res) { onStart(req, res); });
        stop_srv_ = create_service<std_srvs::srv::Trigger>(
            "~/stop_mapping",
            [this](const std::shared_ptr<std_srvs::srv::Trigger::Request> req,
                   std::shared_ptr<std_srvs::srv::Trigger::Response> res) { onStop(req, res); });
        save_srv_ = create_service<std_srvs::srv::Trigger>(
            "~/save_map",
            [this](const std::shared_ptr<std_srvs::srv::Trigger::Request> req,
                   std::shared_ptr<std_srvs::srv::Trigger::Response> res) { onSave(req, res); });
        status_srv_ = create_service<std_srvs::srv::Trigger>(
            "~/mapping_status",
            [this](const std::shared_ptr<std_srvs::srv::Trigger::Request> req,
                   std::shared_ptr<std_srvs::srv::Trigger::Response> res) { onStatus(req, res); });

        RCLCPP_INFO(get_logger(),
                    "slam_mapping 기동: scan=%s odom=%s map=%s res=%.3fm queue=%zu(%s) auto_start=%d",
                    scan_topic.c_str(), odom_topic.c_str(), map_topic.c_str(), map_resolution_,
                    queue_size_, queue_policy_.c_str(), auto_start_ ? 1 : 0);
        RCLCPP_INFO(get_logger(), "TF 는 발행하지 않는다 — map→odom 은 mcl2d 소유. 매핑 중 mcl2d 동시 기동 금지.");

        last_map_build_ = now();
        worker_ = std::thread([this] { workerLoop(); });
    }

    ~SlamMappingNode() override
    {
        {
            std::lock_guard<std::mutex> lk(queue_mutex_);
            running_ = false;
        }
        queue_cv_.notify_all();
        if (worker_.joinable())
        {
            worker_.join();
        }
    }

  private:
    /// 워커에 넘길 한 건의 처리 단위.
    struct WorkItem
    {
        slam_karto_core::MapLogRecord rec;
        slam_karto_core::LaserGeometry geom;
    };

    // ── 파라미터 검증 ────────────────────────────────────────────────────────

    /// 잘못된 값으로 조용히 도는 것보다 기동 실패가 낫다(mcl2d 선례).
    void validateParams()
    {
        if (!(map_resolution_ > 0.0))
        {
            RCLCPP_FATAL(get_logger(), "map_resolution 은 양수여야 한다 (받은 값 %.6f)", map_resolution_);
            throw std::invalid_argument("map_resolution must be > 0");
        }
        if (!(max_range_ > min_range_))
        {
            RCLCPP_FATAL(get_logger(), "max_range(%.3f) 는 min_range(%.3f) 보다 커야 한다", max_range_, min_range_);
            throw std::invalid_argument("max_range must exceed min_range");
        }
        if (queue_size_ == 0)
        {
            RCLCPP_FATAL(get_logger(), "queue_size 는 1 이상이어야 한다");
            throw std::invalid_argument("queue_size must be >= 1");
        }
        if (queue_policy_ != kPolicyKeepLatest && queue_policy_ != kPolicyDropNewest)
        {
            RCLCPP_FATAL(get_logger(), "queue_full_policy 는 \"%s\" 또는 \"%s\" 여야 한다 (받은 값 \"%s\")",
                         kPolicyKeepLatest, kPolicyDropNewest, queue_policy_.c_str());
            throw std::invalid_argument("invalid queue_full_policy");
        }
        if (max_map_cells_ <= 0)
        {
            RCLCPP_FATAL(get_logger(), "max_map_cells 는 1 이상이어야 한다");
            throw std::invalid_argument("max_map_cells must be >= 1");
        }
    }

    /// 새 매퍼를 만든다. 파라미터(rssi 임계·g2o 반복수)를 적용한 상태로 돌려준다.
    std::unique_ptr<slam_karto_core::SeerSlamMapper> makeMapper() const
    {
        auto m = std::make_unique<slam_karto_core::SeerSlamMapper>();
        m->setRssiThreshold(rssi_threshold_);
        m->setMaxIterations(g2o_max_iterations_);
        return m;
    }

    // ── 구독 콜백 (executor 스레드 — 가볍게 유지한다) ───────────────────────

    void onOdom(const nav_msgs::msg::Odometry &o)
    {
        tf2::Quaternion q;
        tf2::fromMsg(o.pose.pose.orientation, q);
        OdomSample s;
        s.stamp = rclcpp::Time(o.header.stamp);
        s.x = o.pose.pose.position.x;
        s.y = o.pose.pose.position.y;
        s.yaw = tf2::getYaw(q);

        std::lock_guard<std::mutex> lk(odom_mutex_);
        odom_buf_.push_back(s);
        while (odom_buf_.size() > kOdomBufferSize)
        {
            odom_buf_.pop_front();
        }
    }

    /// 스캔 시각에 가장 가까운 오도 표본을 고른다.
    ///
    /// **선형보간이 아니라 최근접(nearest-in-time)을 택했다.** 이 스택에서 /odom 은 바로 그
    /// /scan_merged 로부터 icp_odometry 가 산출한다(icp_odometry_bringup/launch/icp_odometry.launch.py:4,63).
    /// 즉 스캔과 오도는 같은 원천·같은 주기라 스캔 시각을 감싸는 두 오도 표본이 있는 상황 자체가
    /// 드물고, 있어도 보간은 ICP 가 보고하지 않은 중간 운동을 지어내는 셈이 된다.
    /// 대신 시각차 게이트(odom_match_max_dt)를 두어 짝이 멀면 그 스캔을 버린다.
    ///
    /// @param  stamp 스캔 시각
    /// @return 짝지은 오도 표본. 버퍼가 비었거나 시각차가 게이트를 넘으면 비어 있다.
    std::optional<OdomSample> matchOdom(const rclcpp::Time &stamp) const
    {
        std::lock_guard<std::mutex> lk(odom_mutex_);
        if (odom_buf_.empty())
        {
            return std::nullopt;
        }
        const OdomSample *best = nullptr;
        double best_dt = 0.0;
        for (const auto &s : odom_buf_)
        {
            const double dt = std::fabs((stamp - s.stamp).seconds());
            if (best == nullptr || dt < best_dt)
            {
                best = &s;
                best_dt = dt;
            }
        }
        if (best_dt > odom_match_max_dt_)
        {
            return std::nullopt;
        }
        return *best;
    }

    void onScan(const sensor_msgs::msg::LaserScan &scan)
    {
        if (!accepting_.load())
        {
            return;
        }
        if (scan.ranges.empty())
        {
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs, "빈 스캔 수신 — 무시");
            return;
        }
        const auto odo = matchOdom(rclcpp::Time(scan.header.stamp));
        if (!odo)
        {
            ++dropped_no_odom_;
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs,
                                 "스캔에 맞는 오도(±%.3fs)를 못 찾았다 — 누적 %lu건 폐기",
                                 odom_match_max_dt_, static_cast<unsigned long>(dropped_no_odom_.load()));
            return;
        }

        WorkItem item;
        const std::size_t n = scan.ranges.size();
        item.rec.odo_x = odo->x;
        item.rec.odo_y = odo->y;
        item.rec.odo_w = odo->yaw;
        item.rec.beam_dist.resize(n);
        item.rec.beam_angle.resize(n);
        for (std::size_t i = 0; i < n; ++i)
        {
            // 각도는 헤더값에서 재구성한다 — 코어가 균일 간격을 요구하므로 누산이 아니라 곱으로 만든다.
            item.rec.beam_angle[i] = scan.angle_min + static_cast<double>(i) * scan.angle_increment;
            item.rec.beam_dist[i] = static_cast<double>(scan.ranges[i]); // 비유한·범위밖은 코어가 정규화
        }
        if (scan.intensities.size() == n)
        {
            item.rec.beam_rssi.resize(n);
            for (std::size_t i = 0; i < n; ++i)
            {
                item.rec.beam_rssi[i] = static_cast<double>(scan.intensities[i]);
            }
        }
        item.geom.min_angle = scan.angle_min;
        item.geom.angular_resolution = scan.angle_increment;
        item.geom.min_range = min_range_;
        item.geom.max_range = max_range_;
        item.geom.offset_x = laser_offset_x_;
        item.geom.offset_y = laser_offset_y_;
        item.geom.offset_yaw = laser_offset_yaw_;

        {
            std::lock_guard<std::mutex> lk(queue_mutex_);
            if (queue_.size() >= queue_size_)
            {
                if (queue_policy_ == kPolicyDropNewest)
                {
                    ++dropped_queue_full_;
                    logQueueDrop();
                    return;
                }
                queue_.pop_front(); // keep_latest — 가장 오래된 것을 버린다
                ++dropped_queue_full_;
                logQueueDrop();
            }
            queue_.push_back(std::move(item));
        }
        queue_cv_.notify_one();
    }

    /// 큐 포화 폐기를 알린다. `get_clock()` 이 비-const 라 이 함수도 비-const 여야 한다.
    void logQueueDrop()
    {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs,
                             "처리 큐 포화(%zu) 정책=%s — 누적 %lu건 폐기 (매핑이 입력보다 느리다)",
                             queue_size_, queue_policy_.c_str(),
                             static_cast<unsigned long>(dropped_queue_full_.load()));
    }

    // ── 워커 스레드 ──────────────────────────────────────────────────────────

    void workerLoop()
    {
        while (true)
        {
            WorkItem item;
            bool have = false;
            {
                std::unique_lock<std::mutex> lk(queue_mutex_);
                queue_cv_.wait_for(lk, std::chrono::milliseconds(kWorkerIdleWaitMs),
                                   [this] { return !queue_.empty() || !running_; });
                if (!running_)
                {
                    return;
                }
                if (!queue_.empty())
                {
                    item = std::move(queue_.front());
                    queue_.pop_front();
                    have = true;
                }
            }
            if (have)
            {
                processOne(item);
            }
            maybePublishMap();
        }
    }

    void processOne(const WorkItem &item)
    {
        slam_karto_core::ProcessResult r;
        std::string err;
        int n_scans = 0;
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            r = mapper_->processRecord(item.rec, item.geom);
            if (r == slam_karto_core::ProcessResult::kInvalidInput)
            {
                err = mapper_->lastError();
            }
            n_scans = mapper_->numScans();
        }
        switch (r)
        {
        case slam_karto_core::ProcessResult::kAdded:
            ++n_added_;
            map_dirty_ = true;
            RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs,
                                 "스캔 추가 %d개 (게이트 폐기 %lu, 입력불량 %lu, 큐폐기 %lu)", n_scans,
                                 static_cast<unsigned long>(n_gated_.load()),
                                 static_cast<unsigned long>(n_invalid_.load()),
                                 static_cast<unsigned long>(dropped_queue_full_.load()));
            break;
        case slam_karto_core::ProcessResult::kGateRejected:
            ++n_gated_; // 이동 게이트 미달 — 정상 동작이다
            break;
        case slam_karto_core::ProcessResult::kInvalidInput:
            ++n_invalid_;
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs, "입력 검증 실패: %s", err.c_str());
            break;
        }
    }

    /// 주기가 됐고 새 스캔이 들어왔으면 맵을 재산출해 발행한다. **워커 스레드에서만 부른다.**
    void maybePublishMap()
    {
        if (!map_dirty_)
        {
            return;
        }
        const rclcpp::Time t = now();
        if ((t - last_map_build_).seconds() < map_publish_period_)
        {
            return;
        }
        last_map_build_ = t;
        map_dirty_ = false;

        slam_karto_core::MapResult m;
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            m = mapper_->buildMap();
        }
        publishGrid(m, t);
    }

    /// 점군을 격자로 래스터화해 /map 으로 낸다.
    /// 점유셀만 100, 나머지는 미지(-1). free space 라이캐스팅은 하지 않는다.
    /// @param m 매핑 결과 (좌표 m, map 프레임)
    /// @param stamp 헤더 시각
    void publishGrid(const slam_karto_core::MapResult &m, const rclcpp::Time &stamp)
    {
        if (!m.valid || m.normal_pos_list.empty())
        {
            return;
        }
        const double res = map_resolution_;
        const double origin_x = m.min_x - kMapMarginCells * res;
        const double origin_y = m.min_y - kMapMarginCells * res;
        const std::int64_t w =
            static_cast<std::int64_t>(std::floor((m.max_x - origin_x) / res)) + 1 + kMapMarginCells;
        const std::int64_t h =
            static_cast<std::int64_t>(std::floor((m.max_y - origin_y) / res)) + 1 + kMapMarginCells;
        if (w <= 0 || h <= 0)
        {
            return;
        }
        if (w * h > static_cast<std::int64_t>(max_map_cells_))
        {
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), kLogThrottleMs,
                                 "격자 %ldx%ld = %ld셀 이 상한 %d 를 넘어 /map 발행 생략 "
                                 "(map_resolution 을 키우거나 max_map_cells 를 올릴 것)",
                                 static_cast<long>(w), static_cast<long>(h), static_cast<long>(w * h),
                                 max_map_cells_);
            return;
        }

        nav_msgs::msg::OccupancyGrid grid;
        grid.header.stamp = stamp;
        grid.header.frame_id = map_frame_;
        grid.info.map_load_time = stamp;
        grid.info.resolution = static_cast<float>(res);
        grid.info.width = static_cast<std::uint32_t>(w);
        grid.info.height = static_cast<std::uint32_t>(h);
        grid.info.origin.position.x = origin_x;
        grid.info.origin.position.y = origin_y;
        grid.info.origin.orientation.w = 1.0;
        grid.data.assign(static_cast<std::size_t>(w * h), kUnknownCellValue);

        for (const auto &p : m.normal_pos_list)
        {
            const std::int64_t ix = static_cast<std::int64_t>(std::floor((p.first - origin_x) / res));
            const std::int64_t iy = static_cast<std::int64_t>(std::floor((p.second - origin_y) / res));
            if (ix < 0 || iy < 0 || ix >= w || iy >= h)
            {
                continue; // 경계 계산의 부동소수 오차로 밖으로 나가는 점을 버린다
            }
            grid.data[static_cast<std::size_t>(iy * w + ix)] = kOccupiedCellValue;
        }
        map_pub_->publish(grid);
        RCLCPP_INFO(get_logger(), "/map 발행: %ldx%ld cell, 점군 %zu (스캔 %d)", static_cast<long>(w),
                    static_cast<long>(h), m.normal_pos_list.size(), m.num_scans);
    }

    // ── 서비스 (executor 스레드) ────────────────────────────────────────────

    /// 원본 6100 대응. 기존 그래프를 버리고 새로 매핑을 시작한다.
    void onStart(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*req*/,
                 std::shared_ptr<std_srvs::srv::Trigger::Response> res)
    {
        accepting_.store(false); // 먼저 유입을 끊고 나서 교체한다
        {
            std::lock_guard<std::mutex> lk(queue_mutex_);
            queue_.clear();
        }
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            mapper_ = makeMapper();
        }
        n_added_ = 0;
        n_gated_ = 0;
        n_invalid_ = 0;
        dropped_queue_full_ = 0;
        dropped_no_odom_ = 0;
        map_dirty_ = false;
        last_map_build_ = now();
        accepting_.store(true);
        res->success = true;
        res->message = "매핑 시작 (그래프 초기화)";
        RCLCPP_INFO(get_logger(), "%s", res->message.c_str());
    }

    /// 원본 6101 대응. 유입을 끊는다. 그래프는 남겨 둔다 — 이어서 save_map 을 부를 수 있어야 한다.
    void onStop(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*req*/,
                std::shared_ptr<std_srvs::srv::Trigger::Response> res)
    {
        accepting_.store(false);
        int n = 0;
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            n = mapper_->numScans();
        }
        res->success = true;
        res->message = "매핑 종료 — 스캔 " + std::to_string(n) + "개 (" + statusText() + ")";
        RCLCPP_INFO(get_logger(), "%s", res->message.c_str());
    }

    /// 원본 4010 대응. 현재 그래프에서 맵을 산출해 .smap 으로 저장한다.
    /// 저장 경로는 파라미터 `save_path`. 비어 있으면 실패로 돌려준다.
    /// ※ buildMap 은 무겁다 — 이 호출 동안 executor 가 잠시 막힌다(명시적 사용자 조작이라 허용).
    void onSave(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*req*/,
                std::shared_ptr<std_srvs::srv::Trigger::Response> res)
    {
        const std::string path = get_parameter("save_path").as_string();
        if (path.empty())
        {
            res->success = false;
            res->message = "save_path 파라미터가 비어 있다 — 저장 경로를 먼저 설정하라 "
                           "(ros2 param set /slam_mapping save_path /path/to/x.smap)";
            RCLCPP_ERROR(get_logger(), "%s", res->message.c_str());
            return;
        }

        slam_karto_core::MapResult m;
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            m = mapper_->buildMap();
        }
        if (!m.valid)
        {
            res->success = false;
            res->message = "저장할 맵이 없다 (스캔 " + std::to_string(m.num_scans) + "개, 점군 0)";
            RCLCPP_ERROR(get_logger(), "%s", res->message.c_str());
            return;
        }

        mcl2d::SmapMap sm;
        sm.map_type = kSmapMapType;
        sm.map_name = get_parameter("map_name").as_string();
        sm.version = get_parameter("smap_version").as_string();
        sm.resolution = map_resolution_;
        sm.min_x = m.min_x;
        sm.min_y = m.min_y;
        sm.max_x = m.max_x;
        sm.max_y = m.max_y;
        sm.obstacles = m.normal_pos_list;
        sm.rssi_points = m.rssi_pos_list;
        sm.valid = true;

        if (!mcl2d::saveSmap(sm, path))
        {
            res->success = false;
            res->message = "saveSmap 실패: " + path + " (경로 권한 또는 좌표에 NaN/inf)";
            RCLCPP_ERROR(get_logger(), "%s", res->message.c_str());
            return;
        }
        res->success = true;
        res->message = "저장 완료: " + path + " (스캔 " + std::to_string(m.num_scans) + ", 장애물 " +
                       std::to_string(sm.obstacles.size()) + ", 반사판 " +
                       std::to_string(sm.rssi_points.size()) + ")";
        RCLCPP_INFO(get_logger(), "%s", res->message.c_str());
    }

    /// 진단 — 처리·폐기 카운터와 최적화 계측을 문자열로 돌려준다.
    void onStatus(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*req*/,
                  std::shared_ptr<std_srvs::srv::Trigger::Response> res)
    {
        res->success = true;
        res->message = statusText();
    }

    std::string statusText()
    {
        int n_scans = 0;
        slam_karto_core::SolverStats st;
        {
            std::lock_guard<std::mutex> lk(mapper_mutex_);
            n_scans = mapper_->numScans();
            st = mapper_->solverStats();
        }
        std::size_t qlen = 0;
        {
            std::lock_guard<std::mutex> lk(queue_mutex_);
            qlen = queue_.size();
        }
        return std::string("accepting=") + (accepting_.load() ? "1" : "0") +
               " scans=" + std::to_string(n_scans) + " queue=" + std::to_string(qlen) + "/" +
               std::to_string(queue_size_) + " added=" + std::to_string(n_added_.load()) +
               " gate_rejected=" + std::to_string(n_gated_.load()) +
               " invalid=" + std::to_string(n_invalid_.load()) +
               " dropped_queue_full=" + std::to_string(dropped_queue_full_.load()) +
               " dropped_no_odom=" + std::to_string(dropped_no_odom_.load()) +
               " g2o_compute_calls=" + std::to_string(st.compute_calls) +
               " nodes=" + std::to_string(st.nodes_added) + " edges=" + std::to_string(st.edges_added) +
               " edges_rejected=" + std::to_string(st.edges_rejected) +
               " last_iterations=" + std::to_string(st.last_iterations) +
               " has_fixed_node=" + (st.has_fixed_node ? "1" : "0");
    }

    // ── 상태 ─────────────────────────────────────────────────────────────────
    std::unique_ptr<slam_karto_core::SeerSlamMapper> mapper_;
    mutable std::mutex mapper_mutex_; ///< mapper_ 전체(처리·buildMap·교체)를 지킨다

    std::deque<WorkItem> queue_;
    mutable std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    bool running_ = true; ///< queue_mutex_ 보호
    std::thread worker_;

    std::deque<OdomSample> odom_buf_;
    mutable std::mutex odom_mutex_;

    rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr map_pub_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr start_srv_, stop_srv_, save_srv_, status_srv_;

    std::atomic<bool> accepting_{false};
    std::atomic<std::size_t> n_added_{0}, n_gated_{0}, n_invalid_{0};
    std::atomic<std::size_t> dropped_queue_full_{0}, dropped_no_odom_{0};
    bool map_dirty_ = false;      ///< 워커 스레드 전용
    rclcpp::Time last_map_build_; ///< 워커 스레드 전용

    std::string map_frame_, queue_policy_, save_path_, map_name_, smap_version_;
    double laser_offset_x_ = 0.0, laser_offset_y_ = 0.0, laser_offset_yaw_ = 0.0;
    double min_range_ = kDefaultMinRangeM, max_range_ = kDefaultMaxRangeM;
    double map_resolution_ = kSeerMapResolutionM;
    double rssi_threshold_ = kDefaultRssiThreshold;
    double odom_match_max_dt_ = kDefaultOdomMatchMaxDtSec;
    double map_publish_period_ = kDefaultMapPublishPeriodSec;
    int max_map_cells_ = static_cast<int>(kDefaultMaxMapCells);
    int g2o_max_iterations_ = kDefaultG2oMaxIterations;
    std::size_t queue_size_ = static_cast<std::size_t>(kDefaultQueueSize);
    bool auto_start_ = true;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SlamMappingNode>());
    rclcpp::shutdown();
    return 0;
}
