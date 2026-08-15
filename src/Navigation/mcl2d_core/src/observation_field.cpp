#include "mcl2d_core/observation_field.hpp"

#include <cmath>

namespace mcl2d
{
namespace
{

// 원본 rbk::foundation::utils 각도 헬퍼 (libfoundation.so 디스어셈블 확정; π=M_PI 실측).  comment-check: ignore
inline double deg2rad(double deg)
{
    return deg * M_PI / 180.0;
}
inline double rad2deg(double rad)
{
    return rad * 180.0 / M_PI;
}
// Normalize: (-π, π] 로 랩. (원본 Normalize @libfoundation+0x18750 재현.)
inline double normalize(double a)
{
    const double P = M_PI;
    if (a > -P && a <= P)
        return a;
    double k = std::floor(a / (2.0 * P));
    double r = a - 2.0 * P * k;
    if (r > P)
        r -= 2.0 * P;
    return r;
}

} // namespace

long ObservationField::stampCell(double coord_mm) const
{
    return static_cast<long>(std::floor(coord_mm / static_cast<double>(grid_size_)));
}

void ObservationField::build(const std::vector<std::pair<double, double>> &obstacles_m,
                             const std::vector<std::pair<double, double>> &reflectors_m, const ObsFieldParams &p)
{
    grid_size_ = p.grid_size_mm;
    quad_resolution_mm_ = p.quad_resolution_mm;
    subcells_per_quad_ = p.quad_resolution_mm / p.grid_size_mm;
    gaussein_ = p.gaussein;
    closer_mm_ = p.laser_closer_dist_m * 1000.0;
    far_mm_ = p.laser_far_dist_m * 1000.0;
    search_ = p.search;

    // ── 가우시안 PDF 테이블: gauss[i] = (uint8)(255*exp(-i/gaussein^2)), i∈[0,25501) ──
    const double g2 = gaussein_ * gaussein_;
    gauss_.resize(25501);
    for (int i = 0; i < 25501; ++i)
        gauss_[i] = static_cast<std::uint8_t>(255.0 * std::exp(-static_cast<double>(i) / g2));

    // ── sin/cos LUT: table[i] = sinf/cosf((float)Deg2Rad(i/100 - 180)), i∈[0,36000) ──
    sin_.resize(36000);
    cos_.resize(36000);
    for (int i = 0; i < 36000; ++i)
    {
        double deg = static_cast<double>(i) / 100.0 - 180.0;
        double rad = deg2rad(deg);
        sin_[i] = std::sin(static_cast<float>(rad)); // sinf
        cos_[i] = std::cos(static_cast<float>(rad)); // cosf
    }

    // ── 점집합(mm) = 장애물(×1000) + 반사판(원시값, 무변환) ──
    //   원본 initialize: normal_pos_list 는 mm 로 로드, rssi_pos_list 는 원시값 그대로 append.
    std::vector<std::pair<double, double>> pts;
    pts.reserve(obstacles_m.size() + reflectors_m.size());
    for (const auto &o : obstacles_m)
        pts.emplace_back(o.first * 1000.0, o.second * 1000.0);
    for (const auto &r : reflectors_m)
        pts.emplace_back(r.first, r.second); // 원시값 (원본 rssi 무변환)

    if (pts.empty())
    {
        fld_.clear();
        marked_.clear();
        W_ = H_ = qwidth_ = qheight_ = 0;
        return;
    }

    // ── 거리장 스탬프: 셀=floor(coord/grid_size)[double], 창[-search,search-1]^2, 값=min(dx^2+dy^2), 초기 255 ──
    minx_ = miny_ = (1L << 60);
    long maxx = -(1L << 60), maxy = -(1L << 60);
    std::vector<std::pair<long, long>> oc;
    oc.reserve(pts.size());
    for (const auto &pt : pts)
    {
        long cx = stampCell(pt.first), cy = stampCell(pt.second);
        oc.emplace_back(cx, cy);
        minx_ = std::min(minx_, cx);
        maxx = std::max(maxx, cx);
        miny_ = std::min(miny_, cy);
        maxy = std::max(maxy, cy);
    }
    const int R = search_;
    W_ = maxx - minx_ + 2 * R + 1;
    H_ = maxy - miny_ + 2 * R + 1;
    fld_.assign(static_cast<std::size_t>(W_) * H_, 255);
    for (const auto &c : oc)
        for (int dy = -R; dy < R; ++dy) // [-search, search-1]
            for (int dx = -R; dx < R; ++dx)
            {
                int sq = dx * dx + dy * dy;
                std::size_t ix =
                    static_cast<std::size_t>(c.first + dx - minx_ + R) + static_cast<std::size_t>(c.second + dy - miny_ + R) * W_;
                if (sq < fld_[ix])
                    fld_[ix] = static_cast<std::uint8_t>(sq);
            }

    // ── 마크 quad: 점 포함 quad + 축방향 이웃(점 서브셀 ±search 가 이웃 quad 도달 시) ──
    //   원본 quad_map_vec_[]!=-1 와 비트 일치(10318/10318 확인).
    //   quad 경계 = floor((coord±margin)·(1/quad_res)), 스칼라는 double(원본 region 계산과 일치·검증).
    const double qscale_d = 1.0 / static_cast<double>(quad_resolution_mm_);
    const double subcells_per_quad = static_cast<double>(subcells_per_quad_); // 50
    double mnx = 1e18, mny = 1e18, mxx = -1e18, mxy = -1e18;
    for (const auto &pt : pts)
    {
        mnx = std::min(mnx, pt.first);
        mxx = std::max(mxx, pt.first);
        mny = std::min(mny, pt.second);
        mxy = std::max(mxy, pt.second);
    }
    qminx_ = static_cast<int>(std::floor((mnx - p.region_margin_mm) * qscale_d));
    qminy_ = static_cast<int>(std::floor((mny - p.region_margin_mm) * qscale_d));
    qwidth_ = static_cast<int>(std::floor((mxx + p.region_margin_mm) * qscale_d)) - qminx_ + 1;
    qheight_ = static_cast<int>(std::floor((mxy + p.region_margin_mm) * qscale_d)) - qminy_ + 1;
    marked_.assign(static_cast<std::size_t>(qwidth_) * qheight_, 0);
    auto mark = [&](int qx, int qy) {
        int cx = qx - qminx_, cy = qy - qminy_;
        if (cx >= 0 && cx < qwidth_ && cy >= 0 && cy < qheight_)
            marked_[static_cast<std::size_t>(cy) * qwidth_ + cx] = 1;
    };
    for (const auto &pt : pts)
    {
        double fx = pt.first / static_cast<double>(grid_size_), fy = pt.second / static_cast<double>(grid_size_);
        int pqx = static_cast<int>(std::floor(fx / subcells_per_quad));
        int pqy = static_cast<int>(std::floor(fy / subcells_per_quad));
        mark(pqx, pqy);
        int xm = static_cast<int>(std::floor((fx - R) / subcells_per_quad));
        int xp = static_cast<int>(std::floor((fx + R) / subcells_per_quad));
        int ym = static_cast<int>(std::floor((fy - R) / subcells_per_quad));
        int yp = static_cast<int>(std::floor((fy + R) / subcells_per_quad));
        if (xm != pqx)
            mark(xm, pqy);
        if (xp != pqx)
            mark(xp, pqy);
        if (ym != pqy)
            mark(pqx, ym);
        if (yp != pqy)
            mark(pqx, yp);
    }
}

int ObservationField::distByte(double wx_mm, double wy_mm) const
{
    if (fld_.empty())
        return -1;
    // qscale = float(1/quad_resolution). 원본 m_quad_scale 는 float(실측) → 반드시 float 정밀도.
    const float qscale = 1.0f / static_cast<float>(quad_resolution_mm_);
    const int nsub = subcells_per_quad_; // 50
    double qfx = static_cast<double>(qscale) * wx_mm, qfy = static_cast<double>(qscale) * wy_mm;
    int qx = static_cast<int>(std::floor(qfx)), qy = static_cast<int>(std::floor(qfy));
    if (qx - qminx_ < 0 || qx - qminx_ >= qwidth_ || qy - qminy_ < 0 || qy - qminy_ >= qheight_)
        return -1; // checkOverBorder
    if (marked_[static_cast<std::size_t>(qy - qminy_) * qwidth_ + (qx - qminx_)] == 0)
        return -1; // quad_map == -1
    int sx = static_cast<int>(std::floor((qfx - static_cast<double>(qx)) * static_cast<double>(nsub)));
    int sy = static_cast<int>(std::floor((qfy - static_cast<double>(qy)) * static_cast<double>(nsub)));
    if (sx < 0 || sx >= nsub || sy < 0 || sy >= nsub)
        return -1;
    long cx = static_cast<long>(qx) * nsub + sx, cy = static_cast<long>(qy) * nsub + sy;
    long fx = cx - minx_ + search_, fy = cy - miny_ + search_;
    if (fx < 0 || fx >= W_ || fy < 0 || fy >= H_)
        return 255;
    return fld_[static_cast<std::size_t>(fx) + static_cast<std::size_t>(fy) * W_];
}

void ObservationField::setScan(std::vector<LaserScanGroup> groups)
{
    groups_ = std::move(groups);
    wtab_.assign(groups_.size(), {});
    valid_beam_ = 0;
    for (std::size_t g = 0; g < groups_.size(); ++g)
    {
        const auto &beams = groups_[g].beams;
        wtab_[g].assign(beams.size(), 0);
        for (std::size_t k = 0; k < beams.size(); ++k)
        {
            if (!beams[k].is_valid)
                continue;
            int di = static_cast<int>(beams[k].dist_mm);
            if (!(closer_mm_ < static_cast<double>(di) && static_cast<double>(di) < far_mm_))
                continue;
            int idx = static_cast<int>((beams[k].angle_deg + 180.0) / 0.01);
            if (idx < 0 || idx >= 36000)
                continue;
            wtab_[g][k] = 1;
            ++valid_beam_;
        }
    }
}

void ObservationField::setScan(std::vector<PolarBeam> beams)
{
    std::vector<LaserScanGroup> g(1);
    g[0].beams = std::move(beams);
    setScan(std::move(g));
}

double ObservationField::getPostProb(double px_mm, double py_mm, double ptheta_rad) const
{
    if (cos_.empty() || valid_beam_ == 0) // 미빌드 또는 유효빔 0 → 1e-6 (원본 floor)
        return 1e-6;

    double sum = 0.0;
    for (std::size_t g = 0; g < groups_.size(); ++g)
    {
        const auto &beams = groups_[g].beams;
        const auto &wt = wtab_[g];
        // 누적기 = pose.xy + laser mount(mm) 를 pose.theta 로 회전. (mount=0 이면 pose 그대로.)
        const double mount_lx = groups_[g].mount_lx_mm, mount_ly = groups_[g].mount_ly_mm;
        double mrange = std::sqrt(mount_lx * mount_lx + mount_ly * mount_ly);
        double mang = std::atan2(mount_ly, mount_lx) + ptheta_rad;
        double accx = px_mm + mrange * std::cos(mang);
        double accy = py_mm + mrange * std::sin(mang);

        for (std::size_t k = 0; k < beams.size(); ++k)
        {
            double a = normalize(deg2rad(beams[k].angle_deg) + ptheta_rad);
            double world_ang = rad2deg(a);
            int idx = static_cast<int>((world_ang + 180.0) * 100.0);
            // normalize 는 (-π,π] 라 world_ang==180.0 일 때 idx==36000 (LUT 크기 36000, 경계밖).
            //   원본은 이때 인접 테이블(cos[0]/gauss[0]-as-float=-2.5e33)을 읽어 끝점이 지도 밖 → distByte 스킵(기여 0).
            //   → idx>=36000 스킵은 원본과 동일 결과(기여 0)이자 메모리 안전. (실측: -180° beam·θ=0 에서만 발생.)
            if (idx < 0 || idx >= 36000)
                continue;
            double ex = accx + beams[k].dist_mm * static_cast<double>(cos_[idx]);
            double ey = accy + beams[k].dist_mm * static_cast<double>(sin_[idx]);
            int dd = distByte(ex, ey);
            if (dd < 0)
                continue; // 미마크 quad/경계/서브셀밖 → 미기여
            int index = grid_size_ * grid_size_ * dd; // 100*d
            if (index >= 25501)
                continue;
            sum += static_cast<double>(gauss_[index]) * static_cast<double>(wt[k]);
        }
    }
    return sum / static_cast<double>(valid_beam_) / 255.0;
}

} // namespace mcl2d
