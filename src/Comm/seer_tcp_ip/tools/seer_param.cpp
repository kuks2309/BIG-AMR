// Seer 파라미터를 실기에 직접 물어본다.
//
// Seer 의 동작 상수 다수(포트 동시연결 한도 포함)는 문서가 정하는 값이 아니라 로봇의
// 런타임 파라미터다. 매뉴얼로는 확정할 수 없고 로봇에 물어야 한다.
//
// 사용:
//   ros2 run seer_tcp_ip seer_param                       # 포트 동시연결 한도 6종
//   ros2 run seer_tcp_ip seer_param <플러그인> <파라미터>   # 임의 파라미터
//   환경변수 SEER_IP 로 대상 지정(기본 192.168.44.82)
#include <cstdio>
#include <cstdlib>
#include <string>

#include "seer_tcp_ip/api.hpp"

namespace
{

void printOne(seer_tcp_ip::SeerApi &api, const std::string &plugin, const std::string &param,
              const char *label)
{
    try
    {
        const auto resp = api.getParam(plugin, param);
        const auto d = resp.value(plugin, seer_tcp_ip::Json::object())
                           .value(param, seer_tcp_ip::Json::object());
        if (d.empty())
        {
            std::printf("  %-14s %-46s (응답에 항목 없음)\n", label, param.c_str());
            return;
        }
        std::printf("  %-14s %-46s value=%s default=%s range=%s~%s\n", label, param.c_str(),
                    d.value("value", seer_tcp_ip::Json()).dump().c_str(),
                    d.value("defaultValue", seer_tcp_ip::Json()).dump().c_str(),
                    d.value("minValue", seer_tcp_ip::Json()).dump().c_str(),
                    d.value("maxValue", seer_tcp_ip::Json()).dump().c_str());
    }
    catch (const std::exception &e)
    {
        std::printf("  %-14s %-46s 실패: %s\n", label, param.c_str(), e.what());
    }
}

}  // namespace

int main(int argc, char **argv)
{
    const char *env = std::getenv("SEER_IP");
    const std::string ip = env ? env : "192.168.44.82";
    try
    {
        seer_tcp_ip::SeerApi api(ip, 4.0);
        if (argc >= 3)
        {
            printOne(api, argv[1], argv[2], "");
            return 0;
        }
        std::printf("=== Seer 포트 동시연결 한도 — 실기 %s ===\n", ip.c_str());
        std::printf("⚠ 문서 판본이 정하는 상수가 아니라 런타임 파라미터다(변경 가능).\n");
        const struct { std::uint16_t port; const char *label; } kPorts[] = {
            {seer_tcp_ip::ports::kState, "19204 Status"},
            {seer_tcp_ip::ports::kCtrl, "19205 Control"},
            {seer_tcp_ip::ports::kTask, "19206 Task"},
            {seer_tcp_ip::ports::kConfig, "19207 Config"},
            {seer_tcp_ip::ports::kOther, "19210 Other"},
            {seer_tcp_ip::ports::kPush, "19301 Push"},
        };
        for (const auto &p : kPorts)
        {
            const auto it = seer_tcp_ip::ports::maxConnectionParam().find(p.port);
            if (it != seer_tcp_ip::ports::maxConnectionParam().end())
            {
                printOne(api, "NetProtocol", it->second, p.label);
            }
        }
        return 0;
    }
    catch (const std::exception &e)
    {
        std::fprintf(stderr, "실패: %s\n", e.what());
        return 1;
    }
}
