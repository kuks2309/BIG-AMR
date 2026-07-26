# AMR 기구학 + 헤드리스 구동 (Chassis Kinematics & Headless Drive)

AMR(Autonomous Mobile Robot) 4륜 독립조향(multi-steer) **역기구학(inverse kinematics)** +
can-relay 연동 **헤드리스 구동 스택**. `can_relay/drive_gui.py`(monolith GUI)에서
**GUI 분리 원칙**으로 구동/제어 로직을 PyQt 에서 완전히 떼어낸 계층형 구성 (로직 비트 동일 보존).

## 계층 구조 (GUI 분리)
```
chassis_kinematics.py   순수 수학 (math only)              ← 의존 0
        ▲
direct_driver.py        CAN 프로토콜 + DirectDriver 스레드   ← python-can
        ▲
relay_authority.py      can-relay 주도권 코디네이터           ← python-can + scripts/relay_cangw.sh
        ▲
drive_headless.py       GUI 없는 진입점 (조립)
```
GUI(PyQt)는 이 계층들을 **import 만** 하면 됨 — 구동 로직은 GUI 에 없다(분리 완료).

## 파일
| 파일 | 계층 | 책임 |
|------|------|------|
| [chassis_kinematics.py](chassis_kinematics.py) | 수학 | `kin_inverse` · `twist_to_targets` · `kin_selftest` (math only) |
| [direct_driver.py](direct_driver.py) | 구동 | CAN SDO 헬퍼 + `DirectDriver`(enable·50Hz TX·2단계 발진) |
| [relay_authority.py](relay_authority.py) | 주도권 | `RelayAuthority`(gate on/off) · `make_seer_gate_hook` · `run_cangw` |
| [drive_headless.py](drive_headless.py) | 진입점 | 3계층 조립 — CLI 로 실차 주행 |
| [scripts/relay_cangw.sh](scripts/relay_cangw.sh) | — | 커널 can-gw 게이트 제어 (start/gate_on/gate_off/stop, root) |

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
# 수학만 (무-하드웨어, 의존 0)
python3 chassis_kinematics.py --selftest      # 5케이스 수학 자가시험 (5/5 PASS)

# 구동 (python-can + CAN 인터페이스 필요)
python3 direct_driver.py --selftest --channel vcan1   # DirectDriver 송신 경로 자가시험

# can-relay 연동 실차 주행 (헤드리스, GUI 없음)
python3 drive_headless.py --demo                      # can1 구동 + can0 Seer 게이트, 저속 데모
python3 drive_headless.py --demo --no-relay           # 게이트 생략(Seer 미연결 벤치)
python3 drive_headless.py --twist 0.05 0 0 --dur 2    # (vx,vy,ω) 2초 주행
```

### can-relay 연동 흐름
1. 커널 릴레이 가동: `sudo scripts/relay_cangw.sh start` (평시 Seer↔모터 저지연 포워딩)
2. `drive_headless.py` 실행 → `RelayAuthority` 가 `gate_on` 으로 Seer 주도권을 PC 로 전환
   (Seer 쓰기 차단 + 가짜 ack 합성, 읽기·guard RTR 통과)
3. `DirectDriver` 가 모터 버스(can1)로 enable + 50Hz 조향/구동 SDO 송신
4. 종료 시 `gate_off` → 즉시 Seer 로 주도권 반환
- gate 전환에 root 필요 → 무프롬프트 원하면 `sudoers` NOPASSWD 등록(README 하단 예 / 원본 can_relay README).

## 요구사항
- `python-can` (구동 계층) · `can-utils`(cangw) · SocketCAN 인터페이스(can0=Seer, can1=모터)
- 수학 계층(`chassis_kinematics`)은 표준 라이브러리만 사용 — 별도 설치 불요.

## 출처 / 근거
- 원본: `can_relay/drive_gui.py` · `relay_core.py` · `scripts/relay_cangw.sh` (`can_relay_2026-07-10.zip`)
- 기구학 이식원: `kin_viz` `chassis_kin::inverse_multisteer` (seer_robotics_analysis@b0bce72, `models.hpp:127-142`)
- 바퀴 기하: Roll_A084 실측 config (`live_models.hpp:67`) — Front x=+0.6039, Rear x=−0.5961, 휠베이스 1.200 m
- ADR: `docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md` · `docs/adr/2026-07-09-relay-authority-arbitration.md`
- 프로토콜: `References/Tongyi-Motor-Controller/tongyi-canopen-protocol-reference.md`

## ⚠ 주의 (실차 미검증 가정)
- **노드 매핑** (node1=Rear, node2=Front) 과 **조향 부호** `KIN_STEER_SIGN` 은 미검증 가정.
- 첫 실차 구동은 **저속에서 크랩/스핀 방향 확인 후** 사용할 것.
- `twist_to_targets` 의 `steer_counts` 절대위치는 실측 조향 홈(N3 7871815, N4 7840086) 기준.
- 본 스택은 개발 PC(python-can 미설치)에서 **구문 컴파일 + mock CAN 로직 검증**까지만 완료.
  실 CAN 버스/실차에서의 구동은 **미검증** — 로봇 환경에서 `--no-relay` 벤치 → can-relay 연동 순으로 확인 필요.
- 실로봇 구동: 안전구역·E-STOP 상비. `direct/기구학` 모드는 **커널 릴레이 gate 전환 후**에만(버스 충돌 방지).
