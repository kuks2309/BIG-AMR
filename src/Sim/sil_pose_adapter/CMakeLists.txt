cmake_minimum_required(VERSION 3.8)
project(sil_pose_adapter)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(sil_pose_adapter_node
  src/sil_pose_adapter_node.cpp
)

ament_target_dependencies(sil_pose_adapter_node
  rclcpp
  geometry_msgs
)

install(TARGETS sil_pose_adapter_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
