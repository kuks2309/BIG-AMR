#include "slam_karto_core/g2o_solver.hpp"

#include <algorithm>
#include <cmath>

#include <Eigen/Dense>
#include <g2o/core/block_solver.h>
#include <g2o/core/optimization_algorithm_levenberg.h>
#include <g2o/core/sparse_optimizer.h>
#include <g2o/types/slam2d/edge_se2.h>
#include <g2o/types/slam2d/vertex_se2.h>

#if defined(SLAM_G2O_USE_CSPARSE)
#include <g2o/solvers/csparse/linear_solver_csparse.h>
#else
#include <g2o/solvers/eigen/linear_solver_eigen.h>
#endif

namespace slam_karto_core
{

namespace
{
using BlockSolver = g2o::BlockSolverX;
#if defined(SLAM_G2O_USE_CSPARSE)
using LinearSolver = g2o::LinearSolverCSparse<BlockSolver::PoseMatrixType>; // 원본 충실
#else
using LinearSolver = g2o::LinearSolverEigen<BlockSolver::PoseMatrixType>; // 폴백
#endif

/// 공분산 역행렬 허용오차 — **원본 실측값**.
///   `0xebe10 movsd 0x10e080` (= 1e-14) → `0xebe18 call karto::Matrix3::InverseFast(Matrix3&, double)`.
///   상류 `Karto.h` 의 `Matrix3::Inverse()` 기본값(`KT_TOLERANCE`)이 아니라 이 값을 명시 전달한다.
constexpr double kCovarianceInverseTolerance = 1e-14;

} // namespace

G2OSolver::G2OSolver() : optimizer_(new g2o::SparseOptimizer())
{
    // g2o 스택: 선형해법기 → BlockSolverX → Levenberg-Marquardt.
    // g2o 2020.5.29(ros-humble-libg2o)는 unique_ptr API 다 — 원시 포인터 생성자는 컴파일되지 않는다.
    auto linear_solver = g2o::make_unique<LinearSolver>();
    // 원본 실측: `0xeb7cf movb $0x0,0x38(%r12)` — 라이브러리 기본값 true 를 명시적으로 끈다
    // (`LinearSolverCSparse()` ctor `0xec9fc movb $0x1,0x38(%rbx)` 가 기본 true 를 세운다).
    // 이걸 빼면 CSparse fill-reducing 순서 전략이 반대가 되어 소거 순서가 달라진다.
    linear_solver->setBlockOrdering(false);
    auto block_solver = g2o::make_unique<BlockSolver>(std::move(linear_solver));
    auto *algorithm = new g2o::OptimizationAlgorithmLevenberg(std::move(block_solver));
    optimizer_->setAlgorithm(algorithm);
    optimizer_->setVerbose(false); // [우리가 추가] 원본에 없음(g2o 기본값이 이미 false 라 무영향)
}

G2OSolver::~G2OSolver() = default;

void G2OSolver::setMaxIterations(int n)
{
    if (n > 0)
    {
        max_iterations_ = n;
    }
}

void G2OSolver::AddNode(karto::Vertex<karto::LocalizedRangeScan> *pVertex)
{
    if (pVertex == nullptr)
    {
        return;
    }
    karto::LocalizedRangeScan *pScan = pVertex->GetObject();
    if (pScan == nullptr)
    {
        return;
    }
    const karto::Pose2 &pose = pScan->GetCorrectedPose();

    auto *v = new g2o::VertexSE2();
    v->setId(pScan->GetUniqueId());
    v->setEstimate(g2o::SE2(pose.GetX(), pose.GetY(), pose.GetHeading()));
    if (first_node_)
    {
        v->setFixed(true); // 맵 원점 앵커 — 이게 없으면 SE(2) 게이지 자유도 3이 남는다
        first_node_ = false;
    }
    if (optimizer_->addVertex(v))
    {
        vertex_order_.push_back(v->id()); // 원본의 vector<VertexSE2*> 멤버에 대응(삽입 순서 보관)
        ++stats_.nodes_added;
        if (v->fixed())
        {
            stats_.has_fixed_node = true;
        }
    }
    else
    {
        delete v; // id 중복 등으로 거부된 경우 — 소유권이 넘어가지 않았다
    }
}

void G2OSolver::AddConstraint(karto::Edge<karto::LocalizedRangeScan> *pEdge)
{
    if (pEdge == nullptr)
    {
        return;
    }
    karto::LocalizedRangeScan *pSource = pEdge->GetSource()->GetObject();
    karto::LocalizedRangeScan *pTarget = pEdge->GetTarget()->GetObject();
    auto *pLink = dynamic_cast<karto::LinkInfo *>(pEdge->GetLabel());
    if (pSource == nullptr || pTarget == nullptr || pLink == nullptr)
    {
        ++stats_.edges_rejected;
        return;
    }

    g2o::HyperGraph::Vertex *v_src = optimizer_->vertex(pSource->GetUniqueId());
    g2o::HyperGraph::Vertex *v_dst = optimizer_->vertex(pTarget->GetUniqueId());
    if (v_src == nullptr || v_dst == nullptr)
    {
        ++stats_.edges_rejected;
        return;
    }

    const karto::Matrix3 &k_cov = pLink->GetCovariance();

    // 원본과 **같은 알고리즘**으로 역행렬을 구한다 — `karto::Matrix3::InverseFast(inv, 1e-14)`.
    //   근거: `0xebe10 movsd 0x10e080`(=1e-14) → `0xebe18 call karto::Matrix3::InverseFast@plt`.
    //   Eigen `FullPivLU` 로 바꾸면 대수적으로는 같아도 **부동소수 결과가 비트 동일하지 않다**
    //   (여인수/det 방식 vs 피벗 LU). RE 제1원칙상 원본 경로를 쓴다.
    //
    // ⚠ 특이 공분산에서의 거동도 원본을 따른다. 상류 `InverseFast` 는 여인수 행렬을 **먼저 다 쓴 뒤**
    //   `|det| <= tol` 이면 `1/det` 스케일링 없이 `false` 를 반환하고(Karto.h), 원본은 그 반환값을
    //   **검사하지 않는다**(`0xebe18` 직후 `0xebe1d movaps (%rsp),%xmm0` 로 곧장 결과를 읽는다).
    //   즉 원본은 특이 간선을 정규화 안 된 여인수 행렬과 함께 **그대로 채택**한다 — inf/NaN 이 아니다.
    //   우리도 그대로 채택하되, 몇 번 일어났는지는 계측한다(원본에 없는 관측점이지만 거동 불변).
    karto::Matrix3 k_inv;
    const bool well_conditioned = k_cov.InverseFast(k_inv, kCovarianceInverseTolerance);
    if (!well_conditioned)
    {
        ++stats_.singular_covariances;
    }

    Eigen::Matrix3d info;
    for (unsigned r = 0; r < 3; ++r)
    {
        for (unsigned c = 0; c < 3; ++c)
        {
            info(r, c) = k_inv(r, c);
        }
    }

    auto *e = new g2o::EdgeSE2();
    e->vertices()[0] = v_src;
    e->vertices()[1] = v_dst;
    const karto::Pose2 diff = pLink->GetPoseDifference();
    e->setMeasurement(g2o::SE2(diff.GetX(), diff.GetY(), diff.GetHeading()));
    e->setInformation(info);
    if (optimizer_->addEdge(e))
    {
        ++stats_.edges_added;
    }
    else
    {
        ++stats_.edges_rejected;
        delete e;
    }
}

void G2OSolver::Compute()
{
    corrections_.clear();
    if (optimizer_->vertices().size() < 2)
    {
        return; // 최적화할 그래프 부족
    }

    ++stats_.compute_calls;
    optimizer_->initializeOptimization();
    stats_.last_iterations = optimizer_->optimize(max_iterations_);

    // 원본과 같은 순서로 수집한다 — 삽입 순서(`vertex_order_`). 정렬하지 않는다.
    // 원본은 자체 벡터를 인덱스 순회하며 정점 멤버를 직접 읽는다(`0xebb2a`~`0xebb62`, sort 호출 0건).
    corrections_.reserve(vertex_order_.size());
    for (const int id : vertex_order_)
    {
        auto *v = dynamic_cast<g2o::VertexSE2 *>(optimizer_->vertex(id));
        if (v == nullptr)
        {
            continue;
        }
        const g2o::SE2 est = v->estimate();
        corrections_.emplace_back(
            id, karto::Pose2(est.translation().x(), est.translation().y(), est.rotation().angle()));
    }
}

const karto::ScanSolver::IdPoseVector &G2OSolver::GetCorrections() const
{
    return corrections_;
}

void G2OSolver::Clear()
{
    // 상류 계약: 직전 corrections 만 버린다. 그래프는 건드리지 않는다 (헤더 주석 참조).
    corrections_.clear();
}

void G2OSolver::Reset()
{
    corrections_.clear();
    optimizer_->clear();
    vertex_order_.clear();
    first_node_ = true;
    stats_ = SolverStats{};
}

} // namespace slam_karto_core
