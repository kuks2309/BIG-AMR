cmake_minimum_required(VERSION 3.8)
project(amr_motor_cmd_translator)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(trnav_msgs REQUIRED)

include_directories(include)

add_executable(amr_motor_cmd_translator_node
  src/main.cpp
  src/amr_motor_cmd_translator_node.cpp
)

ament_target_dependencies(amr_motor_cmd_translator_node
  rclcpp
  trnav_msgs
)

install(TARGETS amr_motor_cmd_translator_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY config
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()
