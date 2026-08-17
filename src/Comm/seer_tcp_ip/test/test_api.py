"""seer_tcp_ip.api 회귀 시험 — 편호·포트 배선과 지령 포트 게이트.

정책 시험이 핵심이다: ADR 2026-08-07 §Decision 3 의 "지령 포트는 broker 단일 소유"를
문서가 아니라 코드가 강제하는지 확인한다.
"""
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seer_tcp_ip import api, ports  # noqa: E402
from seer_tcp_ip.api import SeerApi  # noqa: E402
from seer_tcp_ip.transport import SeerGuardedPortError, SeerProtocolError  # noqa: E402


class RecordingTransport:
    """SeerTransport 대역 — 호출을 기록하고 준비된 응답을 돌려준다."""

    def __init__(self, ip, port, timeout=5.0, min_interval=0.0):
        self.ip = ip
        self.port = port
        self.calls = []
        self.responses = {}
        self.raw_responses = {}
        self.closed = False

    def request(self, api_type, msg=None, expect_type=None):
        self.calls.append((api_type, msg))
        return self.responses.get(api_type, {"ret_code": 0})

    def request_raw(self, api_type, msg=None, expect_type=None):
        self.calls.append((api_type, msg))
        return self.raw_responses.get(api_type, b"{}"), api_type + 10000

    def close(self):
        self.closed = True


@pytest.fixture
def client(monkeypatch):
    made = {}

    def factory(ip, port, timeout=5.0, min_interval=0.0):
        tr = RecordingTransport(ip, port, timeout, min_interval)
        made[port] = tr
        return tr

    monkeypatch.setattr(api, "SeerTransport", factory)
    c = SeerApi("192.168.44.82")
    c._made = made
    return c


# ---------- 지령 포트 게이트 ----------

def test_guarded_ports_blocked_by_default(client):
    """19205/06/07/10 은 기본값에서 막힌다 — 문서를 안 읽어도 사고가 안 나야 한다."""
    for call in (client.stop, lambda: client.open_loop_move(0.1),
                 lambda: client.go_target("LM1"), lambda: client.set_do(15, True),
                 lambda: client.download_map("m")):
        with pytest.raises(SeerGuardedPortError):
            call()


def test_status_port_is_allowed_by_default(client):
    client.get_pose()
    assert ports.API_PORT_STATE in client._made


def test_guarded_allowed_when_opted_in(monkeypatch):
    made = {}
    monkeypatch.setattr(api, "SeerTransport",
                        lambda ip, port, **k: made.setdefault(port, RecordingTransport(ip, port)))
    c = SeerApi("192.168.44.82", allow_guarded=True)
    c.open_loop_move(0.1, 0.0, 0.0)
    assert made[ports.API_PORT_CTRL].calls == [(api.API_CTRL_MOTION,
                                                {"vx": 0.1, "vy": 0.0, "w": 0.0})]


def test_api_numbers_are_pinned_to_literals():
    """편호를 **리터럴**로 고정한다.

    상수를 기대값에 그대로 쓰면(`assert calls == [(api.API_X, ...)]`) 상수가 틀려도
    기대값이 같이 틀려서 시험이 통과한다 — 실제로 A5(4011→4010) 가 그렇게 빠져나갔다.
    출처: References/Seer-Driver/seer_api_guide.md §5 레시피표 / 맵 관련은
    T-Robot_seer_gui `019-download-maps-from-robots.md`.
    """
    assert (api.API_ROBOT_INFO, api.API_LOC, api.API_SPEED, api.API_BATTERY) == (1000, 1004, 1005, 1007)
    assert (api.API_LASER, api.API_IO, api.API_TASK_STATUS) == (1009, 1013, 1020)
    assert (api.API_ALARM, api.API_ALL, api.API_MAP_STATUS) == (1050, 1100, 1300)
    assert (api.API_CTRL_STOP, api.API_CTRL_RELOC, api.API_CTRL_MOTION) == (2000, 2002, 2010)
    assert api.API_TASK_GOTARGET == 3051
    assert api.API_CONFIG_DOWNLOAD_MAP == 4011
    assert api.API_OTHER_SET_DO == 6001


def test_ports_are_pinned_to_literals():
    assert (ports.API_PORT_STATE, ports.API_PORT_CTRL, ports.API_PORT_TASK) == (19204, 19205, 19206)
    assert (ports.API_PORT_CONFIG, ports.API_PORT_OTHER, ports.API_PORT_PUSH) == (19207, 19210, 19301)
    assert ports.RESPONSE_TYPE_OFFSET == 10000


def test_observed_max_connections_match_measurement():
    """**[실측 2026-08-07]** Foil_A082(rbk 3.4.5.22) 값과 일치하는가.

    출처 ① 실기 API 1400 6건 ② 원본 하드 `robot.param` `NetProtocol` 테이블(동일 값).
    ⚠ 이전 판은 문서 v1.2.1 을 근거로 지령 포트를 **1** 로 적었다 — 틀렸다. 실제는 5 다.
    """
    assert ports.OBSERVED_MAX_CONNECTIONS[19204] == 10
    assert ports.OBSERVED_MAX_CONNECTIONS[19301] == 10
    for p in (19205, 19206, 19207, 19210):
        assert ports.OBSERVED_MAX_CONNECTIONS[p] == 5
    assert ports.observed_max_connections(19204) == 10
    assert ports.observed_max_connections(19208) is None


def test_guarded_set_is_explicit_not_derived_from_limit():
    """게이트 집합은 한도에서 파생하면 안 된다 — 한도가 5 라 파생하면 집합이 비어 게이트가 사라진다."""
    assert ports.GUARDED_PORTS == frozenset({19205, 19206, 19207, 19210})
    for p in ports.GUARDED_PORTS:
        assert ports.is_guarded(p)
        assert ports.OBSERVED_MAX_CONNECTIONS[p] > 1, "한도가 1 이 아닌데도 막혀 있어야 한다"
    for p in (19204, 19301):
        assert not ports.is_guarded(p)


def test_max_connection_param_names_are_pinned():
    """API 1400 으로 물어볼 파라미터 이름 — libNetProtocol.so 문자열과 실기 응답 키에서 확정."""
    assert ports.MAX_CONNECTION_PARAM[19204] == "RobotStatusAPITCPServerMaxConnections"
    assert ports.MAX_CONNECTION_PARAM[19205] == "RobotControlAPITCPServerMaxConnections"
    assert ports.MAX_CONNECTION_PARAM[19206] == "RobotTaskAPITCPServerMaxConnections"
    assert ports.MAX_CONNECTION_PARAM[19207] == "RobotConfigAPITCPServerMaxConnections"
    assert ports.MAX_CONNECTION_PARAM[19210] == "RobotOtherAPITCPServerMaxConnections"
    assert ports.MAX_CONNECTION_PARAM[19301] == "RobotPushTCPServerMaxConnections"
    assert ports.CONNECTION_LIMIT_RET_CODE == 61001


def test_get_max_connections_asks_the_robot(client):
    """한도 판정은 상수가 아니라 로봇에 물어서 한다(런타임 파라미터이므로)."""
    client.get_pose()
    tr = client._made[ports.API_PORT_STATE]
    tr.responses[1400] = {"NetProtocol": {
        "RobotControlAPITCPServerMaxConnections": {"value": 7, "defaultValue": 5}}, "ret_code": 0}
    assert client.get_max_connections(19205) == 7, "상수 5 가 아니라 응답값 7 을 써야 한다"
    assert tr.calls[-1] == (1400, {"plugin": "NetProtocol",
                                   "param": "RobotControlAPITCPServerMaxConnections"})
    assert client.get_max_connections(19208) is None  # 한도 파라미터 없는 포트


def test_get_max_connections_uses_status_port_not_guarded(client):
    """19205 의 한도를 물을 때도 조회는 19204 로 나가야 한다 — 게이트에 걸리면 안 된다."""
    client.get_max_connections(19205)
    assert ports.API_PORT_CTRL not in client._made
    assert ports.API_PORT_STATE in client._made


# ---------- 편호·포트 배선 ----------

@pytest.mark.parametrize("method,api_type", [
    ("get_robot_info", 1000),
    ("get_pose", 1004),
    ("get_speed", 1005),
    ("get_battery", 1007),
    ("get_io", 1013),
    ("get_alarms", 1050),
    ("get_all_status", 1100),
    ("get_map_status", 1300),
])
def test_status_api_numbers(client, method, api_type):
    getattr(client, method)()
    tr = client._made[ports.API_PORT_STATE]
    assert tr.calls == [(api_type, None)]


def test_get_lasers_returns_array_and_supports_step(client):
    tr_port = ports.API_PORT_STATE
    client.get_lasers()
    tr = client._made[tr_port]
    tr.responses[1009] = {"lasers": [{"device_info": {"device_name": "front"}}], "ret_code": 0}
    assert len(client.get_lasers()) == 1
    client.get_lasers(step=5)
    assert tr.calls[-1] == (1009, {"step": 5})


def test_get_lasers_missing_key_is_empty_list(client):
    client._made  # noqa: B018 — fixture 초기화
    assert client.get_lasers() == []


def test_ret_code_error_raises(client):
    client.get_pose()
    tr = client._made[ports.API_PORT_STATE]
    tr.responses[1004] = {"ret_code": 8, "err_msg": "not allowed"}
    with pytest.raises(SeerProtocolError, match="ret_code=8"):
        client.get_pose()


def test_ret_code_absent_is_ok(client):
    client.get_pose()
    tr = client._made[ports.API_PORT_STATE]
    tr.responses[1004] = {"x": 1.0, "y": 2.0, "angle": 0.5}
    assert client.get_pose()["x"] == 1.0


def test_iter_alarms_flattens(client):
    client.get_alarms()
    tr = client._made[ports.API_PORT_STATE]
    tr.responses[1050] = {
        "fatals": [{"50000": 1497698400}],
        "errors": [{"52111": 1497698402}, {"52118": 1497698404}],
        "warnings": [],
        "ret_code": 0,
    }
    got = sorted(client.iter_alarms(), key=lambda t: t[1])
    assert got == [("fatals", 50000, 1497698400),
                   ("errors", 52111, 1497698402),
                   ("errors", 52118, 1497698404)]


def test_iter_alarms_handles_null_levels(client):
    client.get_alarms()
    tr = client._made[ports.API_PORT_STATE]
    tr.responses[1050] = {"fatals": None, "ret_code": 0}
    assert list(client.iter_alarms()) == []


# ---------- 맵 다운로드 ----------

def _map_client(monkeypatch, raw):
    made = {}

    def factory(ip, port, **k):
        tr = RecordingTransport(ip, port)
        tr.raw_responses[api.API_CONFIG_DOWNLOAD_MAP] = raw
        made[port] = tr
        return tr

    monkeypatch.setattr(api, "SeerTransport", factory)
    c = SeerApi("192.168.44.82", allow_guarded=True)
    c._made = made
    return c


def test_download_map_returns_raw_bytes(monkeypatch):
    body = json.dumps({"header": {"mapName": "260709_test"},
                       "normalPosList": [{"x": 1.0}] * 500}).encode()
    c = _map_client(monkeypatch, body)
    got = c.download_map("260709_test")
    assert got == body, "맵은 파싱하지 말고 원문 바이트를 그대로 넘겨야 md5 대조가 성립한다"
    assert c._made[ports.API_PORT_CONFIG].calls == [
        (api.API_CONFIG_DOWNLOAD_MAP, {"map_name": "260709_test"})]


def test_download_map_md5_verification(monkeypatch):
    body = b'{"header": {"mapName": "m"}}'
    c = _map_client(monkeypatch, body)
    assert c.download_map("m", verify_md5=hashlib.md5(body).hexdigest()) == body
    with pytest.raises(SeerProtocolError, match="md5"):
        c.download_map("m", verify_md5="0" * 32)


def test_download_map_error_object_raises(monkeypatch):
    c = _map_client(monkeypatch, b'{"ret_code": 4, "err_msg": "no such map"}')
    with pytest.raises(SeerProtocolError, match="ret_code=4"):
        c.download_map("nope")


def test_download_map_large_body_not_misread_as_error(monkeypatch):
    """큰 맵 안에 ret_code 키가 있어도 에러로 오판하지 않는다(짧은 응답만 판정)."""
    body = json.dumps({"ret_code": 9, "pad": "x" * 5000}).encode()
    c = _map_client(monkeypatch, body)
    assert c.download_map("big") == body


# ---------- 연결 관리 ----------

def test_transport_is_reused_per_port(client):
    client.get_pose()
    client.get_speed()
    assert len(client._made) == 1


def test_close_releases_all(client):
    client.get_pose()
    tr = client._made[ports.API_PORT_STATE]
    client.close()
    assert tr.closed and client._transports == {}
