// SeerMapperConfig — karto::Mapper 에 Seer RE(Reverse Engineering) 파라미터 적용.
//
// 근거 등급을 값마다 명시한다. 등급을 섞으면 "실측 아닌 값이 실측처럼" 보인다
// (2026-08-08 리뷰 Medium — `minimum_time_interval` 이 그 사례였다).
//
//   [실측]   원본 `karto::Mapper::InitializeParameters()` @0xe1c50 디스어셈블에서 즉치 확인.
//   [상류]   상류 open_karto 기본값과 동일 — 원본도 이 값이다.
//   [선택]   실측 근거 없음. 구현자가 정했다.
//
// 2026-08-08 전량 재추출 완료 — 28개 파라미터 전부 이름·타입·값 확정. 추출 실패 0건.
//   방법: 파라미터 블록 경계(`mov $0x50,%edi; call operator new` 정확히 28회)
//         + std::string SSO 이름 길이 즉치(`movq $<len>,(%rsp)`)
//         + 값 슬롯(`0x48(obj)` 스토어 28회, 블록과 1:1)
//         + DWARF decodedline 줄번호(1842~2046 단조 증가) — 4중 교차.
//   판본 교차검증: 3.4.5.20 과 3.4.8 의 같은 함수를 명령 스트림 정규화 대조 → 1,925개 중 차이 0건.
//
// ★ = 상류 stock 과 다름(= Seer 가 튜닝한 값). 상류 기본값은
//    third_party/open_karto/src/Mapper.cpp `Mapper::InitializeParameters()` 원문으로 대조했다.
#ifndef SLAM_KARTO_CORE_SEER_MAPPER_CONFIG_HPP
#define SLAM_KARTO_CORE_SEER_MAPPER_CONFIG_HPP

namespace karto
{
class Mapper;
}

namespace slam_karto_core
{

/// Seer RE 파라미터 전량(29개). 기본값 = 원본 배포값(등급은 각 줄 주석 참조).
struct SeerMapperParams
{
    // ── 노드 추가 게이트 ──────────────────────────────────────────────────
    /// [실측] linearUpdate. **0.01 m** — 컴파일 기본값 0.2 가 아니다.
    ///   `KartoSLAM` 생성자가 0.2 를 넣지만(`c9ccb: movabs $0x3fc999999999999a`),
    ///   `SlaMapping::run()` 이 **매 메시지마다 리터럴로 덮어쓴다**:
    ///   `70499: movaps 0x1033d0(%rip),%xmm0` / `704a0: movups %xmm0,0x10(%rsi)`,
    ///   `.rodata:0x1033d0` = `(0.01, 30.0)` (SlaMapping.cpp:92). 그 뒤 `SetParam` → `Process` 에서
    ///   `ca9b1: call setParamMinimumTravelDistance` 로 적용된다(KartoSLAM.cpp:150).
    ///   ⚠ 초기 이식본은 생성자 값 0.2 를 채택했다 — **노드 밀도가 20배 달랐다.**
    double minimum_travel_distance = 0.01;
    /// [실측] angularUpdate. **0.05 rad** — 컴파일 기본값 0.174533(10°)이 아니다.
    ///   `704a4: movdqa 0x1033e0(%rip),%xmm0` / `704ac: movdqu %xmm0,(%rsi)` (SlaMapping.cpp:93),
    ///   `.rodata:0x1033e0` = `(0.05, 0.019999999552965164)`. 적용은
    ///   `ca9c2: call setParamMinimumTravelHeading` (KartoSLAM.cpp:151).
    double minimum_travel_heading = 0.05;
    /// [선택][원본 부재] **원본에는 이 파라미터가 아예 없다.** Seer 는 상류 29개 중 이것을 뺀
    ///   28개만 등록한다 — 근거 3중: ① `InitializeParameters()` 파라미터 블록 전수 28개
    ///   ② `.so` 18,437,896 B 전체 바이트열 검색에서 `"MinimumTimeInterval"` 0회
    ///      (대조군 `"MinimumTravelDistance"` 는 14회 검출) ③ DWARF 멤버명 0회. 3.4.8 도 동일.
    ///   값 3600.0 은 상류 기본값과 같아 거동은 중립이나, **원본 충실 항목이 아니다.**
    ///   보강 근거: 원본 라이브러리 전체에 `Mapper::setParam*` 호출은 **2개뿐**이고
    ///   (`setParamMinimumTravelDistance`·`setParamMinimumTravelHeading`, PLT `0x6cfb0`·`0x6a000`),
    ///   나머지 파라미터는 `InitializeParameters()` 기본값을 그대로 쓴다.
    double minimum_time_interval = 3600.0;

    // ── ★ Seer 튜닝 (거동 재현의 핵심) ────────────────────────────────────
    /// ★ [실측] 상류 70 → 100. `e2136: movl $0x64,0x48(%r15)`
    ///   (이름 앵커 `e20a5: movq $0xe,0x30(%rsp)` = len 14 "ScanBufferSize"). 3.4.8 `c8cb6` 동일.
    int scan_buffer_size = 100;
    /// ★ [실측] 상류 4.0 → 20.0 (5배 확대. 훨씬 먼 루프까지 탐색)
    double loop_search_maximum_distance = 20.0;
    /// ★ [실측] 상류 0.8 → 0.35 (coarse 게이트 대폭 완화)
    double loop_match_minimum_response_coarse = 0.35;
    /// ★ [실측] 상류 0.8 → 0.6 (fine 게이트 완화)
    double loop_match_minimum_response_fine = 0.6;
    /// ★ [실측] 상류 8.0 → 6.0 (탐색 공간 축소)
    double loop_search_space_dimension = 6.0;

    // ── 나머지 (전부 상류와 동일값으로 실측됨) ─────────────────────────────
    double scan_buffer_maximum_scan_distance = 20.0;      ///< [실측][상류] m
    int loop_match_minimum_chain_size = 10;               ///< [실측][상류] `e2789: movl $0xa,0x48(%r15)`
    double loop_match_maximum_variance_coarse = 0.16;     ///< [실측][상류] = 0.4^2
    double correlation_search_space_dimension = 0.3;      ///< [실측][상류] m
    double correlation_search_space_resolution = 0.01;    ///< [실측][상류] m
    double correlation_search_space_smear_deviation = 0.03; ///< [실측][상류] m
    double link_match_minimum_response_fine = 0.8;        ///< [실측][상류]
    double link_scan_maximum_distance = 10.0;             ///< [실측][상류] m
    double distance_variance_penalty = 0.09;              ///< [실측][상류] = 0.3^2
    double angle_variance_penalty = 0.12184696791468343;  ///< [실측][상류] = (20°)^2 rad^2
    double coarse_search_angle_offset = 0.3490658503988659;   ///< [실측][상류] 20°
    double coarse_angle_resolution = 0.03490658503988659;     ///< [실측][상류] 2°
    double fine_search_angle_offset = 0.003490658503988659;   ///< [실측][상류] 0.2°
    double loop_search_space_resolution = 0.05;           ///< [실측][상류] m
    /// [실측][상류] m. 즉치가 아니라 `e3171: mov %r15,0x48(%rbx)` — 컴파일러가 블록 17
    ///   (`CorrelationSearchSpaceSmearDeviation`)의 상수 0.03(`e2e27`)을 레지스터로 재사용했다.
    ///   `e2e27`~`e3171` 구간 전 명령에 `%r15` 쓰기 0건으로 값 보존 확인.
    ///   ⚠ 이전 조사가 이 항목과 `DistanceVariancePenalty`(0.09)를 혼동했었다 — 0.09 는 후자다.
    double loop_search_space_smear_deviation = 0.03;
    double minimum_angle_penalty = 0.9;                   ///< [실측][상류] `e37bd`
    double minimum_distance_penalty = 0.5;                ///< [실측][상류] `e38e8`
    bool do_loop_closing = true;                          ///< [실측][상류] `e268d: movb $0x1,0x48(%rbx)`
    bool use_scan_matching = true;                        ///< [실측][상류] `e1d25: movb $0x1,0x48(%r15)`
    bool use_scan_barycenter = true;                      ///< [실측][상류] `e1e36: movb $0x1,0x48(%r15)`
    bool use_response_expansion = false;                  ///< [실측][상류] `e3a07: movb $0x0,0x48(%rbx)`
};

/// Mapper 파라미터가 **아닌** 원본 실측값들 — 이 구조체 밖 계층에서 쓰인다. 이식 시 잊지 말 것.
namespace seer_runtime
{
/// 출력 맵 해상도 (m). `SlaMapping::run()` 이 `MapConfigData::resolution` 에 넣는 리터럴
///   `.rodata:0x1033e0` high lane = `0x3F947AE140000000` = `(double)0.02f`.
///   출력 시 `roundTo(..., 3)` 을 거쳐 0.02 로 나간다(SlaMapping.cpp:155). 실측 `.smap` 헤더도 0.02.
constexpr double kOutputMapResolutionM = 0.02;

/// `LaserRangeFinder::SetRangeThreshold` 에 들어가는 값 (m). **30.0 고정**이며
///   `Message_MapLog.laser_range_max`(실측 40.0)가 아니다 — 생성자가 넣은 laser_range_max 를
///   `run()` 이 `.rodata:0x1033d0` high lane = 30.0 으로 덮는다(SlaMapping.cpp:92 → KartoSLAM.cpp:121).
constexpr double kLaserRangeThresholdM = 30.0;

/// 반사강도 임계. `70495: mov %rax,0x38(%rsi)`, `0x4062C00000000000` = **150.0** (SlaMapping.cpp:91).
///   빔별 이진화에 쓰인다 — `RssiThres < rssi[i]` 이면 100.0, 아니면 0.0 (KartoSLAM.cpp:112-115).
///   교차 확인: 위치추정 쪽 `robot.param` 의 `MCLoc.ReflectorRSSI` 도 150.0.
constexpr double kRssiThreshold = 150.0;
} // namespace seer_runtime

/// `mapper` 에 Seer 파라미터 29개를 **전량 명시 설정**한다.
///
/// 상류 기본값과 같은 항목도 생략하지 않는다 — 벤더링 판본이 바뀌면 조용히 달라지기 때문이다
/// (2026-08-08 리뷰 Medium: 이전 구현은 4개를 설정하지 않아 상류 기본값에 의존했다).
///
/// @param mapper 대상 Mapper. `nullptr` 이면 아무 것도 하지 않는다.
/// @param p      적용할 파라미터. 기본값 = 원본 배포값.
void applySeerParams(karto::Mapper *mapper, const SeerMapperParams &p = {});

} // namespace slam_karto_core

#endif // SLAM_KARTO_CORE_SEER_MAPPER_CONFIG_HPP
