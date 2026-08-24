// 원본 libOdoCalculator.so 의 MultiSteersOdometer 를 직접 구동해 수치를 뽑는다.
//
// 플러그인 프레임워크는 재현하지 않는다 — dlopen + dlsym 으로 심볼을 직접 부른다.
// 객체는 DWARF 가 준 크기(424 B)로 잡고 원본 생성자를 호출한다.
// 구조체는 원본 레이아웃을 그대로 미러링한다(같은 libstdc++ new ABI).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <map>
#include <string>
#include <vector>

struct MotorParam {
    std::string name;                 // 0
    double x, y, yaw;                 // 32, 40, 48
    std::uint32_t canID, encoderLine; // 56, 60
    std::string func;                 // 64
    double wheelRadius, reductionRatio, steerOffset, maxAngle, minAngle;
    double cpwheelRadius, cpx, cpy, cpyaw, cpsteerOffset; // 136..168
};
struct MotorVitalInfo {
    bool flagSet;             // 0
    std::uint64_t t_nsec;     // 8
    bool stop;                // 16
    double speed;             // 24
    double position;          // 32
    std::int32_t encoder;     // 40
    double v_enc;             // 48
    double dpos;              // 56
};
struct EigenMat { double *data; long rows; long cols; }; // Eigen::MatrixXd

static const char *SO = "/media/amap/6ab6980d-f090-4387-8753-a2251e75651d"
                        "/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so";
// DWARF 실측 오프셋
enum : int {
    OFF_FLAG_FIRST = 11, OFF_FLAG_DEBUG = 12, OFF_FLAG_CUM = 13, OFF_FLAG_CONSIST = 14,
    OFF_MAP_PARAM = 16, OFF_CUR_VITAL = 64, OFF_OUTPUT = 200,
    OFF_THRES = 320, OFF_PAIR = 328, OFF_A = 376, OFF_APLUS = 400, OBJ_SIZE = 424
};
struct Output { // OdometerOutput, 원본 offset 200~
    std::uint64_t t; bool stop; double vx, vy, vw, dx, dy, dyaw, x, y, yaw;
};

template <typename F> static F sym(void *h, const char *n) {
    void *p = dlsym(h, n);
    if (!p) { std::fprintf(stderr, "dlsym 실패: %s\n", n); std::exit(2); }
    return reinterpret_cast<F>(p);
}

int main(int argc, char **argv) {
    void *h = dlopen(SO, RTLD_NOW | RTLD_LOCAL);
    if (!h) { std::fprintf(stderr, "dlopen 실패: %s\n", dlerror()); return 1; }

    auto ctor       = sym<void (*)(void *)>(h, "_ZN19MultiSteersOdometerC1Ev");
    auto calOdoCoef = sym<void (*)(void *)>(h, "_ZN19MultiSteersOdometer10CalOdoCoefEv");
    auto calSpeed   = sym<void (*)(void *)>(h, "_ZN19MultiSteersOdometer8CalSpeedEv");
    auto caldPose   = sym<void (*)(void *)>(h, "_ZN19MultiSteersOdometer8CaldPoseEv");
    auto calPose    = sym<void (*)(void *)>(h, "_ZN16AbstractOdometer7CalPoseEv");
    auto checkModel = sym<int (*)(void *)>(h, "_ZN19MultiSteersOdometer15CheckModelParamEv");

    alignas(16) static unsigned char buf[OBJ_SIZE * 2];
    std::memset(buf, 0, sizeof buf);
    ctor(buf);

    auto *thres = reinterpret_cast<double *>(buf + OFF_THRES);
    std::printf("[M1] 생성 후 thresConsistent = %.17g\n", *thres);

    // 기하 주입 — 생성자가 이미 map 을 구성해 두었으므로 참조로 잡아 넣는다.
    auto &mp = *reinterpret_cast<std::map<std::string, MotorParam> *>(buf + OFF_MAP_PARAM);
    struct W { const char *n; double x, y, cpx, cpy; };
    // 인자: [이름 x y cpx cpy] 반복. 없으면 Foil_A082 실측 기하.
    std::vector<W> wheels;
    if (argc >= 11) {
        for (int i = 1; i + 4 < argc; i += 5)
            wheels.push_back({argv[i], atof(argv[i+1]), atof(argv[i+2]),
                              atof(argv[i+3]), atof(argv[i+4])});
    } else {
        wheels = {{"front", 0.6039, 0.0, 0.0, 0.0}, {"rear", -0.5961, 0.0, 0.0, 0.0}};
    }
    for (const auto &w : wheels) {
        MotorParam p{};
        p.name = w.n; p.func = "steer";
        p.x = w.x; p.y = w.y; p.cpx = w.cpx; p.cpy = w.cpy;
        p.wheelRadius = 0.125; p.reductionRatio = 32.0;
        mp[p.name] = p;
    }
    std::printf("[M1] mapMotorParam 크기 = %zu\n", mp.size());

    // 파생 클래스는 휠 수를 offset 328 의 문자열 맵에서 가져온다(0x170 = 그 맵의 node_count).
    //   조향↔주행 모터 짝 맵으로 보이며, 여기서는 자기 자신으로 짝지어 넣는다.
    auto &pair = *reinterpret_cast<std::map<std::string, std::string> *>(buf + OFF_PAIR);
    for (const auto &w : wheels)
        pair[w.n] = w.n;
    std::printf("[M1] 짝 맵 크기 = %zu\n", pair.size());

    *(buf + OFF_FLAG_FIRST) = 1;
    *(buf + OFF_FLAG_CUM) = 1;
    *(buf + OFF_FLAG_DEBUG) = 0;

    // 원본은 파라미터 검증 전에는 계수 계산을 거부한다(flagModelParamCheck, offset 9).
    //   플래그를 손으로 세우지 않고 원본 검증 함수를 태운다.
    const int chk = checkModel(buf);
    std::printf("[M1] CheckModelParam -> %d · flagModelFileRead=%d flagModelParamCheck=%d\n",
                chk, (int)buf[8], (int)buf[9]);
    if (!buf[9]) {
        // 검증이 서지 않으면 그 이유를 보고하고, 플래그를 세워 계수 경로만 따로 확인한다.
        std::printf("[M1] 검증 미통과 — 플래그를 직접 세워 계수 경로를 확인한다\n");
        buf[8] = 1; buf[9] = 1;
    }
    calOdoCoef(buf);
    auto *A = reinterpret_cast<EigenMat *>(buf + OFF_A);
    auto *Ap = reinterpret_cast<EigenMat *>(buf + OFF_APLUS);
    std::printf("[M2] A = %ldx%ld · Aplus = %ldx%ld\n", A->rows, A->cols, Ap->rows, Ap->cols);
    if (A->data && A->rows > 0) {
        std::printf("[M2] A (열 우선):\n");
        for (long r = 0; r < A->rows; ++r) {
            std::printf("     ");
            for (long c = 0; c < A->cols; ++c)
                std::printf("%24.17g", A->data[c * A->rows + r]);
            std::printf("\n");
        }
    }
    if (Ap->data && Ap->rows > 0) {
        std::printf("[M2] Aplus (열 우선):\n");
        for (long r = 0; r < Ap->rows; ++r) {
            std::printf("     ");
            for (long c = 0; c < Ap->cols; ++c)
                std::printf("%24.17g", Ap->data[c * Ap->rows + r]);
            std::printf("\n");
        }
    }
    // ── 시나리오 구동 ────────────────────────────────────────────────────────
    // 같은 (dpos, position) 을 양쪽에 먹이고 출력을 %.17g 로 찍는다. 반올림하면 대조가 무의미하다.
    auto &cv = *reinterpret_cast<std::map<std::string, MotorVitalInfo> *>(buf + OFF_CUR_VITAL);
    auto *out = reinterpret_cast<Output *>(buf + OFF_OUTPUT);

    struct Scene { const char *name; double d0, a0, d1, a1; };
    const Scene scenes[] = {
        {"straight", 0.10, 0.0, 0.10, 0.0},
        {"spin", 0.06039, 1.5707963267948966, -0.05961, 1.5707963267948966},
        {"arc", 0.20, 0.15, 0.20, -0.15},
        {"mixed", 0.037, 0.4, -0.021, -0.9},
        {"tiny", 1e-6, 0.001, -1e-6, -0.001},
    };
    std::printf("[M3] 시나리오 구동 (누적 자세는 연속)\n");
    for (const auto &sc : scenes) {
        double d[2] = {sc.d0, sc.d1}, a[2] = {sc.a0, sc.a1};
        for (std::size_t i = 0; i < wheels.size() && i < 2; ++i) {
            MotorVitalInfo v{};
            v.flagSet = true;
            v.position = a[i];
            v.dpos = d[i];
            v.v_enc = d[i] * 10.0; // 속도 경로용 — 같은 값을 우리 쪽에도 준다
            cv[wheels[i].n] = v;
        }
        calSpeed(buf);
        std::printf("SPEED %-9s vx=%.17g vy=%.17g vw=%.17g consistent=%d\n",
                    sc.name, out->vx, out->vy, out->vw, (int)buf[OFF_FLAG_CONSIST]);
        caldPose(buf);
        std::printf("DPOSE %-9s dx=%.17g dy=%.17g dyaw=%.17g\n",
                    sc.name, out->dx, out->dy, out->dyaw);
        calPose(buf);
        std::printf("POSE  %-9s x=%.17g y=%.17g yaw=%.17g\n",
                    sc.name, out->x, out->y, out->yaw);
    }
    // ── 잔차 역추출 ──────────────────────────────────────────────────────────
    // 원본은 잔차 값을 노출하지 않는다. 그러나 판정 플래그(offset 14)는 노출하고
    //   판정은 `잔차 <= thresConsistent` 다. 임계를 이분 탐색하면 그 경계가 곧 잔차다.
    std::printf("[M4] 잔차 역추출 (임계 이분 탐색 100회)\n");
    for (const auto &sc : scenes) {
        double d[2] = {sc.d0, sc.d1}, a[2] = {sc.a0, sc.a1};
        for (std::size_t i = 0; i < wheels.size() && i < 2; ++i) {
            MotorVitalInfo v{};
            v.flagSet = true; v.position = a[i]; v.dpos = d[i]; v.v_enc = d[i] * 10.0;
            cv[wheels[i].n] = v;
        }
        auto consistentAt = [&](double t) {
            *thres = t;
            buf[OFF_FLAG_CONSIST] = 0;
            calSpeed(buf);
            return buf[OFF_FLAG_CONSIST] != 0;
        };
        // lo: 불일치로 나오는 임계, hi: 일치로 나오는 임계
        double lo = 0.0, hi = 1.0;
        if (consistentAt(lo)) { std::printf("RESID %-9s = 0 (임계 0 에서도 일치)\n", sc.name); continue; }
        while (!consistentAt(hi) && hi < 1e12) hi *= 2.0;
        for (int k = 0; k < 100; ++k) {
            const double mid = lo + (hi - lo) * 0.5;
            if (mid == lo || mid == hi) break;
            (consistentAt(mid) ? hi : lo) = mid;
        }
        std::printf("RESID %-9s = %.17g\n", sc.name, hi);
    }
    dlclose(h);
    return 0;
}
