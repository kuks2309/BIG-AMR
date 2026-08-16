# Seer 레거시 런타임 배선 — 무엇이 무엇을 받는가

> 출처: 원본 하드 `rbk/rbk.plugin` (JSON, 88줄). 로드할 플러그인 목록과 토픽 pub→sub 표가
> **평문으로 선언**돼 있다. 심볼·디스어셈블로 추정할 필요가 없는 1차 자료다.
>
> 재현: `Tools/seer_re/amap_server.sh ssh "cat <rbk>/rbk.plugin"`

## 왜 이 파일이 정본인가

플러그인이 무엇을 **구독**하는지는 그 플러그인 바이너리를 봐도 알 수 있지만,
그 플러그인의 출력이 **어디를 거쳐 최종 소비자에게 가는지**는 바이너리에 없다.
그 배선은 이 파일에만 있다. 「원본에서 A 가 B 를 받는가」는 여기를 먼저 본다.

## 오도·측위 경로 (실측)

```
DSPChassis ──Message_MotorInfos──→ OdoCalculator
DSPChassis ──Message_Controller ──→ OdoCalculator
MoveFactory ─Message_NavSpeed ───→ OdoCalculator
                                        │
                                        │ Message_Odometer (휠 오도)
                                        ▼
                            NetProtocol · MoveFactory · CalibrationTask · DSPChassis
                                        │
                                        ▼
DSPChassis ──Message_IMU─────────→ RobotPosEKF
                                        │
                                        │ Message_Odometer (오도 + IMU 융합)
                                        ▼
                                  MCLoc · OnlineMapLogger
                                        │
MultiLaser ─Message_AllLasers ───→ MCLoc
                                        │ Message_Localization
                                        ▼
              SensorFuser · NetProtocol · MoveFactory · LaserSegmentation ·
              CalibrationTask · LocalReMap · MultiDcamera · OnlineMapLogger · DSPChassis
```

**핵심**: `MCLoc` 은 `OdoCalculator` 의 오도를 **직접 받지 않는다.**
`RobotPosEKF` 가 오도와 IMU 를 융합해 다시 발행한 `Message_Odometer` 를 받는다.

## 관련 pub→sub 원문

| 발행자 | 토픽 | 구독자 |
| --- | --- | --- |
| `DSPChassis` | `Message_MotorInfos` | `OdoCalculator` |
| `DSPChassis` | `Message_Controller` | `MoveFactory`, `NetProtocol`, `ChargerAdapter`, `OdoCalculator` |
| `MoveFactory` | `Message_NavSpeed` | `DSPChassis`, `NetProtocol`, `OdoCalculator` |
| `OdoCalculator` | `Message_Odometer` | `NetProtocol`, `MoveFactory`, **`RobotPosEKF`**, `CalibrationTask`, `DSPChassis` |
| `DSPChassis` | `Message_IMU` | **`RobotPosEKF`**, `NetProtocol`, `MoveFactory`, `CalibrationTask`, `OnlineMapLogger`, `MCLoc` |
| **`RobotPosEKF`** | `Message_Odometer` | **`MCLoc`**, `OnlineMapLogger` |
| `MultiLaser` | `Message_AllLasers` | `SensorFuser`, `MoveFactory`, `NetProtocol`, `LaserSegmentation`, `OnlineMapLogger`, `MCLoc` |
| `OpticalMotionCapture` | `Message_Localization` | `MCLoc` |

전체 52개 토픽 중 오도·측위 관련만 추렸다.

## RobotPosEKF — 무엇인가

`libRobotPosEKF.so`(43 MB)의 심볼:

```
estimation::OdomEstimation::addOdoMeasurement(rbk::protocol::Message_Odometer)
estimation::OdomEstimation::addImuMeasurement(rbk::protocol::Message_IMU)
estimation::OdomEstimation::update()
estimation::OdomEstimation::getFilterOdometer(rbk::protocol::Message_Odometer&)
estimation::OdomEstimation::angleOverflowCorrect(double&, double)
RobotPosEKF::setLaserOdom(bool) · isEnableLaserOdom() · getTargetMsgLaser(Message_AllLasers)
```

`estimation::OdomEstimation` 은 ROS `robot_pose_ekf` 의 클래스명과 같다 — 오도·IMU(·레이저 오도)를
융합하는 확장 칼만 필터 계열이다.

배포 파라미터(`robot.param` 의 `RobotPosEKF` 테이블):

| 키 | 값 | 뜻 |
| --- | --- | --- |
| `UseIMU` | **1** | **IMU 융합 활성** |
| `UseVO` | 0 | 시각 오도 미사용 |
| `StartSkidDetection` | 0 | EKF 쪽 슬립 감지 미사용 |
| `LaserOdomDetectSkid` | 0 | 레이저 오도 기반 슬립 감지 미사용 |
| `OpenIMUErrorDetect` | 0 | IMU 이상 감지 미사용 |
| `IMUNoiseDetectThred` · `IMUErrorDetectThred` | 3.0 · 20.0 | (감지 꺼져 있어 미적용) |
| `SkidDetect*Threshold` | 0.35 · 5.0 · 0.08 | (감지 꺼져 있어 미적용) |

## 미확인 (여기서 말하지 않는 것)

- **융합식·상태벡터·공분산** — `OdomEstimation` 내부를 조사하지 않았다.
- **IMU 축 정렬·부호 규약**, `ReadIMUParam()` 이 읽는 값.
- `UseIMU=0` 일 때 통과(passthrough)인지 다른 경로인지.
- 슬립 감지 3종이 꺼져 있는 이유(이 기체 판단인지 기본값인지).

→ `debt-107` 로 등록.

---

# 부록 A — RobotPosEKF 융합식 (역어셈블 확정)

`[존재]` 라벨: 아래는 전부 바이너리 정적 사실이다(`nm`/`gdb ptype`/`objdump`).
`[동작]` 은 §RobotPosEKF 의 `rbk.plugin` 배선 + `robot.param UseIMU=1` 로 별도 확정돼 있다.

## A.1 정체 — 상류 ROS `robot_pose_ekf` 이식본

`libRobotPosEKF.so` 에 BFL(Bayesian Filtering Library) 클래스가 그대로 있다:
`BFL::ExtendedKalmanFilter`(23) · `BFL::LinearAnalyticMeasurementModelGaussianUncertainty`(15) ·
`BFL::NonLinearAnalyticConditionalGaussianOdo` · `estimation::OdomEstimation`.
뒤 두 개는 `robot_pose_ekf` 패키지 고유 클래스명이다.

## A.2 상태벡터 — 6차원

생성자(`OdomEstimation::OdomEstimation()` @0x178300)가 만드는 크기로 확정:

| 객체 | 크기 | 뜻 |
| --- | --- | --- |
| `ColumnVector(6)` · `SymmetricMatrix(6)` | **6** | 상태 = (x, y, z, roll, pitch, yaw) |
| `odom_covariance_` `SymmetricMatrix(6)` | 6×6 | 오도 관측 공분산 |
| `imu_covariance_` `SymmetricMatrix(3)` | 3×3 | IMU 관측 공분산(자세 3축) |

⇒ **오도는 6-D 관측, IMU 는 3-D 관측**으로 들어간다.

## A.3 예측식 — `NonLinearAnalyticConditionalGaussianOdo::ExpectedValueGet()` @0x177970

인덱스 인자를 순서대로 읽으면(BFL 은 1-based):

```
x(6) → cos → × u(1) → x(1) 에 가산
x(6) → sin → × u(1) → x(2) 에 가산
        u(2) → x(6) 에 가산
결과 + AdditiveNoiseMuGet()
```

즉

```
  x⁺ = x + v·cos(θ)
  y⁺ = y + v·sin(θ)
  θ⁺ = θ + ω
  z, roll, pitch : 예측에서 불변 (관측으로만 움직인다)
```

`u = (v, ω)` 는 조건인자 1번(제어입력), `θ = x(6)` 이 yaw 다.
평면 2WS 기체에서 z·roll·pitch 가 예측 대상이 아닌 것은 이 식의 직접 결과다.

## A.4 야코비안 — `dfGet(unsigned int)` @0x1779f0 부근

`sin`·`cos` 각 1회 + `Matrix` 생성 + `ostream<<` 3회 + `exit@plt` 1회.
인자가 0이 아니면 오류 출력 후 종료하는 상류 구조와 같다. 비영 항은 yaw 열뿐이다:

```
  F = I,  F(1,6) = −v·sin(θ),  F(2,6) = +v·cos(θ)
```

## A.5 `update()` @0x1795d0 — 상류와 다른 부분

| 항목 | 상류 `robot_pose_ekf` | 이 바이너리 |
| --- | --- | --- |
| 시그니처 | `update(bool odom_active, bool imu_active, bool vo_active, bool gps_active, const Time&, bool&)` | **무인자** `update()` |
| VO·GPS 융합 | 있음 | **멤버·심볼 완전 부재**(`vo_meas`·`gps_meas` 검색 0건) |
| 잡음 σ 설정 | 생성자/초기화 | `update()` 안에서 `AdditiveNoiseSigmaSet` **2회** |
| 추가 멤버 | — | `double wzOdoAbsDeg` (offset 464) |

`update()` 본문 460 명령: 행렬 역행렬 2회 · 행렬곱 4회 · 간접(가상) 호출 5회 ·
`sin`/`cos`/`atan2` 각 2회 · `rbk::foundation::utils::Normalize` 1회.
쓰는 상수는 각도 계열뿐이다(π, 2π, ±π, 180.0, 1.0, −0.0) — **잡음 수치는 여기 없다.**

## A.6 IMU 갱신 게이트 — Seer 고유 개조 (핵심)

상류 `robot_pose_ekf` 에 없는 분기가 `update()` 안에 있다. 세 조각이 맞물린다.

**① 값 만들기** — `addOdoMeasurement()` @+320:

```
movss  0x50(%r15),%xmm0          ; Message_Odometer.vel_rotate (float, rad/s)
cvtss2sd
call   rbk::foundation::utils::Rad2Deg(double)
andps  [0x197550]                ; 0x7fffffffffffffff — 부호비트 제거 = 절대값
movlps %xmm0, 0x1d0(%r14)        ; → wzOdoAbsDeg
```

⇒ `wzOdoAbsDeg = |Rad2Deg(odom.vel_rotate)|` — **오도가 보고한 각속도의 절대값 [deg/s]**.
이름 그대로 `wz`(ω_z) · `Abs` · `Deg` 다.

**② 쓰기** — `update()` @+905:

```
cmpb    $0x0, 0x99(%r12)         ; m_imu_init (offset 153 = 0x99)
je      → IMU 갱신 건너뜀
movsd   0x1d0(%r12),%xmm0        ; wzOdoAbsDeg
ucomisd [0x1975c0],%xmm0         ; 상수 = 1.0
jbe     → IMU 갱신 건너뜀
... Matrix::inverse → Matrix::operator*   ; 여기서 IMU 측정 갱신
```

⇒ **IMU 측정 갱신은 `m_imu_init` 이 참이고 `|ω| > 1.0 deg/s` 일 때만 수행된다.**

**③ 뜻** — 정지·직진 중에는 IMU 를 융합하지 않는다. 자이로 바이어스가 정지 구간에서 적분돼
yaw 를 흔드는 것을 원천 차단하는 설계다. 회전할 때만 IMU 를 믿고, 그때 오도의 조향각 기반 yaw 를 교정한다.
**임계 1.0 deg/s 는 코드에 하드코딩**돼 있다 — `robot.param` 에 이 값을 바꾸는 키가 없다.

## A.7 시스템 잡음 공분산

생성자 @+328~+472 가 `SymmetricMatrix(6)` 을 0 으로 채운 뒤 대각을 세운다:

```
(1,1) … (6,6) = 1000000.0        ; movabs $0x412e848000000000
```

⇒ **σ_sys = 1000** (분산 10⁶), 6축 동일. 상류 `robot_pose_ekf` 의 `sysNoise_Cov(i,i) = pow(1000,2)` 와 같은 값이다.
사실상 "예측을 거의 믿지 않는다" 는 설정이며, 그래서 관측(오도·IMU)이 자세를 지배한다.

## A.8 IMU 장착·보정값의 출처

`RobotPosEKF::ReadIMUParam()` 이 부르는 것:

```
rbk::chasis::Model::Instance / getModelDevices / getModelParam<double|string>
rbk::chasis::Calibration::Instance / getCalibParam<double>
```

⇒ IMU 장착 정보와 보정값은 `robot.param` 이 아니라 **`robot.model`(장치 목록) + 보정 저장소**에서 온다.
`Message_ImuInstallInfo` 문자열도 바이너리에 있다.

## A.9 레이저 오도 — 존재하나 꺼져 있다

`libRobotPosEKF.so` 안에 **`rf2o::LaserOdometry2D`** 가 들어 있다(`N4rf2o15LaserOdometry2DE`).
`RobotPosEKF::setLaserOdom(bool)`·`isEnableLaserOdom()`·`getTargetMsgLaser(Message_AllLasers)` 로 배선된다. `[존재]`

배포 파라미터 `[동작]`:

| 키 | 테이블 | 값 |
| --- | --- | --- |
| `StartLaserOdo` | `MCLoc` | **0** |
| `LaserOdomDetectSkid` | `RobotPosEKF` | **0** |

⇒ 이 기체에서 **레이저 오도는 쓰이지 않는다.**

## A.10 초기 공분산 — `initialize()`

`initialize(Matrix const&)` @0x178f60 (343 명령)은 `SymmetricMatrix::operator()` 를 **36회**
호출한다 = 6×6 전량을 채운다. 유일한 즉치 상수:

```
movabs $0x3eb0c6f7a0b5ed8d   →  1e-06
```

⇒ **prior 공분산 대각 = 1e-6 (σ = 0.001)**, 비대각 0. 상류의 `prior_Cov(i,i) = pow(0.001,2)` 와 같다.
초기 자세를 강하게 믿고 출발한다는 뜻이다.

`addOdoMeasurement()` 이 `initialize()` 를 호출한다 — **첫 오도 메시지가 필터를 초기화**한다.

## A.11 관측 잡음이 필터에 들어가는 지점

`update()` 안의 `AdditiveNoiseSigmaSet` 2회는 멤버를 **그대로** 넘긴다:

| 위치 | 대상 pdf | 넘기는 공분산 |
| --- | --- | --- |
| @+673 | `0x18(%r12)` = `odom_meas_pdf_` | `lea 0x48(%r12)` = **`odom_covariance_`** (6×6) |
| @+1361 | `0x28(%r12)` = `imu_meas_pdf_` | `lea 0x70(%r12)` = **`imu_covariance_`** (3×3) |

⚠ 두 인자 모두 **멤버 주소 그대로**이고 임시 객체가 아니다. 상류가 하는
`odom_covariance_ * pow(dt,2)` 같은 **dt² 스케일링이 이 경로에는 보이지 않는다.**
(행렬 곱 임시가 있었다면 `%rsi` 가 스택을 가리켜야 한다.)

각 호출 직전에는 `addsd`/`subsd`/`ucomisd`/`ja` 로 도는 짧은 루프가 있다 —
`while` 형 각도 정규화이며, 앞서 확인한 ±π·2π 상수와 맞물린다.

## A.12 관측 모델 — 생성자에서 전량 확정

전 라이브러리에서 `SymmetricMatrix`/`Matrix` 원소를 쓰는 함수는 **둘뿐**이다
(`objdump` 전량 + 심볼 귀속: `initialize()` 36회 · 생성자 33회). 즉 관측 모델은 **생성자에 상수로 박혀 있고**
런타임에 바뀌지 않는다.

생성자가 만드는 객체와 채우는 인덱스:

| 스택 슬롯 | 형 | 채운 인덱스 | 정체 | 값 |
| --- | --- | --- | --- | --- |
| `rsp+0x60` | `SymmetricMatrix(6)` | (1,1)…(6,6) | **시스템 잡음 공분산** | **1e6** (σ 1000) |
| `rsp+0x38` | `SymmetricMatrix(6)` | (1,1)…(6,6) | **오도 관측 잡음** | **1.0** |
| `rsp+0xe8` | `Matrix(6,6)` | **(1,1) · (2,2) · (6,6)** | **`Hodom`** — 오도 관측행렬 | **1.0** |
| `rsp+0x90` | `SymmetricMatrix(3)` | (1,1)…(3,3) | **IMU 관측 잡음** | **1.0** |
| `rsp+0xb8` | `Matrix(3,6)` | **(1,4) · (2,5) · (3,6)** | **`Himu`** — IMU 관측행렬 | **1.0** |

값은 `movabs $0x3ff0000000000000,%r13` → `mov %r13,(%rax)` 로 확인했다(= 1.0).
행렬은 만들자마자 `operator=(0.0)`(`xorps`)으로 0 채운 뒤 위 원소만 세운다.

**뜻**:

```
  Hodom :  오도는 (x, y, yaw) 만 관측한다   — z·roll·pitch 는 오도가 말하지 않는다
  Himu  :  IMU 는 (roll, pitch, yaw) 를 관측한다
```

두 행렬이 겹치는 유일한 성분이 **yaw** 다. 그래서 yaw 는 오도(조향각 유도)와 IMU(자이로)가
동시에 밀고 당기는 유일한 축이고, §A.6 의 `|ω| > 1.0 deg/s` 게이트가 바로 그 경합을 조절한다.
z·roll·pitch 는 오도가 건드리지 않으므로 IMU 관측만으로 결정된다.

## A.13 관측 잡음 멤버가 채워지지 않는다 `[존재]`

§A.11 에서 `update()` 가 매 주기 넘기는 두 멤버를 추적한 결과다.

**생성자는 크기만 잡는다** (@+42~+87):

```
lea  0x48(%r12),%r14        ; &odom_covariance_
mov  $0x6,%esi
call MatrixWrapper::SymmetricMatrix::SymmetricMatrix(int)     ; 6×6, 값 미설정
lea  0x70(%r12),%r13        ; &imu_covariance_
mov  $0x3,%esi
call MatrixWrapper::SymmetricMatrix::SymmetricMatrix(int)     ; 3×3, 값 미설정
movw $0x0,0x98(%r12)        ; m_odom_init = m_imu_init = 0
```

**그 뒤로 값을 넣는 곳을 찾지 못했다.** 라이브러리 전량(269,153줄 디스어셈블 + 심볼 귀속)에서:

| 경로 | 결과 |
| --- | --- |
| 원소 쓰기 `SymmetricMatrix::operator()(i,j)` + 저장 | `initialize()`·생성자 **둘뿐**이며 모두 **스택 지역변수** 대상 |
| 복사 대입 `SymmetricMatrix::operator=(const SymmetricMatrix&)` | **라이브러리 전체 0건** |
| 스칼라 대입 `operator=(double)` | 생성자 지역변수에만 |
| `memmove` (update 내 2회) | `odom_meas_old_ ← odom_meas_`(0x138→0x168) · `imu_meas_old_ ← imu_meas_`(0x198→0x1c8) — 공분산 아님 |

⇒ `odom_covariance_`·`imu_covariance_` 는 **차원만 잡힌 채** 매 주기
`AdditiveNoiseSigmaSet` 으로 측정모델에 들어간다.

상류 `robot_pose_ekf` 는 이 자리를 메시지에서 채운다
(`odom_covariance_ = odom_meas.covariance`, `imu_covariance_ = imu_meas.covariance`).
**Seer 판에는 그 대입이 없다.**

⚠ **라벨 주의**: 위는 `[존재]` — "쓰는 코드가 없다" 는 정적 사실이다.
그 결과 런타임에 어떤 값이 실리는지(`SymmetricMatrix(n)` 가 0으로 채우는지 미초기화인지)는
**`[동작-미검증]`** 이다. 실행 대조 없이 "측정 잡음이 0이다 / 쓰레기값이다" 라고 단정하지 않는다.

⚠ **조사 한계**: 위 네 경로 밖으로 값이 들어가는 길(내부 버퍼로의 직접 `memcpy`,
참조를 다른 곳에서 얻어 쓰기, 상속·friend 접근)은 이 방법으로 잡히지 않는다.

## A.14 `SymmetricMatrix(int)` 는 값을 초기화하지 않는다 `[존재]`

`MatrixWrapper::SymmetricMatrix::SymmetricMatrix(int)` @0x180660 — 전문이 24 명령이다:

```
mov  %rcx,0x8(%rbx)          ; n 저장
lea  0x1(%rcx),%rax
imul %rcx,%rax
shr  %rdi                    ; 원소 수 = n(n+1)/2
mov  %rdi,0x18(%rbx)
shl  $0x3,%rdi
call operator new            ; 원시 할당
mov  %rax,0x20(%rbx)         ; 버퍼 포인터
mov  <vtable>,(%rbx)
ret
```

**`memset`·0 채움 루프가 없다.** `operator new` 로 받은 메모리를 그대로 버퍼로 쓴다.

⇒ §A.13 과 합치면: `odom_covariance_`(6×6 대칭 = 원소 21개)·`imu_covariance_`(3×3 = 6개)는
**초기화되지 않은 힙 메모리**를 담은 채 매 주기 `AdditiveNoiseSigmaSet` 으로 측정모델에 들어간다.

⚠ **여기까지가 `[존재]`다.** 런타임에 그 메모리에 무엇이 있는지는 `[동작-미검증]`이다.
프로세스 초기 할당이면 커널이 0으로 준 페이지라 사실상 0일 수 있고, 재사용된 힙이면 임의값이다.
**실행 대조 없이 "측정 잡음이 0이다" 도 "쓰레기값이다" 도 단정하지 않는다.**

관측 잡음을 실험으로 잡지 않고 상수로 두고 넘어가는 것은 현장에서 흔한 선택이지만,
여기서는 **상수조차 넣지 않은 상태**라는 점이 다르다. 상류 `robot_pose_ekf` 가 메시지 공분산으로
채우던 자리를 이식하면서 대입만 빠진 형태로 보인다.

## A.15 `update()` 전체 흐름 — 초기화 플래그와 게이트

두 플래그(`m_odom_init` @0x98 · `m_imu_init` @0x99)의 전 접근 지점을 찾았다.
생성자가 `movw $0x0,0x98` 로 둘을 한 번에 0으로 놓고, 이후 건드리는 곳은 `update()` 뿐이다.

```
@0x17965d  cmpb $0x0, 0x98(%r12)     ; m_odom_init 이 0이면
           → 오도 측정 갱신을 건너뛰고 기준(odom_meas_old_)만 세운다
@0x1798a1  movb $0x1, 0x98(%r12)     ; m_odom_init = 1

@0x179959  cmpb $0x0, 0x99(%r12)     ; m_imu_init 이 0이면
           → IMU 측정 갱신을 건너뛰고 기준(imu_meas_old_)만 세운다
@0x179b61  movb $0x1, 0x99(%r12)     ; m_imu_init = 1
@0x179968  movsd 0x1d0(%r12)         ; 초기화됐으면 wzOdoAbsDeg 를 보고
@0x179972  ucomisd 1.0               ; |ω| > 1.0 deg/s 일 때만
@0x179980  → IMU 측정 갱신 수행
```

⇒ 각 센서의 **첫 주기는 기준선만 세우고 융합하지 않는다**(상류와 같은 패턴).
IMU 는 거기에 더해 **회전 중일 때만** 반영된다(§A.6).

`memmove` 2회가 그 기준선 갱신이다 — `odom_meas_old_ ← odom_meas_`(0x138→0x168),
`imu_meas_old_ ← imu_meas_`(0x198→0x1c8).

## A.16 `UseIMU` 파라미터의 소비 지점 — 미확정

`loadFromConfigFile` @0xddfd9 이 `"UseIMU"` 를 SSO 즉치(`movl $0x49657355` + `movw $0x554d`)로 만들어
`lea 0x340(%r15),%rsi` 로 넘긴다 ⇒ **`MutableParam<bool>` 슬롯 = `RobotPosEKF + 0x340`**,
값 바이트는 `+0x3b0`(생성자가 `movb $0x0,0x3b0(%r12)` 로 0 초기화).

**그런데 `+0x3b0` 을 읽는 지점을 찾지 못했다.** 라이브러리 전량에서 그 오프셋 접근은
생성자·소멸자뿐이고, `setSubscriberCallBack`·`messageIMUCallBack` 에도 그 값을 보는 분기가 없다.

가능성(미검증): 접근자 인라인으로 다른 형태가 됐거나, 다른 멤버로 옮겨 담아 쓰거나,
`RobotPosEKF::run()` 계열에서 소비한다. **"UseIMU 가 무시된다"고 단정하지 않는다** —
찾지 못한 것이지 없음을 증명한 것이 아니다.

## A.17 아직 모르는 것

- `UseIMU` 값을 실제로 읽는 지점(위 A.16).
- 두 공분산 버퍼의 런타임 값(§A.13~A.14) — 실기·원본 구동 대조 필요.
- 슬립 감지 3종이 꺼진 이유.
- `IMUErrorDetect*` 가 켜졌을 때의 거동.
- `wzOdoAbsDeg` 게이트 임계 1.0 deg/s 의 근거.
