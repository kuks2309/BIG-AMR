cmake_minimum_required(VERSION 3.10)
project(seer_lidar_tf CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
# Seer TCP 프로토콜은 여기서 재구현하지 않는다.
find_package(seer_tcp_ip REQUIRED)

add_executable(seer_lidar_tf_node src/seer_lidar_tf_node.cpp)
ament_target_dependencies(seer_lidar_tf_node rclcpp geometry_msgs tf2_ros seer_tcp_ip)

install(TARGETS seer_lidar_tf_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

ament_package()
