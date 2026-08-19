#ifndef WALL_LOCALIZER_CORE__WALL_LOCALIZER_HPP_
#define WALL_LOCALIZER_CORE__WALL_LOCALIZER_HPP_

#include <string>
#include <vector>

#include "wall_localizer_core/line_extractor.hpp"
#include "wall_localizer_core/pose_solver.hpp"
#include "wall_localizer_core/wall_matcher.hpp"
#include "wall_localizer_core/types.hpp"

namespace wall_localizer_core
{

enum class Status
{
    OK = 0,        // 전 기준 벽 대응 + 전 게이트 통과
    DEGRADED = 1,  // min_walls 이상 대응 + 전 게이트 통과 (일부 벽 미대응)
    LOST = 2       // 해 없음 — 자세 출력 금지
};

// 벽별 대응·잔차 (진단용).
struct WallFit
{
    std::string name;
    bool matched{false};
    double dist_residual_m{0.0};   // d_pred − d_meas (해 적용 후)
    double angle_residual_rad{0.0};
    double seg_rms_m{0.0};
    int seg_points{0};
};

struct LocalizeResult
{
    Status status{Status::LOST};
    Pose2D T_station_base;  // OK/DEGRADED 일 때만 유효
    std::vector<WallFit> wall_fits;
    std::string reason;  // LOST 사유 코드: no_segments | insufficient_matches |
                         // degenerate_normals | residual_gate | jump_gate
    int iterations{0};
    int num_segments{0};
    double normal_spread{0.0};
};

// 파이프라인 파사드. 스캔 1회분 → 자세 1건. 추적 상태(직전 해)를 내부에 유지한다.
class WallLocalizer
{
  public:
    // T_base_lidar: base_link 내 라이다 장착 자세. initial_T_station_base: 스테이션 내
    // 로봇 초기 추정(대응 게이트 시드 + 기준 벽 법선 정향 기준).
    WallLocalizer(const std::vector<WallRef> &walls, const WallLocalizerParams &params,
                  const Pose2D &T_base_lidar, const Pose2D &initial_T_station_base);

    // 스캔 1회분 처리. ranges_m[i] 의 빔각 = angle_min_rad + i·angle_inc_rad.
    LocalizeResult update(const std::vector<float> &ranges_m, double angle_min_rad,
                          double angle_inc_rad);

    // 추적 초기화 — 이후 첫 update 는 이 추정을 대응 시드로 쓴다(점프 게이트도 재무장).
    void reset(const Pose2D &T_station_base_guess);

    const Pose2D &lastPose() const
    {
        return last_T_station_base_;
    }
    bool hasFix() const
    {
        return has_fix_;
    }

  private:
    // 기각 1회 누적. 연속 기각이 한도를 넘으면 추적을 버리고 초기 추정으로 복귀한다.
    void registerReject();

    std::vector<OrientedWall> oriented_walls_;
    WallLocalizerParams params_;
    Pose2D T_base_lidar_;
    Pose2D initial_T_station_base_;
    Pose2D last_T_station_base_;
    bool has_fix_{false};
    int consecutive_rejects_{0};
};

}  // namespace wall_localizer_core

#endif  // WALL_LOCALIZER_CORE__WALL_LOCALIZER_HPP_
