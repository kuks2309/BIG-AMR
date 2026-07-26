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
| 3050 | robot_task_gonav_req | 자유 내비게이션 |
| 3051 | robot_task_gotarget_req | **고정 경로 내비게이션**(id=사이트) |
| 3052 | robot_task_translate_req | 평동(translate) |
| 3053 | robot_task_turn_req | 회전(turn) |
| — | (巡检 patrol) | 순회 |

### 4-4. Robot Configuration API (port 19207)
| ID | 이름 | 설명 |
|---|---|---|
| 4000 | robot_config_setmode_req | 운행 모드 전환 |
| 4001 | robot_config_setparams_req | **파라미터 설정** |
| 4002 | robot_config_saveparams_req | **파라미터 설정+저장** |
| 4003 | robot_config_reloadparams_req | 파라미터 재로드 |
| 4004 | robot_config_clearfatal_req | Fatal 에러코드 클리어 |

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
