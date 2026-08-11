cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_core)

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
find_package(trnav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)

# ── Platform-agnostic primitives only.
#    QD-specific controllers (path controller, mpc, wheel set packer, TwoWsActionServerBase)
#    live in `trnav_2ws_motion`. DD-specific in `trnav_motion_dd` (not present in this
#    repository). Kinematics (IK / bicycle model) live in `trnav_2ws_kinematics`
#    (src/Control/Motion_Control/2WS/).
#    See ADR-012 (2026-05-21) + amendment (2026-07-04) for the separation rationale. ──

# ── Motion Profile (no ROS dep) ──
add_library(motion_profile STATIC
  src/motion_profile.cpp
)
target_include_directories(motion_profile PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
set_target_properties(motion_profile PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Transient Guard (no ROS dep) ──
add_library(transient_guard STATIC
  src/transient_guard.cpp
)
target_include_directories(transient_guard PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
set_target_properties(transient_guard PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Localization Monitor (rclcpp + geometry_msgs + tf2 + tf2_ros) ──
add_library(localization_monitor STATIC
  src/localization_monitor.cpp
)
target_include_directories(localization_monitor PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(localization_monitor
  rclcpp
  geometry_msgs
  tf2
  tf2_ros
)
set_target_properties(localization_monitor PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Header-only utilities (no add_library — installed via install(DIRECTORY include/)):
#   action_mutex.hpp, math_utils.hpp, recursive_moving_average.hpp, robot_geometry.hpp,
#   velocity_ramp.hpp

# ── Install ──
install(TARGETS
  motion_profile
  transient_guard
  localization_monitor
  EXPORT trnav_2ws_core_targets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Export for downstream packages (trnav_2ws_motion, trnav_motion_dd, trnav_2ws_action_server, ...)
ament_export_targets(trnav_2ws_core_targets HAS_LIBRARY_TARGET)
ament_export_dependencies(
  rclcpp
  rclcpp_action
  trnav_msgs
  sensor_msgs
  std_msgs
  geometry_msgs
  tf2
  tf2_ros
)

# ── 시험 (2WS 스택 최초) ────────────────────────────────────────────────
# `TransientGuard` 는 순수 클래스라 리팩터 없이 고정할 수 있다. `yaw_control` 의
# 조향 미도달 감시(status −8)가 이 클래스의 `gate_blocked` 위에 서 있으므로,
# 게이트 판정이 조용히 바뀌면 그 가드가 발화하지 않거나 정상 주행을 막는다.
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_transient_guard test/test_transient_guard.cpp)
  target_link_libraries(test_transient_guard transient_guard)
  ament_add_gtest(test_motion_profile test/test_motion_profile.cpp)
  target_link_libraries(test_motion_profile motion_profile)
  # 헤더 전용 자산(robot_geometry · recursive_moving_average · action_mutex) — 링크 대상 없음
  ament_add_gtest(test_core_utils test/test_core_utils.cpp)
  target_include_directories(test_core_utils PRIVATE include)
  # velocity_ramp 도 헤더 전용 — 7개 액션 서버가 복제해 쓰던 램프를 하나로 모은 것
  ament_add_gtest(test_velocity_ramp test/test_velocity_ramp.cpp)
  target_include_directories(test_velocity_ramp PRIVATE include)
endif()

ament_package()
