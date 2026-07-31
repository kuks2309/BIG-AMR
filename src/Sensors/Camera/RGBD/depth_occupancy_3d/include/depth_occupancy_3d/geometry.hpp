// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// surround depth 점유맵의 순수 기하 연산. **ROS 의존이 없다** — 단위 시험이 하드웨어도
// 미들웨어도 없이 돌게 하려는 의도다(test/test_geometry.cpp).
//
// 좌표계
//   - 카메라 광학 좌표계: REP-103 규약 +x 우 / +y 하 / +z 전방
//   - 차체 좌표계(base_link): +x 전방 / +y 좌측 / +z 상방
//   두 좌표계 사이 변환은 TF 가 담당하므로 이 헤더는 다루지 않는다.

#ifndef DEPTH_OCCUPANCY_3D__GEOMETRY_HPP_
#define DEPTH_OCCUPANCY_3D__GEOMETRY_HPP_

#include <cmath>
#include <cstddef>
#include <cstdint>

namespace depth_occupancy_3d
{

/// 핀홀 카메라 내부 파라미터. sensor_msgs/CameraInfo 의 K 행렬에서 뽑는다.
struct PinholeIntrinsics
{
  double fx{0.0};
  double fy{0.0};
  double cx{0.0};
  double cy{0.0};

  /// 역투영에 쓸 수 있는 값인지. 초점거리가 0 이면 0 나눗셈이 된다.
  bool isUsable() const { return fx > 0.0 && fy > 0.0; }
};

/// 3차원 점 (단위 m).
struct Point3
{
  double x{0.0};
  double y{0.0};
  double z{0.0};
};

/// 3차원 보셀 격자의 범위·해상도. 전 구간 base_link 기준(단위 m).
struct GridSpec
{
  double min_x{-3.0};
  double max_x{3.0};
  double min_y{-3.0};
  double max_y{3.0};
  double min_z{0.0};
  double max_z{2.0};
  double resolution{0.05};

  std::size_t sizeX() const { return spanCells(min_x, max_x); }
  std::size_t sizeY() const { return spanCells(min_y, max_y); }
  std::size_t sizeZ() const { return spanCells(min_z, max_z); }

  /// 격자 전체 셀 수. 노드는 이 크기로 버퍼를 **한 번만** 잡고 매 주기 재사용한다
  /// (유입률과 무관하게 메모리 상한이 고정돼야 한다 — vision_guard 가 유계화 없는 큐로
  ///  RSS 11 GB 까지 자란 선례: docs/issues_and_fixes/issues_and_fixes.md:279).
  std::size_t cellCount() const { return sizeX() * sizeY() * sizeZ(); }

  /// 격자 범위·해상도가 쓸 수 있는 값인지.
  bool isUsable() const
  {
    return resolution > 0.0 && max_x > min_x && max_y > min_y && max_z > min_z;
  }

private:
  std::size_t spanCells(double lo, double hi) const
  {
    if (resolution <= 0.0 || hi <= lo) {
      return 0;
    }
    return static_cast<std::size_t>(std::ceil((hi - lo) / resolution));
  }
};

/// 차체 풋프린트(자기 자신) 판정에 쓰는 반치수. 단위 m.
struct FootprintHalfExtent
{
  double half_length{0.0};  ///< x 방향 반치수
  double half_width{0.0};   ///< y 방향 반치수
};

/// 깊이 픽셀을 카메라 광학 좌표계의 점으로 역투영한다.
///
/// \param u 픽셀 열 좌표
/// \param v 픽셀 행 좌표
/// \param depth_m 그 픽셀의 깊이(m)
/// \param intrinsics 핀홀 내부 파라미터
/// \return 광학 좌표계 점. intrinsics 가 못 쓸 값이면 원점을 돌려준다(호출부가 isUsable 로 선판정).
inline Point3 backProject(
  double u, double v, double depth_m, const PinholeIntrinsics & intrinsics)
{
  if (!intrinsics.isUsable()) {
    return Point3{};
  }
  return Point3{
    (u - intrinsics.cx) * depth_m / intrinsics.fx,
    (v - intrinsics.cy) * depth_m / intrinsics.fy,
    depth_m};
}

/// 차체 풋프린트 안쪽인지 판정한다.
///
/// z 를 보지 않는 무한 기둥 마스크다 — 차체 높이를 모르는 상태에서 기둥으로 두면 풋프린트
/// 안쪽 점이 전부 자기 차체로 걸러진다. 장애물을 자기 몸으로 오인하는 쪽이 아니라 자기 몸을
/// 장애물로 오인하지 않는 쪽으로 틀리므로 오차 방향이 안전하다.
inline bool isInsideFootprint(double x, double y, const FootprintHalfExtent & footprint)
{
  return std::abs(x) <= footprint.half_length && std::abs(y) <= footprint.half_width;
}

/// 점이 격자 범위 안이면 선형 보셀 인덱스를 계산한다.
///
/// \param[out] index 격자 범위 안일 때만 기록된다.
/// \return 범위 안이면 true.
inline bool voxelIndex(const GridSpec & grid, const Point3 & point, std::size_t & index)
{
  if (!grid.isUsable()) {
    return false;
  }
  if (point.x < grid.min_x || point.x >= grid.max_x ||
      point.y < grid.min_y || point.y >= grid.max_y ||
      point.z < grid.min_z || point.z >= grid.max_z)
  {
    return false;
  }
  const auto ix = static_cast<std::size_t>((point.x - grid.min_x) / grid.resolution);
  const auto iy = static_cast<std::size_t>((point.y - grid.min_y) / grid.resolution);
  const auto iz = static_cast<std::size_t>((point.z - grid.min_z) / grid.resolution);
  index = (iz * grid.sizeY() + iy) * grid.sizeX() + ix;
  return index < grid.cellCount();
}

/// 선형 보셀 인덱스를 그 보셀 중심의 좌표로 되돌린다(발행용).
inline Point3 voxelCenter(const GridSpec & grid, std::size_t index)
{
  const std::size_t nx = grid.sizeX();
  const std::size_t ny = grid.sizeY();
  const std::size_t ix = index % nx;
  const std::size_t iy = (index / nx) % ny;
  const std::size_t iz = index / (nx * ny);
  const double half = grid.resolution * 0.5;
  return Point3{
    grid.min_x + static_cast<double>(ix) * grid.resolution + half,
    grid.min_y + static_cast<double>(iy) * grid.resolution + half,
    grid.min_z + static_cast<double>(iz) * grid.resolution + half};
}

/// 360° 가상 스캔의 각도 구간. sensor_msgs/LaserScan 규약을 그대로 따른다.
struct ScanSpec
{
  double angle_min{-M_PI};
  double angle_max{M_PI};
  std::size_t bin_count{360};

  double angleIncrement() const
  {
    return bin_count > 0 ? (angle_max - angle_min) / static_cast<double>(bin_count) : 0.0;
  }
};

/// 점의 방위각이 속한 스캔 빈 인덱스를 구한다.
///
/// \param[out] bin 범위 안일 때만 기록된다.
/// \return 유효한 빈이면 true. 원점(x=y=0)은 방위각이 정의되지 않아 false.
inline bool azimuthBin(const ScanSpec & scan, double x, double y, std::size_t & bin)
{
  if (scan.bin_count == 0 || (x == 0.0 && y == 0.0)) {
    return false;
  }
  const double increment = scan.angleIncrement();
  if (increment <= 0.0) {
    return false;
  }
  const double angle = std::atan2(y, x);
  const auto raw = static_cast<long long>(std::floor((angle - scan.angle_min) / increment));
  if (raw < 0 || static_cast<std::size_t>(raw) >= scan.bin_count) {
    return false;
  }
  bin = static_cast<std::size_t>(raw);
  return true;
}

/// 수평 거리(방위각 평면상 거리). 가상 스캔의 range 값이다.
inline double horizontalRange(double x, double y) { return std::hypot(x, y); }

}  // namespace depth_occupancy_3d

#endif  // DEPTH_OCCUPANCY_3D__GEOMETRY_HPP_
