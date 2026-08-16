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
