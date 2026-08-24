// 재구현본을 오라클과 **같은 순서·같은 입력**으로 돌려 같은 형식으로 찍는다.
#include <cstdio>
#include "seer_odom_core/multisteer_odometer.hpp"
using namespace seer_odom_core;
int main() {
    MultiSteersOdometer o;
    o.setMotorParams({{"front", 0.6039, 0.0, 0.0, 0.0}, {"rear", -0.5961, 0.0, 0.0, 0.0}});
    o.setFirstInputGot(true);
    o.setCumEncPoseMode(true);
    o.setThresConsistent(0.05); // 원본 생성자 기본값
    struct Scene { const char *name; double d0, a0, d1, a1; };
    const Scene scenes[] = {
        {"straight", 0.10, 0.0, 0.10, 0.0},
        {"spin", 0.06039, 1.5707963267948966, -0.05961, 1.5707963267948966},
        {"arc", 0.20, 0.15, 0.20, -0.15},
        {"mixed", 0.037, 0.4, -0.021, -0.9},
        {"tiny", 1e-6, 0.001, -1e-6, -0.001},
    };
    for (const auto &sc : scenes) {
        std::map<std::string, MotorVitalInfo> m;
        MotorVitalInfo f{}, r{};
        f.flag_set = true; f.position = sc.a0; f.dpos = sc.d0; f.v_enc = sc.d0 * 10.0;
        r.flag_set = true; r.position = sc.a1; r.dpos = sc.d1; r.v_enc = sc.d1 * 10.0;
        m["front"] = f; m["rear"] = r;
        o.setVitalInfo(m);
        o.calSpeed();
        std::printf("SPEED %-9s vx=%.17g vy=%.17g vw=%.17g consistent=%d\n",
                    sc.name, o.output().vx, o.output().vy, o.output().vw, (int)o.wheelConsistent());
        o.caldPose();
        std::printf("DPOSE %-9s dx=%.17g dy=%.17g dyaw=%.17g\n",
                    sc.name, o.output().dx, o.output().dy, o.output().dyaw);
        o.calPose();
        std::printf("POSE  %-9s x=%.17g y=%.17g yaw=%.17g\n",
                    sc.name, o.output().x, o.output().y, o.output().yaw);
    }
}
