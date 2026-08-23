// 제어권 경로를 실기로 확인한다 — 로봇을 **움직이지 않는다**.
//
// 확인하는 것: 1060 조회 → 4005 획득 → 1060 재조회(내 이름이 보이는가) → 2000 정지 → 4006 반납
//              → 1060 재조회(비었는가). ControlSession 의 계약이 실기에서 성립하는지 본다.
//
// 왜 도구인가 — 「제어권이 실기에서 된다」를 한 번 확인하고 말면 다음 사람은 다시 못 믿는다.
// 재실행할 수 있어야 근거로 쓸 수 있다.
//
// 안전 가드 2개(둘 다 `--force` 로만 넘어간다):
//   · 4005 는 기존 소유자의 제어권을 빼앗으며 반납해도 원 소유자로 자동 복귀시키지 않는다.
//     → 시작 전 1060 이 `locked=true` 면 중단.
//   · 2000 은 주행 중인 로봇을 세운다(정지 상태면 무동작).
//     → 시작 전 1005 속도가 0 이 아니면 중단.
//
// 사용:
//   ros2 run seer_tcp_ip control_probe [--force]
//   환경변수 SEER_IP 로 대상 지정(기본 192.168.44.82)
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "seer_tcp_ip/control.hpp"

namespace
{

int fail(const char *what, const std::exception &e)
{
    std::fprintf(stderr, "✗ %s — %s\n", what, e.what());
    return 1;
}

bool nearZero(double v)
{
    return v < 1e-6 && v > -1e-6;
}

}  // namespace

int main(int argc, char **argv)
{
    bool force = false;
    for (int i = 1; i < argc; ++i)
    {
        if (std::strcmp(argv[i], "--force") == 0)
        {
            force = true;
        }
    }
    const char *env = std::getenv("SEER_IP");
    const std::string ip = env ? env : "192.168.44.82";
    const std::string nick = "big-amr-control-probe";

    try
    {
        // 1) 사전 안전 조회 — 조회 포트만 쓴다.
        seer_tcp_ip::SeerApi look(ip, 4.0);
        std::printf("대상: %s\n", ip.c_str());
        std::printf("1060 사전 : %s\n", seer_tcp_ip::describeOwner(look).c_str());

        const auto owner = look.getControlOwner();
        if (owner.value("locked", false) && !force)
        {
            std::fprintf(stderr,
                         "✗ 다른 소유자가 제어권을 쥐고 있다 — 4005 는 그것을 뺏고 반납해도 "
                         "복귀시키지 않는다. 정말 뺏으려면 --force.\n");
            return 2;
        }

        const auto speed = look.getSpeed();
        const double vx = speed.value("vx", 0.0), vy = speed.value("vy", 0.0),
                     w = speed.value("w", 0.0);
        std::printf("1005 속도 : vx=%.4f vy=%.4f w=%.4f\n", vx, vy, w);
        if (!(nearZero(vx) && nearZero(vy) && nearZero(w)) && !force)
        {
            std::fprintf(stderr, "✗ 로봇이 움직이는 중이다 — 2000 이 세운다. 정말 하려면 --force.\n");
            return 3;
        }

        // 2) 제어권 왕복 — 지령 포트를 쓰므로 게이트를 명시적으로 연다.
        seer_tcp_ip::SeerApi api(ip, 4.0, /*allowGuarded=*/true);
        {
            seer_tcp_ip::ControlSession session(api, nick);
            std::printf("4005 획득 : OK (이전 소유자 = %s)\n",
                        session.previousOwner().value("locked", false)
                            ? session.previousOwner().value("nick_name", std::string()).c_str()
                            : "없음");

            const auto mine = look.getControlOwner();
            const std::string who = mine.value("nick_name", std::string());
            const bool ok = mine.value("locked", false) && who == nick;
            std::printf("1060 중간 : locked=%s nick_name='%s' → %s\n",
                        mine.value("locked", false) ? "true" : "false", who.c_str(),
                        ok ? "내 이름이 보인다 ✓" : "✗ 기대와 다르다");
            if (!ok)
            {
                std::fprintf(stderr,
                             "✗ 4005 가 수리됐는데 1060 이 내 이름을 보이지 않는다 — "
                             "제어권 계약이 성립하지 않는다.\n");
                return 4;
            }
            // 이탈 시 ControlSession 이 2000 정지 후 4006 반납한다.
        }
        std::printf("2000+4006 : 세션 이탈 시 정지 후 반납 (ControlSession 소멸자)\n");

        const auto after = look.getControlOwner();
        const bool freed = !after.value("locked", false);
        std::printf("1060 사후 : %s → %s\n", seer_tcp_ip::describeOwner(look).c_str(),
                    freed ? "반납 확인 ✓" : "✗ 아직 잡혀 있다");
        if (!freed)
        {
            return 5;
        }

        std::printf("\n제어권 경로 실기 확인 완료 — 1060 → 4005 → 1060 → 2000 → 4006 → 1060.\n");
        std::printf("⚠ 이 도구는 로봇을 움직이지 않는다. 2010 개루프·내비게이션은 여전히 미검증이다.\n");
        return 0;
    }
    catch (const seer_tcp_ip::GuardedPortError &e)
    {
        return fail("게이트에 막혔다(allowGuarded 누락)", e);
    }
    catch (const std::exception &e)
    {
        return fail("제어권 경로 실패", e);
    }
}
