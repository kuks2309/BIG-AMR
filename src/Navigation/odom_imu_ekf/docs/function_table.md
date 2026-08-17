# odom_imu_ekf 함수표 · 멤버변수표 (모듈 로컬 권위본)

> 대상: 패키지 전체(ROS 무의존 코어 + 노드 + 회귀 하니스). 원본 대조 근거는
> 배선 정본 [Tools/seer_re/docs/legacy_runtime_wiring.md](../../../../Tools/seer_re/docs/legacy_runtime_wiring.md) 부록 A.

## include/odom_imu_ekf/ekf.hpp · src/ekf.cpp — `OdomImuEkf` (ROS 무의존 코어)

| 함수 | 위치 | 입력 | 출력 | 부작용 |
| --- | --- | --- | --- | --- |
| `normalizeAngle(a)` | ekf.cpp:8-15 | 각도(rad) | [−π, π) 로 정규화된 각 | 없음(순수) |
| `OdomImuEkf(params)` 생성자 | ekf.cpp:17-21 | `Params` | — | 공분산 대각을 `prior_covariance` 로 채운다. 상태는 0 |
| `addOdom(pose, yaw_rate)` | ekf.cpp:23-29 | 오도 절대 자세, 회전율(rad/s) | — | 직전/현재 오도 갱신. **절대값이 아니라 증분만** 쓰이고, 회전율은 IMU 게이트 판정용 |
| `addImu(roll, pitch, yaw)` | ekf.cpp:31-37 | IMU 자세 3축(rad) | — | 최신 IMU 자세 보관 + 수신 플래그 |
| `predict(d_trans, d_yaw)` | ekf.cpp:39-66 | 병진 증분(m), 회전 증분(rad) | — | 상태 전진 + 공분산 전파. 야코비안 비영은 yaw 열뿐이라 그 희소성만큼만 전개하고 대각에 시스템 잡음을 더한다 |
| `correct(indices, count, measurement, noise)` | ekf.cpp:68-101 | 관측 상태 인덱스 목록, 관측값, 관측 잡음 | — | 성분별 순차 갱신. H 가 상태를 고르기만 하므로 스칼라 잔차로 같은 결과가 난다. 각도 성분은 잔차·결과 모두 정규화 |
| `update()` | ekf.cpp:103-156 | — | bool(한 주기 성립 여부) | 한 주기 융합. **오도·IMU 를 둘 다 받기 전에는 거짓**을 돌려주고 아무것도 하지 않는다. 센서별 첫 주기는 기준선만 세운다. IMU 는 회전율이 게이트를 넘을 때만 반영 |
| `pose()` / `odomInitialized()` / `imuInitialized()` / `lastImuApplied()` | ekf.hpp:75-93 | — | 융합 자세 · 초기화·반영 여부 | 없음(조회 전용). `lastImuApplied` 는 게이트 통과 진단용 |

### 멤버 변수 (전역변수 없음 — 모듈 전역 0)

| 변수 | 위치 | 용도 |
| --- | --- | --- |
| `params_` | ekf.hpp:103-103 | 잡음·게이트 상수 묶음. 생성 시 고정 |
| `x_` / `P_` / `pose_` | ekf.hpp:104-106 | 상태(x·y 는 내부 스케일) / 공분산 / 스케일 환원한 출력 |
| `odom_init_` / `imu_init_` / `last_imu_applied_` | ekf.hpp:108-110 | 센서별 첫 주기 판정과 게이트 반영 여부 |
| `has_odom_` / `has_imu_` | ekf.hpp:112-113 | 수신 래치 — 둘 다 서기 전에는 `update()` 가 진행하지 않는다 |
| `odom_cur_` / `odom_prev_` / `odom_yaw_rate_` | ekf.hpp:114-115 | 증분 계산 기준점과 게이트 판정용 회전율 |
| `imu_roll_` / `imu_pitch_` / `imu_yaw_` | ekf.hpp:116-116 | 최신 IMU 자세 3축 |

### 상수 (원본에서 옮겨 온 값)

| 상수 | 위치 | 값 | 근거 |
| --- | --- | --- | --- |
| `kStateDim` | ekf.hpp:16-16 | 6 | 원본이 `ColumnVector(6)`/`SymmetricMatrix(6)` 으로 잡는다 |
| `kPositionScale` | ekf.hpp:30-30 | 100.0 | 원본이 x·y 에만 거는 내부 스케일. 입력에서 나누고 출력에서 곱해 대칭이나, **잡음 상수가 이 공간에서 정의돼 있어** 함께 옮겼다 |
| `Params::system_noise` | ekf.hpp:46-46 | 1e6 | 원본 생성자가 6축 모두 이 값으로 채운다 |
| `Params::prior_covariance` | ekf.hpp:48-48 | 1e-6 | 원본 `initialize()` 가 6×6 전량을 채운다 |
| `Params::imu_gate_rate` | ekf.hpp:56-56 | 1 deg/s | 원본 하드코딩. 정지·직진 중 자이로 바이어스가 yaw 로 새는 것을 막는다 |

## src/odom_imu_ekf_node.cpp — `OdomImuEkfNode` (rclcpp::Node)

| 함수 | 위치 | 입력 | 출력 | 부작용 |
| --- | --- | --- | --- | --- |
| `quatToRpy(x, y, z, w, roll, pitch, yaw)` | odom_imu_ekf_node.cpp:23-37 | 쿼터니언 4성분 | roll·pitch·yaw(참조 출력) | 없음(순수). `asin` 인자를 잘라 수치오차로 NaN 이 되는 것을 막는다 |
| `OdomImuEkfNode()` 생성자 | odom_imu_ekf_node.cpp:43-75 | ROS 파라미터(잡음 4종·게이트·발행 프레임·진단 주기) | — | 코어 생성, 구독 2종(오도 BEST_EFFORT·IMU SensorDataQoS), 발행 2종, 진단 타이머 |
| `onImu(m)` | odom_imu_ekf_node.cpp:78-84 | `sensor_msgs/Imu` | — | 자세를 코어에 넣고 수신 표시. 여기서는 융합을 돌리지 않는다 |
| `onOdom(m)` | odom_imu_ekf_node.cpp:86-126 | `nav_msgs/Odometry` | — | 한 주기 융합 구동 + 발행. 수신 메시지를 그대로 물려 보내며 **자세만** 덮는다. IMU 미수신이면 발행하지 않는다 |
| `publishDiag()` | odom_imu_ekf_node.cpp:128-169 | — (타이머 구동) | — | `/diagnostics` 발행. IMU 미수신은 ERROR — 조용한 무발행을 막는다. 누적값이 「발행은 되는데 IMU 는 한 번도 안 쓰인다」를 드러낸다 |
| `main` | odom_imu_ekf_node.cpp:184-190 | argc/argv | int | `rclcpp::spin` |

### 멤버 변수 (전역변수 없음 — 모듈 전역 0)

| 변수 | 위치 | 용도 |
| --- | --- | --- |
| `ekf_` | odom_imu_ekf_node.cpp:171-171 | 융합 코어 한 대 |
| `sub_odom_` / `sub_imu_` | odom_imu_ekf_node.cpp:172-173 | 오도(BEST_EFFORT) · IMU(SensorDataQoS) 구독 |
| `pub_` / `pub_diag_` / `diag_timer_` | odom_imu_ekf_node.cpp:174-176 | 융합 오도 발행 / 진단 발행 / 진단 주기 타이머 |
| `publish_frame_` | odom_imu_ekf_node.cpp:177-177 | 비어 있지 않으면 발행 메시지의 `frame_id` 를 덮는다 |
| `imu_seen_` / `published_` / `imu_applied_` / `odom_yaw_rate_max_` | odom_imu_ekf_node.cpp:178-181 | 진단 지표 — 수신 여부·발행 수·IMU 반영 수·관측된 최대 회전율 |

## test/test_ekf.cpp — 회귀 하니스 (노드 미포함)

| 함수 | 위치 | 입력 | 출력 | 부작용 |
| --- | --- | --- | --- | --- |
| `main` | test_ekf.cpp:26-136 | — | 0(통과) / 1(실패) | 8항목 검사. 원본이 관측 잡음 자리에 미초기화 메모리를 넘겨 **비트 대조가 성립하지 않으므로** 수치 특성으로 고정한다 |
