# can_relay — 판다 릴레이 경유 모터 구동 ROS2 드라이버

> ⚠ **이름 주의.** 이 패키지는 `Tools/Can_Relay/` 의 **판다 펌웨어 프로젝트가 아니다.**
> 저장소에서 `can_relay` 는 지금까지 그 펌웨어를 뜻해 왔다(`docs/can_relay/`,
> `docs/code_review/can_relay_firmware/`, `README.md:1` "CATL-Ford CAN-Relay").
> 이쪽은 그 릴레이를 **호스트에서 사용하는** rclpy 드라이버다.
> 문서·주석에서 인용할 때 어느 쪽인지 반드시 병기할 것 — debt-015.

## 무엇을 하는가

comma.ai panda 기반 CAN 릴레이를 경유해 Tongyi 4축 서보(구동 node1·2 / 조향 node3·4)를 구동한다.
Seer 마스터가 붙어 있는 상태에서 릴레이 intercept 로 주도권을 가져와 지령을 덮어쓴다.

## `src/Actuators/motor_control` 과 무엇이 다른가

| | `motor_control` | 이 패키지 |
| --- | --- | --- |
| 물리 경로 | socketcan `can1` 직결 | USB → panda → bus 2 |
| Seer | **분리 필수** | **연결 필수** |
| 정지 근간 | guard RTR 20 Hz 중단 → 500 ms HALT | heartbeat 상실 → 펌웨어가 구동 0 + 릴레이 개방 |
| RTR 송신 | 가능(필수) | **불가** — 판다 패킷 헤더에 RTR 비트가 없다 |

두 안전 모델은 **배타적**이다. 한쪽 전제가 다른 쪽 실패조건이므로 합칠 수 없다.
**두 패키지를 동시에 띄우지 말 것** — 이를 막는 기계 장치는 아직 없다(debt-018).

## 쓰는 법

```bash
colcon build --packages-select can_relay --symlink-install && source install/setup.bash

# 하드웨어 없이 (기본 검증용)
ros2 launch can_relay can_relay.launch.py link:=mock

# 실기 — 기동만으로는 아무것도 움직이지 않는다. 제어권은 명시 호출로만 잡는다.
ros2 launch can_relay can_relay.launch.py
ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"

ros2 topic pub --once /can_relay_node/steer_deg std_msgs/Float64 "{data: 45.0}"
ros2 topic pub --once /can_relay_node/drive_mmps std_msgs/Float64 "{data: 50.0}"
ros2 service call /can_relay_node/stop std_srvs/srv/Trigger

ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: false}"
```

`~/drive_mmps` 는 워치독(`cmd_timeout_s`, 기본 0.3 s)이 걸려 있다 — 한 번 쏘고 두면
0.3 초 뒤 자동으로 0 이 된다. 계속 주행하려면 주기 발행이 필요하다. 이것은 결함이 아니라 설계다.

## 안전 규칙 (코드가 강제한다 — 회귀 84건이 고정)

| 규칙 | 강제 지점 |
| --- | --- |
| 비유한(NaN/inf) 지령 **거부**, 워치독도 갱신 안 함 | `safety.finite()` |
| 조향 **±90° 클램프**를 counts 생성 지점에 | `safety.steer_deg_to_counts()` |
| 구동 지령 **주기 재송신**, 만료 시 0 | `backend._loop` |
| 정지는 **어떤 상태에서도 수용** | `backend.stop()` |
| heartbeat 유지 = 펌웨어 fail-safe 무장 | `link.acquire()` + 제어 루프 |
| 호밍 중(bit15=0) **위치 사용 금지** | `safety.position_trustworthy()` |
| 호밍 완료는 **0→1 전이**로만 판정 | `safety.HomingJudge` |
| 피드백 만료 시 각도 `None`(0 으로 채우지 않음) | `backend.steer_angles_deg()` |
| 브링업·호밍·제어권은 **명시 요청 전용** | `allow_bringup=false`, `~/home`, `~/engage` |

## 주요 상수의 근거

| 상수 | 값 | 근거 |
| --- | --- | --- |
| `COUNTS_PER_DEG` | 57344 | 16384×4×315/360. 실측 홈↔90° Δ = +5,160,960 = 정확히 90.00° |
| `STEER_LIMIT_DEG` | 90.0 | **실측 검증 범위**. 기구 한계(±140°)는 다른 기체 config 값이라 쓰지 않는다 |
| `VEL_MAX_UNITS` | 4889 | ≈0.2 m/s. ⚠ 실측이 아니라 config 환산 + 계승된 안전 상한 |
| `steer_home_counts` | 7871815 / 7840086 | ⚠ **debt-007/016 미판정.** 실측 캡처의 호밍 후 정착 목표는 7882020 / 7859062 로 +0.178° / +0.331° 다르다. "실측 없이 값 변경 금지" 지시에 따라 계승했다 |
| `GUARD_TIME` / `LIFE_FACTOR` | 500 ms / 1 | 캡처 t=17.891~17.896 의 Seer init 값 |
| 호밍 속도 | 2500 | 0.1 r/min → 250 r/min. 캡처 t=17.918 |
| safety_mode | 30 | `SAFETY_SEER_GATE`. **릴레이를 강제 전환하지 않는 유일한 모드** |
| CAN 속도 | 250 kbps | 판다 부팅 기본값. ⚠ 500 k 로 덮으면 버스가 죽는다 |

## 검증

```bash
cd src/Comm/CAN/can_relay && PYTHONPATH=. python3 -m pytest test -q   # 84 passed
```

`protocol.py` 가 만드는 프레임 **28종 전부**가 실측 캡처 `Log/homing_capture_220350.jsonl`
(Seer 마스터 180 s, 253,510 프레임)에 **바이트 동일**로 존재한다(총 12,958건 일치).

**실기 미검증 항목** — 지면 사용 전 반드시 해소:
- 구동축 브링업 시퀀스(debt-017) — `allow_bringup` 기본 false. 잭업에서만 확인할 것
- 판다 guard RTR 불가 → Seer forward 의존(debt-012)
- `kin_steer_sign` 미확정(debt-004) — 확정 전 `cmd_vel` crab/스핀 금지
- 판다 fail-safe 정지 실효성(debt-013) — 이 패키지 정지의 근간이다

## 미구현 (의도적)

- **역기구학을 자체 구현하지 않는다.** 저장소에 이미 3벌 있고 접기 임계가 ±90°/±115°/±140° 로
  갈려 있다. `cmd_vel` 은 `motor_control.kinematics` 를 빌려 쓰며, import 실패 시 조용히
  대체하지 않고 구독을 만들지 않는다.
- `cmd_vel` 은 **동일각(직진·크랩)만** 지원한다. 스핀·선회는 축별 각이 갈리므로 거부한다.
- `wheel_motor_state`(2WS 모션 스택이 기다리는 것) 발행은 Phase 2.

## 관련 문서

- 설계 결정: `docs/adr/2026-07-29-can-relay-ros2-package.md`
- 감사 기록: `docs/code_review/can_relay_ros2/2026-07-29.md` (10인 + 적대적 심문 3인)
- 부채: `docs/debt/registry.md` debt-004·007·012·013·015·016·017·018
