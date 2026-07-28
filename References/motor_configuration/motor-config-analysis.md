# Tongyi 4축 모터 설정 분석 (EasyDRIVE Property window)

> 출처: `References/motor_configuration/*.png` (EasyDRIVE 설정 스크린샷, 실차 config). 검증 ✓ = 스크린샷 직접.
> 이 설정으로 이전 실측의 미확정 스케일(조향 counts→°, 구동 rpm→m/s, 위치 counts→m)이 확정됨.

## 노드 매핑 (canID) ✓
| canID = Node | Device | 역할 | 위치 x,y (m) | maxRPM | encoderLine | reductionRatio | 기구 |
|---|---|---|---|---|---|---|---|
| **1** | FrontWalk | 전 구동 | +0.6039, -0.0014 | 3000 | 16384 | **32** | wheelRadius 0.125 m |
| **2** | RealWalk(후) | 후 구동 | -0.5961, -0.0014 | 3000 | 16384 | **32** | wheelRadius 0.125 m |
| **3** | FrontSteer | 전 조향 | +0.6039, -0.0014 | 3000 | 16384 | **315** | 조향범위 -280~0° |
| **4** | RearSteer | 후 조향 | -0.5961, -0.0014 | 3000 | 16384 | **315** | steerOffset ~137~138° |

> ⚠ 정정(2026-07-27 — 스크린샷 재판독): 위 표 원문은 보존하되, 아래 3건을 정본으로 삼는다.
>
> **(1) node2 Device name 오기** — 원문 `RealWalk(후)` 는 파일명 `realwalk*.png` 에서 유래한 오기다.
> EasyDRIVE Property window 의 Device name 실제 값은 **`RearWalk`** 이다
> [`References/motor_configuration/realwalk1.png` — "Device name: RearWalk", canID 2].
> (node4 는 `RearSteer` 로 이미 올바름 [`realsteer1.png`] — 표 안에서 표기가 불일치했다.)
>
> **(2) steerOffset 은 근사 범위가 아니라 6자리 소수 정밀값이다** — `~137~138°` 로 뭉갠 탓에
> 「config 원본은 정밀값을 주지 않는다」는 판정이 파생됐다. 스크린샷 실제 값:
>
> | 노드 | minAngle | maxAngle | **steerOffset** | resetMode | 출처 |
> |---|---|---|---|---|---|
> | **3** FrontSteer | `-280.000000 °(+4.574613)` | `0.000000 °(+0.301932)` | **`138.000000 °(-0.726422)`** | `resetByDriver` | `frontsteer2.png` |
> | **4** RearSteer | `-280.000000 °(+4.987079)` | `0.000000 °(+0.301704)` | **`137.250000 °(-0.529735)`** | `resetByDriver` | `realsteer2.png` |
>
> **(3) 조향범위 `-280~0°` 는 node3 전용이 아니다** — 원문은 node3 행에만 적혀 node4 가 다른 범위인 것처럼
> 읽혔으나, 두 조향축의 minAngle/maxAngle 은 **동일**하고 노드별로 다른 것은 steerOffset 뿐이다
> [`frontsteer2.png` / `realsteer2.png`].

- 구조: **전/후 2모듈, 각 모듈 = 구동+조향 독립** (dual-steer AGV). **휠베이스 = 0.6039-(-0.5961) = 1.200 m**.
- inverse 체크됨(전 노드), currentFactor 1.0, steerResolution 0.1°, positionSpeed 30°/s, func 모드: walk/spin/steer/linear/rotation.

### 호밍·원점·리밋 파라미터 ✓ (2026-07-27 보강 — 원문 누락분)

> 이 절은 정정이 아니라 **원문에 통째로 빠져 있던 항목의 추가**다. config 정본 파생문서인데
> 원점이 어디서 오는지를 문서만 보고는 알 수 없었다.

- **컨트롤러(EasyDRIVE) 레벨 DI 미사용**: 4노드 모두 `upLimitDI = downLimitDI = zeroDI = -1`,
  `motorDI = none` [`frontsteer1.png`/`realsteer1.png`/`frontwalk2.png`/`frontsteer3.png`].
  > ⚠ 이것을 **「리밋 스위치가 없다」로 읽지 말 것**(2026-07-27 실기 검증으로 반증됨).
  > 뜻하는 바는 「상위 컨트롤러가 리밋/제로 스위치를 직접 읽지 않는다」이며, 실제 리밋은
  > **드라이브 자체 입력**으로 들어온다 — 전 노드 `0x6098(Homing method) = 1` 실기 판독,
  > 즉 **Home 1 = 음(−)의 리밋 트리거 신호** 방식이고 [Handbook V7.0 §4.6 page 116 · 기본 RstMode=1],
  > 리밋 상태는 `0x6000` sub 1 의 **bit3(−Limit)** 으로 노출된다
  > (`Log/homing_capture_220350.jsonl` — 조향 노드 bit3 세트 t≈47.0, `0x6041` bit15 0→1 t≈49.0).
- **outEncoder 미사용**: 4노드 모두 `outEncoderLine = -1`, `outEncoderBrand = none`
  → 각도는 모터측 16384 라인 엔코더로만 산출(= 57,344 counts/°) [`frontsteer2.png`, `frontsteer3.png`].
- **resetMode**: 조향(node3·4) = `resetByDriver`, 구동(node1·2) = `none`.
  선택지는 `none / resetBySpeed / resetByDriver` 3종 [`toggle3.png`].
  → 원점 복귀를 **드라이브 내부 호밍에 위임**한다는 뜻. 상위(Seer)가 `0x6098`(method)을 한 번도 쓰지 않고
  `0x6099`(호밍속도) + `0x60FB.4`(RstStart)만 쓰는 실측과 정합
  (`Log/homing_capture_220350.jsonl` 253,510 프레임 전수 스캔에서 **0x6098 write·read 0건**).
  ⚠ 따라서 다른 통합사 코드처럼 `0x6098 = 35`(Home 35)를 흉내내면 RstMode 가 0(호밍 꺼짐)으로 리셋되어
  [Handbook V7.0 §4.6 page 122] Seer 호밍이 죽는다.
- **구동축(node1·2)은 호밍하지 않는다** — `resetMode = none` [`frontwalk2.png`] 이고, 실측에서도 Seer 는
  조향 노드에만 호밍 프레임을 보냈다(`Log/homing_capture_220350.jsonl`). 구동륜에 기계적 원점은 없다.
- **조향 프로파일**: `maxSpeed 0.005 °/s`, `maxAcc/maxDec/maxJerk 0.100000`, `positionSpeed 30.000000 °/s`,
  `bySpeed` 미체크, `steerOffsetFile` 빈칸, `steerResolution 0.100000°` [`frontsteer2.png`/`realsteer2.png`].
  ⚠ `maxSpeed 0.005 °/s` 는 실동작(호밍 후 137° 복귀에 약 3.4 s ≈ 40 °/s,
  `Log/homing_capture_220350.jsonl` t=49.14 지령 → t=52.6 수렴)과 4자리 어긋나 실효성 미확인.
- **구동 파라미터**: `wheelRadius 0.125 m`, `reductionRatio 32`, `minimumSpeed 0.050000`,
  `deltaCnt -1`(위치편차 감시 off), `deadDealerK 100.000000` [`frontwalk2.png`].
- **brand**: `Tongyi-IxL-CANOpen` (전 노드) [`frontsteer3.png`].

### 괄호값 `°(x)` 의 의미 — ⚠ 추정(수치 근거는 강함)

`유효값 = 표시값 + x`, x 의 단위는 표시 필드와 같은 **도(°)**.
- 근거: `(138.000000 + (-0.726422)) × 57344 = 7,871,816` ≈ 저장소 상수 `STEER_HOME[3] = 7,871,815` (Δ 1.06),
  `(137.250000 + (-0.529735)) × 57344 = 7,840,087` ≈ `STEER_HOME[4] = 7,840,086` (Δ 0.88)
  — **두 독립 노드가 같은 상수 C ≈ 57,344.007 로 닫힌다.**
- 배제된 해석: 라디안 변환(단위 불일치), 필드값의 선형함수(3점 피팅 불일치), 기어비 환산.
- ⚠ `maxAngle`/`minAngle` 의 괄호값에는 동일 규칙을 검증할 교차 데이터가 없다 — 부호 방향 미확정.

## ★ 스케일 확정

### 조향 (B5) — counts ↔ 각도
- counts/° = encoderLine(16384) × 4(쿼드러처) × reductionRatio(315) / 360 = **57,344 counts/°**
- **검증**: 실측 "홈→회전/크랩 자세" 0x607A Δ = **+5,160,960 counts** ÷ 57,344 = **정확히 90.00°** ✅
  → 크랩·회전 시 바퀴는 **정확히 90° 조향**. 크랩 미세조정 ±7,617 counts = **±0.13°**.
- (16384×4=65536 counts/모터rev 가정이 90.0° 로 정확 일치 → 쿼드러처 ×4 확정)

### 구동 속도 (B6) — 0x60FF ↔ 차속
- 0x60FF Target velocity 단위 = 0.1 rpm(모터). 차속 = V×0.1 ÷ 32(reduction) ÷ 60 × (2π×0.125m)
- 환산: **1 unit(0.1rpm) ≈ 4.09e-5 m/s**
  | 실측 지령 | 모터 rpm | 차속 |
  |---|---|---|
  | ±2,445 (재생/T2) | ±244.5 | **±0.10 m/s** |
  | ±4,889 (수동) | ±488.9 | ±0.20 m/s |
  | ±24,447 (자율) | ±2,444.7 | ±1.00 m/s |
  | maxRPM 3000 | 3000 | **1.23 m/s (최대)** |

### 구동 위치 (B6) — 0x6064 counts ↔ 거리
- counts/m = 16384 × 4 × 32 ÷ (2π×0.125) = **2,670,177 counts/m** (≈2.67M/m)
- 검증: node1 실운전 Δ ≈ -24.07M counts ÷ 2.67M ≈ **-9.0 m** 이동.

## 미확정 잔여
- Current(0x6078) 단위(0.01A vs 1mA) — config 는 currentFactor 1.0 만 제공, 단위 직접값 없음 → 실측 대조 필요.

  > ⚠ 정정(2026-07-27 — 1차 source 대조로 해소): 단위는 **미확정이 아니다**.
  > **`0x6078 = Current_actual_Value, INT16, RO, Unit: 0.01 A`**
  > [`References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt:9614`
  > (Appendix I 대상물 사전)]. config 의 `currentFactor 1.0` 은 스케일 미변경을 뜻할 뿐이다.
  > 자매 문서 `References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md:239` 은 이미
  > 0.01 A 로 갱신돼 있어, 이 문서만 stale 이었다(두 문서 불일치 상태였음).
  > - ⚠ 같은 Handbook 의 `:9339` 행은 동일 오브젝트를 **UINT16** 으로 상충 기재한다. 실측이 음수를 포함하므로
  >   **INT16 이 실제와 부합**한다 — `Log/homing_capture_220350.jsonl` node1 raw `0xfee2` = **−286** (t=0.0355).
  > - 남은 미확정은 **단위가 아니라** ① 모터 **정격전류 값**(CANopen 미노출, MODBUS 측 파라미터로만 취득 가능)과
  >   ② 정격 대비 실측 대조(과부하 임계 산정)다.

- 조향 절대 원점(steerOffset 137~138°) ↔ 0x6064 절대값 대응은 별도 확인 권장.

  > ⚠ 정정(2026-07-27 — 실기 호밍 캡처로 **해소**): 대응이 3중으로 확정됐다.
  > 근거는 `Log/homing_capture_220350.jsonl`(Seer 주도 호밍, 253,510 프레임 수동청취) + 위 스크린샷.
  >
  > **(1) 대응식: `(steerOffset + 괄호값) × 57,344 = 호밍 전 절대 홈 counts`**
  > | 노드 | 계산 | 계산값 | 저장소 `STEER_HOME` | Seer `0x607A` 지령 (t=0.035) | baseline `0x6064` (t=0.034) |
  > |---|---|---|---|---|---|
  > | 3 | (138.000000 − 0.726422) × 57344 | **7,871,816** | 7,871,815 (Δ1.06) | 7,871,815 | 7,871,818 |
  > | 4 | (137.250000 − 0.529735) × 57344 | **7,840,087** | 7,840,086 (Δ0.88) | 7,840,086 | 7,840,084 |
  >
  > **(2) 원점(0x6064 = 0) 은 음(−)의 리밋 트리거 위치다** — Home 1 방식, 전 노드 `0x6098 = 1` 실기 판독
  > [Handbook V7.0 §4.6 page 116]. 캡처에서 `0x6000` sub 1 bit3(−Limit) 세트 t≈47.0
  > → `0x6041` bit15 0→1(호밍 완료) t≈49.0. 호밍 진행 구간(t≈18.0~49.2) 동안 `0x6064` 는 두 조향 노드 모두
  > 정확히 0 을 반환한다(실위치 아님).
  >
  > **(3) ⚠ 홈 counts 는 전원 사이클 불변 상수가 아니다** — 호밍 **전**과 **후**의 목표가 같은 세션 안에서 바뀐다.
  > | 노드 | 호밍 전 `0x607A` | 호밍 후 `0x607A` (t≈49.14 전환) | Δ counts | Δ 각도 | 호밍 후 정착 `0x6064` |
  > |---|---|---|---|---|---|
  > | 3 | 7,871,815 | **7,882,020** = +137.4515° | +10,205 | +0.178° | 7,882,001 (t≈53.0 수렴) |
  > | 4 | 7,840,086 | **7,859,062** = +137.0512° | +18,976 | +0.331° | 7,859,065 |
  >
  > ⇒ 절대 counts 를 하드코딩하지 말고, **매 기동 호밍 후 `0x6064` 리드백을 정본**으로 삼을 것.
  >
  > **(4) 콜드부팅 직후의 137° 조향 스윙은 이상거동이 아니다** — 호밍 완료 후 원점(리밋)에서
  > 조향 0°(= steerOffset 위치)로 복귀하는 **설계된 이동**이다. 실측 소요 약 3.4 s
  > (`Log/homing_capture_220350.jsonl` t=49.14 지령 → t≈52.6 수렴). 「원인 미상」·「이상 스윙」·
  > 「Home 36/37 기계 하드스톱」 류 서술은 오류다. 또한 호밍은 **원점 경유 → 조향 0° 복귀까지**이며
  > 원점에 머무르지 않는다(리밋에 얹힌 채 두면 그 방향 지령이 막힌다; 실측상 bit3 는 복귀 이동 중 해제).
  >
  > **(5) 잔여 미확정**: 정착값이 EasyDRIVE steerOffset(138.000 / 137.250) 대비 각각 −0.5485° / −0.1988° 낮다.
  > 「직진 자세 = 육안 0°」 여부, 그리고 Seer 측 `encoder ≈ −7,871,810` 의 **부호**는 미확정.

## 실측 실험 문서 갱신 대상
- `experiences/can-decode/*maneuver-analysis*`, `*realop-estop*`: 조향 5.16M = 90°, 속도 ±0.1~1.0 m/s, 위치 2.67M counts/m 로 정량 보강.
