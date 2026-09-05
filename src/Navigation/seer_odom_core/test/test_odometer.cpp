// Seer MultiSteersOdometer 재구현 회귀 — 복원된 원본 성질을 고정한다.
//
// 원본과의 **수치** 대조는 오라클 하니스 소관이다(원본 .so 를 직접 구동해야 한다).
// 여기서는 정적 분석으로 확정한 **구조적 성질**을 고정한다.
#include <cmath>
#include <cstdio>

#include "seer_odom_core/multisteer_odometer.hpp"

using namespace seer_odom_core;

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

// Foil_A082 실측 기하 — inline dual-steer, 앞뒤 센터라인.
static std::vector<MotorParam> foilWheels()
{
    return {{"front", 0.6039, 0.0, 0.0, 0.0}, {"rear", -0.5961, 0.0, 0.0, 0.0}};
}

static std::map<std::string, MotorVitalInfo> measNamed(const char *n1, const char *n2,
                                                       double d_front, double a_front,
                                                       double d_rear, double a_rear,
                                                       bool velocity = false)
{
    std::map<std::string, MotorVitalInfo> m;
    MotorVitalInfo f, r;
    f.position = a_front;
    r.position = a_rear;
    if (velocity)
    {
        f.v_enc = d_front;
        r.v_enc = d_rear;
    }
    else
    {
        f.dpos = d_front;
        r.dpos = d_rear;
    }
    m[n1] = f;
    m[n2] = r;
    return m;
}

// Foil_A082 기본 이름(front/rear) 용 축약.
static std::map<std::string, MotorVitalInfo> meas(double d_front, double a_front, double d_rear,
                                                  double a_rear, bool velocity = false)
{
    return measNamed("front", "rear", d_front, a_front, d_rear, a_rear, velocity);
}

int main()
{
    // 1) normalize 치역 [-π, π) — 원본 0x18750 실측.
    {
        CHECK(normalize(0.0) == 0.0, "0 이 변했다");
        CHECK(normalize(-M_PI) == -M_PI, "-π 는 치역에 포함돼 그대로여야 한다");
        CHECK(normalize(M_PI) < 0.0, "π 는 치역 밖이라 접혀야 한다");
        CHECK(std::fabs(normalize(M_PI) + M_PI) < 1e-12, "π 가 -π 로 접히지 않았다");
        CHECK(normalize(3.5) < M_PI && normalize(3.5) >= -M_PI, "치역을 벗어났다");
        // 구간 안 입력은 손대지 않는다 — 원본 빠른 경로.
        CHECK(normalize(1.0) == 1.0, "치역 안 입력이 변형됐다");
    }

    // 2) 기하가 없으면 굳지 않는다.
    {
        MultiSteersOdometer o;
        CHECK(!o.setMotorParams({}), "휠 0개인데 계수행렬이 굳었다");
        CHECK(!o.coefReady(), "coefReady 가 참이다");
    }

    // 3) 첫 입력 전에는 자세를 누적하지 않는다 — 원본 428·163행 게이트.
    {
        MultiSteersOdometer o;
        CHECK(o.setMotorParams(foilWheels()), "계수행렬이 굳지 않았다");
        o.setVitalInfo(meas(1.0, 0.0, 1.0, 0.0));
        o.caldPose();
        o.calPose();
        CHECK(o.output().x == 0.0 && o.output().y == 0.0 && o.output().yaw == 0.0,
              "첫 입력 플래그가 없는데 자세가 움직였다");
    }

    // 4) 직진 — 양 휠 조향 0, 같은 변위면 dx 만 나온다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        o.setVitalInfo(meas(0.10, 0.0, 0.10, 0.0));
        o.caldPose();
        CHECK(std::fabs(o.output().dx - 0.10) < 1e-12, "직진 dx 가 변위와 다르다");
        CHECK(std::fabs(o.output().dy) < 1e-12, "직진인데 dy 가 생겼다");
        CHECK(std::fabs(o.output().dyaw) < 1e-12, "직진인데 dyaw 가 생겼다");
    }

    // 5) 제자리 스핀 — 2WS 는 구조상 조향 ±90°, 두 휠이 반대로 굴러야 회전만 남는다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        const double h = M_PI / 2.0;
        o.setVitalInfo(meas(0.06039, h, -0.05961, h));
        o.caldPose();
        CHECK(std::fabs(o.output().dx) < 1e-9, "스핀인데 dx 가 생겼다");
        CHECK(o.output().dyaw > 0.0, "스핀 방향이 뒤집혔다");
        CHECK(std::fabs(o.output().dyaw - 0.1) < 1e-9, "스핀 회전량이 기대와 다르다");
    }

    // 6) caldPose 는 속도를 **항상** 지운다 — 원본 190행.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        o.setVitalInfo(meas(0.5, 0.0, 0.5, 0.0, /*velocity=*/true));
        o.calSpeed();
        CHECK(std::fabs(o.output().vx - 0.5) < 1e-12, "속도가 산출되지 않았다");
        o.setVitalInfo(meas(0.01, 0.0, 0.01, 0.0));
        o.caldPose();
        CHECK(o.output().vx == 0.0 && o.output().vy == 0.0 && o.output().vw == 0.0,
              "caldPose 가 속도를 지우지 않았다 — 원본은 항상 지운다");
    }

    // 7) 자세 누적은 **갱신된 각**으로 회전한다(end-point) — 원본 446~450행.
    //    start-point 로 바꾸면 회전이 있는 주기에서 결과가 갈린다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        o.setVitalInfo(meas(0.10, 0.0, 0.10, 0.0));
        o.caldPose();
        // dyaw 를 인위로 넣지 않고, 직진 뒤 스핀을 이어 붙여 각이 먼저 도는지 본다.
        o.calPose();
        const double x_after_straight = o.output().x;
        CHECK(std::fabs(x_after_straight - 0.10) < 1e-12, "직진 누적이 어긋났다");
        const double h = M_PI / 2.0;
        o.setVitalInfo(meas(0.06039 * 5, h, -0.05961 * 5, h));
        o.caldPose();
        o.calPose();
        CHECK(std::fabs(o.output().yaw - 0.5) < 1e-9, "yaw 누적이 어긋났다");
    }

    // 8) 일관성 판정 — 두 휠이 모순된 속도를 주면 임계를 넘는다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        o.setThresConsistent(0.02);
        o.setVitalInfo(meas(0.5, 0.0, 0.5, 0.0, true));
        o.calSpeed();
        CHECK(o.wheelConsistent(), "정합한 입력인데 불일치로 판정했다");
        o.setVitalInfo(meas(0.5, 0.0, 0.5, M_PI / 2.0, true));
        o.calSpeed();
        CHECK(!o.wheelConsistent(), "모순된 입력인데 일치로 판정했다");
    }


    // 9) normalize 는 **큰 각**에서도 원본 방식이어야 한다 — 반복 감산으로 바꾸면 갈린다(§14).
    //    작은 각만 시험하면 두 방식이 같은 값을 내므로 이 항목이 없으면 아무것도 지키지 못한다.
    {
        const double big = 1.0e6;
        const double got = normalize(big);
        // 반복 감산이 내는 값을 여기서 직접 만들어 **다름**을 요구한다.
        //   상수를 박으면 FMA 축약·libm 차이에 흔들려 무엇을 지키는지 흐려진다 —
        //   이 항목이 지키려는 것은 「floor 1회 방식인가」 하나다.
        double iter = big;
        while (iter >= M_PI)
            iter -= 2.0 * M_PI;
        while (iter < -M_PI)
            iter += 2.0 * M_PI;
        CHECK(std::fabs(got - iter) > 1e-9,
              "큰 각 정규화가 반복 감산과 같은 값이다 — floor 1회 방식이 아니다");
        CHECK(got >= -M_PI && got < M_PI, "큰 각 정규화 결과가 치역을 벗어났다");
    }

    // 10) y 가 0 이 아닌 기하 — 계수행렬 yaw 열의 **부호**를 이 배치에서만 확인할 수 있다.
    //     센터라인 기체(y=0)는 부호를 뒤집어도 결과가 같아 검출력이 없다.
    {
        MultiSteersOdometer o;
        // QD 대각 배치(전방좌측 / 후방우측).
        CHECK(o.setMotorParams({{"w1", 0.330, 0.135, 0.0, 0.0}, {"w2", -0.330, -0.135, 0.0, 0.0}}),
              "대각 기하가 굳지 않았다");
        o.setFirstInputGot(true);
        // 두 휠 모두 +x 로 같은 변위 → 순수 직진이어야 한다.
        o.setVitalInfo(measNamed("w1", "w2", 0.10, 0.0, 0.10, 0.0));
        o.caldPose();
        CHECK(std::fabs(o.output().dx - 0.10) < 1e-12, "대각 기하 직진 dx 가 어긋났다");
        CHECK(std::fabs(o.output().dyaw) < 1e-12, "대각 기하 직진인데 회전이 생겼다");
        // 앞쪽만 +y 로 굴리면 반시계 회전이 나와야 한다(yaw 열 부호가 근거).
        o.setVitalInfo(measNamed("w1", "w2", 0.02, M_PI / 2.0, 0.0, 0.0));
        o.caldPose();
        CHECK(o.output().dyaw > 0.0, "yaw 열 부호가 뒤집혔다 — 앞휠 좌측 이동이 반시계가 아니다");
    }

    // 11) 보정항 cpx·cpy 가 실제로 쓰인다 — 무시하면 회전량이 달라진다.
    {
        MultiSteersOdometer a, b;
        const std::vector<MotorParam> plain = {{"w1", 0.330, 0.135, 0.0, 0.0},
                                               {"w2", -0.330, -0.135, 0.0, 0.0}};
        const std::vector<MotorParam> withcp = {{"w1", 0.330, 0.135, 0.050, 0.030},
                                                {"w2", -0.330, -0.135, -0.040, 0.020}};
        a.setMotorParams(plain);
        b.setMotorParams(withcp);
        a.setFirstInputGot(true);
        b.setFirstInputGot(true);
        const auto m = measNamed("w1", "w2", 0.02, M_PI / 2.0, 0.0, 0.0);
        a.setVitalInfo(m);
        b.setVitalInfo(m);
        a.caldPose();
        b.caldPose();
        CHECK(std::fabs(a.output().dyaw - b.output().dyaw) > 1e-6,
              "보정항이 결과를 바꾸지 않는다 — cpx·cpy 가 무시되고 있다");
    }

    // 12) 회전과 병진이 **함께** 있는 주기 — 회전을 갱신 전 각으로 하면 여기서 갈린다.
    //     스핀만 시험하면 병진이 0 이라 회전 순서가 결과를 바꾸지 않는다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        // 앞뒤 조향을 반대로 줘서 호(arc)를 그린다 — 병진과 회전이 동시에 생긴다.
        o.setVitalInfo(meas(0.20, 0.15, 0.20, -0.15));
        o.caldPose();
        CHECK(std::fabs(o.output().dx) > 1e-6, "호 주행인데 병진이 없다");
        CHECK(std::fabs(o.output().dyaw) > 1e-6, "호 주행인데 회전이 없다");
        o.calPose();
        // end-point 회전의 값. start-point 로 바꾸면 y 가 눈에 띄게 달라진다.
        const double yaw = o.output().yaw;
        const double expect_x = std::cos(yaw) * o.output().dx - std::sin(yaw) * o.output().dy;
        const double expect_y = std::sin(yaw) * o.output().dx + std::cos(yaw) * o.output().dy;
        CHECK(std::fabs(o.output().x - expect_x) < 1e-12 &&
                  std::fabs(o.output().y - expect_y) < 1e-12,
              "회전에 **갱신된** 각을 쓰지 않았다(end-point 위반)");
    }

    // 13) 증분이 이미 있어도 첫 입력 플래그가 내려가면 자세를 누적하지 않는다 — 원본 428행.
    //     3번은 증분이 0 이라 게이트를 지워도 결과가 같아 검출력이 없다.
    {
        MultiSteersOdometer o;
        o.setMotorParams(foilWheels());
        o.setFirstInputGot(true);
        o.setVitalInfo(meas(0.10, 0.0, 0.10, 0.0));
        o.caldPose();
        CHECK(std::fabs(o.output().dx - 0.10) < 1e-12, "증분이 만들어지지 않았다");
        o.setFirstInputGot(false);
        o.calPose();
        CHECK(o.output().x == 0.0 && o.output().y == 0.0,
              "첫 입력 플래그가 내려갔는데 자세가 누적됐다");
    }


    // 14) 왕복 시험 — 알려진 (dx, dy, dyaw) 로 휠 관측을 만들고 다시 풀어 복원되는지 본다.
    //     계수행렬의 **부호와 보정항**이 여기서 동시에 고정된다. 부등호만 보는 시험은
    //     특정 입력에서 우연히 통과할 수 있어 이 항목이 필요하다.
    {
        const std::vector<MotorParam> geom = {{"w1", 0.330, 0.135, 0.050, 0.030},
                                              {"w2", -0.330, -0.135, -0.040, 0.020}};
        MultiSteersOdometer o;
        CHECK(o.setMotorParams(geom), "왕복 시험 기하가 굳지 않았다");
        o.setFirstInputGot(true);

        const double dx = 0.030, dy = -0.020, dyaw = 0.050;
        std::map<std::string, MotorVitalInfo> m;
        for (const auto &w : geom)
        {
            // 평면 강체 관계 — 휠 위치는 보정항을 더한 유효 위치다.
            const double ex = w.x + w.cpx;
            const double ey = w.y + w.cpy;
            const double bx = dx - dyaw * ey;
            const double by = dy + dyaw * ex;
            MotorVitalInfo v;
            v.dpos = std::hypot(bx, by);
            v.position = std::atan2(by, bx);
            m[w.name] = v;
        }
        o.setVitalInfo(m);
        o.caldPose();
        CHECK(std::fabs(o.output().dx - dx) < 1e-12, "왕복 dx 가 복원되지 않았다");
        CHECK(std::fabs(o.output().dy - dy) < 1e-12, "왕복 dy 가 복원되지 않았다");
        CHECK(std::fabs(o.output().dyaw - dyaw) < 1e-12, "왕복 dyaw 가 복원되지 않았다");
    }


    // 15) 잔차는 **휠별 2성분 노름의 최대값**이다 — 성분별 최대값(L∞)이 아니다.
    //     원본 calspeed.asm 139행이 mulpd→movhlps→addsd→sqrtpd 로 노름을 만든다.
    //     ⚠ 센터라인 2륜은 y 잔차가 구조상 0 이라 노름과 성분 최대값이 같다 —
    //        그 기하로는 이 성질을 시험할 수 없어 **대각 기하**를 쓴다.
    {
        const std::vector<MotorParam> diag = {{"w1", 0.330, 0.135, 0.0, 0.0},
                                              {"w2", -0.330, -0.135, 0.0, 0.0}};
        MultiSteersOdometer o;
        o.setMotorParams(diag);
        o.setFirstInputGot(true);
        o.setThresConsistent(1e9); // 먼저 크게 열어 두고 (vx, vy, vw) 를 얻는다
        const double d[2] = {0.37, -0.21}, ang[2] = {0.4, -0.9};
        o.setVitalInfo(measNamed("w1", "w2", d[0], ang[0], d[1], ang[1], /*velocity=*/true));
        o.calSpeed();

        // 되돌린 관측과의 잔차를 시험 쪽에서 따로 계산한다.
        double comp_max = 0.0, norm_max = 0.0;
        for (int i = 0; i < 2; ++i)
        {
            const double bx = std::cos(ang[i]) * d[i], by = std::sin(ang[i]) * d[i];
            const double fx = o.output().vx - o.output().vw * (diag[i].y + diag[i].cpy);
            const double fy = o.output().vy + o.output().vw * (diag[i].x + diag[i].cpx);
            const double ex = fx - bx, ey = fy - by;
            comp_max = std::max(comp_max, std::max(std::fabs(ex), std::fabs(ey)));
            norm_max = std::max(norm_max, std::sqrt(ex * ex + ey * ey));
        }
        CHECK(norm_max > comp_max * 1.000001,
              "이 시나리오는 노름과 성분최대값이 갈리지 않는다 — 시험이 성질을 못 지킨다");

        auto judgeAt = [&](double thres) {
            o.setThresConsistent(thres);
            o.setVitalInfo(measNamed("w1", "w2", d[0], ang[0], d[1], ang[1], true));
            o.calSpeed();
            return o.wheelConsistent();
        };
        // 임계를 성분최대값에 두면 **불일치**여야 한다 — 노름이 그보다 크기 때문이다.
        CHECK(!judgeAt(comp_max), "성분최대값 임계에서 일치로 판정했다 — 잔차가 노름이 아니다");
        // 노름에 두면 일치.
        CHECK(judgeAt(norm_max), "노름 임계에서 불일치로 판정했다");
    }

    if (g_fail == 0)
        std::printf("[PASS] Seer MultiSteersOdometer 재구현 회귀 통과\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
