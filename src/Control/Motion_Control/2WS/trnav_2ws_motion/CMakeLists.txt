cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_motion)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ── Dependencies ──
find_package(ament_cmake REQUIRED)
find_package(trnav_2ws_kinematics REQUIRED)
find_package(trnav_2ws_core REQUIRED)
find_package(trnav_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)

# ── Kinematics (IK / Crab IK / Bicycle Model) ──
#    trnav_2ws_kinematics (src/Control/Kinematics/) 로 이동 — AD-012 개정 2026-07-04.
#    qd_action_server_base.hpp 가 trnav_2ws_kinematics/qd_inverse_kinematics.hpp include.

# ── Path Controller (BICYCLE mode only; Wave 2)
#    Depends on header-only math_utils + recursive_moving_average from trnav_2ws_core. ──
add_library(qd_path_controller STATIC
  src/qd_path_controller.cpp
)
target_include_directories(qd_path_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(qd_path_controller
  trnav_2ws_core
)
set_target_properties(qd_path_controller PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Wheel-Set Packer (depends on trnav_msgs) ──
add_library(qd_wheel_set_packer STATIC
  src/qd_wheel_set_packer.cpp
)
target_include_directories(qd_wheel_set_packer PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(qd_wheel_set_packer
  trnav_msgs
  trnav_2ws_core
)
set_target_properties(qd_wheel_set_packer PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Kinematic MPC controller (NLopt SLSQP, bicycle delta_f 출력) ──
find_library(NLOPT_LIB nlopt REQUIRED)
add_library(qd_mpc_controller STATIC
  src/qd_mpc_controller.cpp
)
target_include_directories(qd_mpc_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(qd_mpc_controller ${NLOPT_LIB})
ament_target_dependencies(qd_mpc_controller
  trnav_2ws_core
)
set_target_properties(qd_mpc_controller PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Install ──
install(TARGETS
  qd_path_controller
  qd_mpc_controller
  qd_wheel_set_packer
  EXPORT trnav_2ws_motion_targets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include
)

# Export for downstream packages
ament_export_targets(trnav_2ws_motion_targets HAS_LIBRARY_TARGET)
ament_export_dependencies(
  trnav_2ws_kinematics
  trnav_2ws_core
  trnav_msgs
  rclcpp
  geometry_msgs
  sensor_msgs
  std_msgs
)

ament_package()
