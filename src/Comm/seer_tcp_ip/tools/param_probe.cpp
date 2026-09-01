// 파라미터 쓰기 경로를 실기로 확인한다 — 4100(휘발) 로 썼다가 원래 값으로 되돌린다.
//
// 확인하는 것: 1400 읽기 → 4100 쓰기 → 1400 되읽기(바뀌었는가) → 4100 원복 → 1400 확인(돌아왔는가).
// SeerApi::setParams(save=false) 와 getParam 의 계약이 실기에서 성립하는지 본다.
//
// 왜 4100 인가 — 4101 은 디스크에 저장한다. 4100 은 휘발이라 전원을 다시 넣으면 원래 값으로
// 돌아온다. 원복에 실패해도 영구 손상이 남지 않는 쪽을 고른다.
//
// 안전 설계:
//   · 대상은 **허용 목록**에 있는 파라미터만. 기본은 `NetProtocol.RobotNote`(자유 메모 칸,
//     현재 비어 있음) — 모션·연결·안전 어디에도 관여하지 않는다.
//   · 원복 실패 시 원래 값을 화면에 크게 남긴다. 사람이 손으로 되돌릴 수 있어야 한다.
//   · 로봇을 움직이지 않는다.
//
// 사용:
//   ros2 run seer_tcp_ip param_probe                       # NetProtocol.RobotNote 왕복
//   ros2 run seer_tcp_ip param_probe <플러그인> <파라미터>   # 허용 목록에 있어야 한다
//   환경변수 SEER_IP 로 대상 지정(기본 192.168.44.82)
//
// 종료 코드:
//   0 왕복 성공(썼고, 보였고, 되돌아왔다)   1 통신·프로토콜 실패
//   2 허용 목록 밖 파라미터                 3 문자열이 아닌 파라미터
//   4 4100 이 수리됐는데 1400 이 옛 값       5 원복 실패(원래 값을 화면에서 확인할 것)
#include <cstdio>
#include <cstdlib>
#include <set>
#include <string>
#include <utility>

#include "seer_tcp_ip/api.hpp"

namespace
{

/// 쓰기를 허용하는 파라미터. 「모션·연결·안전에 관여하지 않고 되돌릴 수 있다」가 기준이다.
const std::set<std::pair<std::string, std::string>> &allowList()
{
    static const std::set<std::pair<std::string, std::string>> kAllowed = {
        {"NetProtocol", "RobotNote"},  // 자유 메모 칸
    };
    return kAllowed;
}

seer_tcp_ip::Json readValue(seer_tcp_ip::SeerApi &api, const std::string &plugin,
                            const std::string &param)
{
    const auto resp = api.getParam(plugin, param);
    if (!resp.contains(plugin) || !resp[plugin].contains(param))
    {
        throw seer_tcp_ip::ProtocolError("1400 응답에 " + plugin + "." + param + " 이 없다");
    }
    const auto &d = resp[plugin][param];
    if (!d.contains("value"))
    {
        throw seer_tcp_ip::ProtocolError("1400 응답에 value 가 없다");
    }
    return d["value"];
}

}  // namespace

int main(int argc, char **argv)
{
    const std::string plugin = argc >= 3 ? argv[1] : "NetProtocol";
    const std::string param = argc >= 3 ? argv[2] : "RobotNote";
    const char *env = std::getenv("SEER_IP");
    const std::string ip = env ? env : "192.168.44.82";

    if (allowList().count({plugin, param}) == 0)
    {
        std::fprintf(stderr,
                     "✗ %s.%s 는 쓰기 허용 목록에 없다 — 이 도구는 모션·연결·안전에 관여하지 않고\n"
                     "  되돌릴 수 있는 파라미터만 건드린다. 목록은 tools/param_probe.cpp 에 있다.\n",
                     plugin.c_str(), param.c_str());
        return 2;
    }

    seer_tcp_ip::Json original;
    bool wrote = false;
    try
    {
        seer_tcp_ip::SeerApi api(ip, 4.0, /*allowGuarded=*/true);
        std::printf("대상: %s  파라미터: %s.%s\n", ip.c_str(), plugin.c_str(), param.c_str());

        original = readValue(api, plugin, param);
        std::printf("1400 사전 : value=%s\n", original.dump().c_str());

        // 되돌릴 수 있는 표식. 원래가 문자열이 아니면 허용 목록에 넣지 않았으므로 여기 오지 않는다.
        if (!original.is_string())
        {
            std::fprintf(stderr, "✗ 문자열 파라미터만 다룬다(현재 타입: %s)\n",
                         original.type_name());
            return 3;
        }
        const std::string probeValue = "seer_tcp_ip param_probe";

        api.setParams(seer_tcp_ip::Json{{plugin, {{param, probeValue}}}}, /*save=*/false);
        wrote = true;
        std::printf("4100 쓰기 : value=\"%s\" (휘발 — 전원 재인가로 원복)\n", probeValue.c_str());

        const auto after = readValue(api, plugin, param);
        std::printf("1400 확인 : value=%s → %s\n", after.dump().c_str(),
                    after == seer_tcp_ip::Json(probeValue) ? "쓰기가 반영됐다 ✓"
                                                           : "✗ 반영되지 않았다");
        if (after != seer_tcp_ip::Json(probeValue))
        {
            std::fprintf(stderr,
                         "✗ 4100 이 ret_code 0 을 냈는데 1400 이 옛 값을 보인다 — "
                         "「수리됨」과 「반영됨」이 다르다.\n");
            api.setParams(seer_tcp_ip::Json{{plugin, {{param, original}}}}, false);
            return 4;
        }

        api.setParams(seer_tcp_ip::Json{{plugin, {{param, original}}}}, /*save=*/false);
        const auto restored = readValue(api, plugin, param);
        wrote = (restored != original);
        std::printf("4100 원복 : value=%s → %s\n", restored.dump().c_str(),
                    wrote ? "✗ 원복 실패" : "원래 값으로 돌아왔다 ✓");
        if (wrote)
        {
            std::fprintf(stderr, "\n‼ 원복 실패 — 원래 값은 %s 였다. 손으로 되돌릴 것.\n",
                         original.dump().c_str());
            return 5;
        }

        std::printf("\n파라미터 쓰기 경로 실기 확인 완료 — 1400 → 4100 → 1400 → 4100 → 1400.\n");
        std::printf("⚠ 4101(디스크 저장)·모션 파라미터는 여전히 미검증이다.\n");
        return 0;
    }
    catch (const std::exception &e)
    {
        std::fprintf(stderr, "✗ 실패: %s\n", e.what());
        if (wrote)
        {
            std::fprintf(stderr, "‼ 쓰기 뒤에 실패했다 — 원래 값은 %s. 손으로 되돌릴 것.\n",
                         original.dump().c_str());
        }
        return 1;
    }
}
