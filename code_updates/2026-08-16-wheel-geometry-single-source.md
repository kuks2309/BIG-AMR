# 휠 기하를 config 단일 출처에서 읽도록

## 범위

Seer 오도 분석·이식 범위에 해당하는 **`motor_control/config/tongyi_amr.yaml` 정합만** 이 브랜치에 있다.
시뮬 구현(`trnav_2ws_gazebo`·`translate_sim_odom`)은 `session/5466b21a-simgeom` 으로 분리했다 —
Gazebo·SIL 인프라는 이 세션 목적 밖이다.

## 무엇을

오도메트리 경로가 쓰는 휠 기하를 정본 `trnav_2ws_core/config/robot_geometry_2ws.yaml`
하나로 수렴시키고, 현재 구조(inline dual-steer, 센터라인 y=0, 휠베이스 1.200 m)에 맞췄다.

| 파일 | 변경 |
| --- | --- |
| `trnav_2ws_gazebo/scripts/wheel_odometry.py` | 기하 기본값 제거 → 미주입 시 기동 실패. 두 바퀴가 겹치는 특이 기하도 기동 실패 |
| `trnav_2ws_gazebo/launch/sim.launch.py` | 정본 YAML 을 `wheel_cmd_bridge`·`wheel_odometry` 에 주입 |
| `trnav_2ws_gazebo/launch/fleet.launch.py` | 정본 YAML 을 `wheel_odometry` 에 주입 |
| `motor_control/config/tongyi_amr.yaml` | `module_y` `[-0.0014, -0.0014]` → `[0.0, 0.0]` (정본 정합) |
| `trnav_2ws_gazebo/test/test_wheel_geometry.py` | 신규 — 정본 ↔ 수식 회귀 |

## 왜

정본 파일은 이미 있었고 스스로 "정본" 이라 선언하는데 **그 파일을 로드하는 노드가 하나도 없었다.**
소비자들이 값을 베껴 코드 기본값으로 박아 두어 네 곳의 값이 갈려 있었다 —
`wheel_odometry.py`·`wheel_cmd_bridge.py`·`tongyi_amr.yaml` 은 `y=−0.0014`,
정본과 `translate_sim_odom` 은 `y=0.0`. inline 구조에서 y 잔차는 회전중심을 횡으로 밀어
제자리 스핀을 ±89.867° 로 만든다.

## 설계 선택

- **새 config 파일을 만들지 않았다.** 네 번째 사본을 만드는 것이 지금 문제의 원인이다.
  정본은 이미 `/**:` 와일드카드라 노드 이름과 무관하게 주입된다.
- **코드에 기하 기본값을 두지 않는다.** '그럴듯한' 기본값은 정본이 갱신돼도 그 노드만 옛 값으로
  조용히 돌게 만든다. 미주입은 기동 실패로 처리한다 — 뜨지 않는 편이 낫다.
- **CAN 노드 매핑(`module_x` 의 전·후 배정)은 건드리지 않았다** — 미판정이다(registry 「미등록 사항」).
  이번 변경은 좌표값을 정본에 맞출 뿐이다.
- **QD 스택은 손대지 않았다** — LGIT 검증 후 재이식 예정이라 범위 밖.

## 검증

- 새 회귀 `test_wheel_geometry.py`: 정본 로드 → 설계행렬 → 직진·제자리 스핀·크랩·차동 조향에서
  차체 트위스트 복원 확인. `det(AᵀA) = 2·d²` 항등도 확인.
- 돌연변이 5건 전부 검출(y 잔차 되살리기 · 전후 반전 · 휠베이스 변경 · 두 바퀴 겹침 · 반지름 부호),
  원복 시 0.
- `trnav_2ws_core` 빌드 후 `share/trnav_2ws_core/config/robot_geometry_2ws.yaml` 설치 확인 —
  런치의 `FindPackageShare` 주입이 성립한다.
- 런치 3개 문법 확인(`ast.parse`), YAML 2개 파싱 확인.

## 검증하지 못한 것

`trnav_2ws_gazebo` 실빌드는 **선행 결함으로 막혔다** — 의존 패키지 `trnav_2ws_description` 이
없는 `launch/` 를 설치하려다 CMake 에서 죽는다(debt-091, 이번 작업과 무관).
따라서 런치 수정은 정적 확인까지이고 **실기동 확인은 못 했다.**

## 남긴 것

- **debt-090** — 휠 기하 사본이 둘 남았다(`sim_params.yaml` 자체 보유 · `wheel_cmd_bridge.py` 기본값).
- **debt-091** — `trnav_2ws_description` 빌드 불가(선행 결함).
