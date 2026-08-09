// SLAM 매핑 I/O 타입 — Seer Message_MapLogData(입력) / Message_Map(출력) 대응.
//
// 스키마 정본: References/seer/slam_mapping/proto/message_map.proto (원본 하드 회수본, 302줄)
//   입력  Message_MapLogData{robot_odo_x=1, robot_odo_y=2, robot_odo_w=3,
//                            laser_beam_dist=4, laser_beam_angle=5, rssi=6, header=7}
//   출력  Message_Map{normal_pos_list=3, rssi_pos_list=11, ...}
// 리뷰: docs/code_review/seer-slam-mapping/2026-08-08.md
#ifndef SLAM_KARTO_CORE_TYPES_HPP
#define SLAM_KARTO_CORE_TYPES_HPP

#include <string>
#include <utility>
#include <vector>

namespace slam_karto_core
{

/// 한 시점의 로그 레코드 (Seer Message_MapLogData 대응). 각도·거리는 라이다 로컬프레임.
struct MapLogRecord
{
    double odo_x = 0.0;             ///< 오도메트리 위치 x (m)
    double odo_y = 0.0;             ///< 오도메트리 위치 y (m)
    double odo_w = 0.0;             ///< 오도메트리 방위 (rad)
    std::vector<double> beam_dist;  ///< 빔 거리 (m). 무효/무반사는 range_max 이상.
    std::vector<double> beam_angle; ///< 빔 각도 (rad, 라이다 로컬). **균일 간격 필수**(Karto 전제).
    std::vector<double> beam_rssi;  ///< 빔 반사강도 (선택; 비었으면 rssi 미산출).
};

/// 평면 포즈 (맵/월드 프레임). 스캔별 보정 포즈를 밖으로 내보내는 용도.
struct Pose2D
{
    double x = 0.0;     ///< 위치 x (m)
    double y = 0.0;     ///< 위치 y (m)
    double theta = 0.0; ///< 방위 (rad)
};

/// "스캔 식별자 없음" 표식. Karto 의 uniqueId 는 0 부터 시작하므로 음수만 안전하다.
constexpr int kNoScanId = -1;

/// `processRecord` 의 처리 결과. bool 로 뭉뚱그리면 "게이트 미달"과 "입력 불량"이 구분되지 않는다.
///   — 원본 `karto::Mapper::Process` 는 bool 만 돌려주지만, 입력 검증은 그 앞단(우리 책임)이다.
enum class ProcessResult
{
    kAdded,        ///< 스캔이 그래프에 추가됨 (이동 게이트 통과)
    kGateRejected, ///< Karto 이동 게이트 미달로 폐기 — 정상 동작
    kInvalidInput, ///< 입력 검증 실패. 사유는 `SeerSlamMapper::lastError()`
};

/// 매핑 결과 (Seer Message_Map 대응). 점군은 미터, 맵(월드) 프레임.
struct MapResult
{
    std::vector<std::pair<double, double>> normal_pos_list; ///< 장애물 점군 (보정 포즈 반영)
    std::vector<std::pair<double, double>> rssi_pos_list;   ///< 반사판 점군 (rssi 임계 초과 빔)
    double min_x = 0.0; ///< 점군 경계 (m) — .smap `header.minPos` 대응
    double min_y = 0.0;
    double max_x = 0.0;
    double max_y = 0.0;
    int num_scans = 0; ///< 그래프에 추가된 스캔(노드) 수
    bool valid = false;
};

/// 그래프 최적화 계측 — "루프클로저가 실제로 돌았는가"를 시험이 단언할 수 있게 노출한다.
///   (합계 통과 숫자로는 이것이 0 이어도 알 수 없다 — 2026-08-08 리뷰 Low #18)
struct SolverStats
{
    int compute_calls = 0;   ///< `Compute()` 호출 횟수 (= CorrectPoses 진입 횟수)
    int nodes_added = 0;     ///< 그래프에 들어간 정점 수
    int edges_added = 0;     ///< 그래프에 들어간 간선 수
    int edges_rejected = 0;  ///< 널 입력·정점 미등록 등으로 버린 간선 수
    /// 공분산이 특이해 `InverseFast` 가 false 를 돌려준 횟수. **간선은 버리지 않는다** —
    /// 원본이 반환값을 검사하지 않고 정규화 안 된 여인수 행렬을 그대로 채택하기 때문이다.
    /// 관측만 하는 계측점이며 거동에는 영향이 없다.
    int singular_covariances = 0;
    int last_iterations = 0; ///< 직전 `optimize()` 가 보고한 반복 수
    /// 맵 원점 앵커(첫 노드 fixed)가 실제로 걸렸는가. 이게 false 면 SE(2) 게이지 자유도 3이 남는다.
    /// LM 감쇠가 자유 게이지를 어느 정도 가려 결과만 봐서는 드러나지 않으므로 불변식을 직접 노출한다.
    bool has_fixed_node = false;
};

} // namespace slam_karto_core

#endif // SLAM_KARTO_CORE_TYPES_HPP
