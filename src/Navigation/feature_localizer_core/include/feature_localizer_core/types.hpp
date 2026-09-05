#ifndef WALL_LOCALIZER_CORE__TYPES_HPP_
#define WALL_LOCALIZER_CORE__TYPES_HPP_

#include <cmath>
#include <string>
#include <vector>

// 벽 3면 라이다 정밀 측위 코어 공용 타입.
// 단위: 내부 전체 m·rad 단일 (변환은 어댑터 경계에서 1회).
// 변환 표기: T_a_b 는 "b 프레임의 점을 a 프레임으로" — p_a = R(yaw)·p_b + t.
// 직선 법선형: n·p = d, ||n||=1, d ≥ 0, n 은 해당 프레임 원점→직선 수직 방향
//   (원점 정향 규칙 — 무방향 직선의 π 모호성을 제거한다).

namespace feature_localizer_core
{

// 2D 점 (m). 프레임은 사용처 시그니처·주석에 명시.
struct Point2D
{
    double x_m{0.0};
    double y_m{0.0};
};

// SE(2) 자세 = 변환 T_a_b (x_m, y_m = t, yaw_rad = R).
struct Pose2D
{
    double x_m{0.0};
    double y_m{0.0};
    double yaw_rad{0.0};
};

// 무한 직선 법선형 (헤더 서두의 정향 규칙 적용).
struct LineNormalForm
{
    double nx{0.0};
    double ny{0.0};
    double d_m{0.0};
};

// 라이다 프레임 추출 선분.
struct ExtractedSegment
{
    LineNormalForm line;  // 라이다 원점 정향
    Point2D p1;           // 직선 위로 사영한 양 끝점 (라이다 프레임)
    Point2D p2;
    int num_points{0};
    double length_m{0.0};
    double rms_m{0.0};  // 점-직선 수직거리 RMS
};

// 기준 특징면 (스테이션 프레임 끝점 2개, m).
struct FeatureRef
{
    std::string name;
    Point2D p1;
    Point2D p2;
};

// [-π, π) 로 정규화.
inline double normalizeAngle(double a_rad)
{
    double a = std::atan2(std::sin(a_rad), std::cos(a_rad));
    // atan2 는 +π 를 반환할 수 있다 — 반개구간 [-π, π) 로 접는다.
    if (a >= M_PI)
    {
        a = -M_PI;
    }
    return a;
}

// p_a = T_a_b · p_b
inline Point2D transformPoint(const Pose2D &T_a_b, const Point2D &p_b)
{
    const double c = std::cos(T_a_b.yaw_rad);
    const double s = std::sin(T_a_b.yaw_rad);
    return {T_a_b.x_m + c * p_b.x_m - s * p_b.y_m, T_a_b.y_m + s * p_b.x_m + c * p_b.y_m};
}

// T_a_c = T_a_b ∘ T_b_c
inline Pose2D compose(const Pose2D &T_a_b, const Pose2D &T_b_c)
{
    const Point2D t = transformPoint(T_a_b, {T_b_c.x_m, T_b_c.y_m});
    return {t.x_m, t.y_m, normalizeAngle(T_a_b.yaw_rad + T_b_c.yaw_rad)};
}

// T_b_a = (T_a_b)⁻¹
inline Pose2D inverse(const Pose2D &T_a_b)
{
    const double c = std::cos(T_a_b.yaw_rad);
    const double s = std::sin(T_a_b.yaw_rad);
    return {-(c * T_a_b.x_m + s * T_a_b.y_m), -(-s * T_a_b.x_m + c * T_a_b.y_m),
            normalizeAngle(-T_a_b.yaw_rad)};
}

// 직선 추출 파라미터.
struct ExtractParams
{
    double range_min_m{0.05};     // 이 미만 거리 표본 폐기
    double range_max_m{30.0};     // 이 초과 거리 표본 폐기
    double angle_min_rad{-M_PI};  // 섹터 게이트 (빔각 하한)
    double angle_max_rad{M_PI};   // 섹터 게이트 (빔각 상한)
    double max_point_gap_m{0.2};  // 인접 표본 간격 초과 시 클러스터 분리 (가림 경계)
    // 분할 임계는 라이다 거리 잡음 3σ 수준으로 둔다 — 더 좁히면 잡음이 벽을 토막 낸다.
    double split_dist_m{0.03};
    // 병합 각도는 짧은 토막의 잡음 적합 각도 산포를 덮되, 직교 벽(90°)과는 충분히 먼 값.
    double merge_angle_rad{5.0 * M_PI / 180.0};
    double merge_dist_m{0.03};  // 공선 병합 직선 간격 임계
    int min_points{8};                           // 선분 최소 표본 수
    // 선분 최소 길이 — ANT localization+ 의 최소 추출 세그먼트 40 cm 준용
    // [ANT localization+ User Manual R2.6, §D 3.1, page 128](References/Bluebotics/)
    double min_length_m{0.4};
};

// 벽 대응 파라미터.
struct MatchParams
{
    double gate_angle_rad{10.0 * M_PI / 180.0};  // 예측 벽과 각도차 게이트
    double gate_dist_m{0.30};                    // 예측 벽과 수직거리차 게이트
    // 겹침비 = (벽에 귀속된 선분들의 구간 합집합) / 예측 벽 구간 길이 — "기대한 벽을
    // 얼마나 봤나". 선분 자기 길이 기준으로 재면 잡음으로 토막난 짧은 조각이 비율
    // 1.0 으로 본선분을 이기고 대응을 가로챈다.
    double min_overlap_ratio{0.25};
    // 재적합 회랑 반폭: 대응된 벽의 예측 직선에서 이 거리 안의 원시 점 전체로 측정을
    // 다시 적합한다(토막은 대응 근거일 뿐). 잡음 3σ 이상으로 두되, 벽 근처 클러터와
    // 겹치지 않는 크기여야 한다.
    double refit_corridor_m{0.06};
    // 재적합 시 예측 벽 구간 양끝 여유 (구간 밖 점 유입 한도)
    double refit_margin_m{0.10};
};

// 자세 해석 파라미터.
struct SolveParams
{
    // 가관측성 하한: Σw·nnᵀ 의 최소고유값/Σw. 벽 2면 등가중이면 (1−cos α)/2 이므로
    // 0.05 는 법선 사이각 α ≳ 26° 를 요구한다 — 사실상 평행한 벽만으로는 해를 내지 않는다.
    double min_normal_spread{0.05};
    int max_iterations{3};          // 대응→해석 반복 상한
    double converge_eps_m{1e-4};    // 반복 종료 병진 변화량
    double converge_eps_rad{1e-4};  // 반복 종료 회전 변화량
};

// 품질 판정 파라미터.
struct QualityParams
{
    int min_walls{2};                  // DEGRADED 하한 (비평행 검사는 solver 가 수행)
    double max_dist_residual_m{0.03};  // 벽별 수직거리 잔차 상한
    double max_angle_residual_rad{3.0 * M_PI / 180.0};  // 벽별 각도 잔차 상한
    double max_jump_m{0.10};                            // 직전 해 대비 병진 점프 상한
    double max_jump_rad{5.0 * M_PI / 180.0};            // 직전 해 대비 회전 점프 상한
    int max_consecutive_rejects{5};  // 연속 기각 초과 시 추적을 버리고 초기 추정으로 복귀
};

struct FeatureLocalizerParams
{
    ExtractParams extract;
    MatchParams match;
    SolveParams solve;
    QualityParams quality;
};

}  // namespace feature_localizer_core

#endif  // WALL_LOCALIZER_CORE__TYPES_HPP_
