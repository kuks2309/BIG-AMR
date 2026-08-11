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
    scripts/fleet_wheel_bridge.py
    scripts/wheel_odometry.py
    scripts/teleop_gui.py
    scripts/show_roads.py
    scripts/generate_world.py
    scripts/generate_cad_world.py
    scripts/audit_cad_world.py
    scripts/stop_sim.sh
    scripts/run_gui.sh
    scripts/start_sim.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
