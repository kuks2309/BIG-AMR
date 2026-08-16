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

## A.6 아직 모르는 것

- **잡음 σ 수치** — 생성자가 `SymmetricMatrix` 원소를 (1,1)…(6,6)·(4,1)…(4,6) 순으로 채우는 것까지는
  보이나 각 원소의 값을 뽑지 못했다. `update()` 의 `AdditiveNoiseSigmaSet` 2회가 무엇을 넣는지도 미확정.
- **`odom_covariance_`·`imu_covariance_` 의 런타임 출처** — 메시지 동봉 공분산인지 파라미터인지.
- **`wzOdoAbsDeg` 의 용도** — Seer 가 추가한 멤버. 이름은 "오도 각속도 절대값(도)" 를 시사하나 미확인.
- **`ReadIMUParam()`** 이 읽는 값과 IMU 축·부호 규약.
- **`setLaserOdom`/`isEnableLaserOdom`/`getTargetMsgLaser`** — 레이저 오도 융합 경로가 코드에 `[존재]`한다.
  활성 여부는 배포 파라미터 대조 전까지 `[동작-미검증]`.
