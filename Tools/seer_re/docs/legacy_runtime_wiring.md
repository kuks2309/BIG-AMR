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

## A.16 파라미터 13개의 슬롯 지도와 소비 여부

`RobotPosEKF::loadFromConfigFile()` 의 `loadParam` 호출 **13회**를 순서대로 뽑고
`robot.param` 의 `RobotPosEKF` 테이블 13행과 대조했다 — **타입 순서가 정확히 일치**해
1:1 매핑이 확정된다(b,b,i,d,d,b,b,b,d,d,d,i,i).

값 오프셋은 **슬롯 + 0x78** 이다. `libMCLoc` 의 `MutableParam` 과 같은 배치이며,
아래 세 건이 그 규칙을 교차 검증한다(슬롯에서 +0x78 한 주소가 `run()` 에서 실제로 읽힌다).

| 파라미터 | 슬롯 | 값 주소 | 읽는 곳 |
| --- | --- | --- | --- |
| `UseIMU` | 0x340 | **0x3b8** | **없음** |
| `OpenIMUErrorDetect` | 0x778 | 0x7f0 | `run()` ×2 ✓ |
| `IMUErrorDetectTime` | 0x518 | 0x590 | — |
| `IMUNoiseDetectThred` | 0x5d8 | 0x650 | — |
| `IMUErrorDetectThred` | 0x6a8 | 0x720 | `update()` 부근에서 읽힘 |
| `UseVO` | 0x830 | 0x8a8 | `run()` · `modelChangedSubscriber` · `calibChangedSubscriber` ✓ |
| `StartSkidDetection` | 0x3d0 | **0x448** | **없음** |
| `LaserOdomDetectSkid` | 0xcd8 | 0xd50 | `run()` ×2 · `setLaserOdom` · `isEnableLaserOdom` ✓ |
| `SkidDetectAccWarnThreshold` | 0x8e8 | 0x960 | `run()` ✓ |
| `SkidDetectRotWarnThreshold` | 0x9b8 | 0xa30 | `run()` ✓ |
| `SkidDetectDiffPoseWarnThreshold` | 0xa88 | 0xb00 | `run()` ✓ |
| `SkidDetectInertialWinCnt` | 0xb58 | 0xbd0 | `SkidDetector::Update` 인자 ✓ |
| `SkidDetectDiffPoseWinCnt` | 0xc18 | 0xc90 | `SkidDetector::Update` 인자 ✓ |

**`UseIMU` 와 `StartSkidDetection` 만 읽는 곳이 없다.**

⚠ 이것은 여전히 `[존재]` 주장이지만 **대조군이 있다** — 같은 기법이 나머지 파라미터의 소비 지점을
정확히 찾아냈으므로, 두 건의 부재는 방법 실패가 아니라 실제 부재일 가능성이 높다.
그래도 **인라인·다른 접근 형태의 가능성은 남으므로 「죽은 파라미터」로 확정하지 않는다.**

⚠ 함의가 있다: `StartSkidDetection` 을 읽지 않는다면 배포값 `0`이 **슬립 감지를 끄지 못한다**.
`SkidDetector::Update` 호출은 `run()` 에 실재하고 임계·윈도우 파라미터는 정상적으로 읽힌다.
바깥 게이트(`jbe → +4323`)의 정체를 확인하기 전까지 **「이 기체는 슬립 감지를 쓰지 않는다」고 말할 수 없다.**

## A.17 `run()` — IMU 는 선택이 아니라 **필수 전제** `[존재]`

필터를 구동하는 것은 전부 `RobotPosEKF::run()` 이다(3,414 명령). 그 안에서만
`addOdoMeasurement`(2) · `addImuMeasurement`(2) · `update()`(2) · `getFilterOdometer`(1) 을 부른다.

주루프의 진입 조건(@+1072):

```
cmpb $0x0, 0x338(%r13)     ; 오도 수신 플래그
je   → nanosleep           ; 없으면 자고 다시
cmpb $0x0, 0x339(%r13)     ; IMU 수신 플래그
je   → nanosleep           ; 없으면 자고 다시
... getSubscriberData<Message_Odometer> → 이후 융합·발행
```

두 플래그의 성격이 다르다:

| 오프셋 | 세우는 곳 | 지우는 곳 | 성격 |
| --- | --- | --- | --- |
| `0x338` | `messageOdometerCallBack` | **`run()` 이 매 반복 지움**(@0xe9f6f) | "새 오도가 왔다" |
| `0x339` | `messageIMUCallBack` | **생성자뿐**(라이브러리 전량 확인) | "IMU 를 한 번이라도 봤다" — **래치** |

⇒ **IMU 메시지가 한 번도 오지 않으면 `run()` 은 영원히 `nanosleep` 만 하고 아무것도 발행하지 않는다.**
`MCLoc` 의 오도 입력은 이 플러그인의 출력이므로, **IMU 가 없으면 위치추정에 이동량이 아예 공급되지 않는다.**

이것이 `UseIMU` 파라미터보다 강한 구조적 제약이다. §A.16 에서 `UseIMU` 값(`+0x3b0`)을 읽는 지점을
찾지 못했는데, 루프가 이미 IMU 수신을 전제로 짜여 있다는 점과 맞물린다 —
**다만 「UseIMU 는 죽은 파라미터다」로 단정하지 않는다.** 읽는 지점을 못 찾은 것이지 부재 증명이 아니다.

## A.18 `run()` 이 필터를 두 번 구동하는 이유

`addOdoMeasurement` → `addImuMeasurement` → `update()` 3연속 호출이 `run()` 안에 **두 번** 있다.
뒤따르는 코드가 둘을 가른다:

| 블록 | 위치 | 뒤에 오는 것 | 성격 |
| --- | --- | --- | --- |
| ① | `+637 ~ +753` | `rbk::core::Time::init()` → `VelocityEstimatorIMU()` 생성 | **초기화 1회** — `getFilterOdometer` 없음 ⇒ **발행 안 함** |
| ② | `+12381 ~ +12535` | `Message_Odometer` 생성 → `CopyFrom` → **`getFilterOdometer()`** | **주기 경로** — 결과를 꺼내 발행 |

⇒ 첫 블록은 첫 샘플로 필터·시간·속도추정기를 세우는 워밍업이고, 실제 융합 산출은 둘째 블록에서 나온다.
§A.15 의 "첫 주기는 기준선만" 과 층위가 다르다 — 이쪽은 `run()` 진입 시 1회, 저쪽은 `update()` 내부 플래그다.

## A.19 곁가지 구성요소 (같은 플러그인 안)

`libRobotPosEKF.so` 는 EKF 말고도 몇 가지를 더 담고 있다.

**`VelocityEstimatorIMU`** — IMU 기반 속도 추정기. 메서드에 `LowPassFilter(double,double,double)` 이 있다.
`run()` 이 **호출은 한다** `[존재]` (`DataInput(6 doubles)` ×2 · `DataOutputVelX/Y` ×2 ·
`GetAngularVelMeas` ×2 · `Init`/`ResetData` 각 1).

⚠ **그러나 그 결과를 아무도 읽지 않는다.** 출력은 멤버 `0xdc0`(VelX)·`0xdc8`(VelY)·`0xdd0`(AngularVel)에
저장되는데, 라이브러리 전량에서 그 세 오프셋에 대한 명령은 **저장 6건뿐이고 적재 0건**이다.
`RobotPosEKF` 에 속도 접근자도 없다.

⇒ **계산은 돌지만 산출물은 소비되지 않는다**(write-only). 이 추정기가 융합·발행에 관여한다는
근거는 없다. 「IMU 가 속도 추정에도 쓰인다」로 읽으면 안 된다.

**`SkidDetector`** — 미끄러짐 감지기. 오버로드 2종:
`Update(Message_Odometer&, Message_IMU, int, int)`(@+2632) 와 레이저까지 받는
`Update(Message_Odometer&, Message_IMU, Message_Laser, int, int)`(@+2822).
설정자 4종(`SetInertialThreshold(double,double)` · `SetOdometryThreshold(double)` ·
`SetLaserOdomSwitch(bool)` · `SetLaserParam(double,double,double)`)이 `robot.param` 의
`SkidDetect*` 키들과 대응한다.

두 오버로드는 **멤버 `0xd50` 의 bit0** 로 갈린다(`mov 0xd50(%r13),%al` → `test $0x1,%al` → `jne`):
세워져 있으면 레이저 포함 판정으로, 아니면 IMU 전용 판정으로 간다. 인자 두 개는 멤버
`0xbd0`·`0xc90`(int)에서 온다.

⚠ **바깥 게이트는 확인하지 못했다** — 이 구간 진입 직전이 수치 비교(`jbe → +4323`)이고
`StartSkidDetection` 을 읽는 지점으로 특정하지 못했다. 배포가 `StartSkidDetection = 0` 이므로
실행 여부는 여전히 **`[동작-미검증]`** 이다.

**`VarianceCalculator::cal(double)`** — `run()` 에서 3회. 결과는 스택 지역(`0x98(%rsp)`·`(%rsp)`)으로
가서 후속 계산에 쓰이며, **§A.13 의 EKF 공분산 멤버로 들어가지 않는다.** 공분산 미스터리와는 무관하다.

## A.20 슬립 감지의 바깥 게이트 — 파라미터가 아니라 **타임스탬프 신선도**

`SkidDetector` 블록 진입 직전(@+2344~+2391)에 같은 형태의 검사가 **두 번** 있다:

```
mov  0x…(%rsp),%rax        ; Message_Header 포인터
test %rax,%rax ; jne       ; null 이면 _default_instance_ 사용
mov  0x…(%rsp),%rcx        ; 직전에 처리한 시각
cmp  %rcx,0x20(%rax)       ; header 의 +0x20 (타임스탬프)
jbe  → +4323 (건너뜀)
```

⇒ **오도·IMU 각각의 헤더 타임스탬프가 직전보다 새로울 때만** 아래로 내려간다.
`StartSkidDetection` 을 읽는 지점은 여기에도 없다(§A.16).

그 아래에서 임계·윈도우 파라미터 5개를 읽어 설정자에 넣고
`SkidDetector::Update` 를 부른다 — 즉 **파라미터로 끄는 구조가 보이지 않는다.**

⚠ 다만 `Update` 의 반환값이 이후 어떻게 쓰이는지는 끝까지 따라가지 않았다.
반환값 소비 지점에서 다시 걸러질 가능성은 남는다. **「슬립 감지가 돈다」로 확정하지 않는다.**

## A.21 `run()` 이 올리는 진단 2건 — IMU 이상 감지

| 호출 | 코드 | `rbk.error` 등급·문구 |
| --- | --- | --- |
| `setFatal(50400)` @+13322 | **50400** | **fatal** — "gyro original data error" |
| `warningExists`/`setWarning`/`clearWarning`(54300) @+14072/+14126/+14397 | **54300** | warning — "imu noise is too large" |

두 블록 모두 `OpenIMUErrorDetect`(값 주소 `0x7f0`) 아래에 있다 —
@0xeca74 에서 `mov 0x7f0(%r13),%al` → `test $0x1,%al` → `je` 로 건너뛴다.

배포값은 `OpenIMUErrorDetect = 0` 이고 **코드가 그 값을 실제로 읽으므로**
이 두 진단은 **`[동작]` 비활성**이라고 말할 수 있다(§A.16 의 `StartSkidDetection` 과 대비된다 —
그쪽은 읽는 곳이 없어 배포값 0 이 효력을 갖는지 알 수 없다).

임계 `IMUNoiseDetectThred = 3.0` · `IMUErrorDetectThred = 20.0` · `IMUErrorDetectTime = 10` 은
그래서 현재 적용되지 않는다.

## A.22 슬립 판정 결과는 **로그로만 나간다**

`SkidDetector::Update` 의 반환값을 끝까지 따라갔다.

```
+2640/+2827 : mov %eax,%ebx            ; Update 반환값 보관
+2876       : cmpb $0x0,0x33a(%r13)    ; CalibStatus 수신 플래그
+2884       : sete %al                 ; al = (캘리브 상태 아님)
+2887       : and  %bl,%al             ; al = 슬립판정 AND 캘리브아님
+2905       : je   → +4265             ; 거짓이면 건너뜀
+2919~      : stringstream → ostream_insert → rbk::Logger::thread
```

참일 때 실행되는 블록은 **로깅뿐이다.** 그 구간(+2876~+3120)에
`setError`·`setWarning`·`setFatal` 도, 상태 멤버 쓰기도 없다.

그리고 `Message_Odometer::set_detect_skid` 는 **호출 명령이 0건**이다
(동적 심볼 테이블에는 있으나 `.text` 에 호출지 없음) ⇒ 발행하는 오도 메시지의
`detect_skid` 필드를 **세우지 않는다.**

⇒ **이 플러그인의 슬립 감지는 시스템 거동에 영향을 주지 않는다.** 로그만 남는다.
`StartSkidDetection` 파라미터를 읽지 않아 「끄지 못하는 것 아닌가」 했던 우려(§A.16)는
결과적으로 무해하다 — 켜져 있어도 로그뿐이다.

측위 쪽 슬립 대응은 별개다 — `MCLoc::CheckWheelSkid` 가 `setError(0xcdee=52718)`
'Detect skid and stop AGV' 를 올린다(오도 생산 문서 §8.4). 두 기구는 서로 무관하다.

## A.23 미초기화 공분산은 **실제로 필터에 복사된다** `[존재]`

`BFL::AnalyticConditionalGaussianAdditiveNoise::AdditiveNoiseSigmaSet` @0x191f40 전문:

```
mov  0x8(%r14),%rcx ; mov %rcx,0x100(%rbx)   ; n 복사
... 원소 수가 다르면 operator new 로 재할당, 기존 버퍼 delete ...
mov  0x18(%r14),%r15 ; shl $0x3,%r15         ; 원소 수 × 8 바이트
mov  0x20(%r14),%rsi                          ; src 버퍼
mov  0x118(%rbx),%rdi                         ; dst 버퍼
jmp  memmove@plt                              ; tail-call
```

**크기만 쓰는 것이 아니라 데이터를 `memmove` 로 통째 복사한다.**

⇒ §A.13~A.14 와 합치면: `odom_covariance_`·`imu_covariance_` 의 **초기화되지 않은 힙 내용이
매 주기 측정모델의 additive noise sigma 로 그대로 들어간다.** 경로가 끊겨 있지 않다.
런타임에 그 메모리가 무엇인지는 여전히 `[동작-미검증]` 이다.

## A.24 `UseIMU`·`StartSkidDetection` — 읽는 코드가 없다는 판정의 근거

`MutableParam` 의 공개 접근자는 `isChanged` · `isMutable` · `init` · 생성자/소멸자뿐이고
**값을 꺼내는 `operator T()`·`get()` 류가 없다**(동적 심볼 전수). 즉 값은 **멤버 직접 접근**으로만
읽히며, 그것이 §A.16 에서 쓴 기법(값 주소 `슬롯+0x78` 스캔)과 정확히 일치한다.

`loadFromConfigFile` 의 `UseIMU` 적재 직후에도 다른 멤버로 복사하는 명령이 없다(다음 `loadParam` 로 바로 넘어간다).

⇒ 대조군(읽히는 파라미터 11개) + 접근자 부재 + 적재 직후 미복사 — 세 근거가 모여
**`UseIMU`(0x3b8)·`StartSkidDetection`(0x448)은 이 라이브러리에서 소비되지 않는다**고 볼 근거가 강하다.
다만 인라인 최적화로 형태가 완전히 달라졌을 가능성은 원리상 남으므로 **`[존재]` 수준**으로 둔다.

## A.25 `wzOdoAbsDeg` 임계 1.0 deg/s — 근거 없음

`robot.param` 전 테이블에서 값이 `1`/`1.0` 이면서 각속도 관련 이름을 가진 키를 조회했으나
`RobotPosEKF` 테이블에는 없다(걸린 것은 `MCLoc.ExtraMoveAngleThreshold`·`MoveFactory.GoAngle` 등 무관한 키).
바이너리 문자열에도 그 임계를 설명하는 항목이 없다.

⇒ **1.0 deg/s 는 코드에 하드코딩된 값이며, 그 선택 근거는 원본 자산에서 확인할 수 없다.**
벤더 판단으로 보이나 **추측하지 않는다.**

## A.26 EKF 입출력의 100배 스케일 — 대칭이며 단위는 보존된다 `[존재]`

**출력** `getFilterOdometer` @0x17a1a0:

```
state(1) → mulsd [0x197ee8]=100.0 → Message_Odometer.x    (0x30, double)
state(2) → mulsd [0x197ee8]=100.0 → Message_Odometer.y    (0x40, double)
state(6) → cvtsd2ss                → Message_Odometer.angle(0x3c, float)
```

**입력** `addOdoMeasurement` @0x179f20:

```
Message_Odometer.x (0x30) → divsd [0x197ee8]=100.0
Message_Odometer.y (0x40) → divsd [0x197ee8]=100.0
Message_Odometer.angle(0x3c) → cvtss2sd (배율 없음)
```

⇒ **입력 ÷100, 출력 ×100 으로 대칭이다.** 각도에는 양쪽 모두 배율이 없다.
`proto/message_odometer.proto` 는 `double x = 3; // m` · `double y = 4; // m` · `float angle = 5; // rad` 이므로
**발행 메시지의 단위는 미터로 보존되고, EKF 내부 상태만 그 1/100 스케일로 다룬다**(수치 조건화로 보인다).

⇒ 단위 사슬은 **깨지지 않는다.** (이 절의 초판에서 "단위 정합이 어긋날 수 있다" 고 경고했으나,
입력 쪽을 확인한 결과 대칭이어서 그 우려는 해소됐다.)

속도 필드(`vel_*`)·`is_stop`·`motor_info` 는 `getFilterOdometer` 가 건드리지 않는다 —
`run()` 이 직전에 수신 오도 메시지를 `CopyFrom` 하므로 **원본 오도 값이 그대로 실려 나간다.**
§A.19 대로 `VelocityEstimatorIMU` 결과는 여기에도 들어가지 않는다.

## A.28 `ReadIMUParam()` 이 읽는 것 — IMU 장착·보정 `[존재]`

`RobotPosEKF::ReadIMUParam()` @0xe2ef0 이 부르는 함수는 다섯이다:

```
rbk::chasis::Model::Instance()
rbk::chasis::Model::getModelDevices("controller")   ; 즉치 "controll"+"er", 길이 0xa
double rbk::chasis::Model::getModelParam<double>(...)
rbk::chasis::Calibration::Instance()
rbk::utils::hashmap::HashBucket<...>                ; 키 조회
```

⇒ IMU 값의 출처는 `robot.param`(SQLite)이 **아니라** `robot.model`(JSON)의 `controller`
디바이스다. 그 디바이스의 파라미터와 이 기체 배포값:

| 키 | 단위 | 값 | 뜻 |
| --- | --- | --- | --- |
| `Bax` · `Bay` · `Baz` | m/s² | 0 · 0 · 0 | 가속도계 축별 바이어스 |
| `x` · `y` · `z` | m | 0 · 0 · 0 | IMU 장착 위치 |
| `qx` · `qy` · `qz` · `qw` | 1 | 0 · 0 · 0 · **1** | 장착 자세 쿼터니언 |
| `SSF` | LSB/(°/s) | 16.03556 | 자이로 감도 스케일 |

**IMU 축·부호 규약**: 장착 자세가 **단위 쿼터니언**이고 위치가 (0,0,0)이므로 이 기체에서
IMU 프레임은 차체 프레임과 같다 — 축 교환도 부호 반전도 없다. 바이어스도 전부 0이다.

⚠ **이 배포값은 `Roll_A084` 것이다.** 원본 하드의 `robot.model` 은 `"model":"Roll_A084"` 이고
우리 기체는 `Foil_A082` 다. 값을 우리 쪽으로 옮겨 쓰지 말 것 — 규약(단위 쿼터니언 = 축 변환 없음)만
참고 대상이다. 또 `controller` 디바이스는 `isEnabled: false` 다.

출처: `/usr/local/etc/.SeerRobotics/rbk/resources/models/robot.model`
(⚠ `rbk/` 아래가 아니다 — 이전 조사에서 `rbk/robot.model` 로 찾다 못 찾았다.)

## A.29 `UseIMU` — 이 플러그인은 이름으로 참조하지 않는다 `[존재]`

`robot.param` 의 `RobotPosEKF` 테이블에 실재한다:

```
Key                              Type  Value  Mutable
UseIMU                           b     1      0        ← 이것만 Mutable=0
OpenIMUErrorDetect               b     0      1
IMUErrorDetectTime               i     10     1
IMUNoiseDetectThred              d     3.0    1
IMUErrorDetectThred              d     20.0   1
StartSkidDetection               b     0      1
LaserOdomDetectSkid              b     0      1
```

**대조군 실험** — 각 키 문자열의 `.rodata` 오프셋을 구해 `lea …(%rip)` 참조를 센 결과:

| 키 | 오프셋 | 참조 |
| --- | --- | --- |
| `UseIMU` | 0x19ad68 | **0건** |
| `OpenIMUErrorDetect` | 0x19ad84 | 1건 |
| `StartSkidDetection` | 0x19ae5f | 1건 |
| `IMUErrorDetectThred` | 0x19ae29 | 1건 |
| `IMUNoiseDetectThred` | 0x19adf3 | 1건 |
| `IMUErrorDetectTime` | 0x19adac | 1건 |
| `LaserOdomDetectSkid` | 0x19ae8e | 1건 |

형제 6개가 전부 정확히 1건인데 `UseIMU` 만 0건이다. **`Mutable=0` 인 유일한 키**라는 점과
정합한다 — 이름 문자열을 필요로 하는 등록 경로(`MutableParam<T>::init`)를 타지 않는다.

⚠ **판별력 없는 검사 하나를 함께 적어 둔다.** 「데이터 섹션에 그 주소를 담은 8바이트 포인터가
있는가」도 봤는데 **세 키 모두 0건**이었다. 즉 이 검사는 참조되는 키와 안 되는 키를 가르지
못하므로 **근거로 쓸 수 없다.** 판별력이 있는 것은 위의 `lea` 참조 쪽이다.

⇒ **`UseIMU=0` 경로는 이 라이브러리 안에 없다.** 값을 읽는 코드가 없으므로 0으로 바꿔도
이 플러그인의 거동은 바뀌지 않는다. IMU 융합을 끄는 스위치가 아니라는 뜻이며,
§A.20(주루프가 IMU 수신 래치를 무조건 기다린다)과 합치면 **IMU 는 선택이 아니라 전제**다.

⚠ `[존재]` 수준이다 — 다른 바이너리가 이 값을 읽어 플러그인 로드 자체를 가르는 가능성은
이 조사로 배제되지 않는다(`grep -rl 'UseIMU'` 결과 이 `.so` 와 `robot.param` 두 곳뿐이지만,
값 전달은 이름 없이도 가능하다).

## A.27 아직 모르는 것

- 두 공분산 버퍼의 **런타임 값**(§A.13·A.14·A.23) — 정적 분석은 여기까지다. 실기 또는 원본 구동 대조가 필요하다.
- `VelocityEstimatorIMU` 결과가 버려지는 것이 의도인지 잔재인지 — 판단 근거 없음.
- 내부 상태를 1/100 로 스케일한 이유 — 수치 조건화로 보이나 근거는 확인 불가.
- `UseIMU` 값을 **다른 바이너리가** 읽어 쓰는지(§A.29) — 이 플러그인 밖은 조사하지 않았다.
