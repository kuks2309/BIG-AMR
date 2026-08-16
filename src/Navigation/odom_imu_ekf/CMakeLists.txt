cmake_minimum_required(VERSION 3.10)
project(odom_imu_ekf)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
# ament 기본 빌드타입은 비어 있어 최적화가 붙지 않는다. 융합은 센서 주기마다 도는 핫패스라
#   형제 패키지(mcl2d_core·mcl2d_ros2)와 같이 기본을 Release 로 둔다.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(diagnostic_msgs REQUIRED)

# 코어는 ROS 무의존 — 시계·미들웨어 없이 시험할 수 있어야 한다.
add_library(odom_imu_ekf_core src/ekf.cpp)
target_include_directories(odom_imu_ekf_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

add_executable(odom_imu_ekf_node src/odom_imu_ekf_node.cpp)
target_link_libraries(odom_imu_ekf_node odom_imu_ekf_core)
ament_target_dependencies(odom_imu_ekf_node rclcpp nav_msgs sensor_msgs diagnostic_msgs)

install(TARGETS odom_imu_ekf_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  # 코어 회귀 — ROS 없이 돌아가므로 상시 ctest 대상.
  add_executable(test_ekf test/test_ekf.cpp)
  target_link_libraries(test_ekf odom_imu_ekf_core)
  add_test(NAME test_ekf COMMAND test_ekf)
endif()

ament_package()
