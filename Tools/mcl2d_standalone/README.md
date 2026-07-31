> **위치 주석(2026-07-28)**: 본 폴더는 Big-AMR 규약상 비-ROS2 도구로 `Tools/` 에 배치됨. 코어는 `src/Navigation/mcl2d_core`, ROS2 노드는 `src/Navigation/mcl2d_ros2`(본 폴더의 mcl2d_localizer.cpp 파사드를 공유 컴파일). 원본: amap-1 Seer_Analysis non-ros-src.

# mcl2d non-ROS 어댑터

`src/mcl2d_core`(2D 레이저 파티클필터 위치추정)를 **ROS 없이** 직접 쓰는 비-ROS 어댑터.
Seer 원본도 비-ROS(자체 ZeroMQ+protobuf 미들웨어)이므로, 본 어댑터는 **어떤 전송계층에도 묶이지 않는 순수 호출 인터페이스**(`Mcl2dLocalizer`)를 제공한다. 파일·소켓·ZeroMQ 등 전송은 호출측이 선택.

## 구성
- `include/mcl2d_localizer.hpp` · `src/mcl2d_localizer.cpp` — 파사드(`Mcl2dLocalizer`): loadMap → setLasers → setInitialPose → update(반복).
- `main.cpp` — standalone 데모 러너: **Roll_A084 듀얼 라이다**(전 @(0.879,−0.579,−45°) + 후 @(−0.879,0.579,135°)) 구성으로 합성 방에서 궤적 추종, ROS 없이 위치추정 수렴 입증.

## 빌드 / 실행
```bash
# 정상 cmake:
cmake -S . -B build && cmake --build build && ./build/mcl2d_non_ros_demo

# 현재 호스트는 시스템 cmake 손상(debt-011) → g++ 직접:
g++ -std=c++17 -O2 -Inon-ros-src/include -Isrc/mcl2d_core/include \
  non-ros-src/main.cpp non-ros-src/src/mcl2d_localizer.cpp src/mcl2d_core/src/*.cpp \
  -o demo && ./demo
```
검증(실측): 50스텝 듀얼 라이다 궤적 추종 → 최종 오차 ~6mm, 신뢰도 ~0.80, `[PASS]`.

## API 예시
```cpp
mcl2d::Mcl2dLocalizer loc(params);
loc.loadMap(obstacles);                 // 장애물 점군 → 우도장
loc.setLasers({front_mount, rear_mount}); // 듀얼 라이다
loc.setInitialPose({x, y, theta});
Pose2D est = loc.update(prev_odom, cur_odom, {front_scan, rear_scan});
double conf = loc.confidence();         // 0 이면 위치손실 가능
```

## 양형 관계
- 본 어댑터(non-ROS) ↔ (예정) `mcl2d_ros2`(rclcpp 노드) — 동일 `mcl2d_core` 공유.
- 근거/설계: [ADR](../docs/adr/2026-06-24-mcl2d-core.md), [코어 README](../src/mcl2d_core/README.md).
