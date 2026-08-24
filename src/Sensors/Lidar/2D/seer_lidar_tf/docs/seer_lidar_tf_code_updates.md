# seer_lidar_tf Code Updates

> 본 파일은 이 패키지 + 같은 디렉토리의 형제 자산 2개(`../seer_read_lidar_install.py`,
> `../seer_lidar_tf_launch.py`)의 수정 이력을 함께 담는다 — 셋이 한 작업 단위로 움직인다.
> 인벤토리(함수표·전역변수표): [docs/code_review/seer-lidar-tf/2026-08-10.md](code_review/seer-lidar-tf/2026-08-10.md)

## 2026-08-23 / (pending commit) — ament_python → ament_cmake, 노드 C++ 재작성

- **왜**: `seer_tcp_ip` 가 C++ 라이브러리가 되면서 rclpy 노드가 그것을 import 할 수 없다.
  저장소 언어 표준(README `언어 표준:`)도 ROS2 패키지는 C++ 다.
  ADR `docs/adr/2026-08-18-seer-tcp-ip-cpp-rewrite.md` §Decision 3.
- **조치**: `seer_lidar_tf/seer_lidar_tf_node.py`(207줄) → `src/seer_lidar_tf_node.cpp`(278줄).
  `setup.py`·`setup.cfg`·`resource/` 제거, `CMakeLists.txt` 신설, `package.xml` 을 ament_cmake 로.
  런치 파일은 그대로 — 실행파일 이름(`seer_lidar_tf_node`)과 파라미터 9개를 유지했다.
- **동작 유지 확인**: 두 모드(publish latch/폴링, calibration write) 그대로. 실기에서 Python 판과
  **같은 install_info 값**으로 `base_footprint -> [scan_front, scan_rear]` TF 발행.
- **부수 확인**: `seer_port` 에 지령 포트(19205)를 넣으면 `seer_tcp_ip` 게이트가 막는 것을
  실기에서 확인했다 — 게이트가 라이브러리 안에서 끝나지 않고 노드 단에서 작동한다.
- **잔여(⚠)**: 이 노드는 조회(19204)만 쓴다. 지령 포트 API 의 실기 검증은 debt-111 소관.

## 2026-08-10 / (pending commit) — 게이트 개명에 따른 주석 정정 + 함수표 신설

- **증상**: `seer_lidar_tf_node.py` 의 클라이언트 생성부 주석이 `allow_exclusive` 를 언급 —
  `seer_api` 쪽 게이트가 `allow_guarded` 로 개명되면서 **사실과 어긋난 이름**이 되었다.
  코드는 기본값을 쓰므로 동작에는 영향이 없으나, 주석이 존재하지 않는 인자를 가리켰다.
- **진단**: 개명 근거는 실측 반증(동시연결 1 → 실제 5, 거부형) —
  [ADR 2026-08-07-seer-api-tcp-hal](../../../../../../docs/adr/2026-08-07-seer-api-tcp-hal.md) §Decision 3.
  이 파일은 그 개명의 하류인데 함께 갱신되지 않았다.
- **조치**:
  - 주석을 현재 사실로 교정 — "지령 포트를 쓸 일이 없으므로 `allow_guarded` 기본값(False) 유지 /
    `seer_port` 에 지령 포트를 넣으면 seer_api 게이트가 막는다(의도된 동작)".
  - **함수표·전역변수표 신설** — 이 3파일은 표가 없어 `coding-inventory-gate.py` 의
    「표 없으면 통과」 기본값(coding.md:53, **debt-042**)으로 최초 작성부터 무검사였다.
    루트 정본 `docs/code_review/seer-lidar-tf/2026-08-10.md` + 패키지 병기 이중 기록.
- **검증**: 표의 `파일:줄` 앵커를 스크립트로 소스와 대조 — 함수표 9건·인스턴스 상태 5건 **불일치 0**.
  `flake8` 0건, `colcon build --packages-select seer_api seer_lidar_tf` 성공,
  실기(192.168.44.82) 재구동 → `TF 발행 완료: base_footprint -> [scan_front, scan_rear]`.
- **잔여(⚠)**: 표에 기록한 구조 위험 2건은 **이번에 고치지 않았다** —
  ① `_broadcaster`·`_timer` 가 write 모드에는 존재하지 않는다(`__init__` 조기 반환).
     현재 호출 경로가 없어 무해하나 두 모드를 한 클래스가 겸하는 구조가 원인.
  ② `install_info` 사본이 3벌(launch 상수 · merger YAML · 런타임 TF)이라 재캘리브 시 어긋날 수 있다.

## 2026-08-07 / (pending commit) — Seer TCP 프로토콜 자체 구현 제거, seer_api 로 이관

- **증상**: 16B 헤더(0x5A + JSON)가 저장소 안에서 **각자 재구현**돼 있었다 —
  이 노드(`_SYNC`/`_HDR`/`_recv_n` 자체 보유)와 `../seer_read_lidar_install.py`.
  두 구현 모두 **seq 를 1 로 고정**하고 응답 seq 를 대조하지 않았으며 요청 간격 제한이 없었다.
  `seer_read_lidar_install.py` 는 부분 수신 시 `break` 로 빠져나가 짧은 버퍼를 `struct.unpack` 에 넣었다.
- **진단**: 프로토콜 구현 지점이 늘어나는 것이 관측된 사실이므로 단일 지점으로 모은다 —
  [ADR 2026-08-07-seer-api-tcp-hal](../../../../../../docs/adr/2026-08-07-seer-api-tcp-hal.md).
  HAL 경계는 이 라이브러리가 아니라 ROS 인터페이스에 둔다(상위는 `seer_api` 를 import 하지 않는다).
- **조치**:
  - `seer_lidar_tf_node.py` — `socket`/`struct`/`json` import 와 `_SYNC`·`_VERSION`·`_HDR`·
    `_API_LASER_*` 상수, `_query_lasers` 의 소켓 코드, `_recv_n` 정적 메서드 **삭제**.
    `SeerApi` 를 lazy 로 보유하고 `_query_lasers` 는 `self._client.call(self.seer_port, API_LASER)` 한 줄.
    `main` 의 `finally` 에 `_client.close()` 추가(소켓 누수 방지).
  - `../seer_read_lidar_install.py` — 자체 `query()` 삭제, `SeerApi.get_lasers()` 사용.
    패키지 밖 단독 스크립트라 미소싱 환경용 소스 트리 경로 fallback 을 둔다.
  - `package.xml` — `<exec_depend>seer_api</exec_depend>` 추가.
  - **ROS 파라미터·출력 형식은 바꾸지 않았다** — `seer_port` 를 그대로 존중해
    `call(self.seer_port, …)` 로 넘긴다(launch 파일이 19204 를 명시하고 있다).
- **검증**:
  - 이관 등가성 — `seer_read_lidar_install.py` 출력이 이전 리비전(`git show HEAD:…`)과 **바이트 동일**(`diff` 무차이).
  - 실기 — 노드 재구동 시 `FrontLiDAR x=0.8809 y=-0.5783 yaw=-45.573°` /
    `RearLiDAR x=-0.8564 y=0.6067 yaw=135.093°`, TF 발행 정상.
  - 실패경로 — 도달불가 IP(`192.168.44.199`)로 기동 → `Seer 조회 실패(timed out) — 2.0s 후 재시도`
    반복, 크래시·소켓 누수 없음.
- **얻은 것(공짜)**: seq 순환 · 응답 seq/편호 대조 · 부분 수신 정확 처리 · 요청 간격 제한(≥100ms) ·
  한도 초과 거부의 전용 예외. 이관 전 두 구현에는 하나도 없었다.
- **잔여(⚠)**: 이 노드는 조회(19204)만 쓴다. `seer_api` 의 지령 포트 API 는 실기 미검증(debt-072).
