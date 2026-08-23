// dock_control 코어 — 도킹 모션 순수함수.
//
// 정본: references/tc_docking/phase1_gui.py (무수정 보존). 각 함수의 `정본 :N` 은 그 파일의 줄번호다.
// 설계표: dock_control/docs/function_table.md
//
// 이 헤더는 **ROS 를 모른다** — rclcpp·메시지 타입 참조 0건이 계약이다(⟦CI:dock-no-ros⟧).
// 기하·게인·한계는 전부 인자로 주입받는다. 리터럴 상수 금지(⟦CI:dock-no-drive-constants⟧).
#ifndef DOCK_CONTROL__DOCK_CORE_HPP_
#define DOCK_CONTROL__DOCK_CORE_HPP_

#include <optional>

namespace dock_control
{

/// 바퀴 단위 지령 — 전/후 각각 (속도, 조향).
/// wheel-level 로 내는 이유: Phase 4 는 `af == ar` 이면서 `vf != vr` 이라 BodyVelocity 로 표현 불가
/// (diff_drive.hpp:26 `vy = 0.0`). 계획 ADR-CMD.
struct DockWheelCommand
{
    double vf{0.0};  ///< 전륜 속도 [m/s] (부호 = 전/후)
    double af{0.0};  ///< 전륜 조향 [rad]
    double vr{0.0};  ///< 후륜 속도 [m/s]
    double ar{0.0};  ///< 후륜 조향 [rad]
};

/// PID 게인. 정본은 GUI 스핀박스에서 주입한다(축마다 별도 3종).
struct PidGains
{
    double kp{0.0};
    double ki{0.0};
    double kd{0.0};
};

/// PID 보조 한계. **축마다 값이 다르다** — 거리는 PHASE4_I_BAND, 수평(δ)은 PHASE4_I_BAND_PX.
struct PidLimits
{
    double i_band{0.0};   ///< |e| 가 이 안일 때만 적분 (적분 분리)
    double i_clamp{0.0};  ///< |i_term| 상한
    double lpf_a{0.0};    ///< 측정미분 LPF 계수 (0..1, 클수록 원값 추종)
};

/// PID 누적 상태. **축마다 별도 인스턴스를 소유**할 것 — 공유하면 거리·δ 적분이 섞인다.
struct PidState
{
    double i_term{0.0};
    double d_filt{0.0};
};

/// distPidStep 결과. 정본의 5-튜플을 구조체로 묶었다(설계표 §3 D2).
struct PidOutput
{
    double u{0.0};    ///< 포화 적용된 출력 (정본의 v_app / delta)
    double u_p{0.0};
    double u_i{0.0};  ///< 갱신 후 i_term (로깅용 사본)
    double u_d{0.0};
};

/// (-180, 180] 로 wrap.
double wrapPm180(double deg);

/// (-90, 90] 로 wrap — dock line 법선의 180° 모호성 전용.
/// ⚠ wrapPm180 과 **절대 혼용 금지**. 정본 :265-271 이 별도 함수로 둔 이유가 이것이다.
double wrapMod180(double deg);

/// PID 1-step. 거리·수평(δ)·자세가 모두 이 엔진을 재사용한다. 정본 :352-371.
///
/// anti-windup 3중: ① 적분 분리 |e| <= i_band ② 출력 포화 && 오차가 포화 방향이면 동결
/// ③ |i_term| <= i_clamp. 추가로 **오차 부호 교차 시 I 하드 리셋**.
/// 정본 주석이 밝힌 트레이드오프: 오버슛 0.15 mm(무리셋 11 mm) vs 일정외란 잔류 4.7 mm(무리셋 0 mm).
/// "도킹은 도크 방향 초과 진입이 더 위험" 이라 하드 리셋을 채택했다 — 되돌리지 말 것.
/// D 항은 **측정 미분**(setpoint 고정이라 derivative kick 없음).
///
/// @param e_prev 직전 오차. **nullptr = 첫 cycle**(정본의 `None`). NaN 을 쓰면 부호교차 비교가
///               조용히 false 가 되어 하드 리셋이 죽는다(설계표 §3 D1).
/// @param state  입출력 — i_term·d_filt 가 갱신된다. 이 함수의 유일한 부작용.
PidOutput distPidStep(double e, const double *e_prev, double d_raw, double dt,
                      PidState &state, const PidGains &gains, double cap,
                      const PidLimits &limits);

/// 카메라 수평오차(px) → 조향 보정 δ[rad]. 정본 :1836-1846.
///
/// `travel = (e_d >= 0) ? +1 : -1`, `e_px = travel * approach_sign * err_px`.
/// travel 보정이 필요한 이유(정본 :1834-1835): δ 는 "속도 방향" 기준이라 **후퇴(재접근) 중
/// δ 의 x축 효과가 반전**된다. 정본 :2063 이 기록한 사고 — 이 보정이 없어 후퇴 중 δ 가 반대로
/// 작용해 err_px 가 +200 px 까지 벌어져 FOV 밖에서 정지했다.
///
/// 반환은 δ 자체이며 조향 합성(`approach_sign*pi/2 - delta` 및 클램프)은 호출자 몫이다.
/// @param px_prev 직전 e_px. nullptr = 첫 cycle. **호출자가 e_px 를 보관**해야 하므로
///                반환된 다음 상태를 얻으려면 out_e_px 를 쓴다.
/// @param out_e_px 금회 계산된 e_px (호출자가 다음 cycle 의 px_prev 로 넘길 값)
/// @param state    δ 축 전용 PidState (거리와 공유 금지)
double phase4Delta(double err_px, double e_d, double approach_sign,
                   const double *px_prev, double dt, PidState &state,
                   const PidGains &gains, double delta_max_rad,
                   const PidLimits &limits, double *out_e_px);

/// 기하 진입 조향 — 도크 정면 경유점을 **직선으로** 겨냥하는 crab 각.
///
/// 순수 crab 은 회전이 없으므로 base_link 속도는 `v(cosθ, sinθ)`, `θ = as(π/2 − δ)` 이고
/// 접근거리 `D` 로 나누면 속도가 소거되어 `d(cte_x)/dD = tan δ` 만 남는다. 즉 **수평 폐합은
/// 시간이 아니라 접근 거리에 비례**하며, 경유점까지 남은 거리 `e_d` 에 대해
///
///     δ* = atan(cte_x / e_d)   ⇒   d(cte_x)/d(e_d) = cte_x/e_d   ⇒   cte_x ∝ e_d
///
/// 가 되어 수평오차가 남은 거리에 정비례해 줄고 **경유점에서 정확히 0** 이 된다. 이득이 없으므로
/// 튜닝 대상이 아니고, 경로가 직선이라 도달 지점과 쓸림 폭을 사전에 계산할 수 있다.
///
/// 클램프에 걸린다는 것은 «그 경유점까지 직선으로는 못 간다»(|cte_x|/e_d > tan δmax)는 뜻이며,
/// 이때 반환각은 최선의 근사다 — 판정이 필요하면 호출자가 같은 조건을 직접 본다.
///
/// @param e_d 경유점까지 남은 접근거리 [m]. 0 이하이면 이미 지났으므로 0 을 낸다.
double geomEntryDelta(double cte_x, double e_d, double delta_max_rad);

/// 기하각에 **과조향 바이어스**를 얹는다 — 오차 방향으로만 키우고 상한에서 클램프한다.
///
/// 왜 더 도는가. 두 가지가 같은 방향을 가리킨다:
///   · **실측 폐합률이 이론의 91%** 다(포화 구간 적합 −0.4246 대 이론 −0.4663). 순수 기하각은
///     계통적으로 덜 돈다 — δ 13° 지령이 실효 11.87° 로 작동해 약 1.2° 부족하다.
///   · 비대칭: 덜 돌면 경유점에 오차를 남긴 채 도착해 **도크 가까이서** 고쳐야 하고, 더 돌면
///     0 에 일찍 닿아 **멀리서** 피드백으로 넘어간다. 후자가 접근 여유 측면에서 낫다.
///
/// 과조향은 그대로 두면 반대편으로 넘어가므로 **조기 전환(`entry_exit_px`)이 짝** 이다.
/// 그 장치 없이 이 함수만 쓰면 안 된다.
///
/// 부호는 기하각이 정한다. 그리고 **바이어스는 기하각 자신을 넘지 않는다** —
/// `applied = min(bias, |δ*|)`. 오차가 거의 없는데 고정량을 더하면 «이유 없이 3° 틀기» 가
/// 되므로, 과조향은 기하각의 2배를 상한으로 두고 오차가 0 으로 갈수록 함께 0 이 된다.
double geomEntryDeltaBiased(double cte_x, double e_d, double delta_max_rad, double bias_rad);

/// 기하 진입이 조향 한계 안인가 — 밖이면 **선행 translate 로 줄여야 할 수평량**[m] 을 낸다.
///
/// 직선 진입의 성립 조건은 `|cte_x| <= tan(δmax)·e_d` 다. 이를 넘으면 crab 각이 클램프에 걸려
/// 경유점을 향하지 못하고, 남은 오차를 접근 내내 끌고 가다 근접부에서 횡으로 쓸게 된다.
/// 그때는 거리를 바꾸지 않는 translate(조향 0° 전후진)로 수평을 먼저 줄이는 편이 맞다 —
/// translate 는 도크면과 평행하게 움직이므로 접근 여유를 잠식하지 않는다.
///
/// ⚠ **경유점 안쪽(`e_d <= 0`)에서는 남은 거리로 지울 것이 없다** — 그렇다고 진입이 불가한
/// 것이 아니다. 수평이 이미 완료 허용치 안이면 필요한 진입각은 0 이고, 조향은 그냥 ±90°
/// 순수 크랩이라 그대로 들어가면 된다. 그래서 `tol_m` 안쪽은 **줄일 필요가 없는 양**으로 본다.
/// 이 항이 없던 판에서는 3.2 mm 잔류가 「진입 불가」로 판정돼, 3-2 가 자기 허용치(5 px)까지
/// 줄여도 통과할 수 없는 — 반복해도 끝나지 않는 — 상태가 됐다(실기 실측).
///
/// @param tol_m 수평 완료 허용치[m](`converge_tol_center_mm`). 이 안이면 부족분 0.
/// @return 0 이면 그대로 기하 진입 가능. 양수면 그만큼 `|cte_x|` 를 줄여야 가능해진다.
double geomEntryTranslateNeed(double cte_x, double e_d, double delta_max_rad, double tol_m);

/// Phase 4 관측 게이트 — **지령을 만드는 데 실제로 쓰이는 축**만 요구한다.
///
/// 무효 축의 잔류값을 쓰면 안 된다는 원칙(정본이 source 를 뭉뚱그려 각도 무효 프레임에 카메라
/// 잔류값을 쓴 것이 실기 실패 10회의 원인)은 그대로다. 다만 **쓰지 않는 축까지 요구하면**
/// 제어가 이유 없이 멈춘다 — 요구 조건은 «관측이 있는가» 가 아니라 «이 지령이 그 축을
/// 소비하는가» 로 정해야 한다.
///
/// 수평·거리축은 Phase 4 의 두 지령 채널(δ·v_app)과 완료 판정에 항상 쓰이므로 언제나 요구한다.
/// 자세축은 heading 이득이 살아 있을 때만 ω 에 기여하므로, 이득이 0 이면 요구하지 않는다.
///
/// 자세축의 가용성은 환경에 따라 크게 흔들린다 — 검은 도크 배경에서는 근적외선 반사가 약해
/// 라이다 자세축 유효율이 **4.2%** 까지 떨어진다(같은 시점 거리축 99.2% · 카메라 99.2%,
/// lgit-c6-4 실측). 순수 crab 은 ω 가 0 이므로 이 축이 없어도 지령이 온전하다.
bool phase4AxesReady(bool has_lateral, bool has_range, bool has_yaw, bool yaw_channel_active);

/// Phase 4 조향 합성 — 크랩 기준각 `as·90°` 에 수평 보정 δ 를 얹고 클램프한다.
///
/// **`as·(π/2 − δ)` 이지 `as·π/2 − δ` 가 아니다.** 정본(:1844)은 후자로 적혀 있으나 정본 기체는
/// 좌측 접근(`as=+1`)뿐이라 두 식이 같은 값을 낸다 — 차이는 우측 접근에서만 드러난다.
///
/// 우측 접근(`as=−1`)에서 `as·π/2 − δ` 를 쓰면 δ 가 오차를 **키우는** 방향으로 붙는다.
/// 크랩 기준각이 뒤집히면 «오차를 줄이는 x 성분» 의 부호도 함께 뒤집혀야 하기 때문이다.
/// 실기 실측(lgit-c6-4, 2026-08-13): `err_px −110.8` 에서 종전 식은 조향 −115° 를 내
/// 후진 성분을 만들었고 `err_px` 가 −273 까지 벌어져 마커가 FOV 밖으로 나갔다.
/// 같은 조건에서 본 식은 −65° 를 내며 전진 성분이 된다(측정 규칙: +x 전진 → err_px 증가).
///
/// @param delta_max_rad δ 상한. 클램프 한계는 정본과 같이 `π/2 + delta_max_rad`.
double phase4Steer(double approach_sign, double delta, double delta_max_rad);

/// 접근측이 후방일 때 **명령 프레임**에 얹는 조향 오프셋[rad].
///
/// 코어의 축 규약은 «거리축 = base_link y(라이다) · 수평축 = base_link x(카메라 err_px)» 로
/// 고정돼 있다 — 카메라가 **측면**에 달린 좌·우 접근을 전제한 것이다. 후방 접근은 그 두 축이
/// 90° 돌아간 것뿐이므로 **제어식·게인·수렴판정을 하나도 바꾸지 않고** 명령 프레임만 돌린다.
///
/// 그래서 각 페이즈의 조향은 이렇게 자동으로 갈린다(오프셋을 더하기만 한다):
///   · 3-2 수평 정렬 : 좌·우 `0`(전후 직진) → 후방 `∓90°`(크랩)
///   · 4 접근       : 좌·우 `as·(π/2−δ)`(크랩) → 후방 `≈0`(후진 직진)
///
/// 값이 `−as·π/2` 인 이유가 그 둘째 줄이다 — δ=0 에서 `phase4Steer` 결과와 더해 0 이 되어야
/// 접근이 «거리축을 따라 곧게» 가는 동작이 된다.
///
/// @param rear_approach 후방 접근인가 (좌·우면 false)
/// @param approach_sign 접근측 부호(좌 +1 · 우 −1). 후방의 부호는 실측으로 정한다.
double steerFrameOffset(bool rear_approach, double approach_sign);

/// `reachableSteer` 의 결과. 「보낼 각이 없다」를 값으로 표현하기 위한 그릇이다.
struct SteerTarget
{
    bool has_value{false};
    double value{0.0};
};

/// 한계를 지나지 않고 갈 수 있는 조향 목표각을 고른다. 없으면 `has_value == false`.
///
/// 조향축은 회전 자유가 아니라 **유한 구간**(±`limit_rad`)이다. 그래서 「가까운 쪽」을 고르는
/// 통상의 각도 wrap 은 틀렸다 — 짧은 길이 한계를 통과하면 축이 그 앞에서 멈추고, 그 자리는
/// 지령이 더는 안 먹는 자리가 된다.
///
/// ⚠ **`tgt ± 180°` 를 후보로 삼지 않는다.** 그것은 「같은 직선, 구동 부호 반대」라 각도만
///   바꾸고 속도를 그대로 두면 그 바퀴가 반대로 민다. 게다가 축마다 다른 표현이 채택되면
///   앞뒤가 갈리고, 그 상태에서 정지 유지가 한쪽에 180° 를 내보내 **바퀴 하나가 반 바퀴를
///   쓸며 한계에 박힌다**(실기 관측: 앞축이 +70° → −110° 를 훑고 정지).
///
/// @param cur 현재 조향각 [rad] · @param tgt 원하는 조향각 [rad] · @param limit_rad 구간 반폭
SteerTarget reachableSteer(double cur, double tgt, double limit_rad);

/// **도킹전용 crab 합성** — 조향은 전/후 동일, 속도차로 yaw 를 만든다. 정본 :1877-1881.
///
/// `dv = radians(w_deg) * arm_m`, `af = ar = steer`, `vf = v_app + as*dv`, `vr = v_app - as*dv`.
///
/// 이것이 기존 QdCrabIK 로 표현 불가한 지점이다 —
/// qd_crab_inverse_kinematics.cpp:125-128 이 `w1.wheel_speed = w2.wheel_speed = speed` 로
/// 두 바퀴 속도를 **강제로 같게** 만든다. 그래서 도킹 패키지가 이 합성을 직접 소유한다.
///
/// 정본 근거(:1872-1876): 순수 crab 에서 yaw 의 기구학 정확 채널은 `vy_i = vy + w*x_i`(x = +-0.33).
/// 실차 증명 = 삭제된 트림(F +9.3 / R -9.3 mm/s -> 1.5 deg/s 실회전, rec_173926).
/// **travel 인자를 받지 않는다** — `vy = v_app*approach_sign` 이라 후퇴는 v_app 부호가 담당한다.
/// +w(CCW) = 전륜이 빠르다.
///
/// ⚠ 정확 IK(QdDualSteerIK) 로 치환 금지 — 정본이 rec_153222 로 배제한 경로(⟦CI:dock-no-exact-ik⟧).
/// ⚠ arm_m 은 본 기체 실측 없음(tc 트림 유효값 0.356). 주입값의 출처를 호출자가 책임진다.
DockWheelCommand composePhase4Wheels(double v_app, double steer_rad, double w_deg,
                                     double approach_sign, double arm_m);

/// 근접구간 속도 상한. 정본 :1812-1814.
/// `if |e_d| <= near_zone_m: cap = min(cap, v_near)`. 무가속 램프는 **없다**(정본 :726-727).
double phase4Vcap(double v_stage, double e_d, double near_zone_m, double v_near);

/// IMU 누적 요각 상태 — Phase 4 하드캡용. 정본 :1854-1857 의 `imu_prev`/`imu_cum` 대응.
struct ImuAccum
{
    double cum_deg{0.0};    ///< 시작 이후 누적 회전량 [deg]. **180° 를 넘을 수 있다**
    double prev_deg{0.0};   ///< 직전 표본 [deg]
    bool have_prev{false};  ///< 첫 표본은 증분을 만들지 않는다
};

/// IMU 표본 1개를 누적에 반영한다. 정본 :1854-1857.
///
/// `cum += wrapPm180(iy - prev)` — **매 스텝 wrap** 이라 ±180 경계를 지나도 누적이 끊기지 않는다.
/// 첫 호출은 기준점만 잡고 누적하지 않는다(정본 `if imu_prev is None: imu_prev = iy`).
///
/// ⚠ 절대 방위의 정확도는 요구되지 않는다 — **차분만** 쓰므로 자기 드리프트에 둔감하다.
void imuAccumStep(ImuAccum &state, double imu_yaw_rad);

/// Phase 4 하드 runaway 판정. 정본 :1859 `abs(imu_cum) > PHASE4_YAW_RUNAWAY_DEG`.
///
/// 어떤 오작동이든 **마커 이탈 전에** 정지시키는 최후 방어선이다.
/// 계기: v2 가 stale scan 으로 피드백이 동결돼 19° 회전하며 마커를 놓쳤다(정본 :199·:224).
bool imuRunaway(const ImuAccum &state, double cap_deg);

/// 공전 오버슛 판정. 정본 :1272-1274.
///
/// 누적이 아니라 **시작 기준 단일 차분**이다(`wrapPm180(now - imu0)`) — 공전 1회는 180° 미만이라
/// 누적이 필요 없고, 단일 wrap 이 부호 뒤집힘을 막는다.
/// `|imu_rot| > |dphi| + cap` 이면 「목표보다 그만큼 더 돌았다」 = 관측 이상 → 안전 정지.
bool orbitOvershoot(double imu_yaw_rad, double imu0_yaw_rad, double dphi_deg, double cap_deg);

/// dock 면 법선각 → 제어 오차 e_yaw[deg]. 정본 :1864.
/// `wrapPm180(yaw_err_deg - copysign(90, yaw_err_deg))`.
/// ⚠ 입력 `yaw_err_deg` 는 **dock 면 법선각**(정렬 시 ~ +-90 deg)이지 제어 오차가 아니다.
double dockLineYawError(double yaw_err_deg);

/// Phase 3-1 ICR 의 y 좌표 c1y = 마커 법선과 base_link y축의 교점. 정본 :1352-1356.
/// `nx = cos(yaw_err)`, `ny = sin(yaw_err)`, `c1y = my - mx*ny/nx`.
/// `|nx| < nx_min` 이면 법선이 y축과 평행해 교점이 발산하므로 **nullopt**(정본 :1354 는 중단).
///
/// 정본 :1356 은 이 값을 **페이즈 진입 1회만** 산출하고 루프는 w 만 갱신한다 — 조향 상수성이
/// Phase 3-1 의 설계 전제다(:86-88). 호출자는 루프 안에서 재호출하지 말 것.
std::optional<double> computeOrbitCenter(double mx, double my, double yaw_err_deg,
                                         double nx_min);

// ── 원위치(RETURN_HOME) ─────────────────────────────────────────────────────
// 정본 `do_return_home`(:2001~2123)에서 **판정만** 떼어낸 것이다. 지령 산출은 Phase 4 와
// 같은 함수(`phase4Delta`·`phase4Steer`·`distPidStep`·`composePhase4Wheels`)를 그대로 쓴다 —
// 원위치는 목표 거리와 게인·게이트만 다르다.

/// 원위치 중단 사유. `OK` 만 제어를 계속한다.
enum class HomeAbort
{
    OK,           ///< 계속 진행
    STALE,        ///< 관측이 낡았거나 marker 상실이 유예를 넘겼다 (정본 :2030~2031)
    MARKER_WAIT,  ///< marker 간헐 결손 — **중단이 아니다.** steer-hold 정지로 복귀를 기다린다
    LIDAR_WAIT,   ///< scan 간헐 끊김 — 위와 같다
    LIDAR_OVER,   ///< 라이다 복귀 대기 한도 초과 (정본 :2036~2037)
    FOV,          ///< 마커가 화면 끝단 (정본 :2042~2043)
    TIMEOUT,      ///< 전체 시간 초과 (정본 :2044~2045)
};

/// `returnHomeAbort` 입력. **인자를 나열하지 않고 구조체로 받는다** — 무타입 순서배열이
/// 순서 실수를 컴파일러에게서 숨기는 실패 양식(`debt-055`)을 코어로 복제하지 않기 위해서다.
struct HomeAbortInput
{
    bool obs_fresh{false};            ///< 관측 나이 <= 상한 (정본 `ORBIT_OBS_STALE_S` 0.5)
    bool has_lateral{false};          ///< 카메라 수평축 유효 (정본 `e is None` 의 대응)
    bool has_range{false};            ///< 라이다 거리축 유효 (정본 `d is None` 의 대응)
    double err_px{0.0};               ///< 수평 오차 [px]
    double fov_edge_px{0.0};          ///< |err_px| 가 이 값을 넘으면 FOV
    /// marker 상실 시작 이후 경과 [s] (`has_lateral` 이 false 인 동안만 의미).
    double marker_lost_elapsed_s{0.0};
    /// marker 결손 유예 [s] — 이만큼은 «눈을 감고 정지» 로 견딘다.
    ///
    /// **왜 1프레임 즉시 종료가 아닌가.** 관측이 *안 오는* 경우는 `obs_max_age_s`(0.5 s)까지
    /// 견디면서, 관측이 «아무것도 못 봤다» 고 *말해 주면* 즉시 죽는 것은 앞뒤가 맞지 않는다 —
    /// 두 경우의 정보량은 같다. 실기 실측(lgit-c6-4)에서 마커 결손이 **5.1%**, 연속 최대
    /// **7프레임(0.49 s)** 로 나타나 1프레임 규칙으로는 1 초 넘는 복귀가 완주 불가였다.
    double marker_grace_s{0.0};
    double lidar_wait_elapsed_s{0.0}; ///< 라이다 대기 시작 이후 경과 [s] (`has_range` 가 false 인 동안만 의미)
    double lidar_wait_limit_s{0.0};   ///< 라이다 대기 한도 [s]
    double elapsed_s{0.0};            ///< 페이즈 시작 이후 경과 [s]
    double timeout_s{0.0};            ///< 전체 상한 [s]
};

/// 원위치 중단 판정. 정본 :2030~2045 의 **제어흐름 순서를 그대로** 재현한다.
///
/// 순서가 곧 의미다 — 정본은 `d is None` 이면 `continue`(:2040) 하므로 **라이다 대기 중에는
/// FOV·timeout 을 아예 검사하지 않는다.** 순서를 바꾸면 scan 이 끊긴 채 정지해 기다리는
/// 동안 timeout 이 흘러 「대기 초과」가 아니라 「시간 초과」로 죽는다 — 사유가 원인을
/// 가리키지 못하면 현장에서 오진한다.
///
/// ⚠ `LIDAR_WAIT` 는 **중단 사유가 아니다.** 호출자는 이 값을 받으면 steer-hold 정지를
/// 내고 다음 사이클로 넘어가야 한다(정본 :2038~2040).
///
/// ⚠ 대기 시각의 set/clear 는 이 함수 밖이다 — 호출자가 `has_range` 가 살아나는 순간
/// 래치를 지워야 한다(정본 :2041 `lidar_wait = None`). 해제를 빠뜨리면 간헐 결측이
/// 누적돼 정상 주행 중 한도를 넘긴다.
HomeAbort returnHomeAbort(const HomeAbortInput &in);

/// 원위치 완료 판정 — **거리 단독**. 정본 :2052 `abs(e_d) <= RETURN_TOL_D`.
///
/// ⚠ 이 함수에 수평·자세를 더하지 말 것. 3축으로 통일하면 거리 수렴 후 `v -> 0` 이라
/// 수평을 교정할 수단이 없어 영구 대기·움찔로 교착한다(정본 :2048~2051, FAILURES #24).
/// 사용자 확정 규약이며 `DockCommand.srv:12-13` 이 같은 문장을 계약으로 못박고 있다.
/// 판정을 함수로 떼어낸 이유가 이것이다 — 호출부의 `if` 를 편집해 축을 끼워넣지 못하게 한다.
bool returnHomeDone(double e_d, double tol);

/// 주입 수평오차[mm] → 픽셀 등가. 정본 :2065 `dx_mm * fx / (z_cam * 1000)`.
///
/// 정본 :2047 의 정변환 `x_mm = err_px * z_cam / fx * 1000` 의 **역함수**다. 반복 시험에서
/// 시작 수평오차를 의도적으로 주입할 때, 그 목표를 제어가 쓰는 픽셀 좌표로 옮긴다.
/// `z_cam`·`fx` 가 0 에 가까우면 변환이 성립하지 않으므로 **0 을 반환**한다(무주입과 동일).
double homeErrPxTarget(double dx_mm, double z_cam, double fx);

}  // namespace dock_control

#endif  // DOCK_CONTROL__DOCK_CORE_HPP_
