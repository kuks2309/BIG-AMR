// Seer(SRC) Robokit TCP API 바인딩 — 편호를 이름으로 감싼다.
//
// 19204(Status)·19301(Push) 는 조회라 직결이 열려 있고, 19205/06/07/19210 은 지령·설정이라
// allowGuarded=true 없이는 막힌다.
#ifndef SEER_TCP_IP_API_HPP_
#define SEER_TCP_IP_API_HPP_

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "seer_tcp_ip/ports.hpp"
#include "seer_tcp_ip/transport.hpp"

namespace seer_tcp_ip
{
namespace api
{

// 조회 — 19204 Status
inline constexpr std::uint16_t kRobotInfo = 1000;      // model, vehicle_id, version
inline constexpr std::uint16_t kRunInfo = 1002;        // 운행시간·주행거리
inline constexpr std::uint16_t kMode = 1003;
inline constexpr std::uint16_t kLoc = 1004;            // x, y, angle
inline constexpr std::uint16_t kSpeed = 1005;          // vx, vy, w, steer_angles
inline constexpr std::uint16_t kBlocked = 1006;
inline constexpr std::uint16_t kBattery = 1007;
inline constexpr std::uint16_t kBrake = 1008;
inline constexpr std::uint16_t kLaser = 1009;          // lasers[].install_info / beams
inline constexpr std::uint16_t kPath = 1010;
inline constexpr std::uint16_t kArea = 1011;
inline constexpr std::uint16_t kEstop = 1012;          // emergency/soft_emc/driver_emc/electric
inline constexpr std::uint16_t kIo = 1013;
inline constexpr std::uint16_t kTaskStatus = 1020;
inline constexpr std::uint16_t kRelocStatus = 1021;
inline constexpr std::uint16_t kLoadmapStatus = 1022;
inline constexpr std::uint16_t kSlamStatus = 1025;     // {"return_resultmap": bool}
inline constexpr std::uint16_t kMotorInfo = 1040;      // encoder·position
inline constexpr std::uint16_t kAlarm = 1050;          // fatals / errors / warnings
inline constexpr std::uint16_t kControlOwner = 1060;   // locked, ip, nick_name
inline constexpr std::uint16_t kAll = 1100;
inline constexpr std::uint16_t kAll2 = 1101;           // steer·r_steer(rad)
inline constexpr std::uint16_t kAll3 = 1102;
inline constexpr std::uint16_t kInitStatus = 1111;
inline constexpr std::uint16_t kMapStatus = 1300;      // current_map, current_map_md5, maps[]
inline constexpr std::uint16_t kStations = 1301;
inline constexpr std::uint16_t kMapMd5 = 1302;         // {"map_names":[…]} → map_info[]{name,md5}
inline constexpr std::uint16_t kParam = 1400;          // {"plugin":…, "param":…}
inline constexpr std::uint16_t kRobotModel = 1500;     // 응답 본문이 모델 JSON

// 제어 — 19205 Control
inline constexpr std::uint16_t kCtrlStop = 2000;
inline constexpr std::uint16_t kCtrlGyro = 2001;
inline constexpr std::uint16_t kCtrlReloc = 2002;
inline constexpr std::uint16_t kCtrlConfirmLoc = 2003;
inline constexpr std::uint16_t kCtrlMotion = 2010;     // {"vx","vy","w","duration"}

// 작업 — 19206 Task/Nav
inline constexpr std::uint16_t kTaskPause = 3001;
inline constexpr std::uint16_t kTaskResume = 3002;
inline constexpr std::uint16_t kTaskCancel = 3003;
inline constexpr std::uint16_t kTaskGoPoint = 3050;
inline constexpr std::uint16_t kTaskGoTarget = 3051;   // {"id","source_id",…}
inline constexpr std::uint16_t kTaskPatrol = 3052;
inline constexpr std::uint16_t kTaskTranslate = 3055;  // 필드명 미확인 — 저수준 dict 만 받는다
inline constexpr std::uint16_t kTaskTurn = 3056;       // 필드명 미확인 — 저수준 dict 만 받는다
inline constexpr std::uint16_t kTaskGoTargetList = 3066;  // {"move_task_list":[…]}

// 설정 — 19207 Config
inline constexpr std::uint16_t kConfigSetMode = 4000;
inline constexpr std::uint16_t kConfigSetParams = 4100;   // 설정만 (저장 안 함)
inline constexpr std::uint16_t kConfigSaveParams = 4101;  // 설정 + 저장
inline constexpr std::uint16_t kConfigReloadParams = 4102;
inline constexpr std::uint16_t kConfigClearFatal = 4300;
inline constexpr std::uint16_t kConfigSeizeControl = 4005;   // {"nick_name":…}
inline constexpr std::uint16_t kConfigReleaseControl = 4006;  // 무파라미터
inline constexpr std::uint16_t kConfigUploadMap = 4010;   // 요청 본문이 smap JSON 전체
inline constexpr std::uint16_t kConfigDownloadMap = 4011;  // 응답 본문이 맵 JSON 전체

// 기타 — 19210 Other
inline constexpr std::uint16_t kOtherSpeaker = 6000;
inline constexpr std::uint16_t kOtherSetDo = 6001;      // {"id":N,"status":bool}
inline constexpr std::uint16_t kOtherSoftEstop = 6004;  // {"status":bool}

}  // namespace api

/// 포트별 연결을 관리하며 편호 호출을 이름으로 제공한다.
/// 포트마다 별도 TCP 연결을 열고, 연결은 첫 호출 시 lazy 로 열린다.
class SeerApi
{
  public:
    explicit SeerApi(std::string ip, double timeoutSec = 5.0, bool allowGuarded = false,
                     int minIntervalMs = ports::kMinRequestIntervalMs,
                     StreamFactory factory = nullptr);
    ~SeerApi();

    SeerApi(const SeerApi &) = delete;
    SeerApi &operator=(const SeerApi &) = delete;

    /// 포트 전송 객체(없으면 생성). 지령·설정 포트인데 allowGuarded 가 false 면 GuardedPortError.
    Transport &transport(std::uint16_t port);
    void close();

    /// 공통 호출 + ret_code 검사.
    Json call(std::uint16_t port, std::uint16_t apiType, const Json &msg, bool checkRet = true);
    Json call(std::uint16_t port, std::uint16_t apiType, bool checkRet = true);

    // ---- 조회 (19204) ----
    Json getRobotInfo();
    Json getPose();
    Json getSpeed();
    Json getBattery();
    Json getIo();
    Json getLasers(int step = 0);   ///< lasers 배열. step>0 이면 빔 다운샘플.
    Json getAlarms();
    Json getAllStatus();
    Json getMapStatus();
    Json getParam(const std::string &plugin, const std::string &param);
    /// 해당 포트의 현재 동시연결 한도를 로봇에 묻는다. 한도 파라미터가 없는 포트면 -1.
    int getMaxConnections(std::uint16_t port);
    Json getRunInfo();
    Json getMode();
    Json getBlocked();
    Json getBrake();
    Json getPath();
    Json getArea();
    Json getEstop();
    Json getRelocStatus();
    /// 1021 의 `reloc_status` 값만 꺼낸다. 키가 없으면 -1.
    int getRelocStatusCode();
    Json getLoadmapStatus();
    Json getSlamStatus(bool returnResultmap = false);
    Json getMotorInfo();     ///< motor_info 배열
    Json getControlOwner();
    Json getAllStatus2();
    Json getAllStatus3();
    Json getInitStatus();
    Json getStations();      ///< stations 배열
    /// 지도 md5 → {넘긴 이름: md5}. 1302 는 `.smap` 을 요구하고 1300 은 확장자 없이 준다 —
    /// 그 비대칭을 흡수한다. all-or-nothing 이라 없는 지도가 섞이면 로봇이 요청 전체를 거부한다.
    std::map<std::string, std::string> getMapMd5(const std::vector<std::string> &mapNames);
    Json getRobotModel();

    // ---- Config (19207, 게이트) ----
    /// `.smap` 원문 바이트. 응답 본문이 맵 JSON 전체이므로 파싱하지 않고 그대로 돌려준다.
    /// 무결성 대조가 필요하면 호출자가 한다 — 로봇이 주는 md5 는 getMapStatus()·getMapMd5() 에 있다.
    std::vector<char> downloadMap(const std::string &mapName);
    /// 제어권 획득. 지령 계열은 이것 없이는 ret_code 40020 으로 거부된다.
    /// 기존 소유자의 제어권을 뺏고, 반납해도 원 소유자에게 자동 복귀하지 않는다.
    Json seizeControl(const std::string &nickName);
    Json releaseControl();
    Json setMode(const Json &body);
    /// 파라미터 설정. save=false 는 4100(휘발), true 는 4101(저장까지).
    /// 본문은 {플러그인: {키: 값}} — 예: {"MoveFactory": {"MaxAcc": 1.0}}.
    ///
    /// 반영 여부를 알아야 하면 getParam 으로 되읽는다 — 그 왕복을 하는 도구가 tools/param_probe 다.
    Json setParams(const Json &params, bool save = false);
    Json reloadParams();
    Json clearFatal();
    Json uploadMap(const Json &smap);

    // ---- Control (19205, 게이트) ----
    Json stop();
    /// 개루프 운동. durationMs 는 dead-man 타이머다 — 그 시간 안에 새 지령이 오지 않으면
    /// 로봇이 스스로 멈춘다. 0 은 무한이며, 보내는 쪽이 죽어도 로봇이 계속 간다.
    /// 기본값을 두지 않는 이유가 이것이다 — 호출자가 정지 시간을 반드시 고르게 한다.
    Json openLoopMove(double vx, double vy, double w, int durationMs);
    Json calibrateGyro();
    /// 재측위 지령(2002). **보냈다는 것은 성공이 아니다** — 로봇이 수리했을 뿐이다.
    /// 성공은 1021 의 `reloc_status` 가 1 이 될 때이며, 판정·확정까지 묶으려면
    /// control.hpp 의 relocateAndConfirm() 을 쓴다.
    Json relocate(double x, double y, double angle);
    /// 좌표 외 방식(`{"isAuto":true}`·`{"home":true}` 등). 성공 판정은 relocate() 와 같다.
    Json relocateWith(const Json &params);
    Json confirmLocation();

    // ---- Task / Nav (19206, 게이트) ----
    Json goTarget(const std::string &siteId, const std::string &sourceId = "SELF_POSITION",
                  const Json &options = Json::object());
    Json goTargetList(const Json &moveTaskList);
    Json goPoint(const Json &body);
    Json patrol(const Json &body);
    Json translate(const Json &body);
    Json turn(const Json &body);
    Json pauseTask();
    Json resumeTask();
    Json cancelTask();

    // ---- 기타 (19210, 게이트) ----
    Json softEstop(bool on);
    Json speaker(const Json &body);
    Json setDo(int doId, bool status);

  private:
    void raiseOnRetCode(std::uint16_t apiType, const Json &resp);
    void raiseIfErrorPayload(std::uint16_t apiType, const std::vector<char> &raw);

    std::string ip_;
    double timeoutSec_;
    bool allowGuarded_;
    int minIntervalMs_;
    StreamFactory factory_;
    std::map<std::uint16_t, std::unique_ptr<Transport>> transports_;
};

}  // namespace seer_tcp_ip

#endif  // SEER_TCP_IP_API_HPP_
