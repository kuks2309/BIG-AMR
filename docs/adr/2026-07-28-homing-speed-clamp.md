# ADR 2026-07-28 — 호밍 속도(`0x6099`) 상한 검증 추가

## 상태

**Accepted — 2026-07-28 실기 플래시·검증 완료.**

| 단계 | 결과 |
|---|---|
| 빌드 | 통과(`-Werror`), 30,280 B / 한도 49,152 B |
| 플래시 | 서명 md5 `0163ee0b3887d183…` 실기=빌드 일치 |
| 실기 거부 검증 | `speed` 65535·3001·99 → `0xea` resp=0, `0xeb` state=0(미개시) |
| 실기 수락 검증 | `--speed 2500` → 수락, 호밍 완주 `DONE`(36.0 s), `reached_mask=0x03` |
| 회귀 없음 | `speed=0`(기존 도구 기본값)은 범위검사를 건너뜀 — 기존 절차 무영향 |

⚠ 본 ADR 의 줄번호는 **2026-07-28 주석 제거·`0xec` 제거 이후 기준**으로 갱신됨
(`safety_seer_gate.h` md5 `c35daf53…`, 475줄).

## 맥락

`0xea`(호밍 개시) 명령의 `wIndex` 16비트 생값이 **아무 검증 없이** 드라이브의 `0x6099`(Homing Speeds)로 전달된다.

```
usb_comms.h:406   seer_homing_cmd(start, setup->b.wIndex.w)   ← 16비트 생값
safety_seer_gate.h:331   seer_home_speed = (speed == 0U) ? SEER_HOME_SPEED_DEF : speed;   ← 0 만 치환
safety_seer_gate.h:359   seer_home_sdo_write(n, 0x6099U, 0U, seer_home_speed, 4U);        ← 그대로 송신
```

호밍은 조향축이 **음의 리밋 스위치(기계적 정지면)를 향해 주행**하는 동작이므로(Home method 1, 전 노드 `0x6098=1` 실기 판독), 그 속도는 안전 파라미터다.

### 1차 source 대조 (`external_reference` 규칙 준수)

`References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt`

| 항목 | 값 | 인용 |
|---|---|---|
| `0x6099` 단위 | 0.1 r/min | `:8600-8601` "Homing Speeds … unit 0.1r/min" |
| 드라이브 파라미터 | `0x4492 SelfSofRst.uwRstStarSpd`, 16비트 | `:10249` |
| **문서화된 유효 범위** | **0~10000** (= 0~1000 rpm) | `:5915`, `:10249` |
| 드라이브 기본값 | 1000 (100 rpm) | `:5915` |

| 우리 값 | 비고 |
|---|---|
| 운용값 `SEER_HOME_SPEED_DEF` = 2500 (250 rpm) | Seer 실측 관례 (`safety_seer_gate.h:196`) |
| **주입 가능 최대 = 65535 (6553.5 rpm)** | 문서 상한의 **6.5배**, 운용값의 26배 |

### 미판정 (본 ADR이 해소하지 않는 것)

**드라이브가 범위 밖 값을 클램프하는지 거부(SDO abort)하는지 Handbook에 명시가 없다.** 범위 `0~10000`은 파라미터 표에만 있고 초과 시 거동 서술이 없다. `:5703`의 "드라이브 내부 최고속도는 모터 정격속도로 제한"은 PT(Profile Torque) 모드 절 안이라 호밍에 일반화할 수 없다. ⇒ **"드라이브가 알아서 막아줄 것"이라는 가정 위에 설계하지 않는다.**

### 현실적 위협 모델

악의가 아니라 **오타**다. `Tools/docking_field_kit/orin_homing_run.py:39`의 `--speed`는 `type=int`이고 검증이 없어, `--speed 25000`(0 하나 더)이 그대로 나간다.

> **연결 주의**: 2026-07-27 node4 137° 갇힘 사고는 **부호·목표값 미대조와 급점프**가 원인이며(`docs/claude-mistake/2026-07-27-002`) **속도 문제가 아니었다.** 본 ADR의 근거는 그 사고가 아니라 위 Handbook 상한 초과 사실 자체다. 두 건의 공통점은 "호스트 미검증 입력이 하드웨어 모션 지령까지 도달한다"는 계열뿐이다.

## 결정

`seer_homing_cmd()` 개시 인터록에 **속도 범위 검증**을 추가한다. 클램프(값을 조용히 잘라내기)가 아니라 **거부(reject)** 한다 — `0xea`는 이미 `resp[0]`으로 수락/거부를 반환하므로, 호스트가 자기 값이 틀렸음을 알 수 있어야 한다.

```c
#define SEER_HOME_SPEED_MIN 100U    // 10 r/min — 이보다 느리면 120 s 안에 리밋 도달 불가
#define SEER_HOME_SPEED_MAX 3000U   // 300 r/min — 운용값 2500 의 1.2배

if ((speed != 0U) && ((speed < SEER_HOME_SPEED_MIN) || (speed > SEER_HOME_SPEED_MAX))) {
  return false;
}
```

**상한을 문서 상한(10000)이 아니라 3000으로 조인 이유**: 우리 운용 범위는 2500 하나뿐이고, 정지면을 향한 주행에서 1000 rpm(문서 상한)은 과하다. 필요해지면 상수 하나만 올리면 되고, 그때 이 ADR을 supersede 한다.

**하한 100의 근거**: `SEER_HOME_TIMEOUT_S = 120`이고 speed=1(0.1 rpm)이면 리밋에 닿기 전 타임아웃한다. 위험하지는 않으나 조용한 실패를 막는다.

## Rollback Plan

| 항목 | 내용 |
|---|---|
| **직전 실기 이미지** | `Tools/Can_Relay/fw_backups/panda.bin.signed.device_2026-07-28_b31d6789` (30,268 B, 서명 md5 `b31d67899631bdf3`) — **2026-07-28 18:27 실기 조회로 이 이미지가 장치에 올라가 있음을 확인**하고 백업 |
| **되돌리는 법** | `python3 Tools/docking_field_kit/flash_panda.py <위 파일>` 후 `0xd3`+`0xd4` 서명 md5가 `b31d6789…`로 복귀했는지 확인 |
| **되돌림 판단 기준** | 호밍 개시가 거부(`0xea` resp[0]==0)되는데 속도가 정상 범위(예: 2500)인 경우 → 검증 로직 오류 |
| **부분 롤백** | 불가(펌웨어 단위). 전체 이미지 교체만 |
| **⚠ 이후 변경** | 본 ADR 적용 후 `0xec` 제거가 추가돼 현재 실기는 `…clamp_and_0xec_removed_2026-07-28_5caa5cff`(30,188 B) 다. 클램프-단독 중간 빌드(30,280 B, 서명 `0163ee0b…`)는 **보존 실패** — 재빌드 필요. 체인 전체는 `fw_backups/README-2026-07-28.md` |
| **위험** | 플래시 실패 시 부트스텁 갇힘 가능 → DFU(`flash_panda.py --recover`)로 복구. 앱 크기가 49,152 B를 넘지 않는지 **플래시 전 반드시 확인**(초과 시 서명검증 실패, 2026-07-27 실증) |

## 영향 범위

- **펌웨어**: `board/safety/safety_seer_gate.h` 만. 상수 2개 + 조건문 1개 추가.
- **호스트**: 없음. `0xea`의 반환 규약(`resp[0]` 1=수락/0=거부)이 그대로이고, 기존 호출처(`orin_homing_run.py`)는 `--speed 0`(기본) 또는 2500 계열을 쓰므로 거부되지 않는다.
- **회귀 위험**: 정상 범위 밖 속도로 호밍을 돌리던 절차가 있었다면 거부된다. 저장소 내 호출처 grep 결과 그런 절차는 없다.

## 검증

- [x] 1차 source 대조 (Handbook `:5915`·`:8600`·`:10249`)
- [x] 빌드 통과 + 앱 크기 < 49,152 B (30,280 B)
- [x] 경계값 실기 검증: `65535`·`3001`·`99` 거부 확인 / `2500` 수락·호밍 완주 확인
- [x] 실기 플래시 + 서명 md5 대조
- [ ] `100`·`3000` 정확 경계는 미시험(각각 수락되면 호밍이 실제 구동되므로 대표값 2500 으로 갈음)

## 참조

- 리뷰 결함 C4: `docs/code_review/can_relay_firmware/2026-07-28.md` §Critical
- 함수표 #22 `seer_homing_cmd` / 전역표 #218 `SEER_HOME_SPEED_DEF` · #232 `seer_home_speed` (동 문서 §3·§4)
