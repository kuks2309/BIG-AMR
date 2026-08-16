cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_action_server)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ── Dependencies ──
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(trnav_2ws_interfaces REQUIRED)
find_package(trnav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(trnav_2ws_core REQUIRED)
find_package(trnav_2ws_motion REQUIRED)
find_package(trnav_2ws_kinematics REQUIRED)
# 라인 추종이 소비하는 인식 오차 메시지(ai_msgs/LineError). 인터페이스 패키지만 의존하며
# 런타임 AI 노드(torch·ultralytics)에는 의존하지 않는다.
find_package(ai_msgs REQUIRED)

# ── Spin pilot node ──
add_executable(amr_spin_node
  src/spin/spin_main.cpp
  src/spin/spin_action_server.cpp
)

target_include_directories(amr_spin_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_spin_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  tf2
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_spin_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
)

# ── Translate Forward pilot node (BICYCLE 고정, forward direction only) ──
add_executable(amr_translate_forward_node
  src/translate_forward/translate_forward_main.cpp
  src/translate_forward/translate_forward_action_server.cpp
)

target_include_directories(amr_translate_forward_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_translate_forward_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_translate_forward_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_motion::qd_path_controller
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── Translate Reverse pilot node (BICYCLE 고정, reverse direction) ──
add_executable(amr_translate_reverse_node
  src/translate_reverse/translate_reverse_main.cpp
  src/translate_reverse/translate_reverse_action_server.cpp
)

target_include_directories(amr_translate_reverse_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_translate_reverse_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_translate_reverse_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_motion::qd_path_controller
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── CrabLinear pilot node (target_yaw 능동 유지 + start↔end 직선 closed-loop 추종, 2026-05-21) ──
#   기존 crab (open-loop integration) 폐기, 동일 source_id=4 슬롯 재사용.
add_executable(amr_crab_linear_node
  src/crab_linear/crab_linear_main.cpp
  src/crab_linear/crab_linear_action_server.cpp
)

target_include_directories(amr_crab_linear_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_crab_linear_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_crab_linear_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_kinematics::qd_crab_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_motion::qd_path_controller
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── Turn pilot node (R-turn arc motion, T-Robot ROS2 원본 그대로 이식 2026-04-28) ──
add_executable(amr_turn_node
  src/turn/turn_main.cpp
  src/turn/turn_action_server.cpp
)

target_include_directories(amr_turn_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_turn_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  tf2
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_turn_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
)

# ── TurnReverse pilot node (후진 원호, 2026-08-09 신설) ──
#    전진판 amr_turn_node 와 IK 입력 vx 부호 · feedback 선속도의 크기(|vx|) 보고 · source_id 기본값(12) 만 다르다. ADR: docs/adr/2026-08-09-turn-reverse.md
add_executable(amr_turn_reverse_node
  src/turn_reverse/turn_reverse_main.cpp
  src/turn_reverse/turn_reverse_action_server.cpp
)

target_include_directories(amr_turn_reverse_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_turn_reverse_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  tf2
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_turn_reverse_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
)

# ── YawControl pilot node (ROS1 개념 + bicycle + 거리 종료, 신규 설계 2026-04-28) ──
add_executable(amr_yaw_control_node
  src/yaw_control/yaw_control_main.cpp
  src/yaw_control/yaw_control_action_server.cpp
)

target_include_directories(amr_yaw_control_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_yaw_control_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_yaw_control_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── MPC pilot node (nav_msgs/Path 다중 waypoint, kinematic bicycle NLopt SLSQP, 2026-05-28) ──
add_executable(amr_mpc_node
  src/mpc/mpc_main.cpp
  src/mpc/mpc_action_server.cpp
)

target_include_directories(amr_mpc_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_mpc_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_mpc_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_motion::qd_mpc_controller
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── YawControlReverse pilot node (yaw_control 의 reverse 분리, 2026-04-28) ──
#   vx_max magnitude(>0) + 내부 부호 반전. effective_yaw 보정 미적용.
add_executable(amr_yaw_control_reverse_node
  src/yaw_control_reverse/yaw_control_reverse_main.cpp
  src/yaw_control_reverse/yaw_control_reverse_action_server.cpp
)

target_include_directories(amr_yaw_control_reverse_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_yaw_control_reverse_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_yaw_control_reverse_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── MPC Reverse pilot node (2026-05-28) ──
#   effective_yaw = robot_yaw + π 보정 → MpcController 사용
#   wheel 출력 × -1. translate_reverse 패턴 준용. mux source_id=9.
add_executable(amr_mpc_reverse_node
  src/mpc_reverse/mpc_reverse_main.cpp
  src/mpc_reverse/mpc_reverse_action_server.cpp
)

target_include_directories(amr_mpc_reverse_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_mpc_reverse_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_mpc_reverse_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_motion::qd_mpc_controller
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── LineFollow pilot node (영상 라인 추종, mux source 13) ──
#    /line/error (ai_msgs/LineError) 를 소비해 조향 PD 로 라인을 추종한다.
#    ADR: docs/adr/2026-08-14-line-follow-2ws-action.md
add_executable(amr_line_follow_node
  src/line_follow/line_follow_main.cpp
  src/line_follow/line_follow_action_server.cpp
)

target_include_directories(amr_line_follow_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(amr_line_follow_node
  rclcpp
  rclcpp_action
  trnav_2ws_interfaces
  trnav_msgs
  ai_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  trnav_2ws_core
  trnav_2ws_motion
)

target_link_libraries(amr_line_follow_node
  trnav_2ws_kinematics::qd_inverse_kinematics
  trnav_2ws_kinematics::qd_crab_inverse_kinematics
  trnav_2ws_core::motion_profile
  trnav_2ws_motion::qd_wheel_set_packer
  trnav_2ws_kinematics::qd_bicycle_model
  trnav_2ws_core::transient_guard
  trnav_2ws_core::localization_monitor
)

# ── Tests ──
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  # 제어 코어는 ROS 비의존 헤더 온리라 링크 없이 헤더 경로만 준다.
  ament_add_gtest(line_follow_core_test test/line_follow_core_test.cpp)
  if(TARGET line_follow_core_test)
    target_include_directories(line_follow_core_test PRIVATE
      ${CMAKE_CURRENT_SOURCE_DIR}/include)
    # 코어가 진행 방향을 인자로 받지 않는 근거는 IK 쪽 기하다 — 그 계약을 같은 시험에서 건다.
    target_link_libraries(line_follow_core_test
      trnav_2ws_kinematics::qd_crab_inverse_kinematics)
  endif()
endif()

# ── Install ──
install(TARGETS
  amr_spin_node
  amr_translate_forward_node
  amr_translate_reverse_node
  amr_crab_linear_node
  amr_turn_node
  amr_turn_reverse_node
  amr_yaw_control_node
  amr_yaw_control_reverse_node
  amr_mpc_node
  amr_mpc_reverse_node
  amr_line_follow_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()
