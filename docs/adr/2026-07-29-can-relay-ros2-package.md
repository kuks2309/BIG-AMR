# ADR 2026-07-29 — can_relay ROS2 패키지 신설 (판다 릴레이 경유 모터 구동)

- Status: Accepted (Phase 1 — 골격 + 안전게이트). **실차 구동은 아래 HIL 게이트 뒤.**
- Date: 2026-07-29
- 사용자 지시: sess:520bf3ab 2026-07-29 09:56 — "`src/Comm/CAN/can_relay` 에 이제 모터 구동을 위한
  ros2 패키지를 만들어야 합니다. 10명 투입하여 관련 코드 검토해주세요. 적대적 토론 진행"
- 근거: 10인 코드감사 + 3인 적대적 반대심문 → `docs/code_review/can_relay_ros2/2026-07-29.md`
- 관련: `docs/adr/2026-07-09-motor-control-ros2-package.md`(Accepted, 별개 경로),
  `docs/adr/2026-07-28-can-transport-abstraction.md`(Accepted Phase 1-5),
  `docs/claude-mistake/2026-07-27-002`(node4 물리 손상)

## Context

`src/Comm/CAN/can_relay/` 는 2026-07-25 에 생성된 뒤 **파일 0개·git 미추적**으로 비어 있었다
(`git ls-files src/Comm` → 0건). 즉 이 결정은 기존 결정을 뒤집는 것이 아니라 아직 내려지지 않은
결정을 내리는 것이다.

같은 저장소에 `src/Actuators/motor_control`(974줄, 테스트 35건)이 이미 있다. 10인 감사 중
리뷰어 8이 "중복이므로 신설 말고 확장하라"고 주장했고, 변호인 D1 이 코드로 반박했다. 확정된 사실:

| 축 | `motor_control` | 본 패키지 |
| --- | --- | --- |
| 물리 경로 | socketcan `can1` 직결 (`driver_node.py:81`) | USB → panda → bus 2 (`gui.py:835` 와 동일) |
| Seer | **물리 분리 필수** (`README.md:83` "단독 마스터") | **연결 필수** (guard RTR forward 의존) |
| 정지 근간 | guard RTR 20 Hz 중단 → 500 ms HALT (`protocol.py:120-122`) | heartbeat 상실 → 펌웨어 `seer_stop_drives()` + 릴레이 개방 |
| RTR 송신 | 가능(필수) | **물리적 불가** — 판다 CAN 패킷 헤더에 RTR 비트가 없다 |
| 실차 구동 이력 | **없음** (`design-inputs.md:221` "실차 T4 미실시") | 같은 경로를 `gui.py` 가 2026-07-28 실기 확인 |

두 안전 모델은 포함관계가 아니라 **배타관계**다. 한쪽 전제(Seer 분리)가 다른 쪽 실패조건이며,
`motor_control` 에 판다 백엔드를 얹으면 그 패키지의 유일한 문서보증 정지수단(guard RTR 중단)이
**조용히 무력화**된다. 이는 리팩터가 아니라 안전 모델 제거다. 또한 debt-007 의 실체가
"판다 read 와 직결 read 의 조향값 불일치"이므로, 대조 실험이 가능하려면 두 구현이 따로 살아 있어야
한다. ⇒ 중복이 아니다.

## Decision

**1. `src/Comm/CAN/can_relay` 에 `ament_python` 패키지를 신설한다.**

- 경로: 사용자 지시대로. `README.md:24` 가 `Comm` 을 승인된 도메인으로 명시 열거하며,
  `src/Sensors/Camera/USB/` 라는 전송매체 분기 선례도 실재한다.
- 언어: Python(rclpy). 모터·CAN 도메인 선례가 만장일치이고(C++ 모터 코드 0줄), 50 Hz 는
  guard 타임아웃 500 ms 대비 25배 여유다. `stack.md:30` §2 는 미기입이라 선례로 판정했다.

**2. 이름 `can_relay` 를 유지한다 — 단, 알려진 비용을 문서화한다.**

리뷰어 8·변호인 D1 이 모두 개명을 권고했다. 근거는 저장소에서 `can_relay` 가 이미 판다 펌웨어를
뜻하며(`Tools/Can_Relay/`, `docs/can_relay/`, `docs/code_review/can_relay_firmware/`, `README.md:1`),
그 이름 공유로 **debt id 오참조가 실제 발생한 기록**이 있다는 것이다(`docs/debt/registry.md:41-45`).
사용자가 원안을 선택했으므로 그대로 가되, 완화책을 강제한다:
`package.xml` `<description>` 첫 단락이 펌웨어 프로젝트와의 구분을 명시하고, 본 ADR 과
아래 debt-015 가 충돌 위험을 등록한다. **문서·주석에서 인용할 때 어느 쪽인지 반드시 병기한다.**

**3. Phase 1 범위 = 골격 + 안전게이트. 모터는 돌리지 않는다.**

| 모듈 | 책임 |
| --- | --- |
| `protocol.py` | SDO 코덱 + 검증된 시퀀스. 버스·판다 무의존 순수 함수 |
| `safety.py` | 클램프·NaN 거부·bit15 신뢰게이트·호밍 2상 판정·정착 판정. 순수 함수 |
| `link.py` | `PandaLink`(주도권 5스텝·heartbeat) + `MockLink`(무-하드웨어 대역) |
| `backend.py` | 단일 제어 스레드. 주기 재송신·워치독·정지·수신 파싱 |
| `driver_node.py` | rclpy 진입점. `~/engage` 명시 호출 전까지 제어권을 잡지 않는다 |

**4. 역기구학을 자체 구현하지 않는다.** 저장소에 같은 IK 가 이미 3벌 있고 접기 임계가
±90°/±115°/±140° 로 서로 다르다. 4벌째는 발산을 고착시킨다. `cmd_vel` 경로는
`motor_control.kinematics` 를 **의존**하며, import 실패 시 조용히 대체하지 않고 구독을 만들지 않는다.

**5. 코드로 강제하는 안전 요건** (전부 회귀 시험으로 고정 — 84건 PASS):

| # | 요건 | 강제 지점 | 사고 근거 |
| --- | --- | --- | --- |
| S1 | 비유한(NaN/inf) 지령 **거부**, 워치독 갱신도 안 함 | `safety.finite()` → 각 콜백 | `max(-v,min(v,nan))` = `+v` — 오염 1개가 최대속도 지령 |
| S2 | 조향 ±90° 클램프를 **counts 생성 지점**에 | `safety.steer_deg_to_counts()` | 90~140° 미검증 구간. 후진 선회 twist 로 118° 도달 |
| S3 | 구동 지령 **주기 재송신**(단발 금지) + 워치독 만료 시 0 | `backend._loop` | 단발 송신은 프레임 1개 유실로 정지가 사라짐 |
| S4 | 정지는 어떤 상태에서도 **거부되지 않는다** | `backend.stop()` | 폴링 사망 시 GUI 가 정지를 반려한 결함 |
| S5 | heartbeat 유지 = 펌웨어 fail-safe 무장 | `link.acquire()` + 제어 루프 인터리브 | `set_safety_mode` 기본값 `0xf8` 가 fail-safe 전체를 끔 |
| S6 | 호밍 중(bit15=0) **위치를 쓰지 않는다** | `safety.position_trustworthy()` | `0x6064`=0 고정(3,080/3,080) → ≈−137° 가 상위로 누설 |
| S7 | 호밍 완료는 **0→1 전이**로만 판정 | `safety.HomingJudge` | 이미 호밍된 축을 즉시 완료로 오독 |
| S8 | 피드백 만료(TTL) 시 각도 `None` — 0 으로 채우지 않음 | `backend.steer_angles_deg()` | 구 GUI 의 신선도 게이트가 대체 없이 삭제됨 |
| S9 | 브링업·호밍은 **명시 요청 전용**, launch 기본 비활성 | `allow_bringup=false`, `~/home` | 호밍은 100°+ 스윙이고 시작하면 SW 가 못 멈춤 |
| S10 | 제어권은 `~/engage` 명시 호출로만 | `driver_node._srv_engage` | launch 만으로 움직일 수 있는 상태를 만들지 않음 |

**6. 조향 홈 상수는 바꾸지 않는다.** 실측 캡처에서 Seer 가 호밍 후 유지한 0° 목표는
`7882020`/`7859062` 로 config 값과 `+10,205`/`+18,976` counts(= `+0.178°`/`+0.331°`) 다르다.
그러나 debt-007 상환계획 ③ 이 "실측 없이 값 변경 금지"를 지시하고, 실기에서 쓰이는 값은 현 config
값이다. **파라미터로 노출하되 기본값은 유지**하고, 근본 해법(호밍 완료 후 실측 정착값 자동 취득)은
debt-016 으로 등록한다.

## Verification

무-하드웨어로 수행한 것(실행 명령·출력 그대로):

```
$ cd src/Comm/CAN/can_relay && PYTHONPATH=. python3 -m pytest test -q
84 passed in 1.78s

$ colcon build --packages-select motor_control can_relay --symlink-install
Summary: 2 packages finished [7.76s]
```

**인코더 ↔ 실측 캡처 바이트 대조** — 본 패키지가 만드는 프레임 28종 전부가
`Log/homing_capture_220350.jsonl`(Seer 마스터 180 s, 253,510 프레임)에 바이트 동일로 존재한다
(총 12,958건 일치). 브링업·호밍·조향·구동·guard 설정 전 종류가 포함된다. 즉 우리 바이트는
자체 주장이 아니라 **실기에서 오간 바이트와 같음이 원본 대조로 확인**됐다.

mock 링크로 노드를 실제 기동해 확인한 경로: engage → 조향 200° 지령이 90° 로 클램프 →
구동 지령 → NaN 거부 → 워치독 만료로 속도 0 → 정지 → 제어권 반환. 빌드 후 `cmd_vel` 경로도
확인(직진 0.1 m/s → 0°/2445 raw, 좌크랩 → 90°, NaN 거부, 스핀 거부).

**하지 않은 것 (반드시 남길 것)**: 장치 접속 0, 판다 플래시 0, 실모터 구동 0.
따라서 본 ADR 의 어떤 문장도 실차 거동을 확정하지 않는다.

## HIL 게이트 — 실차 구동 전 필수 (미통과)

1. **잭업 상태**에서 `link: mock` → `panda` 전환 후 `~/engage` 만 수행하고 지령 없이 관측
   (제어권 획득이 모터를 움직이지 않는지).
2. **구동축 브링업 미검증**(debt-017) — `allow_bringup: true` 는 잭업에서만. `gui.py` 에는 이
   시퀀스가 없고 Seer 브링업에 올라타는 방식이라 우리에겐 실기 자산이 0 이다.
3. **debt-012** (판다 guard RTR 불가 → Seer forward 의존) — 잭업 5분+ 구동으로 HALT 미발생 확인.
4. **debt-004** (`kin_steer_sign` 미확정) — 확정 전까지 `cmd_vel` 의 crab/스핀 사용 금지.
5. **debt-013** (S4 정지 명령 실효성 미검증) — 판다 fail-safe 가 본 패키지의 정지 근간이다.
6. 하드웨어 E-STOP 상비. 본 패키지의 소프트 estop 은 **구동만** 세우며 조향축은 PP 모드라
   직전 목표까지 회전한다.

## Consequences

- (+) 실기 검증된 판다 경로를 ROS2 로 올리면서, 사고를 낸 안전 결함(클램프·NaN·워치독·신선도)을
  **복제하지 않고** 코드로 강제한다. 강제는 84건 회귀로 고정된다.
- (+) `motor_control` 과 병존하므로 debt-007 의 두 경로 대조 실험이 가능하다.
- (+) `MockLink` 로 tegra 에서 무-하드웨어 검증이 가능하다 — 2026-07-27-002 가 요구한 사전 게이트.
- (−) `can_relay` 이름이 판다 펌웨어와 충돌한다(debt-015). 인용 시 병기 부담이 영구히 남는다.
- (−) 모터 구동 ROS2 패키지가 둘이 된다. **동시 기동 금지** — 두 패키지가 같은 드라이브에 서로 다른
  전제로 쓰면 충돌한다. 현재 이를 막는 기계 장치는 없다 — 근거(2026-07-29 실행, 0건):
  `grep -rniE 'flock|lockfile|pidfile|singleton' src/Comm/CAN/can_relay src/Actuators/motor_control --include=*.py`.
  부채로 등록했다(debt-018).
- (−) `cmd_vel` 은 동일각(직진/크랩)만 지원한다. 스핀·선회는 축별 각이 갈리므로 명시 거부한다.
- (−) 2WS 모션 스택이 기다리는 `wheel_motor_state` 발행자는 아직 만들지 않았다(Phase 2).

## Rollback Plan

되돌림은 **디렉토리 삭제 + colcon 산출물 제거**로 완결된다. 비가역 변경이 없기 때문이다:

```bash
rm -rf src/Comm/CAN/can_relay/{can_relay,test,config,launch,resource} \
       src/Comm/CAN/can_relay/{package.xml,setup.py,setup.cfg}
rm -rf build/can_relay install/can_relay
```

- 펌웨어를 쓰지 않는다(플래시 0건) → 판다 상태 변화 없음.
- 드라이브 파라미터를 영구 저장하지 않는다(`0x1010` Store 미사용) → 모터 상태 변화 없음.
- 기존 패키지를 수정하지 않는다 — `motor_control` 은 `exec_depend` 로 **읽기 전용 참조**만 한다.
- 유일한 저장소 변경은 본 ADR·debt 등록·리뷰 산출물이며, 이력 보존을 위해 삭제하지 않고
  `Status: Superseded` 로 표기한다.
