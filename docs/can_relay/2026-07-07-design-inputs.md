# CAN Relay 제작 설계 입력 문서 — 실측 트래픽 기반 (2026-07-07)

> 목적: Seer↔Tongyi 모터 CAN(Controller Area Network) 구간에 인라인 삽입할 **CAN 릴레이(Black Panda, STM32F4)** 제작에 필요한 요구사항·프레임 사전·타이밍 예산을 **실측 로그 기반**으로 확정한다.
> 상위 아키텍처: [docs/sw_structure/system-architecture/2026-06-27.md](../sw_structure/system-architecture/2026-06-27.md) (D2 인라인 삽입, D5 Black Panda, D6 원본 프레임 모사, D14 PLC 직결, D4 fail-safe)
> 실측 근거: [expriments/can_data/analysis/2026-07-07_tongyi_can_analysis.md](../../expriments/can_data/analysis/2026-07-07_tongyi_can_analysis.md) (로그 2본, 475 s, 737k 프레임)

---

## 1. 버스 물리·프로토콜 파라미터 [실측 확정]

| 항목 | 값 | 비고 |
|---|---|---|
| 비트레이트 | **250 kbps** | classic CAN, CAN-FD 아님 |
| ID 형식 | 11-bit standard | 확장 ID 없음 |
| 프로토콜 | CANopen — **SDO(Service Data Object) 폴링 전용** | PDO(Process Data Object)·SYNC·EMCY(Emergency)·TIME 부재 |
| 노드 | 1·2 (구동), 3·4 (조향) | QD(Quad Drive) 조향구동휠 유닛 2세트, 페어링 (1+3)/(2+4) |
| NMT(Network Management) | 전 노드 **pre-operational 고정** | operational 천이 없음 — 표준 가정 금지 |
| 노드 감시 | **Node Guarding: 마스터 RTR(Remote Transmission Request) → 노드 응답** | heartbeat 아님. 50 ms/노드 |
| 버스 부하 | **69 % (long) / 74 % (run)** | 1,500~1,600 frames/s |

## 2. 트래픽 모델 [실측]

관찰된 전체 CAN ID 와 방향·주기 (run.asc 기준 초당 프레임):

| ID | 방향 | 내용 | 레이트 |
|---|---|---|---|
| 0x601–0x604 | Seer → 모터 | SDO 요청 (읽기/쓰기) | 노드당 147–203 fps |
| 0x581–0x584 | 모터 → Seer | SDO 응답 | 노드당 147–203 fps |
| 0x701–0x704 (RTR) | Seer → 모터 | node guard 요청 (DLC 0, RTR) | 노드당 20 fps |
| 0x701–0x704 (data) | 모터 → Seer | node guard 응답 (1 byte, 0x7F/0xFF 토글) | 노드당 20 fps |

폴링 스케줄 (Seer 마스터):

| 루프 | 오브젝트 | 주기 |
|---|---|---|
| 위치 읽기 | 0x6064 (Position actual) ×4노드 | **10 ms** |
| 지령 쓰기 | N1/N2: 0x60FF / N3/N4: 0x607A + 0x6040 | ~20 ms |
| 상태 읽기 | 0x6041·0x603F·0x6078·0x6000:01 ×4노드 | ~425 ms |
| node guard | RTR ×4노드 | 50 ms |

## 3. 프레임 사전 (mini-DBC) [실측 — inject 시 원본 모사 근거, D6]

전 프레임 DLC=8 (node guard 제외), 멀티바이트 리틀엔디언.

### Seer → 모터 (0x600+node)

| 용도 | 데이터 | 의미 |
|---|---|---|
| 속도 지령 쓰기 | `23 FF 60 00 VV VV VV VV` | 0x60FF:00 ← int32, **0.1 r/min** 단위 (관찰 범위 ±4889 = ±488.9 rpm) |
| 위치 지령 쓰기 | `23 7A 60 00 PP PP PP PP` | 0x607A:00 ← int32, 조향 카운트 |
| Controlword 쓰기 | `2B 40 60 00 3F 00 00 00` | 0x6040 ← 0x003F 고정 (new set-point + change set immediately), 매 사이클 재기록 |
| 위치 읽기 요청 | `40 64 60 00 00 00 00 00` | 0x6064 upload request |
| 상태 읽기 요청 | `40 41 60 00 …` / `40 3F 60 00 …` / `40 78 60 00 …` / `40 00 60 01 …` | statusword / error code / current / digital input |

### 모터 → Seer (0x580+node)

| 용도 | 데이터 | 의미 |
|---|---|---|
| 쓰기 확인 | `60 FF 60 00 00…` / `60 7A 60 00 00…` / `60 40 60 00 00…` | download 성공 응답 |
| 위치 응답 | `43 64 60 00 PP PP PP PP` | int32 카운트 |
| Statusword 응답 | `4B 41 60 00 SS SS 00 00` | 관찰값: 0x8050/0x8450 (N1·2), 0x9050/0x9450 (N3·4) — bit10 = 기동 연동 |
| 에러코드 응답 | `4B 3F 60 00 00 00 00 00` | 전 로그에서 항상 0 |
| 전류 응답 | `4B 78 60 00 II II 00 00` | int16, 단위 미확정 |
| 디지털입력 응답 | `4F 00 60 01 01 00 00 00` | 항상 0x01 |

> ⚠ **정정 (2026-07-27 실기 검증)** — 위 표의 **Statusword 응답·디지털입력 응답** 두 행은 2026-07-07 로그(정상 주행 구간)만 본 것이라 **호밍 국면이 통째로 빠져 있다**. 원문은 이력 보존을 위해 남긴다. 근거: `Log/homing_capture_220350.jsonl` (Seer 주도 호밍 180 s 수동청취, 253,510 프레임).
>
> **① Statusword 관찰값 — 호밍 중 `bit15=0` 값 2종 누락**
> - 실측 전수 집계: **N1·N2 = `0x8050` 단일값(각 420/420)** — 이번 캡처에서 `0x8450` 은 나오지 않았다(원문의 `0x8450` 은 2026-07-07 로그 근거이므로 삭제하지 않고 출처를 병기한다).
> - **N3·N4 = 4종이 모두 나온다**(노드별로 값이 갈리지 않는다 — 두 노드 다 동일 4종):
>   `0x9450`(334) · `0x9050`(9) · **`0x1450`(105)** · **`0x1050`(N3 1,527 / N4 1,523)**
> - **`0x1050`·`0x1450` 은 `bit15=0`, 즉 호밍 진행 중 상태**다 — 원문 목록에 없다. 실증: `Log/homing_capture_220350.jsonl:12773` (`t=17.9562`, id 0x583, `4b41600050100000` = 0x1050) / `:52174` (`t=47.0009`, id 0x584, `4b41600050140000` = 0x1450). **freeze/emulate 스냅샷을 원문 4종만으로 설계하면 호밍 국면을 표현할 수 없다.**
> - **비트 의미 정정**: `bit15` = **Home attained**(호밍 완료) [Handbook V7.0 §6.9, page 171], `bit10` = **Target reached** — 원문의 "bit10 = 기동 연동" 은 부정확하다. 실증(node3 137° 스윙 구간): `t=49.0795` 0x9450 → **`t=49.3267`~`52.5245` 0x9050**(bit10=0, 이동 중) → `t=52.9315` 0x9450(bit10=1, 도달). 같은 구간 `0x6064` 는 23,252(t=49.3148) → 7,882,008(t=52.9354) 로 실제 이동.
>
> **② 디지털입력 "항상 0x01" 은 성립하지 않는다 — 호밍 원점 신호가 이 비트로 올라온다**
> - `0x6000` 은 배열 오브젝트이고 실제 입력값은 **sub 1**(sub 0 = 항목 수 2). sub 1 비트: **bit0 = ServoEnable, bit3 = −Limit(음의 리밋)**.
> - 실측 전이(조향 노드에만 발생, 구동 노드 N1·N2 는 전 구간 `0x01` 420/420 고정):
>   `t=47.0249`(N3) / `t=47.0254`(N4) **`0x01` → `0x09`**(bit3 set = 음의 리밋 물림) → `t=49.4223`(N3) / `t=49.4227`(N4) **`0x09` → `0x01`**(해제).
> - 해제가 조향 0° 복귀 이동 **중**에 일어난다 — 호밍은 원점에 머무는 것이 아니라 **원점 경유 후 조향 0° 복귀까지**이며, 리밋에 얹힌 채 두면 그 방향 지령이 막힌다.
> - ⇒ 릴레이가 이 프레임을 "상수 0x01" 로 가정하면(예: emulate 시 하드코딩) **호밍 원점 검출을 Seer 에게서 감춘다**. 정정된 서술: `4F 00 60 01 DD 00 00 00`, 정상 대기 `0x01` / 호밍 원점 검출 시 조향 N3·N4 만 `0x09`.

### Node guard (0x700+node)

- 요청: RTR, DLC 0 (Seer → 모터) — **릴레이는 RTR 프레임을 반드시 중계해야 함**
- 응답: 1 byte, `7F`/`FF` 교대 (toggle bit + pre-operational 상태)

## 4. 릴레이 기능 요구사항

| # | 요구 | 근거 |
|---|---|---|
| R1 | **투명 패스스루**: 양방향 전 프레임 (데이터 + **RTR**) 무손실 중계 | §2 — RTR 미중계 시 50 ms node guard 실패 → Seer 의 노드 상실 판정 |
| R2 | **처리량**: 지속 1,600 fps 이상 (버스당), 버스트 여유 포함 설계 목표 ≥ 2,500 fps | 실측 최대 1,601 fps, 부하 74 % |
| R3 | **지연**: 프레임당 중계 지연 최소화. 250 kbps 8-byte 프레임 시간 ≈ 0.44 ms — store-and-forward 시 홉당 +0.44 ms. SDO 왕복(요청+응답)에 릴레이 2회 개입 = **+0.9 ms/트랜잭션** | Seer 는 10 ms 폴링 주기에 노드 4개 인터리브 — 지연 누적 시 주기 붕괴 위험, §6 시험으로 검증 |
| R4 | **fail-safe**: 무전원/워치독 타임아웃 시 하드웨어 패스스루 복귀 | 아키텍처 D4 |
| R5 | **inject 모드**: PC(Personal Computer) 지령을 §3 프레임 사전과 **바이트 동일**하게 생성. 대상 = 0x60FF (N1·2), 0x607A + 0x6040 (N3·4) | 아키텍처 D6 |
| R6 | **SDO 충돌 방지**: CANopen SDO 는 노드당 단일 확인형 채널 — Seer 폴링과 PC 주입이 동시 진행되면 confirm 순서 붕괴. → inject 는 **Seer 의 쓰기 프레임을 가로채 데이터 필드만 치환**(write-substitute)하는 방식을 1차안으로 제안. Seer 의 읽기 폴링·node guard 는 그대로 투과시켜 Seer 오도메트리·감시 유지 | §2 폴링 구조 [제안 — ADR 필요] |
| R7 | **모드 게이트**: passthrough/inject 전환 권한 = PLC(Programmable Logic Controller) (2-key: PLC 허가 CAN + PC 명령 USB) | 아키텍처 D3·D14 |

## 5. 타이밍 예산 [실측 기반]

| 항목 | 값 | 여유 판단 |
|---|---|---|
| 프레임 시간 (8B, 250 kbps) | ~0.44 ms | — |
| 버스 유휴 시간 | 26–31 % | 신규 프레임 삽입 여유 = 초당 ~400 프레임분 — PLC↔Panda 직결 트래픽(D14)은 **별도 버스** 사용 권장 |
| Seer 위치 폴링 주기 | 10 ms/노드 | 릴레이 왕복 지연 +0.9 ms 는 주기 대비 9 % — 1차 판단 수용 가능, 실증 필요 |
| node guard 마진 | 50 ms 주기. 타임아웃 = 0x100C(Monitoring Time) × 0x100D(Life Time Factor), 초과 시 **HALT(모터 전원 유지)** | 실장값은 **드라이브 SDO 읽기로 직접 확인 가능** (0x100C/0x100D, RW 오브젝트). 출처: [Handbook V7.0, p142–144](../../References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf) |
| Seer SDO 타임아웃 | **미상** | 릴레이 지연 예산 확정의 최대 미지수 — Seer 설정/펌웨어에서 확인 (§7) |

## 6. 검증 계획 (제작 후)

1. **골든 트래픽 재생**: `expriments/can_data/*.asc.gz` 를 재생 장비로 양방향 재생 → 릴레이 통과 후 프레임 손실 0·순서 보존·RTR 중계 확인
2. **지연 실측**: 요청·응답 각각의 통과 지연 분포 (목표: p99 < 1 ms/홉)
3. **실차 passthrough 소킹**: 릴레이 삽입 상태로 §4 주행 레퍼토리(직진/횡행/스핀) 재현 — node guard 상실·SDO 타임아웃·statusword 이상 0건
4. **inject 리허설**: 정지 상태에서 0x60FF=0 치환 주입 → 쓰기 확인 응답 정상 수신 확인부터 단계 상승

## 7. 미해결 (설계 차단 요소 아님, 확정 필요)

- [ ] **Seer SDO 타임아웃** — Seer 설정 파일 확보 예정 (사용자, 2026-07-07). node guard 타임아웃은 드라이브 0x100C/0x100D SDO 읽기로 별도 확인 가능 (§5)
- [ ] 조향 카운트↔각도, 구동 rpm↔차속 환산 — Seer 모델 파일 (기어비·엔코더 분해능·휠 좌표)
- [x] ~~Tongyi statusword 0x?050 비트 정의~~ → **해소(2026-07-07)**: Handbook §6.6.2 대조 완료 — 상태 = "Switch on disabled"인데 구동됨 = 하드웨어 enable 추정, [분석 보고서 §5](../../expriments/can_data/analysis/2026-07-07_tongyi_can_analysis.md) 참조
  - ⚠ **정정 (2026-07-27 실기 검증) — "하드웨어 enable **추정**" 을 실측 확정으로 승급**(원문은 이력 보존을 위해 남긴다). 같은 캡처 안에서 statusword 하위바이트 `0x50`("Switch on disabled")이 **유지된 채로** 조향이 실제 프로파일 이동하는 것이 동시에 관측됐다: node3 `0x6041` = `0x9050` 유지 구간(`t=49.3267`~`52.5245`) 동안 `0x6064` 가 23,252(`t=49.3148`) → 7,882,008(`t=52.9354`) 로 137° 이동, 도달 시각 `t=52.9315` 에 `0x9450`(bit10 Target reached) 로 전이. 전 구간·전 노드 하위바이트는 `0x50` 고정(N1·N2 `0x8050` 420/420, N3·N4 는 상위 nibble 만 변동). 근거: `Log/homing_capture_220350.jsonl`, [Handbook V7.0 §6.6.2, 인쇄 page 150–151]
  - ⇒ **이 드라이브에서 `0x6041` 하위 4비트·bit9(Remote)는 CiA402 상태머신 의미로 동작하지 않는다.** enable/fault 판정에 하위바이트를 쓰지 말고 `0x603F`(error code) + `0x6078`(current) 로 할 것. 반대로 **상위 비트는 유효**하다 — `bit15` = Home attained [Handbook V7.0 §6.9, page 171], `bit10` = Target reached (§3 표 아래 정정 ① 참조)
- [ ] inject 방식 확정 (R6 write-substitute vs 마스터 대행) — ADR(Architecture Decision Record) 작성 필요
- [ ] 실차가 로그 취득 구성과 동일한지 (노드 수·비트레이트) 현장 확인

## 8. 프로토타입 플랫폼 — PCAN FD 2채널 (사용자 보유 장비, 2026-07-07 추가)

보유한 PCAN FD 2채널 장비(PEAK, CAN-FD 지원)로 **소프트웨어 릴레이 프로토타입** 구성 가능. FD 장비는 classic CAN 250 kbps 하위 호환.

**구성**: 기존 Seer↔모터 버스를 절단 → 채널 1 = Seer 측 세그먼트, 채널 2 = 모터 측 세그먼트, PC 소프트웨어가 양방향 포워딩.

```
Seer ──[세그먼트 A]── PCAN ch1 ═══ PC(포워딩) ═══ PCAN ch2 ──[세그먼트 B]── 모터 N1~N4
```

**용도별 판단**:

| 용도 | 판단 |
|---|---|
| §6 검증 계획 실행 (골든 재생·지연 실측) | ✅ 최적 — 즉시 착수 가능 |
| R6 write-substitute 실험 (inject 리허설) | ✅ 적합 — 소프트웨어라 수정 반복 빠름 |
| 최종 양산 릴레이 | ⚠ 제약 — PC/앱 다운 시 버스 단절 = **fail-stop**(모터는 node guard 타임아웃으로 정지). 아키텍처 D4 는 무전원 **passthrough** 복귀 요구 — fail-stop 이 수용 가능한지 별도 결정 필요 |

**구현 옵션**:
1. **Linux + socketcan + can-gw (권장)**: `cangw` 커널 게이트웨이로 in-kernel 포워딩(사용자 공간 왕복 없음, 추가 지연 최소) + ID 필터·프레임 수정 룰 지원 → write-substitute 실험까지 커버. PCAN 은 `peak_usb` 드라이버로 socketcan 네이티브 지원
2. Windows + PCAN-Basic API 사용자 루프: 구성 간단, 지연·지터 큼 — 기능 실험용

**테스트 킷 (2026-07-07 작성)**: [expriments/pcan_relay_test/](../../expriments/pcan_relay_test/) — socketcan 셋업·cangw 릴레이·사용자 공간 릴레이(inject 훅)·**Qt5(PyQt5) GUI 조작반**·골든 로그 변환기·지연 리포트 + 시험 절차 T0~T4 (README 참조). GUI 는 윈도우 PC 에서 `--selftest` 통과(mock 릴레이 무손실·처리지연 p50 23 µs), 실 CAN 연동은 리눅스 실기 대기

**배선·설정 주의**:
- 버스 절단 시 **두 세그먼트 각각 양단 120 Ω 종단** 필요 (절단점 쪽 종단은 PCAN 커넥터측에 추가; 장비 내장 종단 스위치 유무 확인)
- 비트레이트 250 kbps, **classic CAN 모드** (FD 프레임 송신 금지)
- **RTR 중계 확인** (R1): socketcan/can-gw 는 RTR 투과 — 초기 스모크 테스트에서 node guard 응답(0x70x) 왕복부터 확인
- 지연 실측: 장비 하드웨어 타임스탬프로 ch1 수신↔ch2 송신 차이 기록 → §5 타이밍 예산 검증
