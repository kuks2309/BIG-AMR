# 휠 오도 + IMU 융합 EKF 이식 (레거시 RobotPosEKF)

## 무엇을

`src/Navigation/odom_imu_ekf/` 패키지를 신설했다. 레거시 배선의 `RobotPosEKF` 자리에 대응한다.

```
휠 오도 (nav_msgs/Odometry) ─┐
                              ├→ odom_imu_ekf → odom_fused → (측위)
IMU (sensor_msgs/Imu) ───────┘
```

| 파일 | 내용 |
| --- | --- |
| `include/odom_imu_ekf/ekf.hpp` · `src/ekf.cpp` | ROS-무의존 6-D EKF 코어 |
| `src/odom_imu_ekf_node.cpp` | rclcpp 노드 + `/diagnostics` |
| `test/test_ekf.cpp` | 코어 회귀(8항목) |
| `launch/odom_imu_ekf.launch.py` | 단독 기동 + 토픽 remap |

## 왜

원본 분석 결과 **측위가 소비하는 오도는 휠 오도가 아니라 오도·IMU 융합본**이고
(`Tools/seer_re/docs/legacy_runtime_wiring.md` §A.1~A.27), 우리 스택에는 그 층이 통째로 없었다.
레거시가 yaw 드리프트를 잡던 기구가 빠져 있던 셈이다.

## 원본에서 그대로 옮긴 것

- 상태 6-D (x, y, z, roll, pitch, yaw)
- 예측 `x⁺=x+v·cosθ` · `y⁺=y+v·sinθ` · `θ⁺=θ+ω` (z·roll·pitch 는 관측으로만)
- 야코비안 비영 항은 yaw 열뿐 — `F(1,6)=−v·sinθ`, `F(2,6)=+v·cosθ`
- 관측행렬 `Hodom`=(x,y,yaw) · `Himu`=(roll,pitch,yaw)
- 시스템 잡음 대각 1e6(σ=1000) · prior 대각 1e-6(σ=0.001)
- IMU 갱신 게이트 `|ω| > 1.0 deg/s`
- 센서별 첫 주기는 기준선만 세우고 융합하지 않음
- 내부 x·y 스케일 ÷100 / ×100 — **잡음 상수가 그 공간에서 정의돼 있어 한 벌로 옮겼다**
- 오도·IMU 를 둘 다 받기 전에는 발행하지 않음(IMU 수신은 래치)
- 자세만 융합으로 덮고 `twist` 등은 수신 메시지를 그대로 물려 보냄

## 의도적으로 이탈한 것

**관측 잡음.** 원본은 `odom_covariance_`·`imu_covariance_` 를 크기만 잡고 값을 넣지 않아
초기화되지 않은 힙 메모리가 매 주기 측정모델로 `memmove` 된다(§A.13·A.14·A.23).
재현 대상이 아니므로 **파라미터로 노출된 상수**를 쓴다(기본값은 원본 생성자가 측정모델에 넘긴
지역 행렬 대각 1.0).

⇒ 이 이탈 때문에 **비트 대조는 성립하지 않는다.** 검증은 수치 특성 시험으로 한다.

## 이식하지 않은 것

원본에 있으나 **소비되지 않는** 것들: `UseIMU`·`StartSkidDetection`(읽는 코드 없음),
`VelocityEstimatorIMU`(출력 소비 없음), 슬립 감지(로그만), rf2o 레이저 오도(배포 비활성),
VO·GPS(멤버째 삭제).

## 검증

- 코어 회귀 8항목 통과: 두 센서 대기 · 센서별 첫 주기 기준선(게이트 통과 시에도) ·
  게이트 미만 미반영 · 게이트 초과 시 두 관측 사이로 융합 · 절대 드리프트 미전파 ·
  z 불변 · roll·pitch 반영 · 내부 스케일 값
- **돌연변이 6건 전부 검출**(게이트 제거 · 첫주기 건너뛰기 · 절대값 사용 · 관측축 오배정 ·
  IMU 없이 진행 · 스케일 제거), 원복 시 0
  - 최초 6건 중 「첫주기 건너뛰기」가 **미검출**이라 시험 2b 를 추가해 닫았다
- `colcon build` · `colcon test` 1/1 통과
- **실기동 확인**(청정 도메인): IMU 없이 오도만 있을 때 `/odom_fused` 무발행,
  `/diagnostics` 가 ERROR("IMU not received")로 드러냄
  - ⚠ 첫 시도는 다른 도메인의 잔여 발행자 때문에 오염됐다 — 청정 도메인에서 재확인했다

## 측위 배선

`bringup.launch.py` 에 `imu_fusion` 인자를 넣었다. **기본값 false** — 켤 때만 경로가 바뀌므로
현행 스택 거동은 그대로다.

```
imu_fusion:=false   icp_odometry ──/odom────────────────────> mcl2d      (현행)
imu_fusion:=true    icp_odometry ──/odom──┐
                                           ├→ odom_imu_ekf ──/odom_fused──> mcl2d
                    iahrs_driver ─/imu/data┘
```

측위는 오도 토픽을 **증분 예측**에만 쓰고 `map→odom` 은 TF 를 되짚어 역산한다
(`mcl2d_localization_node.cpp` 의 `lookupTransform(odom_frame_, base_frame_)`).
그래서 융합 토픽을 물려도 TF 체인은 어긋나지 않는다 — 바뀌는 것은 예측 증분뿐이다.

**레거시와 다른 점**: 원본의 융합 입력은 휠 오도였는데 여기서는 ICP 오도다.
휠 오도는 조향 부호가 확정되기 전까지 신뢰할 수 없다(`debt-004`·`debt-007`).

## 배선 과정에서 잡은 결함

- **런치 경유 기동이 죽는 상태였다.** `imu_gate_rate_deg` 를 문자열 그대로 double 파라미터에
  넘겨 타입이 어긋났다. 앞선 검증이 실행 파일 직접 기동이라 드러나지 않았다 —
  `ParameterValue(..., value_type=float)` 로 고치고 **런치 경유로 다시 검증**했다.
- **게이트가 한 번도 안 열리는 무증상 실패**를 볼 수 없었다. 진단이 1 Hz 스냅샷뿐이라
  놓친다 — 누적값 `imu_applied`·`odom_yaw_rate_max` 를 넣어 「발행은 되는데 IMU 는 한 번도
  안 쓰인다」가 드러나게 했다.

## 배선 검증 (청정 도메인)

- 런치 경유 기동: 인자 `imu_gate_rate_deg:=2.0` 이 실제로 적용됨(기동 로그 `게이트 2.00 deg/s`)
- IMU 없이 오도만: `/odom_fused` 무발행 + `/diagnostics` level 2(ERROR)
- IMU 부착 후: 발행 91 · `imu_applied` 90 — 첫 주기 기준선 1건을 뺀 값과 정확히 일치,
  `odom_yaw_rate_max` 0.5 (게이트 2 deg/s 통과)
- `imu_fusion:=false`: 측위가 `/odom` 구독, 융합기 부재
- `imu_fusion:=true`: `/odom` 구독 1(=융합기) → `/odom_fused` 발행 1·구독 1(=측위), 중복 노드 0
  - ⚠ 첫 시도는 앞 케이스 프로세스가 남아 노드가 둘로 보였다 — 단독 재실행으로 확정했다

## 남은 것

- **기본값을 true 로 돌리는 것은 실기 검증 후 결정**한다 → `debt-108` (③ 존치)
- 휠 오도를 소스로 쓰려면 조향 부호 2건(`debt-004`·`debt-007`)이 선결이다 —
  IMU 융합은 오차를 줄이지만 **부호 반전을 고쳐 주지 않는다**
- 실기·rosbag 검증 0회. 지금까지는 합성 발행자로만 확인했다
