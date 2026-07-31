cmake_minimum_required(VERSION 3.10)
project(mcl2d_non_ros CXX)

# non-ROS 위치추정 어댑터 — mcl2d_core(../mcl2d_core) 위에 ROS 없이 동작.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

set(CORE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../src/Navigation/mcl2d_core)

add_library(mcl2d_localizer
  src/mcl2d_localizer.cpp
  ${CORE_DIR}/src/likelihood_grid.cpp
  ${CORE_DIR}/src/motion_model.cpp
  ${CORE_DIR}/src/observation_model.cpp
  ${CORE_DIR}/src/observation_field.cpp
  ${CORE_DIR}/src/skid_detector.cpp
  ${CORE_DIR}/src/particle_filter.cpp)
target_include_directories(mcl2d_localizer PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CORE_DIR}/include)

add_executable(mcl2d_non_ros_demo main.cpp)
target_link_libraries(mcl2d_non_ros_demo PRIVATE mcl2d_localizer)

enable_testing()
add_test(NAME non_ros_demo COMMAND mcl2d_non_ros_demo)
