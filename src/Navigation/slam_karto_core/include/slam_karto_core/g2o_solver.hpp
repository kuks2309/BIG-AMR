// G2OSolver — Seer SLAM 매핑 backend 어댑터 (karto::ScanSolver 구현).
//
// RE(Reverse Engineering) 근거: 원본 `libSlaMapping.so` 는 g2o 스택
//   `SparseOptimizer` + `LinearSolverCSparse<BlockSolverX::PoseMatrixType>` + `BlockSolverX`(=`<-1,-1>`)
//   + `OptimizationAlgorithmLevenberg`(LM) 를 쓴다. 첫 노드 fixed 로 맵 원점을 고정한다.
//   심볼 실측: `g2o::VertexSE2`, `g2o::EdgeSE2`, `g2o::BlockSolver<BlockSolverTraits<-1,-1>>`,
//   `g2o::LinearSolverCSparse<Eigen::MatrixXd>`, `g2o::OptimizationAlgorithmLevenberg`,
//   `g2o::csparse_extension::cs_cholsolsymb`. 로버스트 커널 심볼은 0건이었다
//   (`nm -C libSlaMapping.so | grep -ic robust` → 0) → 커널 미사용이 원본 충실.
//   리뷰: docs/code_review/seer-slam-mapping/2026-08-08.md
//
// 선형해법기: 배포 기본 = CSparse(원본 충실) + **`setBlockOrdering(false)`**(원본 실측 `0xeb7cf`).
//   SuiteSparse/`cs.h` 부재 환경은 Eigen 해법기로 폴백하는데 이건 **우리가 추가한 분기**이며 원본에 없다.
//   ⚠ 두 해법기의 산출이 수치적으로 동등한지는 **미검증**이다 — 폴백 빌드는 원본 충실이 아니다.
#ifndef SLAM_KARTO_CORE_G2O_SOLVER_HPP
#define SLAM_KARTO_CORE_G2O_SOLVER_HPP

#include <memory>
#include <vector>

#include <open_karto/Mapper.h>

#include "slam_karto_core/types.hpp"

namespace g2o
{
class SparseOptimizer;
}

namespace slam_karto_core
{

/// karto::ScanSolver 구현 — Karto MapperGraph 의 노드/제약을 g2o 포즈그래프로 최적화한다.
class G2OSolver : public karto::ScanSolver
{
  public:
    G2OSolver();
    ~G2OSolver() override;

    G2OSolver(const G2OSolver &) = delete;
    G2OSolver &operator=(const G2OSolver &) = delete;

    /// 포즈그래프 최적화 실행(LM). 반복 수 = `max_iterations_`.
    /// 정점이 2개 미만이면 아무 것도 하지 않는다(최적화할 그래프 부족).
    void Compute() override;

    /// 최적화된 `(scanId, Pose2)` 목록. 순서는 **정점 삽입 순서**(원본과 동일) — 정렬하지 않는다.
    ///   원본은 자체 `vector<VertexSE2*>` 를 인덱스 순회한다(`0xebb2a`~`0xebb62`, sort 호출 0건).
    ///   g2o `vertices()` 해시맵을 순회하면 실행마다 순서가 달라져 결정성이 깨진다.
    const karto::ScanSolver::IdPoseVector &GetCorrections() const override;

    /// Karto `Vertex<LocalizedRangeScan>` → `g2o::VertexSE2`
    /// (id = scan UniqueId, estimate = CorrectedPose). 첫 노드는 fixed — 맵 원점 앵커.
    void AddNode(karto::Vertex<karto::LocalizedRangeScan> *pVertex) override;

    /// Karto `Edge` → `g2o::EdgeSE2` (measurement = LinkInfo PoseDifference,
    /// information = Covariance 역행렬). 역행렬은 **원본과 같은 `karto::Matrix3::InverseFast(inv, 1e-14)`**
    /// 로 구하며, 특이해도 간선을 버리지 않는다(원본이 반환값을 검사하지 않는다 — `.cpp` 주석 참조).
    void AddConstraint(karto::Edge<karto::LocalizedRangeScan> *pEdge) override;

    /// 상류 계약: **직전 corrections 를 버린다. 그래프는 건드리지 않는다.**
    ///   `third_party/open_karto/src/Mapper.cpp` 의 `MapperGraph::CorrectPoses()` 가
    ///   `Compute()` → 보정 적용 → `Clear()` 를 **루프클로저마다** 호출하므로,
    ///   여기서 그래프를 비우면 매 루프클로저마다 포즈그래프가 파괴된다.
    ///   세션 재시작이 필요하면 `Reset()` 을 쓸 것.
    void Clear() override;

    /// 매핑 세션 재시작 — 그래프를 비우고 첫 노드 고정 상태로 되돌린다.
    /// `Clear()` 와 달리 Karto 가 호출하지 않는다(우리 전용).
    void Reset();

    /// LM 반복 상한. 0 이하는 무시한다.
    void setMaxIterations(int n);

    /// 최적화 계측(호출 횟수·정점/간선 수·기각 수). 시험이 "루프클로저가 실제로 돌았는지"를
    /// 단언할 수 있게 하려고 노출한다.
    const SolverStats &stats() const
    {
        return stats_;
    }

  private:
    std::unique_ptr<g2o::SparseOptimizer> optimizer_;
    karto::ScanSolver::IdPoseVector corrections_;
    /// 정점 id 를 **삽입 순서대로** 보관한다. 원본은 `std::vector<g2o::VertexSE2*>` 멤버(+0x28..0x40)를
    /// 두고 `Compute()` 에서 그 순서로 순회한다(`0xebb2a`~`0xebb62`). g2o 의 `vertices()` 는 해시맵이라
    /// 순회 순서가 실행마다 다를 수 있으므로, 원본과 같은 순서·결정성을 얻으려면 이 목록이 필요하다.
    std::vector<int> vertex_order_;
    SolverStats stats_;
    /// 원본 실측값 50 (`0xebb20 mov $0x32,%esi` → `optimize(50, false)`).
    int max_iterations_ = 50;
    bool first_node_ = true;
};

} // namespace slam_karto_core

#endif // SLAM_KARTO_CORE_G2O_SOLVER_HPP
