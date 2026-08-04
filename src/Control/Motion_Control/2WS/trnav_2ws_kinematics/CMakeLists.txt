cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_kinematics)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ── Dependencies ──
find_package(ament_cmake REQUIRED)

# ── Inverse Kinematics (pure math, stdlib only) ──
add_library(qd_inverse_kinematics STATIC
  src/qd_inverse_kinematics.cpp
)
target_include_directories(qd_inverse_kinematics PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
set_target_properties(qd_inverse_kinematics PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Crab IK (CRAB linear 전용 — DualSteerIK 의 ±90° normalize edge 회피) ──
add_library(qd_crab_inverse_kinematics STATIC
  src/qd_crab_inverse_kinematics.cpp
)
target_include_directories(qd_crab_inverse_kinematics PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(qd_crab_inverse_kinematics qd_inverse_kinematics)
set_target_properties(qd_crab_inverse_kinematics PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Bicycle Model (depends on QD IK) ──
add_library(qd_bicycle_model STATIC
  src/qd_bicycle_model.cpp
)
target_include_directories(qd_bicycle_model PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(qd_bicycle_model qd_inverse_kinematics)
set_target_properties(qd_bicycle_model PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ── Install ──
install(TARGETS
  qd_inverse_kinematics
  qd_crab_inverse_kinematics
  qd_bicycle_model
  EXPORT trnav_2ws_kinematics_targets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include
)

# Export for downstream packages (trnav_2ws_motion, trnav_2ws_action_server, amr_dock_align, ...)
ament_export_targets(trnav_2ws_kinematics_targets HAS_LIBRARY_TARGET)

ament_package()
