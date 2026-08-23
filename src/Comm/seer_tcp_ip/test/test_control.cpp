// 제어권 세션·dead-man jog·재측위 확정 회귀 시험.
//
// 고정 대상: 획득/반납의 짝, 예외 경로에서도 반납, 반납 전 정지, dead-man 주기 불변식,
//            「2002 를 보냈다」가 성공이 아니라는 것.
#include <memory>
#include <string>
#include <vector>

#include "fake_stream.hpp"
#include "harness.hpp"
#include "seer_tcp_ip/control.hpp"

using namespace seer_tcp_ip;

namespace
{

/// 지령 포트가 열린 SeerApi + 응답을 편호별로 넣어 두는 대역.
struct Rig
{
    fake::Stream stream;
    std::unique_ptr<SeerApi> api;
    std::vector<std::uint16_t> calls;          ///< 보낸 편호 순서 — 이것이 계약이다
    std::map<std::uint16_t, std::string> body; ///< 편호 → 응답 JSON 본문
    std::vector<int> relocSequence;            ///< 1021 이 순서대로 낼 reloc_status
    std::size_t relocIdx = 0;

    Rig()
    {
        stream.chunk = 7;
        stream.onWrite = [this](fake::Stream &s, const std::vector<char> &frame) {
            const Head h = unpackHead(frame.data(), kHeadLen);
            calls.push_back(h.apiType);
            std::string payload = "{\"ret_code\":0}";
            if (h.apiType == 1021 && !relocSequence.empty())
            {
                const int st = relocSequence[std::min(relocIdx, relocSequence.size() - 1)];
                ++relocIdx;
                payload = "{\"ret_code\":0,\"reloc_status\":" + std::to_string(st) + "}";
            }
            else
            {
                const auto it = body.find(h.apiType);
                if (it != body.end())
                {
                    payload = it->second;
                }
            }
            s.reset(fake::makeResponse(h.seq, static_cast<std::uint16_t>(h.apiType + 10000),
                                       payload));
        };
        api.reset(new SeerApi("1.2.3.4", 1.0, /*allowGuarded=*/true, /*minIntervalMs=*/0,
                              fake::factoryFor(&stream)));
    }

    bool sent(std::uint16_t n) const
    {
        for (auto c : calls) { if (c == n) return true; }
        return false;
    }
    int countOf(std::uint16_t n) const
    {
        int k = 0;
        for (auto c : calls) { if (c == n) ++k; }
        return k;
    }
};

/// 시험용 가짜 시계 — 폴링을 실시간 대기 없이 돌린다.
struct FakeClock
{
    std::int64_t now = 0;
    ClockMs clock() { return [this] { return now; }; }
    SleepMs sleep() { return [this](std::int64_t ms) { now += ms; }; }
};

}  // namespace

int main()
{
    // ---------- 제어권 세션 ----------
    {
        CASE("세션 순서: 소유자→획득→정지→반납");
        Rig r;
        r.body[1060] = R"({"ret_code":0,"locked":false})";
        {
            ControlSession s(*r.api, "big-amr");
            CHECK(s.held());
        }
        const std::vector<std::uint16_t> want = {1060, 4005, 2000, 4006};
        CHECK_EQ(r.calls, want);
    }
    {
        CASE("예외로 빠져나가도 반납한다");
        Rig r;
        r.body[1060] = R"({"ret_code":0,"locked":false})";
        try
        {
            ControlSession s(*r.api, "big-amr");
            throw std::runtime_error("작업 중 실패");
        }
        catch (const std::runtime_error &)
        {
        }
        CHECK(r.sent(4006));
    }
    {
        CASE("이전 소유자를 기록한다");
        Rig r;
        r.body[1060] = R"({"ret_code":0,"locked":true,"nick_name":"operator-0.1","ip":"192.168.44.49"})";
        ControlSession s(*r.api, "big-amr");
        CHECK_EQ(s.previousOwner().value("nick_name", std::string()), std::string("operator-0.1"));
    }
    {
        CASE("이중 획득 거부");
        Rig r;
        r.body[1060] = R"({"ret_code":0,"locked":false})";
        ControlSession s(*r.api, "big-amr");
        CHECK_THROWS_MSG(s.acquire(), ControlError, "이중 획득");
    }
    {
        CASE("빈 nickName 거부");
        Rig r;
        CHECK_THROWS_MSG(ControlSession(*r.api, "   "), std::invalid_argument, "nickName");
    }
    {
        CASE("stopOnExit=false 면 정지를 안 보낸다");
        Rig r;
        r.body[1060] = R"({"ret_code":0,"locked":false})";
        {
            ControlSession s(*r.api, "big-amr", /*stopOnExit=*/false);
        }
        CHECK(!r.sent(2000));
        CHECK(r.sent(4006));
    }

    // ---------- dead-man jog ----------
    {
        CASE("주기 >= dead-man 은 생성 거부");
        Rig r;
        CHECK_THROWS_MSG(JogKeepalive(*r.api, 0.1, 0, 0, 200, 200), std::invalid_argument, "이상이다");
        CHECK_THROWS_MSG(JogKeepalive(*r.api, 0.1, 0, 0, 100, 200), std::invalid_argument, "이상이다");
        CHECK_NOTHROW(JogKeepalive(*r.api, 0.1, 0, 0, 600, 200));
    }
    {
        CASE("duration<=0 은 거부 — 0 은 무한이라 dead-man 이 사라진다");
        Rig r;
        // ⚠ 메시지를 「durationMs」로 보면 안 된다 — 그 가드를 지워도 뒤의 interval 가드가
        //    같은 단어를 담아 통과한다(Python 판에서 실제로 밟은 함정).
        CHECK_THROWS_MSG(JogKeepalive(*r.api, 0.1, 0, 0, 0, 200), std::invalid_argument, "0 은 무한");
        CHECK_THROWS_MSG(JogKeepalive(*r.api, 0.1, 0, 0, -1, 200), std::invalid_argument, "0 은 무한");
    }
    {
        CASE("모든 재송신이 duration 을 싣는다");
        Rig r;
        FakeClock fc;
        JogKeepalive jog(*r.api, 0.1, 0.0, -0.2, 600, 200, fc.clock());
        CHECK(jog.tick());          // 첫 호출 즉시
        CHECK(!jog.tick());         // 아직 시점 아님
        fc.now += 200;
        CHECK(jog.tick());
        CHECK_EQ(jog.sentCount(), 2L);
        CHECK_EQ(r.countOf(2010), 2);
        // 선로에 duration 이 실렸는가 — 문자열로 직접 본다
        const std::string wire(r.stream.sent.begin(), r.stream.sent.end());
        CHECK(wire.find("\"duration\":600") != std::string::npos);
    }
    {
        CASE("setVelocity 는 스스로 송신하지 않는다");
        Rig r;
        FakeClock fc;
        JogKeepalive jog(*r.api, 0.1, 0, 0, 600, 200, fc.clock());
        jog.tick();
        fc.now += 500;              // 시점을 지나게 둔다 — 이래야 「즉시 송신」이 드러난다
        jog.setVelocity(0.3, 0, 0);
        CHECK_EQ(r.countOf(2010), 1);
        jog.tick();
        CHECK_EQ(r.countOf(2010), 2);
    }
    {
        CASE("stop 은 속도를 0 으로 되돌리고 스케줄을 지운다");
        Rig r;
        FakeClock fc;
        JogKeepalive jog(*r.api, 0.5, 0, 0, 600, 200, fc.clock());
        jog.tick();
        jog.stop();
        CHECK_EQ(jog.vx(), 0.0);
        CHECK(jog.due());
        CHECK(r.sent(2000));
    }

    // ---------- 재측위 확정 ----------
    {
        CASE("「2002 를 보냈다」는 성공이 아니다 — 1 이 될 때까지 폴링한다");
        Rig r;
        FakeClock fc;
        r.relocSequence = {reloc::kRelocing, reloc::kRelocing, reloc::kSuccess};
        relocateAndConfirm(*r.api, Json{{"isAuto", true}}, 10000, 500, fc.clock(), fc.sleep());
        CHECK(r.sent(2002));
        CHECK_EQ(r.countOf(1021), 3);
        CHECK(!r.sent(2003));       // 상태 3 을 안 봤으니 확정 불필요
    }
    {
        CASE("상태 3(계산 완료·미확정)이면 2003 을 보낸다 — 이 기체가 그 판이다");
        Rig r;
        FakeClock fc;
        r.relocSequence = {reloc::kCompleted, reloc::kSuccess};
        relocateAndConfirm(*r.api, Json{{"isAuto", true}}, 10000, 500, fc.clock(), fc.sleep());
        CHECK(r.sent(2003));
    }
    {
        CASE("확정되지 않으면 예외 — 조용히 성공으로 넘어가지 않는다");
        Rig r;
        FakeClock fc;
        r.relocSequence = {reloc::kRelocing};   // 영원히 진행중
        CHECK_THROWS_MSG(
            relocateAndConfirm(*r.api, Json{{"isAuto", true}}, 2000, 500, fc.clock(), fc.sleep()),
            ControlError, "확정되지 않았다");
    }
    {
        CASE("params 가 비면 2002 를 보내지 않고 기다리기만 한다");
        Rig r;
        FakeClock fc;
        r.relocSequence = {reloc::kSuccess};
        relocateAndConfirm(*r.api, Json::object(), 10000, 500, fc.clock(), fc.sleep());
        CHECK(!r.sent(2002));
        CHECK(r.sent(1021));
    }
    {
        CASE("reloc 상태 상수");
        CHECK_EQ(reloc::kSuccess, 1);
        CHECK_EQ(reloc::kRelocing, 2);
        CHECK_EQ(reloc::kCompleted, 3);
    }

    // ---------- 진단 ----------
    {
        CASE("40020 판별");
        CHECK(preemptedByControl(std::runtime_error("API 2010 ret_code=40020 err_msg='x'")));
        CHECK(!preemptedByControl(std::runtime_error("API 2010 ret_code=8 err_msg='x'")));
    }

    return harness::report("test_control");
}
