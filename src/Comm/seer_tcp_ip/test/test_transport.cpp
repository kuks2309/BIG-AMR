// 전송 계층 회귀 시험.
//
// 고정 대상:
//   1. 공식 SDK packMsg 와 **바이트 동일** — 우리가 만든 프레임이 로봇이 받는 프레임과 같은가.
//   2. 부분 수신을 끝까지 모으는가(공식 데모의 recv(1024) 절단 결함을 재도입하지 않는가).
//   3. 응답 편호·seq 를 실제로 대조하는가.
//   4. 요청 간 최소 간격을 지키는가.
//   5. 한도 거부(61001)를 전용 예외로 구분하는가.
#include <cstring>
#include <string>
#include <vector>

#include "fake_stream.hpp"
#include "harness.hpp"
#include "seer_tcp_ip/transport.hpp"

using namespace seer_tcp_ip;

namespace
{

std::string hex(const std::vector<char> &v, std::size_t n)
{
    static const char *d = "0123456789ABCDEF";
    std::string s;
    for (std::size_t i = 0; i < n && i < v.size(); ++i)
    {
        const unsigned char c = static_cast<unsigned char>(v[i]);
        s += d[c >> 4];
        s += d[c & 0xF];
    }
    return s;
}

struct FakeClock
{
    std::int64_t now = 0;
    std::vector<std::int64_t> slept;
    ClockMs clock() { return [this] { return now; }; }
    SleepMs sleep()
    {
        return [this](std::int64_t ms) {
            slept.push_back(ms);
            now += ms;
        };
    }
};

}  // namespace

int main()
{
    // ---------- 1. 프레임 생성 ----------
    {
        CASE("무파라미터 프레임은 16B, 헤더 각 바이트가 사양대로");
        const std::vector<char> f = pack(0x1234, 1009);
        CHECK_EQ(f.size(), std::size_t(16));
        //  5A   01  |  1234  |  00000000  |  03F1  |  000000000000
        //  sync ver    seq        len=0        1009     예약 6B
        CHECK_EQ(hex(f, 16), std::string("5A0112340000000003F1000000000000"));
    }
    {
        CASE("본문이 있으면 길이 필드가 본문 바이트 수와 같다");
        const Json msg{{"x", 10.0}};
        const std::vector<char> f = pack(7, 2002, msg);
        const std::string body = msg.dump();
        CHECK_EQ(f.size(), 16 + body.size());
        const Head h = unpackHead(f.data(), 16);
        CHECK_EQ(h.jsonLen, static_cast<std::uint32_t>(body.size()));
        CHECK_EQ(h.apiType, std::uint16_t(2002));
        CHECK_EQ(h.seq, std::uint16_t(7));
    }
    {
        CASE("빈 객체는 본문을 붙이지 않는다 — 공식 packMsg 의 if(msg != {}) 분기");
        for (std::uint16_t api : {std::uint16_t(1000), std::uint16_t(1004), std::uint16_t(1050)})
        {
            CHECK_EQ(pack(1, api, Json::object()).size(), std::size_t(16));
            CHECK_EQ(pack(1, api).size(), std::size_t(16));
        }
    }
    {
        CASE("예약 6바이트가 0 으로 채워진다");
        const std::vector<char> f = pack(1, 1000);
        for (int i = 10; i < 16; ++i)
        {
            CHECK_EQ(f[i], char(0));
        }
    }

    // ---------- 2. 헤더 해석 ----------
    {
        CASE("짧은 버퍼 거부");
        const char buf[3] = {0x5A, 0x01, 0x00};
        CHECK_THROWS_MSG(unpackHead(buf, 3), ProtocolError, "헤더 길이");
    }
    {
        CASE("sync 불일치 거부");
        std::string r = fake::makeResponse(1, 11009, "{}", 0x00);
        CHECK_THROWS_MSG(unpackHead(r.data(), 16), ProtocolError, "sync");
    }

    // ---------- 3. 수신 ----------
    {
        CASE("1바이트씩 와도 끝까지 모은다");
        fake::Stream s;
        s.chunk = 1;
        s.reset(fake::makeResponse(1, 11009, R"({"ret_code":0,"lasers":[1,2,3]})"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        const Json r = tr.request(1009);
        CHECK_EQ(r["lasers"].size(), std::size_t(3));
    }
    {
        CASE("큰 응답이 잘리지 않는다 — recv(1024) 절단 결함 재도입 금지");
        std::string big = "{\"ret_code\":0,\"beams\":[";
        for (int i = 0; i < 2000; ++i)
        {
            big += (i ? "," : "") + std::to_string(i);
        }
        big += "]}";
        fake::Stream s;
        s.chunk = 997;
        s.reset(fake::makeResponse(1, 11009, big));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_EQ(tr.request(1009)["beams"].size(), std::size_t(2000));
    }
    {
        CASE("수신 중 끊기면 예외 + 소켓 정리");
        fake::Stream s;
        const std::string full = fake::makeResponse(1, 11009, "{}");
        s.reset(full.substr(0, 10));  // 헤더도 못 채우고 끊김
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_THROWS_MSG(tr.request(1009), TransportError, "수신 중 연결 종료");
        CHECK(!tr.isConnected());
    }

    // ---------- 4. 대조 ----------
    {
        CASE("엉뚱한 응답 편호 거부");
        fake::Stream s;
        s.reset(fake::makeResponse(1, 60000, "{}"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_THROWS_MSG(tr.request(1009), ProtocolError, "60000");
    }
    {
        CASE("seq 반향 불일치 거부");
        fake::Stream s;
        s.reset(fake::makeResponse(999, 11009, "{}"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_THROWS_MSG(tr.request(1009), ProtocolError, "seq");
    }
    {
        CASE("seq 는 고정이 아니라 순환한다");
        fake::Stream s;
        std::vector<std::uint16_t> seqs;
        s.onWrite = [&seqs](fake::Stream &st, const std::vector<char> &f) {
            const Head h = unpackHead(f.data(), 16);
            seqs.push_back(h.seq);
            st.reset(fake::makeResponse(h.seq, 11004, "{}"));
        };
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        for (int i = 0; i < 3; ++i)
        {
            tr.request(1004);
        }
        const std::vector<std::uint16_t> want = {1, 2, 3};
        CHECK_EQ(seqs, want);
    }
    {
        CASE("expectType 지정(4011 → 14011)");
        fake::Stream s;
        s.reset(fake::makeResponse(1, 14011, "{}"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_NOTHROW(tr.request(4011, Json::object(), 14011));
    }

    // ---------- 5. 한도 거부 ----------
    {
        CASE("한도 거부는 전용 예외 — 편호가 포트 번호로 온다");
        fake::Stream s;
        s.reset(fake::makeResponse(
            1, ports::kState,
            R"({"ret_code":61001,"err_msg":"reach the maximum of status api connection limitation"})"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_THROWS_MSG(tr.request(1004), ConnectionLimitError, "61001");
    }
    {
        CASE("한도 예외는 ProtocolError 의 하위 — 기존 호출자를 안 깬다");
        fake::Stream s;
        s.reset(fake::makeResponse(1, ports::kState, R"({"ret_code":61001,"err_msg":"x"})"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        CHECK_THROWS_MSG(tr.request(1004), ProtocolError, "61001");
    }
    {
        CASE("포트 번호가 아닌 편호 불일치는 일반 예외로 남는다");
        fake::Stream s;
        s.reset(fake::makeResponse(1, 60000, R"({"ret_code":61001})"));
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s));
        bool wasLimit = false;
        try
        {
            tr.request(1004);
        }
        catch (const ConnectionLimitError &)
        {
            wasLimit = true;
        }
        catch (const ProtocolError &)
        {
        }
        CHECK(!wasLimit);
    }

    // ---------- 6. 스로틀 ----------
    {
        CASE("요청 간 최소 간격을 지킨다");
        fake::Stream s;
        s.onWrite = [](fake::Stream &st, const std::vector<char> &f) {
            const Head h = unpackHead(f.data(), 16);
            st.reset(fake::makeResponse(h.seq, 11004, "{}"));
        };
        FakeClock fc;
        Transport tr("1.2.3.4", ports::kState, 1.0, 100, fake::factoryFor(&s), fc.clock(),
                     fc.sleep());
        tr.request(1004);
        CHECK(fc.slept.empty());     // 첫 요청은 대기 없음
        tr.request(1004);            // 즉시 재요청 → 100ms 대기
        CHECK_EQ(fc.slept.size(), std::size_t(1));
        CHECK_EQ(fc.slept[0], std::int64_t(100));
        fc.now += 5000;
        tr.request(1004);            // 충분히 지난 뒤 → 추가 대기 없음
        CHECK_EQ(fc.slept.size(), std::size_t(1));
    }
    {
        CASE("간격 0 이면 대기하지 않는다");
        fake::Stream s;
        s.onWrite = [](fake::Stream &st, const std::vector<char> &f) {
            const Head h = unpackHead(f.data(), 16);
            st.reset(fake::makeResponse(h.seq, 11004, "{}"));
        };
        FakeClock fc;
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, fake::factoryFor(&s), fc.clock(), fc.sleep());
        tr.request(1004);
        tr.request(1004);
        CHECK(fc.slept.empty());
    }

    // ---------- 7. 연결 수명 ----------
    {
        CASE("연결 실패는 죽은 스트림을 남기지 않는다 — 다음 요청이 새로 연결한다");
        // 실기 실패경로에서 드러난 결함: 실패한 connect 뒤 stream_ 이 남아 다음 요청이
        // 죽은 서술자에 send 를 걸고 `Bad file descriptor` 로 한 번 더 헛돌았다.
        struct Flaky : IByteStream
        {
            int *attempts;
            bool *failNext;
            std::string body;
            std::size_t pos = 0;
            bool open = false;
            void connect(const std::string &, std::uint16_t, double) override
            {
                ++(*attempts);
                if (*failNext)
                {
                    throw TransportError("connect 실패(시험)");
                }
                open = true;
            }
            std::size_t read(char *b, std::size_t n) override
            {
                const std::size_t take = std::min(n, body.size() - pos);
                if (take == 0) { return 0; }
                std::memcpy(b, body.data() + pos, take);
                pos += take;
                return take;
            }
            void writeAll(const char *, std::size_t) override
            {
                if (!open) { throw TransportError("Bad file descriptor"); }
            }
            void close() override { open = false; }
            bool isOpen() const override { return open; }
        };
        int attempts = 0;
        bool failNext = true;
        auto factory = [&attempts, &failNext]() -> std::unique_ptr<IByteStream> {
            auto f = std::unique_ptr<Flaky>(new Flaky());
            f->attempts = &attempts;
            f->failNext = &failNext;
            f->body = fake::makeResponse(1, 11004, "{}");
            return f;
        };
        Transport tr("1.2.3.4", ports::kState, 1.0, 0, factory);
        CHECK_THROWS_MSG(tr.request(1004), TransportError, "connect 실패");
        CHECK(!tr.isConnected());          // 죽은 스트림이 남으면 안 된다
        failNext = false;
        CHECK_NOTHROW(tr.request(1004));   // 다음 요청은 새로 연결해 성공한다
        CHECK_EQ(attempts, 2);
    }
    {
        CASE("connect 는 멱등, close 후 재연결");
        fake::Stream s;
        s.reset(fake::makeResponse(1, 11004, "{}"));
        Transport tr("9.9.9.9", ports::kState, 1.0, 0, fake::factoryFor(&s));
        tr.connect();
        tr.connect();
        CHECK(tr.isConnected());
        CHECK_EQ(s.connectedIp, std::string("9.9.9.9"));
        CHECK_EQ(s.connectedPort, ports::kState);
        tr.close();
        CHECK(!tr.isConnected());
    }

    return harness::report("test_transport");
}
