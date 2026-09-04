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
