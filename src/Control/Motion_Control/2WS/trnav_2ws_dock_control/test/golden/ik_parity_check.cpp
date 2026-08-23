// ADR-IK 등가 검증 — 정본 orbit_wheel_cmd/fwd_wheel_cmd 와 QdDualSteerIK::computeWheel 대조.
//
// 왜 별도 하네스인가: 「소스 편입」을 결정하기 **전에** 등가를 재도출해야 한다.
// 계획서가 "200k 샘플 max diff 0.0" 이라 적어 뒀지만, 남이 쓴 수치(내가 이전에 쓴 것 포함)는
// 1차 근거가 아니다. 여기서 정본 골든과 실제 IK 구현을 직접 맞댄다.
//
// 빌드(ROS 미source):
//   g++ -std=c++17 -I <ik>/include ik_parity_check.cpp <ik>/src/qd_inverse_kinematics.cpp -o /tmp/ikp
//
// ⚠ computeWheel 은 **private** 이다 — 공개 표면은 compute(VelocityCommand)/computeSpin 뿐이다.
//   ADR-IK 의 편입 대상은 그 공개 표면이며, 바퀴별 분해는 compute() 안에서 일어난다.
#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace
{

// 정본 :88-89 ORBIT_W1/W2 (QD 기하 — 골든 벡터가 이 기하로 생성됐으므로 등가 판정에는 QD 값을 그대로 쓴다). 기하가 다르면 등가 판정이 무의미하므로
// 값이 바뀌면 여기서 즉시 드러나도록 리터럴로 두고 골든 헤더와 대조한다.
constexpr double W1X = 0.330, W1Y = 0.135;
constexpr double W2X = -0.330, W2Y = -0.135;
// steer/speed 비교에는 영향이 없다(둘은 drive_rpm 에만 쓰인다). 생성자 요구를 채우는 값.
constexpr double WHEEL_RADIUS = 0.08, GEAR_WALK = 20.0;

double g_tol = 0.0;   // 기본 = 비트 동일 요구

/// canon 의 (v, steer) 표현으로 환산 — canon 은 부호 포함 속도를, IK 는 speed+direction 을 낸다.
void wheelToCanon(const trnav::motion::two_ws::WheelOutput &w, double &v, double &steer)
{
    v = w.wheel_speed * static_cast<double>(w.direction);
    steer = w.steer_rad;
}

bool close(double a, double b)
{
    if (std::isnan(a) && std::isnan(b)) { return true; }
    const double d = std::abs(a - b);
    return d <= g_tol * std::max(std::abs(b), 1.0);
}

}  // namespace

int main(int argc, char **argv)
{
    const std::string path = (argc > 1) ? argv[1] : "test/golden/golden.tsv";
    if (argc > 2) { g_tol = std::stod(argv[2]); }

    trnav::motion::two_ws::TwoWsDualSteerIK ik(
        {{W1X, W1Y}, {W2X, W2Y}}, WHEEL_RADIUS, GEAR_WALK);

    std::ifstream fh(path);
    if (!fh) { std::fprintf(stderr, "골든 없음: %s\n", path.c_str()); return 2; }

    std::string line;
    int lineno = 0, n_orbit = 0, n_fwd = 0, bad = 0, thresh = 0;
    double worst = 0.0;
    while (std::getline(fh, line))
    {
        ++lineno;
        if (line.empty() || line[0] == '#') { continue; }
        std::istringstream ss(line);
        std::string name, tok;
        std::vector<double> in, want;
        bool bar = false;
        while (std::getline(ss, tok, '\t'))
        {
            if (name.empty()) { name = tok; continue; }
            if (tok == "|") { bar = true; continue; }
            (bar ? want : in).push_back(std::stod(tok));
        }

        double got[4];
        if (name == "orbitWheelCmd")
        {
            // 정본 :275-296 — ICR 을 C=(cx,cy) 에 놓는 body 속도(vx = cy·ω, vy = −cx·ω).
            // 바퀴별 분해(vx_i = vx − ω·y_i)는 compute() 가 그대로 수행한다(:23-28).
            const double cx = in[0], cy = in[1], om = in[2];
            const auto res = ik.compute({cy * om, -cx * om, om});
            for (int i = 0; i < 2; ++i)
            {
                wheelToCanon(res.wheels[i], got[i * 2], got[i * 2 + 1]);
            }
            ++n_orbit;
        }
        else if (name == "fwdWheelCmd")
        {
            const auto res = ik.compute({in[0], 0.0, 0.0});
            wheelToCanon(res.wheels[0], got[0], got[1]);
            got[2] = got[0];
            got[3] = got[1];
            ++n_fwd;
        }
        else { continue; }

        bool ok = true;
        double dmax = 0.0;
        for (int k = 0; k < 4; ++k)
        {
            ok = ok && close(got[k], want[k]);
            dmax = std::max(dmax, std::abs(got[k] - want[k]));
        }
        if (!ok)
        {
            // 정본에 없는 C++ 임계(spd < 1e-6 조기반환)로 인한 차이인지 분리한다.
            const bool below = (name == "fwdWheelCmd")
                                   ? std::abs(in[0]) < 1e-6
                                   : (std::abs(want[0]) < 1e-6 && std::abs(want[2]) < 1e-6);
            if (below) { ++thresh; }
            else
            {
                ++bad;
                worst = std::max(worst, dmax);
                if (bad <= 8)
                {
                    std::printf("불일치 [%s] golden.tsv:%d  in=", name.c_str(), lineno);
                    for (double v : in) { std::printf("%.17g ", v); }
                    std::printf("\n   IK  =");
                    for (int k = 0; k < 4; ++k) { std::printf(" %.17g", got[k]); }
                    std::printf("\n   정본=");
                    for (int k = 0; k < 4; ++k) { std::printf(" %.17g", want[k]); }
                    std::printf("\n");
                }
            }
        }
    }

    std::printf("ADR-IK 등가 대조: orbit %d · fwd %d (허용오차 %g)\n", n_orbit, n_fwd, g_tol);
    std::printf("  임계 밖 불일치 : %d 건", bad);
    if (bad) { std::printf("  (최대 차 %.3g)", worst); }
    std::printf("\n  |v|<1e-6 차이  : %d 건  ← 정본에 없는 C++ 조기반환(steer 0 복귀). "
                "steer-hold 계약 위반이므로 래퍼가 덮어야 한다\n", thresh);
    return bad == 0 ? 0 : 1;
}
