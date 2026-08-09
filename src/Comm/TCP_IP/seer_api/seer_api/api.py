"""Seer(SRC) Robokit TCP API 바인딩 — 편호를 이름으로 감싼다.

편호·포트·요청 JSON 의 출처는 References/Seer-Driver/seer_api_guide.md §5 레시피표(등급 ✓),
맵 관련(1300/4011)은 사용자 저장소 `T-Robot_seer_gui`
(`references/seer/robokit-api/robot-configuration-api/019-download-maps-from-robots.md`) 가 정본이다
— 동봉 PDF v1.2.1 에는 4011 이 없다(있다고 착각하면 안 된다).

포트 정책(ADR docs/adr/2026-08-07-seer-api-tcp-hal.md §Decision 3):
  - 19204(Status)·19301(Push) 는 조회 → 라이브러리 직결 허용.
  - 19205/06/07/19210 은 **지령·설정** → 기본 차단. 단발 도구만 `allow_guarded=True` 를 명시한다.

⚠ 차단 근거 정정 2026-08-07 — 최초에는 "동시연결 1 이라 선점된다"였으나 실측으로 반증됐다
   (한도 5, 초과 시 거부형, 기존 연결 유지). 지금 근거는 **지령 중재**다 — `ports.GUARDED_PORTS` 참조.
"""
import hashlib

from . import ports
from .transport import SeerGuardedPortError, SeerProtocolError, SeerTransport

# ---- API 편호 (공식 SDK 이름 병기) ----
API_ROBOT_INFO = 1000  # robot_status_info_req
API_LOC = 1004  # robot_status_loc_req — x, y, angle
API_SPEED = 1005  # robot_status_speed_req — vx, vy, w
API_BATTERY = 1007  # 배터리
API_LASER = 1009  # robot_status_laser_req — lasers[].install_info / beams
API_IO = 1013  # DI/DO
API_TASK_STATUS = 1020
API_ALARM = 1050  # fatals / errors / warnings
API_ALL = 1100  # 배치 조회
API_MAP_STATUS = 1300  # current_map, current_map_md5, maps[]

API_CTRL_STOP = 2000
API_CTRL_RELOC = 2002
API_CTRL_MOTION = 2010  # 개루프 운동 (manual 모드 전용)

API_TASK_GOTARGET = 3051

API_PARAM = 1400  # robot_status_param_req — {"plugin":…, "param":…}
API_CONFIG_DOWNLOAD_MAP = 4011  # robot_config_downloadmap_req (v1.4 계열)

API_OTHER_SET_DO = 6001


class SeerApi:
    """포트별 연결을 관리하며 편호 호출을 이름으로 제공한다.

    한 인스턴스가 여러 포트를 다루되 포트마다 별도 TCP 연결을 연다(카테고리별 독립 포트).
    연결은 첫 호출 시 lazy 로 열린다 — 생성만으로 소켓을 잡지 않는다.
    """

    def __init__(self, ip: str, timeout: float = 5.0, allow_guarded: bool = False,
                 min_interval: float = ports.MIN_REQUEST_INTERVAL_S):
        """:param allow_guarded: 지령·설정 포트 사용을 명시적으로 허용.
                                 기본 False — broker 없이 로봇에 지령하는 사고를 막는다.
        """
        self.ip = ip
        self.timeout = timeout
        self.allow_guarded = allow_guarded
        self.min_interval = min_interval
        self._transports = {}

    # ---- 연결 관리 ----
    def transport(self, port: int) -> SeerTransport:
        """포트 전송 객체를 얻는다(없으면 생성).

        :raises SeerGuardedPortError: 지령·설정 포트인데 allow_guarded 가 False.
        """
        if ports.is_guarded(port) and not self.allow_guarded:
            raise SeerGuardedPortError(
                f"포트 {port} 는 지령·설정 계열 — 두 주체가 동시에 지령하면 위험하므로 "
                f"broker 단일 소유가 원칙이다. 단발 도구라면 "
                f"SeerApi(..., allow_guarded=True) 를 명시할 것. "
                f"(연결 수는 부족하지 않다 — 한도 "
                f"{ports.observed_max_connections(port)}, 초과 시 거부형.)"
            )
        tr = self._transports.get(port)
        if tr is None:
            tr = SeerTransport(self.ip, port, timeout=self.timeout,
                               min_interval=self.min_interval)
            self._transports[port] = tr
        return tr

    def close(self):
        for tr in self._transports.values():
            tr.close()
        self._transports.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- 공통 호출 ----
    def call(self, port: int, api_type: int, msg=None, check_ret: bool = True) -> dict:
        """편호 호출 후 응답 dict 반환.

        :param check_ret: True 면 ret_code 가 0/부재가 아닐 때 예외.
        """
        resp = self.transport(port).request(api_type, msg)
        if check_ret:
            self._raise_on_ret_code(api_type, resp)
        return resp

    @staticmethod
    def _raise_on_ret_code(api_type: int, resp: dict):
        ret = resp.get("ret_code")
        if ret not in (0, None):
            raise SeerProtocolError(
                f"API {api_type} ret_code={ret} err_msg={resp.get('err_msg')!r}"
            )

    # ---- Status (19204, 동시 10 — 직결 허용) ----
    def get_robot_info(self) -> dict:
        return self.call(ports.API_PORT_STATE, API_ROBOT_INFO)

    def get_pose(self) -> dict:
        """현재 위치. 응답 핵심: x, y, angle(rad)."""
        return self.call(ports.API_PORT_STATE, API_LOC)

    def get_speed(self) -> dict:
        """현재 속도. 응답 핵심: vx, vy, w."""
        return self.call(ports.API_PORT_STATE, API_SPEED)

    def get_battery(self) -> dict:
        return self.call(ports.API_PORT_STATE, API_BATTERY)

    def get_io(self) -> dict:
        return self.call(ports.API_PORT_STATE, API_IO)

    def get_lasers(self, step=None) -> list:
        """레이저 목록. 각 원소에 device_info / install_info(x, y, yaw[deg]) 등.

        :param step: 지정 시 빔 다운샘플(요청 JSON `{"step": N}`).
        :returns: `lasers` 배열. 키가 없으면 빈 리스트.
        """
        msg = {"step": int(step)} if step else None
        return self.call(ports.API_PORT_STATE, API_LASER, msg).get("lasers", [])

    def get_alarms(self) -> dict:
        """알람. fatals / errors / warnings 각각 `[{코드: epoch}]` 배열."""
        return self.call(ports.API_PORT_STATE, API_ALARM)

    def iter_alarms(self):
        """(level, code:int, timestamp:int) 로 평탄화해 순회한다."""
        resp = self.get_alarms()
        for level in ("fatals", "errors", "warnings"):
            for item in resp.get(level) or []:
                for code, ts in item.items():
                    yield level, int(code), ts

    def get_all_status(self) -> dict:
        """배치 조회(1100) — 1002~1050 대부분을 한 번에."""
        return self.call(ports.API_PORT_STATE, API_ALL)

    def get_map_status(self) -> dict:
        """맵 상태. current_map, current_map_md5, maps[]."""
        return self.call(ports.API_PORT_STATE, API_MAP_STATUS)

    def get_param(self, plugin: str, param: str) -> dict:
        """플러그인 파라미터 조회(1400). 응답에 value·defaultValue·min/maxValue 가 온다."""
        return self.call(ports.API_PORT_STATE, API_PARAM,
                         {"plugin": str(plugin), "param": str(param)})

    def get_max_connections(self, port: int):
        """해당 포트의 **현재** 동시연결 한도를 로봇에 물어본다.

        `ports.OBSERVED_MAX_CONNECTIONS` 는 관측 기본값일 뿐이고, 이 값은 런타임 파라미터라
        기체·시점마다 다를 수 있다(`minValue` 1 ~ `maxValue` 20). 판정이 필요하면 이걸 쓴다.
        조회 자체는 19204(조회 포트)로 나가므로 지령 게이트에 걸리지 않는다.

        :returns: 현재 값(int). 한도 파라미터가 없는 포트면 None.
        """
        name = ports.MAX_CONNECTION_PARAM.get(port)
        if name is None:
            return None
        resp = self.get_param("NetProtocol", name)
        return resp.get("NetProtocol", {}).get(name, {}).get("value")

    # ---- Config (19207, 배타) ----
    def download_map(self, map_name: str, verify_md5=None) -> bytes:
        """`.smap` 원문 바이트를 받는다 (4011 → 14011).

        응답 데이터부가 맵 JSON 원문 전체다 — 에러일 때만 ret_code/err_msg 객체가 온다.
        그래서 파싱하지 않고 바이트를 그대로 돌려주며, 오류 판정은 짧은 응답에 한해 시도한다.

        :param verify_md5: 주면 받은 바이트의 md5 와 대조(1300 의 current_map_md5).
        :raises SeerProtocolError: 로봇이 에러 객체를 반환했거나 md5 불일치.
        """
        raw, _ = self.transport(ports.API_PORT_CONFIG).request_raw(
            API_CONFIG_DOWNLOAD_MAP, {"map_name": map_name}
        )
        self._raise_if_error_payload(API_CONFIG_DOWNLOAD_MAP, raw)
        if verify_md5 is not None:
            got = hashlib.md5(raw).hexdigest()
            if got != verify_md5:
                raise SeerProtocolError(f"맵 md5 불일치 got={got} want={verify_md5}")
        return raw

    @staticmethod
    def _raise_if_error_payload(api_type: int, raw: bytes):
        """맵 원문 대신 에러 객체가 왔는지 판정.

        맵 JSON 은 수십만 바이트라 짧은 응답만 에러 후보로 본다 — 정상 맵을 파싱해
        키를 뒤지는 비용을 치르지 않기 위해서다.
        """
        if len(raw) > 4096:
            return
        import json as _json

        try:
            obj = _json.loads(raw.decode("utf-8", "replace") or "{}")
        except ValueError:
            return  # JSON 이 아니면 판정 불가 — 호출자에게 원문을 넘긴다
        if isinstance(obj, dict) and obj.get("ret_code") not in (0, None):
            raise SeerProtocolError(
                f"API {api_type} ret_code={obj.get('ret_code')} err_msg={obj.get('err_msg')!r}"
            )

    # ---- Control (19205, 배타) / Task (19206, 배타) / Other (19210, 배타) ----
    def stop(self) -> dict:
        """즉시 정지(2000). manual 모드 전용."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_STOP)

    def open_loop_move(self, vx: float = 0.0, vy: float = 0.0, w: float = 0.0) -> dict:
        """개루프 운동(2010). **manual 모드에서만 유효**하며 즉시 반환한다."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_MOTION,
                         {"vx": float(vx), "vy": float(vy), "w": float(w)})

    def relocate(self, x: float, y: float, angle: float) -> dict:
        """재측위(2002)."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_RELOC,
                         {"x": float(x), "y": float(y), "angle": float(angle)})

    def go_target(self, site_id: str) -> dict:
        """고정경로 내비게이션(3051) — 사이트 id 로 이동."""
        return self.call(ports.API_PORT_TASK, API_TASK_GOTARGET, {"id": str(site_id)})

    def set_do(self, do_id: int, status: bool) -> dict:
        """DO 출력(6001)."""
        return self.call(ports.API_PORT_OTHER, API_OTHER_SET_DO,
                         {"id": int(do_id), "status": bool(status)})
