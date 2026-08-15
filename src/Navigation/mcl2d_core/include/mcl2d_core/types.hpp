// mcl2d_core — 2D MCL(Monte Carlo Localization) 파티클필터 핵심 자료구조.
// Seer libMCLoc.so 의 2D 레이저 파티클필터 모드를 리버스 엔지니어링으로 복원해 재구현.
// 근거: References/seer/libMCLoc/2026-06-24-localization-deep-dive.md
#ifndef MCL2D_CORE_TYPES_HPP
#define MCL2D_CORE_TYPES_HPP

#include <cstdint>
#include <vector>

namespace mcl2d
{

// 평면 자세 (Seer rbk::algorithm::StateVar2D 대응: x, y, heading)  comment-check: ignore
struct Pose2D
{
    double x = 0.0;     // m
    double y = 0.0;     // m
    double theta = 0.0; // rad
};

// 파티클 (Seer MCLParticle2D 대응). log_weight 는 본 재구현에서 미사용(선형 가중만).
struct Particle
{
    Pose2D pose;
    double weight = 0.0;
};

// 오도메트리 절대 자세(연속 두 시점). 모션모델이 증분을 계산한다.
struct OdomSample
{
    Pose2D pose;
    bool is_stop = false;
};

// 오도 증분을 로봇좌표로 분해한 제어변수 (Seer MCLMotionModel2D 멤버 0x98/0xa0/0x90 대응).
//   supplyControlVar() 가 채우고 doParticleMove() 가 소비한다.
struct ControlIncrement2D
{
    double trans = 0.0;     // m,   직전→현재 오도의 병진량
    double direction = 0.0; // rad, 이동 방향(직전 오도 헤딩 기준 상대각)
    double dtheta = 0.0;    // rad, 회전 증분(정규화됨)
};

// ExtraMove(산포) 크기 (Seer setExtraMoveParams 인자 2개 + 로그에 찍히는 모드 번호).
struct ExtraMoveParams
{
    double radius = 0.0; // m,   x·y 각각에 U(-0.5,+0.5) 로 곱해지는 반폭
    double angle = 0.0;  // rad, theta 에 U(-0.5,+0.5) 로 곱해지는 반폭
    int mode = 0;        // 1~5 (Seer MCLocUpdateMode 로그값). 진단용
};

// 로봇 기준 레이저 장착 자세 (robot.model laser.x/y/yaw 대응)
struct LaserMount
{
    double x = 0.0;   // m (전방+)
    double y = 0.0;   // m (좌측+)
    double yaw = 0.0; // rad
};

// 단일 2D 레이저 스캔 (극좌표 빔열)
struct LaserScan
{
    double angle_min = 0.0;       // rad, 첫 빔 각도
    double angle_increment = 0.0; // rad, 빔 간격
    double range_min = 0.0;       // m
    double range_max = 0.0;       // m
    std::vector<float> ranges;    // m, 무효는 0 또는 범위밖
};

// 보고용 위치추정 상태 (Seer Message_Localization_LocState 대응).
enum class LocReportState
{
    Normal = 0,
    Skidding = 1,
    LowConfidence = 2
};

// 내부 위치추정 방식 (Seer MCLoc::LocState 대응). 현재 재구현 = PF/Odo만.  comment-check: ignore
enum class LocMode
{
    PF = 0,
    Ref,
    Tag,
    Odo,
    SLAM,
    Correct,
    Laser3D,
    Tag3D,
    FT
};

// 파티클필터/모션/관측 파라미터. 기본값은 Seer robot.param 실측 배포값.
struct Mcl2dParams
{
    // 표본 수 (Seer: InitParticleNumber=10000, Min/Max=500/3000)
    int init_particle_number = 10000;
    int min_particle_number = 500;
    int max_particle_number = 3000;

    // 적응표본: n = (점유 (x,y,theta) bin 수) * sample_factor, clamp[min,max]
    // (Seer 실측: factor=2.5, 각도 bin=6deg, xy_step=AdaptiveSampleNumberXYStep)
    double adaptive_sample_factor = 2.5;
    double adaptive_angle_bin_deg = 6.0;
    double adaptive_xy_step = 0.1; // m

    // ExtraMove 산포 크기 후보. Seer: ParticleMoveRadius/ParticleExtraMoveRadius(mm), ParticleExtraMoveAngle(deg)
    //   원본은 예측(kMove)이 아니라 별도 액션 kExtraMove 에서만 산포한다 — selectExtraMove() 가 모드별로 고른다.
    double move_radius = 0.010;       // m  (ParticleMoveRadius 10mm)
    double extra_move_radius = 0.040; // m  (ParticleExtraMoveRadius 40mm)
    double extra_move_angle = 0.052;  // rad (ParticleExtraMoveAngle 3deg)

    // ExtraMove 모드 판정 임계. Seer MCLParams2D 실측 배포값(robot.param, 2026-07-31 조회).
    double extra_move_dist_threshold = 0.020;       // m  (ExtraMoveDistThreshold 20mm)
    double extra_move_angle_threshold = 0.0174533;  // rad (ExtraMoveAngleThreshold 1deg)
    double best_particle_tolerant_threshold = 0.8;  // 우도 이상이면 "신뢰 높음" 취급
    double low_speed_move_radius = 0.010;           // m  (lowSpeedMoveRadius 10mm)
    double low_speed_move_angle = 0.0174533;        // rad (lowSpeedMoveAngle 1deg)
    bool force_extra_move = false;                  // ForceExtraMove (배포 0)
    double motor_stop_threshold = 0.02;             // m/s·rad/s (MotorStopThreshold) — 이하이면 정지로 본다
    double force_extra_move_dist = 0.010;           // m  (ForceExtraMoveDist 10mm)
    double force_extra_move_angle = 0.0349066;      // rad (ForceExtraMoveAngle 2deg)

    // 초기 산포 (Seer: InitParticleDistScatter=700, AngleScatter=180)
    double init_dist_scatter = 0.7;     // m
    double init_angle_scatter = 3.1416; // rad

    // 관측: 사용할 최대 빔 수, 유효 거리 (Seer: BeamsNumUsedInLoc=541, LaserFarDist=80, CloserDist=0.01)
    int beams_used = 541;
    double laser_far_dist = 80.0;   // m
    double laser_close_dist = 0.01; // m

    // 우도 정규화 분모 (Seer 실측: pdf_sum / valid_beam / 255)
    double pdf_max = 255.0;

    // 재위치추정 (Seer DoRelocAction 실측): 영역 살포 → 담금질 반복 → 이중 게이팅.
    int reloc_max_iterations = 100;       // 반복 상한 (Seer 100)
    double reloc_anneal_denom = 100000.0; // 담금질 분모 (Seer 100000)
    // 성공 임계 — 관측 우도는 이제 Seer 충실(ObservationField, getPostProb 비트일치)이라
    //   우도 스케일 확정: 좋은 정합 ~0.2, 자세 소이탈(0.01rad)~0.11, 대이탈~0.004(측정).
    //   맵 밀도·빔수에 따라 절대값이 달라지므로 배포별 튜닝 대상(희소맵은 낮게). 기본은 일반값.
    //   ※ Seer DoRelocAction 의 정확한 성공 게이트(임계·판정식)는 별도 RE 백로그.
    //   (구 0.5 는 가우시안 근사 시절 스케일.)
    double reloc_success_threshold = 0.1;

    // 슬립(skid) 감지 (Seer CheckWheelSkid/skidDetect 실측 기본값)
    double skid_check_distance = 1.0; // 병진 변위 임계 (m)
    double skid_check_angle = 0.5236; // 회전 변위 임계 (rad, =30°)
    double skid_mismatch_ratio = 2.0; // 휠↔레이저 오도 불일치 배율 (Seer 하드코딩 2.0)
    double recover_time = 1.0;        // 정지 후 복구 대기 (s)

    // 저신뢰 정지 임계 — meanWeight(평균 관측 우도) < 이 값이면 LowConfidence.
    //   충실 우도 스케일 기준(수렴 시 파티클 평균 meanWeight ~0.05, 측정). 맵별 튜닝 대상.
    //   (구 0.3 은 가우시안 근사 시절 스케일.)
    double stop_confidence = 0.02;
};

} // namespace mcl2d

#endif // MCL2D_CORE_TYPES_HPP
