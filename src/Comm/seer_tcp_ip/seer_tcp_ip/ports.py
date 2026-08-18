"""Seer(SRC) Robokit TCP API 포트 정책.

동시연결 한도는 고정 상수가 아니라 로봇의 런타임 파라미터다
(`Robot<카테고리>APITCPServerMaxConnections`, `uint32`, 1~20, 기체·시점마다 바뀔 수 있다).
아래 표는 관측 기본값이며 정확한 값은 `SeerApi.get_max_connections()` 로 로봇에 묻는다.
"""

# 포트 상수 — 공식 SDK 이름 유지(원문 대조가 가능해야 한다)
API_PORT_ROBOD = 19200  # 코어 데몬
API_PORT_STATE = 19204  # 조회
API_PORT_CTRL = 19205  # 즉시 제어
API_PORT_TASK = 19206  # 내비게이션·작업
API_PORT_CONFIG = 19207  # 파라미터·맵 설정
API_PORT_KERNEL = 19208  # 종료·재시작
API_PORT_OTHER = 19210  # DO·스피커
API_PORT_PUSH = 19301  # 로봇 능동 push

#: 포트 → 한도 파라미터 이름 (API 1400 `{"plugin":"NetProtocol","param":<이름>}` 으로 조회).
MAX_CONNECTION_PARAM = {
    API_PORT_STATE: "RobotStatusAPITCPServerMaxConnections",
    API_PORT_CTRL: "RobotControlAPITCPServerMaxConnections",
    API_PORT_TASK: "RobotTaskAPITCPServerMaxConnections",
    API_PORT_CONFIG: "RobotConfigAPITCPServerMaxConnections",
    API_PORT_OTHER: "RobotOtherAPITCPServerMaxConnections",
    API_PORT_PUSH: "RobotPushTCPServerMaxConnections",
}

#: Foil_A082(rbk 3.4.5.22) 관측 기본값. 정본이 아니다 — 판정은 `get_max_connections()` 로 한다.
OBSERVED_MAX_CONNECTIONS = {
    API_PORT_STATE: 10,
    API_PORT_CTRL: 5,
    API_PORT_TASK: 5,
    API_PORT_CONFIG: 5,
    API_PORT_OTHER: 5,
    API_PORT_PUSH: 10,
}

#: 한도 초과 시 로봇이 내는 `ret_code`. 그 거부 응답의 편호는 요청+10000 이 아니라
#: **포트 번호 그대로**이고, 본문 `err_msg` 는 "reach the maximum of … connection limitation".
CONNECTION_LIMIT_RET_CODE = 61001

#: 라이브러리 직결을 막는 포트 — **연결 수가 부족해서가 아니라 지령이 겹치면 위험해서**다.
#: 한도는 5 이고 초과는 거부형(기존 연결 유지)이라 선점 위험은 없다. 그래도 막는 이유는 중재다 —
#: 두 주체가 동시에 로봇을 움직이거나 설정을 쓰면 소켓이 남아돌아도 사고가 난다.
#: 이 집합은 **명시 집합**이다. 한도에서 파생하면 5 > 1 이라 비어서 게이트가 조용히 사라진다.
GUARDED_PORTS = frozenset({
    API_PORT_CTRL,    # 2000 정지 · 2002 재측위 · 2010 개루프 주행
    API_PORT_TASK,    # 3051 자율 주행
    API_PORT_CONFIG,  # 4002 파라미터 쓰기 (4011 맵 다운로드는 읽기지만 포트 단위로 묶는다)
    API_PORT_OTHER,   # 6001 DO 출력
})

#: 요청 간 최소 간격(초). 가이드 §1 "≥100~200ms 권장, 과빈번 시 로봇이 연결 정리".
MIN_REQUEST_INTERVAL_S = 0.1

#: 응답 편호 = 요청 편호 + 이 값 (가이드 §3). 오류 응답은 이 규칙을 따르지 않는다.
RESPONSE_TYPE_OFFSET = 10000


def is_guarded(port: int) -> bool:
    """라이브러리 직결을 막는 포트인가 (지령·설정 계열).

    막는 이유는 연결 수가 아니라 **지령 중재**다 — `GUARDED_PORTS` 주석 참조.
    """
    return port in GUARDED_PORTS


def observed_max_connections(port: int):
    """관측 기본 동시연결 한도. 미관측 포트는 None.

    ⚠ 이 값은 참고용이다. 로봇이 실제로 쓰는 값은 런타임에 바뀔 수 있으므로
    판정이 필요하면 `SeerApi.get_max_connections(port)` 로 로봇에 물어본다.
    """
    return OBSERVED_MAX_CONNECTIONS.get(port)
