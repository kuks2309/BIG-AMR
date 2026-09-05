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
