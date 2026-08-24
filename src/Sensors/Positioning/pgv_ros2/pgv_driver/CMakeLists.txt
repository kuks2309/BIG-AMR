cmake_minimum_required(VERSION 3.8)
project(pgv_driver)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(pgv_interfaces REQUIRED)

# 프로토콜 인코딩/파싱 — ROS 무의존 순수 라이브러리 (단위 테스트 대상)
add_library(pgv_protocol src/pgv_protocol.cpp)
target_include_directories(pgv_protocol PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

add_executable(pgv_driver_node src/pgv_driver_node.cpp)
target_link_libraries(pgv_driver_node pgv_protocol)
ament_target_dependencies(pgv_driver_node rclcpp std_msgs pgv_interfaces)

install(TARGETS pgv_protocol pgv_driver_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_pgv_protocol test/test_pgv_protocol.cpp)
  target_link_libraries(test_pgv_protocol pgv_protocol)
endif()

ament_package()
