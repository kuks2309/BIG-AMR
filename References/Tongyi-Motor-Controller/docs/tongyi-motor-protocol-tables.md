# Tongyi IxLII/IxLs/IxH 서보 드라이버 — 모터 프로토콜 테이블 정리

> 작성: 2026-07-08 · 1차 source: [IxLII/IxLs/IxH Servo Driver Handbook V7.0, §6, page 133–197](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) + [EDS Servo_Driver_20200805.eds](../canopen/EDS_extracted/Servo_Driver_20200805.eds) + 실측([tongyi-canopen-protocol-reference.md](tongyi-canopen-protocol-reference.md))
> 검증 등급: **✓** 1차 source/실측 직접 확인 · **ⓦ** 타 보고만 · **⚠** 미확정/확인 필요
> 참고: 본 폴더 경로는 표준(`references/<vendor>/<product>/`)과 다른 기존 관례(`References/Tongyi-Motor-Controller/`)를 유지한다.

**약어**: CAN(Controller Area Network) · CiA(CAN in Automation) · COB-ID(Communication Object Identifier) · NMT(Network Management) · SYNC(Synchronization Object) · EMCY(Emergency Object) · SDO(Service Data Object) · PDO(Process Data Object) · RPDO/TPDO(Receive/Transmit PDO) · RTR(Remote Transmission Request) · DLC(Data Length Code) · EDS(Electronic Data Sheet) · PP(Profile Position) · PV(Profile Velocity) · PT(Profile Torque) · IP(Interpolated Position) · AGV(Automated Guided Vehicle)

## 1. 물리·링크 계층

| 항목 | 값 | 근거 |
| --- | --- | --- |
| 프로토콜 | CANopen CiA301(통신) / CiA402(모션) | ✓ [Handbook V7.0, 제품표, page 14 등](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) "Standard CanOpen Protocol CiA301/402" |
| 프레임 | Classic CAN, 11-bit identifier + 8-byte data | ✓ [Handbook V7.0, §6.2, page 136](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) |
| 지원 보드레이트 | 10/20/50/125/250/500/800/1000 kbps | ✓ [EDS DeviceInfo](../canopen/EDS_extracted/Servo_Driver_20200805.eds) `BaudRate_*=1` |
| **현장 설정** 보드레이트 | **250 kbps** (Seer AGV 실측) | ✓ 실측 — device spec 아님, 현장 설정값 |
| Node-ID | 최대 127 슬레이브 | ✓ Handbook §6.1 |
| **현장 설정** Node-ID | 1=FrontWalk, 2=RearWalk, 3=FrontSteer, 4=RearSteer | ✓ 실측+EasyDRIVE config |
| PDO 개수 | RPDO 4 / TPDO 4 | ✓ [EDS](../canopen/EDS_extracted/Servo_Driver_20200805.eds) `NrOfRXPDO=4, NrOfTXPDO=4` |
| 바이트 오더 | Little-endian | ✓ [Handbook V7.0, §6.7.2, page 157](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) |

## 2. COB-ID 할당표 (CiA301 사전 정의)

[Handbook V7.0, §6.2, page 137](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓

| 통신 객체 | COB-ID | 방향(드라이버 기준) | 관련 오브젝트 |
| --- | --- | --- | --- |
| NMT | 0x000 | 수신 | — |
| SYNC | 0x080 | 수신 | 0x1005–0x1007 |
| EMCY | 0x081 + Node-ID | 송신 | — |
| TPDO1 | 0x180 + Node-ID | 송신 | 0x1800/0x1A00 |
| RPDO1 | 0x200 + Node-ID | 수신 | 0x1400/0x1600 |
| TPDO2 | 0x280 + Node-ID | 송신 | 0x1801/0x1A01 |
| RPDO2 | 0x300 + Node-ID | 수신 | 0x1401/0x1601 |
| TPDO3 | 0x380 + Node-ID | 송신 | 0x1802/0x1A02 |
| RPDO3 | 0x400 + Node-ID | 수신 | 0x1402/0x1602 |
| TPDO4 | 0x480 + Node-ID | 송신 | 0x1803/0x1A03 |
| RPDO4 | 0x500 + Node-ID | 수신 | 0x1403/0x1603 |
| SDO (T, 응답) | 0x580 + Node-ID | 송신 | 0x1200 |
| SDO (R, 요청) | 0x600 + Node-ID | 수신 | 0x1200 |
| Heartbeat / Node Guarding | 0x700 + Node-ID | 송신(RTR 수신) | 0x1016, 0x1017, 0x100C/0x100D |

> ✓ 실측(Seer AGV): 실제 버스에서는 **SDO(0x580/0x600+N)와 Node Guarding(0x700+N)만 사용**. PDO·SYNC·EMCY·NMT Start 미관측.
>
> **⚠ 2026-07-27 감사 — 서술 완화(관측 범위 명시). 위 문장은 이력 보존을 위해 지우지 않는다.**
> 근거는 한정된 캡처 구간이다 — `tongyi-canopen-protocol-reference.md:3`「**2026-07-07~08 실측**」.
> 같은 사실을 자매 문서는 단정 대신 관측어로 적는다: `tongyi-canopen-protocol-reference.md:24`「**미관측(미사용)**」.
> 「미관측」에서 「만 사용」으로의 도약에는 별도 근거가 없다 — 전원 사이클·폴트·재호밍 등 미캡처 국면이 남아 있다
> (`docs/ros2_driver/2026-07-09-design-inputs.md:139`「0 기준점이 절대 엔코더 기준인지 미확인 — **2회 전원 사이클
> 관측뿐**」, 같은 문서 `:8-22` 는 그 캡처 자산 자체가 현재 재대조 불가라고 기록).
> ⇒ 정확한 서술: **관측 구간(2026-07-07~08 캡처)에서는 SDO·Node Guarding 만 관측. PDO·SYNC·EMCY·NMT Start 미관측
> (= '미사용' 단정 아님).**

## 3. NMT 명령표

[Handbook V7.0, §6.3, page 141](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓ — 프레임: `0x000` DLC2 `[명령][Node-ID]` (Node-ID=0 → 전체)

| Byte0 (명령) | 동작 | 비고 |
| --- | --- | --- |
| 0x01 | Start (Operational 진입) | PDO 활성화 |
| 0x02 | Stop | 노드 비활성 |
| 0x80 | Pre-Operational 진입 | SDO 만 가능 |
| 0x81 | Reset Node | 파라미터 초기화·servo OFF·알람 리셋. MODBUS 로 설정한 PDO 파라미터 소실 |
| 0x82 | Reset Communication | 통신 리셋 |

## 4. Heartbeat / Node Guarding

[Handbook V7.0, §6.4, page 141–142](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓

| 항목 | 프레임 | 상태값 |
| --- | --- | --- |
| Heartbeat (드라이버→마스터) | `0x700+N` DLC1 `[status]`, 주기 = 0x1017 (ms), 0=정지 | 0=Boot-Up, 4=Stopped, 5=Operational, 127=Pre-operational |
| Node Guarding 요청 (마스터→드라이버) | `0x700+N` **RTR** 프레임 | — |
| Guarding 응답 | `0x700+N` DLC1, 상태 + bit7 토글 | 상동 |
| 통신 두절 보호 | 0x100C GuardTime(ms) × 0x100D LifeFactor 초과 수신 없음 → HALT (모터 전원 유지) | 두 값 중 0 이면 비활성 |

> ✓ 실측(Seer AGV): 마스터가 Node Guarding RTR 을 노드당 20 Hz(50 ms)로 송신, GuardTime=500 ms·LifeFactor=1 설정. Heartbeat 방식은 미사용(부트업 0x00 1회만).

## 5. SDO 명령어 표

[Handbook V7.0, §6.7, page 156–157](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓ — 프레임(8 byte): `[cmd][idx_lo][idx_hi][sub][d0][d1][d2][d3]`, expedited(≤4 byte)

| 방향 | cmd | 의미 |
| --- | --- | --- |
| 요청 0x600+N | 0x23 | 쓰기 4 byte |
| 요청 0x600+N | 0x27 | 쓰기 3 byte |
| 요청 0x600+N | 0x2B | 쓰기 2 byte |
| 요청 0x600+N | 0x2F | 쓰기 1 byte |
| 요청 0x600+N | 0x40 | 읽기 요청 |
| 응답 0x580+N | 0x60 | 쓰기 성공 |
| 응답 0x580+N | 0x43 / 0x47 / 0x4B / 0x4F | 읽기 응답 4/3/2/1 byte |
| 응답 0x580+N | 0x80 | Abort — `[80][idx][sub][Error_Code 4B]` |

예(Handbook, node 0x0A): 쓰기 `0x60A: 2B 40 60 00 06 00 00 00` → 응답 `0x58A: 60 40 60 00 ...` / 읽기 `0x60A: 40 40 60 00 ...` → 응답 `0x58A: 4B 40 60 00 06 00 ...`

> ✓ 실측(Seer AGV): SDO 왕복 지연 평균 ~1 ms(p99 ~1.1 ms), 총 폴링 ~1600 fps.

## 6. 기본(default) PDO 매핑표

[Handbook V7.0, §6.8.3, page 160–161](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓ — 현장(Seer AGV)은 PDO 미사용이므로 참고용

| PDO | COB-ID | 크기 | 매핑 오브젝트 | 내용 |
| --- | --- | --- | --- | --- |
| RPDO1 | 0x200+N | 2 B | 0x6040 Controlword | 06=Ready to Switch On, 07=Switched On, 0F=Operation Enable, 05=Disable |
| RPDO2 | 0x300+N | 1 B | 0x6060 Mode | 1=PP, 3=PV, 4=PT, 7=IP |
| RPDO3 | 0x400+N | 6 B | 속도지령(⚠ 표기 "0x67FF" — 0x60FF 오기 추정) + 0x6071 전류지령 | 속도 0.1 rpm 단위, 전류 지령 |
| RPDO4 | 0x500+N | 8 B | 0x607A 위치지령 + 0x6081 속도 | 위치: 하위 16 bit 각도 + 상위 16 bit 회전수 |
| TPDO1 | 0x180+N | 2 B | 0x6041 Statusword | inhibit 2 ms / event 50 ms |
| TPDO2 | 0x280+N | 2 B | 0x603F Error code | inhibit 2 ms / event 50 ms |
| TPDO3 | 0x380+N | 6 B | 0x606C 속도 + 0x6078 전류 피드백 | inhibit 20 ms / event 50 ms |
| TPDO4 | 0x480+N | 8 B | 0x60FB.02 회전수 + 0x6064 각도 피드백 | inhibit 20 ms / event 50 ms |

## 7. CiA402 상태머신 — Controlword (0x6040)

[Handbook V7.0, §6.6.1, page 149–150](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓

**비트 배치**: bit0 Switch on · bit1 Enable voltage · bit2 Quick stop · bit3 Enable operation · bit4–6 모드별 · bit7 Fault reset · bit8 Halt · bit15 Reset Home(벤더 특유, 1 쓰면 호밍 기동 후 자동 클리어)

> **⚠ 정정 (2026-07-27) — bit15 서술 보강. 위 문장은 이력 보존을 위해 지우지 않는다.**
> ① 「벤더 특유(=출처 불명)」가 아니라 **핸드북 본문에 정의된 항목**이다 —
> 「Bit15: Reset Home is the motor homing activation bit … this bit will be reset automatically」,
> 같은 문단이 Statusword bit15 연동(호밍 중 0 / 완료 시 1)까지 명시한다.
> [IxLII/IxLs/IxH Servo Driver Handbook V7.0 §6.6.1, page 149]
> ② **호밍 트리거는 두 경로**다 — `0x6040` bit15 **또는** `0x60FB.04`(RstStart).
> 현장(Seer)은 **후자만** 쓴다: 실기 캡처 180 s·253,510 프레임 전 구간에서 조향 Controlword 는
> `0x3F` 6,464회 · `0x86` 2회뿐이고 `0x800F` 는 **0회**다 (`Log/homing_capture_220350.jsonl`).
> ⇒ 재현 구현은 §10 「호밍」 표의 `0x60FB.04` 경로를 따를 것.

| 명령 | bit7 | bit3 | bit2 | bit1 | bit0 | 대표값 |
| --- | --- | --- | --- | --- | --- | --- |
| Shutdown | 0 | * | 1 | 1 | 0 | 0x0006 |
| Switch On | 0 | 0 | 1 | 1 | 1 | 0x0007 |
| Enable Operation | 0 | 1 | 1 | 1 | 1 | 0x000F |
| Disable Voltage | 0 | * | * | 0 | * | 0x0000 |
| Quick Stop | 0 | * | 0 | 1 | * | 0x0002 |
| Disable Operation | 0 | 0 | 1 | 1 | 1 | 0x0007 |
| Fault Reset | ↑상승엣지 | * | * | * | * | 0x0080 |

**지령값 사전** ([Handbook V7.0, Appendix I 0x6040, page 194](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓):

| 값 | 의미 |
| --- | --- |
| 0x0006 | Ready to switch on |
| 0x0007 | Switch on |
| 0x000F | Operation enable (servo ON, 모터 통전) |
| 0x0005 | servo enable 해제(모터 전원 차단) |
| 0x0002 | Quick stop |
| 0x010F | Halt |
| 0x001F→0x000F | 절대위치 지연 실행 |
| 0x003F→0x000F | 절대위치 즉시 실행 |
| 0x005F→0x004F | 상대위치 지연 실행 |
| 0x007F→0x004F | 상대위치 즉시 실행 |
| 0x800F | 호밍 시작(bit15 Reset Home, 자동 클리어) <br> ⚠ 정정 (2026-07-27): **현장 미사용** — Seer 는 `0x60FB.04=1`(RstStart) 경로로 호밍을 개시한다. 실기 캡처 253,510 프레임 전 구간 `0x800F` **0회**(조향 Controlword 는 `0x3F` 6,464회·`0x86` 2회뿐) [`Log/homing_capture_220350.jsonl`] |
| 0x0080 | 알람 클리어 |

**모드별 bit4–6/8** (§6.6.1):

| bit | Velocity | PP(위치) | PV | PT |
| --- | --- | --- | --- | --- |
| 4 | Rfg enable | New set-point | 예약 | 예약 |
| 5 | Rfg unlock | Change set immediately | 예약 | 예약 |
| 6 | Rfg use ref | 1=상대/0=절대 | 예약 | 예약 |
| 8 | Halt | Halt | Halt | Halt |

> ✓ 실측(Seer AGV): 마스터는 표준 시퀀스(06→07→0F) 대신 **0x86**(fault reset+enable, 구동축 기동 1회)·**0x3F**(신규 setpoint+즉시, 조향축)만 사용 — CiA402 상태머신 엄격 미준수(벤더 허용 동작).
>
> **⚠ 2026-07-27 감사 — 「0x86 = 구동축 기동 1회」한정은 반증됐다(값 변경 없음, 서술만 정정).**
> 같은 기동 캡처의 전수 디코드는 **조향축(N3·4)에도 `0x6040=0x86`** 이 두 번 기록됐음을 보인다 —
> `docs/ros2_driver/2026-07-09-design-inputs.md:80`「조향축 1차(t≈45.7s): **`0x6040=0x86`** → `0x6099=2500` → …」,
> `:81`「조향축 2차(t≈76.8s): **`0x6040=0x86`** → `0x100D=1` → …」.
> 재현 구현도 조향 노드에 0x86 을 보낸다 — `src/Actuators/motor_control/motor_control/backend.py:264-265`.
> ⇒ 정정: **0x86 은 구동축 1회 + 조향축 2회(t≈45.7 s·t≈76.8 s)** 기록. `0x3F`가 조향 setpoint 용이라는 부분은 유지.
> (이 한정 서술이 정상 코드를 결함으로 오지적한 이력:
> `docs/code_review/motor_control-can-consistency/2026-07-26.md:70-74` → `:76` 에서 「전제는 반증됨」으로 정정.)
> ※ 근거 캡처 자산은 현재 재대조 불가 상태이므로(design-inputs.md:8-22) 위 정정도 원 세션 기록에 근거한다.
>
> **⚠⚠ 재정정 (2026-07-27) — 재대조 가능한 실기 캡처 확보. 위 정정의 횟수 한정도 반증됐다.**
> `Log/homing_capture_220350.jsonl`(180 s / 253,510 프레임) 전수 디코드 결과:
> · **구동축 `0x6040=0x86` = 노드당 106회 반복**(≈8 Hz, t=5.343~17.883) — 「구동축 1회」는 미성립.
> · **조향축 `0x6040=0x86` = 노드당 2회**로 확인되며, 그 2회의 의미는 **호밍 개시 직전(t=17.910/17.911)** 과
>   **호밍 완료 직후(t=49.003/49.084)** 다.
> · 위 인용의 「조향축 1차 / 2차」는 **별개 시퀀스가 아니라 하나의 호밍 상태머신의 두 지점**이다 —
>   1차 = `0x86` → `0x6099=2500` → `0x60FB.04=1`(호밍 개시), 그 사이 ≈31 s 는 **드라이브가 원점을 탐색하는 구간**,
>   2차 = 완료 후 PP 설정 + `0x607A`(조향 0° 복귀). 상세는 §10 「호밍」 정정표 참조.
> · `0x3F`(6,464회)가 조향 setpoint 용이라는 부분은 유지되나, **호밍 구간(t=17.96~49.14) 동안은 완전히 중단**된다.

## 8. Statusword (0x6041)

[Handbook V7.0, §6.6.2, page 150–151](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓

| bit | 의미 | | bit | 의미 |
| --- | --- | --- | --- | --- |
| 0 | Ready to switch on | | 7 | Warning |
| 1 | Switched on | | 9 | Remote |
| 2 | Operation enabled | | 10 | Target reached |
| 3 | Fault | | 11 | Internal limit active |
| 4 | Voltage enabled | | 12–13 | 모드별 (PV: bit12 Speed=0) |
| 5 | Quick stop | | 14 | 예약(Appendix I: Battery alarm) |
| 6 | Switch on disabled | | 15 | Home attained (호밍 완료=1) |

**상태 판정** (bit0–3, 5, 6 조합):

| 패턴(Bin) | 상태 |
| --- | --- |
| *0** 0000 | Not ready to switch on |
| *1** 0000 | Switch on disabled |
| *01* 0001 | Ready to switch on |
| *01* 0011 | Switched on |
| *01* 0111 | Operation enabled |
| *00* 0111 | Quick stop active |
| *0** 1111 | Fault reaction active |
| *0** 1000 | Fault |

> ⚠ 실측 편차: 운전 중에도 bit6(Switch on disabled)=1 관측(실측 정지값 0x8050/0x9450) — 비표준 Controlword 사용의 결과로 추정. 상태 판정표를 그대로 신뢰하지 말 것.

## 9. 운전 모드 (0x6060 / 0x6061)

[Handbook V7.0, §6.6.3, page 152](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓

| 값 | 모드 | 지령 오브젝트 |
| --- | --- | --- |
| 1 | Profiled Position (PP) | 0x607A + 0x6081 |
| 3 | Profiled Velocity (PV) | 0x60FF |
| 4 | Profiled Torque (PT) | 0x6071 |
| 7 | Interpolated Position (IP) | 0x60C1 |
| 8 | Cyclic Synchronous Position (CSP) | 0x607A (+0x60B0) |
| 9 | Cyclic Synchronous Velocity (CSV) | 0x60FF (+0x60B1) |
| 10 | Cyclic Synchronous Torque (CST) | 0x6071 (+0x60B2) |

> ✓ 실측(Seer AGV): 구동축(N1·2)=3(PV). 조향축(N3·4)은 위치 제어(0x607A 사용, 0x3F controlword).

## 10. 주요 오브젝트 딕셔너리 (단위 포함)

[Handbook V7.0, Appendix I, page 194–197](../manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) ✓ (Seer AGV 실측 사용 오브젝트는 **굵게**)

### 지령 (RW)

| Index | 이름 | 타입 | 단위·의미 |
| --- | --- | --- | --- |
| **0x6040** | Controlword | UINT16 | §7 참조 |
| **0x6060** | Modes_of_operation | INT8 | §9 참조 |
| **0x60FF** | Target_velocity (PV) | INT32 | **0.1 r/min** |
| **0x607A** | Target_position (PP) | INT32 | 65536 counts = 모터 1회전 (예 0x18000=1.5회전) |
| 0x6071 | Target_torque(전류지령) | INT16 | 0.01 A |
| **0x6081** | Profile_velocity (PP 속도) | INT32 | 0.1 r/min |
| **0x6083** | Profile_acceleration | UINT32 | ms/krpm |
| **0x6084** | Profile_deceleration | UINT32 | ms/krpm |
| 0x6073 | Max_Current | UINT16 | 0.01 A (rms) |
| 0x60B0/B1/B2 | Position/Velocity/Torque offset (CS 모드) | INT32/INT32/INT16 | —/0.1 rpm/0.01 A |

### 피드백 (RO)

| Index | 이름 | 타입 | 단위·의미 |
| --- | --- | --- | --- |
| **0x6041** | Statusword | UINT16 | §8 참조 |
| **0x603F** | Error_code | UINT16 | §6.6.4 폴트표 (0x0001 DCBUS 과전압, 0x0002 저전압, 0x0004 과전류, 0x0008 엔코더 …) |
| **0x6064** | Position_actual (각도) | INT32 | 상위 16 bit 회전수 + 하위 16 bit 각도(65536=1회전) |
| 0x606C | Velocity_actual | INT32 | 0.1 r/min |
| **0x6078** | Current_actual | INT16 | **0.01 A** (Appendix I 명기 — 실측 미확정이던 단위의 1차 source 값) |
| 0x6079 | DC_link_voltage | UINT32 | 0.001 V |
| 0x60FB.02 | Position_actual_Turn(회전수) | INT32 | 회전수 피드백 |
| **0x6000** | Digital_Input | ~~UINT32~~ → **ARRAY, 실입력값은 `sub 1` = UINT8** | ~~bit0 Servo Enable, bit1 +Limit, bit2 Alarm, bit3 −Limit~~ <br> ⚠ 정정 (2026-07-27): ① `0x6000` 은 **배열 오브젝트**다 — `sub 0` = 항목 수(=2), 실제 입력 상태는 **`sub 1`**. 타입은 UINT32 가 아니라 **UINT8**(캡처 응답이 전부 `cmd=0x4F` 1바이트 expedited). 위 UINT32 는 핸드북 ARRAY 헤더 행 표기를 그대로 옮긴 것. ② 비트: **bit0 Servo Enable(DI1)** · bit1 +Limit(DI2 POT, 정방향 구동금지) · **bit2 = Alarm _clearing_ 입력(DI3)의 상태 — 「알람 발생」이 아니다** · **bit3 −Limit(DI4 NOT, 역방향 구동금지)** · bit4 Origin signal(DI5). [Handbook V7.0 Appendix I, page 199(인쇄 197)] + [같은 문서 Appendix II `0x4651 sysWKS.uwDigitalInputs`, page 208(인쇄 206)] ③ ✓ **실측으로 확정된 비트는 bit0·bit3** — 조향 노드(N3·4)에서 `0x01`→`0x09`(t=47.0249/47.0254, 음의 리밋 물림) → `0x01`(t=49.4223/49.4227, 0° 복귀 중 해제), 구동 노드(N1·2)는 전 구간 `0x01` 무변화 [`Log/homing_capture_220350.jsonl`] ④ ⚠ POT/NOT 액티브 레벨은 핸드북 미기술 · 핸드북의 default `0xBF` 는 실측 유휴값 `0x01` 과 불일치(미해소) |
| 0x2300/0x2301 | 드라이버/모터 온도 | UINT | 제조사 특유 영역 |

### 호밍

| Index | 이름 | 단위 |
| --- | --- | --- |
| 0x6098 | Homing method | 1–35 (0=off) |
| **0x6099** | Homing speeds | 0.1 r/min |
| 0x607C | Homing offset | 65536 = 1회전 |
| 0x609A | Homing acceleration | ms |

> ### ⚠ 정정·보강 (2026-07-27) — 위 표는 이력 보존을 위해 지우지 않는다. 정본은 아래 표다.
>
> 위 표는 (a) `0x6098` 범위가 틀렸고, (b) 호밍을 실제로 **개시**하는 `0x60FB.04` 와 **완료 판정** `0x6041` bit15 가
> 빠져 있어 이 표만으로는 호밍을 재현할 수 없었다.
>
> **(1) `0x6098` 범위는 1–37 (0=off)** — [Handbook V7.0 §6.9, page 173(인쇄 171)] 「0-Home off, 1-37 Home 1-37」.
> 위 「1–35」는 같은 핸드북 Appendix I(page 199) 표기로, **핸드북 자체가 두 곳에서 상이**하다(⚠ 판본 충돌, 미해소).
>
> **(2) ✓ 이 로봇의 `0x6098` 저장값은 전 노드 = 1 = Home 1(음(−)의 리밋 트리거)** — 2026-07-27 드라이브 파라미터
> 직접 판독으로 확정. Handbook 기본 RstMode 도 1 [§4.6 page 116]. ⇒ 조향축에는 **리밋 스위치가 실재**하며,
> 「리밋 스위치 없음 / Home 36·37 기계 하드스톱」류 추정은 **오류**다.
>
> **(3) ⚠ `0x6098` 을 쓰지 말 것** — Seer 도 우리도 캡처 전 구간에서 `0x6098` 을 **write·read 모두 0회**로 다루고
> 드라이브 저장값을 그대로 쓴다. Home 35 등을 써 넣으면 `RstMode` 가 0(호밍 꺼짐)으로 리셋되어
> [§4.6 page 122] **Seer 호밍이 죽는다**.
>
> | Index | 이름 | 단위·의미 | 현장(Seer) 실측 |
> | --- | --- | --- | --- |
> | 0x6098 | Homing method | §6.9 표기 **1–37** / Appendix I 표기 1–35 (0=off). 벤더 대응 파라미터 `uwRstMode`, 기본값 1 = Home 1(음의 리밋이 원점) [§4.6 page 116] | **write·read 모두 0회** → 드라이브 저장값 사용. 판독 결과 **전 노드 = 1** |
> | **0x6099** | Homing speeds | 0.1 r/min (기본 1000 = 100 rpm) | **2500**(= 250 rpm) 1회, t=17.9183/17.9190 |
> | 0x607C | Homing offset | 65536 = 1회전 | **미기록** |
> | 0x609A | Homing acceleration | ms | **미기록** |
> | **0x60FB.04** | **RstStart — 호밍 개시 트리거** (0 = Reset off, 1 = Reset on) [Handbook V7.0 §6.9, page 171 표 1행; Appendix I page 196] | ⚠ **모터를 물리적으로 움직이는 쓰기** | **1** 1회, t=17.9252(N3)/17.9257(N4) |
> | 0x6041 bit15 | Home attained | 호밍 중 0 / 완료 1 | 0 최초 관측 t=17.9562/17.9567 (⚠ 전이 확정 구간 (5.138, 17.956]) → 0→1 t=48.9993(N4)/49.0795(N3) |
> | 0x6000.01 bit3 | Negative Limit = **Home 1 의 원점 신호** | 1 = 트리거(리밋 물림) | 0→1 t=47.0249/47.0254 → 1→0 t=49.4223/49.4227 |
>
> **✓ 실측 호밍 시퀀스** (`Log/homing_capture_220350.jsonl`, 180 s / 253,510 프레임, 조향 N3·N4 만):
> `0x6040=0x86`(t=17.910/17.911) → `0x6099=2500` → `0x60FB.04=1`(t=17.925) → **원점 탐색 ≈29.1 s**
> → 리밋 물림 `0x6000.01 = 0x01→0x09`(t=47.025) → 완료 `0x6041` bit15 0→1(t≈49.0)
> → `0x6060=1`(PP, t=49.033/49.113) → `0x6081=30000` / `0x6083=250` / `0x6084=250`
> → `0x607A=조향 0° 위치` + `0x6040=0x3F`(t=49.140/49.142) → **≈3.5 s 만에 수렴**(t≈52.67).
> 개시→완료 총 ≈31.1 s (§4.6 타임아웃 120 s 이내).
>
> **✓ 호밍은 「원점 경유 → 조향 0° 복귀」까지가 1 사이클**이다 — 원점(리밋)에 머무는 것이 아니다.
> 리밋에 얹힌 채 두면 그 방향 지령이 막히며, 실측에서도 리밋 비트는 0° 복귀 이동 중(t=49.42) 해제된다.
> 복귀 목표(= 조향 0° 자세의 엔코더 카운트)는 **N3 7,882,020 / N4 7,859,062 counts**
> (= +137.451° / +137.051° @57,344 counts/°, EasyDRIVE `steerOffset` 138.000 / 137.250 대응).
>
> **✓ 구동축(N1·2)은 호밍하지 않는다** — Seer 는 조향 노드에만 호밍 프레임을 보냈고, 구동륜에는 기계적 원점이 없다.
>
> ⚠ 핸드북은 「Home 1/2 는 PP 모드에서만 유효」[§4.6 page 116]라고 적지만, **실측 Seer 는 호밍 개시 전에 `0x6060` 을
> 쓰지 않는다**(조향 `0x6060=1` 은 t=49.03/49.11 = 호밍 **완료 후** 1회). 이 불일치는 미해소이므로,
> 재현 구현이 `0x6060=1` 을 선행 설정하는 것은 「Seer 재현」이 아니라 **핸드북 요구를 추가로 만족시킨 변형**이다.

### 통신 설정

| Index | 이름 | 의미 |
| --- | --- | --- |
| **0x100C / 0x100D** | Guard Time (ms) / Life Time Factor | Node Guarding 두절 판정 |
| 0x1017 | Producer Heartbeat Time (ms) | 0=중지 |
| 0x1400–0x1403 / 0x1600–0x1603 | RPDO 통신/매핑 | 전송타입 초기값 255 |
| 0x1800–0x1803 / 0x1A00–0x1A03 | TPDO 통신/매핑 | inhibit 단위 100 µs, event 단위 ms |
| 0x1008/0x1009/0x100A | 제조사 ID | "TYA" / "IXL" / "C09" |

## 11. 현장(Seer AGV) 실측 프로파일 요약 ~~✓ 실측~~ → **✓ 관측(2026-07-07~08 캡처 범위) · ⚠ 기동 행은 조건 누락**

세부는 [tongyi-canopen-protocol-reference.md](tongyi-canopen-protocol-reference.md) 참조.

| 항목 | 값 |
| --- | --- |
| 제어 방식 | 전량 SDO 폴링 (PDO·SYNC·EMCY·NMT Start 미사용, Pre-operational 유지) |
| 노드 | 1·2 구동(PV), 3·4 조향(위치) |
| 폴링 | Position 210 Hz, 지령 96 Hz, 진단 5 Hz, 총 ~1600 fps (버스부하 ~75 %) |
| Controlword 관례 | ~~0x86(구동 enable, 1회)~~ / 0x3F(조향 setpoint) — 비표준 <br> ⚠ 정정: 0x86 은 조향축에도 2회 기록(§7 감사 주석) <br> ⚠ **재정정 (2026-07-27, 전수 디코드)**: 「1회」한정은 **미성립** — 구동축 `0x6040=0x86` 은 **노드당 106회 반복**(≈8 Hz, t=5.343~17.883). 조향축 `0x86` 은 **2회**로 각각 **호밍 개시 직전(t=17.910/17.911)** 과 **호밍 완료 직후(t=49.003/49.084)**. 조향 `0x3F`(6,464회)는 호밍 구간(t=17.96~49.14) 동안 **완전히 중단**된다. [`Log/homing_capture_220350.jsonl`, 253,510 프레임] |
| 스케일(조향) | 57,344 counts/°, 홈↔90° = ±5,160,960 (reduction 315) |
| 스케일(구동) | 0.1 rpm 지령, ±24447 = ±1.0 m/s (reduction 32, wheel r=0.125 m) |
| 기동 | 부트업(0x700+N=0x00) → ~45 s → 0x6040=0x86 → guard/profile 설정 → 폴링 <br> ⚠ **누락 단계 있음 — 아래 감사 주석 필독(기동만으로 바퀴가 물리적으로 돈다)** |

> ### ⚠⚠ 2026-07-27 감사 — 위 「기동」행은 **폴링으로 끝나지 않는다**(값·시퀀스는 변경하지 않고 누락 단계를 append)
>
> 같은 기동 캡처의 전수 디코드는 guard/profile 설정 뒤에 **조향축 위치 지령 단계**가 있고 그 결과 바퀴가 물리적으로
> 움직인다고 기록한다 — `docs/ros2_driver/2026-07-09-design-inputs.md:81`「조향축 2차(t≈76.8 s): … `0x6060=1`(PP)
> → `0x6081=30000` → `0x6083=250` → `0x6084=250` → **`0x607A=홈상수(7,871,815/7,840,086)` + `0x6040=0x3F` 48 Hz 반복**」,
> `:82`「조향이 **0에서 홈까지 3.3 s 물리 스윙**」.
> ⇒ 기동 행의 정확한 끝단: **… → 조향축 `0x607A`=홈상수 기록 + `0x6040=0x3F` 48 Hz → 0→홈 약 **+137°** 물리 스윙(3.3 s)
> → 폴링**.
>
> **⚠ 안전: 브링업만으로 조향 바퀴가 약 137° 회전한다 — 주변 확보 필수**
> (`docs/ros2_driver/2026-07-09-design-inputs.md:114`「**137° 물리 스윙 발생 — 주변 확보 필수**」).
> 각도 표기 조건: 원문의 「+137.3° = config steerOffset」은 같은 문서 `:92-97` 이 등치·소수 정밀도 모두 근거 없음으로
> 정정했고, 57,344 counts/° 환산 시 **N3 = +137.28° / N4 = +136.73°** 로 두 축이 0.55° 다르다.
> 미검증 절대위치 지령 뒤 실피해 이력: `docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md:19-20`
> (node4 가 137° 로 밀려 물리적 갇힘). 0→홈 이동은 단발 절대 점프 금지, 단계 램프로만(design-inputs.md:120-124).
> ※ 사건은 기록됐으나 「급점프/범위이탈이 원인」이라는 인과는 같은 기록 `:106` 이 **미확정 가설**로 표시한다.
> 홈 상수 자체는 미판정 모순 상태이므로 무비판 신뢰 금지(`docs/verified_facts/2026-07-27.md:185-213` §B-1,
> `src/Actuators/motor_control/config/tongyi_amr.yaml:91` debt-007).
> ※ 근거 캡처 자산은 현재 재대조 불가(design-inputs.md:8-22) — 위 보완도 원 세션 기록에 근거한다.
>
> ### ⚠⚠ 재정정 (2026-07-27 실기 검증) — 위 감사 주석의 전제 3개가 반증됐다. 위 문단은 이력 보존을 위해 지우지 않는다.
>
> 근거: `Log/homing_capture_220350.jsonl`(Seer 주도 호밍, 180 s / 253,510 프레임) 전수 디코드 + 드라이브 파라미터 직접 판독.
>
> **① 「137° 물리 스윙」은 원인 미상의 이상거동이 아니라 호밍의 설계된 마지막 단계다.**
> 기동 행의 실제 끝단은 「… → 폴링」도, 「… → 홈상수 스윙 → 폴링」도 아니고
> **`0x6040=0x86` → `0x6099=2500` → `0x60FB.04=1`(호밍 개시) → 원점(음의 리밋) 탐색 ≈29 s
> → `0x6041` bit15 0→1(완료) → PP 설정 → `0x607A`(조향 0° 자세) + `0x6040=0x3F` → ≈3.5 s 복귀 → 폴링** 이다.
> 즉 그 회전은 **원점(리밋)에서 조향 0° 로 돌아오는 복귀 이동**이다. 상세·타임스탬프는 §10 「호밍」 정정표 참조.
> ⇒ 「이상 스윙」·「Home 36/37 기계 하드스톱」·「리밋 스위치 없음」류 서술은 **전부 오류**다 —
> 전 노드 `0x6098 = 1`(Home 1, 음의 리밋 트리거) 실기 판독 확정, 리밋 스위치는 **실재**한다.
>
> **② 각도 「N3 +137.28° / N4 +136.73°, 두 축 0.55° 차」는 호밍 _이전_ 값에서 나온 수치다.**
> 그 값은 호밍 전 구간의 `0x607A`(7,871,815 / 7,840,086)를 환산한 것이다. **호밍 후 정착 목표**는
> **N3 7,882,020 / N4 7,859,062 counts = +137.451° / +137.051°**(리드백 7,882,001 / 7,859,058~065,
> t=49.140 지령 → t≈52.67 수렴)이고 **두 축 차는 0.40°** 다.
> EasyDRIVE `steerOffset` 138.000(N3) / 137.250(N4) 와 대응한다.
>
> **③ 「홈 상수 자체는 미판정 모순 상태」는 해소됐다** — 두 값은 모순이 아니라 **호밍 전 / 호밍 후**로 국면이 다르다.
> 정본은 **호밍 후 정착값**(위 ②)이다. 다만 하드코딩 금지 원칙과 debt-007 의 리드백 정본화 지침은 그대로 유효하다.
>
> **⚠ 안전 서술은 그대로 유효**: 브링업만으로 조향 바퀴가 약 137° 회전한다 — 주변 확보 필수.
> 정상 거동임이 확인됐다고 해서 무인 기동을 허용하는 근거가 되지는 않는다.
> `0x60FB.04=1` 은 **모터를 물리적으로 움직이는 쓰기**이므로 무심코 재현하지 말 것.

## 12. 미확정(⚠) 항목

| 항목 | 상태 |
| --- | --- |
| RPDO3 속도지령 인덱스 "0x67FF" | ⚠ Handbook page 160 원문 표기 — 0x60FF 의 오기로 추정, PDO 실사용 시 EDS/실기로 확인 필요 |
| 0x6075 | ⚠ Appendix I 에 "Motor_rate_current, 전류 지령 가감속, 단위 ms" 로 기재 — CiA402 표준명(Motor rated current)과 상이, 확인 필요 |
| 실측 Statusword bit6 편차 | ⚠ 원인 미확정 (§8 참조) |
| ~~조향 절대원점 대응, 단일 노드 dropout 거동, Seer SDO 타임아웃~~ | ~~⚠ 실측 미완~~ → **분리(2026-07-27): 조향 절대원점만 해소, 아래 두 행 참조** |
| 조향 절대원점 대응 | ✓ **해소 (2026-07-27 실기 호밍 캡처)** — 원점 = **음(−)의 리밋 스위치**(`0x6098` 전 노드 = 1 = Home 1, 실기 판독). 호밍 중 `0x6064` = 0. 호밍 완료 후 **조향 0° 자세** = 지령 **N3 7,882,020 / N4 7,859,062 counts**(리드백 7,882,001 / 7,859,058~065) = **+137.451° / +137.051°** @57,344 counts/° ≈ EasyDRIVE `steerOffset` 138.000 / 137.250. 근거 `Log/homing_capture_220350.jsonl`(t=47.025 리밋 물림 → t≈49.0 완료 → t=49.140 복귀 지령 → t≈52.67 수렴). ⚠ 잔여: Seer 1040 `encoder` 부호(−) 미확정 |
| 단일 노드 dropout 거동, Seer SDO 타임아웃 | ⚠ 실측 미완 |
