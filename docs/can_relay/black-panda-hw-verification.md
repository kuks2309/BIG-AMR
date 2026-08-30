# Black Panda 하드웨어 인식·통신·프로그램 모드 실증 기록

> 실측 기록. 등급 ✓(실행 출력 원문 기준). 대상: Black Panda 시리얼 `3e003f001351333033383534`.

## 1. 결론

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| USB(Universal Serial Bus) 열거 | ✅ 정상 | `USB\VID_BBAA&PID_DDCC\3E003F001351333033383534`, Status OK |
| 컨트롤 명령 통신 | ✅ 정상 | `get_type()` = `0x03`, `get_version()` = `DEV-23456789-DEBUG` |
| 디버그 시리얼 콘솔 | ✅ 정상 | `serial_read(SERIAL_DEBUG)` 1023 바이트 수신 |
| 프로그램 모드(부트스텁) 진입·복귀 | ✅ 정상 | PID(Product ID) `DDCC` → `DDEE` → `DDCC` 왕복 |
| 펌웨어 플래시 | ✅ **실증 완료(2026-07-18, 리눅스)** → ⚠ **이 저장소 기준 '외부 근거, 미대조'** (아래 주 참조) | 커밋 `26524538` 빌드본 플래시 후 CAN 양방향 송수신 ✅ — [CAN-relay-test-resolution.md](../../References/Black-Panda/CAN-relay-test-resolution.md) |

> **⚠ 2026-07-27 검증가능성 표시 — 인용된 근거 문서가 이 저장소에 부재.** (기록·라벨 원문은 이력 보존을 위해 유지)
> `ls References/` = `motor_configuration`, `Seer-Driver`, `Tongyi-Motor-Controller` 뿐이며 `References/Black-Panda/`·`References/panda-source/` 는 없다(`find . -name CAN-relay-test-resolution.md` 무히트).
> 따라서 위 ✅ "실증 완료"와 본 문서 `:19`(panda-source/board/README.md L18)·`:31`·`:77`, 그리고 `docs/can_relay/usb-can-mapping-table.md:7`("릴레이 근거: `References/Black-Panda/CAN-relay-test-resolution.md`"), `docs/can_relay/2026-07-07-design-inputs.md:5`(`expriments/can_data/analysis/2026-07-07_tongyi_can_analysis.md` — 경로 부재)는 **이 저장소만으로는 재검증 불가**하다.
> → 라벨은 근거 동반 전까지 **'외부 근거, 미대조'** 로 낮춘다. 조치: 원본 저장소·경로와 **커밋 해시를 병기**하거나 근거 문서를 `References/` 로 동반 이식할 것.

## 2. 초기 미인식 → 해소 경위

- 초기 확인 시 `VID_BBAA` 장치 없음. PnP(Plug and Play) 로그에 `VID_0000&PID_0002` "장치 설명자 요청 실패" 1건만 존재.
- 사용자 확인: **펌웨어 미탑재 제품**. 펌웨어 없는 STM32 는 USB 열거 자체를 하지 않으므로 미인식이 정상 동작 — 하드웨어 불량 아님.
  - 근거: [panda-source/board/README.md](../../References/panda-source/board/README.md) L18 — LED 꺼짐 + `lsusb` 미표시 → DFU(Device Firmware Upgrade) 진입 필요.
- 이후(플래싱 완료 상태로 추정) 재확인 시 정상 열거 확인.

## 3. 실증 절차 및 출력

### 3.1 장치 탐색

```
Panda devices: ['3e003f001351333033383534']
DFU devices:   []
```

`panda` 파이썬 라이브러리는 [References/panda-source/](../../References/panda-source/) 를 패키지로 연결해 사용. 의존성: `libusb1`, `opendbc`.

### 3.2 디버그 시리얼 콘솔 (부팅 로그 원문)

```
************************ MAIN START ************************
Config:
  Board type: Black
  USB serial
detected car harness with orientation 01
switching harness to passthrough (relay off)
Initializing RTC
switching harness to intercept (relay on)
**** INTERRUPTS ON ****
USB enumeration complete
device hasn't sent a heartbeat for 0x00000002 seconds. Safety is set to SILENT mode.
```

관찰:
- `Board type: Black` — 펌웨어가 Black Panda 로 자기 식별. 하드웨어 타입 `0x03` 과 일치.
- 하니스 감지 방향 `01` → 릴레이 intercept 전환.
- 호스트 heartbeat 부재 → **SILENT 모드**(CAN 송신 차단, 수신 전용). 무연결 상태에서 정상·안전.
  - > **⚠ 2026-07-27 반증 — "무연결 상태에서 정상·안전"은 무조건 참이 아니다.** (원문은 이력 보존을 위해 유지)
    > `docs/issues_and_fixes/issues_and_fixes.md:9` — "**문제**: 호스트 소프트웨어를 **하나도 실행하지 않은 채** 전원만 인가하면 Seer 가 `52106 odo data lost` + `52111 motor driver connection error` + `54022 CAN1 Bit Recessive error`(10 초마다 타임스탬프 갱신 = 진행 중) + `54301 Motor is calibrating` 을 지속 발생. 판다 health 는 `safety_mode=0`". 즉 **정확히 이 SILENT·무연결 상태에서 버스가 파괴되고 있었다.**
    > 원인(같은 파일 `:11`): ② "`board/main.c:405-406` `can_silent = ALL_CAN_LIVE` + 루프마다 `enable_can_transceivers(true)` 로 **판다가 그 버스에 live 로 부착**"(현행 소스에서는 `Tools/Can_Relay/panda-firmware/board/main.c:414`·`:421`) ③ "`board/drivers/can_common.h:164-166` `.can_speed = 5000U` = **500 kbps**(버스는 250 kbps)".
    > → **SILENT 는 USB 레벨 TX 차단일 뿐 트랜시버는 live** 이며, 부팅 기본 비트레이트가 버스와 다르면 무연결 전원 인가만으로 버스를 파괴한다. "무연결 상태에서 정상·안전"은 **비트레이트 정합(250 kbps) 전제에서만** 성립한다(정정 근거: `can_common.h:162-171` 주석, `issues_and_fixes.md:11` 해결·상태 항).

### 3.3 프로그램 모드 왕복

```
[1] app mode devices: [('0xbbaa', '0xddcc')]
[2] connected, bootstub flag: False , version: DEV-23456789-DEBUG
[3] sending enter-bootstub (0xd1 wValue=1) ...
    (disconnect expected): USBErrorPipe LIBUSB_ERROR_PIPE [-9]
[4] after reset devices: [('0xbbaa', '0xddee')]
[5] reconnected, bootstub flag: True , version: v1.7.5-EON-unknown-DEBUG
[6] resetting back to app ...
[7] after app reset, bootstub flag: False , version: DEV-23456789-DEBUG
[8] final devices: [('0xbbaa', '0xddcc')]
```

**주의**: master `panda` 라이브러리의 `reset(enter_bootstub=True)` 는 `SUPPORTED_DEVICES` assert 로 Black Panda(`0x03`)를 거부한다(deprecated 기종). 따라서 레거시와 동일한 **원시 컨트롤 전송 `0xd1` (wValue=1)** 을 직접 발행해 진입. 펌웨어 측은 정상 지원.

## 4. 플래시 — ✅ 실증 완료 (선행 기록으로 확인)

본 절의 초판은 "미실행"으로 기술했으나, **선행 기록 검토 결과 플래시는 이미 성공**했다. 정정한다.

| 항목 | 내용 | 출처 |
| --- | --- | --- |
| DFU 통신 (읽기) | `0483:DF11` 업로드로 플래시 전체 1.5MB 추출, RDP 레벨 0 | 커밋 `f0feb04` (2026-07-04 덤프) |
| **펌웨어 쓰기** | 커밋 `26524538` 기반 패치 빌드본을 `Panda().recover()`(부트스텁+앱, DFU)로 플래시 | [CAN-relay-test-resolution.md](../../References/Black-Panda/CAN-relay-test-resolution.md) §4 (2026-07-18) |
| 플래시 후 동작 | CAN 양방향 송수신 ✅ (TX 65프레임, RX 60/60 ACK 정상) | 동 문서 §1 |

- 실행 환경은 **리눅스 `amap-1`** (Ubuntu 22.04, gcc-arm-none-eabi 10.3 + scons + dfu-util). 본 Windows PC 가 아님.
- 빌드 기준 커밋은 `f849893b` 가 아니라 **`26524538`** (black.h 지원, opendbc 불요). 본 문서 초판의 `f849893b` 추정은 선행 기록으로 대체됨.
- 부트스텁이 디버그 빌드(`v1.7.5-EON-unknown-DEBUG`)라 공개 디버그 키 서명 펌웨어를 수용 — 위 성공의 전제.

## 5. 미해결·후속

1. 하니스 미연결 상태에서 `orientation 01` 감지된 원인 확인 (감지 핀 상태 해석)
2. Windows 단독 플래시 경로는 미검증 — 현재 플래시는 리눅스 `amap-1` 에서만 실증됨
