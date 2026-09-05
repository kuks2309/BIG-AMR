# docking_field_kit — 함수표 (모듈 권위본)

> 대상: `Tools/docking_field_kit/` — Orin 현장 킷(판다 직결 실험 스크립트). 표는 2026-09-04 부터
> 신규·수정 파일만 등재한다(기존 스크립트는 미등재 — 손댈 때 등재).

## 함수표 — orin_cycle_capture.py (1사이클 take→release 양 버스 전체 캡처, debt-129/130 검증)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `steer` | `steer() -> list[float] \| None` | Seer API `get_speed().steer_angles`(rad) 판독, 실패 시 None | orin_cycle_capture.py:9 |
| `alarms` | `alarms() -> list[tuple]` | Seer `get_alarms()` 의 fatals/errors/warnings 를 (등급, code, desc 꼬리) 튜플로 평탄화 | orin_cycle_capture.py:12 |
| `cap` | `cap(dur: float, phase: str) -> dict` | `dur` 초 동안 판다 `can_recv()`(bus 필터 없음, 2 ms 폴)를 jsonl 로 기록하고 bus 별 프레임 수 반환 | orin_cycle_capture.py:25 |

## 전역변수표 — orin_cycle_capture.py

| 이름 | 값/형 | 용도 | 위치 |
| --- | --- | --- | --- |
| `seer` | `SeerApi` | 192.168.44.82 TCP API 핸들 | orin_cycle_capture.py:8 |
| `LOG` | str | 전체 캡처 jsonl 경로 `Log/e1_all_<stamp>.jsonl` | orin_cycle_capture.py:21 |
| `rig` | `Rig` | `orin_home_experiment.Rig` — take/release/heartbeat·bus2 로그 | orin_cycle_capture.py:22 |
| `p` | `Panda` | `rig.p` 판다 핸들 | orin_cycle_capture.py:23 |
| `T0` | float | 캡처 상대시각 기준(epoch) | orin_cycle_capture.py:23 |

## 함수표 — orin_ros_stall_test.py (ROS 실행기 정체 주입 실기 검증 — 심박 중단 시 조향 재송신 0·펌웨어 fail-safe 복원)

| 함수 | 시그니처 | 용도 | 위치 |
|---|---|---|---|
| `seer_probe` | `seer_probe() -> dict` | Seer API `get_speed().steer_angles`(rad)·`get_alarms()` 코드 목록, 실패 시 `error` | orin_ros_stall_test.py:37 |
| `fw_status` | `fw_status(link) -> dict` | 링크 락 아래 판다 `health().safety_mode` + USB 0xec 6바이트(핸드오버 state·source·result·pending·ticks·pc_authority) | orin_ros_stall_test.py:53 |
| `main` | `main() -> None` | 실노드 spin(도메인 126) → engage → 홈 확인 → 조향 +5° → spin 중단(정체) → 백엔드·펌웨어·Seer 판정 → 반환·JSON 저장 | orin_ros_stall_test.py:62 |
| `spin` (내부) | `spin() -> None` | `alive` 가 서 있는 동안만 `spin_once` — 내리면 실행기가 선다(정체 주입점) | orin_ros_stall_test.py:70 |
| `counting_send` (내부) | `counting_send(frames)` | `backend._send` 래퍼 — 0x607A(index 바이트 0x7A 0x60) 프레임 수를 센 뒤 원함수 호출 | orin_ros_stall_test.py:80 |
| `log` (내부) | `log(step, **kw)` | 단계 기록을 stdout JSON 1줄 + `rec.steps` 에 적재 | orin_ros_stall_test.py:92 |

## 전역변수표 — orin_ros_stall_test.py

| 이름 | 타입 | 용도 | 위치 |
|---|---|---|---|
| `DEPLOY` | str | 배포 워크트리 루트(판다 파이썬·설정 yaml 출처) | orin_ros_stall_test.py:19 |
| `CFG`·`MACHINE` | str | 노드 파라미터 yaml 2종(배포 사본, 구동 상한 포함) | orin_ros_stall_test.py:30-31 |
| `STEER_DEG` | float | 정체 전 넣는 조향 목표(+5°) | orin_ros_stall_test.py:32 |

## 함수표 — orin_supervisor_e2e.py (배포 감시자 복귀 E2E — 드라이버 사망 복귀·감시자 동반 재기동 pid 추론·수동 해제 비복귀)

| 함수 | 시그니처 | 용도 | 위치 |
|---|---|---|---|
| `Observer.__init__` | `Observer()` | rclpy 노드(도메인 125) — `/diagnostics` 구독으로 드라이버(`can_relay:`)·감시자(`can_relay_supervisor`) 최신 상태·수신 시각 보관, `/can_relay_node/engage` 클라이언트 | orin_supervisor_e2e.py:38 |
| `Observer._spin` | `_spin() -> None` | `rclpy.ok()` 동안 `spin_once` — shutdown 뒤 스레드가 자연 종료돼 종료 시 abort 가 없다 | orin_supervisor_e2e.py:48 |
| `Observer._on_diag` | `_on_diag(msg)` | 상태 이름 접두로 드라이버/감시자 KeyValue 를 dict 로 갱신 | orin_supervisor_e2e.py:52 |
| `Observer.engage` | `engage(on: bool) -> tuple[bool, str]` | `~/engage` 동기 호출(10 s) | orin_supervisor_e2e.py:63 |
| `Observer.wait_for` | `wait_for(pred, timeout) -> bool` | 0.2 s 폴로 조건 대기(`while` 재확인) | orin_supervisor_e2e.py:71 |
| `main_pid` | `main_pid(unit) -> int` | `systemctl show -p MainPID` | orin_supervisor_e2e.py:79 |
| `kill_driver_node` | `kill_driver_node(ob) -> dict` | 진단 `pid` 의 드라이버 노드 프로세스에 SIGKILL(크래시 재현, launch 종료→systemd 재기동) | orin_supervisor_e2e.py:85 |
| `kill_sup_node` | `kill_sup_node() -> dict` | `pgrep -f lib/can_relay/relay_supervisor` 로 감시자 노드 프로세스에 SIGKILL | orin_supervisor_e2e.py:93 |
| `journal_since` | `journal_since(unit, since) -> list[str]` | 감시자 저널에서 판정 전이·복귀 지시·pid 추론 줄만 추출 | orin_supervisor_e2e.py:90 |
| `seer_probe` | `seer_probe() -> dict` | Seer API 알람 코드 목록(52111 확인) | orin_supervisor_e2e.py:99 |
| `path_a` | `path_a(ob) -> dict` | engage→RUNNING→드라이버 kill→(WAIT/DEAD)→RESTORE→새 pid 로 engaged→RUNNING→수동 해제→IDLE 유지 | orin_supervisor_e2e.py:110 |
| `path_b` | `path_b(ob) -> dict` | engage→RUNNING→드라이버·감시자 동시 kill→새 감시자 pid 추론 warn→RESTORE→engaged→해제 | orin_supervisor_e2e.py:141 |
| `path_c` | `path_c(ob) -> dict` | engage→감시자만 kill→RUNNING(복귀 호출 0)→해제→감시자만 kill→IDLE 유지(비복귀) | orin_supervisor_e2e.py:170 |
| `main` | `main() -> None` | 인자(A/B/C)로 고른 경로를 순차 실행(무인자=전부), 판정 표 출력, JSON 저장(부분 실행은 `_<경로>` 접미) | orin_supervisor_e2e.py:213 |

## 전역변수표 — orin_supervisor_e2e.py

| 이름 | 타입 | 용도 | 위치 |
|---|---|---|---|
| `DRV`·`SUP` | str | systemd 유닛 이름 2종 | orin_supervisor_e2e.py:30-31 |
| `OUT` | str | 결과 JSON 경로 `logs/orin_supervisor_e2e.json` | orin_supervisor_e2e.py:32 |

## 토픽·서비스표 — orin_supervisor_e2e.py

| 토픽/서비스 | 타입 | QoS | 위치 |
|---|---|---|---|
| `/diagnostics` (구독) | `diagnostic_msgs/DiagnosticArray` | 기본(RELIABLE·VOLATILE, depth 10) — 드라이버 `pub_diag` 와 동일 | orin_supervisor_e2e.py:42 |
| `/relay_supervisor/status` (구독) | `diagnostic_msgs/DiagnosticArray` | 기본(RELIABLE·VOLATILE, depth 10) — 감시자 `pub_status` 와 동일 | orin_supervisor_e2e.py:43 |
| `/can_relay_node/engage` (클라이언트) | `std_srvs/SetBool` | 서비스 기본 | orin_supervisor_e2e.py:44 |
