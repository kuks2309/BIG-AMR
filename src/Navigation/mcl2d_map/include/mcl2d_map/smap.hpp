// Seer .smap 맵 로더 — 실제 Seer 맵(JSON)을 우리 위치추정 코어로 로드.
// .smap 구조(실측): header{mapName,minPos,maxPos,resolution,version} +
//   normalPosList[{x,y}] = 장애물 점군 + advancedPointList[명명 위치] + rssiPosList[반사판].
// ※ 0인 좌표는 JSON에서 생략됨 → 기본값 0 처리. 의존성 0(자체 최소 JSON 파서).
#ifndef MCL2D_MAP_SMAP_HPP
#define MCL2D_MAP_SMAP_HPP

#include <string>
#include <utility>
#include <vector>

namespace mcl2d
{

// advancedPointList 명명 위치 (내비 목표점, LocationMark 등)
struct NamedPoint
{
    std::string name; // instanceName
    std::string cls;  // className
    double x = 0.0;
    double y = 0.0;
    double dir = 0.0; // 방향 (rad)
};

struct SmapMap
{
    std::string map_name;
    std::string version;
    double resolution = 0.05; // header.resolution (m/cell)
    double min_x = 0, min_y = 0, max_x = 0, max_y = 0;
    std::vector<std::pair<double, double>> obstacles;   // normalPosList (m)
    std::vector<std::pair<double, double>> rssi_points; // rssiPosList (반사판, m)
    std::vector<NamedPoint> named_points;               // advancedPointList
    bool valid = false;
};

// .smap 파일 로드. 실패 시 valid=false.
SmapMap loadSmap(const std::string &path);

} // namespace mcl2d

#endif // MCL2D_MAP_SMAP_HPP
