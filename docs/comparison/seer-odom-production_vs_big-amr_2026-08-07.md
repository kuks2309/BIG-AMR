# Seer 오도메트리 **생산** 방식 ↔ Big-AMR (부재, `icp_odometry` 대체)

> 2026-08-07 (KST) · 대상: rbk(Robokit) 3.4.5.20 `libOdoCalculator.so` (63G SATA 원본, 읽기 전용)
> 질문: **"Seer 는 odom 을 어떻게 만드는가"** — 앞선 [위치추정 분석](seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md)이
> *소비* 쪽이었다면 본 문서는 *생산* 쪽이다.
> 1차 산출물: [References/seer/libOdoCalculator/](../../References/seer/libOdoCalculator/PROVENANCE.md)

## 0. 검증 등급

| 기호 | 의미 |
| --- | --- |
| **✓** | 이 세션이 원본 바이너리·배포 자산에서 직접 확인(주소·문자열 인용) |
| **⚠** | 추론·미확정 |

배포 자산은 `robot.model`(model `Roll_A084`, chassis `basic.name` `Foil_A085` — **두 이름이 다르며 합치지 않는다**)과
`robot.param`(SQLite)이다.

## 1. 파이프라인 ✓

```
Tongyi CANopen 4모터  (robot.model 의 brand 문자열 "Tongyi-IxL-CANOpen" ×9)
   FrontWalk (x=+0.6) · RearWalk (x=−0.6)   : func=walk,  wheelRadius 0.125 m, reductionRatio 32
   FrontSteer(x=+0.6) · RearSteer(x=−0.6)   : func=steer, reductionRatio 315, steerOffset 138 / 137.6
        ↓ Message_MotorInfos
AbstractOdometer::Update()                    @0x1539c0   ← 주기 진입점
   +0x60 ExtractMotorInfo → +0x68 JudgeStop → +0x70 CaldPosVenc → +0x78 CalSpeed
        → [cmpb 0xd] +0x80 CaldPose → +0x88 CalPose
        ↓
OdoCalculator::SetMsgOdo → Message_Odometer{x, y, angle(float), is_stop, timestamp}
        ↓
MCLoc::DoMoveAction  (위치추정 입력 — 앞 문서 §1)
```

vtable 슬롯은 `_ZTV19MultiSteersOdometer`(0x4046c0)의 **재배치 항목 실측**이다(파일에는 0, `R_X86_64_64` 로 채워짐):
`+0x78 = MultiSteersOdometer::CalSpeed`(0x14d690) · `+0x80 = MultiSteersOdometer::CaldPose`(0x14f300) ·
`+0x88 = AbstractOdometer::CalPose`(0x15d490).

## 2. 기구학 — `multiSteers` ✓

`robot.model` 의 `chassis.mode = combo=multiSteers` → `MultiSteersOdometer` 가 선택된다.

- **`CalOdoCoef()`** @0x14c9f0 — 모터 맵을 돌며 각 바퀴 좌표(+오프셋)로 계수행렬 구성(`14cc1c`·`14cc60`).
- **`CalSpeed()`** @0x14d690 — 유닛마다 `v·cos δ`, `v·sin δ` 를 관측벡터에 적재(`14d942` cos → `14d94c` mul,
  `14d968` sin → `14d972` mul) 후 `Eigen::general_matrix_vector_product` → **(vx, vy, ω)**.
- **`CaldPose()`** @0x14f300 — **완전히 같은 구조**인데 입력 슬롯만 다르다: `+0x30`(속도) 대신 **`+0x38`**(변위)
  (`14f569` vs `14d91c`). 결과 → **(Δx, Δy, Δθ)**. `dt` 곱 없음.

즉 같은 선형 사상을 속도에 쓰면 속도, 변위에 쓰면 변위 증분이 나온다.
> ⚠ `+0x38` 이 "엔코더 변위"라는 것은 구조 정합과 함수명(`CaldPose`·`CaldPosVenc`)까지다 — 그 필드를 채우는
> 지점(`ExtractMotorInfo`)은 아직 안 봤다.

## 3. 자세 갱신 — **두 경로, 플래그가 고른다** ✓

`AbstractOdometer::CalPose()` @0x15d490:

```
15d4b7  cmpb $0x0, 0xd(%r12)          ← CumEncPoseMode (AbstractOdometer::SetCumEncPoseMode(bool), odometer.h:43)
15d4bd  je   15d5c8                    ← 0 이면 속도 경로로

[플래그 1 — 엔코더 변위 누적]          [플래그 0 — 속도 적분]
15d4c3  0xd0(rsp) ← m[0xf0]  (Δx)      15d5c8  rax = m[0xb8]        (Δt, 나노초)
15d4d5  0xe0(rsp) ← m[0xf8]  (Δy)      15d5f6  dt  = Δt / 1e9       (상수 0x19c0a0 = 1e9 실측)
15d4e7  xmm0      ← m[0x100] (Δθ)      15d5fe  0xd0(rsp) ← m[0xd8]·dt   (vx·dt)
        ※ dt 곱 없음                   15d615  0xe0(rsp) ← m[0xe0]·dt   (vy·dt)
                                        15d62c  xmm0      ← m[0xe8]·dt   (ω·dt)
                    └──────── 공통 누적부 (15da10~) ────────┘
15da10  θ ← θ + Δθ            (멤버 0x118)
15da24  θ ← Normalize(θ)      → 15da29 저장
15da33  sinθ    15da4b  cosθ  ← **갱신된 θ 로 회전**(end-point)
15da6e~ (x, y) ← (x, y) + R(θ)·(Δx, Δy)   (멤버 0x108/0x110, `movupd`+`addpd`)
```

같은 플래그가 `Update()` 에서 `CaldPose()` 호출도 게이트한다(`153a6d cmpb $0x0,0xd(%rbx)` → `je` 로 건너뜀) —
**플래그가 1일 때만 변위 증분이 생산되고, 그때 `CalPose` 가 그것을 쓴다.** 앞뒤가 맞는다.

## 4. 이 기체가 실제로 도는 경로 ✓

`robot.param` 의 **`OdoCalculator.FlagCumEncPoseMode = 1`** (실측) ⇒ **엔코더 변위 누적 경로**.
**속도 적분(∫v dt)은 코드에 존재하지만 이 배포에서는 쓰이지 않는다.**

부가 파라미터(실측): `FlagConsistentCheck 0` · `ThresConsistent 0.02` ·
`MotorFollowMonitorErrThres 0.1` / `WarnThres 0.05` / `ErrWin 1.0` / `WarnWin 0.5` / `Delay 0.05` ·
`LinMotorMonitorErrThres 0.01` · `FlagOdomDebugMode 0`.

## 5. Big-AMR 과의 관계

| | Seer | Big-AMR |
| --- | --- | --- |
| 오도 생산 | 휠 오도메트리(위 파이프라인) | **없음** — `rtabmap_odom/icp_odometry` 가 `/scan_merged` 로 `/odom` 생성 |
| 결과 | 엔코더 변위 누적 자세 | 레이저 정합 자세 |
| 영향 | — | 슬립 감지가 레이저↔레이저 비교가 되어 원 의미(휠 미끄러짐 검출) 상실 → **debt-044** |

우리 이식본(`mcl2d_core`)에는 오도 **생산** 코드가 없다(`dt` 곱·엔코더 처리 grep 0건). 본 문서는 향후 휠 오도를
붙일 때의 정본 근거다.

## 6. 미확정 ⚠

| 항목 | 상태 |
| --- | --- |
| `+0x30`/`+0x38` 필드를 채우는 지점 | `ExtractMotorInfo`(0x1596a0) 미조사 — 속도/변위 해석은 구조 정합까지 |
| `CaldPosVenc()`(0x15adb0) 의 역할 | 매 주기 호출되지만(`+0x70`) 산출물이 어디 쓰이는지 미확인 |
| `JudgeStop()`(0x15a3d0) | `is_stop` 판정 근거 미조사 |
| `CalOdoCoef` 가 만드는 행렬의 정확한 형태 | 의사역행렬 여부 미확인 |

## 7. 분석 이력 정정 (숨기지 않는다)

본 결론에 이르기까지 같은 사안을 **두 번 뒤집었다**:

| 시점 | 서술 | 판정 | 원인 |
| --- | --- | --- | --- |
| 2026-08-06 | "적분식" | 틀림(이 배포 기준) | 함수명만 보고 호칭 |
| 2026-08-07 오전 | "적분이 아니다" | 맞음 | 근거는 `CaldPose` 뿐 — 불완전 |
| 2026-08-07 오후 | "적분이다, 앞 정정이 틀렸다" | 틀림 | `CalPose` 의 **속도 경로만** 보고 플래그 분기를 못 봄 |

기록: [docs/claude-mistake/2026-08-07-001](../claude-mistake/2026-08-07-001_narrow-scope-double-reversal.md).
