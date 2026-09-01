// 편호 바인딩 회귀 시험 — 편호·포트 배선과 지령 포트 게이트.
//
// 편호는 **리터럴**로 고정한다. 상수를 기대값에 그대로 쓰면 상수가 틀려도 기대값이 같이 틀려
// 시험이 통과한다 — Python 판에서 맵 편호(4011)가 그렇게 빠져나갔다.
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "fake_stream.hpp"
#include "harness.hpp"
#include "seer_tcp_ip/api.hpp"

using namespace seer_tcp_ip;

namespace
{

/// 포트별로 「보낸 편호·본문」을 기록하는 대역.
struct Rig
{
    std::map<std::uint16_t, fake::Stream *> streams;   ///< 포트 → 스트림
    struct Call { std::uint16_t port; std::uint16_t api; std::string body; };
    std::vector<Call> calls;
    std::map<std::uint16_t, std::string> reply;        ///< 편호 → 응답 본문
    /// ⚠ 선언 순서가 계약이다 — 멤버는 선언의 역순으로 파괴된다. `api` 를 **마지막에** 두어야
    ///   SeerApi 소멸자(→ Transport::close → Wrapper → Stream)가 살아 있는 스트림을 본다.
    ///   반대로 두면 스트림이 먼저 죽어 소멸 시 세그폴트가 난다.
    std::vector<std::unique_ptr<fake::Stream>> owned;
    std::unique_ptr<SeerApi> api;

    explicit Rig(bool allowGuarded)
    {
        auto factory = [this]() -> std::unique_ptr<IByteStream> {
            owned.emplace_back(new fake::Stream());
            fake::Stream *s = owned.back().get();
            s->chunk = 11;
            s->onWrite = [this](fake::Stream &st, const std::vector<char> &f) {
                const Head h = unpackHead(f.data(), kHeadLen);
                calls.push_back({st.connectedPort, h.apiType,
                                 std::string(f.begin() + kHeadLen, f.end())});
                const auto it = reply.find(h.apiType);
                st.reset(fake::makeResponse(
                    h.seq, static_cast<std::uint16_t>(h.apiType + 10000),
                    it == reply.end() ? "{\"ret_code\":0}" : it->second));
            };
            // connect 시 어느 포트인지 기록되도록 래핑
            return std::unique_ptr<IByteStream>(new fake::Wrapper(s));
        };
        api.reset(new SeerApi("1.2.3.4", 1.0, allowGuarded, 0, factory));
    }

    std::uint16_t lastApi() const { return calls.empty() ? 0 : calls.back().api; }
    std::uint16_t lastPort() const { return calls.empty() ? 0 : calls.back().port; }
    std::string lastBody() const { return calls.empty() ? "" : calls.back().body; }
    int countOf(std::uint16_t n) const
    {
        int k = 0;
        for (const auto &c : calls) { if (c.api == n) ++k; }
        return k;
    }
};

}  // namespace

int main()
{
    // ---------- 지령 포트 게이트 ----------
    {
        CASE("지령·설정 포트는 기본값에서 막힌다");
        Rig r(false);
        CHECK_THROWS_MSG(r.api->stop(), GuardedPortError, "지령·설정");
        CHECK_THROWS_MSG(r.api->openLoopMove(0.1, 0, 0, 600), GuardedPortError, "지령·설정");
        CHECK_THROWS_MSG(r.api->goTarget("LM1"), GuardedPortError, "지령·설정");
        CHECK_THROWS_MSG(r.api->setDo(15, true), GuardedPortError, "지령·설정");
        CHECK_THROWS_MSG(r.api->downloadMap("m"), GuardedPortError, "지령·설정");
        CHECK_THROWS_MSG(r.api->seizeControl("x"), GuardedPortError, "지령·설정");
    }
    {
        CASE("조회는 기본값에서 열려 있다");
        Rig r(false);
        CHECK_NOTHROW(r.api->getPose());
        CHECK_EQ(r.lastApi(), std::uint16_t(1004));
    }
    {
        CASE("게이트 집합은 명시 집합 — 한도에서 파생하면 비어 사라진다");
        const std::set<std::uint16_t> want = {19205, 19206, 19207, 19210};
        CHECK_EQ(ports::guardedPorts(), want);
        for (auto p : want)
        {
            CHECK(ports::isGuarded(p));
            CHECK(ports::observedMaxConnectionsFor(p) > 1);
        }
        CHECK(!ports::isGuarded(19204));
        CHECK(!ports::isGuarded(19301));
    }
    {
        CASE("관측 한도 실측값");
        CHECK_EQ(ports::observedMaxConnectionsFor(19204), 10);
        CHECK_EQ(ports::observedMaxConnectionsFor(19301), 10);
        CHECK_EQ(ports::observedMaxConnectionsFor(19205), 5);
        CHECK_EQ(ports::observedMaxConnectionsFor(19208), -1);
    }

    // ---------- 편호 리터럴 고정 ----------
    {
        CASE("편호 상수를 리터럴로 고정");
        CHECK_EQ(api::kRobotInfo, 1000);  CHECK_EQ(api::kRunInfo, 1002);
        CHECK_EQ(api::kMode, 1003);       CHECK_EQ(api::kLoc, 1004);
        CHECK_EQ(api::kSpeed, 1005);      CHECK_EQ(api::kBlocked, 1006);
        CHECK_EQ(api::kBattery, 1007);    CHECK_EQ(api::kBrake, 1008);
        CHECK_EQ(api::kLaser, 1009);      CHECK_EQ(api::kPath, 1010);
        CHECK_EQ(api::kArea, 1011);       CHECK_EQ(api::kEstop, 1012);
        CHECK_EQ(api::kIo, 1013);         CHECK_EQ(api::kTaskStatus, 1020);
        CHECK_EQ(api::kRelocStatus, 1021); CHECK_EQ(api::kLoadmapStatus, 1022);
        CHECK_EQ(api::kSlamStatus, 1025); CHECK_EQ(api::kMotorInfo, 1040);
        CHECK_EQ(api::kAlarm, 1050);      CHECK_EQ(api::kControlOwner, 1060);
        CHECK_EQ(api::kAll, 1100);        CHECK_EQ(api::kAll2, 1101);
        CHECK_EQ(api::kAll3, 1102);       CHECK_EQ(api::kInitStatus, 1111);
        CHECK_EQ(api::kMapStatus, 1300);  CHECK_EQ(api::kStations, 1301);
        CHECK_EQ(api::kMapMd5, 1302);     CHECK_EQ(api::kParam, 1400);
        CHECK_EQ(api::kRobotModel, 1500);
        CHECK_EQ(api::kCtrlStop, 2000);   CHECK_EQ(api::kCtrlGyro, 2001);
        CHECK_EQ(api::kCtrlReloc, 2002);  CHECK_EQ(api::kCtrlConfirmLoc, 2003);
        CHECK_EQ(api::kCtrlMotion, 2010);
        CHECK_EQ(api::kTaskPause, 3001);  CHECK_EQ(api::kTaskResume, 3002);
        CHECK_EQ(api::kTaskCancel, 3003); CHECK_EQ(api::kTaskGoPoint, 3050);
        CHECK_EQ(api::kTaskGoTarget, 3051); CHECK_EQ(api::kTaskPatrol, 3052);
        CHECK_EQ(api::kTaskTranslate, 3055); CHECK_EQ(api::kTaskTurn, 3056);
        CHECK_EQ(api::kTaskGoTargetList, 3066);
        CHECK_EQ(api::kConfigSetMode, 4000); CHECK_EQ(api::kConfigSetParams, 4100);
        CHECK_EQ(api::kConfigSaveParams, 4101); CHECK_EQ(api::kConfigReloadParams, 4102);
        CHECK_EQ(api::kConfigClearFatal, 4300); CHECK_EQ(api::kConfigSeizeControl, 4005);
        CHECK_EQ(api::kConfigReleaseControl, 4006); CHECK_EQ(api::kConfigUploadMap, 4010);
        CHECK_EQ(api::kConfigDownloadMap, 4011);
        CHECK_EQ(api::kOtherSpeaker, 6000); CHECK_EQ(api::kOtherSetDo, 6001);
        CHECK_EQ(api::kOtherSoftEstop, 6004);
        CHECK_EQ(ports::kControlPreemptedRetCode, 40020);
        CHECK_EQ(ports::kConnectionLimitRetCode, 61001);
    }

    // ---------- 조회 배선 ----------
    {
        CASE("조회 메서드가 올바른 편호를 보낸다");
        Rig r(false);
        struct { void (*call)(SeerApi &); std::uint16_t api; } cases[] = {
            {[](SeerApi &a) { a.getRobotInfo(); }, 1000},
            {[](SeerApi &a) { a.getRunInfo(); }, 1002},
            {[](SeerApi &a) { a.getMode(); }, 1003},
            {[](SeerApi &a) { a.getPose(); }, 1004},
            {[](SeerApi &a) { a.getSpeed(); }, 1005},
            {[](SeerApi &a) { a.getBlocked(); }, 1006},
            {[](SeerApi &a) { a.getBattery(); }, 1007},
            {[](SeerApi &a) { a.getBrake(); }, 1008},
            {[](SeerApi &a) { a.getPath(); }, 1010},
            {[](SeerApi &a) { a.getArea(); }, 1011},
            {[](SeerApi &a) { a.getEstop(); }, 1012},
            {[](SeerApi &a) { a.getIo(); }, 1013},
            {[](SeerApi &a) { a.getRelocStatus(); }, 1021},
            {[](SeerApi &a) { a.getLoadmapStatus(); }, 1022},
            {[](SeerApi &a) { a.getControlOwner(); }, 1060},
            {[](SeerApi &a) { a.getAllStatus(); }, 1100},
            {[](SeerApi &a) { a.getAllStatus2(); }, 1101},
            {[](SeerApi &a) { a.getAllStatus3(); }, 1102},
            {[](SeerApi &a) { a.getInitStatus(); }, 1111},
            {[](SeerApi &a) { a.getMapStatus(); }, 1300},
            {[](SeerApi &a) { a.getRobotModel(); }, 1500},
        };
        for (const auto &c : cases)
        {
            c.call(*r.api);
            CHECK_EQ(r.lastApi(), c.api);
        }
    }
    {
        CASE("무파라미터 조회는 본문을 싣지 않는다");
        Rig r(false);
        r.api->getPose();
        CHECK_EQ(r.lastBody(), std::string(""));
    }
    {
        CASE("1025 는 return_resultmap 을 싣는다");
        Rig r(false);
        r.api->getSlamStatus(true);
        CHECK_EQ(r.lastApi(), std::uint16_t(1025));
        CHECK(r.lastBody().find("\"return_resultmap\":true") != std::string::npos);
    }
    {
        CASE("1400 파라미터 조회 본문");
        Rig r(false);
        r.api->getParam("NetProtocol", "RobotControlAPITCPServerMaxConnections");
        CHECK(r.lastBody().find("\"plugin\":\"NetProtocol\"") != std::string::npos);
        CHECK(r.lastBody().find("RobotControlAPITCPServerMaxConnections") != std::string::npos);
    }
    {
        CASE("한도 조회는 상수가 아니라 로봇 응답을 쓴다");
        Rig r(false);
        r.reply[1400] = R"({"ret_code":0,"NetProtocol":{"RobotControlAPITCPServerMaxConnections":{"value":7}}})";
        CHECK_EQ(r.api->getMaxConnections(19205), 7);   // 상수 5 가 아니라 7
        CHECK_EQ(r.api->getMaxConnections(19208), -1);  // 한도 파라미터 없는 포트
    }
    {
        CASE("배열 응답은 키가 없으면 빈 배열");
        Rig r(false);
        CHECK_EQ(r.api->getMotorInfo().size(), std::size_t(0));
        CHECK_EQ(r.api->getStations().size(), std::size_t(0));
        CHECK_EQ(r.api->getLasers().size(), std::size_t(0));
    }
    {
        CASE("ret_code != 0 은 예외");
        Rig r(false);
        r.reply[1004] = R"({"ret_code":8,"err_msg":"not allowed"})";
        CHECK_THROWS_MSG(r.api->getPose(), ProtocolError, "ret_code=8");
    }
    {
        CASE("ret_code 부재는 정상 — 있는 응답만 검사한다");
        Rig r(false);
        r.reply[1004] = R"({"x":1.0,"y":2.0,"angle":0.5})";
        CHECK_NOTHROW(r.api->getPose());
    }

    // ---------- 1302 맵 md5 ----------
    {
        CASE("1302 는 .smap 을 붙이고 반환 키는 호출자 형태 — 1300 과 맞물린다");
        Rig r(false);
        r.reply[1302] = R"({"ret_code":0,"map_info":[{"name":"m1.smap","md5":"aa"},{"name":"m2.smap","md5":"bb"}]})";
        const auto got = r.api->getMapMd5({"m1", "m2.smap"});
        CHECK_EQ(got.at("m1"), std::string("aa"));
        CHECK_EQ(got.at("m2.smap"), std::string("bb"));
        CHECK(r.lastBody().find("\"m1.smap\"") != std::string::npos);
    }
    {
        CASE("요청한 이름이 응답에 없으면 예외 — 빈 md5 가 흘러가면 대조가 조용히 통과한다");
        Rig r(false);
        r.reply[1302] = R"({"ret_code":0,"map_info":[{"name":"m1.smap","md5":"aa"}]})";
        CHECK_THROWS_MSG(r.api->getMapMd5({"m1", "없는맵"}), ProtocolError, "없는맵");
    }

    // ---------- 지령 배선 (게이트 열고) ----------
    {
        CASE("2010 은 duration 을 반드시 싣는다");
        Rig r(true);
        r.api->openLoopMove(0.1, -0.2, 0.3, 600);
        CHECK_EQ(r.lastApi(), std::uint16_t(2010));
        CHECK(r.lastBody().find("\"duration\":600") != std::string::npos);
        CHECK(r.lastBody().find("\"vx\":0.1") != std::string::npos);
    }
    {
        CASE("제어권은 4005/4006, 설정 포트로");
        Rig r(true);
        r.api->seizeControl("big-amr");
        CHECK_EQ(r.lastApi(), std::uint16_t(4005));
        CHECK(r.lastBody().find("\"nick_name\":\"big-amr\"") != std::string::npos);
        r.api->releaseControl();
        CHECK_EQ(r.lastApi(), std::uint16_t(4006));
        CHECK_EQ(r.lastBody(), std::string(""));
    }
    {
        CASE("3051 은 source_id 를 싣고 옵션을 통과시킨다");
        Rig r(true);
        r.api->goTarget("LM1");
        CHECK(r.lastBody().find("\"source_id\":\"SELF_POSITION\"") != std::string::npos);
        r.api->goTarget("LM2", "LM1", Json{{"max_speed", 0.5}});
        CHECK(r.lastBody().find("\"max_speed\":0.5") != std::string::npos);
        CHECK(r.lastBody().find("\"source_id\":\"LM1\"") != std::string::npos);
    }
    {
        CASE("3066 은 move_task_list 로 감싼다");
        Rig r(true);
        r.api->goTargetList(Json::array({Json{{"source_id", "LM1"}, {"id", "LM2"}}}));
        CHECK_EQ(r.lastApi(), std::uint16_t(3066));
        CHECK(r.lastBody().find("\"move_task_list\"") != std::string::npos);
    }
    {
        CASE("translateBy·turnBy 는 부호 규약을 강제한다");
        {
            Rig r(true);
            // dist·angle 은 절대값 — 방향은 vx·vw 의 부호가 정한다
            CHECK_THROWS_MSG(r.api->translateBy(-1.0, 0.1), ProtocolError, "절대값");
            CHECK_THROWS_MSG(r.api->turnBy(-0.5, 0.1), ProtocolError, "절대값");
            // 속도 0 은 무동작이므로 보내지 않는다
            CHECK_THROWS_MSG(r.api->translateBy(1.0, 0.0), ProtocolError, "vx=0");
            CHECK_THROWS_MSG(r.api->turnBy(0.5, 0.0), ProtocolError, "vw=0");
        }
        {
            Rig r(true);
            r.api->translateBy(0.5, -0.1);   // 후진 0.5 m
            CHECK_EQ(r.lastApi(), std::uint16_t(3055));
            CHECK_EQ(r.lastPort(), ports::kTask);
            CHECK(r.lastBody().find("\"dist\":0.5") != std::string::npos);
            CHECK(r.lastBody().find("\"vx\":-0.1") != std::string::npos);
            // mode 는 보내지 않는다 — 자기측위 모드는 벤더가 「현재 사용 불가」로 명시한다
            CHECK(r.lastBody().find("mode") == std::string::npos);
        }
        {
            Rig r(true);
            r.api->turnBy(1.5, 0.2);
            CHECK_EQ(r.lastApi(), std::uint16_t(3056));
            CHECK_EQ(r.lastPort(), ports::kTask);
            CHECK(r.lastBody().find("\"angle\":1.5") != std::string::npos);
            CHECK(r.lastBody().find("\"vw\":0.2") != std::string::npos);
            CHECK(r.lastBody().find("mode") == std::string::npos);
        }

        CASE("restoreFactoryParams 는 전체 공장초기화 요청을 만들 수 없다");
        {
            Rig r(true);
            // 빈 배열 = 로봇이 「전 플러그인 전 파라미터 초기화」로 읽는 형태
            CHECK_THROWS_MSG(r.api->restoreFactoryParams(Json::array()), ProtocolError,
                             "공장 초기화");
            // 객체를 보내면 로봇이 ret_code 60002 로 거부한다 — 보내기 전에 막는다
            CHECK_THROWS_MSG(r.api->restoreFactoryParams(Json::object()), ProtocolError,
                             "JSON 배열");
            // plugin 이 비면 로봇이 그 원소를 조용히 무시한다
            CHECK_THROWS_MSG(r.api->restoreFactoryParams(Json::array({{{"plugin", ""}}})),
                             ProtocolError, "plugin");
            CHECK_THROWS_MSG(r.api->restoreFactoryParams(Json::array({{{"params", Json::array()}}})),
                             ProtocolError, "plugin");
        }
        {
            Rig r(true);
            r.api->restoreFactoryParams(Json::array({{{"plugin", "NetProtocol"},
                                                      {"params", Json::array({"RobotNote"})}}}));
            CHECK_EQ(r.lastApi(), std::uint16_t(4102));
            CHECK_EQ(r.lastPort(), ports::kConfig);
        }

        CASE("setParams 는 save 로 4100/4101 을 가른다");
        Rig r(true);
        const Json body{{"MoveFactory", {{"MaxAcc", 1.0}}}};
        r.api->setParams(body, false);
        CHECK_EQ(r.lastApi(), std::uint16_t(4100));
        r.api->setParams(body, true);
        CHECK_EQ(r.lastApi(), std::uint16_t(4101));
    }
    {
        CASE("소프트 비상정지는 6004");
        Rig r(true);
        r.api->softEstop(true);
        CHECK_EQ(r.lastApi(), std::uint16_t(6004));
        CHECK(r.lastBody().find("\"status\":true") != std::string::npos);
    }
    {
        CASE("필드명 미확인 편호는 dict 를 그대로 싣는다 — 이름을 발명하지 않는다");
        Rig r(true);
        r.api->translate(Json{{"dist", 1.0}});
        CHECK_EQ(r.lastApi(), std::uint16_t(3055));
        CHECK(r.lastBody().find("\"dist\":1.0") != std::string::npos);
        r.api->turn(Json{{"angle", 1.57}});
        CHECK_EQ(r.lastApi(), std::uint16_t(3056));
    }
    {
        CASE("작업 제어 3001/3002/3003");
        Rig r(true);
        r.api->pauseTask();   CHECK_EQ(r.lastApi(), std::uint16_t(3001));
        r.api->resumeTask();  CHECK_EQ(r.lastApi(), std::uint16_t(3002));
        r.api->cancelTask();  CHECK_EQ(r.lastApi(), std::uint16_t(3003));
    }
    {
        CASE("각 API 가 규약대로의 포트로 나간다 — 편호만 보면 오배선을 못 잡는다");
        Rig r(true);
        struct { void (*call)(SeerApi &); std::uint16_t port; const char *what; } wiring[] = {
            {[](SeerApi &a) { a.getPose(); }, ports::kState, "1004 조회"},
            {[](SeerApi &a) { a.getControlOwner(); }, ports::kState, "1060 조회"},
            {[](SeerApi &a) { a.stop(); }, ports::kCtrl, "2000 제어"},
            {[](SeerApi &a) { a.openLoopMove(0, 0, 0, 600); }, ports::kCtrl, "2010 제어"},
            {[](SeerApi &a) { a.confirmLocation(); }, ports::kCtrl, "2003 제어"},
            {[](SeerApi &a) { a.goTarget("LM1"); }, ports::kTask, "3051 작업"},
            {[](SeerApi &a) { a.cancelTask(); }, ports::kTask, "3003 작업"},
            {[](SeerApi &a) { a.seizeControl("x"); }, ports::kConfig, "4005 설정"},
            {[](SeerApi &a) { a.releaseControl(); }, ports::kConfig, "4006 설정"},
            {[](SeerApi &a) { a.clearFatal(); }, ports::kConfig, "4300 설정"},
            {[](SeerApi &a) { a.setDo(1, true); }, ports::kOther, "6001 기타"},
            {[](SeerApi &a) { a.softEstop(true); }, ports::kOther, "6004 기타"},
            {[](SeerApi &a) { a.speaker(Json::object()); }, ports::kOther, "6000 기타"},
        };
        for (const auto &w : wiring)
        {
            w.call(*r.api);
            CHECK_EQ(r.lastPort(), w.port);
        }
    }
    {
        CASE("ret_code 부재와 ret_code=0 을 같게 다룬다");
        Rig r(false);
        r.reply[1004] = R"({"x":1.0})";              // ret_code 없음
        CHECK_NOTHROW(r.api->getPose());
        r.reply[1005] = R"({"ret_code":0,"vx":0.1})"; // ret_code=0
        CHECK_NOTHROW(r.api->getSpeed());
        r.reply[1007] = R"({"ret_code":1})";          // 0 이 아니면 예외
        CHECK_THROWS_MSG(r.api->getBattery(), ProtocolError, "ret_code=1");
    }
    {
        CASE("객체가 아닌 응답에도 죽지 않는다 — value() 가 type_error 를 던지는 경로");
        Rig r(false);
        r.reply[1010] = "[1,2,3]";        // 배열 응답
        CHECK_NOTHROW(r.api->getPath());
        r.reply[1011] = "\"문자열\"";
        CHECK_NOTHROW(r.api->getArea());
    }
    {
        CASE("포트별 전송은 재사용된다");
        Rig r(false);
        r.api->getPose();
        r.api->getSpeed();
        CHECK_EQ(r.owned.size(), std::size_t(1));   // 조회 포트 하나만 열렸다
    }

    return harness::report("test_api");
}
