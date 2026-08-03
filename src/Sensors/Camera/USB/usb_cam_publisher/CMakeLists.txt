cmake_minimum_required(VERSION 3.8)
project(usb_cam_publisher)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
find_package(OpenCV REQUIRED)

add_executable(usb_cam_publisher_node src/usb_cam_publisher_node.cpp)
target_include_directories(usb_cam_publisher_node PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  ${OpenCV_INCLUDE_DIRS})
ament_target_dependencies(usb_cam_publisher_node
  rclcpp sensor_msgs std_msgs cv_bridge image_transport)
target_link_libraries(usb_cam_publisher_node ${OpenCV_LIBS})

install(TARGETS usb_cam_publisher_node
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_pixel_format test/test_pixel_format.cpp)
  target_include_directories(test_pixel_format PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include ${OpenCV_INCLUDE_DIRS})
  target_link_libraries(test_pixel_format ${OpenCV_LIBS})
endif()

ament_package()
