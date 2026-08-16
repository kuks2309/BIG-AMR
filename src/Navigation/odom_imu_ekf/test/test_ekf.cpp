// 오도+IMU 융합 EKF 회귀 — 레거시 RobotPosEKF 이식분의 구조적 성질을 고정한다.
//
// 원본은 관측 잡음 자리에 초기화되지 않은 메모리를 넘기므로 **비트 대조가 성립하지 않는다.**
// 그래서 여기서는 수치 특성(게이트·기준선·증분 사용·관측 축 분리)을 검사한다.
// NDEBUG 와 무관하게 실패할 수 있도록 자체 CHECK 매크로를 쓴다.
#include <cmath>
#include <cstdio>

#include "odom_imu_ekf/ekf.hpp"

using namespace odom_imu_ekf;

static int g_fail = 0;
#define CHECK(cond, msg)                                                                                               \
    do                                                                                                                 \
    {                                                                                                                  \
        if (!(cond))                                                                                                   \
        {                                                                                                              \
            std::printf("[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);                                            \
            ++g_fail;                                                                                                  \
        }                                                                                                              \
    } while (0)

static constexpr double kDeg = M_PI / 180.0;

int main()
{
    // 1) 두 센서를 다 받기 전에는 진행하지 않는다(원본 run() 의 두 수신 플래그).
    {
        OdomImuEkf f;
        CHECK(!f.update(), "아무것도 안 받았는데 진행했다");
        f.addOdom({0, 0, 0, 0, 0, 0}, 0.0);
        CHECK(!f.update(), "IMU 없이 진행했다 — 원본은 IMU 를 필수로 기다린다");
        f.addImu(0, 0, 0);
        CHECK(f.update(), "둘 다 받았는데 진행하지 않았다");
    }

    // 2) 오도 첫 주기는 기준선만 세운다 — 그 자세가 그대로 나와야 한다.
    {
        OdomImuEkf f;
        f.addOdom({2.0, -1.0, 0, 0, 0, 0.5}, 0.0);
        f.addImu(0, 0, 0.5);
        CHECK(f.update(), "첫 주기 진행 실패");
        CHECK(std::fabs(f.pose().x - 2.0) < 1e-9 && std::fabs(f.pose().y + 1.0) < 1e-9,
              "첫 주기 기준선이 오도 자세와 다르다");
        CHECK(std::fabs(f.pose().yaw - 0.5) < 1e-9, "첫 주기 yaw 가 오도와 다르다");
        CHECK(!f.lastImuApplied(), "IMU 첫 주기인데 융합했다(기준선만 세워야 한다)");
    }

    // 2b) IMU 첫 주기는 **게이트를 넘겨도** 반영하지 않는다 — 기준선만 세운다.
    //     (2번은 게이트가 막아서 통과하므로, 첫 주기 규칙 자체를 이 항목이 고정한다.)
    {
        OdomImuEkf f;
        f.addOdom({0, 0, 0, 0, 0, 0.0}, 30.0 * kDeg); // 게이트 통과하는 회전율
        f.addImu(0, 0, 1.0);                          // 오도와 크게 다른 yaw
        CHECK(f.update(), "첫 주기 진행 실패");
        CHECK(!f.lastImuApplied(), "IMU 첫 주기인데 융합했다 — 기준선만 세워야 한다");
        CHECK(std::fabs(f.pose().yaw) < 1e-9, "첫 주기인데 IMU 가 yaw 를 끌고 갔다");
    }

    // 3) 정지·직진에서는 IMU 를 반영하지 않는다(게이트 |ω| > 1 deg/s).
    {
        OdomImuEkf f;
        f.addOdom({0, 0, 0, 0, 0, 0}, 0.0);
        f.addImu(0, 0, 0);
        f.update();
        // 오도는 직진만, IMU 는 yaw 가 크게 틀어진 값을 준다.
        f.addOdom({1.0, 0, 0, 0, 0, 0.0}, 0.5 * kDeg); // 0.5 deg/s — 게이트 미만
        f.addImu(0, 0, 1.0);
        f.update();
        CHECK(!f.lastImuApplied(), "게이트 미만인데 IMU 를 반영했다");
        CHECK(std::fabs(f.pose().yaw) < 1e-3, "IMU 를 안 써야 하는데 yaw 가 끌려갔다");
    }

    // 4) 회전 중에는 IMU 가 반영된다.
    {
        OdomImuEkf f;
        f.addOdom({0, 0, 0, 0, 0, 0}, 0.0);
        f.addImu(0, 0, 0);
        f.update();
        f.addOdom({0, 0, 0, 0, 0, 0.10}, 30.0 * kDeg); // 30 deg/s — 게이트 통과
        f.addImu(0, 0, 0.30);
        f.update();
        CHECK(f.lastImuApplied(), "게이트를 넘겼는데 IMU 를 반영하지 않았다");
        // 오도(0.10)와 IMU(0.30) 사이로 당겨져야 한다 — 어느 한쪽 그대로면 융합이 아니다.
        CHECK(f.pose().yaw > 0.10 + 1e-6 && f.pose().yaw < 0.30 - 1e-6,
              "yaw 가 두 관측 사이로 융합되지 않았다");
    }

    // 5) 오도의 **절대값 드리프트**는 자세로 전파되지 않는다 — 증분만 쓴다.
    {
        OdomImuEkf a, b;
        for (auto *f : {&a, &b})
        {
            f->addImu(0, 0, 0);
        }
        // a: 원점에서 시작해 1 m 전진. b: 1000 m 오프셋 지점에서 같은 1 m 전진.
        a.addOdom({0, 0, 0, 0, 0, 0}, 0.0);
        a.update();
        a.addOdom({1.0, 0, 0, 0, 0, 0}, 0.0);
        a.addImu(0, 0, 0);
        a.update();

        b.addOdom({1000.0, 0, 0, 0, 0, 0}, 0.0);
        b.update();
        b.addOdom({1001.0, 0, 0, 0, 0, 0}, 0.0);
        b.addImu(0, 0, 0);
        b.update();

        const double moved_a = a.pose().x - 0.0;
        const double moved_b = b.pose().x - 1000.0;
        CHECK(std::fabs(moved_a - moved_b) < 1e-6, "같은 증분인데 절대 위치에 따라 결과가 달라졌다");
    }

    // 6) IMU 는 z 를 건드리지 않는다 — Himu 가 roll·pitch·yaw 만 고른다.
    {
        OdomImuEkf f;
        f.addOdom({0, 0, 0, 0, 0, 0}, 0.0);
        f.addImu(0, 0, 0);
        f.update();
        f.addOdom({0, 0, 0, 0, 0, 0.10}, 30.0 * kDeg);
        f.addImu(0.2, 0.1, 0.30);
        f.update();
        CHECK(std::fabs(f.pose().z) < 1e-12, "z 가 움직였다 — 어떤 관측도 z 를 고르지 않는다");
        CHECK(f.pose().roll > 1e-6 && f.pose().pitch > 1e-6, "IMU 의 roll·pitch 가 반영되지 않았다");
    }

    // 7) 내부 스케일은 대칭이라 인터페이스에서 보이지 않는다.
    CHECK(std::fabs(kPositionScale - 100.0) < 1e-12, "내부 스케일이 원본(100)과 다르다");

    if (g_fail == 0)
        std::printf("[PASS] 오도+IMU 융합 EKF 회귀 통과\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
