# SEER SRC — CAN/모터드라이버 통신 에러·설정 변수 (web 추출)

> 수집일: 2026-07-26 (KST, sess:e717f1dd) · 사용자 지시: "GitHub에 CAN timing/모터 제어기 관련 자료 없으면 web에서 추출", "보통 CAN 통신엔 통신 설정 오류·관련 변수가 있는 게 정상"
> 방법: ① GitHub 공식 SDK/PDF(`robotkit-netprotocol-l-1.2.1`) 검사 → CAN 설정 없음 확인 ② **Feishu wiki(guest, computer-use) ModbusTCP 레지스터 맵 직접 판독** + PDF 알람코드표
> 검증 등급: ✓ = 공식 원문(PDF/Feishu 화면) 직접 확인 / ⚠ = 미노출·추정
> 관련: [[robokit_tcp_api]](TCP/IP API 정본) · [[sources]] · [[biguamr-motor-control-port]]

## 0. 결론 요약

| 사용자가 찾던 것 | 존재? | 어디에 |
|---|---|---|
| CAN **통신 에러 변수**(드라이버 연결 끊김 등) | **✓ 있음** | 알람코드 52111/52116~52118, ModbusTCP 에러코드 레지스터 00031~00033 |
| 모터 **고장 에러 변수**(과전압/과전류/과열/과속) | **✓ 있음** | 알람코드 52130~52135, 54003~54004 |
| CAN **timing/설정**(baud·Node-ID·heartbeat·PDO·error-counter) | **✗ 외부 API 미노출** | SRC 내부(RoboShop 전용), 로그인 게이트 헬프센터에만 존재(⚠) |

→ **"통신 설정 오류·관련 변수는 정상적으로 존재"** 라는 사용자 판단이 맞음. 단, 그 변수는 **CAN 버스 raw 설정(baud/node)** 이 아니라 **상위 "연결 상태/고장" 알람코드 + 에러코드 레지스터** 형태로 노출됨. raw CAN 타이밍 설정은 외부 프로토콜(TCP/IP·Modbus) 어디에도 없음.

## 1. GitHub SDK 검사 결과 (CAN 설정 부재 확정) ✓

- `netprotocol/rbkNetProtoEnums.py`, 데모, 공식 PDF v1.2.1 전수 grep: **CAN/baud/node/PDO/CANopen 설정 항목 0건**.
- PDF 부록 C "机器人参数配置指南"(파라미터 설정 가이드)의 플러그인 = LaserObstacleDetection·MCLoc·MoveFactory·NetProtocol·XBox360Joystick **뿐 → CAN/모터드라이버 통신 플러그인 없음**.
- 즉 SRC↔모터드라이버 CAN 링크의 baud/Node-ID/heartbeat/PDO 는 **외부 API 로 조회·설정 불가**(RoboShop 내부 설정). 이는 [[sources]] §1-1 의 미확정 항목과 일치.

## 2. 통신·모터 알람코드 (PDF 부록A 机器人告警码) ✓

TCP API `1050 robot_status_alarm_req`(port 19204) 또는 ModbusTCP 에러코드 레지스터(§3)로 읽는 코드. **통신(comm) 관련이 굵게**.

### Fatal/Error 급 (52xxx)
| 코드 | 이름 | 설명(원문) | 분류 |
|---|---|---|---|
| 52100 | laser error | 失去与激光设备的通讯 (레이저 장비 통신 상실) | **통신** |
| 52101 | laser data invalid | 모든 레이저 데이터 무효 | 센서 |
| 52110 | imu error | 자이로 오류 | 센서 |
| **52111** | **motor driver connection error** | **驱动器连接故障 (드라이버 연결 고장 = CAN 링크)** | **통신/모터** |
| 52112 | ultrasonic error | 초음파 레이더 고장 | 센서 |
| 52113 | RFID reader error | RFID 읽기 고장 | 센서 |
| 52114/52115 | magnetic 0/1 tracker error | 자기 트랙 센서 고장 | 센서 |
| **52116** | **controller net down** | **控制器网络断开 (컨트롤러 네트워크 단절)** | **통신** |
| **52117** | **controller link down** | **控制器连接断开 (컨트롤러 연결 단절)** | **통신** |
| **52118** | **subsystem error** | **子系统连接故障 (서브시스템 연결 고장)** | **통신** |
| **52119** | **low task frequency** | **单片机任务频率过低 (MCU 태스크 주파수 저하)** | 실시간성 |
| 52130 | motor GVDD over voltage | 电机GVDD过压 | 모터 |
| 52131 | motor FET over current | 电机桥臂过流 | 모터 |
| 52132 | motor over temperature | 电机驱动器过热 | 모터 |
| 52133 | motor VDD under voltage | 电机电源欠压 | 모터 |
| 52135 | motor error see log | 电机其他(로그 확인) | 모터 |
| 52200~52210 | (내비/경로 실패군) | bezier/target/patrol 등 | 내비 |
| 52300 | too low confidence of localization | 측위 신뢰도 저하 | 측위 |

### Warning 급 (54xxx)
| 코드 | 이름 | 설명 | 분류 |
|---|---|---|---|
| 54000 | joystick error | 手柄连接出错 (조이스틱 연결 오류) | 통신 |
| **54001** | **battery error** | **电池通讯出错 (배터리 통신 오류)** | **통신** |
| 54002 | temperature sensor error | 温度传感器出错 | 센서 |
| 54003 | motor over speed | 电机超速 | 모터 |
| 54004 | motor emergency stop | 电机被拍急停 | 모터 |

> ⚠ 목록은 PDF v1.2.1 발췌(52301 이하 "…" 로 생략). 전체 최신본은 Feishu wiki 부록/헬프센터 참조.

## 2-1. TCP API 1050 (alarm) 응답 구조 ✓ (PDF §2.2.18)

- 요청 `1050 robot_status_alarm_req` (port **19204**, JSON 데이터부 없음) → 응답 `11050 robot_status_alarm_res`.
- 응답 JSON: `fatals` / `errors` / `warnings` 각각 **array[object]**, `ret_code`, `err_msg`.
- object 포맷 = `{"<알람코드>": <타임스탬프>}` — key=알람코드, value=**해당 알람 발생 시각(1970-01-01 08:00:00 기준 경과 초, 즉 epoch@UTC+8)**.
```json
// 11050 응답 예 (PDF 원문): 52118=서브시스템 연결고장(통신), 54003=모터 과속
{ "fatals":  [{"50000":1497698400}],
  "errors":  [{"52201":1497698402},{"52118":1497698404}],
  "warnings":[{"54003":1497698405}] }
```
> `1100 all1` 배치 조회에 1050 포함 → 위치·속도·IO 등과 한 번에 alarm 획득 가능.

## 3. ModbusTCP 레지스터로 읽는 통신·모터 에러 변수 ✓

출처: Feishu wiki **ModbusTcp API → Read-only register [3x] / Read-only Status Variable [1x]** (Modified 2025-11-19), computer-use 화면 직접 판독.
> **주소 규칙(중요)**: 문서 주소는 **00001 부터** 시작 → 실제 ModbusTCP 요청 시 **주소 −1** 필요. 32bit(float32)는 2 레지스터 연속.

### 3-1. Input Register [3x] — 에러코드·헬스 수치 (uint16/float32)
| Function | Type | Addr(문서) | Unit | 비고 |
|---|---|---|---|---|
| **Fatal Error Code** | uint16 | **00031** | — | 현재 Fatal 코드(0=없음, 복수면 첫 코드) |
| **Error Error Code** | uint16 | **00032** | — | 현재 Error 코드(0=없음) |
| **Error Error Code Collection** | uint16 | **00120~00125** | — | Error 코드 최대 6개 동시 노출 |
| **Warning Error Code** | uint16 | **00033** | — | 현재 Warning 코드(0=없음) |
| Battery Current | float32 | 00019,00020 | A | |
| **Controller Temperature** | float32 | 00021,00022 | ℃ | 컨트롤러 발열(통신/모터 부하 진단) |
| Controller humidity | float32 | 00023,00024 | 0~100 | |
| **Controller Voltage** | float32 | 00025,00026 | V | |
| Total Mileage | float32 | 00027,00028 | m | 누적 주행 |
| Cumulative operating time | float32 | 00029,00030 | h | 누적 가동 |
| Robot X/Y/angle | float32 | 00001~00006 | m/rad | 위치 |
| Robot Positioning Status | uint16 | 00008 | — | 0=실패,1=정상,2=재측위,3=완료 |
| Current/Prev/Next station | int16 | 00034/00035/00036 | — | 사이트 id |

→ **00031(Fatal)/00032(Error)/00120~00125(Error set)/00033(Warning) 레지스터를 폴링하면 §2 의 52111(드라이버 연결)·52116~52118(네트워크/링크 단절)·5213x(모터 고장) 코드가 그대로 읽힘.** 이것이 사용자가 말한 "CAN 통신 에러 변수".

### 3-2. Discrete Input [1x] — 상태 플래그 (bit)
| Function | Addr | 의미 |
|---|---|---|
| Whether to decelerate | 00001 | 0=감속안함,1=감속 |
| Is it blocked? | 00002 | 0=비차단,1=차단 |
| Is it charging? | 00003 | 0=비충전,1=충전 |
| **Is it an emergency stop?** | **00004** | 0=정상,1=급정지 |
| Whether to brake | 00005 | 0=해제,1=제동(브레이크 장착 로봇만) |
| **Is there a Fatal?** | **00008** | 0=없음,1=있음 |
| **Is there an Error?** | **00009** | 0=없음,1=있음 |
| **Is there a Warning?** | **00010** | 0=없음,1=있음 |
| (jacking/roller emergency stop) | 00012/00015 | 0=정상,1=급정지 |
| DI 0~N | 00020~ | 물리 디지털 입력 0=Low,1=High |

→ 00008/00009/00010 = Fatal/Error/Warning **존재 플래그**(빠른 폴링용), 상세 코드는 §3-1 Input Register.

## 4. 미노출·추가 확인 대상 (정직한 한계)

- ✗ **CAN raw 타이밍/설정**(baud rate, Node-ID, SYNC/heartbeat 주기, PDO 매핑, bus-off/error counter): SEER **외부 API(TCP/IP·ModbusTCP) 어디에도 없음**. SRC↔드라이버 CAN 은 SRC 펌웨어 내부에서 RoboShop 로 설정, 외부 조회 불가.
- ⚠ 이 raw CAN 설정을 얻으려면: ① SEER 헬프센터 SRC User Guide "모터 드라이버 연동"(docs/books.seer-group.com, 로그인 게이트) ② **Seer↔Tongyi 구간 실버스 CAN 캡처**([[sources]] §5-3, 최종 확정 수단) ③ SEER 문의. 하류 Tongyi 는 CANopen CiA301/402 ✓([[biguamr-motor-control-port]]).
- ⚠ 52301 이하 알람코드 전체·ModbusTCP Writable register[4x]/Status Variable 은 미판독(필요 시 추가 캡처).

## 5. 실무 권고 (본 PC 관점)

- 모터/CAN "통신 오류" 감시가 목적이면 → **TCP API 1050(alarm) 폴링** 또는 **ModbusTCP 00008~00010(플래그)+00031~00033/00120~00125(코드) 폴링**으로 52111/52116~52118/5213x 즉시 감지 가능(외부에서 접근 가능한 유일 경로). ✓
- CAN 버스 자체의 타이밍/에러카운터를 봐야 하면 → Seer 외부 API 로는 불가, **실버스 CAN 탭** 필요.
