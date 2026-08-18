// SLAM 매핑 행동 검증 — 합성 궤적(사각 방 한 바퀴 + 루프 복귀)에서 Karto + G2OSolver 파이프라인이
//   (1) 이동 게이트로 스캔을 선별하고
//   (2) **루프클로저를 실제로 성립시켜 g2o 최적화를 호출**하고
//   (3) 오도 드리프트를 교정해 일관된 맵을 산출하는지 확인한다.
//
// ※ SLAM 매핑은 "Open Karto + g2o 채용" 이라 원본 비트 대조 대상이 아니다 → 행동(behavioral) 검증.
//   원본 `.smap` 대조는 회수한 실 로그(References/seer/slam_mapping/rawmaps/*.rawmap)로 별도 수행한다.
//
// 검증 매크로는 NDEBUG 무관 `CHECK` 다 — `assert` 는 Release 에서 사라진다(check.hpp 주석 참조).
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <limits>
#include <vector>

#include "check.hpp"
#include "slam_karto_core/seer_slam_mapper.hpp"

using namespace slam_karto_core;

namespace
{
// 방 크기는 **Seer 튜닝값에 맞춰** 정해야 한다. `LoopSearchMaximumDistance=20 m`·
// `LinkScanMaximumDistance=10 m`·`LoopMatchMinimumChainSize=10` 기준에서 작은 방(10x8 m)은
// 전 구간이 "이미 근접 연결(near linked)" 로 분류돼 루프 후보 체인이 만들어지지 않는다 —
// 실측: 10x8 m 에서 노드 77개·간선 80개가 생겨도 `TryCloseLoop` 성립 0회.
// Seer 가 이 값을 쓴 대상은 공장 바닥이므로, 시험 환경도 그 규모여야 루프클로저를 볼 수 있다.
constexpr double kRoomWidth = 40.0;  ///< m
constexpr double kRoomHeight = 30.0; ///< m
constexpr double kMaxRange = 50.0;   ///< m — 방 대각(50 m)을 덮어야 벽이 보인다
constexpr int kBeamCount = 360;
constexpr double kBeamStepRad = M_PI / 180.0;
constexpr double kDriftPerStepRad = 0.0004; ///< 스텝마다 누적되는 방위 드리프트
constexpr double kReflectorRssi = 200.0;    ///< 반사판 빔 (원본 임계 150.0 초과)
constexpr double kBackgroundRssi = 50.0;    ///< 일반 빔 — 원본 `.rawmap` 실측 기저값
constexpr int kStationaryFrames = 30;       ///< 정지 구간 프레임 수(이동 게이트 검증용)

/// 사각 방 [0,W]x[0,H] 벽까지 레이캐스트해 빔 거리를 만든다 (라이다 로컬 = 로봇 헤딩 기준).
MapLogRecord makeScan(double rx, double ry, double rth)
{
    MapLogRecord r;
    r.odo_x = rx;
    r.odo_y = ry;
    r.odo_w = rth;
    for (int i = 0; i < kBeamCount; ++i)
    {
        const double la = -M_PI + i * kBeamStepRad; // 라이다 로컬각
        const double a = rth + la;                  // 월드각
        const double ca = std::cos(a);
        const double sa = std::sin(a);
        double best = kMaxRange;
        if (ca > 1e-9)
        {
            best = std::min(best, (kRoomWidth - rx) / ca);
        }
        if (ca < -1e-9)
        {
            best = std::min(best, (0.0 - rx) / ca);
        }
        if (sa > 1e-9)
        {
            best = std::min(best, (kRoomHeight - ry) / sa);
        }
        if (sa < -1e-9)
        {
            best = std::min(best, (0.0 - ry) / sa);
        }
        r.beam_dist.push_back(best);
        r.beam_angle.push_back(la);
        // 실측 규모에 맞춘다 — 회수한 원본 `.rawmap` 의 rssi 기저값이 50.0 이고,
        // 원본 임계 `RssiThres` 는 150.0 이다(SlaMapping.cpp:91 @0x7048b).
        r.beam_rssi.push_back((i % 90 == 0) ? kReflectorRssi : kBackgroundRssi);
    }
    return r;
}

LaserGeometry makeLaser()
{
    LaserGeometry laser;
    laser.min_angle = -M_PI;
    laser.angular_resolution = kBeamStepRad;
    laser.min_range = 0.05;
    laser.max_range = kMaxRange;
    return laser;
}

/// 방 안쪽 2 m 여백의 닫힌 사각 경로 + 시작점 복귀(루프 클로저 유발).
std::vector<std::array<double, 3>> makeTruthPath()
{
    std::vector<std::array<double, 3>> truth;
    auto addLeg = [&truth](double x0, double y0, double x1, double y1, int steps) {
        for (int s = 0; s < steps; ++s)
        {
            const double t = static_cast<double>(s) / steps;
            truth.push_back({x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, std::atan2(y1 - y0, x1 - x0)});
        }
    };
    // 벽에서 4 m 안쪽 둘레를 한 바퀴. 스텝 간격 약 0.18 m < MinimumTravelDistance(0.2 m)
    // → 일부는 이동 게이트로 폐기된다(게이트 동작 검증).
    constexpr double kMargin = 4.0;
    const double x0 = kMargin;
    const double y0 = kMargin;
    const double x1 = kRoomWidth - kMargin;
    const double y1 = kRoomHeight - kMargin;
    addLeg(x0, y0, x1, y0, 180);
    addLeg(x1, y0, x1, y1, 120);
    addLeg(x1, y1, x0, y1, 180);
    addLeg(x0, y1, x0, y0, 120);
    // 정지 구간 — 같은 자세를 반복 투입한다. 원본 이동 게이트는 0.01 m / 0.05 rad 로 아주 촘촘해
    // 스텝 간격(약 0.18 m)으로는 게이트를 시험할 수 없다. 실제로 멈춰 세워야 폐기가 일어난다.
    for (int i = 0; i < kStationaryFrames; ++i)
    {
        truth.push_back({x0, y0, 0.0});
    }
    return truth;
}

/// 입력 검증이 실제로 거부하는지 확인한다 — 없으면 잘못된 입력이 조용히 왜곡된 맵을 만든다.
void testInputValidation()
{
    const LaserGeometry laser = makeLaser();

    {
        SeerSlamMapper m;
        MapLogRecord bad = makeScan(2, 2, 0);
        bad.beam_angle.pop_back(); // 길이 불일치
        CHECK(m.processRecord(bad, laser) == ProcessResult::kInvalidInput,
              "빔 배열 길이 불일치를 거부해야 한다");
        CHECK(!m.lastError().empty(), "거부 사유가 기록돼야 한다");
    }
    {
        // 비균일 각도: **기본은 거부하지 않는다(원본 충실)**. 원본 Karto 는 per-beam 각도 배열을
        // 쓰지 않고 `minAngle + i*res` 로 재생성하므로 비균일 입력을 그대로 처리한다.
        // 실 로그에서 213 중 90 스캔이 비균일이었고(최대 1.54°), 거부하면 대조가 성립하지 않는다.
        constexpr double kInjectedDeviationRad = 0.01;
        SeerSlamMapper lenient;
        MapLogRecord bad = makeScan(2, 2, 0);
        bad.beam_angle[100] += kInjectedDeviationRad;
        CHECK(lenient.processRecord(bad, laser) == ProcessResult::kAdded,
              "기본 모드는 비균일 각도를 거부하지 않아야 한다(원본 충실)");
        CHECK(lenient.lastAngleDeviation() > kInjectedDeviationRad / 2.0,
              "비균일을 거부하지 않더라도 편차는 관측돼야 한다");

        // 엄격 모드(우리 전용 안전장치)에서는 거부한다.
        SeerSlamMapper strict;
        strict.setStrictAngleUniformity(true);
        CHECK(strict.processRecord(bad, laser) == ProcessResult::kInvalidInput,
              "엄격 모드는 비균일 각도를 거부해야 한다");
    }
    {
        SeerSlamMapper m;
        MapLogRecord bad = makeScan(2, 2, 0);
        bad.odo_w = std::nan("");
        CHECK(m.processRecord(bad, laser) == ProcessResult::kInvalidInput,
              "비유한 오도메트리를 거부해야 한다");
    }
    {
        SeerSlamMapper m;
        CHECK_FATAL(m.processRecord(makeScan(2, 2, 0), laser) == ProcessResult::kAdded,
                    "첫 스캔은 추가돼야 한다");
        LaserGeometry moved = laser;
        moved.offset_x += 0.5; // 도중 기하 변경
        CHECK(m.processRecord(makeScan(3, 2, 0), moved) == ProcessResult::kInvalidInput,
              "도중 LaserGeometry 변경을 거부해야 한다");
    }
    std::printf("[OK] 입력 검증 4종 (비균일 각도는 기본 허용 / 엄격 모드에서만 거부)\n");
}

/// 무효 거리(0·NaN·inf)가 들어와도 크래시 없이 max_range 로 정규화되는지.
void testRangeNormalization()
{
    SeerSlamMapper m;
    const LaserGeometry laser = makeLaser();
    MapLogRecord rec = makeScan(2, 2, 0);
    rec.beam_dist[0] = 0.0;
    rec.beam_dist[1] = std::nan("");
    rec.beam_dist[2] = std::numeric_limits<double>::infinity();
    rec.beam_dist[3] = -5.0;
    CHECK(m.processRecord(rec, laser) == ProcessResult::kAdded,
          "무효 거리는 레코드 거부 사유가 아니다(빔 단위로 걸러진다)");
    const MapResult map = m.buildMap();
    CHECK(map.valid, "무효 빔이 섞여도 맵이 산출돼야 한다");

    // **개수를 못박는다.** 무효 빔 4개는 점군에서 빠져야 한다.
    //   ⚠ 한때 범위 밖 거리를 `max_range` 로 정규화했는데, Karto 의 필터가
    //   `InRange(dist, minRange, rangeThreshold)` 이고 `rangeThreshold == max_range` 라
    //   **정확히 max_range 인 값이 통과**해 무반사 빔이 "그 거리에 벽이 있다"로 둔갑했다.
    //   오라클 대조 실측: 우리 점군 101,074개(=194x521 전 빔) vs 원본 81,948개.
    //   `map.valid` 만 보면 이 결함이 통과한다 — 개수 단언이 있어야 잡힌다.
    constexpr std::size_t kInvalidBeams = 4;
    CHECK(map.normal_pos_list.size() == static_cast<std::size_t>(kBeamCount) - kInvalidBeams,
          "무효 빔이 점군에 섞여 들어갔다(또는 유효 빔이 빠졌다)");
    for (const auto &p : map.normal_pos_list)
    {
        CHECK_FATAL(std::isfinite(p.first) && std::isfinite(p.second),
                    "점군에 비유한값이 새어나왔다");
    }
    std::printf("[OK] 무효 거리 정규화\n");
}

/// 본 시험 — 궤적 투입 후 게이트·루프클로저·최적화·맵 일관성을 단언한다.
void testMappingPipeline()
{
    SeerSlamMapper mapper;
    mapper.setMaxIterations(50);
    const LaserGeometry laser = makeLaser();
    const std::vector<std::array<double, 3>> truth = makeTruthPath();

    double drift = 0.0;
    double max_odo_err = 0.0;
    for (const auto &pose : truth)
    {
        // 스캔은 진짜 자세로 만들고, 오도에만 점증 드리프트를 주입한다.
        drift += kDriftPerStepRad;
        MapLogRecord rec = makeScan(pose[0], pose[1], pose[2]);
        rec.odo_x = pose[0] + drift * 0.5;
        rec.odo_y = pose[1] + drift * 0.3;
        rec.odo_w = pose[2] + drift;
        max_odo_err = std::max(max_odo_err, std::hypot(rec.odo_x - pose[0], rec.odo_y - pose[1]));
        const ProcessResult r = mapper.processRecord(rec, laser);
        CHECK_FATAL(r != ProcessResult::kInvalidInput, "합성 입력이 검증에서 거부됐다");
    }

    const MapResult map = mapper.buildMap();
    const SolverStats &st = mapper.solverStats();
    std::printf("궤적 %zu 스텝 → 그래프 노드 %d개 (게이트로 %zu개 폐기)\n", truth.size(),
                mapper.numScans(), truth.size() - static_cast<std::size_t>(mapper.numScans()));
    std::printf("맵: normal=%zu, rssi=%zu, 경계 x[%.2f,%.2f] y[%.2f,%.2f]\n",
                map.normal_pos_list.size(), map.rssi_pos_list.size(), map.min_x, map.max_x,
                map.min_y, map.max_y);
    std::printf("솔버: Compute 호출 %d회, 노드 %d, 간선 %d, 기각 %d, 직전 반복 %d\n",
                st.compute_calls, st.nodes_added, st.edges_added, st.edges_rejected,
                st.last_iterations);
    std::printf("주입 오도 최대 오차 %.3f m\n", max_odo_err);

    // (1) 이동 게이트가 동작한다 — 전량 추가도, 거의 미추가도 아니다.
    CHECK(mapper.numScans() >= 5, "스캔이 그래프에 충분히 추가되지 않았다");
    // 정지 구간 프레임은 이동 게이트로 폐기돼야 한다(최소한 그 대부분).
    CHECK(mapper.numScans() <= static_cast<int>(truth.size()) - kStationaryFrames + 1,
          "정지 구간이 이동 게이트로 폐기되지 않았다");

    // (2) 루프클로저가 실제로 성립해 g2o 가 돌았다.
    //     이 단언이 없으면 최적화가 한 번도 안 돌아도 아래 경계 검사는 통과한다.
    CHECK(st.compute_calls >= 1, "루프클로저가 한 번도 성립하지 않았다 — g2o 미호출");
    CHECK(st.nodes_added == mapper.numScans(), "그래프 노드 수가 추가 스캔 수와 다르다");
    CHECK(st.edges_added >= mapper.numScans() - 1, "순차 간선조차 부족하다");
    CHECK(st.edges_rejected == 0, "간선이 기각됐다 — 공분산 특이 가능성");

    // (2-a) 맵 원점 앵커가 실제로 걸렸다. LM 감쇠가 자유 게이지를 가려 결과만으로는 드러나지 않으므로
    //       불변식을 직접 단언한다(이게 없으면 `setFixed(true)` 를 지워도 시험이 통과한다 — 실측).
    CHECK(st.has_fixed_node, "첫 노드 고정(맵 원점 앵커)이 걸리지 않았다");

    // (2-b) 특성 고정(characterization) — 동봉 Karto 커밋 922db50 + Seer 튜닝 조합에서
    //       이 궤적이 만드는 그래프 규모를 못박는다. 파라미터가 바뀌면 여기가 먼저 깨진다.
    //       실측: `loop_search_maximum_distance` 를 상류 stock(4.0)으로 되돌리면
    //       Compute 1→4회, 간선 355→333 으로 변한다.
    constexpr int kExpectedEdgesMin = 700;
    constexpr int kExpectedEdgesMax = 760;
    constexpr int kExpectedComputeCalls = 1;
    CHECK(st.edges_added >= kExpectedEdgesMin && st.edges_added <= kExpectedEdgesMax,
          "그래프 간선 수가 특성 범위를 벗어났다 — Karto 판본 또는 파라미터가 바뀌었다");
    CHECK(st.compute_calls == kExpectedComputeCalls,
          "루프클로저 성립 횟수가 특성값과 다르다 — 파라미터가 바뀌었다");

    // (3) 맵이 산출되고 발산하지 않는다.
    // ── 좌표계 주의 ──────────────────────────────────────────────────────────
    // 산출 맵은 **첫 레코드 오도(pose0) 기준 원점 이동** 좌표계다. 원본 `KartoSLAM` 이
    // `SetCorrectedPose(odom - mPose0)` 로 시작 자세를 원점에 놓기 때문이다(KartoSLAM.cpp:41,123).
    // 이 궤적의 첫 자세는 (kMargin, kMargin, 0) 이므로 방 [0,W]x[0,H] 가 그만큼 평행이동해 보인다.
    constexpr double kPose0X = 4.0; // = kMargin (makeTruthPath 의 첫 자세)
    constexpr double kPose0Y = 4.0;
    const double exp_min_x = 0.0 - kPose0X;
    const double exp_max_x = kRoomWidth - kPose0X;
    const double exp_min_y = 0.0 - kPose0Y;
    const double exp_max_y = kRoomHeight - kPose0Y;

    CHECK_FATAL(map.valid && !map.normal_pos_list.empty(), "맵 점군 미산출");
    // 반사판 점군은 **개수까지** 못박는다. `!empty()` 만으로는 임계값이 무너져도 통과한다 —
    // 실측: `RssiThres` 를 150.0 → 0.0 으로 되돌리면 전 빔이 반사판이 되는데(2,404 → 216,360)
    // `!empty()` 단언은 그대로 통과했다(돌연변이 미검출).
    // 합성 스캔은 90도마다 1개(i%90==0 → i=0,90,180,270)이므로 스캔당 정확히 4점이다.
    constexpr std::size_t kReflectorsPerScan = 4;
    const std::size_t expected_rssi = kReflectorsPerScan * static_cast<std::size_t>(mapper.numScans());
    CHECK(map.rssi_pos_list.size() == expected_rssi,
          "반사판 점군 개수가 예상과 다르다 — rssi 임계 또는 분류 경로가 바뀌었다");
    constexpr double kBoundSlackM = 2.0;
    CHECK(map.min_x > exp_min_x - kBoundSlackM && map.max_x < exp_max_x + kBoundSlackM,
          "맵 x 경계 발산 (pose0 원점 이동 반영)");
    CHECK(map.min_y > exp_min_y - kBoundSlackM && map.max_y < exp_max_y + kBoundSlackM,
          "맵 y 경계 발산 (pose0 원점 이동 반영)");

    // (4) 보정이 실제로 일어났다 — 최적화가 오도 드리프트보다 좁은 범위로 맵을 묶는다.
    //     드리프트를 그대로 두면 점군이 방 밖으로 max_odo_err 만큼 밀린다.
    CHECK(max_odo_err > 0.1, "드리프트 주입이 너무 작아 교정 여부를 볼 수 없다(시험 설계 오류)");
    const double overshoot = std::max({exp_min_x - map.min_x, exp_min_y - map.min_y,
                                       map.max_x - exp_max_x, map.max_y - exp_max_y, 0.0});
    std::printf("경계 초과량 %.3f m (주입 드리프트 %.3f m)\n", overshoot, max_odo_err);
    // 스캔매칭이 프레임마다 오도를 보정하므로 경계 초과량은 방 크기 대비 아주 작아야 한다.
    // (주입 드리프트와의 절대 비교는 노드 밀도에 좌우돼 취약하다 — 파라미터 정정 후 실제로 깨졌다.)
    constexpr double kMaxOvershootM = 0.30;
    CHECK(overshoot < kMaxOvershootM, "보정 후 경계 초과량이 허용치를 넘었다");

    std::printf("[OK] 매핑 파이프라인\n");
}
} // namespace

int main()
{
    setvbuf(stdout, nullptr, _IONBF, 0);
    testInputValidation();
    testRangeNormalization();
    testMappingPipeline();
    return CHECK_SUMMARY();
}
