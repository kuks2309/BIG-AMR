"""Seer(SRC) Robokit NetProtocol 전송 계층 — 16B 헤더 + JSON, TCP 1문1답.

프로토콜 정본: References/Seer-Driver/seer_api_guide.md §3·§4
원본 대조 대상: References/Seer-Driver/github_sdk/Robokit_TCP_API_py/netprotocol/rbkNetProtoEnums.py
                (`packMsg` / `unpackHead` / `PACK_HEAD_FMT_STR`)

이 모듈은 ROS 에 의존하지 않는다 — 단독 스크립트·테스트에서 그대로 쓸 수 있어야 한다.
상위 의미(어떤 편호가 무엇을 뜻하는가)는 api.py 가 갖는다.

헤더 (big-endian, 16B):
    [0]     0x5A     sync
    [1]     0x01     version
    [2-3]   u16      seq (응답이 같은 값을 반향)
    [4-7]   u32      JSON 바이트 길이 (무파라미터 = 0)
    [8-9]   u16      API 편호
    [10-15] 6B       0x00 예약 (생략 불가)
"""
import itertools
import json
import socket
import struct
import time

from . import ports

#: 공식 SDK `PACK_HEAD_FMT_STR` 과 동일. '!' = network(big-endian), L=u32, H=u16.
HEAD_FMT = "!BBHLH6s"
HEAD_LEN = struct.calcsize(HEAD_FMT)  # 16
SYNC = 0x5A
VERSION = 0x01
RSV = b"\x00" * 6


class SeerProtocolError(RuntimeError):
    """헤더·편호·ret_code 등 프로토콜 수준 오류."""


class SeerGuardedPortError(RuntimeError):
    """지령·설정 포트를 broker 없이 직결하려 했다.

    ADR 2026-08-07-seer-api-tcp-hal §Decision 3 — 지령 포트는 단일 소유 broker 가 갖는다.
    단발 도구는 `allow_guarded=True` 를 명시해 그 사용을 기록으로 남긴다.
    (옛 이름 `SeerExclusivePortError` — "동시연결 1" 이 근거였으나 반증됐다. `ports.GUARDED_PORTS` 참조.)
    """


class SeerConnectionLimitError(SeerProtocolError):
    """로봇의 동시연결 한도에 걸려 거부됐다 (`ret_code` 61001).

    거부 응답은 편호 규칙(요청+10000)을 따르지 않고 **포트 번호를 편호로** 보낸다 —
    그래서 일반 편호 대조에 걸리면 "응답 편호 불일치"라는 엉뚱한 진단이 나온다.
    기존 연결은 끊기지 않는다(거부형). 한도는 API 1400 으로 조회·변경 가능.
    """


def pack(seq: int, api_type: int, msg=None) -> bytes:
    """요청 프레임(16B 헤더 + JSON) 을 만든다.

    공식 `packMsg` 와 **바이트 동일**해야 한다 — 빈 메시지는 body 를 붙이지 않고 length=0
    (원본이 `if(msg != {})` 로 그렇게 한다). test/test_transport.py 가 이 동등성을 고정한다.

    :param seq: 0~65535 순번. 응답이 같은 값을 반향한다.
    :param api_type: API 편호.
    :param msg: JSON 직렬화할 dict. None/빈 dict 면 body 없음.
    :returns: 전송할 바이트열.
    """
    body = b""
    if msg:
        body = json.dumps(msg).encode("ascii")
    return struct.pack(HEAD_FMT, SYNC, VERSION, seq, len(body), api_type, RSV) + body


def unpack_head(head: bytes):
    """응답 헤더 16B → (seq, json_len, api_type).

    :raises SeerProtocolError: 길이 부족 또는 sync 바이트 불일치.
    """
    if len(head) != HEAD_LEN:
        raise SeerProtocolError(f"헤더 길이 {len(head)}B (기대 {HEAD_LEN}B)")
    sync, _version, seq, json_len, api_type, _rsv = struct.unpack(HEAD_FMT, head)
    if sync != SYNC:
        raise SeerProtocolError(f"sync 불일치 0x{sync:02X} (기대 0x{SYNC:02X})")
    return seq, json_len, api_type


class SeerTransport:
    """한 포트에 대한 TCP 1문1답 연결.

    한 연결에서 이전 응답을 받기 전 다음 요청을 보내지 않는다(프로토콜 제약).
    스레드 안전하지 않다 — 포트당 소유자 하나가 원칙이다.
    """

    def __init__(
        self,
        ip: str,
        port: int,
        timeout: float = 5.0,
        min_interval: float = ports.MIN_REQUEST_INTERVAL_S,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        """:param min_interval: 요청 간 최소 간격(초). 0 이면 스로틀 없음.
        :param clock, sleep: 시험 주입점(실시간 대기 없이 스로틀 검증).
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._seq = itertools.cycle(range(1, 65536))
        self._sock = None
        self._last_request_at = None

    # ---- 연결 수명 ----
    def connect(self):
        if self._sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, self.port))
            self._sock = sock
        return self

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    # ---- 요청 ----
    def request(self, api_type: int, msg=None, expect_type=None) -> dict:
        """편호 요청 → 응답 JSON(dict).

        :param expect_type: 기대 응답 편호. None 이면 `api_type + 10000` 을 기대한다.
        :raises SeerProtocolError: 응답 편호·seq 불일치, sync 불일치.
        :raises ConnectionError: 수신 중 연결 종료.
        """
        raw, resp_type = self.request_raw(api_type, msg, expect_type=expect_type)
        text = raw.decode("utf-8", "replace") if raw else "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise SeerProtocolError(f"응답 {resp_type} JSON 파싱 실패: {exc}") from exc

    def request_raw(self, api_type: int, msg=None, expect_type=None):
        """편호 요청 → (응답 바이트열, 응답 편호).

        맵 다운로드(4011)처럼 응답 본문이 JSON 원문 그대로여서 바이트 무결성(md5)을
        검증해야 하는 경우를 위해 파싱 전 바이트를 노출한다.
        """
        self._throttle()
        self.connect()
        seq = next(self._seq)
        try:
            self._sock.sendall(pack(seq, api_type, msg))
            resp_seq, json_len, resp_type = unpack_head(self._recv_exact(HEAD_LEN))
            body = self._recv_exact(json_len) if json_len else b""
        except (OSError, ConnectionError):
            self.close()  # 끊긴 소켓을 남기지 않는다 — 다음 요청이 재연결한다
            raise
        finally:
            self._last_request_at = self._clock()

        want = api_type + ports.RESPONSE_TYPE_OFFSET if expect_type is None else expect_type
        if resp_type != want:
            self._raise_connection_limit_if_that(resp_type, body)
            raise SeerProtocolError(f"응답 편호 {resp_type} (기대 {want}, 요청 {api_type})")
        if resp_seq != seq:
            raise SeerProtocolError(f"응답 seq {resp_seq} (기대 {seq}) — 응답 어긋남")
        return body, resp_type

    # ---- 내부 ----
    def _raise_connection_limit_if_that(self, resp_type: int, body: bytes):
        """한도 거부 응답이면 전용 예외로 바꾼다.

        서명: 편호가 **포트 번호**로 오고 본문 `ret_code` 가 61001.
        일반 "편호 불일치" 로 흘려보내면 원인이 가려진다 — 실제로 첫 실측에서
        `응답 편호 19204 (기대 11004)` 라는 오해를 부르는 메시지가 나왔다.
        """
        if resp_type != self.port or not body:
            return
        try:
            obj = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            return
        if not isinstance(obj, dict) or obj.get("ret_code") != ports.CONNECTION_LIMIT_RET_CODE:
            return
        raise SeerConnectionLimitError(
            f"포트 {self.port} 동시연결 한도 초과 (ret_code={obj.get('ret_code')}): "
            f"{obj.get('err_msg')!r} — 기존 연결은 유지된다(거부형). "
            f"한도는 API 1400 `{ports.MAX_CONNECTION_PARAM.get(self.port)}` 로 조회한다."
        )

    def _throttle(self):
        """요청 간 최소 간격 유지. 과빈번 요청은 로봇이 연결을 정리한다(가이드 §1)."""
        if not self.min_interval or self._last_request_at is None:
            return
        wait = self.min_interval - (self._clock() - self._last_request_at)
        if wait > 0:
            self._sleep(wait)

    def _recv_exact(self, n: int) -> bytes:
        """정확히 n 바이트. 부분 수신을 끝까지 모은다.

        공식 데모는 `recv(1024)` 라 레이저처럼 큰 응답에서 잘린다 — 반드시 헤더의
        length 만큼 정확히 읽어야 한다(가이드 §4 주석).
        """
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError(f"수신 중 연결 종료 ({len(buf)}/{n}B)")
            buf += chunk
        return bytes(buf)
