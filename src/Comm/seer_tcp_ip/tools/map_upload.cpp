// 편집한 .smap 을 로봇에 올린다(4010) — 기본은 예행이고, 올리기 전에 반드시 백업한다.
//
// 업로드는 로봇의 지도 파일을 **덮어쓴다**. 되돌릴 수단은 업로드 직전에 받아 둔 원본뿐이므로,
// 이 도구는 백업을 성공시키지 못하면 올리지 않는다.
//
// 절차:
//   1) 4011 로 로봇의 현재 사본을 내려받아 파일로 저장한다(백업). 실패하면 중단.
//   2) 올릴 파일과 백업을 비교해 무엇이 바뀌는지 보여준다.
//   3) 장애물 점군·반사판·스테이션 수가 달라지면 중단한다 — 이 도구는 경로 정리용이다.
//      정말 그것까지 바꾸려면 --allow-structural.
//   4) --yes 가 있어야 실제로 올린다(없으면 여기서 끝, 예행).
//   5) 올린 뒤 다시 내려받아 **값**으로 대조한다 — 로봇이 키를 재정렬하므로 바이트 비교는 못 쓴다.
//   6) --activate 면 2022 로 그 지도로 전환한다.
//
// 사용:
//   ros2 run seer_tcp_ip map_upload --file <새.smap> --backup <폴더>            # 예행
//   ros2 run seer_tcp_ip map_upload --file <새.smap> --backup <폴더> --yes
//   ros2 run seer_tcp_ip map_upload --file <새.smap> --backup <폴더> --yes --activate
//   환경변수 SEER_IP 로 대상 지정(기본 192.168.44.82)
//
// 종료 코드:
//   0 성공(또는 예행 완료)   1 통신·프로토콜 실패      2 인자 오류
//   3 백업 실패 — 올리지 않았다                        4 구조 변경 감지 — 올리지 않았다
//   5 업로드 후 값 대조 불일치 — 백업 파일로 되돌릴 것
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

#include "seer_tcp_ip/api.hpp"

namespace
{

std::string readFile(const std::string &path)
{
    std::ifstream in(path, std::ios::binary);
    if (!in) { throw std::runtime_error("파일을 열 수 없다: " + path); }
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

void writeFile(const std::string &path, const std::string &data)
{
    std::ofstream out(path, std::ios::binary);
    if (!out) { throw std::runtime_error("파일을 쓸 수 없다: " + path); }
    out << data;
}

std::size_t countOf(const seer_tcp_ip::Json &m, const char *key)
{
    return m.contains(key) && m[key].is_array() ? m[key].size() : 0;
}

void report(const char *what, std::size_t before, std::size_t after)
{
    std::printf("  %-18s %5zu → %5zu%s\n", what, before, after,
                before == after ? "" : "   ← 바뀐다");
}

}  // namespace

int main(int argc, char **argv)
{
    std::string file, backupDir;
    bool yes = false, activate = false, allowStructural = false;
    for (int i = 1; i < argc; ++i)
    {
        const std::string a = argv[i];
        if (a == "--file" && i + 1 < argc) { file = argv[++i]; }
        else if (a == "--backup" && i + 1 < argc) { backupDir = argv[++i]; }
        else if (a == "--yes") { yes = true; }
        else if (a == "--activate") { activate = true; }
        else if (a == "--allow-structural") { allowStructural = true; }
    }
    if (file.empty() || backupDir.empty())
    {
        std::fprintf(stderr, "사용: map_upload --file <새.smap> --backup <폴더> [--yes] [--activate]\n");
        return 2;
    }

    const char *env = std::getenv("SEER_IP");
    const std::string ip = env ? env : "192.168.44.82";

    try
    {
        const std::string payload = readFile(file);
        const auto fresh = seer_tcp_ip::Json::parse(payload);
        const std::string mapName = fresh.at("header").at("mapName").get<std::string>();
        std::printf("대상 %s   올릴 파일 %s   지도 이름 %s\n", ip.c_str(), file.c_str(),
                    mapName.c_str());

        seer_tcp_ip::SeerApi api(ip, 8.0, /*allowGuarded=*/true);

        // 1) 백업 — 이것이 실패하면 되돌릴 수단이 없으므로 올리지 않는다.
        const std::string backupPath = backupDir + "/" + mapName + ".backup.smap";
        const auto originalBytes = api.downloadMap(mapName);
        const std::string original(originalBytes.begin(), originalBytes.end());
        writeFile(backupPath, original);
        std::printf("백업       %s (%zu B)\n", backupPath.c_str(), original.size());

        // 2)·3) 무엇이 바뀌는지 — 경로 외의 변화는 막는다.
        const auto old = seer_tcp_ip::Json::parse(original);
        std::printf("차이:\n");
        report("장애물 점군", countOf(old, "normalPosList"), countOf(fresh, "normalPosList"));
        report("반사판", countOf(old, "rssiPosList"), countOf(fresh, "rssiPosList"));
        report("스테이션", countOf(old, "advancedPointList"), countOf(fresh, "advancedPointList"));
        report("경로", countOf(old, "advancedCurveList"), countOf(fresh, "advancedCurveList"));

        const bool structural =
            countOf(old, "normalPosList") != countOf(fresh, "normalPosList") ||
            countOf(old, "rssiPosList") != countOf(fresh, "rssiPosList") ||
            countOf(old, "advancedPointList") != countOf(fresh, "advancedPointList") ||
            old.at("header") != fresh.at("header");
        if (structural && !allowStructural)
        {
            std::fprintf(stderr,
                         "✗ 경로 말고 다른 것이 바뀐다(점군·반사판·스테이션·header). "
                         "이 도구는 경로 정리용이다 — 정말 하려면 --allow-structural.\n");
            return 4;
        }

        if (!yes)
        {
            std::printf("\n예행이다 — 아무것도 올리지 않았다. 실제로 올리려면 --yes.\n");
            return 0;
        }

        // 4) 업로드
        api.uploadMap(fresh);
        std::printf("4010 업로드 : 수리됨\n");

        // 5) 되받아 값으로 대조 — 「수리됨」과 「반영됨」은 다르다.
        //    ⚠ 바이트로 비교하지 않는다. 로봇은 받은 JSON 을 **키 알파벳순으로 재직렬화**해
        //    저장하므로(우리는 header 부터, 로봇은 advancedCurveList 부터 쓴다) 길이가 같아도
        //    바이트는 어긋난다. 보증해야 하는 것은 값이 같다는 것이다.
        const auto echoedBytes = api.downloadMap(mapName);
        const std::string echoed(echoedBytes.begin(), echoedBytes.end());
        const bool same = seer_tcp_ip::Json::parse(echoed) == fresh;
        std::printf("4011 대조   : %zu B ← %zu B   값 %s%s\n", echoed.size(), payload.size(),
                    same ? "일치 ✓" : "불일치 ✗",
                    echoed == payload ? "" : "  (바이트는 다름 — 로봇의 키 정렬)");
        if (!same)
        {
            std::fprintf(stderr,
                         "‼ 올린 값과 로봇에 저장된 값이 다르다. 백업 %s 로 되돌릴 것.\n",
                         backupPath.c_str());
            return 5;
        }

        // 6) 전환
        if (activate)
        {
            api.loadMap(mapName);
            std::printf("2022 전환   : 수리됨 — 1022 로드상태·1300 md5 로 확인할 것\n");
        }
        else
        {
            std::printf("\n올렸지만 전환하지 않았다 — 활성 지도를 바꾸려면 --activate.\n");
        }
        return 0;
    }
    catch (const std::exception &e)
    {
        std::fprintf(stderr, "✗ 실패: %s\n", e.what());
        return 1;
    }
}
