// Seer OdoCalculator 재구현 — 자료형.
//
// 원본 `libOdoCalculator.so` 의 구조체를 이름·의미 그대로 옮긴다. 오프셋까지 맞추지는
//   않는다(비트 대조 대상은 **출력값**이지 메모리 배치가 아니다). 원본 레이아웃은
//   References/seer/libOdoCalculator/layouts.txt 에 보존돼 있다.
//
// ROS 의존이 없다 — 시각은 호출자가 ns 로 준다.
#ifndef SEER_ODOM_CORE_TYPES_HPP
#define SEER_ODOM_CORE_TYPES_HPP

#include <cstdint>
#include <string>

namespace seer_odom_core
{

// 원본 MotorParam(176 B) 중 자세 계산에 쓰이는 항목만 옮긴다.
//   유효 휠 위치는 설계값에 보정항을 더한 (x+cpx, y+cpy) 다 — 원본 CalOdoCoef 89·91행.
struct MotorParam
{
    std::string name;
    double x = 0.0;   // m, 설계 휠 위치
    double y = 0.0;   // m
    double cpx = 0.0; // m, 보정항 (원본 MotorParam +0x90)
    double cpy = 0.0; // m, 보정항 (원본 MotorParam +0x98)
};

// 원본 MotorVitalInfo(64 B) 중 자세 계산 입력.
//   position 은 **조향각**(rad), v_enc 는 엔코더 속도, dpos 는 엔코더 변위다.
//   원본에서 CalSpeed 는 v_enc(+0x30) 를, CaldPose 는 dpos(+0x38) 를 읽는다.
struct MotorVitalInfo
{
    bool flag_set = false;
    std::uint64_t t_nsec = 0;
    bool stop = false;
    double position = 0.0; // rad, 조향각
    double v_enc = 0.0;    // m/s
    double dpos = 0.0;     // m
};

// 원본 OdometerOutput(88 B) 와 같은 필드 구성.
struct OdometerOutput
{
    std::uint64_t t = 0;
    bool stop = false;
    double vx = 0.0, vy = 0.0, vw = 0.0;       // 속도 — CalSpeed 산출
    double dx = 0.0, dy = 0.0, dyaw = 0.0;     // 증분 — CaldPose 산출
    double x = 0.0, y = 0.0, yaw = 0.0;        // 누적 자세 — CalPose 산출
};

} // namespace seer_odom_core

#endif // SEER_ODOM_CORE_TYPES_HPP
