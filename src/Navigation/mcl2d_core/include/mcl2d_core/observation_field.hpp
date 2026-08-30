// Seer QuadGridSearchMap 2D 관측 우도 모델의 충실(bit-exact) 재구현.
//
// RE 제1원칙: 재구현 입출력 = 원본과 100% 동일. 본 모듈은 원본 libMCLoc.so 의
//   setCurrentLaserScan + getPostProbBase(mode=1) + 거리장/가우시안/삼각 LUT 생성을
//   디스어셈블·DWARF·gdb 동적추적으로 완전 해독해 **우리 코드가 자체 생성한 테이블만으로**
//   원본 getPostProb 을 자세 스윕 245/245 비트 일치(Δ=0)로 재현한다.
//   근거·계약: docs/adr/2026-07-12-obs-likelihood-faithful-port.md,
//             docs/verification/localization_oracle/HANDOFF-obs-oracle.md,
//   in-tree 검증: test/test_obs_field_oracle.cpp (원본 dlopen, Δ=0 게이트).
//
// 내부 프레임: 전부 밀리미터(mm). beam.angle=도(degree). 순수 C++17(std만).
#ifndef MCL2D_CORE_OBSERVATION_FIELD_HPP
#define MCL2D_CORE_OBSERVATION_FIELD_HPP

#include <cstdint>
#include <utility>
#include <vector>

namespace mcl2d
{

// 원본 rbk::algorithm::MeasurementPointInPolar2D 대응 (극좌표 빔).
struct PolarBeam
{
    double angle_deg = 0.0; // 빔 각도(도, 로봇좌표 기준)
    double dist_mm = 0.0;   // 거리(밀리미터)
    bool is_valid = false;  // 센서 유효 플래그
};

// 한 라이다의 스캔 + 장착 오프셋 (원본 rbk::algorithm::MeasurementVar2D 대응).
//   원본 setCurrentLaserScan 은 vector<MeasurementVar2D>(다중 라이다)를 받아 valid_beam 을 누적한다.
struct LaserScanGroup
{
    std::vector<PolarBeam> beams;
    double mount_lx_mm = 0.0; // 라이다 장착 x (로봇좌표, mm)
    double mount_ly_mm = 0.0; // 라이다 장착 y (로봇좌표, mm)
};

// 배포 파라미터 (robot.param MCLoc 실측값 기본).
struct ObsFieldParams
{
    int grid_size_mm = 10;          // GridSize (서브셀 크기, mm)
    int quad_resolution_mm = 500;   // QuadTreeResolution (quad 크기, mm)
    double gaussein = 10.0;         // GridMapGaussianDist (gauss 감쇠계수)
    double laser_closer_dist_m = 0.01; // LaserCloserDist (m)
    double laser_far_dist_m = 80.0;    // LaserFarDist (m)
    int search = 10;                // = GridRelocMapGaussianDist/GridSize = 100/10 (스탬프 반경, 서브셀)
    double region_margin_mm = 1000.0;  // 맵 영역 마진 (±1000mm)
};

// 2D 관측 우도장. 사용 순서: build(맵) → setScan(스캔) → getPostProb(자세) [자세별 반복].
class ObservationField
{
  public:
    ObservationField() = default;

    // 맵 장애물(미터) + 반사판/rssi(미터)로 거리장·가우시안·삼각 LUT·마크 quad 구축.
    //   obstacles_m: Message_Map.normal_pos_list (미터), reflectors_m: rssi_pos_list (미터).
    void build(const std::vector<std::pair<double, double>> &obstacles_m,
               const std::vector<std::pair<double, double>> &reflectors_m, const ObsFieldParams &p = {});

    // 스캔 전처리(원본 setCurrentLaserScan): 다중 라이다 그룹별 weight_table + 총 valid_beam 계산.
    //   유효 = is_valid && closer*1000 < (int)dist_mm < far*1000 && 0<=idx<36000.
    //   (원본 grid_ignore=-1 → 로컬셀 dedup 무발화 → 단순 게이트로 비트 일치.)
    void setScan(std::vector<LaserScanGroup> groups);
    // 단일 라이다 편의 오버로드 (mount=0 그룹 1개로 래핑).
    void setScan(std::vector<PolarBeam> beams);

    // 관측 우도(원본 getPostProb, mode=1). pose 는 mm 프레임, theta 는 라디안.
    //   저장된 전 라이다 그룹의 기여를 합산 후 총 valid_beam 으로 정규화. valid_beam==0 이면 1e-6.
    double getPostProb(double px_mm, double py_mm, double ptheta_rad) const;

    int validBeam() const
    {
        return valid_beam_;
    }
    bool empty() const
    {
        return fld_.empty();
    }
    // 월드좌표(mm)의 거리장 바이트 (테스트·진단용). <0 = 스킵(미마크 quad/경계/서브셀밖).
    int distByte(double wx_mm, double wy_mm) const;

  private:
    // 점(mm) → 스탬프 전역셀 = floor(coord/grid_size) [double].
    long stampCell(double coord_mm) const;

    // 파라미터
    int grid_size_ = 10;            // 서브셀 크기(mm)
    int quad_resolution_mm_ = 500;  // quad 크기(mm)
    int subcells_per_quad_ = 50;    // = quad_resolution_mm_ / grid_size_
    double gaussein_ = 10.0;
    double closer_mm_ = 10.0;
    double far_mm_ = 80000.0;
    int search_ = 10;

    // 생성 테이블
    std::vector<std::uint8_t> gauss_; // [25501] = (uint8)(255*exp(-i/gaussein^2))
    std::vector<float> sin_, cos_;    // [36000] = sinf/cosf((float)Deg2Rad(i/100-180))
    std::vector<std::uint8_t> fld_;   // 전역 서브셀 거리장(dx^2+dy^2, 초기 255)
    long minx_ = 0, miny_ = 0, W_ = 0, H_ = 0;

    // 마크 quad (원본 quad_map_vec_[]!=-1 대응)
    std::vector<std::uint8_t> marked_; // qwidth_*qheight_
    int qminx_ = 0, qminy_ = 0, qwidth_ = 0, qheight_ = 0;

    // 스캔 상태 (다중 라이다 그룹)
    std::vector<LaserScanGroup> groups_;
    std::vector<std::vector<std::uint8_t>> wtab_; // 그룹별·빔별 가중(0/1)
    int valid_beam_ = 0;                          // 전 그룹 총합
};

} // namespace mcl2d

#endif // MCL2D_CORE_OBSERVATION_FIELD_HPP
