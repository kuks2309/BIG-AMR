# ADR 2026-08-07 — Seer TCP/IP API 를 `src/Comm/TCP_IP/seer_api` 로 분리하고 HAL 경계를 ROS 인터페이스에 둔다

- **Status**: Accepted — 2026-08-07, **사실 2·3 정정 2026-08-10**
  (라이브러리·이관 실기 검증 완료 / broker 노드는 미착수 — §Decision 3 참조)
  ⚠ 초판의 "지령 포트 동시연결 1" 전제는 **반증됐다**(실제 5, 거부형). 결론은 유지, 근거·이름 교체.
  경위: `docs/claude-mistake/2026-08-07-002`.

## Context

### 사실 1 — 프로토콜 구현이 이미 중복돼 있다

Seer(SRC) Robokit NetProtocol 은 **16B 헤더(0x5A) + JSON, 응답 편호 = 요청 + 10000** 의 TCP 1문1답이다
(정본: `References/Seer-Driver/seer_api_guide.md` §3, 원본 `github_sdk/Robokit_TCP_API_py/netprotocol/rbkNetProtoEnums.py`).
이 헤더 포맷이 저장소 안에서 **각자 재구현**된 곳:

| 위치 | 구현 |
|---|---|
| `src/Sensors/Lidar/2D/seer_read_lidar_install.py:24,35` | `struct.pack(">BBHIH6s", 0x5A, 0x01, 1, ...)` |
| `src/Sensors/Lidar/2D/seer_lidar_tf/seer_lidar_tf/seer_lidar_tf_node.py:25,27,149,156` | `_SYNC/_HDR` 자체 상수 + `_recv_n` 자체 구현 |

두 구현 모두 **seq 를 1 로 고정**하고, 응답 seq 를 대조하지 않으며, 요청 간격 제한이 없다.
`seer_read_lidar_install.py:29-41` 은 부분 수신 시 `break` 로 빠져나가 **짧은 버퍼를 그대로 `struct.unpack`** 에 넣는다
(길이 부족 시 `struct.error`, 조용한 절단은 아니지만 원인 메시지가 없다).

### 사실 2 — 동시연결 한도는 **문서 상수가 아니라 로봇의 런타임 파라미터**다

> ❌ **정정 2026-08-10.** 초판은 여기에 `seer_api_guide.md` §2 표를 근거로
> "19205/06/07/10 은 동시연결 **1** 이라 선점되면 타 연결이 거부된다"고 적었다. **틀렸다.**
> 원본 하드와 실기를 직접 조회한 결과는 아래와 같다. 초판 서술은 이력으로 보존한다.

**[실측 2026-08-07]** 두 경로가 같은 값을 낸다.

- **원본 하드**(amap-server `/media/amap/6ab6980d-…`, `sdb2` 59.1G — Seer 루트파일시스템 사본):
  `usr/local/etc/.SeerRobotics/rbk/resources/params/robot.param`(SQLite) `NetProtocol` 테이블.
  하드의 `rbk/product.version.h` = `PRODUCT_FULL_VERSION "3.4.5.22"` — **실기 컨트롤러와 동일 버전**.
- **실기**(192.168.44.82) API 1400 `{"plugin":"NetProtocol","param":<이름>}` 6건.

| 포트 | 파라미터 | 값 | `defaultValue` | 범위 |
|---|---|---|---|---|
| 19204 Status | `RobotStatusAPITCPServerMaxConnections` | **10** | 10 | 1~20 |
| 19205 Control | `RobotControlAPITCPServerMaxConnections` | **5** | 5 | 1~20 |
| 19206 Task | `RobotTaskAPITCPServerMaxConnections` | **5** | 5 | 1~20 |
| 19207 Config | `RobotConfigAPITCPServerMaxConnections` | **5** | 5 | 1~20 |
| 19210 Other | `RobotOtherAPITCPServerMaxConnections` | **5** | 5 | 1~20 |
| 19301 Push | `RobotPushTCPServerMaxConnections` | **10** | 10 | 1~20 |

즉 **1이 아니라 5**이고, `type: uint32, minValue: 1, maxValue: 20, advanced: true` 로 신고되는
**변경 가능한 설정값**이다. 판본으로 정해지는 상수가 아니므로 "v1.2.1 이냐 v1.4.2 냐"는 애초에
답을 줄 수 없는 질문이었다. `libNetProtocol.so` 가 이 파라미터를 읽어 쓴다(심볼
`_robotControlAPITCPServerMaxConnections` 등 6종, 문자열 `Maximum connections of control API`).

### 사실 3 — 한도 초과 시 거동은 **거부형**이다 (선점 아님)

**[실측 2026-08-07]** 19204(한도 10)에 연결을 늘려가며 관측:

- 8번째까지 성공, **9번째부터 거부**(당시 타 클라이언트가 2 슬롯 점유 중이었던 것으로 보인다).
- 거부 프레임은 편호 규칙(요청+10000)을 **따르지 않는다** — 편호가 **포트 번호 `19204`** 로 오고
  본문이 `{"ret_code":61001,"err_msg":"reach the maximum of status api connection limitation",
  "ip":"192.168.44.2","port":52248, …}`.
  `err_msg` 는 `libNetProtocol.so` 안의 문자열과 **정확히 일치** — 바이너리 ↔ 실기 동작 일치 확인.
- **거부 후에도 기존 연결 #1 이 정상 응답**했다 ⇒ 신규만 거부, 기존은 유지.

⇒ **"선점당해 현장 작업이 끊긴다"는 위험은 존재하지 않는다.** broker 의 근거는 소켓 희소성이
아니라 **지령 중재**(두 주체가 동시에 로봇을 움직이면 소켓이 남아돌아도 사고)로 옮겨간다.

### 사실 4 — HAL 경계를 잘못 두면 교체가 불가능해진다

`Comm/TCP_IP` 는 *전송 수단*으로 나눈 축이고, HAL 이 요구하는 축은 *누가 그 능력을 제공하는가*
(Seer 컨트롤러냐 우리 스택이냐)다. 상위 노드가 `seer_api` 를 직접 import 하면, Seer 를 우리
MCL/nav(`src/Navigation/mcl2d_*`)로 교체할 때 상위 코드를 전부 고쳐야 한다.

### 확인한 제약 (2026-08-07 실측)

```
ping 192.168.44.82 → 0% loss, 6.6ms (dev wlan0 src 192.168.44.2)
port 19204: OPEN / port 19207: OPEN
API 1000 → model=Foil_A082, version=v3.4.5.22
```

`v3.4.5.22` 는 컨트롤러 버전이며 프로토콜 문서 판본(v1.2.1 / v1.4.2)과의 대응표는 여전히 없다.
그러나 **그 대응표는 필요하지 않다** — 사실 2 대로 한도는 판본이 아니라 파라미터가 정하고,
그 값은 로봇에 직접 물어볼 수 있다(`SeerApi.get_max_connections()`).

## Decision

### 1. 배치 — `src/Comm/TCP_IP/seer_api/` (ament_python)

`Comm/<전송>/<상대방>` 축을 `Comm/CAN/can_relay` 와 대칭으로 맞춘다. `Comm/TCP_IP` 는 **전송 버킷**,
`seer_api` 는 **상대방 이름 패키지**다. `Comm/TCP_IP` 아래에 Seer 외 TCP 상대가 생기면 형제 패키지로 추가한다.

### 2. 3층 구조 — 교체 시 무엇이 삭제되고 무엇이 남는지로 층을 가른다

| 층 | 파일 | 책임 | Seer 폐기 시 |
|---|---|---|---|
| 전송 | `seer_api/transport.py` | 소켓, 16B 헤더 pack/unpack, seq 순환·응답 seq 대조, `recv_exact`, 타임아웃·재연결, 최소 요청 간격 | **삭제** |
| 포트 정책 | `seer_api/ports.py` | 포트 상수 + 관측 한도·한도 파라미터 이름 + 게이트 집합 판정 | **삭제** |
| API 바인딩 | `seer_api/api.py` | 편호별 타입드 호출(1004/1005/1007/1009/1050/1300/2000/2010/4011/6001) | **삭제** |
| **HAL 경계** | **ROS2 토픽·서비스·액션 계약** | 능력 이름(`/odom`, 배터리, 맵, nav) | **유지** — 구현만 교체 |

**HAL 경계는 파이썬 클래스가 아니라 ROS 인터페이스 이름이다.** `seer_api` 는 그 계약의 한 구현일 뿐이며,
상위 알고리즘 패키지는 `seer_api` 를 import 하지 않는다.

### 3. 포트 접근 정책 — 지령·설정 포트는 라이브러리 직결 금지

> ❌ **근거 정정 2026-08-10.** 초판의 근거는 "동시연결 1 이라 선점된다"였고 그 표현으로
> `EXCLUSIVE_PORTS`·`allow_exclusive`·`SeerExclusivePortError` 라 이름 붙였다. 사실 2·3 이
> 그 전제를 반증했다(한도 5, 거부형). **결론(어느 포트를 막을지)은 그대로 두고 근거와 이름만
> 바꾼다** — 막아야 할 진짜 이유는 소켓 희소성이 아니라 **지령 중재**다.

- **19204(Status) · 19301(Push)** — 조회. 라이브러리 직결 **허용**. 진단 스크립트·Tools 자유 사용.
- **19205/19206/19207/19210** — 로봇을 움직이거나(2000·2002·2010·3051) 출력·설정을 바꾼다(6001·4002).
  라이브러리 직결 **금지**: 두 주체가 동시에 지령하면 연결이 남아돌아도 위험하다.
  단일 소유 broker 노드가 소켓을 소유하고 다른 노드는 ROS 서비스로 요청한다.
  코드로 강제한다 — `SeerApi(..., allow_guarded=False)` 가 기본이며 해당 포트 호출 시
  `SeerGuardedPortError`. 단발 도구(smap 다운로드 등)는 `allow_guarded=True` 를 **명시**해야 하고,
  그 명시가 "지금 이 도구가 지령 포트를 쓴다"는 흔적이 된다.
- **게이트 집합은 명시 집합(`GUARDED_PORTS`)으로 둔다 — 한도에서 파생하지 않는다.**
  한도가 5 이므로 `n <= 1` 파생은 **빈 집합**이 되어 게이트가 조용히 사라진다.
  이 함정은 돌연변이 `P2` 가 지킨다.
- **한도 자체는 상수로 신뢰하지 않는다.** `OBSERVED_MAX_CONNECTIONS` 는 참고값이고,
  판정이 필요하면 `SeerApi.get_max_connections(port)` 가 API 1400 으로 로봇에 묻는다.
  이 조회는 19204 로 나가므로 게이트에 걸리지 않는다.
- **한도 초과 거부는 전용 예외로 구분한다.** 거부 프레임은 편호가 포트 번호로 오므로 일반
  편호 대조에 걸리면 "응답 편호 19204(기대 11004)" 라는 오해를 부른다 — 실제로 첫 실측에서
  그 메시지가 나왔다. `SeerConnectionLimitError`(=`SeerProtocolError` 하위)로 원인을 남긴다.
- **broker 노드는 본 ADR 범위 밖**(다음 단계, debt-072). 지금 이관하는 두 소비자는 둘 다 19204
  조회이므로 broker 없이 정책을 위반하지 않는다.

### 4. 이관 대상 (본 ADR 범위)

- `src/Sensors/Lidar/2D/seer_lidar_tf/seer_lidar_tf/seer_lidar_tf_node.py` — 자체 헤더·`_recv_n` 제거 → `SeerApi.get_lasers()`
- `src/Sensors/Lidar/2D/seer_read_lidar_install.py` — 동일

이 두 건이 분리의 **첫 회수분**이자 계약의 실사용 검증이다.

## Alternatives (기각)

| 안 | 기각 사유 |
|---|---|
| `src/Comm/Seer/` (상대방 축으로 최상위 분류) | `Comm/CAN/can_relay` 와 축이 어긋난다. 같은 상대(Seer)와 CAN·TCP 두 전송으로 말하는 상황이 실재하므로(판다 CAN 릴레이 ↔ Seer 마스터), 상대방을 최상위로 두면 CAN 쪽과 충돌한다. |
| `src/Sensors/Lidar/2D` 안에 공용 모듈 하나 | Seer API 는 라이다 전용이 아니다(위치·배터리·알람·맵·DO). 센서 패키지에 두면 Navigation 이 Sensors 를 의존하게 된다. |
| 외부 저장소 `T-Robot_seer_gui/seer_core/client.py` 를 그대로 서브모듈로 | 이 저장소는 서브모듈·상류 원격이 없다(README 규약). 코드 사본 대신 `References/Seer-Driver/` 원문 대조로 동등성을 검증한다. |
| 라이브러리만 두고 broker 없이 전 포트 개방 | 두 주체가 동시에 지령하면 위험하다(사실 3 으로 "선점" 근거는 사라졌지만 **중재** 근거는 남는다). |
| 실측으로 근거가 무너졌으니 게이트를 없앤다 | 무너진 것은 *근거*이지 *위험*이 아니다. 소켓이 5개 남아돌아도 두 주체의 동시 지령은 사고다. 근거와 이름만 교체하고 게이트는 유지한다. |

## Consequences

**이득**
- 헤더 재구현이 2곳 → 0곳. 새 소비자는 `SeerApi` 를 쓴다.
- 두 이관 대상이 공짜로 얻는 것: seq 순환·응답 seq 대조·부분 수신 정확 처리·요청 간격 제한·명확한 예외.
- 지령 포트 게이트가 코드로 강제돼, 문서를 안 읽은 다음 세션도 기본값에서 막힌다.
- Seer 교체 시 삭제 대상이 한 디렉토리로 국한된다.
- **동시연결 한도가 미지에서 실측·질의 가능으로 바뀌었다** — 벤더 문의 없이 로봇이 직접 답한다.

**비용**
- `seer_lidar_tf` 가 `seer_api` 에 exec_depend 를 갖는다(colcon 빌드 순서 의존 1건 증가).
- `seer_read_lidar_install.py` 는 패키지 밖 단독 스크립트라, 미소싱 환경을 위해 소스 트리 경로 fallback 을 둔다.

**남는 위험 / 미해결**
- **broker 노드 미착수** (→ **debt-072**) — 지령 포트를 쓰는 실사용(제어·내비·설정)이 생기면 그때 필요하다.
  현재는 `allow_guarded=True` 명시로 단발 사용만 열려 있고, 그 우회구로 두 도구가 동시에 켜지면
  **동시 지령**이 그대로 난다(연결은 5개까지 받아주므로 로봇이 막아 주지 않는다).
- **HAL 경계 메시지 계약 미확정** (→ **debt-073**) — 어떤 토픽/서비스를 우리 표준으로 둘지는 별도 결정.
  본 ADR 은 "경계를 ROS 인터페이스에 둔다"는 위치만 정하고 목록은 정하지 않았다.
  세 번째 소비자가 사실상 계약을 정해버리므로 그 전에 확정해야 한다.
- **Push API(19301) 미구현** — 구독 항목 설정 방법이 `seer_api_guide.md` §6 에서 미열람(⚠)으로 남아 있다.

## Verification (2026-08-07 초판 / 2026-08-10 갱신)

| 무엇 | 결과 | 근거 |
|---|---|---|
| 단위 회귀 | **50 passed** | `python3 -m pytest test/ -q` (패키지 루트) |
| 공식 SDK 바이트 동일성 | 본문 있음/없음 모두 `packMsg` 와 일치 | `test_transport.py::test_pack_matches_official_sdk_*` — 원본 `rbkNetProtoEnums.py` 를 직접 로드해 대조 |
| **회귀 검출력** | **33/33 검출** | `python3 src/Comm/TCP_IP/seer_api/mutation_check.py` |
| colcon 빌드 | `seer_api`, `seer_lidar_tf` 2패키지 성공 | `colcon build --packages-select seer_api seer_lidar_tf --symlink-install` |
| 실기 조회 | 1000/1004/1009/1300/1400 정상 | `Foil_A082 v3.4.5.22`, FrontLiDAR·RearLiDAR install_info, `current_map=260709_test` |
| **동시연결 한도** | 19204·19301=**10**, 19205/06/07/10=**5** | 실기 API 1400 6건 + 원본 하드 `robot.param` `NetProtocol` 테이블(동일 값) |
| **한도 초과 거동** | **거부형** — 신규만 거부, 기존 연결 생존 | 19204 에 연결 증가 → 9번째부터 `type=19204`, `ret_code=61001`; 직후 #1 재요청 정상 |
| 바이너리 ↔ 실기 정합 | `err_msg` 문자열 일치 | `libNetProtocol.so` 의 `reach the maximum of status api connection limitation` = 실기 응답 본문 |
| 이관 등가성 | `seer_read_lidar_install.py` 출력 **바이트 동일** | 이전 리비전(`git show HEAD:…`)과 `diff` 무차이 |
| 이관 노드 실기 | TF 발행 정상 | `ros2 run seer_lidar_tf seer_lidar_tf_node` → `base_footprint -> [scan_front, scan_rear]` |
| 이관 노드 실패경로 | 재시도 반복, 크래시·소켓 누수 없음 | 도달불가 IP(`192.168.44.199`)로 기동 → `Seer 조회 실패(timed out) — 2.0s 후 재시도` |

⚠ **검증 범위 한정** — 위가 보증하는 것은 "이 목록의 동작이 회귀로 고정돼 있고, 19204 조회 경로와
한도·거부 거동이 실기에서 확인됐다"까지다. **지령 포트(19205/06/10)의 쓰기 API 는 실기에서 한 번도
호출하지 않았다** — `stop`·`open_loop_move`·`relocate`·`go_target`·`set_do` 는 단위 시험(가짜 소켓)만
통과했다. 19207 `download_map` 도 미호출이다. 문서 서술·안전 문구는 기계 검증 대상이 아니다.

**검증 과정에서 하네스 자체의 결함 3건을 잡았다** (기록 목적 — 「전부 검출」이 세 번 거짓이었다):
1. `mutation_check.py` 초기판이 **`__pycache__` 오염**으로 27/27 을 보고했다 — `.pyc` 유효성이
   (mtime 초, 파일크기)로 판정되므로 같은 초에 같은 크기로 쓴 변조(1004→1005, 4011→4010)가
   직전 항목의 바이트코드를 재사용했다. `python -B` + `PYTHONDONTWRITEBYTECODE` + `__pycache__`
   삭제로 고친 뒤 다시 돌리자 **A5 는 실제로 미검출**이었다.
2. 그 A5(맵 편호 4011)를 잡는 시험이 없던 이유는 **기대값에 상수 자신을 썼기** 때문이다
   (`assert calls == [(api.API_CONFIG_DOWNLOAD_MAP, …)]` — 상수를 바꾸면 기대값도 같이 바뀐다).
   편호·포트를 **리터럴로 고정하는 시험**을 추가해 닫았다.
3. 08-10 정정 때 새로 넣은 **P2 돌연변이가 무력**이었다 —
   `frozenset(파생) or frozenset({리터럴})` 로 썼는데 파생 집합이 비면 falsy 라 `or` 가 원본으로
   되돌아가 **아무것도 변조하지 않았다.** 「미검출」을 보고 시험을 의심했으나 범인은 돌연변이였다.
   ⇒ **미검출이 나오면 시험보다 돌연변이를 먼저 의심한다**(주석으로 박제).

## Rollback

가역. 되돌리는 절차:

1. `git revert` 또는 이관 2파일을 이전 리비전으로 복원 —
   `git checkout <이전-커밋> -- src/Sensors/Lidar/2D/seer_read_lidar_install.py src/Sensors/Lidar/2D/seer_lidar_tf/`
2. `src/Comm/TCP_IP/` 디렉토리 삭제.
3. `seer_lidar_tf/package.xml` 의 `<exec_depend>seer_api</exec_depend>` 제거.
4. `colcon build --packages-select seer_lidar_tf` 재실행.

영속 상태·스키마·펌웨어 변경 없음. Seer 컨트롤러에 쓰기 동작 없음(조회만).
