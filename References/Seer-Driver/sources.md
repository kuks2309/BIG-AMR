# Seer Driver (SEER Robotics SRC 컨트롤러) — 참조 자료 수집 (Sources & Index)

> 수집일: 2026-06-23 (KST) · 출처: SEER Robotics / Shanghai Seer Intelligent Technology Corporation (上海仙工智能, "SEER")
> 공식 사이트: https://seer-robotics.ai/ · 그룹: https://www.seer-group.com/ · 문의: contact@seer-group.com
> 검증 등급 표기: **✓** 1차 source(공식 제품 페이지) 직접 확인 / **ⓦ** 타 보고만 / **⚠** 추정·확인 필요(마케팅 페이지에 미기재)

## 0. 프로젝트 맥락 (왜 수집했나)

AMR(Autonomous Mobile Robot) CAN relay 제어 체인의 **상위 제어단(controller)** 이 SEER 제품이다:

```
PLC(Programmable Logic Controller) → Seer Driver(SEER Robotics SRC 컨트롤러) ┐
                                                                            ├→ Black Panda(CAN relay) → Tongyi 서보 드라이버 → 휠
PC(Personal Computer) ─────────────────────────────────────────────────────┘
```

- **Seer Driver** = SEER 의 SRC(SEER Robot Controller) 코어 컨트롤러. AGV/AMR 의 매핑·측위·내비게이션·모션 제어를 담당하며, **모션 명령을 모터/서보 드라이버로 CAN 을 통해 하달**한다.
- 본 프로젝트 AGV 는 **단일/이중 스티어링 휠(steering wheel)** 모션을 쓰고(Tongyi TYD250/TYD160 휠 사용), 따라서 **SRC-F10(단일 스티어링 휠)** 과 **SRC-2000 계열**, 이중 스티어링은 **SRC-R10** 이 가장 관련성이 높다.
- relay 설계 핵심 = **Seer Driver 가 어느 CAN 채널로, 어떤 프로토콜로 모터 드라이버에 무엇을 보내는가.**

## 1. 핵심 결론

### 1-1. CAN 인터페이스 (relay 관점, 최우선)

**모든 SRC 모델이 CAN 채널을 2개(2-Way) 제공한다** ✓ — 공식 제품 페이지 각각에서 직접 확인 (accessed 2026-06-23):
- SRC-880, SRC-F10, SRC-R10, SRC-2000-I(S), SRC-2000-F(S), SRC-3000FS 모두 **"CAN: 2-Way"**.
- SRC-F10/R10 페이지는 "dual CAN redundancy(이중 CAN 이중화)" 로 표기 ✓.

| 항목 | 값 | 근거 / 등급 |
| --- | --- | --- |
| CAN 채널 수 | **2-Way (전 모델 공통)** | ✓ 각 모델 공식 페이지 |
| CAN 용도 | 통상 1채널이 **모터/서보 드라이버 연결**, 다른 채널은 배터리/주변기기 (모델에 따라 배터리는 RS485 또는 CAN 선택) | ⓦ 업계 일반 + SEER help-center 항목 존재(아래 §3) |
| **CAN 프로토콜** | **공식 마케팅 페이지에 미명시** — CANopen(CiA402)/J1939/독자 여부 불명 | ⚠ **확인 필요** (아래 §4) |
| RS485 | 모델별 3~4-Way (배터리 통신 1채널 포함) | ✓ 각 모델 페이지 |
| 배터리 통신 | RS485-0 전용(880/F10/R10/2000) 또는 CAN/RS485 선택(3000FS) | ✓ 각 모델 페이지 |

> ⚠ **relay 설계상 가장 중요한 미확인 사항**: Seer Driver 가 Tongyi 드라이버에 보내는 CAN 프레임의 **프로토콜·보드레이트·Node-ID·PDO 매핑**. SEER 공식 페이지는 CAN 채널 "개수"만 공개하고 프로토콜은 비공개. **하류 Tongyi 측은 표준 CANopen CiA301/402 로 확인됨**(References/Tongyi-Motor-Controller/docs/sources.md ✓)이므로, Seer↔Tongyi 구간은 **CANopen 일 개연성이 높으나 실버스 캡처로 확정 필요**(추정, ⚠).

### 1-2. PC 사양 (사용자 질의 — 두 가지 의미 모두)

질문은 (A) 컨트롤러에 내장/동봉되는 산업용 PC(IPC, Industrial PC) 사양과, (B) SEER 소프트웨어(RoboShop / RDS 등)를 돌리는 권장 호스트/엔지니어링 PC 사양 두 가지를 포함한다. 결론부터:

**(A) SRC 컨트롤러 내장 컴퓨팅(온보드 IPC) 사양**
- SRC 컨트롤러는 **별도 x86 IPC 가 아니라, ARM 기반 임베디드 SoC 를 내장한 통합 모션/내비 컨트롤러**로 보인다.
- **SRC-3000FS: "High-performance 8-core ARM processor(고성능 8코어 ARM)"** ✓ — 공식 SRC-3000FS 페이지에서 유일하게 CPU 가 명시됨.
- 그 외 모델(880/F10/R10/2000-I(S)/2000-F(S))은 **CPU/RAM/스토리지/OS 가 공식 페이지에 일절 미기재** ⚠. SRC-2000-I(S) 도 동일(기존 수집에서 이미 확인).
- OS: 전 모델 미공개 ⚠ (임베디드 Linux 계열로 추정되나 근거 없음 — 단정 금지).

**(B) SEER 소프트웨어(RoboShop Pro / RDS) 구동용 호스트 PC 권장 사양**
- **SEER 공식 1차 source(제품/헬프센터 페이지)에서는 직접 확인하지 못함** ⚠ — docs/books.seer-group.com 헬프센터의 "Installation Environment Requirements" 섹션 정황만 검색으로 확인(ⓦ), 본 환경 WebFetch 차단(ECONNREFUSED)으로 본문 인용 불가.
- 다만 **동봉 `README.md`(이전 수집 pass)에 2차 출처(中 산업매체 gongkong.com / ofweek.com)의 RoboShop Pro 설치 가이드 수치가 정리되어 있음** ⓦ:
  - OS: **Windows 10 (64-bit)** ⓦ
  - RAM: **최소 4GB**, 대형 맵(200m×200m↑)은 **8GB↑ 권장** ⓦ
  - 저장: **8GB↑ 여유** ⓦ / 디스플레이: 1366×768↑(1920×1080 권장) ⓦ
  - 설치: 비시스템 드라이브(D:) 권장, `Program Files` 금지 ⓦ
  - ⓦ 이므로 SEER 공식 매뉴얼 원문으로 ✓ 승격 필요. i5/i7·고용량 등 그 이상 수치는 미확인.
- RDS 는 서버/웹 기반(PC·태블릿·스마트폰 접속), RDS **서버 하드웨어 요구사항은 공식 미공개** ⚠.
- **참고: SRC-3000FS RAM/스토리지 "4GB LPDDR4 + 16GB eMMC + 64GB SATA SSD"** 가 일부 검색 스니펫에 등장하나 **공식 페이지 미확인 → 미검증(⚠)**. 단정 금지.

> 같은 폴더의 `README.md` 는 이전 수집 pass 산출물로, 위 PC 사양(ⓦ)·SEER GitHub firmware/SDK 공개현황·RDS 설명을 추가로 담고 있다. 본 `sources.md` 가 정식 인덱스이며, `README.md` 의 ⓦ 수치는 여기 등급대로 해석할 것(공식 미확정).

## 2. 모델별 스펙 요약 (전부 ✓ — 공식 제품 페이지, accessed 2026-06-23)

| 항목 | SRC-F10 (단일 스티어링) | SRC-R10 (이중 스티어링) | SRC-880 (차동) | SRC-2000-I(S) (범용) | SRC-2000-F(S) (포크리프트) | SRC-3000FS (안전) |
| --- | --- | --- | --- | --- | --- | --- |
| 모션 모델 | Single steering wheel | Dual steering drive | Two-wheel differential | Steering wheel 등 4종 | Steering wheel | 2 Types |
| **CPU** | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | **8-core ARM** ✓ |
| RAM/스토리지/OS | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ | 미기재 ⚠ |
| **CAN** | **2-Way (dual redundancy)** | **2-Way** | **2-Way** | **2-Way** | **2-Way** | **2-Way** |
| RS485 | 4-Way (1=배터리) | 4-Way (1=배터리) | 4-Way (1=배터리) | 3-Way | 3-Way (+1 배터리) | 3-Way |
| Ethernet | 2×Gbps + 1×100M | 2×Gbps + 1×100M | 2×Gbps + 1×100M | 6+1 Gbps | 6+1 Gbps | 5×Gbps (TSN) |
| USB | 2×USB3.0 | 2×USB3.0 | 2×USB2.0 | 4×USB3.0 | 4×USB3.0 | 1×USB2.0 + 2×USB3.0 |
| DI | 10 | 10 | 10 | 11(NPN) | 11(NPN) | 24 (16 PNP+8 옵션) |
| DO | 8 + Power DO 2(24V/1A) | 8 + Power DO 2 | 8 + Power DO 2 | Power DO 8 + DO 2 | Power DO 8 + DO 2 | Power DO 4 + DO 12 |
| 비상정지 | 입력1/출력1 | — | 입력1/출력1 | 입력1/출력2 | 입력1/출력2 | — |
| 전원 | 24V, <12W | 24V, <12W | 24V, <12W | 24V, 48W | 24V, 48W | 24V/50V, 18W |
| 측위정밀 | ±5mm/±1° | ±5mm/±1° | ±5mm/±1° | ±5mm/±1° | ±2mm/±1°(reflector) | ±5mm/±1° |
| 최고속도 | ≤2 m/s | ≤2 m/s | ≤2 m/s | ≤2 m/s | ≤2 m/s | ≤2 m/s |
| 내비게이션 | SLAM/QR/Laser Reflector/NFL | SLAM/QR/NFL | SLAM/QR/Laser Reflector/NFL | SLAM/QR/Laser/NFL | SLAM/QR/Laser/NFL | SLAM/QR/Laser/NFL |
| 맵 면적 | ≤400,000 m² | ≤400,000 m² | ≤400,000 m²(880-T) | ≤400,000 m² | ≤400,000 m² | ≤400,000 m² |
| 치수(mm) | 171×118.5×38 | 171×118.5×38 | 171×118.5×38 | (미수집) | 225.2×128×83.8 | 218×140×64.8 |
| 무게 | 0.75 kg | 0.75 kg | 0.75 kg | — | 1.73 kg | 1.5 kg |
| IP/온도 | IP20, -30~55℃ | — | IP20, -30~55℃ | — | IP42, 0~50℃ | IP52, — |
| 안전등급 | — | — | — | — | — | **ISO 13849-1 Cat.3 PLd / IEC 61508 SIL2** ✓ |
| Wi-Fi | Wi-Fi6 2.4/5G 802.11ax 2T2R | Wi-Fi6 802.11ax 2T2R | 802.11ac 2T2X (Wi-Fi6 업그레이드) | 802.11ac 1T1X | 802.11ac 1T1X | 802.11ac 2T2X |
| 인증 | — | CE-EMC/LVD, UL | CE-EMC/LVD, EN61010 | — | — | CE/UL ETL/FCC, RED |

> 비고: F10·R10·880 은 동일 폼팩터(171×118.5×38, 0.75kg)로 보임 — entry 라인 공통 하드웨어로 추정. SRC-3000FS 만 CPU(8코어 ARM)와 안전등급을 공개.

## 3. 출처 URL 목록 (1차 source)

전부 accessed 2026-06-23. **다운로드 가능한 PDF 는 확보하지 못함**(아래 §3-2 참조).

### 3-1. 공식 제품 페이지 (✓ 스펙 직접 확인)
- 컨트롤러 인덱스: https://seer-robotics.ai/amr-controllers
- SRC-F10 (단일 스티어링): https://seer-robotics.ai/amr-controllers/SRC-F10
- SRC-R10 (이중 스티어링): https://seer-robotics.ai/amr-controllers/SRC-R10
- SRC-880 (차동, entry): https://seer-robotics.ai/amr-controllers/SRC-880
- SRC-2000-I(S) (범용): https://seer-robotics.ai/amr-controllers/SRC-2000-I(S)
- SRC-2000-F(S) (포크리프트): https://seer-robotics.ai/amr-controllers/SRC-2000-F(S)
- SRC-3000FS (안전, 8-core ARM 명시): https://seer-robotics.ai/amr-controllers/SRC-3000FS
- SRC 코어 컨트롤러 소개(마케팅): https://seer-robotics.ai/media/5.0

### 3-1a. 사용자 제공 — SEER 공식 RoboKit API 위키(Feishu), **Public access·로그인 불요** (2026-07-25 최초, 2026-09-02 재확인)
- **SEER RoboKit 문서(Feishu/Lark 위키)**: https://seer-group.feishu.cn/wiki/BAKswyH5biNRHgk2piNcULZWnZd
  - 사용자(kukwonko)가 lidar 멀티캐스트/API 확인용으로 제시(2026-07-25, sess:54fbef84).
  - ✅ **2026-07-25 판독 완료** — computer-use 로 guest 열람(Public access). "Robokit API Protocol" 위키.
  - 발췌 산출물: **[robokit_tcp_api_laser.md](robokit_tcp_api_laser.md)** — 레이저 포인트클라우드 TCP API(1009/11009), 포트 매핑(Status 19204·Push 19301 등), 프로토콜 헤더·운영 주의.
  - 핵심: **Seer가 레이저(lidar) 포인트클라우드를 TCP API(port 19204, API 1009)로 제공 → 이 PC는 SICK 직접 tap 없이 Seer에서 pull 가능(유니캐스트 충돌 해소).**
  - 하위 페이지 URL: Laser=`/wiki/SZcywRZC5ievYhkWQ8hc2ekCnod`, API Introduction(Port)=`/wiki/EJ9QwJUIfiIDMQk3OKfcNbHlnZf`, Overview=`/wiki/MiuMwbcaTiDofPkyMTRcAE9fnUf`.
  - ✅ **2026-09-02 재열람** — 같은 URL, 여전히 **Public access**(로그인 불요, "Guest User" 워터마크로 표시).
  - **열람 방법이 브라우저에 갈린다**: **Chromium 은 정상 렌더**, **Firefox 는 "This browser is not supported" 로 본문이 빈 화면**. WebFetch 는 로그인 리다이렉트로 여전히 불가. → 이 위키를 볼 때는 **Chromium + computer-use**.
  - 좌측 목차 경로: `API > TCP/IP API > {Overview · API Usage Tutorial · API Overview · Robot Status API · Robot Control API · Robot Navigation API · Robot Configuration API · Other API · Robot Push API · Appendix} > Best Practices`.
  - 하위 페이지 URL 추가: **Set Robot Params Temporarily**(=4100) = `/wiki/VpJmwnxheibbKvk3xvjcvUZinVe`.
  - **편호 정본으로 쓸 것** — 이 위키가 `Set Robot Params Temporarily = API number 4100 (0x1004)` 라 적는다. 동봉 PDF v1.2.1 추출본(`github_sdk/robotkit-netprotocol-l-1.2.1.txt:3320,3401`)도 같다. 파생 정리본 [robokit_tcp_api.md](robokit_tcp_api.md) 는 2026-09-02 이전까지 이 4종을 `4001/4002/4003/4004` 로 잘못 적고 있었고 그 오류가 코드로 전파됐다(debt-095·debt-126). **파생본과 원문이 갈리면 원문이 이긴다.**

### 3-1b. 사용자 제공 — GitHub 공개 SDK 우선 수집 (2026-07-26, sess:e717f1dd) ✓
- **github.com/seer-robotics** (SEER 공식 조직). Feishu 는 WebFetch 로그인 리다이렉트로 프로그램 수집 불가 → GitHub 공개 코드/PDF 로 정본 확보.
  - `Robokit_TCP_API_py`(Python NetProtocol 데모 + **공식 PDF `robotkit-netprotocol-l-1.2.1.pdf`**), `SeerTCPTest`(C++/Qt 헤더), `Robokit-Modbus`(ModbusTCP 툴킷).
  - 원본 파일: **`github_sdk/`** (PDF + 추출 `.txt` + Python/C++ 소스). 정리 산출물 아래 2건.
- 산출물:
  - **[seer_api_guide.md](seer_api_guide.md)** ★ **개발 진입점** — 프로토콜 요약 + 재사용 `SeerClient`(공식 packMsg 바이트 동일성 검증 ✓) + 자주 쓰는 API 레시피표 + 체크리스트. API 활용 작업은 여기서 시작.
  - **[robokit_tcp_api.md](robokit_tcp_api.md)** — TCP/IP API 정본: 포트(19204~19210/19301), 16B 헤더, packMsg/unpackHead, **전체 API 편号 맵**(Status/Control/Task/Config/Kernel/Other), 사용예, v1.2.1↔v1.4.2 버전차.
  - **[can_timing_motor_controller.md](can_timing_motor_controller.md)** — 사용자 지시(CAN timing/모터제어기): **GitHub 엔 CAN 설정 부재 확정** → Feishu ModbusTCP 레지스터+PDF 알람코드로 **통신/모터 에러 변수**(52111 드라이버연결·52116~52118 네트워크단절·5213x 모터고장; ModbusTCP 00031/00032/00033/00120~00125) 정리. **raw CAN baud/node/timing 은 외부 API 미노출**(RoboShop 내부).

### 3-2. 미확보(차단/SPA) — URL 만 보존
- SEER 다운로드 센터: https://seer-robotics.ai/download — **JS SPA 라우트**. `download?id=NN`(예: 880=154, F10=278, R10=279, 2000-I(S)=55, 2000-F(S)=56, 3000FS=54)는 모두 **동일한 HTML 셸(84KB)** 만 반환, 실제 PDF 아님 → magic byte `%PDF` 미검출, 폐기함.
- SEER 헬프센터(SRC-2000 User Guide, CAN/모터드라이버 연동·드라이버별 설정): https://docs.seer-group.com/en/en/d/1651868142940479490.html — **WebFetch 차단(ECONNREFUSED)**. 모터 드라이버 연동 항목 다수 존재(Ming Chi MBDV, ELMO 등 드라이버별 설정 페이지: books.seer-group.com).
- RoboShop / RDS 시스템 요구사항: 헬프센터 내 "Installation Environment Requirements" 섹션 정황만 확인(ⓦ), 본문 차단으로 수치 미확보.
- 합본 카탈로그(SEER Composite Catalog): Scribd 호스팅(로그인 월) — 공식 직링크 PDF 미발견. https://www.scribd.com/document/669901592/SEER-Composite-Catalog (ⓦ 2차)
- RoboShop 인스톨러(비공식 미러, 2017, 구버전): https://sourceforge.net/projects/seer-roboshop/ (`RoboshopInstaller_1.1.6.rar`, 61.2MB) — **비공식·구버전, 권장 사양 비포함**(ⓦ).

### 3-3. 동봉 문서
- `README.md` (이전 수집 pass) — 모델별 스펙표 + **RoboShop Pro PC 사양(ⓦ)** + RDS 설명 + **SEER GitHub firmware/SDK 공개현황**(SRC 코어 펌웨어 비공개, NetProtocol TCP/Modbus API 만 공개: github.com/seer-robotics) 포함. 본 인덱스의 보강 자료.

## 3-4. 다운로드한 파일 목록
- **없음.** 모든 공식 datasheet 링크가 JS SPA 라우트(실 PDF 아님)였고, `head -c 8 | xxd` 결과 `%PDF` 미검출(전부 `<!DOCTYPE html>`). 가짜 HTML bin 파일은 삭제함. `datasheets/` 폴더는 향후 확보분 대비 빈 상태로 유지.

## 4. 미수집 / 추가 확인 대상 (정직한 한계)

- ⚠ **[relay 최우선] Seer Driver↔모터드라이버 CAN 프로토콜**: CANopen(CiA402) 여부·보드레이트·Node-ID·PDO 매핑 — 공식 페이지 비공개. 확정 경로: ① SEER 헬프센터 SRC-2000 User Guide / 드라이버별 설정 페이지(books.seer-group.com, 차단 우회 필요) ② **Seer↔Tongyi 구간 실버스 CAN 캡처**(최종 확정 수단) ③ SEER 문의(contact@seer-group.com). 하류 Tongyi 는 CANopen CiA301/402 ✓ 이므로 상류도 CANopen 개연성 높음(⚠ 추정).
- ⚠ **컨트롤러 내장 컴퓨팅(IPC) 상세**: SRC-3000FS 만 "8-core ARM" ✓. 나머지 모델의 CPU/RAM/스토리지/OS 전부 미공개. SRC 는 x86 IPC 가 아니라 ARM SoC 통합형으로 추정.
- ⚠ **[사용자 질의 핵심] RoboShop Pro / RDS 호스트 PC 권장 사양**(CPU 등급·RAM·디스크·Windows 버전): 공식 헬프센터에 섹션 존재 정황(ⓦ)만 확인, 본문 차단으로 수치 미확보. → 헬프센터 직접 열람 또는 SEER 문의 필요.
- ⚠ **공식 datasheet/카탈로그 PDF**: SPA·로그인월로 직다운로드 실패. 정식 PDF 는 SEER 영업/헬프센터 경유 필요.
- ⚠ SRC-2000-I(S) 치수·무게: 본 수집 미확보(페이지에 표기되어 있을 수 있으나 발췌 누락).

## 5. 다음 단계 제안

1. SEER 헬프센터(docs/books.seer-group.com)를 **브라우저로 직접** 열어 ① SRC-2000 User Guide 의 모터 드라이버 연동(CAN 프로토콜) ② RoboShop Pro "System Requirements" 챕터(PC 권장 사양) 캡처 → 본 문서 ⚠ 항목을 ✓ 로 승격.
2. 실 AGV 의 BOM 으로 탑재 SRC 모델 확정(단일=F10 / 이중=R10 / 범용=2000 추정).
3. **Seer↔Tongyi 구간 CAN 실버스 캡처** → 프로토콜·보드레이트·Node-ID·PDO 확정(Tongyi sources.md §1 의 0x6040/0x6081 등과 대조).
4. 확정된 프로토콜로 Black Panda relay 개입 지점(pass-through ↔ injection) 설계.
