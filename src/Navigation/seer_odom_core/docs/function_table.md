# seer_odom_core 함수표 · 멤버변수표 (모듈 로컬 권위본)

> 대상: Seer `OdoCalculator`(`MultiSteersOdometer`) 재구현. ROS 의존 0.
> 복원 근거는 [docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md](../../../../docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md) §2·§9~§14,
> 채취물은 [References/seer/libOdoCalculator/](../../../../References/seer/libOdoCalculator/).

## src/multisteer_odometer.cpp — `MultiSteersOdometer`

| 함수 | 위치 | 입력 | 출력 | 부작용 | 원본 대응 |
| --- | --- | --- | --- | --- | --- |
| `normalize(x)` | multisteer_odometer.cpp:10-21 | 각도(rad) | [−π, π) | 없음(순수) | `rbk::foundation::utils::Normalize` 0x18750 |
| `setMotorParams(wheels)` | multisteer_odometer.cpp:23-57 | 휠 기하 목록 | bool(굳었는가) | 계수행렬 (AᵀA)⁻¹Aᵀ 사전 계산 | `CalOdoCoef` 79~107 |
| `setVitalInfo(info)` | multisteer_odometer.cpp:59-62 | 모터별 계측 map | — | 이번 주기 계측 보관 | `ExtractMotorInfo` 계열 |
| `buildObservation(use_velocity, b)` | multisteer_odometer.cpp:64-78 | 속도/변위 선택 | bool(전 휠 계측 존재) | 관측벡터 b 채움 | `CalSpeed`/`CaldPose` 공통부 |
| `applyCoef(b, r0, r1, r2)` | multisteer_odometer.cpp:80-90 | 관측벡터 | 3성분 | 없음 | `general_matrix_vector_product` |
| `calSpeed()` | multisteer_odometer.cpp:92-119 | — | — | `output.vx/vy/vw` + `wheel_consistent_` | `CalSpeed` 110~156 |
| `caldPose()` | multisteer_odometer.cpp:121-133 | — | — | `output.dx/dy/dyaw`. **속도는 항상 0으로 지운다** | `CaldPose` 159~195 |
| `calPose(dt_sec)` | multisteer_odometer.cpp:135-160 | dt(속도 경로 전용) | — | `output.x/y/yaw` 누적. 각을 먼저 갱신·정규화하고 **그 각으로** 회전(end-point) | `AbstractOdometer::CalPose` 425~454 |

## 멤버 변수 (전역변수 없음 — 모듈 전역 0)

| 변수 | 위치 | 용도 | 원본 대응 |
| --- | --- | --- | --- |
| `wheels_` | multisteer_odometer.hpp:90-90 | 휠 기하. 순서가 관측벡터 순서를 정한다 | `mapMotorParam` |
| `coef_` | multisteer_odometer.hpp:94-94 | (AᵀA)⁻¹Aᵀ, 열 우선 3×2n | 사전 계산 역행렬 |
| `vital_` | multisteer_odometer.hpp:95-95 | 이번 주기 모터 계측 | `curVitalInfo` |
| `output_` | multisteer_odometer.hpp:97-97 | 속도·증분·누적 자세 | `output` (88 B) |
| `coef_ready_` | multisteer_odometer.hpp:98-98 | 계수행렬이 굳었는가 | `flagCoefCal` |
| `cum_enc_pose_mode_` | multisteer_odometer.hpp:99-99 | 변위 누적(true) vs 속도 적분 | `flagCumEncPoseMode` (배포값 1) |
| `first_input_got_` | multisteer_odometer.hpp:100-100 | 첫 입력 전에는 증분·자세를 만들지 않는다 | `flagFirstInputGot` |
| `wheel_consistent_` | multisteer_odometer.hpp:101-101 | `calSpeed()` 잔차가 임계 이하였는가 | `flagWheelConsistent` |
| `thres_consistent_` | multisteer_odometer.hpp:102-102 | 일관성 임계 (배포값 0.02) | `thresConsistent` |

## 원본에서 의도적으로 이탈한 것

| 항목 | 원본 | 여기 | 이유 |
| --- | --- | --- | --- |
| 특이 행렬 | 검사 없음 | `setMotorParams` 가 거짓 반환 | 굳은 쓰레기값으로 매 주기 도는 것보다 서지 않는 편이 낫다 |
| 로그 | `rbk::Logger` 로 행렬·경고 출력 | 없음 | 대조 대상이 아니다 |
| 파일 덤프 | `FileSystem::rbkUserData` 에 행렬 저장 | 없음 | 〃 |

## test/test_odometer.cpp

| 함수 | 위치 | 출력 | 부작용 |
| --- | --- | --- | --- |
| `main` | test_odometer.cpp:60-294 | 0(통과)/1(실패) | 14항목. **돌연변이 8/8 검출** — 회전 순서·정규화 방식·속도 소거·첫입력 게이트·계수 부호·보정항·입력 슬롯·일관성 임계 |
