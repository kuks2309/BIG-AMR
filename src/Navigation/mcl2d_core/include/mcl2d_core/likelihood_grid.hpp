// 우도장(likelihood field) 격자맵.
// Seer QuadGridSearchMap 의 m_gauss_grid_pdf_table(uint8 0~255) 역할을 재현:
// 각 셀에 "가장 가까운 장애물까지 거리의 가우시안 PDF"를 0~255 로 양자화 저장.
// 근거: getPostProbBase @0x38b9a0 (movzbl PDF 룩업 + /255 정규화).
#ifndef MCL2D_CORE_LIKELIHOOD_GRID_HPP
#define MCL2D_CORE_LIKELIHOOD_GRID_HPP

#include <cstdint>
#include <vector>

namespace mcl2d
{

class LikelihoodGrid
{
  public:
    LikelihoodGrid() = default;

    // 점유 점군(장애물 좌표, m)으로부터 우도장 구축.
    //  resolution: 셀 크기(m), sigma: 가우시안 표준편차(m), max_dist: PDF 계산 최대거리(m)
    void build(const std::vector<std::pair<double, double>> &obstacles, double resolution, double sigma,
               double max_dist);

    // 월드좌표(x,y,m)의 PDF 값(0~255). 맵 밖이면 0.
    std::uint8_t probAt(double x, double y) const;

    bool empty() const
    {
        return data_.empty();
    }
    double resolution() const
    {
        return resolution_;
    }

  private:
    inline bool worldToGrid(double x, double y, int &gx, int &gy) const
    {
        gx = static_cast<int>((x - origin_x_) / resolution_);
        gy = static_cast<int>((y - origin_y_) / resolution_);
        return gx >= 0 && gy >= 0 && gx < width_ && gy < height_;
    }

    double resolution_ = 0.05;
    double origin_x_ = 0.0;
    double origin_y_ = 0.0;
    int width_ = 0;
    int height_ = 0;
    std::vector<std::uint8_t> data_; // row-major, width_*height_
};

} // namespace mcl2d

#endif // MCL2D_CORE_LIKELIHOOD_GRID_HPP
