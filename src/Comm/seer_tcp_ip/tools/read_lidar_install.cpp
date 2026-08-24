// SEER SRC 에서 라이다 장착 pose(install_info)를 조회해 출력한다.
//
// 재장착·재캘리브 시 이 도구로 최신 값을 읽어 seer_lidar_tf 의 LIDARS 상수를 갱신한다.
// 조회 포트(19204)만 쓰므로 지령 게이트에 걸리지 않는다.
//
// 사용: ros2 run seer_tcp_ip read_lidar_install [SEER_IP]
#include <cstdio>
#include <string>

#include "seer_tcp_ip/api.hpp"

int main(int argc, char **argv)
{
    const std::string ip = argc > 1 ? argv[1] : "192.168.44.82";
    try
    {
        seer_tcp_ip::SeerApi api(ip, 3.0);
        const seer_tcp_ip::Json lasers = api.getLasers();
        std::printf("# SEER %s:%u API %u (install_info)\n", ip.c_str(),
                    seer_tcp_ip::ports::kState, seer_tcp_ip::api::kLaser);
        std::printf("# seer_lidar_tf 의 LIDARS 에 반영할 값:\n");
        for (const auto &laser : lasers)
        {
            const std::string name =
                laser.value("device_info", seer_tcp_ip::Json::object()).value("device_name", "?");
            const auto ii = laser.value("install_info", seer_tcp_ip::Json::object());
            std::string low;
            for (char c : name)
            {
                low += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            }
            const std::string child = low.find("front") != std::string::npos  ? "scan_front"
                                      : low.find("rear") != std::string::npos ? "scan_rear"
                                                                              : name;
            std::printf("    (\"%s\", %.17g, %.17g, 0.0, %.17g),  # %s\n", child.c_str(),
                        ii.value("x", 0.0), ii.value("y", 0.0), ii.value("yaw", 0.0), name.c_str());
        }
        return 0;
    }
    catch (const std::exception &e)
    {
        std::fprintf(stderr, "조회 실패: %s\n", e.what());
        return 1;
    }
}
