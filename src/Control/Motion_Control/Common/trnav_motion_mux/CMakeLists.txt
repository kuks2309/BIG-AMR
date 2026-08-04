cmake_minimum_required(VERSION 3.8)
project(trnav_motion_mux)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(trnav_msgs REQUIRED)

add_executable(trnav_motion_mux_node src/trnav_motion_mux_node.cpp)
target_include_directories(trnav_motion_mux_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(trnav_motion_mux_node rclcpp trnav_msgs)

install(TARGETS trnav_motion_mux_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include/${PROJECT_NAME})
install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  # Config schema validation tests (standalone pytest, not launch_testing)
  ament_add_pytest_test(test_validation_v1_v5
    test/test_validation_v1_v5.py
    TIMEOUT 120
  )
  ament_add_pytest_test(test_validation_v6_v10
    test/test_validation_v6_v10.py
    TIMEOUT 120
  )

  # test fixtures — conftest.py 가 ament_index 경유로 접근
  install(DIRECTORY test/fixtures/ DESTINATION share/${PROJECT_NAME}/test/fixtures)
endif()

ament_package()
