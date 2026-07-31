// .smap 로더 검증.
//   인자 없음  → 픽스처 모드: 테스트가 직접 만든 최소 .smap 으로 파싱 결과를 값 단위로 대조 +
//                 실패 경로(파일 없음·JSON 깨짐·장애물 0) 확인. 외부 자산 불요 → ctest 상시 실행.
//   인자 1개  → 실맵 모드: 실제 Seer 맵을 로드하고 우도장 구축까지 확인(성능 로그 포함).
// ※ assert 는 Release(NDEBUG)에서 사라져 테스트가 항상 통과해 버린다 → 자체 CHECK 매크로 사용.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

#include "mcl2d_core/likelihood_grid.hpp"
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

bool nearEq(double a, double b, double tol = 1e-9)
{
    const double d = a - b;
    return (d < 0 ? -d : d) <= tol;
}

void writeFile(const std::string &path, const std::string &text)
{
    std::ofstream f(path, std::ios::binary);
    f << text;
}

// 실제 Seer .smap 의 축소판. 0인 좌표를 일부러 생략해 "생략=0" 규칙까지 덮는다.
const char *kFixtureJson = R"({
  "header": {
    "mapType": "2D-Map", "mapName": "fixture_map",
    "minPos": {"x": -1.5, "y": -2.5}, "maxPos": {"x": 3.25},
    "resolution": 0.05, "version": "1.0.6"
  },
  "normalPosList": [{"x": 1.0, "y": 2.0}, {"y": -3.5}, {"x": 4.25}, {}],
  "advancedPointList": [
    {"instanceName": "LM1", "className": "LocationMark", "pos": {"x": 5.0}, "dir": 1.5},
    {"instanceName": "AP2", "className": "ActionPoint", "pos": {"x": -1.0, "y": 2.5}}
  ],
  "rssiPosList": [{"x": 0.5, "y": 0.5}, {"x": -0.5, "y": 0.25}]
})";

void testFixtureParse()
{
    const std::string path = "test_smap_fixture.smap";
    writeFile(path, kFixtureJson);
    const SmapMap m = loadSmap(path);
    std::remove(path.c_str());

    CHECK(m.valid, "픽스처 맵 로드 실패");
    CHECK(m.map_name == "fixture_map", "mapName 불일치");
    CHECK(m.version == "1.0.6", "version 불일치");
    CHECK(nearEq(m.resolution, 0.05), "resolution 불일치");

    CHECK(nearEq(m.min_x, -1.5) && nearEq(m.min_y, -2.5), "minPos 불일치");
    // maxPos.y 는 JSON 에서 생략됨 → 0 이어야 한다(생략=0 규칙)
    CHECK(nearEq(m.max_x, 3.25) && nearEq(m.max_y, 0.0), "maxPos 생략좌표 0 처리 안 됨");

    CHECK(m.obstacles.size() == 4, "장애물 개수 불일치");
    if (m.obstacles.size() == 4)
    {
        CHECK(nearEq(m.obstacles[0].first, 1.0) && nearEq(m.obstacles[0].second, 2.0), "장애물[0] 좌표 불일치");
        CHECK(nearEq(m.obstacles[1].first, 0.0) && nearEq(m.obstacles[1].second, -3.5), "장애물[1] x 생략 처리 오류");
        CHECK(nearEq(m.obstacles[2].first, 4.25) && nearEq(m.obstacles[2].second, 0.0), "장애물[2] y 생략 처리 오류");
        CHECK(nearEq(m.obstacles[3].first, 0.0) && nearEq(m.obstacles[3].second, 0.0), "장애물[3] 빈 객체 처리 오류");
    }

    CHECK(m.named_points.size() == 2, "명명 위치 개수 불일치");
    if (m.named_points.size() == 2)
    {
        const NamedPoint &p0 = m.named_points[0];
        CHECK(p0.name == "LM1" && p0.cls == "LocationMark", "명명 위치[0] 이름/클래스 불일치");
        CHECK(nearEq(p0.x, 5.0) && nearEq(p0.y, 0.0), "명명 위치[0] 좌표 불일치");
        CHECK(nearEq(p0.dir, 1.5), "명명 위치[0] dir 불일치");
        const NamedPoint &p1 = m.named_points[1];
        CHECK(p1.name == "AP2" && nearEq(p1.x, -1.0) && nearEq(p1.y, 2.5), "명명 위치[1] 불일치");
        CHECK(nearEq(p1.dir, 0.0), "명명 위치[1] dir 생략 시 0 아님");
    }

    CHECK(m.rssi_points.size() == 2, "반사판 개수 불일치");
    if (m.rssi_points.size() == 2)
        CHECK(nearEq(m.rssi_points[1].first, -0.5) && nearEq(m.rssi_points[1].second, 0.25), "반사판[1] 좌표 불일치");

    std::printf("픽스처 파싱  : 장애물 %zu · 명명 %zu · 반사판 %zu\n", m.obstacles.size(), m.named_points.size(),
                m.rssi_points.size());
}

// 실패 경로 — 조용히 빈 맵으로 넘어가지 않고 valid=false 여야 한다.
void testInvalidInputs()
{
    CHECK(!loadSmap("/nonexistent/dir/no_such.smap").valid, "없는 파일인데 valid=true");

    const std::string trunc = "test_smap_truncated.smap";
    writeFile(trunc, R"({"header": {"mapName": "broken", "normalPosList": [{"x": 1.0)");
    CHECK(!loadSmap(trunc).valid, "잘린 JSON 인데 valid=true");
    std::remove(trunc.c_str());

    const std::string empty = "test_smap_noobstacle.smap";
    writeFile(empty, R"({"header": {"mapName": "empty", "resolution": 0.05}, "normalPosList": []})");
    CHECK(!loadSmap(empty).valid, "장애물 0 인데 valid=true");
    std::remove(empty.c_str());

    std::printf("실패 경로    : 파일없음·JSON깨짐·장애물0 모두 valid=false\n");
}

// 픽스처 점군으로 우도장을 만들어 코어 연동까지 확인(장애물 위치 PDF 는 높아야 한다).
void testGridFromFixture()
{
    const std::string path = "test_smap_gridfixture.smap";
    writeFile(path, kFixtureJson);
    const SmapMap m = loadSmap(path);
    std::remove(path.c_str());
    if (!m.valid)
        return; // 위 테스트에서 이미 FAIL 로 보고됨

    LikelihoodGrid grid;
    grid.build(m.obstacles, m.resolution, /*sigma=*/0.2, /*max_dist=*/0.5);
    CHECK(!grid.empty(), "픽스처 우도장 구축 실패");
    for (std::size_t i = 0; i < m.obstacles.size(); ++i)
        CHECK(grid.probAt(m.obstacles[i].first, m.obstacles[i].second) > 200, "장애물 위치 PDF 가 낮음");

    std::printf("우도장 연동  : 장애물 %zu 점 전부 PDF>200\n", m.obstacles.size());
}

int runRealMap(const char *path)
{
    auto t0 = std::chrono::steady_clock::now();
    const SmapMap m = loadSmap(path);
    const double load_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();

    if (!m.valid)
    {
        std::printf("[FAIL] .smap 로드 실패: %s\n", path);
        return 1;
    }

    std::printf("맵 이름   : %s (v%s)\n", m.map_name.c_str(), m.version.c_str());
    std::printf("해상도    : %.3f m/cell\n", m.resolution);
    std::printf("경계      : x[%.2f, %.2f] y[%.2f, %.2f]\n", m.min_x, m.max_x, m.min_y, m.max_y);
    std::printf("장애물점  : %zu\n", m.obstacles.size());
    std::printf("명명 위치 : %zu (첫: %s @(%.2f,%.2f))\n", m.named_points.size(),
                m.named_points.empty() ? "-" : m.named_points[0].name.c_str(),
                m.named_points.empty() ? 0 : m.named_points[0].x, m.named_points.empty() ? 0 : m.named_points[0].y);
    std::printf("반사판점  : %zu\n", m.rssi_points.size());
    std::printf("파싱 시간 : %.1f ms\n", load_ms);

    CHECK(m.obstacles.size() > 1000, "장애물 점 수 비정상");
    CHECK(m.resolution > 0.0 && m.resolution < 1.0, "해상도 비정상");

    auto g0 = std::chrono::steady_clock::now();
    LikelihoodGrid grid;
    grid.build(m.obstacles, m.resolution, /*sigma=*/0.2, /*max_dist=*/0.5);
    const double build_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - g0).count();
    std::printf("우도장 구축: %.2f s (resolution %.3f, %zu점)\n", build_s, m.resolution, m.obstacles.size());
    CHECK(!grid.empty(), "우도장 구축 실패");

    // 장애물 점 위치의 PDF 는 높아야(≈255) 좌표계·그리드 정합이 맞는 것
    int hi = 0;
    const std::size_t step = m.obstacles.size() / 200;
    for (int i = 0; i < 200; ++i)
    {
        const auto &o = m.obstacles[static_cast<std::size_t>(i) * step];
        if (grid.probAt(o.first, o.second) > 200)
            ++hi;
    }
    std::printf("장애물점 PDF>200 비율: %d/200\n", hi);
    CHECK(hi > 150, "장애물 위치 우도가 낮음 — 좌표/그리드 정합 오류");

    if (g_failures == 0)
        std::printf("[PASS] .smap 로더 + 우도장 구축 (실맵: %s)\n", m.map_name.c_str());
    return g_failures == 0 ? 0 : 1;
}

} // namespace

int main(int argc, char **argv)
{
    if (argc >= 2)
        return runRealMap(argv[1]);

    std::printf("=== .smap 로더 픽스처 테스트 (실맵 검사는 인자로 .smap 경로 전달) ===\n");
    testFixtureParse();
    testInvalidInputs();
    testGridFromFixture();

    if (g_failures != 0)
    {
        std::printf("[FAIL] 검사 %d건 실패\n", g_failures);
        return 1;
    }
    std::printf("[PASS] .smap 로더 픽스처 검증 통과\n");
    return 0;
}
