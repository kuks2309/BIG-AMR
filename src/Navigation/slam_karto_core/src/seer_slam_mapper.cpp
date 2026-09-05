#include "slam_karto_core/seer_slam_mapper.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <unordered_map>

#include <open_karto/Karto.h>
#include <open_karto/Mapper.h>

#include "slam_karto_core/g2o_solver.hpp"

namespace slam_karto_core
{

namespace
{
/// Karto `SensorManager` 조회 키. `LocalizedRangeScan` 이 이 이름으로 LaserRangeFinder 를 찾는다.
const char *const kSensorName = "SeerLaser";

/// 각도 간격 균일성 허용 편차 (rad). **엄격 모드에서만** 거부 임계로 쓴다(기본은 관측만).
/// 0.17° step 라이다에서 이 값(약 0.006°)은 부동소수 오차는 통과시키고 실제 비균일은 잡아낸다.
constexpr double kAngleUniformityToleranceRad = 1e-4;

/// 기하 일관성 검사 허용 오차 (m 및 rad).
constexpr double kGeometryMatchTolerance = 1e-9;

/// `angular_resolution` 을 유도하지 못했을 때의 안전 기본값 (1°).
constexpr double kFallbackAngularResolutionRad = M_PI / 180.0;

/// 빔 2개 미만이면 간격을 유도할 수 없다.
constexpr std::size_t kMinBeamsToDeriveResolution = 2;

/// 비유한(NaN/inf) 거리를 밀어낼 배수. `max_range` 의 이 배수로 보내 Karto 필터가 확실히 거르게 한다.
///   원본은 무반사를 9999.999 같은 원시값으로 넘긴다 — 임계보다 크기만 하면 결과는 같다.
constexpr double kNonFiniteRangeSentinelFactor = 2.0;

/// 각도를 (-pi, pi] 로 정규화한다. 원본이 `SetCorrectedPose` 의 heading 에 적용한다.
double normalizeAngle(double a)
{
    while (a > M_PI)
    {
        a -= 2.0 * M_PI;
    }
    while (a <= -M_PI)
    {
        a += 2.0 * M_PI;
    }
    return a;
}

bool nearlyEqual(double a, double b, double tol)
{
    return std::fabs(a - b) <= tol;
}

bool sameGeometry(const LaserGeometry &a, const LaserGeometry &b)
{
    return nearlyEqual(a.min_angle, b.min_angle, kGeometryMatchTolerance) &&
           nearlyEqual(a.min_range, b.min_range, kGeometryMatchTolerance) &&
           nearlyEqual(a.max_range, b.max_range, kGeometryMatchTolerance) &&
           nearlyEqual(a.offset_x, b.offset_x, kGeometryMatchTolerance) &&
           nearlyEqual(a.offset_y, b.offset_y, kGeometryMatchTolerance) &&
           nearlyEqual(a.offset_yaw, b.offset_yaw, kGeometryMatchTolerance);
}
} // namespace

SeerSlamMapper::SeerSlamMapper(const SeerMapperParams &params)
    : params_(params), mapper_(new karto::Mapper()), dataset_(new karto::Dataset()),
      solver_(new G2OSolver())
{
    applySeerParams(mapper_.get(), params_);
    mapper_->SetScanSolver(solver_.get()); // g2o backend 연결
}

SeerSlamMapper::~SeerSlamMapper()
{
    // mapper_ 가 solver_ 를 참조하므로 mapper_ 를 먼저 파괴한다.
    mapper_.reset();
    dataset_.reset();
    solver_.reset();
}

void SeerSlamMapper::setMaxIterations(int n)
{
    solver_->setMaxIterations(n);
}

const SolverStats &SeerSlamMapper::solverStats() const
{
    return solver_->stats();
}

bool SeerSlamMapper::validate(const MapLogRecord &rec, const LaserGeometry &laser)
{
    if (rec.beam_dist.empty())
    {
        last_error_ = "beam_dist 가 비어 있다";
        return false;
    }
    if (rec.beam_dist.size() != rec.beam_angle.size())
    {
        last_error_ = "beam_dist(" + std::to_string(rec.beam_dist.size()) + ") 와 beam_angle(" +
                      std::to_string(rec.beam_angle.size()) + ") 길이 불일치";
        return false;
    }
    if (!rec.beam_rssi.empty() && rec.beam_rssi.size() != rec.beam_dist.size())
    {
        last_error_ = "beam_rssi(" + std::to_string(rec.beam_rssi.size()) +
                      ") 가 beam_dist 와 길이 불일치";
        return false;
    }
    if (!std::isfinite(rec.odo_x) || !std::isfinite(rec.odo_y) || !std::isfinite(rec.odo_w))
    {
        last_error_ = "오도메트리에 비유한값(NaN/inf)";
        return false;
    }
    if (!(laser.max_range > laser.min_range) || !std::isfinite(laser.max_range) ||
        !std::isfinite(laser.min_range))
    {
        last_error_ = "라이다 range 구간이 유효하지 않다";
        return false;
    }

    for (std::size_t i = 0; i < rec.beam_angle.size(); ++i)
    {
        if (!std::isfinite(rec.beam_angle[i]))
        {
            last_error_ = "beam_angle[" + std::to_string(i) + "] 가 비유한값";
            return false;
        }
    }

    // 각도 간격 균일성 — **관측만 하고 거부하지 않는다(기본).**
    //
    // 원본 Karto 는 비균일 각도를 거부하지 않는다. Seer 포크는 per-beam 각도 배열
    // (`LaserRangeScan::m_pAngleReadings`)을 저장하고 점 좌표 계산에 **그 값을 그대로** 쓴다 —
    // 우리 동봉본에도 같은 경로를 패치로 넣어 두었다
    // (third_party/patches/0001-use-measured-per-beam-angles.patch).
    // (상류 무개조본은 `minimumAngle + i * angularResolution` 로 재생성하지만, 그 역시 거부는 안 한다.)
    //
    // ⚠ 초기 이식본은 비균일을 `kInvalidInput` 으로 거부했다. 실측 결과 원본 로그
    // `robokit_2023-08-10_05-41-41.rawmap` 의 213 스캔 중 **90개가 버려졌다**(최대 편차 0.0268 rad ≈ 1.54°).
    // 원본이 처리하는 데이터를 우리가 버리면 대조 자체가 성립하지 않는다 — 원본에 맞춘다.
    // 엄격 모드가 필요하면 `setStrictAngleUniformity(true)` 로 켠다(우리 전용 안전장치).
    last_angle_deviation_ = 0.0;
    if (rec.beam_angle.size() >= kMinBeamsToDeriveResolution)
    {
        const double step = rec.beam_angle[1] - rec.beam_angle[0];
        if (!(std::fabs(step) > 0.0))
        {
            last_error_ = "beam_angle 간격이 0";
            return false;
        }
        for (std::size_t i = 1; i < rec.beam_angle.size(); ++i)
        {
            const double d = std::fabs((rec.beam_angle[i] - rec.beam_angle[i - 1]) - step);
            last_angle_deviation_ = std::max(last_angle_deviation_, d);
        }
        if (strict_angle_uniformity_ && last_angle_deviation_ > kAngleUniformityToleranceRad)
        {
            last_error_ = "beam_angle 간격이 균일하지 않다 (최대편차=" +
                          std::to_string(last_angle_deviation_) + " rad, 허용=" +
                          std::to_string(kAngleUniformityToleranceRad) + ")";
            return false;
        }
    }

    if (laser_ready_ && !sameGeometry(geometry_, laser))
    {
        last_error_ = "LaserGeometry 가 첫 호출과 다르다 — 도중 변경은 허용하지 않는다";
        return false;
    }
    return true;
}

ProcessResult SeerSlamMapper::processRecord(const MapLogRecord &rec, const LaserGeometry &laser)
{
    // 매 호출마다 "직전 결과"를 먼저 입력 오도메트리 / 식별자 없음으로 되돌린다.
    // 추가되지 않은 호출 뒤에 이전 호출의 값이 남아 있으면 대조 도구가 조용히 틀린 포즈를 기록한다.
    last_scan_id_ = kNoScanId;
    last_corrected_pose_ = Pose2D{rec.odo_x, rec.odo_y, rec.odo_w};

    if (!validate(rec, laser))
    {
        return ProcessResult::kInvalidInput;
    }
    last_error_.clear();

    // 첫 레코드: LaserRangeFinder 구성 + 센서 등록.
    if (!laser_ready_)
    {
        geometry_ = laser;
        double ang_res = laser.angular_resolution;
        if (!(ang_res > 0.0) && rec.beam_angle.size() >= kMinBeamsToDeriveResolution)
        {
            ang_res = rec.beam_angle[1] - rec.beam_angle[0];
        }
        if (!(ang_res > 0.0))
        {
            ang_res = kFallbackAngularResolutionRad;
        }
        geometry_.angular_resolution = ang_res;

        // Karto 는 빔 수를 (max-min)/res + 1 로 계산하므로 max_angle 을 실제 빔 수에 맞춘다.
        const int n_beams = static_cast<int>(rec.beam_dist.size());
        const double max_angle = laser.min_angle + (n_beams - 1) * ang_res;

        laser_ = karto::LaserRangeFinder::CreateLaserRangeFinder(karto::LaserRangeFinder_Custom,
                                                                 karto::Name(kSensorName));
        laser_->SetOffsetPose(karto::Pose2(laser.offset_x, laser.offset_y, laser.offset_yaw));
        laser_->SetMinimumRange(laser.min_range);
        laser_->SetMaximumRange(laser.max_range);
        laser_->SetMinimumAngle(laser.min_angle);
        laser_->SetMaximumAngle(max_angle);
        laser_->SetAngularResolution(ang_res);
        laser_->SetRangeThreshold(laser.max_range);
        dataset_->Add(laser_); // SensorManager 에 등록 (Process 가 이름으로 해석)
        laser_ready_ = true;
    }

    // 거리는 **원시값 그대로** 넘긴다 — 유효/무효 판정은 Karto 가 한다.
    //
    // ⚠ 한때 범위 밖 거리를 `max_range` 로 정규화했다가 되돌렸다. Karto 의 필터는
    //   `math::InRange(dist, minRange, rangeThreshold)` 이고 `rangeThreshold == max_range` 이므로
    //   **정확히 max_range 인 값은 통과한다** — 무반사 빔이 "그 거리에 벽이 있다"로 둔갑했다.
    //   실측: 오라클 대조에서 우리 점군 101,074개(=194×521 전 빔) vs 원본 81,948개.
    //   원본은 무반사를 원시값(9999.999)으로 그대로 넘겨 걸러낸다.
    //   비유한값만 임계 밖으로 밀어 안전을 지키고, 유한값은 손대지 않는다.
    karto::RangeReadingsVector readings;
    readings.reserve(rec.beam_dist.size());
    for (const double d : rec.beam_dist)
    {
        readings.push_back(std::isfinite(d) ? d : kNonFiniteRangeSentinelFactor * geometry_.max_range);
    }

    // **첫 레코드 기준 원점 이동** — 원본 `KartoSLAM::Process` 가 하는 그대로다.
    //   odometric = 원시 오도, corrected = 원시 오도 − mPose0 (heading 은 정규화).
    //   근거: KartoSLAM.cpp:41(mPose0 = data[0]) · :123(SetCorrectedPose(odom - mPose0)).
    //   오라클 대조 실측: 이걸 빼먹었을 때 idx 0 부터 위치차 5.82 m·방위차 1.46 rad.
    if (!pose0_set_)
    {
        pose0_ = Pose2D{rec.odo_x, rec.odo_y, rec.odo_w};
        pose0_set_ = true;
    }
    auto *pScan = new karto::LocalizedRangeScan(karto::Name(kSensorName), readings);
    // per-beam 각도를 그대로 넘긴다 — 원본 충실.
    //   상류 Karto 는 `minimumAngle + i*angularResolution` 로 각도를 재생성하지만 Seer 는 그 부분을
    //   개조해 실측 배열(`LaserRangeScan::m_pAngleReadings`)을 쓴다. 동봉본에 같은 경로를 넣어 두었다
    //   (third_party/patches/0001-use-measured-per-beam-angles.patch).
    //   근거: 원본 `LaserRangeFinder` 의 min/maxAngle 은 ±pi/2 기본값 그대로인데(오라클 실측)
    //   재생성 방식이면 521빔이 -90°~+170° 를 덮어야 한다 — 실제 원본 점군은 -130°~+130° 다.
    //   그리고 오라클 대조에서 최초 분기 스캔(idx 20)이 최초 비균일 스캔과 정확히 일치했다.
    pScan->SetAngleReadings(karto::RangeReadingsVector(rec.beam_angle.begin(), rec.beam_angle.end()));
    pScan->SetOdometricPose(karto::Pose2(rec.odo_x, rec.odo_y, rec.odo_w));
    pScan->SetCorrectedPose(karto::Pose2(rec.odo_x - pose0_.x, rec.odo_y - pose0_.y,
                                         normalizeAngle(rec.odo_w - pose0_.theta)));

    const bool added = mapper_->Process(pScan);
    if (!added)
    {
        delete pScan; // 이동 게이트 미달 → 폐기
        return ProcessResult::kGateRejected;
    }

    dataset_->Add(pScan); // 소유권 이전
    ++num_scans_;

    // `Process` 직후의 보정 포즈를 그 자리에서 붙잡는다 — 뒤이은 루프클로저가 덮어쓰기 전 값이다.
    last_scan_id_ = pScan->GetUniqueId();
    {
        const karto::Pose2 &corrected = pScan->GetCorrectedPose();
        last_corrected_pose_ =
            Pose2D{corrected.GetX(), corrected.GetY(), corrected.GetHeading()};
    }

    // rssi 빔 끝점을 로봇좌표(laser offset 반영)로 저장 → buildMap 이 보정포즈로 월드변환.
    if (!rec.beam_rssi.empty())
    {
        std::vector<std::pair<double, double>> local;
        const double c_off = std::cos(geometry_.offset_yaw);
        const double s_off = std::sin(geometry_.offset_yaw);
        for (std::size_t i = 0; i < rec.beam_rssi.size(); ++i)
        {
            if (!(rec.beam_rssi[i] > rssi_threshold_))
            {
                continue;
            }
            const double d = rec.beam_dist[i];
            if (!(std::isfinite(d) && d >= geometry_.min_range && d < geometry_.max_range))
            {
                continue;
            }
            // per-beam 각도 배열을 **그대로** 쓴다 — 원본 충실.
            //
            // ⚠ 한때 `min_angle + i*res` 재생성으로 바꿨다가 되돌렸다. 상류 open_karto 의
            //   `LocalizedRangeScan::Update()` 는 재생성하지만 **Seer 는 그 부분을 개조**해
            //   per-beam 배열(`LaserRangeScan::m_pAngleReadings`)을 쓴다.
            //   근거: 원본 `LaserRangeFinder` 의 min/maxAngle 은 ±pi/2 기본값 그대로인데
            //   (오라클 기록 `oracle_params.json`), 521빔에 `minAngle + i*res` 를 적용하면
            //   -90°~+170° 를 덮어야 한다. 실제 원본 점군은 -130°~+130° 기하와 일치한다.
            //   또 오라클 대조에서 **최초 분기 스캔(idx 20)이 최초 비균일 스캔과 정확히 일치**했다.
            const double a = rec.beam_angle[i];
            // 끝점(라이다 로컬) → 로봇좌표: laser offset(위치 + 방위) 적용.
            const double ex = d * std::cos(a);
            const double ey = d * std::sin(a);
            local.emplace_back(laser.offset_x + ex * c_off - ey * s_off,
                               laser.offset_y + ex * s_off + ey * c_off);
        }
        if (!local.empty())
        {
            rssi_by_scan_.emplace_back(pScan->GetUniqueId(), std::move(local));
        }
    }
    return ProcessResult::kAdded;
}

MapResult SeerSlamMapper::buildMap() const
{
    MapResult out;
    const karto::LocalizedRangeScanVector scans = mapper_->GetAllProcessedScans();
    out.num_scans = static_cast<int>(scans.size());
    if (scans.empty())
    {
        return out;
    }

    // rssi 스캔 조회를 O(1) 로 — 이전 구현은 스캔 전체를 선형 탐색해 O(N_rssi x N_scans) 였다.
    std::unordered_map<int, const karto::LocalizedRangeScan *> by_id;
    by_id.reserve(scans.size());

    double min_x = std::numeric_limits<double>::max();
    double min_y = std::numeric_limits<double>::max();
    double max_x = std::numeric_limits<double>::lowest();
    double max_y = std::numeric_limits<double>::lowest();

    for (auto *pScan : scans)
    {
        if (pScan == nullptr)
        {
            continue;
        }
        by_id.emplace(pScan->GetUniqueId(), pScan);
        // 보정 포즈(최적화 반영) 기준 월드 점군. Karto 가 laser offset + corrected pose 로 변환한다.
        //
        // **`true` = 필터본**(유효 반사만). `false` 는 무반사 빔까지 포함해 `range_threshold`(30 m)로
        // 클램프된 허깨비 점을 전 빔에 만든다 — 실측: 7.6 m 국소 주행에서 점 101,074개(=194×521 전 빔),
        // bbox ±33 m. 필터본은 81,948개다. 장애물 점군의 의미상 필터본이 맞다.
        // (원본 `KartoSLAM::SaveMap` 은 `GetPointReadings` 를 아예 쓰지 않고 `OccupancyGrid` 로 간다 —
        //  그 경로는 미구현이며 debt 로 남아 있다. 여기서는 오라클이 채택한 필터본에 맞춘다.)
        const karto::PointVectorDouble &pts = pScan->GetPointReadings(true);
        for (const auto &pt : pts)
        {
            out.normal_pos_list.emplace_back(pt.GetX(), pt.GetY());
            min_x = std::min(min_x, pt.GetX());
            min_y = std::min(min_y, pt.GetY());
            max_x = std::max(max_x, pt.GetX());
            max_y = std::max(max_y, pt.GetY());
        }
    }

    for (const auto &entry : rssi_by_scan_)
    {
        const auto it = by_id.find(entry.first);
        if (it == by_id.end())
        {
            continue;
        }
        const karto::Pose2 &pose = it->second->GetCorrectedPose();
        const double px = pose.GetX();
        const double py = pose.GetY();
        const double cp = std::cos(pose.GetHeading());
        const double sp = std::sin(pose.GetHeading());
        for (const auto &lp : entry.second)
        {
            out.rssi_pos_list.emplace_back(px + lp.first * cp - lp.second * sp,
                                           py + lp.first * sp + lp.second * cp);
        }
    }

    out.valid = !out.normal_pos_list.empty();
    if (out.valid)
    {
        out.min_x = min_x;
        out.min_y = min_y;
        out.max_x = max_x;
        out.max_y = max_y;
    }
    return out;
}

} // namespace slam_karto_core
