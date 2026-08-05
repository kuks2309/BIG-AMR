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
#    live in `trnav_2ws_motion`. DD-specific in `trnav_motion_dd`. Kinematics (IK / bicycle
#    model) live in `trnav_2ws_kinematics` / `trnav_dd_kinematics` (src/Control/Kinematics/).
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
#   action_mutex.hpp, math_utils.hpp, recursive_moving_average.hpp, robot_geometry.hpp

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

ament_package()
