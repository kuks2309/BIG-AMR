// replay_ours — 원본 Seer 로그(.rawmap → JSONL)를 **우리 이식본** `slam_karto_core` 로 재생하고,
//               원본 `.so` 직접 구동 오라클과 대조 가능한 규격으로 결과를 낸다.
//
// 대조 상대: 원본 `libSlaMapping.so` 를 직접 돌리는 오라클(별도 작업). 두 출력의 키 순서·부동소수 표기가
//   바이트 단위로 같아야 `compare.py` 가 의미 있는 차이만 보고한다.
//
// 입력: `Tools/seer_rawmap/rawmap_to_jsonl.py` 의 산출물
//   - `<log>.jsonl`            : 한 줄 = 한 스캔 `{"odo":[x,y,w],"dist":[...],"angle":[...],"rssi":[...],"t":s}`
//   - `<log>.jsonl.meta.json`  : 파일 단위 상수(라이다 장착 포즈·각도 step·range max·스키마 판정)
//
// 출력(모두 `--out-dir` 아래):
//   - `ours_out.jsonl`    : 스캔별 1줄 + 마지막 summary 1줄 (규격은 README 참조)
//   - `ours_points.jsonl` : 장애물 점군 `[x,y]` 한 줄씩, **스캔 순서 → 빔 순서**
//   - `ours_rssi.jsonl`   : 반사판 점군 `[x,y]` (규격 외 보조 산출 — `num_rssi` 가 어긋날 때 들여다볼 자료)
//   - `ours_params.json`  : 실제로 적용된 파라미터 전량 (설정 차이와 알고리즘 차이를 가르는 근거)
//
// ⚠ 함정 3가지 (모두 실측 근거가 있다):
//   ① `laser_pos_z`(rawmap 헤더 field 3)는 **높이가 아니라 설치 yaw** 다
//      (References/seer/slam_mapping/proto/message_map.proto:44, 디코더 주석 rawmap_decode.py:23,341-345,361-374).
//      높이로 읽으면 라이다 자세가 통째로 틀어진다. 여기서는 meta 의 `laser_install_yaw_rad` 를 쓴다
//      (그 값은 디코더가 field 11 우선 → field 3 폴백으로 이미 해소해 둔 값이다).
//   ② `max_range` 는 헤더의 `laser_range_max`(실측 40.0)가 **아니라 30.0** 이다 —
//      원본 `SetRangeThreshold` 에 들어가는 값(slam_karto_core/seer_mapper_config.hpp:105-109
//      `seer_runtime::kLaserRangeThresholdM`).
//   ③ `SeerMapperParams` 는 손대지 않는다 — 기본값이 이미 원본 디스어셈블 실측값이다.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "slam_karto_core/seer_mapper_config.hpp"
#include "slam_karto_core/seer_slam_mapper.hpp"
#include "slam_karto_core/types.hpp"

#include "json_min.hpp"
#include "sha256.hpp"

namespace
{

/// 부동소수 출력 서식 — **17자리 왕복 무손실**. 반올림하면 오라클 대조가 무의미해진다.
const char *const kFloatFormat = "%.17g";

/// `%.17g` 한 개가 절대 넘지 않는 버퍼 길이 (부호+24자리+지수 여유).
constexpr int kFloatBufferBytes = 64;

/// g2o LM 반복 상한. 원본 실측값 50 (`optimize(50,false)`, slam_karto_core/g2o_solver.hpp:90-91).
/// 명시적으로 설정해야 `ours_params.json` 에 적는 값과 실제 적용값이 반드시 일치한다.
constexpr int kSeerG2oMaxIterations = 50;

/// "각도 격자 대체가 값을 실제로 바꿨다"고 셀 기준 편차 (rad).
/// `SeerSlamMapper` 의 균일성 허용치(1e-4 rad, seer_slam_mapper.cpp:21-24)와 같은 눈금을 쓴다 —
/// 그보다 작은 편차는 부동소수 잡음이고, 그보다 크면 원본과 우리의 각도가 실제로 달랐다는 뜻이다.
constexpr double kAngleGridReportThresholdRad = 1e-4;

/// meta 사이드카 파일명 접미사 (`rawmap_to_jsonl.py:35 META_SUFFIX` 와 같아야 한다).
const char *const kMetaSuffix = ".meta.json";

/// 종료 코드.
constexpr int kExitOk = 0;
constexpr int kExitFailure = 1;

/// 한 `double` 을 무손실 표기 문자열로.
///
/// @param v 값.
/// @return `%.17g` 표기 (예: `-2.2689235751201808`). 단위는 호출자 문맥을 따른다.
std::string f17(double v)
{
    char buf[kFloatBufferBytes];
    std::snprintf(buf, sizeof(buf), kFloatFormat, v);
    return std::string(buf);
}

/// JSON 문자열 리터럴로 이스케이프한다(따옴표 포함).
std::string jsonString(const std::string &s)
{
    std::string out;
    out.reserve(s.size() + 2);
    out.push_back('"');
    for (const char c : s)
    {
        switch (c)
        {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            out.push_back(c);
        }
    }
    out.push_back('"');
    return out;
}

/// 파일 전체를 문자열로 읽는다.
///
/// @param path  파일 경로.
/// @param out   성공 시 내용.
/// @return 읽기 성공 여부.
bool readFile(const std::string &path, std::string *out)
{
    std::ifstream in(path, std::ios::binary);
    if (!in)
    {
        return false;
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    *out = ss.str();
    return true;
}

/// meta 사이드카에서 double 필드를 꺼낸다. 없거나 수치가 아니면 실패.
bool metaNumber(const json_min::Value &meta, const std::string &key, double *out,
                std::string *error)
{
    const json_min::Value *v = meta.find(key);
    if (v == nullptr || !v->isNumber())
    {
        *error = "meta 에 수치 필드 '" + key + "' 가 없다";
        return false;
    }
    *out = v->asNumber(key);
    return true;
}

/// 빔 각도 배열을 어떻게 다룰지.
enum class AngleMode
{
    /// 로그의 `angle` 배열을 **그대로** 넘긴다 (기본값, 원본 충실).
    kAsIs,
    /// `min_angle + i * angular_resolution` 격자로 **대체**한다 (진단용 — 원본에서 멀어진다).
    ///
    /// 근거: Karto 는 스캔의 점 좌표를 계산할 때 per-beam 각도 배열을 **쓰지 않는다** —
    ///   `LocalizedRangeScan` 생성자 입력은 거리 배열뿐이고, `Update()` 가
    ///   `angle = scanPose.GetHeading() + minimumAngle + beamNum * angularResolution` 로 각도를 만든다
    ///   (third_party/open_karto/include/open_karto/Karto.h:5399, 5409).
    ///   즉 원본은 각도 배열의 비균일을 **무시**한다. 우리 코어의 균일성 검증(Karto 전제를 지키려는
    ///   방어)이 원본보다 엄격해, 그대로 두면 원본이 처리한 스캔을 우리만 버려 대조가 성립하지 않는다.
    ///   실측: robokit_2023-08-10_05-41-41 의 213 스캔 중 **90개**가 균일성 위반이다.
    /// 이 모드에서 바뀌는 것은 (a) 검증 통과 여부와 (b) rssi 끝점 계산에 쓰이는 각도뿐이며,
    /// 둘 다 원본과 같은 격자를 쓰게 만드는 방향이다. 장애물 점군 계산에는 애초에 영향이 없다.
    kUniformGrid,
};

/// 명령줄 설정.
struct Options
{
    std::string log_path;                 ///< 입력 JSONL 경로
    std::string meta_path;                ///< meta 사이드카 경로 (빈 값이면 log_path + kMetaSuffix)
    std::string out_dir;                  ///< 출력 디렉터리 (미리 존재해야 한다)
    long limit = -1;                      ///< 처리할 최대 레코드 수 (음수 = 전부)
    int g2o_iterations = kSeerG2oMaxIterations; ///< g2o LM 반복 상한
    /// rssi 임계. 기본값은 원본 실측 150.0 (`seer_runtime::kRssiThreshold`).
    double rssi_threshold = slam_karto_core::seer_runtime::kRssiThreshold;
    /// 라이다 최소 유효 거리 (m). 기본값은 `LaserGeometry` 의 기본값을 그대로 쓴다.
    double min_range = slam_karto_core::LaserGeometry{}.min_range;
    /// 라이다 최대 유효 거리 (m). 기본값 = 원본 `SetRangeThreshold` 실측 30.0.
    double max_range = slam_karto_core::seer_runtime::kLaserRangeThresholdM;
    /// 빔 각도 처리 방식. **기본은 `as-is`** — 로그의 실측 각도를 그대로 넘긴다.
    ///   Seer 의 Karto 는 per-beam 각도 배열을 쓰고, 동봉본에도 패치로 같은 경로를 넣었다
    ///   (third_party/patches/0001-use-measured-per-beam-angles.patch). 격자로 대체하면 원본에서 멀어진다.
    AngleMode angle_mode = AngleMode::kAsIs;
};

/// `AngleMode` 의 문자열 이름 (CLI 값 및 `ours_params.json` 기록용).
const char *angleModeName(AngleMode m)
{
    return m == AngleMode::kAsIs ? "as-is" : "uniform";
}

void printUsage(const char *argv0)
{
    std::cerr
        << "사용법: " << argv0 << " --log <log.jsonl> --out-dir <DIR> [옵션]\n"
        << "  --log PATH            rawmap_to_jsonl.py 가 낸 JSONL (필수)\n"
        << "  --out-dir DIR         출력 디렉터리 (필수, 미리 만들어 둘 것)\n"
        << "  --meta PATH           meta 사이드카 (기본: <log>" << kMetaSuffix << ")\n"
        << "  --limit N             앞의 N개 레코드만 재생 (기본: 전부)\n"
        << "  --g2o-iterations N    g2o LM 반복 상한 (기본: " << kSeerG2oMaxIterations
        << ", 원본 실측)\n"
        << "  --rssi-threshold V    반사판 판정 임계 (기본: "
        << slam_karto_core::seer_runtime::kRssiThreshold << ", 원본 실측)\n"
        << "  --min-range M         라이다 최소 거리 m (기본: "
        << slam_karto_core::LaserGeometry{}.min_range << ")\n"
        << "  --max-range M         라이다 최대 거리 m (기본: "
        << slam_karto_core::seer_runtime::kLaserRangeThresholdM << ", 원본 실측)\n"
        << "  --angle-mode MODE     uniform | as-is (기본: uniform)\n"
        << "                        uniform: 빔 각도를 min_angle + i*step 격자로 대체 — 원본 Karto 와 동일.\n"
        << "                        as-is  : 로그의 각도 배열을 그대로 사용(균일성 검증에 걸릴 수 있다).\n";
}

/// 명령줄을 해석한다. 실패 시 사유를 표준오류에 적고 false.
bool parseArgs(int argc, char **argv, Options *opt)
{
    for (int i = 1; i < argc; ++i)
    {
        const std::string a = argv[i];
        const bool has_next = (i + 1) < argc;
        auto next = [&]() { return std::string(argv[++i]); };

        if (a == "--help" || a == "-h")
        {
            printUsage(argv[0]);
            return false;
        }
        if (!has_next)
        {
            std::cerr << "error: " << a << " 에 값이 없다\n";
            return false;
        }
        if (a == "--log")
        {
            opt->log_path = next();
        }
        else if (a == "--meta")
        {
            opt->meta_path = next();
        }
        else if (a == "--out-dir")
        {
            opt->out_dir = next();
        }
        else if (a == "--limit")
        {
            opt->limit = std::strtol(next().c_str(), nullptr, 10);
        }
        else if (a == "--g2o-iterations")
        {
            opt->g2o_iterations = static_cast<int>(std::strtol(next().c_str(), nullptr, 10));
        }
        else if (a == "--rssi-threshold")
        {
            opt->rssi_threshold = std::strtod(next().c_str(), nullptr);
        }
        else if (a == "--min-range")
        {
            opt->min_range = std::strtod(next().c_str(), nullptr);
        }
        else if (a == "--max-range")
        {
            opt->max_range = std::strtod(next().c_str(), nullptr);
        }
        else if (a == "--angle-mode")
        {
            const std::string mode = next();
            if (mode == "uniform")
            {
                opt->angle_mode = AngleMode::kUniformGrid;
            }
            else if (mode == "as-is")
            {
                opt->angle_mode = AngleMode::kAsIs;
            }
            else
            {
                std::cerr << "error: --angle-mode 는 uniform 또는 as-is (받은 값: " << mode << ")\n";
                return false;
            }
        }
        else
        {
            std::cerr << "error: 알 수 없는 인자 " << a << "\n";
            return false;
        }
    }
    if (opt->log_path.empty() || opt->out_dir.empty())
    {
        std::cerr << "error: --log 와 --out-dir 는 필수다\n";
        printUsage(argv[0]);
        return false;
    }
    if (opt->meta_path.empty())
    {
        opt->meta_path = opt->log_path + kMetaSuffix;
    }
    return true;
}

/// 적용된 파라미터 전량을 JSON 으로 적는다 — "설정이 달랐나 알고리즘이 달랐나"를 먼저 가르기 위한 것.
///
/// @param path   출력 경로.
/// @param p      실제로 `SeerSlamMapper` 에 넣은 Mapper 파라미터.
/// @param g      실제로 `processRecord` 에 넘긴 라이다 기하.
/// @param opt    실행 설정(rssi 임계·g2o 반복 수 등).
/// @param meta_source meta 사이드카가 가리키는 원본 rawmap 파일명.
/// @return 쓰기 성공 여부.
bool writeParams(const std::string &path, const slam_karto_core::SeerMapperParams &p,
                 const slam_karto_core::LaserGeometry &g, const Options &opt,
                 const std::string &meta_source)
{
    std::ofstream out(path, std::ios::binary);
    if (!out)
    {
        return false;
    }
    out << "{\n";
    out << "  \"impl\": \"ours/slam_karto_core\",\n";
    out << "  \"source_basename\": " << jsonString(meta_source) << ",\n";
    out << "  \"log_jsonl\": " << jsonString(opt.log_path) << ",\n";

    out << "  \"mapper_params\": {\n";
    // 순서는 seer_mapper_config.hpp 의 선언 순서를 따른다(대조 시 눈으로 짚기 쉽게).
    out << "    \"minimum_travel_distance\": " << f17(p.minimum_travel_distance) << ",\n";
    out << "    \"minimum_travel_heading\": " << f17(p.minimum_travel_heading) << ",\n";
    out << "    \"minimum_time_interval\": " << f17(p.minimum_time_interval) << ",\n";
    out << "    \"scan_buffer_size\": " << p.scan_buffer_size << ",\n";
    out << "    \"loop_search_maximum_distance\": " << f17(p.loop_search_maximum_distance) << ",\n";
    out << "    \"loop_match_minimum_response_coarse\": "
        << f17(p.loop_match_minimum_response_coarse) << ",\n";
    out << "    \"loop_match_minimum_response_fine\": " << f17(p.loop_match_minimum_response_fine)
        << ",\n";
    out << "    \"loop_search_space_dimension\": " << f17(p.loop_search_space_dimension) << ",\n";
    out << "    \"scan_buffer_maximum_scan_distance\": "
        << f17(p.scan_buffer_maximum_scan_distance) << ",\n";
    out << "    \"loop_match_minimum_chain_size\": " << p.loop_match_minimum_chain_size << ",\n";
    out << "    \"loop_match_maximum_variance_coarse\": "
        << f17(p.loop_match_maximum_variance_coarse) << ",\n";
    out << "    \"correlation_search_space_dimension\": "
        << f17(p.correlation_search_space_dimension) << ",\n";
    out << "    \"correlation_search_space_resolution\": "
        << f17(p.correlation_search_space_resolution) << ",\n";
    out << "    \"correlation_search_space_smear_deviation\": "
        << f17(p.correlation_search_space_smear_deviation) << ",\n";
    out << "    \"link_match_minimum_response_fine\": " << f17(p.link_match_minimum_response_fine)
        << ",\n";
    out << "    \"link_scan_maximum_distance\": " << f17(p.link_scan_maximum_distance) << ",\n";
    out << "    \"distance_variance_penalty\": " << f17(p.distance_variance_penalty) << ",\n";
    out << "    \"angle_variance_penalty\": " << f17(p.angle_variance_penalty) << ",\n";
    out << "    \"coarse_search_angle_offset\": " << f17(p.coarse_search_angle_offset) << ",\n";
    out << "    \"coarse_angle_resolution\": " << f17(p.coarse_angle_resolution) << ",\n";
    out << "    \"fine_search_angle_offset\": " << f17(p.fine_search_angle_offset) << ",\n";
    out << "    \"loop_search_space_resolution\": " << f17(p.loop_search_space_resolution) << ",\n";
    out << "    \"loop_search_space_smear_deviation\": " << f17(p.loop_search_space_smear_deviation)
        << ",\n";
    out << "    \"minimum_angle_penalty\": " << f17(p.minimum_angle_penalty) << ",\n";
    out << "    \"minimum_distance_penalty\": " << f17(p.minimum_distance_penalty) << ",\n";
    out << "    \"do_loop_closing\": " << (p.do_loop_closing ? "true" : "false") << ",\n";
    out << "    \"use_scan_matching\": " << (p.use_scan_matching ? "true" : "false") << ",\n";
    out << "    \"use_scan_barycenter\": " << (p.use_scan_barycenter ? "true" : "false") << ",\n";
    out << "    \"use_response_expansion\": " << (p.use_response_expansion ? "true" : "false")
        << "\n";
    out << "  },\n";

    out << "  \"laser_geometry\": {\n";
    out << "    \"min_angle_rad\": " << f17(g.min_angle) << ",\n";
    out << "    \"angular_resolution_rad\": " << f17(g.angular_resolution) << ",\n";
    out << "    \"min_range_m\": " << f17(g.min_range) << ",\n";
    out << "    \"max_range_m\": " << f17(g.max_range) << ",\n";
    out << "    \"offset_x_m\": " << f17(g.offset_x) << ",\n";
    out << "    \"offset_y_m\": " << f17(g.offset_y) << ",\n";
    out << "    \"offset_yaw_rad\": " << f17(g.offset_yaw) << "\n";
    out << "  },\n";

    out << "  \"runtime\": {\n";
    out << "    \"rssi_threshold\": " << f17(opt.rssi_threshold) << ",\n";
    out << "    \"g2o_max_iterations\": " << opt.g2o_iterations << ",\n";
    out << "    \"angle_mode\": " << jsonString(angleModeName(opt.angle_mode)) << ",\n";
    out << "    \"output_map_resolution_m\": "
        << f17(slam_karto_core::seer_runtime::kOutputMapResolutionM) << "\n";
    out << "  }\n";
    out << "}\n";
    return out.good();
}

} // namespace

int main(int argc, char **argv)
{
    Options opt;
    if (!parseArgs(argc, argv, &opt))
    {
        return kExitFailure;
    }

    // ── meta 사이드카 ────────────────────────────────────────────────────────
    std::string meta_text;
    if (!readFile(opt.meta_path, &meta_text))
    {
        std::cerr << "error: meta 를 읽지 못했다: " << opt.meta_path << "\n";
        return kExitFailure;
    }
    json_min::Value meta;
    try
    {
        meta = json_min::parse(meta_text);
    }
    catch (const json_min::ParseError &e)
    {
        std::cerr << "error: meta 파싱 실패: " << e.what() << "\n";
        return kExitFailure;
    }

    std::string error;
    double laser_x = 0.0;
    double laser_y = 0.0;
    double laser_yaw = 0.0;
    double laser_step = 0.0;
    // ⚠ 함정 ①: yaw 는 `laser_install_yaw_rad` 다. `laser_install_height_m` 을 쓰면 안 된다.
    if (!metaNumber(meta, "laser_pos_x_m", &laser_x, &error) ||
        !metaNumber(meta, "laser_pos_y_m", &laser_y, &error) ||
        !metaNumber(meta, "laser_install_yaw_rad", &laser_yaw, &error) ||
        !metaNumber(meta, "laser_step_rad", &laser_step, &error))
    {
        std::cerr << "error: " << error << "\n";
        return kExitFailure;
    }
    std::string meta_source;
    if (const json_min::Value *v = meta.find("source_basename"))
    {
        if (v->isString())
        {
            meta_source = v->asString("source_basename");
        }
    }

    // ── 입력 JSONL ───────────────────────────────────────────────────────────
    std::ifstream log_in(opt.log_path, std::ios::binary);
    if (!log_in)
    {
        std::cerr << "error: 로그를 열지 못했다: " << opt.log_path << "\n";
        return kExitFailure;
    }

    slam_karto_core::SeerMapperParams params; // ⚠ 함정 ③: 기본값 = 원본 실측값. 손대지 않는다.
    slam_karto_core::SeerSlamMapper mapper(params);
    mapper.setRssiThreshold(opt.rssi_threshold);
    mapper.setMaxIterations(opt.g2o_iterations);

    slam_karto_core::LaserGeometry geometry;
    geometry.angular_resolution = laser_step;
    geometry.min_range = opt.min_range;
    geometry.max_range = opt.max_range; // ⚠ 함정 ②: 30.0 (헤더의 40.0 이 아니다)
    geometry.offset_x = laser_x;
    geometry.offset_y = laser_y;
    geometry.offset_yaw = laser_yaw;
    bool min_angle_fixed = false; // 첫 레코드의 angle[0] 로 확정한다

    std::vector<std::string> scan_lines;
    std::string line;
    long index = 0;
    long added_count = 0;
    long gate_rejected = 0;
    long invalid_input = 0;
    /// 격자 대체가 실제로 값을 바꾼 레코드 수와 그 최대 편차 (rad) — 조용한 데이터 변경을 막는 계측.
    long angle_grid_replaced = 0;
    double angle_grid_max_deviation = 0.0;

    while (std::getline(log_in, line))
    {
        if (opt.limit >= 0 && index >= opt.limit)
        {
            break;
        }
        if (line.empty())
        {
            continue;
        }

        json_min::Value rec;
        std::vector<double> odo;
        std::vector<double> dist;
        std::vector<double> angle;
        std::vector<double> rssi;
        try
        {
            rec = json_min::parse(line);
            const json_min::Value *v_odo = rec.find("odo");
            const json_min::Value *v_dist = rec.find("dist");
            const json_min::Value *v_angle = rec.find("angle");
            const json_min::Value *v_rssi = rec.find("rssi");
            if (v_odo == nullptr || v_dist == nullptr || v_angle == nullptr)
            {
                throw json_min::ParseError("레코드에 odo/dist/angle 이 없다");
            }
            odo = v_odo->asNumberVector("odo");
            dist = v_dist->asNumberVector("dist");
            angle = v_angle->asNumberVector("angle");
            if (v_rssi != nullptr && v_rssi->isArray())
            {
                rssi = v_rssi->asNumberVector("rssi");
            }
        }
        catch (const json_min::ParseError &e)
        {
            std::cerr << "error: 레코드 " << index << " 파싱 실패: " << e.what() << "\n";
            return kExitFailure;
        }

        constexpr std::size_t kOdoFields = 3; // x, y, w
        if (odo.size() != kOdoFields)
        {
            std::cerr << "error: 레코드 " << index << " 의 odo 길이가 " << odo.size()
                      << " 다 (3 이어야 한다)\n";
            return kExitFailure;
        }

        if (!min_angle_fixed && !angle.empty())
        {
            geometry.min_angle = angle.front(); // 첫 빔 각도 = min_angle
            min_angle_fixed = true;
        }

        // 각도 격자 대체 — 원본 Karto 와 같은 각도를 쓰게 만든다(AngleMode 주석의 근거 참조).
        if (opt.angle_mode == AngleMode::kUniformGrid)
        {
            double max_deviation = 0.0;
            for (std::size_t i = 0; i < angle.size(); ++i)
            {
                const double grid =
                    geometry.min_angle + static_cast<double>(i) * geometry.angular_resolution;
                max_deviation = std::max(max_deviation, std::fabs(angle[i] - grid));
                angle[i] = grid;
            }
            if (max_deviation > angle_grid_max_deviation)
            {
                angle_grid_max_deviation = max_deviation;
            }
            if (max_deviation > kAngleGridReportThresholdRad)
            {
                ++angle_grid_replaced;
            }
        }

        slam_karto_core::MapLogRecord log_rec;
        log_rec.odo_x = odo[0];
        log_rec.odo_y = odo[1];
        log_rec.odo_w = odo[2];
        log_rec.beam_dist = std::move(dist);
        log_rec.beam_angle = std::move(angle);
        log_rec.beam_rssi = std::move(rssi);

        const slam_karto_core::ProcessResult result = mapper.processRecord(log_rec, geometry);
        const bool added = (result == slam_karto_core::ProcessResult::kAdded);
        if (added)
        {
            ++added_count;
        }
        else if (result == slam_karto_core::ProcessResult::kGateRejected)
        {
            ++gate_rejected;
        }
        else
        {
            ++invalid_input;
            std::cerr << "warn: 레코드 " << index << " 입력 불량: " << mapper.lastError() << "\n";
        }

        const slam_karto_core::Pose2D &corrected = mapper.lastCorrectedPose();
        std::string out_line = "{\"type\":\"scan\",\"idx\":";
        out_line += std::to_string(index);
        out_line += ",\"added\":";
        out_line += added ? "true" : "false";
        out_line += ",\"unique_id\":";
        out_line += std::to_string(mapper.lastScanId());
        out_line += ",\"odom\":[";
        out_line += f17(log_rec.odo_x) + "," + f17(log_rec.odo_y) + "," + f17(log_rec.odo_w);
        out_line += "],\"corrected\":[";
        out_line += f17(corrected.x) + "," + f17(corrected.y) + "," + f17(corrected.theta);
        out_line += "]}";
        scan_lines.push_back(std::move(out_line));

        ++index;
    }

    if (index == 0)
    {
        std::cerr << "error: 재생할 레코드가 없다: " << opt.log_path << "\n";
        return kExitFailure;
    }

    // ── 맵 산출 ──────────────────────────────────────────────────────────────
    const slam_karto_core::MapResult map = mapper.buildMap();

    // 점군 파일을 쓰면서 **쓴 바이트 그대로** 해시한다 — 파일과 지문이 어긋날 여지를 없앤다.
    const std::string points_path = opt.out_dir + "/ours_points.jsonl";
    std::ofstream points_out(points_path, std::ios::binary);
    if (!points_out)
    {
        std::cerr << "error: 점군 파일을 열지 못했다: " << points_path << "\n";
        return kExitFailure;
    }
    sha256::Hasher hasher;
    for (const auto &pt : map.normal_pos_list)
    {
        const std::string s = "[" + f17(pt.first) + "," + f17(pt.second) + "]\n";
        points_out << s;
        hasher.update(s);
    }
    points_out.close();
    if (!points_out)
    {
        std::cerr << "error: 점군 파일 쓰기 실패: " << points_path << "\n";
        return kExitFailure;
    }
    const std::string points_sha = hasher.hexDigest();

    const std::string rssi_path = opt.out_dir + "/ours_rssi.jsonl";
    {
        std::ofstream rssi_out(rssi_path, std::ios::binary);
        if (!rssi_out)
        {
            std::cerr << "error: rssi 점군 파일을 열지 못했다: " << rssi_path << "\n";
            return kExitFailure;
        }
        for (const auto &pt : map.rssi_pos_list)
        {
            rssi_out << "[" << f17(pt.first) << "," << f17(pt.second) << "]\n";
        }
    }

    // ── 규격 출력 ────────────────────────────────────────────────────────────
    const std::string out_path = opt.out_dir + "/ours_out.jsonl";
    std::ofstream out(out_path, std::ios::binary);
    if (!out)
    {
        std::cerr << "error: 출력 파일을 열지 못했다: " << out_path << "\n";
        return kExitFailure;
    }
    for (const auto &l : scan_lines)
    {
        out << l << "\n";
    }
    out << "{\"type\":\"summary\",\"num_scans\":" << map.num_scans
        << ",\"num_points\":" << map.normal_pos_list.size()
        << ",\"num_rssi\":" << map.rssi_pos_list.size() << ",\"bbox\":[" << f17(map.min_x) << ","
        << f17(map.min_y) << "," << f17(map.max_x) << "," << f17(map.max_y) << "]"
        << ",\"points_sha256\":" << jsonString(points_sha) << "}\n";
    out.close();
    if (!out)
    {
        std::cerr << "error: 출력 파일 쓰기 실패: " << out_path << "\n";
        return kExitFailure;
    }

    const std::string params_path = opt.out_dir + "/ours_params.json";
    if (!writeParams(params_path, params, geometry, opt, meta_source))
    {
        std::cerr << "error: 파라미터 파일 쓰기 실패: " << params_path << "\n";
        return kExitFailure;
    }

    // ── 콘솔 요약 (대조 대상이 아니라 사람용) ────────────────────────────────
    const slam_karto_core::SolverStats &stats = mapper.solverStats();
    std::cerr << "angle_mode=" << angleModeName(opt.angle_mode)
              << " grid_replaced_records=" << angle_grid_replaced
              << " grid_max_deviation_rad=" << f17(angle_grid_max_deviation) << "\n"
              << "records=" << index << " added=" << added_count << " gate_rejected="
              << gate_rejected << " invalid=" << invalid_input << "\n"
              << "num_scans=" << map.num_scans << " num_points=" << map.normal_pos_list.size()
              << " num_rssi=" << map.rssi_pos_list.size() << "\n"
              << "bbox=[" << f17(map.min_x) << ", " << f17(map.min_y) << ", " << f17(map.max_x)
              << ", " << f17(map.max_y) << "]\n"
              << "points_sha256=" << points_sha << "\n"
              << "solver: compute_calls=" << stats.compute_calls
              << " nodes=" << stats.nodes_added << " edges=" << stats.edges_added
              << " edges_rejected=" << stats.edges_rejected
              << " singular_cov=" << stats.singular_covariances
              << " last_iterations=" << stats.last_iterations
              << " has_fixed_node=" << (stats.has_fixed_node ? "true" : "false") << "\n"
              << "wrote: " << out_path << ", " << points_path << ", " << rssi_path << ", "
              << params_path << "\n";
    return kExitOk;
}
