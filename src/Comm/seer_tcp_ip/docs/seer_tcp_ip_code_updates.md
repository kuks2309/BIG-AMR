# seer_tcp_ip Code Updates

> 인벤토리(함수표·전역변수표): [docs/code_review/seer_tcp_ip/2026-08-07.md](code_review/seer_tcp_ip/2026-08-07.md)
> 설계 결정: [ADR 2026-08-07-seer-api-tcp-hal](../../../../docs/adr/2026-08-07-seer-api-tcp-hal.md)

## 2026-08-18 / (pending commit) — 편호 커버리지 17 → 50, 제어권 세션 신설, `duration` 필수화

- **왜**: 모션 지령이 그대로는 동작하지 않았다. Seer 는 지령 전에 제어권(4005)을 요구하고 없으면
  `ret_code 40020` 으로 거부하는데, 패키지에 4005/4006/1060 래퍼가 없었다.
  (ADR `2026-08-18-seer-tcp-ip-api-coverage.md`)
- **조사**: 동봉 참조 문서(`References/Seer-Driver/robokit_tcp_api.md`)에 4005·4006·1060·1040·
  1302·1500·3066·4010·6004 가 **없다**. 요청 JSON 형태까지 있는 정본은 사용자 저장소
  `T-Robot_seer_gui/seer_core/client.py`(로컬 485줄)였다. 근거 없는 편호는 감싸지 않았다.
- **신설** `control.py` — `SeerControlSession`(획득→사용→정지→반납, 예외 경로에서도 반납),
  `JogKeepalive`(dead-man 재송신, `interval < duration` 불변식 검증), `preempted_by_control`,
  `describe_owner`. 스레드를 만들지 않고 호출자가 `tick()` 을 부른다.
- **파괴 변경**: `open_loop_move(vx, vy, w, duration_ms)` — `duration_ms` 를 **필수**로 했다.
  `duration` 은 dead-man 타이머이고 이전 구현은 그 필드를 아예 보내지 않아, 보내는 쪽이 죽었을 때
  로봇이 서는지 말할 수 없었다. 기본값을 두지 않은 이유는 호출자가 정지 시간을 반드시 고르게 하기
  위해서다. 저장소 내 호출자 0건이라 실비용 없음.
- **`go_target`**: `source_id`(기본 `SELF_POSITION`)·`task_id`·임의 옵션 통과를 추가. 이전에는
  `{"id"}` 만 보내 참조 구현과 달랐다.
- **실기에서 잡은 것 2건**
  1. **1302 는 `.smap` 확장자를 요구한다** — 1300 이 주는 이름을 그대로 넣으면
     `ret_code 40051 "no this map file"`. 래퍼가 확장자를 붙이고 반환 키는 호출자 형태로 돌려
     1300 과 맞물리게 했다. 붙인 뒤 md5 가 1300 의 `current_map_md5` 와 일치.
  2. **1302 는 all-or-nothing** — 없는 지도가 섞이면 요청 전체를 거부한다. 처음엔 「없는 것은 빼고
     돌려준다」로 설계·시험했는데 **가짜 소켓이 그 가정을 통과시켰고 실기 호출이 뒤집었다.**
     응답에 요청한 이름이 없으면 예외로 바꿨다(None 이 md5 처럼 흘러가면 대조가 조용히 통과한다).
- **주석 규칙 위반 정정**: 초안에서 근거·인용·정정 이력을 주석에 넣었다가 걷어냈다. 근거는
  인벤토리 §0 으로 옮겼다(경위: `docs/claude-mistake/2026-08-18-001`).
- **검증**: 100 passed · 돌연변이 **57/57 검출**(신규 C1~C12·N1~N12) · flake8 0 · 금지패턴 0 ·
  colcon 2패키지 · 실기 조회 경로 확인(§ 인벤토리 6).
- **잔여(⚠)**: 쓰기 API 24종은 **실기 미검증**(단위 시험만). 2022 편호 충돌 미해소.
  Push(19301) 미구현. broker 미착수 상태에서 제어권 세션이 생겨 **동시 4005 사고가 이제 실제로
  가능**해졌다.

## 2026-08-17 / (pending commit) — 패키지를 `Comm/seer_tcp_ip` 로 옮기고 이름을 `seer_tcp_ip` 로 바꿈

- **왜**: `seer_api` 는 어느 API 인지 말하지 않았다 — Seer 는 TCP/IP NetProtocol·ModbusTCP·내부 zmq
  를 모두 갖고 있고 이 패키지는 첫 번째 전용이다. 그리고 `Comm/TCP_IP/` 중간층은 자식이 하나뿐이라
  아무것도 묶고 있지 않았다. 형제 `can_relay` 도 이름 자체에 전송을 담는다.
  (ADR `2026-08-07-seer-api-tcp-hal` §Decision 1 개정)
- **조치**
  - `src/Comm/TCP_IP/seer_api/` → `src/Comm/seer_tcp_ip/`, 내부 모듈 디렉토리·`resource/` 마커 동반 개명.
    빈 껍데기가 된 `src/Comm/TCP_IP/` 제거.
  - `package.xml <name>`·`setup.py package_name`·`setup.cfg` 경로·`mutation_check.py PKG` 를 `seer_tcp_ip` 로.
  - 소비자 3곳 갱신 — `seer_lidar_tf`(exec_depend + import 2), `seer_read_lidar_install.py`(import +
    소스 트리 fallback 경로), `Tools/seer_re/seer_param.sh`(PYTHONPATH + import).
  - `References/Seer-Driver/seer_api_guide.md` 인용은 **참조 문서 파일명**이라 그대로 둔다.
- **부수 수선**: `test_transport.py` 의 공식 SDK 경로가 고정 `../` 5단이라 이동 후 어긋났다.
  `_load_official` 이 조용히 skip 하면서 바이트 동일성 시험 3건과 그것이 지키던 돌연변이 `T4` 의
  검출력이 함께 사라졌다(47 passed + 3 skipped, T4 미검출). **저장소 루트를 위로 탐색하는
  `_find_sdk()`** 로 바꿔 깊이에 무관하게 만들었다 — 돌연변이 검사가 이 퇴행을 잡았다.
- **검증**: 50 passed · 돌연변이 **33/33 검출** · flake8 0 · `colcon build --packages-select
  seer_tcp_ip seer_lidar_tf` 성공 · 실기(192.168.44.82) 3경로 정상 — 단독 스크립트 출력 동일,
  노드 TF 발행(`base_footprint -> [scan_front, scan_rear]`), `seer_param.sh` API 1400 조회(value=5).
- **잔여(⚠)**: `Comm/CAN/can_relay` 는 그대로라 `Comm/` 아래 깊이가 섞인다. systemd 배포가 경로에
  의존할 수 있어 확인 없이 옮기지 않았다 — 평탄화는 미결(ADR §Decision 1).

## 2026-08-10 / (pending commit) — 포트 정책의 전제가 실측으로 뒤집혀 값·근거·이름을 교체

- **증상**: 초판이 지령 포트 동시연결 한도를 **1** 로 박고(`MAX_CONNECTIONS_V121`),
  `EXCLUSIVE_PORTS` 를 그 값에서 `n <= 1` 로 **파생**시켰다. 근거는 동봉 PDF(protocol v1.2.1)뿐이고,
  실기 컨트롤러가 어느 판본인지 몰라 "보수적으로" 택한 값이었다.
- **진단**: 원본 하드(amap-server `sdb2`, Seer 루트파일시스템 사본, `rbk/product.version.h` =
  `3.4.5.22` 로 **실기와 동일 버전**)와 실기 API 1400 을 조회한 결과 전제가 무너졌다.
  - 한도는 **판본이 정하는 상수가 아니라 로봇의 런타임 파라미터**다 —
    `Robot<카테고리>APITCPServerMaxConnections`, `uint32`, `minValue` 1 ~ `maxValue` 20, mutable.
  - 값은 **19204·19301 = 10, 19205/06/07/10 = 5** (두 경로 일치). 초판의 1 은 5배 틀렸다.
  - 초과 시 거동은 **거부형** — 신규만 거부되고 기존 연결은 살아남는다(19204 실측).
    거부 프레임은 편호 규칙(요청+10000)을 따르지 않고 **편호 = 포트 번호**, `ret_code 61001`,
    `err_msg` 는 `libNetProtocol.so` 안의 문자열과 정확히 일치.
  - ⇒ 게이트의 근거였던 **"선점 사고" 위험은 존재하지 않는다.** 남는 위험은 **지령 중재**다.
  - ⚠ 값을 실측(5)으로 고치면 `n <= 1` 파생 집합이 **빈 집합**이 되어 게이트가 조용히 사라진다 —
    틀린 사실 위에 강제 장치를 얹었던 구조적 결함.
- **조치**:
  - `ports.py` — `MAX_CONNECTIONS_V121` → `OBSERVED_MAX_CONNECTIONS`(실측값, docstring 이 스스로
    "정본 아님·런타임 파라미터"를 선언). `MAX_CONNECTION_PARAM`(포트→파라미터 이름) ·
    `CONNECTION_LIMIT_RET_CODE = 61001` 신설.
  - `EXCLUSIVE_PORTS`(파생) → **`GUARDED_PORTS`(명시 집합)**. 근거를 "동시연결 1"(반증됨) →
    "지령 중재"(반증 불가)로 교체. `is_exclusive` → `is_guarded`.
  - `transport.py` — `SeerExclusivePortError` → `SeerGuardedPortError`.
    `SeerConnectionLimitError`(=`SeerProtocolError` 하위) + `_raise_connection_limit_if_that` 신설 —
    거부를 "응답 편호 19204(기대 11004)" 라는 오해 대신 원인으로 표시한다.
  - `api.py` — `allow_exclusive` → `allow_guarded`. `API_PARAM = 1400`, `get_param`,
    **`get_max_connections(port)`** 신설 — 한도를 상수로 신뢰하지 않고 로봇에 묻는다(19204 로 나가므로
    게이트에 안 걸린다).
  - `mutation_check.py` — 앵커 갱신 + 신규 6건(`P4`·`P5`·`A13`·`A14`·`T13`·`T14`), 총 **33건**.
- **검증**: **50 passed** · 돌연변이 **33/33 검출** · `flake8` 0 · colcon 2패키지 ·
  실기 API 1400 6건 조회 정상. 조회기 `Tools/seer_re/seer_param.sh` 신설(실기·원본 하드 동시 조회,
  두 경로 5/5 일치 확인).
- **하네스 결함 1건 추가 발견**: 새로 넣은 `P2` 돌연변이가 무력이었다 —
  `frozenset(파생) or frozenset({리터럴})` 은 파생이 비면 falsy 라 `or` 가 원본으로 되돌아가
  **아무것도 변조하지 않는다.** 「미검출」을 보고 시험을 의심했으나 범인은 돌연변이였다.
  블록 통째 치환으로 고치고 "미검출이면 시험보다 돌연변이를 먼저 의심한다"를 주석으로 박았다.
- **잔여(⚠)**: 지령 포트 쓰기 API 6종(`stop`·`open_loop_move`·`relocate`·`go_target`·`set_do`·
  `download_map`)은 **실기 미호출** — 단위 시험(가짜 소켓)만 통과. broker 미착수(**debt-072**),
  HAL 메시지 계약 미확정(**debt-073**).
  경위 기록: [docs/claude-mistake/2026-08-07-002](../../../../docs/claude-mistake/2026-08-07-002_vendor-question-drafted-while-holding-the-source.md).

## 2026-08-07 / (pending commit) — 패키지 신설: Seer TCP/IP API 클라이언트 3층

- **증상**: Seer Robokit NetProtocol 16B 헤더가 저장소 안에서 **2곳에 각자 재구현**돼 있었다
  (`seer_read_lidar_install.py`, `seer_lidar_tf_node.py`). 둘 다 seq 고정·응답 seq 미대조·
  요청 간격 무제한. 새 소비자가 생길 때마다 세 번째·네 번째 구현이 늘어날 구조였다.
- **진단**: 전송을 단일 지점으로 모으되, **HAL 경계는 이 라이브러리가 아니라 ROS 인터페이스**에
  둔다 — 상위 알고리즘 패키지가 `seer_api` 를 직접 import 하면 Seer 를 우리 MCL/nav 로 교체할 때
  상위 코드를 전부 고쳐야 한다. 배치는 `Comm/CAN/can_relay` 와 대칭(`Comm/<전송>/<상대방>`).
- **조치**: `src/Comm/TCP_IP/seer_api/` 신설(ament_python, **rclpy 무의존**).
  - `transport.py` — 16B 헤더 pack/unpack, seq 순환·응답 seq 대조, `recv_exact`(부분 수신),
    실패 시 소켓 정리, 최소 요청 간격(≥100ms).
  - `ports.py` — 포트 상수 + 정책.
  - `api.py` — 편호 바인딩(1000/1004/1005/1007/1009/1013/1050/1100/1300/2000/2002/2010/3051/4011/6001).
  - `test/` 2파일 + `mutation_check.py`(검출력 검사).
- **검증**: 공식 SDK `packMsg` 와 **바이트 동일**(원본 `rbkNetProtoEnums.py` 를 직접 로드해 대조,
  본문 유/무 양쪽). 실기 조회 1000/1004/1009/1300 정상(`Foil_A082 v3.4.5.22`).
- **하네스 결함 2건 발견**: ① `__pycache__` 오염으로 27/27 을 잘못 보고 —
  `.pyc` 유효성이 (mtime 초, 파일크기) 판정이라 같은 초·같은 크기 변조가 직전 바이트코드를
  재사용했다. `python -B` + `PYTHONDONTWRITEBYTECODE` + 캐시 삭제로 닫았다.
  ② 그러자 드러난 `A5` 미검출의 원인은 **기대값에 상수 자신을 쓴 시험** — 편호·포트를
  리터럴로 고정하는 시험을 추가해 닫았다.
