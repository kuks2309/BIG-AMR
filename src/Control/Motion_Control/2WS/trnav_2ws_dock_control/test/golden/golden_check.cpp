// 골든 대조 — 정본에서 뽑은 golden.tsv 를 읽어 이식 코어의 출력과 비교한다.
//
// ROS 를 링크하지 않는다(⟦CI:dock-no-ros⟧ 의 실물 증명) — g++ 한 줄로 빌드된다:
//   g++ -std=c++17 -I include src/dock_core.cpp test/golden/golden_check.cpp -o /tmp/golden_check
//
// TSV 1행 = `이름 <TAB> 입력들 <TAB> | <TAB> 기대출력들`.
// e_prev / px_prev 의 `nan` 은 정본의 `None`(첫 cycle) 을 뜻하며 nullptr 로 넘긴다.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace
{

using dock_control::PidGains;
using dock_control::PidLimits;
using dock_control::PidState;

double g_tol = 1e-12;

/// 코어가 구현하지 않고 **다른 하네스에 위임**한 함수. 조용히 통과시키지 않고 별도로 센다 —
/// `ik_parity_check` 가 실제 `QdDualSteerIK` 로 이 행들을 대조한다(ADR-IK).
/// 위임은 «검증 면제» 가 아니라 «검증 주체가 다름» 이다. 두 하네스를 **둘 다** 돌려야 한다.
bool isDelegated(const std::string &name)
{
    return name == "orbitWheelCmd" || name == "fwdWheelCmd";
}

struct Row
{
    std::string name;
    std::vector<double> in;
    std::vector<double> want;
    int lineno{0};
};

/// 상대오차 비교. 기대값이 0 근처면 절대오차로 떨어진다.
bool close(double got, double want)
{
    if (std::isnan(got) && std::isnan(want)) { return true; }
    const double d = std::abs(got - want);
    const double scale = std::max(std::abs(want), 1.0);
    return d <= g_tol * scale;
}

/// `nan` 센티널을 정본의 None(nullptr) 으로 되돌린다.
const double *optArg(const double &v)
{
    return std::isnan(v) ? nullptr : &v;
}

/// 한 행을 실행해 이식본 출력을 만든다. 미지의 이름이면 빈 벡터.
std::vector<double> run(const Row &r)
{
    const std::vector<double> &i = r.in;
    if (r.name == "wrapPm180") { return {dock_control::wrapPm180(i[0])}; }
    if (r.name == "wrapMod180") { return {dock_control::wrapMod180(i[0])}; }

    if (r.name == "distPidStep")
    {
        // in: e, e_prev(nan=None), d_raw, dt, i0, kp, ki, kd, cap, i_band, i_clamp, lpf_a
        PidState st{i[4], 0.0};
        const PidGains g{i[5], i[6], i[7]};
        const PidLimits lim{i[9], i[10], i[11]};
        const auto o = dock_control::distPidStep(i[0], optArg(i[1]), i[2], i[3], st, g, i[8], lim);
        return {o.u, st.i_term, st.d_filt, o.u_p, o.u_d};
    }
    if (r.name == "phase4Vcap") { return {dock_control::phase4Vcap(i[0], i[1], i[2], i[3])}; }
    if (r.name == "dockLineYawError") { return {dock_control::dockLineYawError(i[0])}; }
    if (r.name == "imuAccumStep")
    {
        // 상태를 입력으로 복원해 1스텝만 실행한다 — 골든이 스텝 단위로 기록돼 있다.
        dock_control::ImuAccum st;
        st.cum_deg = i[0];
        st.prev_deg = i[1];
        st.have_prev = (i[2] != 0.0);
        dock_control::imuAccumStep(st, i[3]);
        return {st.cum_deg, st.prev_deg, st.have_prev ? 1.0 : 0.0};
    }
    if (r.name == "imuRunaway")
    {
        dock_control::ImuAccum st;
        st.cum_deg = i[0];
        return {dock_control::imuRunaway(st, i[1]) ? 1.0 : 0.0};
    }
    if (r.name == "orbitOvershoot")
    {
        return {dock_control::orbitOvershoot(i[0], i[1], i[2], i[3]) ? 1.0 : 0.0};
    }
    if (r.name == "computeOrbitCenter")
    {
        const auto o = dock_control::computeOrbitCenter(i[0], i[1], i[2], i[3]);
        return {o.has_value() ? 1.0 : 0.0, o.value_or(0.0)};
    }
    if (r.name == "composePhase4Wheels")
    {
        const auto c = dock_control::composePhase4Wheels(i[0], i[1], i[2], i[3], i[4]);
        return {c.vf, c.af, c.vr, c.ar};
    }
    if (r.name == "returnHomeDone")
    {
        return {dock_control::returnHomeDone(i[0], i[1]) ? 1.0 : 0.0};
    }
    if (r.name == "returnHomeAbort")
    {
        dock_control::HomeAbortInput in;
        in.obs_fresh = (i[0] != 0.0);
        in.has_lateral = (i[1] != 0.0);
        in.has_range = (i[2] != 0.0);
        in.err_px = i[3];
        in.fov_edge_px = i[4];
        in.marker_lost_elapsed_s = i[5];
        in.marker_grace_s = i[6];
        in.lidar_wait_elapsed_s = i[7];
        in.lidar_wait_limit_s = i[8];
        in.elapsed_s = i[9];
        in.timeout_s = i[10];
        return {static_cast<double>(static_cast<int>(dock_control::returnHomeAbort(in)))};
    }
    if (r.name == "homeErrPxTarget")
    {
        return {dock_control::homeErrPxTarget(i[0], i[1], i[2])};
    }
    if (r.name == "phase4Delta")
    {
        // in: err_px, e_d, approach_sign, px_prev(nan=None), dt, kp, ki, kd, dmax,
        //     i_band, i_clamp, lpf_a
        PidState st{0.0, 0.0};
        const PidGains g{i[5], i[6], i[7]};
        const PidLimits lim{i[9], i[10], i[11]};
        double e_px = 0.0;
        const double d = dock_control::phase4Delta(i[0], i[1], i[2], optArg(i[3]), i[4],
                                                   st, g, i[8], lim, &e_px);
        return {d, e_px, st.i_term, st.d_filt};
    }
    return {};
}

}  // namespace

int main(int argc, char **argv)
{
    const std::string path = (argc > 1) ? argv[1] : "test/golden/golden.tsv";
    if (argc > 2) { g_tol = std::stod(argv[2]); }

    std::ifstream fh(path);
    if (!fh)
    {
        std::cerr << "골든 파일 없음: " << path << " — gen_golden.py 를 먼저 실행하십시오\n";
        return 2;
    }

    std::string line;
    int lineno = 0, total = 0, fail = 0, unknown = 0, delegated = 0;
    std::vector<std::string> unknown_names;
    while (std::getline(fh, line))
    {
        ++lineno;
        if (line.empty() || line[0] == '#') { continue; }

        Row r;
        r.lineno = lineno;
        std::istringstream ss(line);
        std::string tok;
        bool after_bar = false;
        while (std::getline(ss, tok, '\t'))
        {
            if (r.name.empty()) { r.name = tok; continue; }
            if (tok == "|") { after_bar = true; continue; }
            (after_bar ? r.want : r.in).push_back(std::stod(tok));
        }

        if (isDelegated(r.name)) { ++delegated; continue; }

        const std::vector<double> got = run(r);
        if (got.empty())
        {
            ++unknown;
            if (unknown_names.empty() || unknown_names.back() != r.name)
            {
                unknown_names.push_back(r.name);
            }
            continue;
        }
        ++total;

        bool ok = (got.size() == r.want.size());
        for (size_t k = 0; ok && k < got.size(); ++k) { ok = close(got[k], r.want[k]); }
        if (!ok)
        {
            if (fail < 10)
            {
                std::printf("불일치 [%s] golden.tsv:%d\n", r.name.c_str(), r.lineno);
                for (size_t k = 0; k < r.want.size(); ++k)
                {
                    const double g = (k < got.size()) ? got[k] : NAN;
                    std::printf("   out[%zu] 이식=%.17g  정본=%.17g  차=%.3g\n",
                                k, g, r.want[k], std::abs(g - r.want[k]));
                }
            }
            ++fail;
        }
    }

    std::printf("골든 대조: %d건 중 %d 불일치 (허용 상대오차 %g)\n", total, fail, g_tol);
    if (delegated > 0)
    {
        std::printf("  위임 %d건 (orbitWheelCmd·fwdWheelCmd) — **ik_parity_check 를 반드시 함께 실행**\n",
                    delegated);
    }
    if (unknown > 0)
    {
        std::printf("⚠ 미구현 %d건 — ", unknown);
        for (const auto &n : unknown_names) { std::printf("%s ", n.c_str()); }
        std::printf("\n   (구현 전 함수가 골든에만 있는 상태 — 이식 미완으로 판정)\n");
    }
    return (fail == 0 && unknown == 0) ? 0 : 1;
}
