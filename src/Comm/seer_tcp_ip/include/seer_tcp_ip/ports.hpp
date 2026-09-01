// Seer(SRC) Robokit TCP API 포트 정책.
//
// 동시연결 한도는 고정 상수가 아니라 로봇의 런타임 파라미터다
// (Robot<카테고리>APITCPServerMaxConnections, uint32, 1~20, 기체·시점마다 바뀔 수 있다).
// 아래 표는 관측 기본값이며 정확한 값은 SeerApi::getMaxConnections() 로 로봇에 묻는다.
#ifndef SEER_TCP_IP_PORTS_HPP_
#define SEER_TCP_IP_PORTS_HPP_

#include <cstdint>
#include <map>
#include <set>
#include <string>

namespace seer_tcp_ip
{
namespace ports
{

// 포트 상수 — 공식 SDK 이름 유지(원문 대조가 가능해야 한다)
inline constexpr std::uint16_t kRobod = 19200;   // 코어 데몬
inline constexpr std::uint16_t kState = 19204;   // 조회
inline constexpr std::uint16_t kCtrl = 19205;    // 즉시 제어
inline constexpr std::uint16_t kTask = 19206;    // 내비게이션·작업
inline constexpr std::uint16_t kConfig = 19207;  // 파라미터·맵 설정
inline constexpr std::uint16_t kKernel = 19208;  // 종료·재시작
inline constexpr std::uint16_t kOther = 19210;   // DO·스피커
inline constexpr std::uint16_t kPush = 19301;    // 로봇 능동 push

/// 요청 간 최소 간격(ms). 과빈번 요청은 로봇이 연결을 정리하는 사유가 된다.
inline constexpr int kMinRequestIntervalMs = 100;

/// 응답 편호 = 요청 편호 + 이 값. 오류 응답은 이 규칙을 따르지 않는다.
inline constexpr std::uint16_t kResponseTypeOffset = 10000;

/// 한도 초과 시 로봇이 내는 ret_code. 그 거부 응답의 편호는 요청+10000 이 아니라
/// 포트 번호 그대로이고, 본문 err_msg 는 "reach the maximum of … connection limitation".
inline constexpr int kConnectionLimitRetCode = 61001;

/// 제어권 없이 지령했을 때 로봇이 내는 ret_code. 4005 를 먼저 잡아야 한다.
inline constexpr int kControlPreemptedRetCode = 40020;

/// 포트 → 한도 파라미터 이름 (API 1400 으로 조회).
const std::map<std::uint16_t, std::string> &maxConnectionParam();

/// Foil_A082(rbk 3.4.5.22) 관측 기본값. 정본이 아니다 — 판정은 getMaxConnections() 로 한다.
const std::map<std::uint16_t, int> &observedMaxConnections();

/// 라이브러리 직결을 막는 포트 — 연결 수가 부족해서가 아니라 지령이 겹치면 위험해서다.
/// 한도는 5 이고 초과는 거부형(기존 연결 유지)이라 선점 위험은 없다. 그래도 막는 이유는 중재다 —
/// 두 주체가 동시에 로봇을 움직이거나 설정을 쓰면 소켓이 남아돌아도 사고가 난다.
/// 이 집합은 명시 집합이다. 한도에서 파생하면 5 > 1 이라 비어서 게이트가 조용히 사라진다.
const std::set<std::uint16_t> &guardedPorts();

/// 지령·설정 포트인가.
bool isGuarded(std::uint16_t port);

/// 관측 한도. 미관측 포트는 -1.
int observedMaxConnectionsFor(std::uint16_t port);

}  // namespace ports
}  // namespace seer_tcp_ip

#endif  // SEER_TCP_IP_PORTS_HPP_
