cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch worlds config
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/wheel_cmd_bridge.py
    scripts/wheel_odometry.py
    scripts/teleop_gui.py
    scripts/stop_sim.sh
    scripts/run_gui.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
