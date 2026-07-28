# AMR 기구학 + 헤드리스 구동 (Chassis Kinematics & Headless Drive)

AMR(Autonomous Mobile Robot) 4륜 독립조향(multi-steer) **역기구학(inverse kinematics)** +
can-relay 연동 **헤드리스 구동 스택**. `can_relay/drive_gui.py`(monolith GUI)에서
**GUI 분리 원칙**으로 구동/제어 로직을 PyQt 에서 완전히 떼어낸 계층형 구성 (로직 비트 동일 보존).

## 계층 구조 (GUI 분리 + 백엔드 추상화)

CAN 백엔드는 `CanTransport` 로 추상화되어 socketcan/pcan/mock 을 spec 문자열로 교체한다
(ADR `docs/adr/2026-07-28-can-transport-abstraction.md`). 구동 로직은 백엔드를 모른다.

```
chassis_kinematics.py   순수 역기구학 수학 (math only)         ← 의존 0
        ▲
can_protocol.py         SDO/RTR 코덱 (stdlib, CanFrame)        ← 의존 0 (python-can 불요)
        ▲
can_transport.py        CanTransport(ABC) + 백엔드              ← python-can (lazy import)
        │   mock · socketcan · pcan  [· panda = Phase 6-9]
        ▲
direct_driver.py        DirectDriver 상태기계·50Hz TX          ← 트랜스포트만 의존
        ▲
authority.py            주도권(KernelCangwAuthority/NoAuthority) ← scripts/relay_cangw.sh
        ▲
drive_headless.py       GUI 없는 진입점 (build_stack 조립)
```
GUI(PyQt)는 이 계층들을 **import 만** 하면 됨 — 구동 로직은 GUI 에 없다(분리 완료).

## 파일
| 파일 | 계층 | 책임 |
|------|------|------|
| [chassis_kinematics.py](chassis_kinematics.py) | 수학 | `kin_inverse` · `twist_to_targets` · `kin_selftest` (math only) |
| [can_protocol.py](can_protocol.py) | 코덱 | `CanFrame` + `sdo_write`/`guard_rtr`/`sdo_read`/`to_signed` (stdlib, 바이트 동일) |
| [can_transport.py](can_transport.py) | 트랜스포트 | `CanTransport(ABC)` + `MockTransport`·`PythonCanTransport` + `open_transport`, arm/preflight 안전배리어 |
| [direct_driver.py](direct_driver.py) | 구동 | `DirectDriver`(transport 주입·enable·50Hz TX·2단계 발진·비무장 거부) |
| [authority.py](authority.py) | 주도권 | `KernelCangwAuthority`(gate on/off·롤백)·`NoAuthority`·`make_seer_gate_hook`·`run_cangw` |
| [relay_authority.py](relay_authority.py) | (shim) | 하위호환 재-export → authority |
| [drive_headless.py](drive_headless.py) | 진입점 | `build_stack(backend)` 조립 — CLI, 기본 dry-run(mock) |
| [scripts/relay_cangw.sh](scripts/relay_cangw.sh) | — | 커널 can-gw 게이트 제어 (start/gate_on/gate_off/stop, root) |
| [tests/](tests/) | 검증 | 바이트동일 회귀·mock 안전게이트·authority 롤백 (stdlib, tegra 실행) |

## 역기구학
차체명령 `(vx, vy, ω)` → 바퀴별 `(조향각 θ, 바퀴속도 v)`:

```
θᵢ = atan2(vy + ω·xᵢ, vx − ω·yᵢ)
vᵢ = hypot(vy + ω·xᵢ, vx − ω·yᵢ)
```

- **±140° 초과 시 등가해 접기**: `θ ∓ π, −v` (조향 한계 내 유지)
- **속도 포화**: 최대 바퀴속도가 `KIN_VMAX(≈0.2 m/s)` 초과 시 전 바퀴 비율 유지 축소

## 함수
| 함수 | 입력 → 출력 | 설명 |
|------|-------------|------|
| `kin_inverse(vx, vy, w, vmax)` | 차체명령 → `{노드: [θ(rad), v(m/s)]}` | 역기구학 core |
| `twist_to_targets(vx, vy, w, …)` | 차체명령 → `(vel_units, steer_counts)` | θ·v → 액추에이터 목표(순수, 송신 없음) |
| `kin_selftest()` | → `bool` | 직진/후진/크랩/스핀/포화 5케이스 수학 검증 |

## 실행
```bash
# 무-하드웨어 검증 (stdlib 전용 — python-can 불요, tegra 가능)
python3 chassis_kinematics.py --selftest      # 역기구학 5케이스 (5/5 PASS)
python3 direct_driver.py --selftest           # MockTransport 구동 자가시험
python3 tests/test_can_protocol.py            # 바이트동일 회귀 (7/7)
python3 tests/test_direct_driver_mock.py      # 안전게이트: 정렬 전 vel≠0 금지 (6/6)
python3 tests/test_authority.py               # 주도권 롤백·멱등 (6/6)

# dry-run(mock) — 실 하드웨어 미접촉 (기본값)
python3 drive_headless.py --demo                       # 전진→크랩→스핀 데모, 프레임만 기록

# 실차 주행 (--live 명시 필수, preflight 통과 후 arm)
python3 drive_headless.py --demo --live --backend socketcan          # can1 구동 + can0 Seer 게이트
python3 drive_headless.py --twist 0.05 0 0 --dur 2 --live --backend socketcan
python3 drive_headless.py --demo --live --backend pcan --motor PCAN_USBBUS1   # PCAN 직결(미검증)
```

### 백엔드 (`--backend`)
| backend | 경로 | 상태 |
|---------|------|------|
| `mock`(기본) | 무-하드웨어, 프레임 기록 | dry-run 정본 검증 |
| `socketcan` | `can.Bus(interface='socketcan')` + 커널 can-gw 게이트 | 실차 성숙 |
| `pcan` | `can.Bus(interface='pcan')` PCANBasic 직결 | ⚠ 미검증(인터페이스 정체 확인 필요) |
| `panda` | comma.ai panda 하드웨어 릴레이 | Phase 6-9 (HIL 승인 게이트, 미배선) |

### can-relay 연동 흐름 (socketcan)
1. 커널 릴레이 가동: `sudo scripts/relay_cangw.sh start` (평시 Seer↔모터 저지연 포워딩)
2. `--live --backend socketcan` → `KernelCangwAuthority` 가 `gate_on` 으로 Seer 주도권을 PC 로 전환
   (Seer 쓰기 차단 + 가짜 ack 합성, 읽기·guard RTR 통과). 부분실패 시 무조건 롤백.
3. preflight 통과 후 트랜스포트 `arm()` → `DirectDriver` 가 모터 버스로 enable + 50Hz SDO 송신
4. 종료 시 `gate_off` → 즉시 Seer 로 주도권 반환
- gate 전환에 root 필요 → 무프롬프트 원하면 `sudoers` NOPASSWD 등록(원본 can_relay README).

## 요구사항
- 수학·코덱·mock 계층(`chassis_kinematics`·`can_protocol`·`can_transport`·테스트)은 **표준 라이브러리만** — tegra 즉시 실행.
- 실 구동(`--live`)에만 `python-can` + `can-utils`(cangw) + CAN 인터페이스(socketcan can0=Seer/can1=모터 또는 pcan) 필요.

## 출처 / 근거
- 원본: `can_relay/drive_gui.py` · `relay_core.py` · `scripts/relay_cangw.sh` (`can_relay_2026-07-10.zip`)
- 기구학 이식원: `kin_viz` `chassis_kin::inverse_multisteer` (seer_robotics_analysis@b0bce72, `models.hpp:127-142`)
- 바퀴 기하: Roll_A084 실측 config (`live_models.hpp:67`) — Front x=+0.6039, Rear x=−0.5961, 휠베이스 1.200 m
  - **⚠ 2026-07-27 감사 — 조건 명시(값 변경 없음).** 위 값은 **Roll_A084 실측 config 에서 가져온 것이고,
    본 기체(Foil_A082) 직접 실측이 아니다.** 이 스택이 구동하는 실기는 Foil_A082 다
    (`docs/verified_facts/2026-07-27.md:11` 「장비: Foil_A082 실기」,
    `docs/adr/2026-07-26-2ws-motion-from-qd-refactor.md` §맥락(2026-07-27 기준 :13)
    「현재 실물 AMR = **Foil_A082**」, 같은 ADR :49 「Foil_A082 를 직접 실측했다는 기록은 저장소에 없다」).
    **두 기체가 같은 휠 기하라는 근거는
    저장소 어디에도 인용돼 있지 않다.**
  - 다만 **크기 자체**는 본 기체 장비 config 와 일치한다 —
    `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md:15`
    「휠베이스 1.20 m, wheelRadius 0.125 m」, 같은 문서 `:11-14` 의 ±0.604 / −0.596.
  - **전/후 노드 귀속은 미판정** (아래 「주의」 항목 참조).
  - 같은 수치를 `src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml:17` 는
    「Foil_A082 실측」 으로 **정반대 귀속**하고 있어 두 기록이 서로 어긋난다 —
    그 파일에도 동일 감사 정정을 붙였다.
- ADR: `docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md` · `docs/adr/2026-07-09-relay-authority-arbitration.md`
- 프로토콜: `References/Tongyi-Motor-Controller/tongyi-canopen-protocol-reference.md`

## ⚠ 주의 (실차 미검증 가정)
- **노드 매핑** (node1=Rear, node2=Front) 과 **조향 부호** `KIN_STEER_SIGN` 은 미검증 가정.
  - **⚠ 2026-07-27 감사 격상 — 노드 매핑은 '미검증 가정'이 아니라 「반증 보고 있음(미판정)」 이다.**
    `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md:11-12`
    (EasyDRIVE canID config, ✓)는 **node1 = FrontWalk +0.604 / node2 = RealWalk −0.596** 으로 정반대다.
    같은 반전이 `docs/code_review/motor_control-can-consistency/2026-07-26.md:59-68` 에
    🔴HIGH 로 등록됐고 **미해소**(같은 문서 :116).
    또한 `chassis_kinematics.py:51` `KIN_STEER_OF={1:3,2:4}` 는 그 레퍼런스(:13-14 node3=FrontSteer)와
    정합하므로, `KIN_NODE_XY`(node1=Rear)와 **같은 파일 안에서 서로 어긋난다**.
    ⇒ 값은 바꾸지 않았다(부호가 실배선·`KIN_DRIVE_SIGN` 과 상쇄되는지 미확정).
    **판정에 필요한 측정**: 잭업(바퀴 지면 이격) 후 node1 단독 저속 구동 → 앞/뒤 육안 확인.
- 첫 실차 구동은 **저속에서 크랩/스핀 방향 확인 후** 사용할 것.
- `twist_to_targets` 의 `steer_counts` 절대위치는 실측 조향 홈(N3 7871815, N4 7840086) 기준.
  - **⚠ 2026-07-27 감사 — 위 문장은 조건이 빠졌다(값 유지, 서술만 정정).**
    이 홈 상수(N3 7871815 / N4 7840086)는 **기동 브링업 스윙을 마친 뒤에만 유효한 기준일 수 있다.**
    `docs/ros2_driver/2026-07-09-design-inputs.md`(2026-07-27 기준 :99, :103)은 「부팅 직후 **전 노드
    `0x6064` ≈ 0**(N3=0, N4=−39 — 홈값 아님, 정상)」, 「조향이 **0에서 홈까지 3.3 s 물리 스윙(+137.3°)**」
    이라고 한다. 즉 홈 상수는 **매 기동 시 스윙으로 도달하는 절대 목표**이지 기동 직후의 현재값이 아니다.
    같은 문서 :160 은 이 항목의 「✓ 해소(전원 사이클 불변)」 판정을 **2026-07-27 재개방(미판정)** 했다.
  - **⚠ 미판정 모순이 등록돼 있다** — `docs/verified_facts/2026-07-27.md` §B-1(안전 직결):
    같은 시각 Seer 1040 은 FrontSteer `encoder −7,871,810` 에서 `position ≈0 rad`·`calib=True`,
    운전자 육안도 바퀴 0°(직진)인데, 판다 read 는 node3 ≈ **−1,517 counts** 였다.
    구동 노드는 두 소스가 절댓값 일치하는데 **조향 노드에서만 7.87 M counts(=137°) 어긋난다.**
    가능 설명 (a) 판다 조향 `0x6064` read 오염 / (b) 호밍 후 드라이브가 위치 기준 재설정 — **미판정**.
  - 이 값은 `direct_driver.py:184` (`sdo_write(n, 0x607A, steer[n], size=4)`, DirectDriver 50 Hz TX 루프)가
    기동 직후부터 조향 노드에 **절대 지령**한다(같은 파일 :15 「3/4=조향(0x607A)」).
    ⇒ **판정 전에는 실차 절대 조향 지령 금지.**
    **판정에 필요한 측정**: 제어권 미획득(비-intercept) 상태의 판다 `0x6064` read 와
    **동시각** Seer 1040 `encoder` 를 대조하여 (a)/(b) 를 분리.
    (같은 뿌리의 사고 기록: `docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md`
    — 조향 node4 가 137° 범위 밖으로 밀려 물리적으로 갇힌 사건.)
- 본 스택은 개발 PC(python-can 미설치)에서 **stdlib 회귀 19/19 PASS**(바이트동일 7 + mock 안전게이트 6 +
  authority 롤백 6)까지 완료. 단, **실 CAN 버스 경로(`PythonCanTransport._to_msg` 바이트 대조)는 미검증**
  — python-can 머신에서 `CanFrame→can.Message` 필드 동일성 1건 대조가 실차 arm 전 게이트(ADR §미해결 M2).
- 실차 승급 순서: `--backend mock`(기본 dry-run) → python-can 머신 `_to_msg` 대조 → `--live --backend socketcan`
  attended 정차(vel 0) → 저속 크랩/스핀 방향부호. 각 승급 전 사용자 명시 승인.
- 실로봇 구동: 안전구역·E-STOP 상비. `direct/기구학` 모드는 **커널 릴레이 gate 전환 후**에만(버스 충돌 방지).
