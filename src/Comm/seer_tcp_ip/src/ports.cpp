#include "seer_tcp_ip/ports.hpp"

namespace seer_tcp_ip
{
namespace ports
{

const std::map<std::uint16_t, std::string> &maxConnectionParam()
{
    static const std::map<std::uint16_t, std::string> kMap = {
        {kState, "RobotStatusAPITCPServerMaxConnections"},
        {kCtrl, "RobotControlAPITCPServerMaxConnections"},
        {kTask, "RobotTaskAPITCPServerMaxConnections"},
        {kConfig, "RobotConfigAPITCPServerMaxConnections"},
        {kOther, "RobotOtherAPITCPServerMaxConnections"},
        {kPush, "RobotPushTCPServerMaxConnections"},
    };
    return kMap;
}

const std::map<std::uint16_t, int> &observedMaxConnections()
{
    static const std::map<std::uint16_t, int> kMap = {
        {kState, 10}, {kCtrl, 5}, {kTask, 5}, {kConfig, 5}, {kOther, 5}, {kPush, 10},
    };
    return kMap;
}

const std::set<std::uint16_t> &guardedPorts()
{
    static const std::set<std::uint16_t> kSet = {
        kCtrl,    // 2000 정지 · 2002 재측위 · 2010 개루프 주행
        kTask,    // 3051 자율 주행
        kConfig,  // 4100 파라미터 쓰기 · 4005 제어권 (4011 맵 다운로드는 읽기지만 포트 단위로 묶는다)
        kOther,   // 6001 DO 출력 · 6004 소프트 비상정지
    };
    return kSet;
}

bool isGuarded(std::uint16_t port)
{
    return guardedPorts().count(port) > 0;
}

int observedMaxConnectionsFor(std::uint16_t port)
{
    const auto it = observedMaxConnections().find(port);
    return it == observedMaxConnections().end() ? -1 : it->second;
}

}  // namespace ports
}  // namespace seer_tcp_ip
