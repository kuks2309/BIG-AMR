cmake_minimum_required(VERSION 3.8)
project(trnav_2ws_description)

find_package(ament_cmake REQUIRED)

# 존재하는 자원 디렉터리만 설치한다. 없는 디렉터리를 목록에 넣으면
#   `file INSTALL cannot find` 로 빌드가 통째로 죽고, 이 패키지에 의존하는
#   trnav_2ws_gazebo 까지 함께 막힌다. 목록에 미리 적어 둔 것은 만들어지는
#   시점부터 자동으로 설치된다.
foreach(resource_dir urdf launch rviz config)
  if(IS_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/${resource_dir})
    install(DIRECTORY ${resource_dir} DESTINATION share/${PROJECT_NAME})
  endif()
endforeach()

ament_package()
