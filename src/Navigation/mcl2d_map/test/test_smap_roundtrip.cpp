// .smap 왕복(round-trip) 검증 — loadSmap ↔ saveSmap 이 서로의 역이어야 한다.
//   인자 없음 → 픽스처 모드: 테스트가 만든 .smap 으로 load→save→load 후 전 필드 대조 +
//                생략 규칙(0 좌표 생략, oneof 값은 0 이어도 기록)·실패 경로 확인.
//                외부 자산 불요 → ctest 상시 실행.
//   인자 N개 → 실맵 모드: 주어진 .smap 들을 load→save→load 대조하고, 원본과 바이트 동일한지도 센다.
//                (References/seer/slam_mapping/maps/*.smap — 없으면 skip 을 보고한다)
// ※ assert 는 Release(NDEBUG)에서 사라져 테스트가 항상 통과해 버린다 → 자체 CHECK 매크로 사용.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "mcl2d_map/smap.hpp"

using namespace mcl2d;

namespace
{

int g_failures = 0;

// NDEBUG 와 무관하게 살아 있는 검사 — 실패해도 계속 진행해 결함을 모아 보고한다.
#define CHECK(cond, msg)                                                                                               \
    do                                                                                                                 \
    {                                                                                                                  \
        if (!(cond))                                                                                                   \
        {                                                                                                              \
            std::printf("  [FAIL] %s (%s:%d) — %s\n", msg, __FILE__, __LINE__, #cond);                                 \
            ++g_failures;                                                                                              \
        }                                                                                                              \
    } while (0)

void writeFile(const std::string &path, const std::string &text)
{
    std::ofstream f(path, std::ios::binary);
    f << text;
}

bool readFile(const std::string &path, std::string &out)
{
    std::ifstream f(path, std::ios::binary);
    if (!f)
        return false;
    std::ostringstream ss;
    ss << f.rdbuf();
    out = ss.str();
    return true;
}

// ── 구조체 동등 비교 — 왕복은 비트 단위로 같아야 하므로 double 도 == 로 본다 ──

struct Diff
{
    int count = 0;
    std::string first; // 처음 발견한 차이의 위치 설명
    void note(const std::string &where)
    {
        if (count == 0)
            first = where;
        ++count;
    }
};

void cmpDouble(Diff &d, const char *what, double a, double b)
{
    if (!(a == b))
    {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "%s (%.17g != %.17g)", what, a, b);
        d.note(buf);
    }
}

void cmpStr(Diff &d, const char *what, const std::string &a, const std::string &b)
{
    if (a != b)
        d.note(std::string(what) + " (\"" + a + "\" != \"" + b + "\")");
}

void cmpPos(Diff &d, const char *what, const MapPos &a, const MapPos &b)
{
    cmpDouble(d, (std::string(what) + ".x").c_str(), a.x, b.x);
    cmpDouble(d, (std::string(what) + ".y").c_str(), a.y, b.y);
    cmpDouble(d, (std::string(what) + ".z").c_str(), a.z, b.z);
}

void cmpAttr(Diff &d, const char *what, const MapAttribute &a, const MapAttribute &b)
{
    cmpStr(d, (std::string(what) + ".description").c_str(), a.description, b.description);
    if (a.color_pen != b.color_pen)
        d.note(std::string(what) + ".colorPen");
    if (a.color_brush != b.color_brush)
        d.note(std::string(what) + ".colorBrush");
    if (a.color_font != b.color_font)
        d.note(std::string(what) + ".colorFont");
}

void cmpProps(Diff &d, const std::string &what, const std::vector<MapProperty> &a, const std::vector<MapProperty> &b)
{
    if (a.size() != b.size())
    {
        d.note(what + ".size");
        return;
    }
    for (std::size_t i = 0; i < a.size(); ++i)
    {
        const std::string w = what + "[" + std::to_string(i) + "]";
        cmpStr(d, (w + ".key").c_str(), a[i].key, b[i].key);
        cmpStr(d, (w + ".type").c_str(), a[i].type, b[i].type);
        cmpStr(d, (w + ".value").c_str(), a[i].value, b[i].value);
        cmpStr(d, (w + ".tag").c_str(), a[i].tag, b[i].tag);
        if (a[i].kind != b[i].kind)
            d.note(w + ".kind");
        if (a[i].bool_value != b[i].bool_value)
            d.note(w + ".boolValue");
        cmpDouble(d, (w + ".numValue").c_str(), a[i].num_value, b[i].num_value);
        cmpStr(d, (w + ".strValue").c_str(), a[i].str_value, b[i].str_value);
    }
}

void cmpNamedPoint(Diff &d, const std::string &what, const NamedPoint &a, const NamedPoint &b)
{
    cmpStr(d, (what + ".name").c_str(), a.name, b.name);
    cmpStr(d, (what + ".cls").c_str(), a.cls, b.cls);
    cmpDouble(d, (what + ".x").c_str(), a.x, b.x);
    cmpDouble(d, (what + ".y").c_str(), a.y, b.y);
    cmpDouble(d, (what + ".z").c_str(), a.z, b.z);
    cmpDouble(d, (what + ".dir").c_str(), a.dir, b.dir);
    if (a.ignore_dir != b.ignore_dir)
        d.note(what + ".ignoreDir");
    cmpProps(d, what + ".property", a.properties, b.properties);
    cmpAttr(d, (what + ".attribute").c_str(), a.attribute, b.attribute);
}

void cmpLine(Diff &d, const std::string &what, const MapLine &a, const MapLine &b)
{
    cmpPos(d, (what + ".startPos").c_str(), a.start_pos, b.start_pos);
    cmpPos(d, (what + ".endPos").c_str(), a.end_pos, b.end_pos);
}

// 두 맵의 전 필드 비교. 반환 Diff.count == 0 이면 완전 일치.
Diff compareMaps(const SmapMap &a, const SmapMap &b)
{
    Diff d;
    if (a.valid != b.valid)
        d.note("valid");
    cmpStr(d, "mapDirectory", a.map_directory, b.map_directory);
    cmpStr(d, "mapType", a.map_type, b.map_type);
    cmpStr(d, "mapName", a.map_name, b.map_name);
    cmpStr(d, "version", a.version, b.version);
    cmpDouble(d, "resolution", a.resolution, b.resolution);
    cmpDouble(d, "minPos.x", a.min_x, b.min_x);
    cmpDouble(d, "minPos.y", a.min_y, b.min_y);
    cmpDouble(d, "maxPos.x", a.max_x, b.max_x);
    cmpDouble(d, "maxPos.y", a.max_y, b.max_y);

    if (a.obstacles.size() != b.obstacles.size())
        d.note("normalPosList.size");
    else
        for (std::size_t i = 0; i < a.obstacles.size(); ++i)
        {
            const std::string w = "normalPosList[" + std::to_string(i) + "]";
            cmpDouble(d, (w + ".x").c_str(), a.obstacles[i].first, b.obstacles[i].first);
            cmpDouble(d, (w + ".y").c_str(), a.obstacles[i].second, b.obstacles[i].second);
        }

    if (a.rssi_points.size() != b.rssi_points.size())
        d.note("rssiPosList.size");
    else
        for (std::size_t i = 0; i < a.rssi_points.size(); ++i)
        {
            const std::string w = "rssiPosList[" + std::to_string(i) + "]";
            cmpDouble(d, (w + ".x").c_str(), a.rssi_points[i].first, b.rssi_points[i].first);
            cmpDouble(d, (w + ".y").c_str(), a.rssi_points[i].second, b.rssi_points[i].second);
        }

    if (a.normal_lines.size() != b.normal_lines.size())
        d.note("normalLineList.size");
    else
        for (std::size_t i = 0; i < a.normal_lines.size(); ++i)
            cmpLine(d, "normalLineList[" + std::to_string(i) + "]", a.normal_lines[i], b.normal_lines[i]);

    if (a.named_points.size() != b.named_points.size())
        d.note("advancedPointList.size");
    else
        for (std::size_t i = 0; i < a.named_points.size(); ++i)
            cmpNamedPoint(d, "advancedPointList[" + std::to_string(i) + "]", a.named_points[i], b.named_points[i]);

    if (a.advanced_lines.size() != b.advanced_lines.size())
        d.note("advancedLineList.size");
    else
        for (std::size_t i = 0; i < a.advanced_lines.size(); ++i)
        {
            const std::string w = "advancedLineList[" + std::to_string(i) + "]";
            cmpStr(d, (w + ".name").c_str(), a.advanced_lines[i].name, b.advanced_lines[i].name);
            cmpStr(d, (w + ".cls").c_str(), a.advanced_lines[i].cls, b.advanced_lines[i].cls);
            cmpLine(d, w + ".line", a.advanced_lines[i].line, b.advanced_lines[i].line);
            cmpProps(d, w + ".property", a.advanced_lines[i].properties, b.advanced_lines[i].properties);
            cmpAttr(d, (w + ".attribute").c_str(), a.advanced_lines[i].attribute, b.advanced_lines[i].attribute);
        }

    if (a.advanced_curves.size() != b.advanced_curves.size())
        d.note("advancedCurveList.size");
    else
        for (std::size_t i = 0; i < a.advanced_curves.size(); ++i)
        {
            const AdvancedCurve &x = a.advanced_curves[i];
            const AdvancedCurve &y = b.advanced_curves[i];
            const std::string w = "advancedCurveList[" + std::to_string(i) + "]";
            cmpStr(d, (w + ".name").c_str(), x.name, y.name);
            cmpStr(d, (w + ".cls").c_str(), x.cls, y.cls);
            cmpNamedPoint(d, w + ".startPos", x.start_pos, y.start_pos);
            cmpNamedPoint(d, w + ".endPos", x.end_pos, y.end_pos);
            cmpPos(d, (w + ".controlPos1").c_str(), x.control_pos1, y.control_pos1);
            cmpPos(d, (w + ".controlPos2").c_str(), x.control_pos2, y.control_pos2);
            cmpPos(d, (w + ".controlPos3").c_str(), x.control_pos3, y.control_pos3);
            cmpPos(d, (w + ".controlPos4").c_str(), x.control_pos4, y.control_pos4);
            cmpProps(d, w + ".property", x.properties, y.properties);
            cmpAttr(d, (w + ".attribute").c_str(), x.attribute, y.attribute);
        }

    if (a.advanced_areas.size() != b.advanced_areas.size())
        d.note("advancedAreaList.size");
    else
        for (std::size_t i = 0; i < a.advanced_areas.size(); ++i)
        {
            const AdvancedArea &x = a.advanced_areas[i];
            const AdvancedArea &y = b.advanced_areas[i];
            const std::string w = "advancedAreaList[" + std::to_string(i) + "]";
            cmpStr(d, (w + ".name").c_str(), x.name, y.name);
            cmpStr(d, (w + ".cls").c_str(), x.cls, y.cls);
            cmpDouble(d, (w + ".dir").c_str(), x.dir, y.dir);
            if (x.pos_group.size() != y.pos_group.size())
                d.note(w + ".posGroup.size");
            else
                for (std::size_t k = 0; k < x.pos_group.size(); ++k)
                    cmpPos(d, (w + ".posGroup[" + std::to_string(k) + "]").c_str(), x.pos_group[k], y.pos_group[k]);
            cmpProps(d, w + ".property", x.properties, y.properties);
            cmpAttr(d, (w + ".attribute").c_str(), x.attribute, y.attribute);
        }

    cmpProps(d, "userData", a.user_data, b.user_data);

    if (a.unsupported_keys != b.unsupported_keys)
        d.note("unsupportedKeys");
    return d;
}

// ── 픽스처 ──
// 실제 Seer .smap 의 축소판. 4종 신규 요소를 모두 담고, 0 인 좌표를 일부러 생략해
// "생략=0" 규칙과 oneof 값 필드의 "0 이어도 기록" 규칙을 함께 덮는다.
const char *kFixtureJson = R"({
  "header": {
    "mapType": "2D-Map", "mapName": "roundtrip_fixture",
    "minPos": {"x": -1.5, "y": -2.5}, "maxPos": {"x": 3.25},
    "resolution": 0.02, "version": "1.0.6"
  },
  "normalPosList": [{"x": 1.0, "y": 2.0}, {"y": -3.5}, {"x": 4.25}, {}],
  "normalLineList": [
    {"startPos": {"x": -4.163, "y": -1.993}, "endPos": {"x": -3.978, "y": -2.026}},
    {"startPos": {"y": 1.5}, "endPos": {"x": 2.0}}
  ],
  "advancedPointList": [
    {"className": "LocationMark", "instanceName": "LM1", "pos": {"x": 5.0}, "dir": 1.5,
     "property": [{"key": "spin", "type": "bool", "value": "ZmFsc2U=", "boolValue": false}]},
    {"className": "TransferLocation", "instanceName": "TL1", "pos": {"x": -1.0, "y": 2.5},
     "ignoreDir": true,
     "property": [{"key": "prepoint", "type": "string", "value": "VEw1", "stringValue": "TL5"}]}
  ],
  "advancedLineList": [
    {"className": "ForbiddenLine", "instanceName": "3",
     "line": {"startPos": {"x": 13.726, "y": -3.498}, "endPos": {"x": 13.712, "y": -5.353}}}
  ],
  "advancedCurveList": [
    {"className": "StraightPath", "instanceName": "LM1-TL1",
     "startPos": {"instanceName": "LM1", "pos": {"x": 4.694, "y": 3.041}},
     "endPos": {"instanceName": "TL1", "pos": {"x": 7.204, "y": 3.041}},
     "property": [{"key": "direction", "type": "int", "value": "MA==", "int32Value": 0},
                  {"key": "movestyle", "type": "int", "value": "MA==", "int32Value": 0},
                  {"key": "maxspeed", "type": "double", "value": "MC4z", "doubleValue": 0.3}]},
    {"className": "BezierPath", "instanceName": "TL1-LM1",
     "startPos": {"instanceName": "TL1", "pos": {"x": 6.455, "y": 2.615}},
     "endPos": {"instanceName": "LM1", "pos": {"x": 2.974, "y": 0.558, "z": 10}},
     "controlPos1": {"x": 5.295, "y": 1.929},
     "controlPos2": {"x": 4.134, "y": 1.244, "z": 60},
     "controlPos3": {"y": 0.5},
     "controlPos4": {"x": 0.8272860654453121},
     "property": [{"key": "direction", "type": "int", "value": "MQ==", "int32Value": 1}]}
  ],
  "advancedAreaList": [
    {"className": "AdvancedArea", "instanceName": "1",
     "posGroup": [{"x": -1.82, "y": 14.583}, {"x": -1.82, "y": 24.662},
                  {"x": -5.21, "y": 24.662}, {"x": -5.21, "y": 14.583}],
     "dir": -1.5707963267948966,
     "property": [{"key": "obsStopDist", "type": "double", "value": "MC4x", "doubleValue": 0.1},
                  {"key": "obsDecDist", "type": "double", "value": "MC4wMTU=", "doubleValue": 0.015},
                  {"key": "obsExpansion", "type": "double", "value": "LTAuMQ==", "doubleValue": -0.1},
                  {"key": "TextFontSize", "type": "int32", "value": "OQ==", "int32Value": 9}],
     "attribute": {"colorPen": 4294901845, "colorBrush": 352299605}}
  ],
  "rssiPosList": [{"x": 0.5, "y": 0.5}, {"x": -0.5, "y": 0.25}]
})";

// 신규 4종 요소가 실제로 채워졌는지 — 왕복만 보면 "둘 다 비어 있음"도 통과해 버린다.
void testNewElementsParsed(const SmapMap &m)
{
    CHECK(m.map_type == "2D-Map", "mapType 파싱 안 됨");

    CHECK(m.normal_lines.size() == 2, "normalLineList 개수 불일치");
    if (m.normal_lines.size() == 2)
    {
        CHECK(m.normal_lines[0].start_pos.x == -4.163 && m.normal_lines[0].end_pos.y == -2.026,
              "normalLineList[0] 좌표 불일치");
        CHECK(m.normal_lines[1].start_pos.x == 0.0 && m.normal_lines[1].start_pos.y == 1.5,
              "normalLineList[1] 생략좌표 0 처리 오류");
    }

    CHECK(m.advanced_lines.size() == 1, "advancedLineList 개수 불일치");
    if (m.advanced_lines.size() == 1)
    {
        CHECK(m.advanced_lines[0].cls == "ForbiddenLine", "금지선 className 불일치");
        CHECK(m.advanced_lines[0].name == "3", "금지선 instanceName 불일치");
        CHECK(m.advanced_lines[0].line.start_pos.x == 13.726 && m.advanced_lines[0].line.end_pos.y == -5.353,
              "금지선 좌표 불일치");
    }

    CHECK(m.advanced_curves.size() == 2, "advancedCurveList 개수 불일치");
    if (m.advanced_curves.size() == 2)
    {
        const AdvancedCurve &c0 = m.advanced_curves[0];
        CHECK(c0.cls == "StraightPath" && c0.name == "LM1-TL1", "경로[0] 클래스/이름 불일치");
        CHECK(c0.start_pos.name == "LM1" && c0.start_pos.x == 4.694, "경로[0] startPos 불일치");
        CHECK(c0.end_pos.name == "TL1" && c0.end_pos.x == 7.204, "경로[0] endPos 불일치");
        CHECK(c0.properties.size() == 3, "경로[0] property 개수 불일치");
        if (c0.properties.size() == 3)
        {
            CHECK(c0.properties[0].key == "direction" && c0.properties[0].kind == MapProperty::ValueKind::Int32 &&
                      c0.properties[0].num_value == 0.0,
                  "direction=0 (oneof) 파싱 오류");
            CHECK(c0.properties[2].key == "maxspeed" && c0.properties[2].num_value == 0.3, "maxspeed 파싱 오류");
        }
        const AdvancedCurve &c1 = m.advanced_curves[1];
        CHECK(c1.cls == "BezierPath", "경로[1] className 불일치");
        CHECK(c1.control_pos1.x == 5.295 && c1.control_pos2.z == 60.0, "제어점 파싱 오류");
        CHECK(c1.control_pos3.x == 0.0 && c1.control_pos3.y == 0.5, "제어점 생략좌표 0 처리 오류");
        CHECK(c1.end_pos.z == 10.0, "endPos.z 파싱 오류");
    }

    CHECK(m.advanced_areas.size() == 1, "advancedAreaList 개수 불일치");
    if (m.advanced_areas.size() == 1)
    {
        const AdvancedArea &a = m.advanced_areas[0];
        CHECK(a.cls == "AdvancedArea" && a.pos_group.size() == 4, "구역 클래스/꼭짓점 개수 불일치");
        CHECK(a.dir == -1.5707963267948966, "구역 dir 불일치");
        CHECK(a.properties.size() == 4, "구역 property 개수 불일치");
        if (a.properties.size() == 4)
        {
            CHECK(a.properties[0].key == "obsStopDist" && a.properties[0].num_value == 0.1, "obsStopDist 불일치");
            CHECK(a.properties[1].key == "obsDecDist" && a.properties[1].num_value == 0.015, "obsDecDist 불일치");
            CHECK(a.properties[2].key == "obsExpansion" && a.properties[2].num_value == -0.1, "obsExpansion 불일치");
        }
        CHECK(a.attribute.color_pen == 4294901845u && a.attribute.color_brush == 352299605u, "구역 attribute 불일치");
    }

    CHECK(m.named_points.size() == 2, "advancedPointList 개수 불일치");
    if (m.named_points.size() == 2)
    {
        CHECK(m.named_points[0].properties.size() == 1 &&
                  m.named_points[0].properties[0].kind == MapProperty::ValueKind::Bool &&
                  m.named_points[0].properties[0].bool_value == false,
              "명명 위치 spin=false (oneof) 파싱 오류");
        CHECK(m.named_points[1].ignore_dir, "ignoreDir 파싱 오류");
        CHECK(m.named_points[1].properties.size() == 1 && m.named_points[1].properties[0].str_value == "TL5",
              "prepoint stringValue 파싱 오류");
    }

    CHECK(m.unsupported_keys.empty(), "픽스처에 미지원 키가 없어야 한다");
}

// 생략 규칙이 쓰기에도 적용되는지 — 원본이 안 쓰는 필드를 우리가 쓰면 Seer 와 호환이 깨진다.
void testOmissionRules(const std::string &written)
{
    CHECK(written.find("\"x\":0,") == std::string::npos && written.find("\"x\":0}") == std::string::npos,
          "0 인 x 좌표를 기록했다(생략 규칙 위반)");
    CHECK(written.find("\"y\":0,") == std::string::npos && written.find("\"y\":0}") == std::string::npos,
          "0 인 y 좌표를 기록했다(생략 규칙 위반)");
    CHECK(written.find("\"z\":0") == std::string::npos, "0 인 z 좌표를 기록했다(생략 규칙 위반)");
    CHECK(written.find("\"dir\":0") == std::string::npos, "0 인 dir 을 기록했다(생략 규칙 위반)");
    // 반대로 oneof 값 필드는 0/false 라도 반드시 남아 있어야 한다.
    CHECK(written.find("\"int32Value\":0") != std::string::npos, "oneof int32Value:0 이 생략됐다");
    CHECK(written.find("\"boolValue\":false") != std::string::npos, "oneof boolValue:false 가 생략됐다");
    CHECK(written.find("\"ignoreDir\":true") != std::string::npos, "ignoreDir:true 가 누락됐다");
    CHECK(written.find(' ') == std::string::npos && written.find('\n') == std::string::npos,
          "출력에 공백/개행이 있다(원본은 공백 없는 한 줄 JSON)");
}

void testFixtureRoundTrip()
{
    const std::string src = "test_smap_rt_src.smap";
    const std::string dst = "test_smap_rt_dst.smap";
    writeFile(src, kFixtureJson);

    const SmapMap m1 = loadSmap(src);
    std::remove(src.c_str());
    CHECK(m1.valid, "픽스처 로드 실패");
    if (!m1.valid)
        return;

    testNewElementsParsed(m1);

    CHECK(saveSmap(m1, dst), "픽스처 저장 실패");
    std::string written;
    CHECK(readFile(dst, written), "저장한 파일을 다시 읽지 못함");
    testOmissionRules(written);

    const SmapMap m2 = loadSmap(dst);
    std::remove(dst.c_str());
    CHECK(m2.valid, "재적재 실패");

    const Diff d = compareMaps(m1, m2);
    CHECK(d.count == 0, "왕복 후 필드 불일치");
    if (d.count != 0)
        std::printf("  차이 %d건, 첫 항목: %s\n", d.count, d.first.c_str());

    std::printf("픽스처 왕복 : 요소 %zu점/%zu선/%zu명명/%zu금지선/%zu경로/%zu구역/%zu반사판, 출력 %zu바이트\n",
                m1.obstacles.size(), m1.normal_lines.size(), m1.named_points.size(), m1.advanced_lines.size(),
                m1.advanced_curves.size(), m1.advanced_areas.size(), m1.rssi_points.size(), written.size());
}

// 미지원 최상위 키가 있으면 손실 쓰기임을 호출자가 알 수 있어야 한다.
void testUnsupportedKeysReported()
{
    const std::string path = "test_smap_rt_unsupported.smap";
    writeFile(path, R"({"header":{"mapName":"u"},"normalPosList":[{"x":1,"y":1}],)"
                    R"("tagPosList":[{"tagValue":7}],"reflectorPosList":[{"x":1}]})");
    const SmapMap m = loadSmap(path);
    std::remove(path.c_str());
    CHECK(m.valid, "미지원 키 맵 로드 실패");
    CHECK(m.unsupported_keys.size() == 2, "미지원 키 개수 불일치");
    if (m.unsupported_keys.size() == 2)
        CHECK(m.unsupported_keys[0] == "tagPosList" && m.unsupported_keys[1] == "reflectorPosList",
              "미지원 키 이름 불일치");
    std::printf("미지원 키   : %zu건 보고 (tagPosList·reflectorPosList)\n", m.unsupported_keys.size());
}

// 쓰기 실패 경로 — 조용히 성공하면 안 된다.
void testSaveFailures()
{
    SmapMap m;
    m.map_name = "bad";
    m.obstacles.push_back({1.0, 1.0});
    CHECK(!saveSmap(m, "/nonexistent/dir/out.smap"), "없는 디렉터리인데 저장 성공 보고");

    SmapMap nan_map = m;
    nan_map.obstacles.push_back({0.0, std::strtod("nan", nullptr)});
    const std::string path = "test_smap_rt_nan.smap";
    std::remove(path.c_str());
    CHECK(!saveSmap(nan_map, path), "NaN 좌표인데 저장 성공 보고");
    std::ifstream probe(path, std::ios::binary);
    CHECK(!probe.good(), "NaN 거부인데 파일이 만들어졌다");
    probe.close();
    std::remove(path.c_str());

    std::printf("쓰기 실패   : 경로없음·NaN 모두 false 반환, 파일 미생성\n");
}

// 정밀도 — 17자리가 필요한 값도 왕복해야 한다(왕복 표기를 15자리로 굳히면 여기서 깨진다).
void testPrecision()
{
    SmapMap m;
    m.map_name = "precision";
    m.resolution = 0.02;
    const double kHard[] = {0.8272860654453121, -1.5707963267948966, 1.0 / 3.0, 1e-12, 123456789.123456789};
    for (double v : kHard)
        m.obstacles.push_back({v, -v});
    m.valid = true; // 손으로 만든 맵이라 직접 세운다(loadSmap 은 장애물이 있으면 true 로 돌려준다)

    const std::string path = "test_smap_rt_precision.smap";
    CHECK(saveSmap(m, path), "정밀도 픽스처 저장 실패");
    const SmapMap back = loadSmap(path);
    std::remove(path.c_str());
    const Diff d = compareMaps(m, back);
    CHECK(d.count == 0, "정밀도 왕복 불일치");
    if (d.count != 0)
        std::printf("  차이 %d건, 첫 항목: %s\n", d.count, d.first.c_str());
    std::printf("정밀도      : 난이도 높은 %zu개 double 왕복 일치\n", sizeof(kHard) / sizeof(kHard[0]));
}

// 실맵 1개 — load→save→load 대조 + 원본과의 바이트 동일 여부(참고 지표).
//   반환: 0 = 통과, 1 = 실패
int runRealMap(const char *path, int &byte_identical)
{
    const SmapMap m1 = loadSmap(path);
    if (!m1.valid)
    {
        std::printf("  [FAIL] 로드 실패: %s\n", path);
        ++g_failures;
        return 1;
    }
    const std::string out = std::string("test_smap_rt_out_") + std::to_string(m1.obstacles.size()) + ".smap";
    if (!saveSmap(m1, out))
    {
        std::printf("  [FAIL] 저장 실패: %s\n", path);
        ++g_failures;
        return 1;
    }
    const SmapMap m2 = loadSmap(out);
    std::string original, written;
    readFile(path, original);
    readFile(out, written);
    std::remove(out.c_str());

    const Diff d = compareMaps(m1, m2);
    const bool same_bytes = (original == written);
    if (same_bytes)
        ++byte_identical;

    std::printf("  %-46s 점 %6zu 경로 %4zu 구역 %2zu 금지선 %2zu | 왕복 %s | 바이트 %s%s\n", m1.map_name.c_str(),
                m1.obstacles.size(), m1.advanced_curves.size(), m1.advanced_areas.size(), m1.advanced_lines.size(),
                d.count == 0 ? "일치" : "불일치", same_bytes ? "동일" : "상이",
                m1.unsupported_keys.empty() ? "" : " | 미지원키 있음");
    if (d.count != 0)
    {
        std::printf("    [FAIL] 차이 %d건, 첫 항목: %s\n", d.count, d.first.c_str());
        ++g_failures;
        return 1;
    }
    return 0;
}

} // namespace

int main(int argc, char **argv)
{
    std::printf("=== .smap 왕복(load→save→load) 검증 ===\n");
    testFixtureRoundTrip();
    testUnsupportedKeysReported();
    testSaveFailures();
    testPrecision();

    if (argc >= 2)
    {
        std::printf("--- 실맵 %d개 ---\n", argc - 1);
        int ok = 0, byte_identical = 0;
        for (int i = 1; i < argc; ++i)
            if (runRealMap(argv[i], byte_identical) == 0)
                ++ok;
        std::printf("실맵 왕복   : %d/%d 통과 (원본과 바이트 동일: %d)\n", ok, argc - 1, byte_identical);
    }
    else
    {
        std::printf("실맵 왕복   : SKIP — 실맵 경로 인자가 없다 (References/seer/slam_mapping/maps/*.smap 이 있으면"
                    " CMake 가 test_smap_roundtrip_realmaps 로 등록한다)\n");
    }

    if (g_failures != 0)
    {
        std::printf("[FAIL] 검사 %d건 실패\n", g_failures);
        return 1;
    }
    std::printf("[PASS] .smap 왕복 검증 통과\n");
    return 0;
}
