cmake_minimum_required(VERSION 3.10)
project(feature_localizer_ros2)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
# ament 기본 빌드타입은 비어 있어 -O0 이 된다 — 형제 mcl2d_ros2 와 동일하게 Release 기본.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(diagnostic_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(visualization_msgs REQUIRED)

# 프레임워크-독립 코어 (형제 디렉터리, ROS 의존 0) — 소스를 직접 컴파일 (mcl2d 관례).
set(CORE ${CMAKE_CURRENT_SOURCE_DIR}/../feature_localizer_core)
add_library(feature_localizer_core_lib STATIC
  ${CORE}/src/line_extractor.cpp
  ${CORE}/src/feature_matcher.cpp
  ${CORE}/src/pose_solver.cpp
  ${CORE}/src/feature_localizer.cpp)
target_include_directories(feature_localizer_core_lib PUBLIC ${CORE}/include)

add_executable(feature_localizer_node src/feature_localizer_node.cpp)
target_link_libraries(feature_localizer_node feature_localizer_core_lib)
ament_target_dependencies(feature_localizer_node
  rclcpp sensor_msgs geometry_msgs diagnostic_msgs tf2 tf2_ros visualization_msgs)

install(TARGETS feature_localizer_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

ament_package()
