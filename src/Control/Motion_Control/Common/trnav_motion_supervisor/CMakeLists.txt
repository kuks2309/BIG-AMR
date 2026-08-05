cmake_minimum_required(VERSION 3.8)
project(trnav_motion_supervisor)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(trnav_msgs REQUIRED)

add_executable(trnav_motion_supervisor_node src/trnav_motion_supervisor_node.cpp)
ament_target_dependencies(trnav_motion_supervisor_node rclcpp trnav_msgs)

install(TARGETS trnav_motion_supervisor_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME})

ament_package()
