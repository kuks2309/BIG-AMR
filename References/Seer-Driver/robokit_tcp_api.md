# SEER Robokit NetProtocol — TCP/IP API 정본 (GitHub 공개 SDK 기반)

> 수집일: 2026-07-26 (KST, sess:e717f1dd) · 방법: **GitHub 공개 SDK 우선**(사용자 선택) — WebFetch 로 원본 코드/PDF 직다운로드
> 1차 source: **github.com/seer-robotics** (SEER 공식 조직) + 동봉 공식 PDF `robotkit-netprotocol-l-1.2.1.pdf`
> 검증 등급: ✓ = 공식 저장소 원본 코드/PDF 직접 확인 / ⚠ = 추정·버전차 주의
> 관련: [[robokit_tcp_api_laser]](레이저 API 상세) · [[sources]](Seer-Driver 인덱스)

## 0. 왜 GitHub SDK 인가

Feishu wiki(guest 열람)는 WebFetch 가 로그인으로 리다이렉트되어 프로그램적 수집 불가(302 → accounts.feishu.cn). 반면 **SEER 가 동일 프로토콜의 데모 코드와 공식 PDF 를 GitHub 에 공개**하고 있어, 화면 전사보다 정확·완전하게 확보 가능. 본 문서는 그 원본을 정리한 것이며, 원본 파일 자체는 `github_sdk/` 에 보존.

## 1. 확보한 저장소·파일 (github_sdk/)

| 저장소 | 용도 | 확보물 |
|---|---|---|
| **Robokit_TCP_API_py** | Python NetProtocol TCP API 데모 | `netprotocol/rbkNetProtoEnums.py`(핵심 정의), 데모 스크립트 다수, **공식 PDF `robotkit-netprotocol-l-1.2.1.pdf`** + 추출 텍스트 `.txt` |
| **SeerTCPTest** (C++/Qt, 44★) | TCP API GUI 테스트 툴 | `SCHeadData.h`(헤더 구조체), `README.md`(사용법) |
| Robokit-Modbus | ModbusTCP 레지스터 툴킷(PLC용, 별개 계층) | (다운로드 안 함 — .mbp 바이너리) |

> 공식 PDF 는 protocol **v1.2.1**. 최신 Feishu wiki 는 v1.4.2 표기 → **버전차 존재**(아래 §6 주의).

## 2. 포트 매핑 ✓

`netprotocol/rbkNetProtoEnums.py` (원본):
```python
API_PORT_ROBOD  = 19200   # daemon / core (rbk 프로세스)
API_PORT_STATE  = 19204   # Robot Status API
API_PORT_CTRL   = 19205   # Robot Control API
API_PORT_TASK   = 19206   # Robot Task/Navigation API
API_PORT_CONFIG = 19207   # Robot Configuration API
API_PORT_KERNEL = 19208   # Robot Core/Kernel API
API_PORT_OTHER  = 19210   # Other API
```

| Category | Port | 동시연결(PDF v1.2.1) | 동시연결(Feishu 최신) |
|---|---|---|---|
| Robot Status API | **19204** | 10 | 10 |
| Robot Control API | **19205** | **1** | 5 |
| Robot Task/Navigation API | **19206** | **1** | 5 |
| Robot Configuration API | **19207** | **1** | 5 |
| Robot Core(Kernel) API | 19208 | — | — |
| Other API | **19210** | **1** | 5 |
| (daemon) | 19200 | — | — |
| **Robot Push API** | **19301** | — | 10 |

> ⚠ **버전차**: PDF v1.2.1 은 Control/Task/Config/Other 를 **동시연결 1** 로 제한(연결 점유 시 타 연결 거부). Feishu 최신판은 5. Push API(19301)는 최신판에만 명시.
> 참고: `robot_status_req` 등 **각 포트는 정해진 report type 만 수신**. 엉뚱한 포트로 보내면 `60000`(잘못된 report type) 응답. 19204 에 timeOut>0 설정 시, 연결이 하나도 없으면 로봇 즉시 정지 후 ReturnPoint 복귀.

## 3. 메시지 구조 (16바이트 헤더 + JSON) ✓

PDF §1.3 + `SCHeadData.h` + `rbkNetProtoEnums.py` 세 곳 일치 확인.

```c
// C++ 공식 헤더 구조체 (PDF §1.3, SCHeadData.h)
struct ProtocolHeader {          // 총 16 byte, big-endian(network order)
    uint8_t  m_sync;             // [0]   동기 헤더 = 0x5A (고정)
    uint8_t  m_version;          // [1]   프로토콜 주버전 = 0x01 (v1.x.x)
    uint16_t m_number;           // [2-3] 序号 seq(0~65535). 응답은 같은 seq 반향 → 요청/응답 대응
    uint32_t m_length;           // [4-7] 데이터부(JSON 직렬화) 길이. 무파라미터면 0x00000000
    uint16_t m_type;             // [8-9] 报文类型 = API 편号 (요청 ID)
    uint8_t  m_reserved[6];      // [10-15] 예약(6byte, 0x00 채움 필수)
};
// 데이터부: m_length 만큼의 JSON(ascii) 직렬화 바이트
```

Python 팩/언팩 (원본 `rbkNetProtoEnums.py`):
```python
import json, struct
# 0x5A + Version + serialNum + jsonLen + reqNum(=API type) + rsv(6B)
PACK_HEAD_FMT_STR = '!BBHLH6s'          # '!' = big-endian
PACK_RSV_DATA = b'\x00\x00\x00\x00\x00\x00'

def packMsg(reqId, msgTyp, msg={}):     # reqId=seq번호, msgTyp=API편号
    jsonStr = json.dumps(msg)
    msgLen = len(jsonStr) if msg != {} else 0
    rawMsg = struct.pack(PACK_HEAD_FMT_STR, 0x5A, 1, reqId, msgLen, msgTyp, PACK_RSV_DATA)
    if msg != {}:
        rawMsg += bytearray(json.dumps(msg), 'ascii')
    return rawMsg

def unpackHead(data):                    # 응답 16B 헤더 파싱
    result = struct.unpack(PACK_HEAD_FMT_STR, data)
    return (result[3], result[4])        # (jsonLen, reqNum)
```

핵심 규칙(PDF §1.3):
- **응답 편号 = 요청 편号 + 10000 (0x2710)**. 예: 1004 요청 → 11004 응답.
- 로봇은 **절대 능동 송신 안 함**(Push API 제외). 한 연결당 **1문1답**(이전 응답 전 다음 요청 금지).
- 헤더 파싱 불가 → 로봇이 연결 끊음(무응답). 데이터부 파싱 실패 → 잘못된 요청 응답.
- 예약 6바이트 생략 불가(0x000000000000 채움). ⚠ 단, `SeerTCPTest`(C++ 툴)는 예약[0-3]에 type·jsonSize 를 중복 기입하는 자체 관례가 있으나 **표준은 0 채움**.

## 4. API 편号 맵 (요청/응답, PDF v1.2.1 §2~7) ✓

응답 = 요청 + 10000. 아래는 요청 편号 기준.

### 4-1. Robot Status API (port 19204)
| ID | 이름 | 설명 |
|---|---|---|
| 1000 | robot_status_info_req | 로봇 정보(버전 등) |
| 1002 | robot_status_run_req | 운행 정보(운행시간·주행거리 등) |
| 1003 | robot_status_mode_req | 운행 모드 |
| 1004 | robot_status_loc_req | **위치**(x,y,angle) |
| 1005 | robot_status_speed_req | **속도**(vx,vy,w) |
| 1006 | robot_status_block_req | 피차단(blocked) 상태 |
| 1007 | robot_status_battery_req | **배터리** 상태 |
| 1008 | robot_status_brake_req | 抱闸(brake) 상태 |
| 1009 | robot_status_laser_req | **레이저(LiDAR) 데이터** → [[robokit_tcp_api_laser]] |
| 1010 | robot_status_path_req | 경로 데이터 |
| 1011 | robot_status_area_req | 현재 위치한 area |
| 1012 | robot_status_emergency_req | **급정지(emergency)** 상태 |
| 1013 | robot_status_io_req | **IO(DI/DO)** 데이터 |
| 1020 | robot_status_task_req | 작업 상태·작업 사이트·경로 |
| 1021 | robot_status_reloc_req | 재측위(reloc) 상태 |
| 1022 | robot_status_loadmap_req | 지도 로드 상태 |
| 1025 | robot_status_slam_req | 스캔(SLAM) 상태 |
| 1050 | robot_status_alarm_req | **告警(alarm/error) 상태** |
| 1100 | robot_status_all1_req | 배치 데이터 1 |
| 1101 | robot_status_all2_req | 배치 데이터 2 |
| 1102 | robot_status_all3_req | 배치 데이터 3 |
| 1111 | robot_status_init_req | 초기화 상태 |
| 1300 | robot_status_map_req | 로드된 지도 + 저장된 지도 목록 |
| 1301 | robot_status_station | 현재 지도의 스테이션 정보 |
| 1400 | robot_status_params_req | **로봇 파라미터** (← CAN/통신 설정 변수 후보, §7 참조) |

### 4-2. Robot Control API (port 19205)
| ID | 이름 | 설명 |
|---|---|---|
| 2000 | robot_control_stop_req | 운동 정지 |
| 2001 | robot_control_gyro_req | 자이로 캘리브레이션 |
| 2002 | robot_control_reloc_req | **재측위(reloc)** — 파라미터 x,y |
| 2003 | robot_control_confirmloc_req | 측위 정확 확인 |
| 2010 | robot_control_motion_req | **개루프 운동**(vx,vy,w 직접) |
| 2022 | robot_control_scan_req | 스캔 시작 |
| 2023 | robot_control_stopscan_req | 스캔 정지 |
| 2024 | robot_control_loadmap_req | 로드 지도 전환 |
| 2025 | robot_control_reloadmap_req | 지도 요소 재로드 |

### 4-3. Robot Task/Navigation API (port 19206)
| ID | 이름 | 설명 |
|---|---|---|
| 3001 | robot_task_pause_req | 현재 작업 일시정지 |
| 3002 | robot_task_resume_req | 현재 작업 계속 |
| 3003 | robot_task_cancel_req | 현재 작업 취소 |
| 3050 | robot_task_gopoint_req | 자유 내비게이션 |
| 3051 | robot_task_gotarget_req | **고정 경로 내비게이션**(id=사이트) |
| 3052 | robot_task_patrol_req | **순찰**(경로 목록 반복) |
| **3055** | robot_task_translate_req | 평동(translate) — 고정 속도·고정 거리 |
| **3056** | robot_task_turn_req | 회전(turn) — 고정 각속도·고정 각도 |

> ❌ **2026-08-08 정정 — 위 표의 번호 2개가 틀려 있었다.** 원문 대조로 고쳤다.
>
> | 정정 전(틀림) | 벤더 원문 v1.2.1 `github_sdk/robotkit-netprotocol-l-1.2.1.txt:2851-2859` |
> | --- | --- |
> | `3052 = translate` | **`3052 = robot_task_patrol_req`(순찰)** |
> | `3053 = turn` | **`3053` 은 정의 자체가 없다** |
> | (없음) | **`3055 = translate` · `3056 = turn`** |
> | `3050 = gonav` | `3050 = gopoint` |
>
> ⚠ **`3052` 를 「평동」인 줄 알고 보내면 순찰이 시작된다.** 실기에 보내기 전 반드시
> 원문(`:2851-2859`, 상세는 `:3192`·`:3248`)을 확인할 것.
>
> **3055/3056 의 `mode` 필드** — `0 = 里程(오도메트리, 기본)` / `1 = 自定位(자기측위)`.
> 원문이 **「自定位模式目前不可用」(자기측위 모드 현재 사용 불가)** 이라고 명시한다.
> 즉 이 두 원시 기동은 **오도메트리 개루프**다. 또 3055 와 3056 은 **동시 수행 불가**.
> 분석: [docs/seer/2026-08-08-seer-path-control.md](../../docs/seer/2026-08-08-seer-path-control.md)

### 4-4. Robot Configuration API (port 19207)
| ID | 이름 | 설명 |
|---|---|---|
| 4000 | robot_config_setmode_req | 운행 모드 전환 |
| 4100 | robot_config_setparams_req | **파라미터 설정** |
| 4101 | robot_config_saveparams_req | **파라미터 설정+저장** |
| 4102 | robot_config_reloadparams_req | 파라미터 재로드 |
| 4300 | robot_config_clearfatal_req | Fatal 에러코드 클리어 |

### 4-5. Robot Core/Kernel API (port 19208)
| ID | 설명 |
|---|---|
| — | 로봇 종료 / 프로그램 정지·시작·재시작 / 로봇 재부팅 / 펌웨어 리셋 |

### 4-6. Other API (port 19210)
| ID | 이름 | 설명 |
|---|---|---|
| 6000 | (喇叭 speaker) | 스피커 제어 |
| 6001 | robot_other_setdo_req | **DO 출력 설정**({"id":N,"status":bool}) |

> 원본 데모: `rbkDemoTurn.py`(2010 motion), `rbkDemoReloc.py`(2002 reloc), `gotarget.py`(3051), `rbkApiSetDO.py`(6001), `rbkApiStatusTaskReq.py`(1020), `rbkApiQueryIO.py`(1013). 전부 `github_sdk/Robokit_TCP_API_py/` 에 보존.

## 4-7. 조향(steering) — **직접 지령 API 는 없다** (2026-08-08 조사)

지시: 「seer api로 각도에 따른 엔코더 값 테이블 있나요?」·「조향 명령어 api 알려주세요 번호라던지」

### 4-7-1. 지령 — 조향각을 직접 주는 API 가 §4-2 에 없다

문서화된 제어 API(19205) 9개 중 조향 항목은 **0개**다. 가장 가까운 것:

| ID | 이름 | 조향과의 관계 |
| --- | --- | --- |
| **2010** | `robot_control_motion_req` | **개루프 운동 `vx, vy, w`**. 조향각이 아니라 **속도 벡터**를 주면 Seer 가 내부에서 조향을 계산한다 — `vy` → crab 자세, `w` → 회전 자세 |
| 2000 | `robot_control_stop_req` | 운동 정지 |

원본 데모: `github_sdk/Robokit_TCP_API_py/rbkDemoTurn.py` (2010 사용, §5 참조).

⇒ **「조향을 몇 도로 세워라」는 이 API 집합으로 표현할 수 없다.** 각도별 자세를 만들려면
`vy`/`w` 를 바꿔 가며 Seer 가 만든 조향을 **관측**하는 방식이어야 한다.

### 4-7-2. 판독 — 값은 있으나 CAN 과 **독립이 아니다**

| ID | 필드 | 성격 |
| --- | --- | --- |
| **1005** `robot_status_speed_req` | `steer_angles` | "The **current** steering angle … unit: rad". 듀얼이면 `[front, rear]` |
| 1005 | `r_steer_angles` | "Steering angles **received**" ⇒ **지령값이지 실측이 아니다** |
| **1040** / 1100 `motor_info[]` | `encoder` · `position` | 축별 엔코더. `motor_name` = `FrontWalk`/`RearWalk`/`FrontSteer`/`RearSteer` |
| 1101 | `steer` · `r_steer` | 배치 데이터의 조향각(rad) |

> 벤더 정의 출처: `T-Robot_seer_gui/references/seer/robokit-api/robot-status-api/005-query-robot-speed.md:40-41`
> (타 저장소 github kuks2309/T-Robot_seer_gui — 본 저장소 `References/` 아님).

⚠ **1005·1040 은 판다가 엿듣는 바로 그 `0x6064` 의 아핀 변환이다** — 기울기 × 57,344 가
1040 = **1.000001**, 1005 = **1.000130**. 근거·상세: `docs/homing/2026-08-03-can-relay-homing-assets.md:608`.

### 4-7-3. ⇒ 「각도 ↔ 엔코더 표」는 만들어도 교차검증이 되지 않는다

두 채널이 같은 원천의 아핀 변환이므로 표를 만들면 `angle = (enc − 영점)/57,344` 라는
**항등식**을 되읽는 것이다. 자세와 무관하게 항상 맞으므로 **정합의 근거가 되지 못한다**
(같은 문서가 「인용 금지」로 못박아 둔 항목).

**표에서 실제로 뽑을 수 있는 값은 「영점」 하나뿐**이다:

```
0° 엔코더 = enc − angle × 57,344
```

2026-08-08 실측(제어권 반환 상태): 전륜 `−13,040,386 counts @ −90.132°` → 0° 엔코더
**−7,871,857**. `foil_a082.yaml` 의 `steer_home_counts[0] = 7,871,815`(부호 반대 규약)와
**42 counts = 0.0007°** 차이로 일치한다.

### 4-7-4. ⚠ 제어권을 쥐면 이 판독은 **얼어붙는다**

`can_relay` 가 intercept 하는 동안 판다 펌웨어가 emulate 로 들어가
(`safety_seer_gate.h:164` `emulate = cover || pc_authority`), Seer 에게는 **engage 시점
스냅샷**이 전달된다. 2026-08-08 실측 — 조향을 10°·20° 실제로 움직였는데
**Seer `motor_info.encoder` 가 1 count 도 변하지 않았다**.

⇒ **Seer 를 계측기로 쓰려면 제어권을 반환**해야 한다. 그리고 반환하더라도 **우리가 제어권을
쥐고 움직인 이력은 Seer 가 모른다.** 표를 만들려면 **Seer 가 직접 몰아야 한다**(2010).

### 4-7-5. 관련 도구 (결과는 미산출)

| 도구 | 목적 | 상태 |
| --- | --- | --- |
| `Tools/docking_field_kit/orin_steer_sweep_1005.py` | 1005 전달함수 실측 | 결과 표 저장소에 없음 |
| `Tools/docking_field_kit/orin_steer_crosscheck.py` | `0x6064` ↔ Seer 1040 동시 기록 | 상동 |

`docs/homing/2026-08-03-can-relay-homing-assets.md:786,801,830` 이 「1005 전달함수 미확정」으로
닫히지 않은 채 남아 있다.

---

## 5. 최소 사용 예 (원본 `rbkDemoTurn.py` 발췌) ✓

```python
from rbkNetProtoEnums import *
import json, socket
so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
so.connect(('192.168.4.136', API_PORT_CTRL))   # 19205 (제어)
so.settimeout(5)
so.send(packMsg(1, robot_control_motion_req, {"vx":0.0, "vy":0.0, "w":2.5}))  # 개루프 회전
data = so.recv(16)                               # 헤더 먼저
jsonDataLen, backReqNum = unpackHead(data)       # 데이터 길이·seq
if jsonDataLen > 0:
    ret = json.loads(so.recv(1024))              # JSON 바디
so.close()
```
> 데모 기본 접속 IP 예시: `192.168.4.136`, `192.168.4.235`, `192.168.192.5` (로봇 IP — 환경별 상이). 본 프로젝트 SRC 후보 IP=`192.168.44.82`(무선, [[biguamr-seer-network-access]]).

## 6. 주의·한계

- ⚠ **버전차**: 본 PDF=v1.2.1, Feishu 최신=v1.4.2. 포트 동시연결수·신규 API(Push 19301 등)·필드가 다를 수 있음. 실사용 전 로봇 펌웨어 버전 대조 필요.
- ⚠ Python 데모의 API ID enum 은 **데모가 쓰는 일부만** 정의. **전체 목록은 PDF(`robotkit-netprotocol-l-1.2.1.txt`) 정본** 참조.
- 요청 간격 **최소 100~200ms 권장**(과빈번 금지) → 폴링 실효 ~5–10Hz.

## 7. CAN 통신 설정·에러 변수 (← 사용자 지시: GitHub 부재 시 web 추출)

**결론: TCP/IP netprotocol(GitHub) 에는 CAN timing/모터제어기 설정 자료 없음.** 확인된 것은 **모터 관련 "에러 코드"뿐**(TCP 로 보고되는 상위 알람):

| 코드 | 의미(원문) |
|---|---|
| 52111 | motor driver connection error / 驱动器连接故障 |
| 52130 | motor GVDD over voltage / 电机GVDD过压 |
| 52131 | motor FET over current / 电机桥臂过流 |
| 52132 | motor over temperature / 电机驱动器过热 |
| 52133 | motor VDD under voltage / 电机电源欠压 |
| 52135 | motor error see log / 电机其他(로그 확인) |
| 54003 | motor over speed / 电机超速 |
| 54004 | motor emergency stop / 电机被拍急停 |

→ 이는 **결과(알람)**이지 **CAN 통신 설정(baud/Node-ID/timing/error counter)** 이 아님. CAN 통신 설정·에러 변수의 web 추출 결과는 **[can_timing_motor_controller.md](can_timing_motor_controller.md)** 에 별도 정리(작업 중).
