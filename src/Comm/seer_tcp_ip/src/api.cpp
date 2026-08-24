#include "seer_tcp_ip/api.hpp"

#include <cstdio>

namespace seer_tcp_ip
{

SeerApi::SeerApi(std::string ip, double timeoutSec, bool allowGuarded, int minIntervalMs,
                 StreamFactory factory)
    : ip_(std::move(ip)), timeoutSec_(timeoutSec), allowGuarded_(allowGuarded),
      minIntervalMs_(minIntervalMs), factory_(std::move(factory))
{
}

SeerApi::~SeerApi()
{
    close();
}

Transport &SeerApi::transport(std::uint16_t port)
{
    if (ports::isGuarded(port) && !allowGuarded_)
    {
        throw GuardedPortError(
            "포트 " + std::to_string(port) +
            " 는 지령·설정 계열 — 두 주체가 동시에 지령하면 위험하므로 broker 단일 소유가 원칙이다. "
            "단발 도구라면 SeerApi(..., allowGuarded=true) 를 명시할 것. (연결 수는 부족하지 않다 — "
            "한도 " + std::to_string(ports::observedMaxConnectionsFor(port)) + ", 초과 시 거부형.)");
    }
    auto it = transports_.find(port);
    if (it == transports_.end())
    {
        auto tr = std::unique_ptr<Transport>(
            new Transport(ip_, port, timeoutSec_, minIntervalMs_, factory_));
        it = transports_.emplace(port, std::move(tr)).first;
    }
    return *it->second;
}

void SeerApi::close()
{
    for (auto &kv : transports_)
    {
        kv.second->close();
    }
    transports_.clear();
}

void SeerApi::raiseOnRetCode(std::uint16_t apiType, const Json &resp)
{
    // 객체가 아닌 응답에 value() 를 쓰면 nlohmann 이 type_error 를 던진다 — 그 전에 막는다.
    // `ret_code` 부재는 별도로 걸러내지 않는다: 기본값 0 이 곧 「정상」이라 검사가 하는 일이 없다.
    if (!resp.is_object())
    {
        return;
    }
    const int ret = resp.value("ret_code", 0);
    if (ret != 0)
    {
        throw ProtocolError("API " + std::to_string(apiType) + " ret_code=" + std::to_string(ret) +
                            " err_msg='" + resp.value("err_msg", std::string()) + "'");
    }
}

Json SeerApi::call(std::uint16_t port, std::uint16_t apiType, const Json &msg, bool checkRet)
{
    Json resp = transport(port).request(apiType, msg);
    if (checkRet)
    {
        raiseOnRetCode(apiType, resp);
    }
    return resp;
}

Json SeerApi::call(std::uint16_t port, std::uint16_t apiType, bool checkRet)
{
    Json resp = transport(port).request(apiType);
    if (checkRet)
    {
        raiseOnRetCode(apiType, resp);
    }
    return resp;
}

// ---- 조회 ----
Json SeerApi::getRobotInfo() { return call(ports::kState, api::kRobotInfo); }
Json SeerApi::getPose() { return call(ports::kState, api::kLoc); }
Json SeerApi::getSpeed() { return call(ports::kState, api::kSpeed); }
Json SeerApi::getBattery() { return call(ports::kState, api::kBattery); }
Json SeerApi::getIo() { return call(ports::kState, api::kIo); }
Json SeerApi::getAlarms() { return call(ports::kState, api::kAlarm); }
Json SeerApi::getAllStatus() { return call(ports::kState, api::kAll); }
Json SeerApi::getMapStatus() { return call(ports::kState, api::kMapStatus); }
Json SeerApi::getRunInfo() { return call(ports::kState, api::kRunInfo); }
Json SeerApi::getMode() { return call(ports::kState, api::kMode); }
Json SeerApi::getBlocked() { return call(ports::kState, api::kBlocked); }
Json SeerApi::getBrake() { return call(ports::kState, api::kBrake); }
Json SeerApi::getPath() { return call(ports::kState, api::kPath); }
Json SeerApi::getArea() { return call(ports::kState, api::kArea); }
Json SeerApi::getEstop() { return call(ports::kState, api::kEstop); }
Json SeerApi::getRelocStatus() { return call(ports::kState, api::kRelocStatus); }

int SeerApi::getRelocStatusCode()
{
    return getRelocStatus().value("reloc_status", -1);
}
Json SeerApi::getLoadmapStatus() { return call(ports::kState, api::kLoadmapStatus); }
Json SeerApi::getControlOwner() { return call(ports::kState, api::kControlOwner); }
Json SeerApi::getAllStatus2() { return call(ports::kState, api::kAll2); }
Json SeerApi::getAllStatus3() { return call(ports::kState, api::kAll3); }
Json SeerApi::getInitStatus() { return call(ports::kState, api::kInitStatus); }
Json SeerApi::getRobotModel() { return call(ports::kState, api::kRobotModel); }

Json SeerApi::getLasers(int step)
{
    if (step > 0)
    {
        return call(ports::kState, api::kLaser, Json{{"step", step}}).value("lasers", Json::array());
    }
    return call(ports::kState, api::kLaser).value("lasers", Json::array());
}

Json SeerApi::getSlamStatus(bool returnResultmap)
{
    return call(ports::kState, api::kSlamStatus, Json{{"return_resultmap", returnResultmap}});
}

Json SeerApi::getMotorInfo()
{
    return call(ports::kState, api::kMotorInfo).value("motor_info", Json::array());
}

Json SeerApi::getStations()
{
    return call(ports::kState, api::kStations).value("stations", Json::array());
}

Json SeerApi::getParam(const std::string &plugin, const std::string &param)
{
    return call(ports::kState, api::kParam, Json{{"plugin", plugin}, {"param", param}});
}

int SeerApi::getMaxConnections(std::uint16_t port)
{
    const auto it = ports::maxConnectionParam().find(port);
    if (it == ports::maxConnectionParam().end())
    {
        return -1;
    }
    const Json resp = getParam("NetProtocol", it->second);
    if (!resp.contains("NetProtocol") || !resp["NetProtocol"].contains(it->second))
    {
        return -1;
    }
    return resp["NetProtocol"][it->second].value("value", -1);
}

std::map<std::string, std::string> SeerApi::getMapMd5(const std::vector<std::string> &mapNames)
{
    std::vector<std::string> sent;
    sent.reserve(mapNames.size());
    for (const auto &n : mapNames)
    {
        const bool hasExt = n.size() >= 5 && n.compare(n.size() - 5, 5, ".smap") == 0;
        sent.push_back(hasExt ? n : n + ".smap");
    }
    const Json resp = call(ports::kState, api::kMapMd5, Json{{"map_names", sent}});
    std::map<std::string, std::string> bySent;
    for (const auto &m : resp.value("map_info", Json::array()))
    {
        bySent[m.value("name", std::string())] = m.value("md5", std::string());
    }
    std::vector<std::string> missing;
    for (std::size_t i = 0; i < mapNames.size(); ++i)
    {
        if (bySent.find(sent[i]) == bySent.end())
        {
            missing.push_back(mapNames[i]);
        }
    }
    if (!missing.empty())
    {
        std::string joined;
        for (const auto &m : missing)
        {
            joined += (joined.empty() ? "" : ", ") + m;
        }
        throw ProtocolError("1302 응답에 요청한 지도가 없다: [" + joined + "]");
    }
    std::map<std::string, std::string> out;
    for (std::size_t i = 0; i < mapNames.size(); ++i)
    {
        out[mapNames[i]] = bySent[sent[i]];
    }
    return out;
}

// ---- Config ----
void SeerApi::raiseIfErrorPayload(std::uint16_t apiType, const std::vector<char> &raw)
{
    // 맵 JSON 은 수십만 바이트라 짧은 응답만 에러 후보로 본다.
    if (raw.size() > 4096)
    {
        return;
    }
    const Json obj = Json::parse(std::string(raw.begin(), raw.end()), nullptr, false);
    if (obj.is_discarded() || !obj.is_object())
    {
        return;
    }
    if (obj.contains("ret_code") && obj.value("ret_code", 0) != 0)
    {
        throw ProtocolError("API " + std::to_string(apiType) +
                            " ret_code=" + std::to_string(obj.value("ret_code", 0)) + " err_msg='" +
                            obj.value("err_msg", std::string()) + "'");
    }
}

std::vector<char> SeerApi::downloadMap(const std::string &mapName)
{
    auto [raw, respType] = transport(ports::kConfig)
                               .requestRaw(api::kConfigDownloadMap, Json{{"map_name", mapName}});
    (void)respType;
    raiseIfErrorPayload(api::kConfigDownloadMap, raw);
    return raw;
}

Json SeerApi::seizeControl(const std::string &nickName)
{
    return call(ports::kConfig, api::kConfigSeizeControl, Json{{"nick_name", nickName}});
}

Json SeerApi::releaseControl() { return call(ports::kConfig, api::kConfigReleaseControl); }
Json SeerApi::setMode(const Json &body) { return call(ports::kConfig, api::kConfigSetMode, body); }

Json SeerApi::setParams(const Json &params, bool save)
{
    return call(ports::kConfig, save ? api::kConfigSaveParams : api::kConfigSetParams, params);
}

Json SeerApi::reloadParams() { return call(ports::kConfig, api::kConfigReloadParams); }
Json SeerApi::clearFatal() { return call(ports::kConfig, api::kConfigClearFatal); }
Json SeerApi::uploadMap(const Json &smap) { return call(ports::kConfig, api::kConfigUploadMap, smap); }

// ---- Control ----
Json SeerApi::stop() { return call(ports::kCtrl, api::kCtrlStop); }

Json SeerApi::openLoopMove(double vx, double vy, double w, int durationMs)
{
    return call(ports::kCtrl, api::kCtrlMotion,
                Json{{"vx", vx}, {"vy", vy}, {"w", w}, {"duration", durationMs}});
}

Json SeerApi::calibrateGyro() { return call(ports::kCtrl, api::kCtrlGyro); }

Json SeerApi::relocate(double x, double y, double angle)
{
    return call(ports::kCtrl, api::kCtrlReloc, Json{{"x", x}, {"y", y}, {"angle", angle}});
}

Json SeerApi::relocateWith(const Json &params) { return call(ports::kCtrl, api::kCtrlReloc, params); }
Json SeerApi::confirmLocation() { return call(ports::kCtrl, api::kCtrlConfirmLoc); }

// ---- Task / Nav ----
Json SeerApi::goTarget(const std::string &siteId, const std::string &sourceId, const Json &options)
{
    Json body{{"id", siteId}, {"source_id", sourceId}};
    for (auto it = options.begin(); it != options.end(); ++it)
    {
        body[it.key()] = it.value();
    }
    return call(ports::kTask, api::kTaskGoTarget, body);
}

Json SeerApi::goTargetList(const Json &moveTaskList)
{
    return call(ports::kTask, api::kTaskGoTargetList, Json{{"move_task_list", moveTaskList}});
}

Json SeerApi::goPoint(const Json &body) { return call(ports::kTask, api::kTaskGoPoint, body); }
Json SeerApi::patrol(const Json &body) { return call(ports::kTask, api::kTaskPatrol, body); }
Json SeerApi::translate(const Json &body) { return call(ports::kTask, api::kTaskTranslate, body); }
Json SeerApi::turn(const Json &body) { return call(ports::kTask, api::kTaskTurn, body); }
Json SeerApi::pauseTask() { return call(ports::kTask, api::kTaskPause); }
Json SeerApi::resumeTask() { return call(ports::kTask, api::kTaskResume); }
Json SeerApi::cancelTask() { return call(ports::kTask, api::kTaskCancel); }

// ---- 기타 ----
Json SeerApi::softEstop(bool on)
{
    return call(ports::kOther, api::kOtherSoftEstop, Json{{"status", on}});
}

Json SeerApi::speaker(const Json &body) { return call(ports::kOther, api::kOtherSpeaker, body); }

Json SeerApi::setDo(int doId, bool status)
{
    return call(ports::kOther, api::kOtherSetDo, Json{{"id", doId}, {"status", status}});
}

}  // namespace seer_tcp_ip
