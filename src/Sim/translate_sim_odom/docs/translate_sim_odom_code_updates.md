# translate_sim_odom Code Updates

2026-04-26 / (pending commit) / 추가: Wave B 신규 패키지 — 폐쇄 SIL odometry 시뮬

- 신규 패키지 `src/SIL/translate_sim_odom/` (Wave B)
- 입력: `/motor/wheel_cmd` (`trnav_msgs::WheelSetArray`, 2 wheels QD)
- 처리:
  - 2-wheel kinematic 역계산 (vx_i = v cos δ, vy_i = v sin δ)
  - IK forward eq 풀어 body (vx, vy, omega) 계산
  - Euler 적분 (50Hz, dt=1/rate)
- 출력:
  - TF `map → base_link` (50Hz)
  - `/rtabmap/localization_pose` (`PoseWithCovarianceStamped`, 50Hz, SensorDataQoS)
  - `/imu/data` (`sensor_msgs::Imu`, 50Hz, SensorDataQoS, yaw quaternion + omega)
  - `/wheel_motor_state` (`trnav_msgs::WheelMotor`, 50Hz, cmd echo)
- 파라미터: w1_xy / w2_xy (QD layout), initial_xyy yaw, integrate_rate_hz
- 의존: rclcpp, trnav_msgs, geometry_msgs, nav_msgs, sensor_msgs, std_msgs, tf2(_ros, _geometry_msgs)

목적: amr_translate_node 의 폐쇄 루프 SIL — 실 라이다·모터 없이 Phase 0/1-3/4 완주 + 후진(reverse=true) 검증.

참조: `docs/request/2026-04-26_translate_reverse_sil.md`, `docs/plan/2026-04-26_translate_reverse_sil.md`
