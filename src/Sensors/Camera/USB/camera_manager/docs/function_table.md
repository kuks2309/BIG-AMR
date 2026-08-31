# camera_manager — 함수표 · 전역변수표 (모듈 권위본)

> 대상: `src/Sensors/Camera/USB/camera_manager/` (카메라 관리 모드 — 감시·자동 복구·CLI).
> 설계 근거: [ADR 2026-08-30 카메라 관리 모드](../../../../../docs/adr/2026-08-30-camera-management-mode.md)

## 함수표 — monitor.py (ROS 무의존 순수 상태기계)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `MonitorConfig` | `@dataclass(frozen=True) MonitorConfig(stall_sec, restart_cooldown_sec, startup_grace_sec)` | 감시 임계 3종 묶음(기본 10/30/20초) | monitor.py:31-42 |
| `CameraInputs` | `@dataclass(frozen=True) CameraInputs(frame_age, unit_active, device_present, depth_active)` | 카메라 1대의 1틱 관측 입력(프레임 나이·유닛 활성·장치 실재·depth 경로 활성) | monitor.py:45-58 |
| `Decision` | `@dataclass(frozen=True) Decision(state, restart, reason)` | 1틱 판정 출력 — 상태 라벨 + 재시작 지시 여부 + 사유 | monitor.py:61-66 |
| `CameraMonitor.__init__` | `__init__(name: str, config: MonitorConfig, now: float)` | 카메라 1대 감시자 생성(기동 유예 기준시각 기록) | monitor.py:72-78 |
| `CameraMonitor.note_external_restart` | `note_external_restart(now: float)` | 외부(CLI 등) 재시작 통보 — 기동 유예를 다시 열어 겹침 재시작 방지 | monitor.py:80-86 |
| `CameraMonitor.evaluate` | `evaluate(inputs: CameraInputs, now: float, auto_enabled: bool) -> Decision` | 억제 3조건(depth 활성·장치 부재·의도적 정지) → 신선 판정 → stall 시 유예/쿨다운 검사 후 재시작 지시. 내부 상태(마지막 재시작 시각·연속 재시작 수) 갱신 | monitor.py:88-131 |

## 함수표 — roster.py (로스터 로더, ROS 무의존)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `Camera` | `@dataclass(frozen=True) Camera(name, serial, device)` | 로스터 1행(논리 이름·시리얼·by-id 장치 경로) | roster.py:21-26 |
| `device_path` | `device_path(by_id_prefix: str, serial: str) -> str` | 시리얼 → by-id 심링크 경로(`/dev/videoN` 은 재부팅마다 바뀌므로 금지) | roster.py:29-31 |
| `find_shared_config` | `find_shared_config(start: str \| None = None) -> str \| None` | 공용 설정 탐색 — `CAMERA_CONFIG` 환경변수 → 상위 10단계 `config/camera/camera_common.yaml` (launch 파일과 동일 규칙) | roster.py:34-52 |
| `load_roster` | `load_roster(config_path: str) -> list[Camera]` | 공용 yaml 파싱 → Camera 목록(`by_id_prefix`·`cameras` 필수 키 검증) | roster.py:55-75 |

## 함수표 — systemd_ctl.py (systemctl 래퍼, ROS 무의존)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `unit_name` | `unit_name(cam: str) -> str` | 논리 이름 → `usb-cam@<cam>.service` | systemd_ctl.py:22-24 |
| `SystemdControl.__init__` | `__init__(runner=subprocess.run)` | 실행기 주입(테스트에서 가짜 runner 사용) | systemd_ctl.py:30-31 |
| `SystemdControl.is_active` | `is_active(cam: str) -> bool \| None` | `systemctl is-active` — active→True / inactive·failed·activating→False / 실행 실패→None(판정 불가) | systemd_ctl.py:33-50 |
| `SystemdControl.control` | `control(verb: str, cam: str) -> tuple[bool, str]` | `sudo -n systemctl start\|stop\|restart` — sudoers 미설치 시 (False, 설치 안내) | systemd_ctl.py:52-67 |

## 함수표 — manager_node.py (rclpy 상주 노드)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `CameraManagerNode.__init__` | `__init__()` | 파라미터 선언 → 로스터 로드 → 카메라별 압축 토픽 구독(sensor QoS) + `/diagnostics` 발행 + `~/set_auto` 서비스 + 판정 타이머 + systemd 워커 스레드 기동 | manager_node.py:62-113 |
| `CameraManagerNode._make_frame_callback` | `_make_frame_callback(cam_name: str)` | 구독 콜백 팩토리 — 도착 단조시각만 기록(페이로드 미사용·미디코드) | manager_node.py:115-121 |
| `CameraManagerNode._on_tick` | `_on_tick()` | 1틱: 카메라별 입력 조립(나이·캐시된 유닛 상태·장치 실재·depth 퍼블리셔 수) → `CameraMonitor.evaluate` → 재시작은 큐로 워커에 위임(콜백 내 blocking 금지) → diagnostics 발행 | manager_node.py:123-145 |
| `CameraManagerNode._on_set_auto` | `_on_set_auto(request, response)` | `std_srvs/SetBool` — 자동 재시작 켜기/끄기 | manager_node.py:147-153 |
| `CameraManagerNode._systemd_worker` | `_systemd_worker()` | 전용 스레드 — 재시작 큐 소진 + 유닛 활성 상태 주기 갱신(subprocess 는 전부 여기서만) | manager_node.py:155-176 |
| `CameraManagerNode._publish_diagnostics` | `_publish_diagnostics(decisions)` | 카메라별 Decision → DiagnosticArray(레벨: ok/suppressed→OK, restarting/stopped/unknown→WARN, stall/no_device→ERROR) | manager_node.py:178-194 |
| `CameraManagerNode.shutdown` | `shutdown()` | 워커 스레드 정리(main 의 finally 에서 호출) | manager_node.py:196-200 |
| `main` | `main(argv=None)` | rclpy 초기화·스핀·정리 | manager_node.py:203-214 |

## 함수표 — cli.py (`camctl` 콘솔 도구)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| (내부) `_load_cameras` | `_load_cameras(args) -> list[Camera]` | --config/CAMERA_CONFIG/자동 탐색으로 로스터 로드 | cli.py:25-31 |
| (내부) `_select` | `_select(cameras, target: str) -> list[Camera]` | 이름 1개 또는 all 선택(미등재 이름 거부) | cli.py:34-41 |
| (내부) `_measure_frames` | `_measure_frames(cameras, window_sec)` | 임시 노드로 window 초 구독 — 카메라별 수신 수 + depth 퍼블리셔 존재 | cli.py:44-76 |
| `cmd_status` | `cmd_status(args) -> int` | 로스터 순회 표 출력 — 장치 실재·유닛 상태·프레임 수신율·depth 점유 | cli.py:79-103 |
| `cmd_control` | `cmd_control(args) -> int` | `start\|stop\|restart <cam>\|all` — sudo -n systemctl, 실패 시 sudoers 설치 안내 | cli.py:106-115 |
| `cmd_auto` | `cmd_auto(args) -> int` | `auto on\|off` — 관리자 노드 `set_auto` 서비스 호출(타임아웃 시 미기동 안내) | cli.py:118-143 |
| `main` | `main(argv=None) -> int` | argparse 서브커맨드 라우팅 | cli.py:146-169 |

## 패키징 파일

| 파일 | 용도 | 위치 |
| --- | --- | --- |
| `setup.py` | ament_python 패키징. 진입점 2개 — `manager_node = camera_manager.manager_node:main`, `camctl = camera_manager.cli:main`. data_files 는 리소스 인덱스·package.xml 뿐 | setup.py:1-27 |
| `__init__.py` | 빈 파일 — 파이썬 패키지 표식뿐, re-export 없음 | __init__.py:1 |
| `setup.cfg` | 스크립트 설치 경로(`lib/camera_manager`) | setup.cfg:1-4 |
| `package.xml` | format 3, ament_python. 의존: rclpy·sensor_msgs·diagnostic_msgs·std_srvs·python3-yaml | package.xml:1-26 |

## 테스트 표

| 파일 | 용도 | 위치 |
| --- | --- | --- |
| `test_monitor.py` | CameraMonitor 상태 전이 14케이스 — 신선/유예/재시작/쿨다운/복구 리셋/억제 3조건/자동 꺼짐/외부 재시작 통보/신선 우선/경계값 | test_monitor.py:1-126 |
| `test_roster.py` | 로스터 로더 — 정상 파싱·필수 키 누락·행 형식 오류·by-id 경로 형식·CAMERA_CONFIG 환경변수 우선·상향 탐색 | test_roster.py:1-62 |
| `test_systemd_ctl.py` | systemctl 래퍼(가짜 runner 주입) — is_active 3분기·control 성공/암호거부 안내/허용외 동사 | test_systemd_ctl.py:1-60 |
| `conftest.py` | 패키지 루트를 sys.path 에 추가 — 저장소 어느 위치에서 pytest 를 불러도 import 가능하게 | conftest.py:1 |

## 전역변수표

| 이름 | 타입 | 용도 | 위치 |
| --- | --- | --- | --- |
| `STATE_OK` 외 상태 상수 7종 | `str` | 상태 라벨(`ok`·`stall`·`restarting`·`no_device`·`stopped`·`suppressed`·`unknown`) — Decision.state 의 정의역 | monitor.py:21-27 |
| `_LEVEL_BY_STATE` | `dict[str, bytes]` | 상태 → diagnostics 레벨 매핑(억제는 의도된 상태라 OK) | manager_node.py:49-56 |
| `_DEFAULT_WALK_UP` | `int` | 공용 설정 상향 탐색 최대 깊이(10, launch 파일과 동일) | roster.py:17 |
| `_SUDO_HINT` | `str` | sudoers 미설치 시 안내문(설치 명령 포함) | systemd_ctl.py:17-19 |
| `_MEASURE_SEC_DEFAULT` | `float` | camctl status 프레임 측정 창 기본값(2초) | cli.py:22 |

## 토픽·서비스 표

| 토픽/서비스 | 타입 | QoS | 방향 | 위치 |
| --- | --- | --- | --- | --- |
| `<cam>/image_raw/compressed` | `sensor_msgs/CompressedImage` | sensor_data(best-effort) | 구독 ×6 | manager_node.py:99-104 |
| `<cam>/depth/image_raw` | — (count_publishers 만) | — | 그래프 조회 | manager_node.py:135 |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | reliable·keep-last 10·volatile | 발행 1Hz | manager_node.py:106-111 |
| `/camera_manager/set_auto` | `std_srvs/SetBool` | 서비스 기본 | 서버 | manager_node.py:112 |
