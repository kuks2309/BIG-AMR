// smap_map_server — Seer `.smap` 을 nav_msgs/OccupancyGrid 로 발행한다.
//
// 왜 별도 노드인가: 측위(mcl2d_localization_node)는 `.smap` 을 읽어 **내부 우도장**으로만 쓰고
//   ROS 로 내보내지 않는다. 그래서 (a) 측위가 어떤 맵 위에서 도는지 화면으로 확인할 수 없고
//   (b) 내비게이션(costmap)이 쓸 맵이 없다. costmap 은 MarkerArray 를 읽지 못하므로 시각화용
//   마커가 아니라 OccupancyGrid 여야 한다. 맵 제공과 측위는 책임이 다르므로 노드를 나눈다 —
//   맵만 필요한 구성(내비게이션만 시험)에서 측위를 띄우지 않아도 된다.
//
// 발행: /map (nav_msgs/OccupancyGrid, TRANSIENT_LOCAL·depth 1 = latched)
//       /map_reflectors (visualization_msgs/MarkerArray, latched) — 반사판 위치(선택)
// 맵은 기동 시 1회 읽고 바뀌지 않으므로 latch 로 한 번만 낸다. 늦게 뜬 구독자도 받는다.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

#include "mcl2d_map/smap.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "rclcpp/rclcpp.hpp"
#include "visualization_msgs/msg/marker_array.hpp"

using namespace mcl2d;

namespace
{
// OccupancyGrid 값 규약(nav_msgs): 0=free, 100=occupied, -1=unknown.
constexpr std::int8_t kFree = 0;
constexpr std::int8_t kOccupied = 100;
// 셀 수 상한 — 실수로 해상도를 0.001 로 주면 수십 GB 를 할당하려다 죽는다. 미리 막는다.
constexpr std::size_t kMaxCells = 64u * 1024u * 1024u;
} // namespace

class SmapMapServer : public rclcpp::Node
{
  public:
    SmapMapServer() : rclcpp::Node("smap_map_server")
    {
        const std::string map_path = declare_parameter<std::string>("map_path", "");
        frame_id_ = declare_parameter<std::string>("frame_id", "map");
        const double margin = declare_parameter<double>("margin", 1.0);
        const bool publish_reflectors = declare_parameter<bool>("publish_reflectors", true);

        if (map_path.empty())
        {
            RCLCPP_FATAL(get_logger(), "map_path 는 필수 파라미터다 — .smap 경로를 지정하라");
            throw std::invalid_argument("map_path is required");
        }
        const SmapMap m = loadSmap(map_path);
        if (!m.valid)
        {
            RCLCPP_FATAL(get_logger(), "맵 적재 실패: %s (파일 없음·JSON 파손·장애물 0 중 하나)", map_path.c_str());
            throw std::runtime_error("map load failed: " + map_path);
        }
        // 해상도 기본값은 맵 헤더값을 그대로 따른다(Seer 가 그 격자로 만든 맵이다).
        const double resolution = declare_parameter<double>("resolution", m.resolution);
        if (resolution <= 0.0)
        {
            RCLCPP_FATAL(get_logger(), "resolution 은 양수여야 한다 (받은 값 %.6f)", resolution);
            throw std::invalid_argument("resolution must be positive");
        }

        // 격자 범위는 **실제 점군 경계**로 잡는다. 헤더의 minPos/maxPos 는 편집 이력 때문에 실제
        //   점 분포보다 넓을 수 있어(이 기체 맵에서 실제로 그렇다) 그대로 쓰면 빈 격자가 커진다.
        //   대신 두 값을 모두 로그로 남겨 차이를 눈으로 확인할 수 있게 한다.
        double min_x = m.obstacles.front().first, max_x = min_x;
        double min_y = m.obstacles.front().second, max_y = min_y;
        for (const auto &p : m.obstacles)
        {
            min_x = std::min(min_x, p.first);
            max_x = std::max(max_x, p.first);
            min_y = std::min(min_y, p.second);
            max_y = std::max(max_y, p.second);
        }
        RCLCPP_INFO(get_logger(), "맵 %s: 헤더 범위 x[%.2f, %.2f] y[%.2f, %.2f] / 점군 범위 x[%.2f, %.2f] y[%.2f, %.2f]",
                    m.map_name.c_str(), m.min_x, m.max_x, m.min_y, m.max_y, min_x, max_x, min_y, max_y);
        min_x -= margin;
        min_y -= margin;
        max_x += margin;
        max_y += margin;

        const auto width = static_cast<std::size_t>(std::ceil((max_x - min_x) / resolution));
        const auto height = static_cast<std::size_t>(std::ceil((max_y - min_y) / resolution));
        if (width == 0 || height == 0 || width * height > kMaxCells)
        {
            RCLCPP_FATAL(get_logger(), "격자 크기가 비정상이다: %zux%zu (해상도 %.4f m). 해상도를 키워라",
                         width, height, resolution);
            throw std::runtime_error("occupancy grid size out of range");
        }

        // 점군 맵에는 자유공간 정보가 없다 — 관측된 것은 "장애물이 있는 칸" 뿐이다.
        //   경계 안쪽을 free(0) 로 두는 것은 "이 영역은 주행 가능"이라는 **가정**이며, 맵이 운영
        //   구역 전체를 덮고 있다는 전제 위에서만 맞다. 미탐색 구역까지 free 로 선언하지 않도록
        //   경계를 점군에서 잡는 이유이기도 하다.
        nav_msgs::msg::OccupancyGrid grid;
        grid.header.frame_id = frame_id_;
        grid.info.resolution = static_cast<float>(resolution);
        grid.info.width = static_cast<std::uint32_t>(width);
        grid.info.height = static_cast<std::uint32_t>(height);
        grid.info.origin.position.x = min_x;
        grid.info.origin.position.y = min_y;
        grid.info.origin.orientation.w = 1.0;
        grid.data.assign(width * height, kFree);

        std::size_t marked = 0, outside = 0;
        for (const auto &p : m.obstacles)
        {
            const auto cx = static_cast<long>((p.first - min_x) / resolution);
            const auto cy = static_cast<long>((p.second - min_y) / resolution);
            if (cx < 0 || cy < 0 || cx >= static_cast<long>(width) || cy >= static_cast<long>(height))
            {
                ++outside;
                continue;
            }
            auto &cell = grid.data[static_cast<std::size_t>(cy) * width + static_cast<std::size_t>(cx)];
            if (cell != kOccupied)
            {
                cell = kOccupied;
                ++marked;
            }
        }
        if (outside != 0)
        {
            RCLCPP_WARN(get_logger(), "격자 밖 장애물 점 %zu개 — 경계 계산 확인 필요", outside);
        }

        // latch: 맵은 1회 발행하고 늦게 뜬 구독자도 받아야 한다(TRANSIENT_LOCAL).
        rclcpp::QoS latched(1);
        latched.transient_local().reliable();
        map_pub_ = create_publisher<nav_msgs::msg::OccupancyGrid>("map", latched);
        grid.header.stamp = now();
        map_pub_->publish(grid);
        RCLCPP_INFO(get_logger(),
                    "/map 발행: %zux%zu 셀 @%.3f m (%.1f x %.1f m), 원점 (%.2f, %.2f), 점유 셀 %zu / 장애물 %zu점",
                    width, height, resolution, width * resolution, height * resolution, min_x, min_y, marked,
                    m.obstacles.size());

        if (publish_reflectors && !m.rssi_points.empty())
        {
            publishReflectors(m, latched);
        }
    }

  private:
    // 반사판은 주행 가능 여부와 무관한 **랜드마크**라 격자에 넣지 않는다. 배치를 눈으로 확인할
    //   수 있도록 마커로만 따로 낸다(내비게이션이 아니라 정합 진단용).
    void publishReflectors(const SmapMap &m, const rclcpp::QoS &latched)
    {
        marker_pub_ = create_publisher<visualization_msgs::msg::MarkerArray>("map_reflectors", latched);
        visualization_msgs::msg::MarkerArray arr;
        visualization_msgs::msg::Marker mk;
        mk.header.frame_id = frame_id_;
        mk.header.stamp = now();
        mk.ns = "reflectors";
        mk.id = 0;
        mk.type = visualization_msgs::msg::Marker::SPHERE_LIST;
        mk.action = visualization_msgs::msg::Marker::ADD;
        mk.pose.orientation.w = 1.0;
        mk.scale.x = mk.scale.y = mk.scale.z = 0.2;
        mk.color.r = 0.95f;
        mk.color.g = 0.66f;
        mk.color.b = 0.23f;
        mk.color.a = 1.0f;
        mk.points.reserve(m.rssi_points.size());
        for (const auto &p : m.rssi_points)
        {
            geometry_msgs::msg::Point pt;
            pt.x = p.first;
            pt.y = p.second;
            mk.points.push_back(pt);
        }
        arr.markers.push_back(mk);
        marker_pub_->publish(arr);
        RCLCPP_INFO(get_logger(), "/map_reflectors 발행: 반사판 %zu개", m.rssi_points.size());
    }

    std::string frame_id_;
    rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr map_pub_;
    rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr marker_pub_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SmapMapServer>());
    rclcpp::shutdown();
    return 0;
}
