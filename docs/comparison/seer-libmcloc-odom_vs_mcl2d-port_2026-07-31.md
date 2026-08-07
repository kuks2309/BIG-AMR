# Seer libMCLoc 오도메트리(odometry) 처리 ↔ mcl2d 이식본 대조

> 2026-07-31 (KST) · 대상: rbk(Robokit) 3.4.5.20 `libMCLoc.so` 2D 위치추정 ↔ 본 저장소 `src/Navigation` 이식본
> 질문: **"기존 Seer 의 위치 추종에서 odom 을 어떻게 처리하는가"**
> v2 (2026-07-31) — 원본 바이너리·배포 파라미터를 **직접 조회**해 v1 의 ⓦ 항목 대부분을 ✓ 로 승격하고,
> 참조 분석 문서의 서술 1건을 반증했다(§6).
> v3 (2026-07-31) — `supplyControlVar` 의 인자 `d` 를 호출지 전수 스캔으로 확정(`0.0`) → 예측 단계 노이즈 소멸.
> v4 (2026-07-31) — 산포 주체(`doExtraMove`)와 그 크기를 정하는 **6개 업데이트 모드**를 CFG(Control Flow Graph)
> 추적으로 완전 복원(§1.1.1·§1.1.2). 예측 경로 미해결 항목 없음.

## 0. 근거 / 검증 등급

| 기호 | 의미 |
| --- | --- |
| **✓** | 이 세션이 1차 source(바이너리·배포 파라미터) 또는 저장소 코드를 직접 확인 |
| **ⓦ** | 분석 문서 보고만, 이번에 재확인하지 않음 |
| **⚠** | 추론·미확정 |

1차 source 접근 경로(2026-07-31 확보): `ssh amap@amap-1` → 63G 원본 하드
`/media/amap/6ab6980d-…`(Seer AMR 루트파일시스템 사본, **읽기 전용 취급**).
- 바이너리 `…/usr/local/SeerRobotics/rbk/plugins/libMCLoc.so` (179,436,032 B, 2023-06-21) — `nm`/`objdump`/`readelf` 로 조회
- 배포 파라미터 `…/usr/local/etc/.SeerRobotics/rbk/resources/params/robot.param`(SQLite) — `/tmp` 사본을 `mode=ro` 로 조회, `MCLoc` 테이블 101키
- 접근법·함정은 [docs/network/seer_network_access.md §amap-1](../network/seer_network_access.md)

분석 문서(2차 자료)는 [References/seer/libMCLoc/](../../References/seer/libMCLoc/PROVENANCE.md).

## 1. Seer 가 odom 을 쓰는 다섯 갈래

| # | 갈래 | 요지 | 등급·근거 |
| --- | --- | --- | --- |
| 1 | **진입** | odom 은 자세 3개가 아니라 `ControlVar2D{x, y, angle, is_stop, timestamp}` 로 들어간다. 메인루프 `RunNew` 게이트가 `odom_received_ && laser_received_` 를 AND 로 요구 | ⓦ deep-dive §2·§6.6④ |
| 2 | **예측** | 아래 §1.1 — 오도 증분을 로봇좌표로 분해해 (병진·방향·회전) 3값으로 저장하고, **병진과 회전에만** 균등 노이즈를 얹는다 | ✓ `doParticleMoveAction` @0x33cb70, `supplyControlVar` @0x33ce70 직접 디스어셈블 |
| 3 | **관측 대체(OdoOnly)** | `robot_pos_likelihood_ < OnlyOdoLikelihoodThreshold` → `loc_state_=kLocOdo`(오도 전용 추측항법). **단 배포값이 `0.0` 이라 이 배포에서는 발동하지 않는다**(우도는 0 미만이 될 수 없음) | 로직 ⓦ deep-dive §6.6② · **배포값 ✓** `robot.param` `OnlyOdoLikelihoodThreshold=0.0` |
| 4 | **정지 처리** | `StopRelocWhenOdoStop` = "오도가 정지를 보고하면 PF(Particle Filter) 위치추정을 멈춘다". **배포값 1(활성)** | 배포값 ✓ `robot.param` · 동작 ⓦ |
| 5 | **무결성 감시(슬립)** | 병진 게이트 `D_odo>CheckDistance ‖ D_state>CheckDistance`, 그 안에서 `D_state>2×D_odo ‖ D_odo>2×D_state` → skid. 회전 `|Δθ 불일치|>CheckAngle` → skid. 복구는 정지 후 `recoverTime` 경과. **배포값 `CheckDistance=1.0`(m) · `CheckAngle=30.0`(°) · `recoverTime=1.0`(s)** | 판정식 ⓦ deep-dive §6.6③ · **배포값 ✓** |

### 1.1 예측 단계 — 실제 식 ✓

`supplyControlVar(const ControlVar2D&, double)` @0x33ce70 이 오도 증분을 분해해 멤버에 적재한다
(`prev` = 직전 오도 사본 @0x58/0x60/0x68, `cur` = 이번 오도 @0x228/0x230/0x238):

```
Δx = cur.x − prev.x ;  Δy = cur.y − prev.y                     # 33cf1e, 33cf2d
Δx_b =  Δx·cos(θ_prev) + Δy·sin(θ_prev)   → m[0x80]            # 33dd27  (로봇 전방 성분)
Δy_b =  Δy·cos(θ_prev) − Δx·sin(θ_prev)   → m[0x88]            # 33dd3c  (로봇 좌측 성분)
m[0x90] = Normalize(cur.angle − prev.angle)                     # 33dd6a  (dθ)
m[0x98] = sqrt(Δx_b² + Δy_b²)                                   # 33dd8b sqrtsd → 33dd9a (병진량)
m[0xa0] = atan2(Δy_b, Δx_b)                                     # 33ddb5 → 33ddba (이동 방향, 직전 헤딩 기준 상대각)
m[0xa8] = m[0x1a0] × 1000 × d / 1000        (= m[0x1a0]·d)      # 33cec9~33cf03 (병진 노이즈 스케일)
m[0xb0] = m[0x1a8] × π/180 × d / 1000                           # 동상            (회전 노이즈 스케일)
```
`d` 는 두 번째 인자. 두 노이즈 스케일 모두 `mulpd` 로 **`d` 에 선형 비례**한다.

**그리고 그 `d` 는 이 배포에서 항상 `0.0` 이다** ✓ — `.text` 전수 스캔(PLT 스텁 `0x1b15b0` 대상 `E8` 호출)으로
호출지가 정확히 2곳이고 둘 다 리터럴 0을 싣는다:

| 호출지 | 소스(DWARF / Debugging With Attributed Record Formats) | 인자 적재 |
| --- | --- | --- |
| `MCLoc::DoMoveAction` → `ParticleFilter2D::supplyControlValue`(단순 전달, `ParticleFliter2D.cpp:505`) | `pfLoc.cpp:465` | `xorps %xmm0,%xmm0` @0x3d7cfe |
| `MCLoc::OdometerMoveAction` (직접 호출) | `pfLoc.cpp:492` | `xorpd %xmm0,%xmm0` @0x3d7e51 |

`rbk/` 트리 전체에서 이 심볼을 참조하는 파일은 `libMCLoc.so` 하나뿐이고(`grep -rl`), 함수 주소를 값으로
싣는 참조(ABS64·`lea rip-rel`)도 0건이다 → **다른 호출 경로 없음.**

⇒ `m[0xa8] = m[0xb0] = 0` ⇒ **`doParticleMoveAction` 의 노이즈 항은 소멸한다. 예측은 순수 결정론적 오도 적용이다.**

`doParticleMoveAction(MCLParticle2D&)` @0x33cb70 이 파티클마다:

```
R = m[0x98] + U(−0.5, +0.5)·m[0xa8]        # RangeRandom(−1000,1000) / 2000.0
Φ = particle.θ + m[0xa0]
particle.x += R·cos(Φ)                      # 33cc30
particle.y += R·sin(Φ)                      # 33cc7a (y·θ 동시 저장, addpd)
particle.θ  = Normalize(particle.θ + m[0x90] + U(−0.5,+0.5)·m[0xb0])   # 33cc83
```

상수 실측(`readelf -S` + 파일 오프셋 역산): `0x59fef0 = 2000.0`, `0x562998 = 1000.0`,
`0x562b00 = {1000.0, 1000.0}`, `0x562978 = 180.0`.

**핵심 1**: 노이즈 항의 *형태*는 이동 거리 R 과 회전각에 대한 가산이다(이동 *방향* Φ 에는 노이즈 없음).
등방(等方) 디스크 산포가 아니다.
**핵심 2**: 그나마도 `d=0` 이라 이 배포에서는 **예측 단계에 노이즈가 전혀 없다.**

### 1.1.1 그러면 파티클 산포는 어디서 오는가 — `doExtraMove` ✓

`ParticleFilter2D::ThreadFunc1/2`(`ParticleFliter2D.cpp:56`·`:77`)는 `Whats2Run` 을 switch 로 갈라
파티클마다 **셋 중 하나만** 호출한다(각 case 가 공통 tail 0x341130 로 점프 — 상호배타):

| case | 호출 | 내용 |
| --- | --- | --- |
| `kOffset` | `doOffsetMove` @0x1aec00(plt) | — |
| `kMove` | `doParticleMoveAction` @0x34105b·0x342065 | 위 §1.1 (노이즈 0) |
| `kExtraMove` | `doExtraMove` @0x341071·0x34207c | **실제 산포** |

`doExtraMove` @0x33cca0 은 x·y 에 **각각 독립** 균등 노이즈를, θ 에 각도 노이즈를 준다(정사각형 산포):

```
x += U(−0.5,+0.5)·m[0xb8]                      # 33cce8
y += U(−0.5,+0.5)·m[0xb8]                      # 33cd25   (같은 스케일, 독립 난수)
θ  = Normalize(θ + U(−0.5,+0.5)·(m[0xc0]·π/180))   # 33cd38~33cd7f
```

`m[0xb8]`·`m[0xc0]` 는 `setExtraMoveParams(double,double,StateVar2D)` @0x33f2b0 이 세팅한다.

### 1.1.2 산포 크기 결정 — 6개 모드 완전 복원 ✓

`MCLoc::DoNormalUpdateAction` 이 매 주기 **업데이트 모드**를 고르고 그 모드의 (거리, 각도) 쌍을
`setExtraMoveParams` 로 넘긴다(호출지 7곳 + `DoRelocAction` 1곳). 모드 번호는 로그 `MCLocUpdateMode` 에
double 로 찍힌다(초기값 −99).

**판정에 쓰는 값** (함수 도입부에서 계산):
```
getCurrentControlVar(cv)                                    # 33ca663
dist   = hypot(cv.x − accum.x, cv.y − accum.y)              # 3ca683~3ca6ce → [rsp+0xf0]  (mm)
dθ_deg = (cv.angle − accum.angle) × 180/π                   # 3ca6d7~3ca6ea → [rsp+0x100]
w      = getParticleLikelihood(추정 자세)                    # 3ca5f6 → 파티클 weight [rsp+0x2b8]
accum ← cv                                                   # 3ca703  (기준점 갱신)
```
비교 임계는 `MCLParams2D` 사본(`MutableParam` 값 +0x38)에서 읽는다:
`0x3d0d288 = ExtraMoveDistThreshold(20 mm)` · `0x3d0d290 = ExtraMoveAngleThreshold(1°)` ·
`0x3d0d250 = BestParticleTolerantThreshold(0.8)`.

**모드 결정 트리와 산포 값** (CFG 추적으로 확정, 배포값 대입):

| 조건 | 모드 | `setExtraMoveParams(거리, 각도)` | 실효값 |
| --- | --- | --- | --- |
| `\|m19e0\|>ε` 또는 `\|m19e8\|>ε` | **6** | `(m[0x19e0], m[0x19e8])` | **미발동** — 두 멤버는 ctor(`MCLoc.cpp:102`)와 `CheckLocState`(`:1648`·`:1687`)에서 0 으로만 쓰이고 `.text` 전체에 다른 writer 가 없다 |
| `dist>20` · `dθ>1°` · `w<0.8` | **1** | `(ParticleExtraMoveRadius, ParticleExtraMoveAngle)` | 40 mm · 3° |
| `dist>20` · `dθ≤1°` | **2** | `(ParticleExtraMoveRadius, 상수 2.0)` | 40 mm · 2° |
| `dist≤20` · `dθ>1°` · `w<0.8` | **3** | `(ParticleMoveRadius, ParticleExtraMoveAngle)` | 10 mm · 3° |
| `dist≤20` · `dθ≤1°` | **4** | `(lowSpeedMoveRadius, lowSpeedMoveAngle)` | 10 mm · 1° |
| `dθ>1°` · `w≥0.8` (거리 무관) | **5** | `ForceExtraMove` ? `(ForceExtraMoveDist, ForceExtraMoveAngle)` : `(상수 10.0, ForceExtraMoveAngle)` | 배포 `ForceExtraMove=0` → 10 mm · 2° |

읽는 법: **많이 움직였는데 신뢰도가 낮으면 크게(40 mm·3°) 뿌리고, 신뢰도가 높으면 작게(10 mm·2°) 뿌리며,
거의 안 움직였으면 최소(10 mm·1°)** 로 줄인다. 회전이 없으면 각도 산포를 2° 로 고정한다.
`doExtraMove` 는 이 값을 `U(−0.5,+0.5)` 로 곱하므로 **실제 1σ 아닌 반폭**이다 — 예: 모드 1 이면
x·y 각각 ±20 mm, θ ±1.5° 범위 균등.

이것이 deep-dive §3.2 가 한 줄로 적은 "정지/저속/이동 모드별 노이즈 스케일 분기"의 실체다.

### 1.2 odom 관련 배포값 (robot.param `MCLoc`) ✓

```
ParticleMoveRadius       10.0     ParticleExtraMoveRadius   40.0    ParticleExtraMoveAngle   3.0
lowSpeedMoveRadius       10.0     lowSpeedMoveAngle          1.0    MotorStopThreshold       0.02
ExtraMoveDistThreshold   20.0     ExtraMoveAngleThreshold    1.0    ForceExtraMove           0
OdoDistError             0.05     OdoAngleError              0.7    UseOdoVxVyVRotate        0
OdoLostTimeThresh        300      ScanLostTimeThresh         300    StartLaserOdo            0
OnlyOdoLikelihoodThreshold 0.0    StopRelocWhenOdoStop       1      RefLikelihoodThreshold   0.95
CheckDistance            1.0      CheckAngle                30.0    recoverTime              1.0
CheckFactor              0.1      useRTKLocalization         1      RTKWeight                0.05
```

- 산포·슬립 파라미터는 전부 정의표 기본값과 동일 → **이 로봇은 odom 관련 튜닝을 하지 않았다** ✓
- `StartLaserOdo = 0` — Seer 에도 레이저 오도 옵션이 있으나 **꺼져 있다**(배포는 휠 오도 전용) ✓
- `useRTKLocalization = 1` 은 켜져 있으나 실제 GNSS 수신 여부는 미확인 ⚠ (2D 실내 AMR 범위 밖)

### 1.3 odom 생산 측 (robot.param `OdoCalculator`) ✓

```
FlagCumEncPoseMode 1   FlagConsistentCheck 0   ThresConsistent 0.02   FlagOdomDebugMode 0
MotorFollowMonitorErrThres 0.1   …WarnThres 0.05   …ErrWin 1.0   …WarnWin 0.5   …Delay 0.05
LinMotorMonitorErrThres 0.01   LinMotorMonitorWarnWin 2.0   FlagSetMotorFollowingError 0
```
`FlagCumEncPoseMode=1` → **엔코더 누적 자세 모드**. 나머지는 모터 추종오차 감시 임계다.
odom 자체의 기구학(`*Odometer::CalSpeed`)은 이 테이블 밖이며 이번 조회 범위 아님 ⚠.

## 2. 이식본 현황 ✓

| 갈래 | 이식 상태 | 위치 |
| --- | --- | --- |
| 1 진입 | `Pose2D` 2개(prev/cur)만. `is_stop`·`timestamp` 없음. `/odom` 콜백이 곧 한 스텝 | [node:56-85](../../src/Navigation/mcl2d_ros2/src/mcl2d_localization_node.cpp#L56-L85) · [types.hpp:29-33](../../src/Navigation/mcl2d_core/include/mcl2d_core/types.hpp#L29-L33) |
| 2 예측 | 증분 재투영(원본과 동일 구조) + **등방 디스크 산포**(반경 U(0,1)·10mm, 방향 U(0,2π)) + 헤딩 U(±3°) | [motion_model.cpp:20-41](../../src/Navigation/mcl2d_core/src/motion_model.cpp#L20-L41) |
| 3 OdoOnly | **미구현** — `LocMode::Odo` 열거만 있고 사용처 0건 | [types.hpp:61-73](../../src/Navigation/mcl2d_core/include/mcl2d_core/types.hpp#L61-L73) |
| 4 정지 처리 | **미배선** — 파사드가 `stopped`/`dt` 를 받지만 전 호출부가 생략(기본 `false`, `0.05`) | [mcl2d_localizer.hpp](../../Tools/mcl2d_standalone/include/mcl2d_localizer.hpp) · 호출부 node:70, main.cpp:98, real_map_demo.cpp:124 |
| 5 슬립 | 판정식·상수 이식됨(1.0m·2.0배·30°·1.0s) — **배포값과 일치 확인** | [skid_detector.cpp:30-45](../../src/Navigation/mcl2d_core/src/skid_detector.cpp#L30-L45) · [types.hpp:116-120](../../src/Navigation/mcl2d_core/include/mcl2d_core/types.hpp#L116-L120) |

## 3. 차이 5건과 영향

| # | 원본 | 이식본 | 영향 |
| --- | --- | --- | --- |
| **D1** | 예측(`kMove`)에 **노이즈 없음**(`d=0` 이라 항 소멸). 산포는 **별도 액션 `kExtraMove`** 가 x·y 독립 균등(정사각형)으로 수행하고, 그 크기는 매 주기 모드별로 재설정 ✓ | 예측 한 단계에 **등방 디스크 산포**를 섞어 넣음. 별도 ExtraMove 액션 없음 | 원본은 "결정론적 예측"과 "산포"를 **분리된 액션**으로 두고 상황(정지/저속/이동)에 맞춰 산포만 조절한다. 이식본은 둘을 합쳐 놓아 **상황별 조절 지점이 없다** |
| D2 | 자체 루프 + `odom_received_ && laser_received_` 게이트 | `/odom` 콜백 = 스텝 | odom 발행률이 곧 필터 주기. 스캔은 최신값 재사용 |
| D3 | `is_stop` + `StopRelocWhenOdoStop=1`(배포 확인) 로 정지 시 PF 정지 | 미배선(`stopped=false` 고정) | 정지 중에도 매 주기 산포 확산. **슬립 복구 조건(정지 후 1s)이 성립 불가 → 한 번 Skidding 이면 복귀 불가** |
| D4 | `kLocOdo` 강등 로직 존재. **단 배포 임계 0.0 이라 이 로봇에선 미발동** | 미구현 | **차이의 실질 영향 없음**(원본도 안 쓰는 경로) — v1 에서 과대평가했던 항목 |
| D5 | 휠 오도 전용(`StartLaserOdo=0` 확인) | 휠 오도 부재 → `icp_odometry`(레이저) | **D5×#5 결합이 구조적 함정**: 슬립 감지가 레이저↔레이저 비교가 되어 휠 미끄러짐 검출 의미를 상실 |

> 본 표는 **차이의 기록**이며 수정 지시가 아니다. D1 을 맞추려면 `motion_model.cpp` 의 산포를
> "R 에 가산 + 방향 무노이즈" 로 바꾸면 되고, D3 은 `stopped` 배선만으로 닫힌다.

## 4. 남은 미확정 ⚠

| 항목 | 상태 |
| --- | --- |
| ~~`supplyControlVar` 의 인자 `d`~~ | **해소** — 호출지 2곳 모두 리터럴 `0.0`(§1.1) |
| ~~`setExtraMoveParams` 호출지 ↔ 파라미터 대응~~ | **해소** — 6개 모드 결정 트리·임계·실효값 전부 확정(§1.1.2) |
| ~~`m[0x1a0]`·`m[0x1a8]`~~ | **무의미로 확정** — `d=0` 이라 결과에 기여하지 않음 |
| `m[0x19e0]`·`m[0x19e8]`(모드 6 입력)의 의미 | ctor·`CheckLocState` 에서 0 으로만 쓰이고 `.text` 전체에 다른 writer 가 없어 **이 빌드에서는 모드 6 미발동**. 두 값의 원래 의도(외부 지정 산포로 추정)는 미확정 ⚠ — **동작에는 영향 없음** |
| odom 생산 기구학(`*Odometer::CalSpeed`) | `libMCLoc.so` 밖(섀시 플러그인). 위치추정 범위 아님 |
| `OdoDistError` 0.05 / `OdoAngleError` 0.7 용처 | 배포값은 확인. 참조 지점 역추적 미실시 |
| kMove ↔ kExtraMove 승격 조건 | `ExtraMoveDistThreshold`(20)·`ExtraMoveAngleThreshold`(1) 가 그 역할로 보이나 분기식 미확인 |
| odom 생산 기구학(`*Odometer::CalSpeed`) | `libMCLoc.so` 밖(섀시 플러그인). 이번 범위 아님 |

## 5. 표기 주의 (원문 그대로 두는 것)

- `tuning_parameters.md` #44/#45(및 #49/#50, #87/#88) 의 description 이 **서로 뒤바뀌어** 있다
  (`ScanLostTimeThresh` 설명이 "receiving odometer", `OdoLostTimeThresh` 설명이 "receiving laser scan").
  원본 문자열이 그러하므로 이름 기준으로 해석한다.
- 원본 바이너리에 `KLD`·`AMCL` 문자열이 없다(deep-dive §1). 적응 표본수는 정식 KLD(Kullback-Leibler Distance)-sampling 이
  아니라 단순 선형 `n = k × 2.5` 다. Seer 위치추정을 "AMCL(Adaptive Monte Carlo Localization)" 로 부르지 않는다.
- 3D·반사판·태그·SLAM·특징·RTK(Real-Time Kinematic) 백엔드는 2D AMR(Autonomous Mobile Robot) 범위 밖이며 이식 대상이 아니다
  ([mcl2d_core/README.md:5](../../src/Navigation/mcl2d_core/README.md#L5), debt-013).

## 6. 참조 분석 문서 반증 1건

[deep-dive §6.5②](../../References/seer/libMCLoc/2026-06-24-localization-deep-dive.md) 는 모션 노이즈를 이렇게 서술한다:

> `RangeRandom(int,int)`(균등난수) **2회**(@0x33cba8, 0x33cbde) + `cos`/`sin` → `r·cosθ, r·sinθ` 디스크 산포.

**디스어셈블 직접 확인 결과 "디스크 산포" 는 성립하지 않는다.** 두 난수는 (반지름, 방향) 이 아니라
**(병진 노이즈, 회전 노이즈)** 이고, `cos`/`sin` 의 인자는 난수가 아니라 결정론적 헤딩 `particle.θ + m[0xa0]` 이다
(§1.1 의 33cc11~33cc7a). 인용된 두 주소(0x33cba8·0x33cbde)는 정확하며, 그 반환값의 *용처* 해석이 어긋난 것이다.

더구나 그 노이즈 항은 **이 배포에서 실행되지도 않는다**(`d=0`, §1.1). 실제 산포는 별도 액션 `kExtraMove`
(`doExtraMove`)가 담당한다 — 즉 §6.5② 는 *형태*(디스크 vs 병진·회전 가산)와 *소재*(move vs extraMove)
두 가지가 모두 어긋나 있다.

이식본 [motion_model.cpp:33-41](../../src/Navigation/mcl2d_core/src/motion_model.cpp#L33-L41) 은 이 서술을 그대로 구현해
디스크 산포를 넣었다 → §3 D1 의 근원. 원본 문서는 수정하지 않는다(외부 참조는 원문 보존, handling.md §1).

---

## 7. 원본 대조 실측 (2026-08-06) — "동일한가"에 대한 답

리버스 엔지니어링(Reverse Engineering) 제1원칙([principle.md](../claude_guideline/reverse_engineering/principle.md) §1)이
인정하는 유일한 증명은 **원본 입력으로 양쪽을 구동해 비트 대조**하는 것이다. 2026-07-31 시점의 이식본은
구조를 디스어셈블로 맞췄을 뿐 그 대조를 하지 않았다. 2026-08-06 에 오라클을 만들어 실제로 돌렸다.

### 7.1 오라클 결과 ✓

`src/Navigation/mcl2d_core/test/test_motion_oracle.cpp` (CMake 옵션 `-DMCL2D_MOTION_ORACLE=ON`).
원본 `libMCLoc.so` 를 `dlopen` 해 `supplyControlVar`·`doParticleMoveAction` 을 직접 호출하고 우리 구현과 대조:

```
표본: supplyControlVar 300 · doParticleMove 300 · 비교 1800 값
불일치 2 / 1800 (max ulp 1)  → 99.89 % 비트 일치     (2026-08-07 dθ 수정 후. 수정 전 17건)
```

| 항목 | 결과 |
| --- | --- |
| `trans` · `direction` | 299/300 — 표본 1개에서 각 1 ulp(원인 미확정 → debt-043) |
| 파티클 `x` · `y` · `theta` | **비트 일치 900/900** |
| `dtheta` | **비트 일치 300/300** — 원본이 `Normalize` 결과를 `atan2(sin,cos)` 로 한 번 더 통과시킨다는 것을 찾아 반영(2026-08-07) |

원본 인스턴스는 크기 미상이라 제로 버퍼(0x800)로 대체하고 초기화 플래그(오프셋 0)만 세워 계산 경로를 탔다.
멤버 오프셋(0x90 dθ · 0x98 trans · 0xa0 direction · 0xa8/0xb0 노이즈 스케일)은 전부 디스어셈블 실측이다.

### 7.2 7개 공백의 처리

| # | 공백 | 결과 |
| --- | --- | --- |
| 1 | 비트 대조 미수행 | **해소** — 오라클 신설·상시 재현 가능(§7.1). 2026-08-07 dθ 원인 규명으로 불일치 17 → **2**. 잔여는 debt-043 |
| 2 | `RangeRandom` 구현 미확인 | **해소 + 코드 정정** — 원본은 `rand() % (max−min) + min`(libfoundation 0x18c60), **상한 배제**라 `RangeRandom(-1000,1000)` = `[-1000, +999]` 2000개 값이다. 우리는 `[-1000, +1000]` 2001개를 쓰고 있었다 → `uniform_int_distribution(-1000, 999)` 로 정정. 시드는 원본이 `srand(time(NULL))` 1회라 **재현 불가**(우리는 mt19937 고정 시드 유지 — 의도적 이탈) |
| 3 | 미이식 함수 4개 | **판정 완료** — `moveRobotAccordingToMotion` 은 원본 정상 경로(오도 콜백)에서 매번 도는 구조적 차이 → **debt-044**. `doOffsetMove`/`setLaserMoveOffset` 은 라이다 오프셋 보정 조건부 경로, `getRealControlVar` 는 접근자(로봇좌표 증분 `m[0xf0]`·`m[0xf8]`·`m[0x100]` 반환) |
| 4 | 스레딩 | **확정(미이식 유지)** — 원본은 `PfThreadNum=4` ThreadPool 로 파티클을 나눠 `ThreadFunc1/2` 실행. 게다가 난수원이 전역 `rand()` 라 **스레드 경쟁이 있다**(glibc `rand()` 는 내부 락 없음). 우리는 단일 루프 + 인스턴스별 `mt19937` — 재현성 면에서 의도적으로 다르게 둔다 |
| 5 | 단위 | **확정(무해)** — 원본 내부는 mm, 우리 코어는 m. `supplyControlVar`·`doParticleMove` 는 순수 기하라 단위에 불변이며, 오라클도 같은 수치를 양쪽에 넣어 비트 일치를 확인했다 |
| 6 | `w` 스케일 정합 | **해소** — `getParticleLikelihood`(0x347920) → `computeLikelihood`(0x357b00) → **`QuadGridSearchMap::getPostProb` tail-call**(357b13). 우리 `likelihoodAt` 은 그 함수와 비트 일치하는 `ObservationField::getPostProb` 를 쓴다. 배포도 `UseOpenCLWithPF=0` 이라 CPU 경로다 ⇒ **스케일 동일**. 임계 0.8 은 원본에서도 잘 성립하지 않는 값이고, 모드 5 가 드문 것은 **원본과 같은 동작**이다(debt-031 의 전제였던 "스케일 불일치" 는 성립하지 않음) |
| 7 | `PF::step()` 누적 미적용 | **해소** — `ParticleFilter2D::step` 도 파사드와 같은 누적 기준점(`accum_odom_`)을 쓰도록 통일 |

### 7.3 그래서 "원본과 동일한가"

- **결정론 경로(예측)**: `trans`·`direction`·파티클 이동은 **비트 일치**. `dθ` 만 1 ulp 잔여(debt-043).
- **난수 경로(산포)**: 값 집합은 이제 원본과 같으나(§7.2 #2) **난수원·시드가 다르므로 수열은 다르다** —
  원본이 `srand(time(NULL))` 인 이상 비트 재현은 원리적으로 불가능하다. 분포 수준 동일이 상한이다.
- **구조**: 액션 분리·모드 트리·임계·정지 분기는 실측대로 이식. 미이식은 debt-044 의 4함수.

⇒ 정직한 등급: **결정론 경로 = 검증된 동일(1 ulp 예외) · 난수 경로 = 분포 동일 · 구조 = 충실(4함수 미이식)**.
