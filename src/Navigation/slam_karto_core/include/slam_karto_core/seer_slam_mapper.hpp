// SeerSlamMapper — Open Karto + g2o(G2OSolver) 파이프라인 파사드.
//
// RE(Reverse Engineering) 근거: 원본 파이프라인은
//   `Message_MapLogData` → `LocalizedRangeScan`(오도 seed) → `karto::Mapper::Process`
//   (스캔매칭 + MapperGraph + TryCloseLoop → `G2OSolver` 최적화 → CorrectPoses)
//   → 보정 포즈 반영 점군(`normal_pos_list`) + rssi(`rssi_pos_list`) = `Message_Map`.
//   리뷰: docs/code_review/seer-slam-mapping/2026-08-08.md
//
// 원본 직접 구동 오라클과 대조 검증됨 (2026-08-09, 실 로그 `robokit_2023-08-10_05-41-41.rawmap`):
//   스캔 채택 판정 213/213 일치 · 점군 개수 81,948 완전 일치 ·
//   보정 포즈 위치차 max 0.026 m / mean 0.0084 m, 방위차 max 0.0073 rad / mean 0.0019 rad.
//   대조 도구: Tools/seer_rawmap/replay/ (compare.py), 오라클: 원본 .so dlopen 하니스.
//
// 원본과의 알려진 격차 (ADR "채용 = 거동 동등" 전제의 명시적 예외):
//   ① 원본은 반사강도를 **스캔매칭 응답**에도 반영한다(`ScanMatcher::GetResponseWithRssi`,
//      `m_pRssiGrid` 상시 할당). 본 모듈에는 그 경로가 없다 — rssi 는 사후 점군 분류로만 쓴다.
//      단 원본에서도 조건부(`sum(vID) > nPoints && nPoints < pointSize`)이며 그 밖에는 수치 동일.
//   ② 원본의 후처리(OccupancyGrid 0.02 m 래스터화, HTLine Hough 벽각 보정)는 여기 없다 —
//      원본 `KartoSLAM::SaveMap` 의 지도 점군은 스캔 점군이 아니라 **점유격자 셀**에서 나온다.
//   ③ per-beam 각도는 동봉 Karto 패치로 재현했다(patches/0001-use-measured-per-beam-angles.patch).
#ifndef SLAM_KARTO_CORE_SEER_SLAM_MAPPER_HPP
#define SLAM_KARTO_CORE_SEER_SLAM_MAPPER_HPP

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "slam_karto_core/seer_mapper_config.hpp"
#include "slam_karto_core/types.hpp"

namespace karto
{
class Mapper;
class Dataset;
class LaserRangeFinder;
} // namespace karto

namespace slam_karto_core
{

class G2OSolver;

/// 라이다 기하 설정. **첫 `processRecord` 호출의 값만 채택**되며 이후 호출의 값은 그것과
/// 일치해야 한다(불일치 시 `kInvalidInput`). 도중에 바뀌면 Karto 가 아는 기하와 rssi 좌표계가
/// 어긋나기 때문이다.
struct LaserGeometry
{
    double min_angle = 0.0;          ///< rad — 첫 빔 각도
    double angular_resolution = 0.0; ///< rad — 빔 간격. 0 이면 `beam_angle` 에서 유도
    /// m. 기본 **0.001 은 원본 실측값** — `KartoSLAM` 생성자가 `SetMinimumRange(0.001)` 로 하드코딩한다
    ///   (KartoSLAM.cpp:32). 초기 이식본의 0.05 는 근거 없는 값이었다.
    double min_range = 0.001;
    double max_range = 30.0;         ///< m
    double offset_x = 0.0;           ///< 라이다 장착 x (m, 로봇좌표)
    double offset_y = 0.0;           ///< 라이다 장착 y (m)
    double offset_yaw = 0.0;         ///< 라이다 장착 방위 (rad)
};

class SeerSlamMapper
{
  public:
    explicit SeerSlamMapper(const SeerMapperParams &params = {});
    ~SeerSlamMapper();

    SeerSlamMapper(const SeerSlamMapper &) = delete;
    SeerSlamMapper &operator=(const SeerSlamMapper &) = delete;

    /// 한 로그 레코드를 처리한다. 첫 호출 시 `laser` 로 `LaserRangeFinder` 를 구성한다.
    ///
    /// 입력을 먼저 검증한다 — 빔 배열 길이 일치, 유한성, 기하 일관성.
    /// 위반 시 `kInvalidInput` 을 돌려주고 사유를 `lastError()` 에 남긴다.
    /// 각도 비균일은 **거부하지 않고 관측만** 한다(원본 충실 — `setStrictAngleUniformity` 참조).
    /// 거리는 **원시값 그대로** Karto 에 넘긴다 — 유효/무효 판정은 Karto 필터가 한다.
    /// 비유한값(NaN/inf)만 임계 밖으로 밀어낸다.
    ///
    /// @param rec   스캔 + 오도메트리 레코드
    /// @param laser 라이다 기하 (첫 호출에만 채택, 이후는 일치 검사)
    /// @return kAdded / kGateRejected / kInvalidInput
    ProcessResult processRecord(const MapLogRecord &rec, const LaserGeometry &laser);

    /// rssi 임계 — 이 값을 **초과**하는 빔만 `rssi_pos_list` 에 넣는다.
    /// 기본값 **150.0 은 원본 실측값**이다(`seer_runtime::kRssiThreshold` 주석 참조).
    ///   초기 이식본은 0.0 을 썼는데, 그러면 모든 빔이 통과해 반사판 점군이 전혀 달라진다.
    void setRssiThreshold(double t)
    {
        rssi_threshold_ = t;
    }

    /// g2o 최적화 반복 상한.
    void setMaxIterations(int n);

    /// 현재까지 누적된 그래프에서 맵(점군)을 산출한다. 보정 포즈(최적화 결과)를 반영한다.
    MapResult buildMap() const;

    /// 그래프에 추가된 스캔(노드) 수.
    int numScans() const
    {
        return num_scans_;
    }

    /// 직전 `processRecord` 호출이 그래프에 추가한 스캔의 Karto uniqueId.
    /// 추가되지 않았으면(`kGateRejected`/`kInvalidInput`) `kNoScanId`(-1).
    ///
    /// ▶ 추가 사유(2026-08-09): 원본 `.so` 를 직접 구동하는 오라클과 **스캔 단위**로 대조하려면
    ///   "몇 번째 입력이 어떤 노드가 됐고 그 보정 포즈가 얼마인가"가 필요한데, 기존 공개 API 는
    ///   `buildMap()`(점군 뭉치)과 `numScans()`(개수)뿐이라 스캔↔포즈 대응을 밖에서 알 수 없었다.
    ///   대조 도구: Tools/seer_rawmap/replay/replay_ours.cpp
    int lastScanId() const
    {
        return last_scan_id_;
    }

    /// 직전 `processRecord` 호출 **직후** 그 스캔의 보정 포즈 (맵 프레임, x·y 는 m, theta 는 rad).
    ///
    /// "직후"가 중요하다 — `Process` 안에서 루프클로저가 성립하면 `CorrectPoses` 가 **과거 스캔들의**
    /// 포즈까지 되돌려 놓으므로, 나중에 읽은 값은 그 시점의 값이 아니다. 그 순간의 값을 기록해 둔다.
    ///
    /// 추가되지 않은 호출(`kGateRejected`/`kInvalidInput`)이면 입력 오도메트리를 그대로 돌려준다
    /// (`kInvalidInput` 은 검증 실패 전이라도 입력값 자체는 기록한다).
    /// 추가 사유는 `lastScanId()` 주석 참조.
    const Pose2D &lastCorrectedPose() const
    {
        return last_corrected_pose_;
    }

    /// 직전 `kInvalidInput` 의 사유. 비어 있으면 아직 없다.
    const std::string &lastError() const
    {
        return last_error_;
    }

    /// 최적화 계측 — `compute_calls == 0` 이면 루프클로저가 한 번도 성립하지 않았다는 뜻이다.
    const SolverStats &solverStats() const;

  private:
    /// 입력 검증. 실패 시 `last_error_` 를 채우고 false.
    bool validate(const MapLogRecord &rec, const LaserGeometry &laser);

  public:
    /// 빔 각도 균일성 위반을 **거부 사유로 쓸지** 정한다. 기본 `false` = 원본 충실.
    ///   원본 Karto 는 per-beam 각도 배열을 쓰지 않고 `minAngle + i*res` 로 재생성하므로
    ///   비균일 입력을 거부하지 않는다. 실 로그에서 213 중 90 스캔이 비균일이었다(최대 1.54°).
    ///   ROS2 어댑터처럼 병합 스캔을 먹이는 경로에서 조기 발견이 필요하면 켠다.
    void setStrictAngleUniformity(bool strict)
    {
        strict_angle_uniformity_ = strict;
    }

    /// 직전 레코드의 빔 각도 간격 최대 편차 (rad). 거부하지 않아도 얼마나 어긋났는지는 알아야 한다.
    double lastAngleDeviation() const
    {
        return last_angle_deviation_;
    }

  private:

    SeerMapperParams params_;
    std::unique_ptr<karto::Mapper> mapper_;
    std::unique_ptr<karto::Dataset> dataset_;
    std::unique_ptr<G2OSolver> solver_;
    karto::LaserRangeFinder *laser_ = nullptr; ///< dataset_ 소유
    LaserGeometry geometry_;                   ///< 첫 호출에서 확정된 기하
    bool laser_ready_ = false;
    /// **첫 레코드**의 오도메트리. 원본 `KartoSLAM` 생성자가 `mPose0 = data[0].robot_odo_*` 로 잡고
    /// (KartoSLAM.cpp:41), 매 스캔 `SetCorrectedPose(odom - mPose0)` 로 빼서 **시작 자세를 원점으로** 옮긴다
    /// (KartoSLAM.cpp:123). 이걸 빼먹으면 전 궤적이 그만큼 평행이동·회전한다 —
    /// 실측: 오라클 대조에서 idx 0 부터 위치차 5.82 m·방위차 1.46 rad 로 갈렸다.
    Pose2D pose0_;
    bool pose0_set_ = false;
    double rssi_threshold_ = seer_runtime::kRssiThreshold;
    bool strict_angle_uniformity_ = false; ///< 기본 false = 원본 충실(비균일 허용)
    double last_angle_deviation_ = 0.0;    ///< 직전 레코드의 각도 간격 최대 편차 (rad)
    int num_scans_ = 0;
    /// 직전 `processRecord` 결과 — `lastScanId()`/`lastCorrectedPose()` 가 돌려주는 값.
    int last_scan_id_ = kNoScanId;
    Pose2D last_corrected_pose_;
    std::string last_error_;
    /// 그래프에 추가된 스캔별 rssi 빔 끝점(로봇좌표, laser offset 반영).
    /// `buildMap()` 이 각 스캔의 보정 포즈로 월드 변환한다.
    std::vector<std::pair<int, std::vector<std::pair<double, double>>>> rssi_by_scan_;
};

} // namespace slam_karto_core

#endif // SLAM_KARTO_CORE_SEER_SLAM_MAPPER_HPP
