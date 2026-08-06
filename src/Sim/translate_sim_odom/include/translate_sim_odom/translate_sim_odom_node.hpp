#ifndef TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_
#define TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_

#include <atomic>
#include <memory>
#include <mutex>
#include <random>

#include "trnav_msgs/msg/wheel_motor.hpp"
#include "trnav_msgs/msg/wheel_motor_state.hpp"
#include "trnav_msgs/msg/wheel_set_array.hpp"
#include "geometry_msgs/msg/pose_with_covariance_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "tf2_ros/transform_broadcaster.h"

namespace translate_sim_odom
{

// 폐쇄 루프 SIL 시뮬레이터 — amr_translate_node 검증용.
//
// 입력  : /motor/wheel_cmd (trnav_msgs::WheelSetArray, 2 wheels QD diagonal)
// 처리  : 구동 가감속 · 조향 슬루 제한 → **실제값** 으로 2-wheel 정기구학 →
//        (vx, vy, omega) → Euler 적분 (50Hz) → 휠 주행거리 누적
// 출력  : TF map→base_link, /rtabmap/localization_pose,
//        /imu/data, /wheel_motor_state, **/wheel_motor_state_detailed(엔코더 counts)**
//
// ⚠ 2026-08-06 이전에는 지령을 **그대로 되울렸다**(cmd echo) — 관성도 조향 소요시간도
//   엔코더도 없었다. 그 결과 상위 액션의 다음 항목이 SIL 에서 **원리적으로 검증 불가**였다:
//     · 정지 지령 후 계속 도는 각(실측 0.57~0.65 s, docs/verified_facts/2026-08-04-…:80)
//     · 조향 자세 전환에 걸리는 시간(90° 스윙 ≈ 1.58 s)
//     · 엔코더 기반 진행량 산출 — 애초에 엔코더가 발행되지 않았다
//   이 세 축이 없으면 시험은 통과하지만 그 통과가 근거가 되지 못한다.
//
// ⚠ 동특성 기본값은 **0(제한 없음) = 종전 즉응 거동** 이다. 이 노드는 SIL·HIL 런치 19개가
//   공유하며 그중 8개가 **검증 완료된 QD 런치**라, 기본값을 바꾸면 그 검증이 말없이 무효가
//   된다. 새 동특성은 런치가 파라미터로 **명시적으로 켤 때만** 작동한다.
//   엔코더 발행(/wheel_motor_state_detailed)은 토픽 추가일 뿐 기존 거동을 바꾸지 않으므로
//   항상 켜 둔다.
//
// QD wheel layout (config):
//   w1 = (w1_x, w1_y) = (+0.330, +0.135)  ← front-left (wheels[0])
//   w2 = (w2_x, w2_y) = (-0.330, -0.135)  ← rear-right (wheels[1])
class TranslateSimOdomNode : public rclcpp::Node
{
  public:
    TranslateSimOdomNode();

  private:
    void wheelCmdCallback(const trnav_msgs::msg::WheelSetArray::SharedPtr msg);
    void integrateAndPublish();

    // ── Robot geometry ──
    double w1_x_;
    double w1_y_;
    double w2_x_;
    double w2_y_;

    // ── Initial pose ──
    double initial_x_;
    double initial_y_;
    double initial_yaw_;

    // ── IMU yaw offset (rad) ──
    // Models real-world misalignment between IMU's own yaw zero and map's yaw zero.
    // imu_published_yaw = ground_truth_yaw + imu_yaw_offset_rad_
    // → yaw_control's calibration: yaw_offset = wrap(start_yaw_map - start_yaw_imu) = -imu_yaw_offset_rad_
    // S7 SIL scenario uses non-zero value to verify offset calibration. Default 0 (legacy behavior).
    double imu_yaw_offset_rad_;

    // ── Integration state (atomic for callback safety) ──
    std::atomic<double> x_{0.0};
    std::atomic<double> y_{0.0};
    std::atomic<double> yaw_{0.0};

    // ── Latest cmd (mutex protected) ──
    std::mutex cmd_mtx_;
    double cmd_v0_{0.0}; // wheels[0] velocity (signed)
    double cmd_s0_{0.0}; // wheels[0] steering (rad)
    double cmd_v1_{0.0};
    double cmd_s1_{0.0};
    bool cmd_received_{false};

    // ── 구동·조향 동특성 (0 이면 제한 없음 = 종전 즉응 거동) ──
    // drive_decel: 실측 유래. 50 mm/s 에서 정지까지 0.57~0.65 s
    //   (docs/verified_facts/2026-08-04-amr-test-gui-field-run.md:80-88) → 0.050/0.6 ≈ 0.083 m/s².
    //   ⚠ 드라이브의 실제 0x6084(profile_dec)는 Seer 마스터가 설정한 값이고 우리가 쓰지 않아
    //     읽어 확인한 바 없다 — 이 값은 **한 동작점(50 mm/s)에서 역산**한 것이다.
    // steer_rate: 설정 유래. steer_profile_velocity 30000(=0.1 rpm 단위) → 모터 3000 rpm,
    //   조향 감속비 315 → 출력 9.524 rpm = 57.1 deg/s. **실측이 아니라 설정에서 유도**했다.
    double drive_accel_mps2_{0.0};
    double drive_decel_mps2_{0.0};
    double steer_rate_rad_s_{0.0};

    // ── 실제(동특성 적용 후) 상태 — 정기구학은 지령이 아니라 이 값으로 푼다 ──
    double act_v0_{0.0};
    double act_s0_{0.0};
    double act_v1_{0.0};
    double act_s1_{0.0};

    // ── 엔코더 — 휠 주행거리 누적(m) 과 counts 환산 상수 ──
    double travel0_m_{0.0};
    double travel1_m_{0.0};
    double wheel_radius_{0.125};
    double pulses_per_rev_{65536.0};
    double gear_walk_{32.0};
    double gear_steer_{315.0};

    // ── IMU yaw 잡음 (deg, 1σ). 기본 0 — 재현성을 위해 명시적으로 켤 때만 쓴다.
    //    고정 시드라 같은 설정이면 같은 수열이 나온다. ──
    double imu_yaw_noise_rad_{0.0};
    std::mt19937 noise_rng_{20260806u};
    std::normal_distribution<double> noise_dist_{0.0, 1.0};

    // ── Pubs/Subs ──
    rclcpp::Subscription<trnav_msgs::msg::WheelSetArray>::SharedPtr wheel_cmd_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr loc_pose_pub_;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_pub_;
    rclcpp::Publisher<trnav_msgs::msg::WheelMotor>::SharedPtr wheel_state_pub_;
    rclcpp::Publisher<trnav_msgs::msg::WheelMotorState>::SharedPtr wheel_state_detailed_pub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;

    // ── Timer ──
    rclcpp::TimerBase::SharedPtr integrate_timer_;
    double integrate_rate_hz_;
    rclcpp::Time last_integrate_time_;
    bool first_step_{true};
};

} // namespace translate_sim_odom

#endif // TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_
