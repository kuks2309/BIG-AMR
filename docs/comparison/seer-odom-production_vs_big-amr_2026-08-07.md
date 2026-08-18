# Seer 오도메트리 **생산** 방식 ↔ Big-AMR (부재, `icp_odometry` 대체)

> 2026-08-07 (KST) · 대상: rbk(Robokit) 3.4.5.20 `libOdoCalculator.so` (63G SATA 원본, 읽기 전용)
> 질문: **"Seer 는 odom 을 어떻게 만드는가"** — 앞선 [위치추정 분석](seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md)이
> *소비* 쪽이었다면 본 문서는 *생산* 쪽이다.
> 1차 산출물: `References/seer/libOdoCalculator/`(`update.asm`·`calpose.asm`·`multisteers_calspeed_caldpose.asm`
> + `PROVENANCE.md`) — **`References/` 는 `.gitignore:12` 대상이라 저장소에 올라가지 않는다(로컬 전용).**
> 재현은 아래 §0 의 명령으로 언제든 다시 뜰 수 있다.

## 0. 검증 등급

| 기호 | 의미 |
| --- | --- |
| **✓** | 이 세션이 원본 바이너리·배포 자산에서 직접 확인(주소·문자열 인용) |
| **⚠** | 추론·미확정 |

**재현 명령**(원본 하드가 붙어 있을 때):
```bash
Tools/seer_re/amap_server.sh ssh \
  "objdump -d --start-address=0x15d490 --stop-address=0x15dd40 <하드>/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so"
```

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
RobotPosEKF  ← Message_IMU (DSPChassis)          ★ 오도·IMU 융합 (UseIMU=1)
        ↓ Message_Odometer (융합본)
MCLoc::DoMoveAction  (위치추정 입력 — 앞 문서 §1)
```

> ⚠ **정정** — `MCLoc` 은 `OdoCalculator` 의 오도를 **직접 받지 않는다.** 배포 배선(`rbk/rbk.plugin`)상
> `OdoCalculator → RobotPosEKF → MCLoc` 이고, 중간의 `RobotPosEKF`(`estimation::OdomEstimation`,
> `robot_pose_ekf` 계열)가 오도와 IMU 를 융합한다. 이 기체는 `RobotPosEKF.UseIMU = 1` 로 **융합이 켜져 있다.**
> ⇒ **위치추정이 소비하는 오도는 순수 휠 오도가 아니다.** 배선 정본: `Tools/seer_re/docs/legacy_runtime_wiring.md`.
> 융합식·공분산·IMU 축 정렬은 미조사(**debt-107**).

### 1.1 측정량·발행량은 `.proto` 정본으로 확정 ✓

원본 트리의 `rbk/proto/` 에 정의가 그대로 있다 — 오프셋 추정이 아니라 **정본 인용**이다.

`message_motorinfos.proto` — 드라이브가 올려보내는 값:
```protobuf
message Message_MotorInfo {
  enum MotorType { WALK=0; STEER=1; SPIN=2; LINEAR=3; ROTATION=4; DO=5; }
  string motor_name = 2;
  float  position   = 5;    // m      ← 주행륜 누적 이동거리 / 조향륜 각도
  float  speed      = 6;    // m/s
  bool   stop       = 9;
  int32  encoder    = 14;   // cnt
  MotorType type    = 15;
  float  raw_position = 19; // steer angle without .cp value
}
```
⇒ `speed`(6)와 `position`(5)이 **둘 다** 올라온다. 오도메터 구조체의 두 슬롯
`+0x30`(CalSpeed 입력)·`+0x38`(CaldPose 입력)이 이 둘에 대응한다.
`stop`(9)이 모터 단위로 이미 오므로 `JudgeStop()`(0x15a3d0)에 **부동소수 비교가 0건**인 것도 설명된다
(속도를 임계와 비교하는 것이 아니라 드라이브 보고 플래그를 취합).

`message_odometer.proto` — 위치추정으로 나가는 값:
```protobuf
message Message_Odometer {
  uint32 cycle = 2;  double x = 3;  double y = 4;  float angle = 5;   // m, m, rad
  bool is_stop = 6;  float vel_x = 7; vel_y = 8; vel_rotate = 9;      // m/s, rad/s
  bool detect_skid = 10;  repeated Message_MotorInfo motor_info = 11;  bool follow_err = 12;
}
```
⇒ `MCLoc::DoMoveAction` 이 읽던 오프셋과 일치한다 — `x@0x30`·`y@0x40`(double), **`angle@0x3c` 를
`movss`+`cvtss2sd` 로 읽던 것**이 여기 `float angle = 5` 다. 서로 다른 두 바이너리의 관측이 정본에서 맞물렸다.
**위치는 double, 각도는 float** 이라 각도만 단정밀도로 잘려 전달된다.

vtable 슬롯은 `_ZTV19MultiSteersOdometer`(0x4046c0)의 **재배치 항목 실측**이다(파일에는 0, `R_X86_64_64` 로 채워짐):
`+0x78 = MultiSteersOdometer::CalSpeed`(0x14d690) · `+0x80 = MultiSteersOdometer::CaldPose`(0x14f300) ·
`+0x88 = AbstractOdometer::CalPose`(0x15d490).

## 2. 기구학 — `multiSteers` ✓

`robot.model` 의 `chassis.mode = combo=multiSteers` → `MultiSteersOdometer` 가 선택된다.

- **`CalOdoCoef()`** @0x14c9f0 — 모터 맵을 돌며 각 바퀴 좌표(+오프셋)로 계수행렬을 구성하고
  (`14cc1c`·`14cc60`, 크기 인자 3 = `vx,vy,ω` — `14ca41`·`14ca50`), **`Eigen::PartialPivLU` 로 역행렬을
  미리 만든다**. 역행렬을 쓰는 함수는 `Omni`·`DualDiff`·`MultiDiff`·`MultiSteers` 의 `CalOdoCoef` 네 곳뿐이다.
  ⇒ 런타임에는 분해를 다시 하지 않고 **행렬–벡터 곱 한 번**으로 끝난다(기하는 굳히고 입력만 바꿔 끼운다).
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
| `+0x30`/`+0x38` 의 정체 | **해소(2026-08-07)** — `.proto` 정본에 `position=5`(m)·`speed=6`(m/s) 둘 다 존재(§1.1). 단 *어느 슬롯이 어느 필드인지*의 최종 대조는 구조 정합(같은 사상, 다른 슬롯)까지다 |
| `JudgeStop()`(0x15a3d0) | **해소** — 전 구간에 `ucomisd`/`cvtss2sd` **0건**. 모터별 `stop`(필드 9) 취합 구조 |
| `CalOdoCoef` 행렬 형태 | **해소** — `Eigen::PartialPivLU` 로 역행렬 사전계산, 크기 인자 3(§2) |
| `CaldPosVenc()`(0x15adb0) 의 역할 | **부분 해소** — 0x2360 크기지만 산술은 8줄뿐(`divsd` 5·`addsd` 2·`mulsd` 1, `cos`/`sin`/`ucomisd` 0). 내부 점프 341·`stringstream` 4벌·Logger 큐 push 4회로 대부분 로깅·맵 순회다. 쓰는 상수는 **π**(0x1a17f0)와 **1e9**(0x19c0a0, = `Δt_ns`→s), 결과는 멤버 **`0x70`·`0x78`** 에 저장한다(`15bbb3`·`15bbc3`). 그 두 멤버를 읽는 함수는 `DualDiffOdometer::CaldPose`(4) · `SkidSteerOdometer::CheckModelParam`(4) · `FilterMotorParam`(1) · 자기 자신(2)뿐이고 **`MultiSteersOdometer` 경로에는 없다** ⇒ 이 기체의 자세 계산에는 쓰이지 않는다. ⚠ 한계: 오프셋만으로 매칭했고(클래스별 같은 오프셋이 같은 필드라는 가정) 필드 의미 자체는 미확정 |

## 7. 분석 이력 정정 (숨기지 않는다)

본 결론에 이르기까지 같은 사안을 **두 번 뒤집었다**:

| 시점 | 서술 | 판정 | 원인 |
| --- | --- | --- | --- |
| 2026-08-06 | "적분식" | 틀림(이 배포 기준) | 함수명만 보고 호칭 |
| 2026-08-07 오전 | "적분이 아니다" | 맞음 | 근거는 `CaldPose` 뿐 — 불완전 |
| 2026-08-07 오후 | "적분이다, 앞 정정이 틀렸다" | 틀림 | `CalPose` 의 **속도 경로만** 보고 플래그 분기를 못 봄 |

기록: [docs/claude-mistake/2026-08-07-001](../claude-mistake/2026-08-07-001_narrow-scope-double-reversal.md).

---

## 8. 누적 오차를 다루는 방식 — 네 겹 (2026-08-08)

휠 오도는 원리상 드리프트가 누적된다. 원본은 **오도를 보정하지 않고, 오도를 신뢰하지 않는 구조**로 감당한다.

### 8.1 위치추정이 오도의 **절대값을 쓰지 않는다** ✓

`MCLoc::supplyControlVar` 는 두 시점을 받아 **차분만** 취한다(`33cf1e` `cur.x−prev.x`, `33cf2d` `cur.y−prev.y`).
오도가 수 미터 드리프트해도 그 누적값은 위치추정 자세로 전파되지 않는다 — 전파되는 것은
"직전 주기에 얼마나 움직였나"뿐이고, 그 짧은 구간의 오차만 들어간다.
`ControlVar2D` 는 절대 자세처럼 생겼지만 **증분 추출용 원재료**다.

### 8.2 매 스캔 주기에 관측이 흡수 ✓

가중치 갱신 → 리샘플이 매 주기 돈다. 드리프트로 어긋난 파티클은 우도가 떨어져 리샘플에서 죽는다.
드리프트 보정은 별도 로직이 아니라 **파티클 필터 자체**다.

### 8.3 오도를 많이 쓴 주기일수록 불확실성을 넓힌다 ✓

`selectExtraMove` 6모드(§ 위치추정 문서 §1.1.2)가 이 일을 한다 — 이동량이 크면 40 mm·3°,
미세 이동이면 10 mm·1°. **오도 증분이 클수록 그 주기의 오차 가능성도 크므로 파티클을 더 넓게 뿌려
관측이 교정할 여지를 만든다.** 드리프트를 지우는 게 아니라 들어올 만큼만 문을 여는 설계다.

### 8.4 크게 틀어지면 멈춘다 ✓

`CheckWheelSkid`: 오도 이동량과 위치추정 이동량이 **2배** 이상 벌어지거나 회전이 **30°** 이상 어긋나면
Skidding → `setError(0xcdee=52718)` 'Detect skid and stop AGV(Automated Guided Vehicle)', 복구는 정지 후 `recoverTime` 1 s.
배포값 `CheckDistance 1.0` m · `CheckAngle 30.0°` · `recoverTime 1.0` s.

### 8.5 오도 자체를 되돌리는 경로는 **없다** — 단, 융합은 있다 ✓

`OdoCalculator` 가 구독하는 것은 `NavSpeed`·`Controller`·`MotorInfos` **셋뿐**이고
**위치추정을 구독하지 않는다**(`setSubscriberCallBack` 계열 심볼 전수). `SetInitVal(OdometerOutput)` 은
`SetInitValFrom_odo()`·`run()` 에서만 불리는 **시작 시 초기화** 경로다.
⇒ **위치추정 결과**를 오도에 되먹여 드리프트를 리셋하는 구조는 아니다. 오도는 계속 흘러가고 소비자가 증분만 떠 쓴다.

⚠ 그러나 **IMU 는 되먹여진다** — `OdoCalculator` 로가 아니라 그 **하류의 `RobotPosEKF`** 에서다.
휠 오도와 IMU 가 융합된 뒤에야 `MCLoc` 으로 간다(§1 정정). 따라서 「오도 = 순수 휠 적분」이라는 그림은
`OdoCalculator` 출력까지만 맞고, 위치추정이 보는 오도에는 **관성 보정이 이미 들어 있다.**
특히 yaw 는 조향각에서 유도된 값과 자이로가 섞이므로, 조향 원점 바이어스의 영향이 그만큼 희석된다.

### 8.6 프로토콜에는 슬립 관측 틀이 있으나 **이 배포에서는 쓰이지 않는다** ✓

`message_odometer.proto` 에 정의가 존재한다:
```protobuf
message Message_SlipSensor {
  enum Type { IMU = 0; LOC = 1; OPT = 2; }   // 관성 · 위치추정 · 광학
  Message_Slip vx = 2; vy = 3; vw = 4;       // slip dist(m) · slip_time(s) · name
  repeated Message_Slip motor = 5;
}
```
그리고 `Message_Odometer.detect_skid = 10`.

**2026-08-08 확인 — 정의만 있고 아무도 안 쓴다.** rbk 트리의 모든 `.so` 를 대상으로 동적 심볼을 대조한 결과:

```
SlipSensor 심볼:  libprotocol.so  정의 88 / 참조 0
                  그 외 전 라이브러리  정의 0 / 참조 0
```

프로토콜 생성 코드(`libprotocol.so`)가 클래스를 정의만 하고 **어떤 플러그인도 참조하지 않는다**(undefined 참조 0).
`OdoCalculator::SetMsgOdo`(0x90bf0–0x90eb0) 안에도 `SlipSensor` 참조가 없다.
⇒ 슬립 대응은 §8.4 의 `CheckWheelSkid`(위치추정 쪽) **한 갈래로만** 돈다.

> 한계: `nm -D` 동적 심볼 대조라 인라인 확장돼 심볼이 남지 않는 접근자는 잡히지 않는다.
> 다만 `Message_SlipSensor` 는 메시지 클래스라 생성자·`Clear`·`CopyFrom` 등이 심볼로 남아야 정상이고,
> 그것이 **0** 이라는 점이 근거다.

### 8.7 Big-AMR 에 주는 함의

| 겹 | 우리 상태 |
| --- | --- |
| 8.1 증분만 사용 | **그대로 작동** — 이식 완료(`supplyControlVar`) |
| 8.2 관측 보정 | **그대로 작동** — 이식 완료 |
| 8.3 적응 산포 | **그대로 작동** — `selectExtraMove` 이식 완료 |
| 8.4 슬립 감지 | **무력** — 오도가 `icp_odometry`(레이저)라 레이저↔레이저 비교가 되어 휠 미끄러짐을 검출하지 못한다 → **debt-044** |

즉 원본이 누적 오차를 감당하는 방식은 "정밀한 적분"이 아니라
**증분만 사용 + 관측 보정 + 불확실성 적응 + 이상 시 정지** 네 겹이고, 우리는 그중 셋을 갖췄다.

---

## 9. `MultiSteersOdometer::CaldPose()` 줄 단위 복원 ✓

`libOdoCalculator.so` 에 **DWARF 가 살아 있다.** 그래서 생 오프셋이 아니라 **멤버 이름**과
**원본 소스 줄 번호**로 확정된다. 원본 트리:
`/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp`
(형제: `odometer.{h,cpp}` · `ackermanodometer.cpp` · `diffodometer.cpp` · `dualdiffodometer.cpp` ·
`multidiffodometer.cpp` · `omniodometer.cpp` · `rgv2odometer.cpp`)

### 9.1 `AbstractOdometer` 레이아웃 — 앞선 §3 의 생 오프셋이 전부 이름으로 확정된다

| 오프셋 | 멤버 | §3 에서 부르던 이름 |
| --- | --- | --- |
| 11 | `bool flagFirstInputGot` | — |
| 12 | `bool flagDebugDetail` | — |
| 13 | `bool flagCumEncPoseMode` | `0xd` |
| 184 / 192 | `uint64_t tcur` / `tpre` | `0xb8` |
| 216 / 224 / 232 | `output.vx` / `vy` / `vw` | `0xd8` / `0xe0` / `0xe8` |
| 240 / 248 / 256 | `output.dx` / `dy` / `dyaw` | `0xf0` / `0xf8` / `0x100` |
| 264 / 272 / 280 | `output.x` / `y` / `yaw` | `0x108` / `0x110` / `0x118` |
| 320 | `double thresConsistent` | — |

`struct OdometerOutput` 전체 88 B, `AbstractOdometer` 전체 328 B.
⇒ §3 의 해독은 **전부 맞았다** — 이름으로 재확인됐다.

### 9.2 `CaldPose()` — 원본 159~195행

주소 `0x14f300`~`0x14fe80`. 줄 번호는 DWARF 줄 테이블 실측이다.

```
159  진입
160  AbstractOdometer::CaldPose()                 ; 기저 클래스 선처리
163  if (!flagFirstInputGot) goto 190             ; 첫 입력 전에는 증분을 만들지 않는다
166  Eigen 벡터 2개 생성 + memset 0
168  ┌ 모터맵 순회 ─────────────────────────────
171  │   ds = motor.second[+0x38]                 ; 휠 변위
172  │   δ  = motor.second[+0x20]                 ; 조향각
173  │   b[2i]   = cos(δ) * ds
174  │   b[2i+1] = sin(δ) * ds
     └ 순회 끝 → general_matrix_vector_product     ; 계수행렬(§2 CalOdoCoef 사전 역행렬) × b
180  output.dx, output.dy ← 결과                  ; 0xf0 에 16 B 동시 저장(movupd)
182  output.dyaw          ← 결과                  ; 0x100
184  if (flagDebugDetail)
185      stringstream → rbk::Logger::thread()
190  output.vx = output.vy = 0 ; output.vw = 0    ; 공통 종료 + 163 의 early-exit 착지점
195  정리
```

**읽어야 할 두 가지**:

1. **`CaldPose` 는 속도를 항상 0으로 지운다**(190행). 속도는 `CalSpeed()` 소관이다 —
   `RobotPosEKF` 의 게이트 입력 `wzOdoAbsDeg`(= `odom.vel_rotate`)는 여기서 나오지 않는다.
2. **첫 입력 전에는 증분이 생산되지 않는다**(163행 게이트). 그 경로도 190행으로 착지하므로
   `dx`/`dy`/`dyaw` 는 **직전 값이 남고** 속도만 0이 된다.

### 9.3 우리 것과의 대조

| | 레거시 `CaldPose` | `motor_control/driver_node.py` |
| --- | --- | --- |
| 휠 계측 | `(ds, δ)` 쌍 | `(ds, δ)` 쌍 — 같은 구조 |
| 벡터화 | `b[2i]=cos δ·ds`, `b[2i+1]=sin δ·ds` | `modules_to_twist` 내부 |
| 역해 | 계수행렬 사전 역행렬 × b | 정기구학 최소자승 |
| 첫 입력 게이트 | `flagFirstInputGot` | `self._prev_pos is not None` — 같은 성질 |
| 속도 | `CaldPose` 가 0으로 지움 | 별도 |

⇒ **구조는 같고 역해 방법이 다르다.** 수치 동일성은 대조로 확인해야 한다 —
`libOdoCalculator.so` 는 `dlopen` 성공·`ldd` 미해결 0건·핵심 심볼 `.dynsym` 공개
(`_ZN19MultiSteersOdometerC1Ev` · `_ZN19MultiSteersOdometer8CaldPoseEv` 등)라
karto 오라클과 같은 경로가 열려 있다.
