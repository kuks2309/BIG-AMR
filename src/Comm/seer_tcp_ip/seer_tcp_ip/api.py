"""Seer(SRC) Robokit TCP API 바인딩 — 편호를 이름으로 감싼다.

19204(Status)·19301(Push) 는 조회라 직결이 열려 있고, 19205/06/07/19210 은 지령·설정이라
`allow_guarded=True` 없이는 막힌다.
"""
import hashlib

from . import ports
from .transport import SeerGuardedPortError, SeerProtocolError, SeerTransport

# ---- API 편호 (공식 SDK 이름 병기) ----

# 조회 — 19204 Status
API_ROBOT_INFO = 1000  # robot_status_info_req — model, vehicle_id, version
API_RUN_INFO = 1002  # robot_status_run_req — 운행시간·주행거리
API_MODE = 1003  # robot_status_mode_req
API_LOC = 1004  # robot_status_loc_req — x, y, angle
API_SPEED = 1005  # robot_status_speed_req — vx, vy, w, steer_angles
API_BLOCKED = 1006  # robot_status_block_req
API_BATTERY = 1007
API_BRAKE = 1008  # robot_status_brake_req
API_LASER = 1009  # robot_status_laser_req — lasers[].install_info / beams
API_PATH = 1010  # robot_status_path_req
API_AREA = 1011  # robot_status_area_req
API_ESTOP = 1012  # robot_status_emergency_req — emergency/soft_emc/driver_emc/electric
API_IO = 1013  # DI/DO
API_TASK_STATUS = 1020
API_RELOC_STATUS = 1021  # robot_status_reloc_req
API_LOADMAP_STATUS = 1022  # robot_status_loadmap_req
API_SLAM_STATUS = 1025  # {"return_resultmap": bool}
API_MOTOR_INFO = 1040  # motor_info[] — encoder·position (motor_name = Front/RearWalk|Steer)
API_ALARM = 1050  # fatals / errors / warnings
API_CONTROL_OWNER = 1060  # locked, ip, nick_name
API_ALL = 1100  # 배치 데이터 1
API_ALL2 = 1101  # 배치 데이터 2 — steer·r_steer(rad)
API_ALL3 = 1102  # 배치 데이터 3
API_INIT_STATUS = 1111  # robot_status_init_req
API_MAP_STATUS = 1300  # current_map, current_map_md5, maps[]
API_STATIONS = 1301
API_MAP_MD5 = 1302  # {"map_names":[…]} → map_info[]{name,md5}
API_PARAM = 1400  # robot_status_params_req — {"plugin":…, "param":…}
API_ROBOT_MODEL = 1500  # 응답 본문이 모델 JSON

# 제어 — 19205 Control
API_CTRL_STOP = 2000  # robot_control_stop_req
API_CTRL_GYRO = 2001  # robot_control_gyro_req
API_CTRL_RELOC = 2002  # robot_control_reloc_req
API_CTRL_CONFIRM_LOC = 2003  # robot_control_confirmloc_req
API_CTRL_MOTION = 2010  # {"vx","vy","w","duration"}

# 작업 — 19206 Task/Nav
API_TASK_PAUSE = 3001
API_TASK_RESUME = 3002
API_TASK_CANCEL = 3003
API_TASK_GOPOINT = 3050  # 자유 내비게이션
API_TASK_GOTARGET = 3051  # {"id","source_id",…}
API_TASK_PATROL = 3052
API_TASK_TRANSLATE = 3055  # 필드명 미확인 — 저수준 dict 만 받는다
API_TASK_TURN = 3056  # 필드명 미확인 — 저수준 dict 만 받는다
API_TASK_GOTARGET_LIST = 3066  # {"move_task_list":[…]}

# 설정 — 19207 Config
API_CONFIG_SET_MODE = 4000  # robot_config_setmode_req
API_CONFIG_SET_PARAMS = 4001  # 설정만 (저장 안 함)
API_CONFIG_SAVE_PARAMS = 4002  # 설정 + 저장
API_CONFIG_RELOAD_PARAMS = 4003
API_CONFIG_CLEAR_FATAL = 4004
API_CONFIG_SEIZE_CONTROL = 4005  # {"nick_name":…}
API_CONFIG_RELEASE_CONTROL = 4006  # 무파라미터
API_CONFIG_UPLOAD_MAP = 4010  # 요청 본문이 smap JSON 전체
API_CONFIG_DOWNLOAD_MAP = 4011  # {"map_name":…}, 응답 본문이 맵 JSON 전체

# 기타 — 19210 Other
API_OTHER_SPEAKER = 6000
API_OTHER_SET_DO = 6001  # {"id":N,"status":bool}
API_OTHER_SOFT_ESTOP = 6004  # {"status":bool}

#: 제어권 없이 지령했을 때 로봇이 내는 `ret_code`. 4005 를 먼저 잡아야 한다.
CONTROL_PREEMPTED_RET_CODE = 40020


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

    # ---- 조회 추가분 (19204) — 전부 무파라미터. 편호는 문서 표 근거 ----
    def get_run_info(self) -> dict:
        """운행 정보(1002) — 운행시간·주행거리."""
        return self.call(ports.API_PORT_STATE, API_RUN_INFO)

    def get_mode(self) -> dict:
        """운행 모드(1003)."""
        return self.call(ports.API_PORT_STATE, API_MODE)

    def get_blocked(self) -> dict:
        """피차단 상태(1006) — 장애물에 막혀 있는가."""
        return self.call(ports.API_PORT_STATE, API_BLOCKED)

    def get_brake(self) -> dict:
        """brake 상태(1008)."""
        return self.call(ports.API_PORT_STATE, API_BRAKE)

    def get_path(self) -> dict:
        """경로 데이터(1010)."""
        return self.call(ports.API_PORT_STATE, API_PATH)

    def get_area(self) -> dict:
        """현재 위치한 area(1011)."""
        return self.call(ports.API_PORT_STATE, API_AREA)

    def get_estop(self) -> dict:
        """급정지 상태(1012).

        키 구분이 중요하다 — `emergency`(물리 버튼) · `soft_emc`(6004 로 건 소프트 정지) ·
        `driver_emc` · `electric`. 소프트 정지는 6004 로 **해제해야** 다시 움직인다.
        """
        return self.call(ports.API_PORT_STATE, API_ESTOP)

    def get_reloc_status(self) -> dict:
        """재측위 진행 상태(1021). 2002 를 건 뒤 이것을 폴링하고 2003 으로 확정한다."""
        return self.call(ports.API_PORT_STATE, API_RELOC_STATUS)

    def get_loadmap_status(self) -> dict:
        """지도 로드 상태(1022)."""
        return self.call(ports.API_PORT_STATE, API_LOADMAP_STATUS)

    def get_slam_status(self, return_resultmap: bool = False) -> dict:
        """스캔(SLAM) 상태(1025).

        :param return_resultmap: 스캔 종료 후 True 로 폴링하면 완성된 지도가 `resultmap` 에 온다.
        """
        return self.call(ports.API_PORT_STATE, API_SLAM_STATUS,
                         {"return_resultmap": bool(return_resultmap)})

    def get_motor_info(self) -> list:
        """모터 정보(1040) — 축별 `encoder`·`position`.

        `motor_name` 은 `FrontWalk`/`RearWalk`/`FrontSteer`/`RearSteer`.
        값은 드라이브 `0x6064` 의 아핀 변환이므로 CAN 판독과 독립이 아니다 — 두 값을 서로의
        교차검증으로 쓸 수 없다.
        """
        return self.call(ports.API_PORT_STATE, API_MOTOR_INFO).get("motor_info", [])

    def get_control_owner(self) -> dict:
        """제어권 소유자(1060) — `locked`·`ip`·`nick_name`. 조회라 게이트에 걸리지 않는다."""
        return self.call(ports.API_PORT_STATE, API_CONTROL_OWNER)

    def get_all_status2(self) -> dict:
        """배치 데이터 2(1101) — `steer`·`r_steer`(rad) 포함."""
        return self.call(ports.API_PORT_STATE, API_ALL2)

    def get_all_status3(self) -> dict:
        """배치 데이터 3(1102)."""
        return self.call(ports.API_PORT_STATE, API_ALL3)

    def get_init_status(self) -> dict:
        """초기화 상태(1111)."""
        return self.call(ports.API_PORT_STATE, API_INIT_STATUS)

    def get_stations(self) -> list:
        """현재 지도의 스테이션 목록(1301) — `{id, type, x, y, r, desc}`."""
        return self.call(ports.API_PORT_STATE, API_STATIONS).get("stations", [])

    def get_map_md5(self, map_names) -> dict:
        """저장된 지도들의 md5(1302) → `{넘긴 이름: md5}`.

        로봇이 들고 있는 파일의 md5 라, 내려받은 바이트와 대조하면 파일 동일성이 확정된다.

        **1302 는 `.smap` 확장자를 요구하고 1300 은 확장자 없이 이름을 준다.** 그 비대칭을 여기서
        흡수한다 — 확장자가 없으면 붙여 보내고, 반환 키는 **호출자가 준 형태 그대로** 돌려준다.
        그래서 1300 의 `maps[]`·`current_map` 과 바로 맞물린다.

        **all-or-nothing 이다** — 목록에 없는 지도가 하나라도 있으면 로봇이 요청 전체를
        `ret_code 40051 "no this map file: <이름>"` 으로 거부한다. 부분 결과는 오지 않는다.

        :raises SeerProtocolError: 없는 지도가 섞였을 때(로봇 거부), 또는 응답에 요청한 이름이 빠졌을 때.
        """
        wanted = [str(n) for n in map_names]
        sent = [n if n.endswith(".smap") else n + ".smap" for n in wanted]
        resp = self.call(ports.API_PORT_STATE, API_MAP_MD5, {"map_names": sent})
        by_sent = {m.get("name"): m.get("md5") for m in (resp.get("map_info") or [])}
        missing = [o for o, s in zip(wanted, sent) if s not in by_sent]
        if missing:
            raise SeerProtocolError(f"1302 응답에 요청한 지도가 없다: {missing}")
        return {orig: by_sent[s] for orig, s in zip(wanted, sent)}

    def get_robot_model(self) -> dict:
        """로봇 모델 파일(1500). 응답 본문이 모델 JSON 이며 스키마는 기체별이다."""
        return self.call(ports.API_PORT_STATE, API_ROBOT_MODEL)

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

    # ---- 제어권 (19207, 게이트) ----
    def seize_control(self, nick_name: str) -> dict:
        """제어권 획득(4005). 지령 계열 API 는 이것 없이는 `ret_code 40020` 으로 거부된다.

        **기존 소유자의 제어권을 뺏는다.** 반납해도 원 소유자에게 자동 복귀하지 않는다 —
        그쪽이 다시 잡아야 한다. 뺏기 전 소유자를 남기려면 `get_control_owner()` 를 먼저 부른다.
        짝을 코드로 강제하려면 `control.SeerControlSession` 을 쓴다.

        :param nick_name: 로봇이 소유자로 표시할 이름.
        """
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_SEIZE_CONTROL,
                         {"nick_name": str(nick_name)})

    def release_control(self) -> dict:
        """제어권 반납(4006). 자기가 가진 것만 풀린다."""
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_RELEASE_CONTROL)

    # ---- Control (19205, 게이트) ----
    def stop(self) -> dict:
        """즉시 정지(2000)."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_STOP)

    def open_loop_move(self, vx: float, vy: float, w: float, duration_ms: int) -> dict:
        """개루프 운동(2010) — 속도 벡터를 직접 준다. 즉시 반환한다.

        `duration_ms` 는 **dead-man 타이머**다 — 그 시간 안에 새 지령이 오지 않으면 로봇이
        스스로 멈춘다. `0` 은 무한이며, 보내는 쪽이 죽어도 로봇이 계속 간다.
        기본값을 두지 않는 이유가 이것이다 — 호출자가 정지 시간을 반드시 고르게 한다.
        주기 재송신이 필요하면 `control.JogKeepalive` 를 쓴다.

        :param vx: 전진 m/s (로봇 좌표 +x 전방)
        :param vy: 횡 m/s (+y 좌)
        :param w: 회전 rad/s (+반시계)
        :param duration_ms: dead-man 시간(ms). 재송신 주기보다 커야 한다.
        """
        return self.call(ports.API_PORT_CTRL, API_CTRL_MOTION,
                         {"vx": float(vx), "vy": float(vy), "w": float(w),
                          "duration": int(duration_ms)})

    def calibrate_gyro(self) -> dict:
        """자이로 캘리브레이션(2001)."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_GYRO)

    def relocate(self, x: float, y: float, angle: float) -> dict:
        """재측위(2002) — 좌표 지정. 뒤이어 `get_reloc_status()` 폴링 → `confirm_location()`."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_RELOC,
                         {"x": float(x), "y": float(y), "angle": float(angle)})

    def relocate_with(self, params: dict) -> dict:
        """재측위(2002) — 좌표 외 방식용. `{"isAuto":True}`·`{"home":True}` 등을 그대로 싣는다."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_RELOC, dict(params))

    def confirm_location(self) -> dict:
        """측위 확정(2003). 재측위가 끝난 뒤 이것을 불러야 자동 운행으로 넘어간다."""
        return self.call(ports.API_PORT_CTRL, API_CTRL_CONFIRM_LOC)

    # ---- Task / Nav (19206, 게이트) ----
    def go_target(self, site_id: str, source_id: str = "SELF_POSITION",
                  task_id=None, **options) -> dict:
        """고정경로 내비게이션(3051) — 사이트 id 로 이동. 즉시 반환하며 도착은 1020 으로 본다.

        :param source_id: 출발 사이트. 기본값은 현재 위치.
        :param task_id: 작업 식별자(문자열로 실린다). None 이면 싣지 않는다.
        :param options: `max_speed`·`method`·`angle` 등을 요청 JSON 에 그대로 통과시킨다.
        """
        body = {"id": str(site_id), "source_id": str(source_id)}
        if task_id is not None:
            body["task_id"] = str(task_id)
        body.update(options)
        return self.call(ports.API_PORT_TASK, API_TASK_GOTARGET, body)

    def go_target_list(self, move_task_list) -> dict:
        """지정경로 내비게이션(3066) — 구간 목록을 순서대로 따른다.

        로봇이 **재계획하지 않는다** — 연속한 두 사이트가 지도에서 직접 연결돼 있어야 한다.
        각 구간은 `{"source_id","id"}` 에 `task_id`·작업 필드를 더한 dict.
        """
        return self.call(ports.API_PORT_TASK, API_TASK_GOTARGET_LIST,
                         {"move_task_list": list(move_task_list)})

    def go_point(self, body: dict) -> dict:
        """자유 내비게이션(3050) — 좌표로 이동. 요청 필드를 그대로 싣는다."""
        return self.call(ports.API_PORT_TASK, API_TASK_GOPOINT, dict(body))

    def patrol(self, body: dict) -> dict:
        """순찰(3052) — 경로 목록 반복. 요청 필드를 그대로 싣는다."""
        return self.call(ports.API_PORT_TASK, API_TASK_PATROL, dict(body))

    def translate(self, body: dict) -> dict:
        """평동(3055) — 고정 속도·고정 거리.

        요청 필드 이름이 확인되지 않아 dict 를 그대로 싣는다. 편의 인자를 만들지 않는 이유가
        그것이다 — 필드명을 추측하면 조용히 무시되거나 다른 동작이 된다.
        """
        return self.call(ports.API_PORT_TASK, API_TASK_TRANSLATE, dict(body))

    def turn(self, body: dict) -> dict:
        """회전(3056) — 고정 각속도·고정 각도. 필드명 미확인이라 dict 를 그대로 싣는다."""
        return self.call(ports.API_PORT_TASK, API_TASK_TURN, dict(body))

    def pause_task(self) -> dict:
        """현재 작업 일시정지(3001)."""
        return self.call(ports.API_PORT_TASK, API_TASK_PAUSE)

    def resume_task(self) -> dict:
        """일시정지한 작업 계속(3002)."""
        return self.call(ports.API_PORT_TASK, API_TASK_RESUME)

    def cancel_task(self) -> dict:
        """현재 작업 취소(3003)."""
        return self.call(ports.API_PORT_TASK, API_TASK_CANCEL)

    # ---- Config 쓰기 (19207, 게이트) ----
    def set_mode(self, body: dict) -> dict:
        """운행 모드 전환(4000). 요청 필드를 그대로 싣는다."""
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_SET_MODE, dict(body))

    def set_params(self, params: dict, save: bool = False) -> dict:
        """파라미터 설정. `save=False` 는 4001(휘발), `True` 는 4002(저장까지).

        본문은 `{플러그인: {키: 값}}` — 예: `{"MoveFactory": {"MaxAcc": 1.0}}`.
        """
        api = API_CONFIG_SAVE_PARAMS if save else API_CONFIG_SET_PARAMS
        return self.call(ports.API_PORT_CONFIG, api, dict(params))

    def reload_params(self) -> dict:
        """파라미터 재로드(4003)."""
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_RELOAD_PARAMS)

    def clear_fatal(self) -> dict:
        """Fatal 알람 클리어(4004)."""
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_CLEAR_FATAL)

    def upload_map(self, smap: dict) -> dict:
        """지도 업로드(4010) — 요청 본문이 smap JSON 전체다.

        저장만 하며 **활성 지도를 바꾸지 않는다.** 전환 편호는 자료가 엇갈려 여기서 감싸지 않는다.
        """
        return self.call(ports.API_PORT_CONFIG, API_CONFIG_UPLOAD_MAP, dict(smap))

    def soft_estop(self, on: bool) -> dict:
        """소프트 비상정지(6004). 걸면 로봇이 비상정지 신호를 내고, **해제해야 다시 움직인다.**

        걸린 상태는 `get_estop()` 의 `soft_emc` 로 보인다.
        """
        return self.call(ports.API_PORT_OTHER, API_OTHER_SOFT_ESTOP, {"status": bool(on)})

    def speaker(self, body: dict) -> dict:
        """스피커 제어(6000). 요청 필드를 그대로 싣는다."""
        return self.call(ports.API_PORT_OTHER, API_OTHER_SPEAKER, dict(body))

    def set_do(self, do_id: int, status: bool) -> dict:
        """DO 출력(6001)."""
        return self.call(ports.API_PORT_OTHER, API_OTHER_SET_DO,
                         {"id": int(do_id), "status": bool(status)})
