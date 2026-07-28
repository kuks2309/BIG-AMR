# 드라이브 정지 수단 설정값 실기 판독 — 2026-07-28

fail-safe 재설계의 전제를 확정하기 위해 4노드의 **정지 관련 오브젝트를 읽기 전용으로 판독**했다.
모터 지령 프레임은 한 개도 보내지 않았다(SDO(Service Data Object) 읽기 `0x40` 만 송신).

## 수행

```bash
cd Tools/docking_field_kit && python3 orin_read_homing_params.py
```

- 판다 펌웨어 `DEV-cd7886dc-DEBUG`
- 제어권 획득(safety=30, auth=PC, intercept) 상태에서 판독 후 반환
- 판독 대상은 `orin_read_homing_params.py` 의 `OBJECTS` 에 2026-07-28 추가된 5개
  (`0x100C`, `0x100D`, `0x605A`, `0x605D`, `0x6085`) + 기존 7개

## 결과 (4노드 전수)

| 객체 | node1 (구동) | node2 (구동) | node3 (조향) | node4 (조향) |
|---|---|---|---|---|
| `0x100C` Guard Time (ms) | **500** | **500** | **500** | **500** |
| `0x100D` Life Time Factor | **1** | **1** | **1** | **1** |
| `0x605A` Quick stop option code | **0** | **0** | **0** | **0** |
| `0x605D` Halt option code | **0** | **0** | **0** | **0** |
| `0x6085` Quick stop deceleration | **0** | **0** | **0** | **0** |
| `0x6098` Homing method | 1 | 1 | 1 | 1 |
| `0x6099` Homing speed (0.1 r/min) | 1000 | 1000 | 2500 | 2500 |
| `0x607C` Homing offset | 0 | 0 | 0 | 0 |
| `0x609A` Homing accel (ms) | 100 | 100 | 100 | 100 |
| `0x6060` Modes of operation | 3 (PV 속도) | 3 (PV 속도) | 1 (PP 위치) | 1 (PP 위치) |
| `0x6041` Statusword | `0x8050` | `0x8050` | `0x9450` | `0x9450` |
| `0x6000.1` Digital Input | `0x01` | `0x01` | `0x01` | `0x01` |

판다 health: `ignition_line=0`, `ignition_can=0`, `safety_mode=0`, `heartbeat_lost=0`

## 판정

### ① Node guarding 이 4노드 전부에 무장돼 있다 — 타임아웃 500 ms

`0x100C = 500`, `0x100D = 1` 이고 **둘 다 0이 아니다.**

Handbook V7.0 §6.4.3 Node Protection (`HB:7146-7164`, printed 142) 원문:

> "When the communication is interrupted or **the master station stops sending request messages** … the
> driver will **enter the HALT state and halt automatically, without powering off the motor**."
> "Request messages of the master station — **0x700 + Node number**; (The frame format is remote frame)"
> "If the monitoring time and any parameter of the life time factor are set to zero, this function will not be activated."

⇒ **마스터가 `0x700+node` RTR(Remote Transmission Request) 폴을 500 ms 멈추면 드라이브가 토크를 유지한 채 자동 정지한다.**
이것은 이 하드웨어에서 **원문으로 보증된 유일한 토크 유지 정지 수단**이다.

이전 캡처(`Log/homing_capture_220350.jsonl`)에서 node3·4 의 `0x100C`/`0x100D` 쓰기가 호밍 **종료 후**(t=49.01/49.09)에만
보였던 것은 Seer 의 재기록일 뿐이며, **설정 자체는 상주한다**는 것이 이번 판독으로 확정됐다.

### ② 능동 정지 프레임(`0x6040`)은 이 하드웨어에서 거동이 정의되지 않는다

`0x605A`(Quick stop option) · `0x605D`(Halt option) · `0x6085`(Quick stop deceleration) 이 **전부 0** 이다.

- Handbook 은 `0x605A`·`0x605D` 의 **값 의미와 기본값을 전문에 기재하지 않는다**(이름만 등장).
  `0x605D` 는 문서 내에서 명칭조차 `Halt_option_code` ↔ `Stop_option_Code` 로 불일치한다.
- ⓦ CiA 402 기준으로는 quick stop option code 0 이 "disable drive function"(토크 상실)에 해당하나,
  **표준 원문이 저장소에 없어 확정할 수 없다.**
- `0x6085 = 0` 이므로 감속률도 미설정이다.

⇒ **`0x6040 = 0x010F`(Halt) 를 fail-safe 정지 수단으로 채택할 근거가 현재 없다.**
채택하려면 옵션코드를 먼저 써서 정의된 값으로 만들어야 하고, 그 쓰기 자체가 드라이브 상주 설정 변경이다.

### ③ heartbeat 임계는 2초로 확정

`check_started()` = `current_board->check_ignition() || ignition_can` 인데
`ignition_line=0`·`ignition_can=0` 이므로 **false** → `HEARTBEAT_IGNITION_CNT_OFF = 2` 가 적용된다
(`board/main.c:153-154, 213`). `HEARTBEAT_IGNITION_CNT_ON`(5초)은 이 장비에서 **도달 불가능한 분기**다.

실효 지연은 정확히 2초가 아니라 **1.0~2.0초** — `heartbeat_counter` 가 1 Hz tick 으로 증가하고
판정이 `>= 2` 이므로, 마지막 심박이 tick 직전이면 2.0 s, 직후면 1.0 s 다.

## 미확인으로 남는 것

| 항목 | 왜 이번 판독으로 안 되는가 | 확인 방법 |
|---|---|---|
| 폴을 실제로 끊었을 때 500 ms 뒤 정지하는가 | 설정값 판독일 뿐 거동 관측이 아니다 | 잭업 상태에서 `0x701~0x704` 중계 차단 후 `0x6064` 정지 관측 |
| HALT 상태에서 홀딩토크가 실제로 유지되는가 | 원문은 "without powering off the motor" 라고만 한다 | 위 실험 중 `0x6041` bit4 및 축 외력 반응 확인 |
| 조향축에 전원차단형 브레이크가 배선돼 있는가 | 매뉴얼 범위 밖 | 배선 확인(Handbook §2.4 Brake Terminal P2) |
| `0x605A`/`0x605D` 값 0 의 이 드라이브에서의 의미 | Handbook 미기재, CiA 원문 부재 | 벤더 문의 또는 CiA 402 원문 입수 |

## 관련

- 도구: [Tools/docking_field_kit/orin_read_homing_params.py](../../Tools/docking_field_kit/orin_read_homing_params.py)
  — 2026-07-28 에 위 5개 객체와 health 출력을 추가했다.
- 1차 source: `References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt`
- 리뷰 결함 C2·C3: [docs/code_review/can_relay_firmware/2026-07-28.md](../code_review/can_relay_firmware/2026-07-28.md)
