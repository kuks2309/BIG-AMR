// Seer .smap 맵 로더/세이버 — 실제 Seer 맵(JSON)을 우리 위치추정 코어로 로드하고 다시 쓴다.
// .smap 은 `rbk.protocol.Message_Map` 의 protobuf-JSON 직렬화이며 proto 의 snake_case 와
// JSON 의 lowerCamelCase 가 1:1 대응한다. 포맷 정본:
//   References/seer/slam_mapping/proto/message_map.proto (Message_Map = 276-295줄)
// 실측 구조: header{mapType,mapName,minPos,maxPos,resolution,version} +
//   normalPosList[{x,y}](장애물 점군) + normalLineList + advancedPointList(명명 위치) +
//   advancedLineList(금지선) + advancedCurveList(경로 topology) + advancedAreaList(안전 구역) +
//   rssiPosList(반사판).
//
// ※ protobuf-JSON 의 생략 규칙 — 읽기·쓰기 양쪽이 지켜야 원본과 왕복(round-trip) 일치한다:
//    1) 기본값(0 / false / 빈 문자열 / 빈 배열)인 **일반 필드는 JSON 에서 생략**된다.
//       예: 좌표 {"y":-3.5} 는 x=0 을 뜻한다.
//    2) 예외로 **oneof 멤버는 값이 0/false 라도 항상 기록**된다(실측 맵에 `"int32Value":0` 다수).
//       → MapProperty 의 타입별 값 필드가 여기 해당한다.
//
// ※ 의존성 0(자체 최소 JSON 파서·직렬화기). 외부 라이브러리를 추가하지 말 것.
#ifndef MCL2D_MAP_SMAP_HPP
#define MCL2D_MAP_SMAP_HPP

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace mcl2d
{

// Message_MapPos (proto 106-110줄). 단위 m. 생략된 성분은 0.
struct MapPos
{
    double x = 0.0;
    double y = 0.0;
    double z = 0.0; // 2D 맵에선 보통 미사용. NURBS 곡선은 이 자리에 제어 가중치를 싣는다(실측).
};

// Message_MapLine (proto 143-146줄). normalLineList 원소이자 AdvancedLine 의 본체.
struct MapLine
{
    MapPos start_pos;
    MapPos end_pos;
};

// Message_MapAttribute (proto 157-162줄) — 편집기 표시용 색/설명. 색은 ARGB 32bit 정수.
struct MapAttribute
{
    std::string description;
    std::uint32_t color_pen = 0;
    std::uint32_t color_brush = 0;
    std::uint32_t color_font = 0;
};

// Message_MapProperty (proto 88-104줄) — 요소별 확장 속성.
//   실측 key 예: 경로의 direction/movestyle/maxspeed(m/s)/maxacc(m/s^2)/holdDir(deg),
//                구역의 obsStopDist/obsDecDist/obsExpansion(m), 위치의 spin/prepoint.
//   value(= proto bytes value=3)는 값의 ASCII 표기를 base64 로 담은 하위호환 필드다.
//   실수는 원본이 6자리 유효숫자로 줄여 넣기도 하므로(실측) 해석·재인코딩하지 않고 원문을 보존한다.
struct MapProperty
{
    // proto 의 oneof oneof_value 중 실제로 설정된 갈래. None = 설정 없음(JSON 에 값 필드 없음).
    enum class ValueKind
    {
        None,
        Bool,   // boolValue
        Int32,  // int32Value
        UInt32, // uint32Value
        Int64,  // int64Value  (proto3 JSON 은 64bit 정수를 문자열로 직렬화)
        UInt64, // uint64Value (동상)
        Float,  // floatValue
        Double, // doubleValue
        String, // stringValue
        Bytes   // bytesValue  (base64 문자열)
    };

    std::string key;   // 속성 이름
    std::string type;  // Seer 표기 타입 문자열 (실측 "int"|"int32"|"double"|"bool"|"string")
    std::string value; // bytes value=3 의 base64 원문 (해석하지 않고 보존)
    std::string tag;   // proto tag=13 (로봇 그룹 한정자). 실측 맵 15개엔 없음.
    ValueKind kind = ValueKind::None;
    bool bool_value = false; // kind==Bool
    double num_value = 0.0;  // kind==Int32|UInt32|Float|Double 공용
    std::string str_value;   // kind==String|Bytes|Int64|UInt64 (64bit 는 JSON 문자열이다)
};

// Message_AdvancedPoint (proto 164-173줄).
//   advancedPointList 의 명명 위치(LocationMark/TransferLocation/LandMark)이자
//   AdvancedCurve 의 시작·끝점 표현이기도 하다.
struct NamedPoint
{
    std::string name; // instanceName
    std::string cls;  // className
    double x = 0.0;   // pos.x (m)
    double y = 0.0;   // pos.y (m)
    double z = 0.0;   // pos.z (m)
    double dir = 0.0; // 방향 (rad)
    bool ignore_dir = false;
    std::vector<MapProperty> properties; // property[] (실측 key: spin, prepoint)
    MapAttribute attribute;
};

// Message_AdvancedLine (proto 175-182줄) — 가상 금지선(실측 className:"ForbiddenLine").
struct AdvancedLine
{
    std::string name; // instanceName
    std::string cls;  // className
    MapLine line;
    std::vector<MapProperty> properties;
    MapAttribute attribute;
};

// Message_AdvancedCurve (proto 184-197줄) — 노드 사이를 잇는 경로(topology).
//   실측 className: "StraightPath"(직선) / "BezierPath"(3차 베지어) / "NURBS6".
//   control_pos1..4 는 곡선 제어점이며 직선 경로에선 전 성분 0(JSON 에 부재)이다.
struct AdvancedCurve
{
    std::string name; // instanceName (실측 "LM1005-LM1006" 형태)
    std::string cls;  // className
    NamedPoint start_pos;
    NamedPoint end_pos;
    MapPos control_pos1;
    MapPos control_pos2;
    MapPos control_pos3;
    MapPos control_pos4;
    std::vector<MapProperty> properties; // direction/movestyle/maxspeed 등
    MapAttribute attribute;
};

// Message_AdvancedArea (proto 199-208줄) — 고급 구역. 안전 파라미터를 property 로 싣는다.
struct AdvancedArea
{
    std::string name;                    // instanceName
    std::string cls;                     // className (실측 "AdvancedArea")
    std::vector<MapPos> pos_group;       // 보통 4점(사각 구역)
    double dir = 0.0;                    // 구역 방향 (rad)
    std::vector<MapProperty> properties; // obsStopDist/obsDecDist/obsExpansion (m)
    MapAttribute attribute;
};

struct SmapMap
{
    std::string map_directory;                         // Message_Map.map_directory (field 1)
    std::string map_type;                              // header.mapType (실측 "2D-Map")
    std::string map_name;                              // header.mapName
    std::string version;                               // header.version
    double resolution = 0.05;                          // header.resolution (m/cell)
    double min_x = 0, min_y = 0, max_x = 0, max_y = 0; // header.minPos/maxPos (m)
    std::vector<std::pair<double, double>> obstacles;   // normalPosList (m) — z 성분은 보존하지 않는다
    std::vector<MapLine> normal_lines;                  // normalLineList
    std::vector<NamedPoint> named_points;               // advancedPointList
    std::vector<AdvancedLine> advanced_lines;           // advancedLineList
    std::vector<AdvancedCurve> advanced_curves;         // advancedCurveList
    std::vector<AdvancedArea> advanced_areas;           // advancedAreaList
    std::vector<std::pair<double, double>> rssi_points; // rssiPosList (반사판, m)
    std::vector<MapProperty> user_data;                 // userData (field 100)
    // 이 로더가 다루지 않은 최상위 키 이름(등장 순, 중복 제거). 비어 있지 않으면 saveSmap 은
    // 그만큼 손실이 있는 쓰기다 — 호출자가 판단할 수 있도록 노출한다.
    //   미지원: normalPos3dList(5) · patrolRouteList(10) · reflectorPosList(12) · tagPosList(13) ·
    //           primitiveList(14) · externalDeviceList(15) · binLocationsList(16)
    //           (회수된 실측 맵 15개에는 전부 부재)
    std::vector<std::string> unsupported_keys;
    bool valid = false;
};

// .smap 파일 로드.
//   path : 읽을 .smap 경로
//   반환 : 파싱 결과. 파일 없음·JSON 파손·장애물 0 이면 valid=false.
SmapMap loadSmap(const std::string &path);

// .smap 파일 저장 (Seer 와 동일한 공백 없는 protobuf-JSON, 기본값 필드 생략).
//   m    : 쓸 맵. m.valid 는 보지 않는다(부분 맵도 쓸 수 있다).
//   path : 쓸 경로. 기존 파일은 덮어쓴다.
//   반환 : true = 성공. false = 좌표·속성에 NaN·무한대가 있어 JSON 으로 표현할 수 없거나,
//          파일 열기/쓰기에 실패한 경우.
//   ※ m.unsupported_keys 가 비어 있지 않으면 그 요소들은 기록되지 않는다(손실 쓰기).
bool saveSmap(const SmapMap &m, const std::string &path);

} // namespace mcl2d

#endif // MCL2D_MAP_SMAP_HPP
