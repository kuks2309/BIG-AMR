cmake_minimum_required(VERSION 3.5)
project(lidar_calibration_2d)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2_eigen REQUIRED)
find_package(message_filters REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(Eigen3 REQUIRED)

include_directories(
  include
)

add_executable(lidar_calibration_2d_node src/calibration_node.cpp)
target_include_directories(lidar_calibration_2d_node PUBLIC
  ${EIGEN3_INCLUDE_DIR}
)
ament_target_dependencies(lidar_calibration_2d_node
  rclcpp
  sensor_msgs
  geometry_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
  tf2_eigen
  message_filters
  ament_index_cpp
)
target_link_libraries(lidar_calibration_2d_node Eigen3::Eigen)

add_executable(lidar_tf_publisher src/tf_publisher_node.cpp)
ament_target_dependencies(lidar_tf_publisher
  rclcpp
  geometry_msgs
  tf2
  tf2_ros
)

install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY
  ui
  DESTINATION share/${PROJECT_NAME}
)

install(TARGETS
  lidar_calibration_2d_node
  lidar_tf_publisher
  DESTINATION lib/${PROJECT_NAME})

# Python UI scripts
install(PROGRAMS
  scripts/calibration_ui_main.py
  scripts/calibration_ui_window.py
  scripts/calibration_engine.py
  scripts/scan_canvas.py
  scripts/ros_scan_bridge.py
  scripts/icp_algorithm.py
  scripts/region_manager.py
  scripts/tf_calculator.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # uncomment the line when a copyright and license is not present in all source files
  #set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # uncomment the line when this package is not in a git repo
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
