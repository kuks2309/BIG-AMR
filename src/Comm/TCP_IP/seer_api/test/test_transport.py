"""seer_api.transport 회귀 시험.

핵심 고정 대상:
  1. 공식 SDK `packMsg` 와 **바이트 동일** — 우리가 만든 프레임이 로봇이 받는 프레임과 같은가.
  2. 부분 수신을 끝까지 모으는가(공식 데모의 recv(1024) 절단 결함을 재도입하지 않는가).
  3. 응답 편호·seq 를 실제로 대조하는가(이관 전 두 구현은 둘 다 대조하지 않았다).
  4. 요청 간 최소 간격을 지키는가.

시험은 실기 없이 돈다 — 소켓을 가짜로 갈아끼운다.
"""
import importlib.util
import json
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seer_api import ports, transport  # noqa: E402
from seer_api.transport import (  # noqa: E402
    SeerProtocolError,
    SeerTransport,
    pack,
    unpack_head,
)

# ---- 공식 SDK 원본 로드 (원문 대조용) ----
_SDK_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../../../../References/Seer-Driver/github_sdk/Robokit_TCP_API_py/netprotocol/rbkNetProtoEnums.py",
)


def _load_official():
    path = os.path.abspath(_SDK_PATH)
    if not os.path.exists(path):
        pytest.skip(f"공식 SDK 원본 없음: {path}")
    spec = importlib.util.spec_from_file_location("rbkNetProtoEnums_ref", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeSocket:
    """프로그램된 바이트를 조금씩 흘려주는 소켓 대역.

    recv 를 1~3B 씩 쪼개 돌려주어 부분 수신 경로를 반드시 지나게 한다.
    """

    def __init__(self, response=b"", chunk=3):
        self.response = response
        self.chunk = chunk
        self.sent = b""
        self.closed = False
        self.connected_to = None
        self.timeout = None
        self._pos = 0

    def settimeout(self, t):
        self.timeout = t

    def connect(self, addr):
        self.connected_to = addr

    def sendall(self, data):
        self.sent += data

    def recv(self, n):
        take = min(n, self.chunk, len(self.response) - self._pos)
        if take <= 0:
            return b""
        out = self.response[self._pos:self._pos + take]
        self._pos += take
        return out

    def close(self):
        self.closed = True


def make_response(seq, api_type, payload: dict, sync=transport.SYNC):
    body = json.dumps(payload).encode("ascii")
    head = struct.pack(transport.HEAD_FMT, sync, transport.VERSION, seq,
                       len(body), api_type, transport.RSV)
    return head + body


def bind(monkeypatch, sock):
    monkeypatch.setattr(transport.socket, "socket", lambda *a, **k: sock)


# ---------- 1. 공식 SDK 바이트 동일성 ----------

def test_pack_matches_official_sdk_with_body():
    """본문 있는 요청이 공식 packMsg 와 바이트 동일."""
    official = _load_official()
    msg = {"x": 10.0, "y": 3.0, "angle": 0}
    assert pack(7, 2002, msg) == official.packMsg(7, 2002, msg)


def test_pack_matches_official_sdk_empty_body():
    """빈 요청은 body 없이 length=0 — 공식 원본의 `if(msg != {})` 분기와 같아야 한다."""
    official = _load_official()
    for api in (1000, 1004, 1009, 1050):
        assert pack(1, api, {}) == official.packMsg(1, api, {})
        assert pack(1, api, None) == official.packMsg(1, api, {})


def test_head_format_string_matches_official():
    official = _load_official()
    assert transport.HEAD_FMT == official.PACK_HEAD_FMT_STR
    assert transport.RSV == official.PACK_RSV_DATA
    assert transport.HEAD_LEN == 16


def test_pack_header_fields_are_literal():
    """헤더 각 바이트가 사양대로인지 직접 확인(포맷 문자열에 의존하지 않는 독립 검증)."""
    frame = pack(0x1234, 1009, None)
    assert len(frame) == 16
    assert frame[0] == 0x5A
    assert frame[1] == 0x01
    assert frame[2:4] == b"\x12\x34"  # seq, big-endian
    assert frame[4:8] == b"\x00\x00\x00\x00"  # length 0
    assert frame[8:10] == struct.pack(">H", 1009)
    assert frame[10:16] == b"\x00" * 6


# ---------- 2. 수신 ----------

def test_recv_exact_reassembles_chunked_response(monkeypatch):
    payload = {"lasers": [{"device_info": {"device_name": "front"}}], "ret_code": 0}
    sock = FakeSocket(make_response(1, 11009, payload), chunk=1)  # 1바이트씩
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    assert tr.request(1009) == payload


def test_large_response_is_not_truncated(monkeypatch):
    """공식 데모의 recv(1024) 절단 결함이 재도입되지 않았는지."""
    payload = {"beams": list(range(2000)), "ret_code": 0}
    sock = FakeSocket(make_response(1, 11009, payload), chunk=997)
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    got = tr.request(1009)
    assert len(got["beams"]) == 2000


def test_connection_closed_midway_raises(monkeypatch):
    full = make_response(1, 11009, {"ret_code": 0})
    sock = FakeSocket(full[:10])  # 헤더도 못 채우고 끊김
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(ConnectionError):
        tr.request(1009)
    assert sock.closed, "끊긴 소켓을 남기면 다음 요청이 재연결하지 못한다"


# ---------- 3. 대조 ----------

def test_unexpected_response_type_raises(monkeypatch):
    sock = FakeSocket(make_response(1, 60000, {}))  # 엉뚱한 포트로 보내면 60000
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(SeerProtocolError, match="60000"):
        tr.request(1009)


def test_seq_mismatch_raises(monkeypatch):
    sock = FakeSocket(make_response(999, 11009, {"ret_code": 0}))  # seq 반향 안 함
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(SeerProtocolError, match="seq"):
        tr.request(1009)


def test_bad_sync_byte_raises(monkeypatch):
    sock = FakeSocket(make_response(1, 11009, {}, sync=0x00))
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(SeerProtocolError, match="sync"):
        tr.request(1009)


def test_connection_limit_rejection_is_its_own_error(monkeypatch):
    """한도 거부는 "편호 불일치"가 아니라 전용 예외로 나와야 한다.

    **[실측 2026-08-07]** 19204 에 9번째 연결 시 로봇이 보낸 실제 프레임을 그대로 재현한다 —
    편호가 요청+10000 이 아니라 **포트 번호(19204)** 이고 `ret_code` 가 61001 이다.
    이 서명을 못 알아보면 `응답 편호 19204 (기대 11004)` 라는 오해를 부르는 진단이 나온다.
    """
    body = (b'{"create_on":"2026-08-07T18:36:40.679+0900",'
            b'"err_msg":"reach the maximum of status api connection limitation",'
            b'"ip":"192.168.44.2","port":52248,"ret_code":61001}')
    head = struct.pack(transport.HEAD_FMT, transport.SYNC, transport.VERSION, 1,
                       len(body), 19204, transport.RSV)
    sock = FakeSocket(head + body)
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(transport.SeerConnectionLimitError, match="61001"):
        tr.request(1004)


def test_connection_limit_error_is_a_protocol_error():
    """기존 `except SeerProtocolError` 호출자를 깨지 않는다."""
    assert issubclass(transport.SeerConnectionLimitError, SeerProtocolError)


def test_other_type_mismatch_still_generic(monkeypatch):
    """포트 번호가 아닌 편호 불일치는 종전대로 일반 예외 — 한도 예외로 뭉뚱그리지 않는다."""
    sock = FakeSocket(make_response(1, 60000, {"ret_code": 61001}))
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    with pytest.raises(SeerProtocolError) as exc:
        tr.request(1004)
    assert not isinstance(exc.value, transport.SeerConnectionLimitError)


def test_unpack_head_rejects_short_buffer():
    with pytest.raises(SeerProtocolError, match="헤더 길이"):
        unpack_head(b"\x5a\x01\x00")


def test_seq_increments_between_requests(monkeypatch):
    """seq 고정(이관 전 두 구현의 결함)이 아니라 순환하는지."""
    seqs = []

    class SeqSocket(FakeSocket):
        def sendall(self, data):
            seqs.append(struct.unpack(">H", data[2:4])[0])
            self._pos = 0
            self.response = make_response(seqs[-1], 11004, {"ret_code": 0})

    sock = SeqSocket(b"")
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    for _ in range(3):
        tr.request(1004)
    assert seqs == [1, 2, 3]


def test_expect_type_override(monkeypatch):
    """4011 처럼 응답 편호를 명시해야 하는 경우."""
    sock = FakeSocket(make_response(1, 14011, {"ret_code": 0}))
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0)
    assert tr.request(4011, expect_type=14011) == {"ret_code": 0}


# ---------- 4. 스로틀 ----------

def test_min_interval_is_enforced(monkeypatch):
    now = [0.0]
    slept = []

    class SeqSocket(FakeSocket):
        def sendall(self, data):
            self._pos = 0
            self.response = make_response(struct.unpack(">H", data[2:4])[0], 11004, {})

    sock = SeqSocket(b"")
    bind(monkeypatch, sock)
    tr = SeerTransport(
        "1.2.3.4", ports.API_PORT_STATE, min_interval=0.1,
        clock=lambda: now[0], sleep=lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)),
    )
    tr.request(1004)          # 첫 요청 — 대기 없음
    assert slept == []
    tr.request(1004)          # 즉시 재요청 — 0.1s 대기해야 한다
    assert slept and abs(slept[0] - 0.1) < 1e-9
    now[0] += 5.0
    tr.request(1004)          # 충분히 지난 뒤 — 추가 대기 없음
    assert len(slept) == 1


def test_zero_min_interval_never_sleeps(monkeypatch):
    slept = []

    class SeqSocket(FakeSocket):
        def sendall(self, data):
            self._pos = 0
            self.response = make_response(struct.unpack(">H", data[2:4])[0], 11004, {})

    sock = SeqSocket(b"")
    bind(monkeypatch, sock)
    tr = SeerTransport("1.2.3.4", ports.API_PORT_STATE, min_interval=0,
                       sleep=lambda s: slept.append(s))
    tr.request(1004)
    tr.request(1004)
    assert slept == []


# ---------- 5. 연결 수명 ----------

def test_context_manager_connects_and_closes(monkeypatch):
    sock = FakeSocket(b"")
    bind(monkeypatch, sock)
    with SeerTransport("9.9.9.9", 19204) as tr:
        assert tr.is_connected
        assert sock.connected_to == ("9.9.9.9", 19204)
    assert sock.closed and not tr.is_connected


def test_connect_is_idempotent(monkeypatch):
    made = []

    def factory(*a, **k):
        s = FakeSocket(b"")
        made.append(s)
        return s

    monkeypatch.setattr(transport.socket, "socket", factory)
    tr = SeerTransport("1.2.3.4", 19204)
    tr.connect()
    tr.connect()
    assert len(made) == 1
