#!/usr/bin/env python3
"""slam_karto_core 회귀 시험의 **검출력**을 증명한다.

「시험을 추가했다」와 「시험이 검출한다」는 다른 명제다. 이 저장소는 그 차이로 사고를 겪었다
(docs/claude-mistake/2026-08-04-001 — 회귀를 붙였다고 보고했으나 배선을 지나가지 않아
한 줄을 지워도 111개가 전부 통과했다).

이 스크립트는 소스를 고의로 한 곳씩 망가뜨리고(=돌연변이) 시험을 돌려, **망가뜨렸는데 통과하면
검출 실패로 판정해 exit 1** 한다. 원본은 항상 복원한다.

사용:
    python3 test/mutation_check.py                # 전체
    python3 test/mutation_check.py --list         # 목록만
    python3 test/mutation_check.py --only anchor  # 하나만
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")

# (이름, 대상파일, 찾을 문자열, 바꿀 문자열, 무엇을 검증하는가)
MUTATIONS = [
    (
        "anchor",
        "src/g2o_solver.cpp",
        "        v->setFixed(true); // 맵 원점 앵커",
        "        // v->setFixed(true); // [MUTATED] 앵커 제거",
        "첫 노드 고정을 없애면 SE(2) 게이지 자유도가 남는다",
    ),
    (
        "clear-wipes-graph",
        "src/g2o_solver.cpp",
        "    // 상류 계약: 직전 corrections 만 버린다. 그래프는 건드리지 않는다 (헤더 주석 참조).\n    corrections_.clear();",
        "    corrections_.clear();\n    optimizer_->clear();  // [MUTATED] 상류 계약 위반",
        "Clear() 가 그래프를 비우면 루프클로저마다 포즈그래프가 파괴된다 "
        "(리뷰 Medium #7 의 '오답' 을 시험이 실제로 잡는지)",
    ),
    (
        "no-pose0-origin-shift",
        "src/seer_slam_mapper.cpp",
        "    pScan->SetCorrectedPose(karto::Pose2(rec.odo_x - pose0_.x, rec.odo_y - pose0_.y,\n"
        "                                         normalizeAngle(rec.odo_w - pose0_.theta)));",
        "    pScan->SetCorrectedPose(karto::Pose2(rec.odo_x, rec.odo_y, rec.odo_w));  // [MUTATED] 원점 이동 제거",
        "원본은 SetCorrectedPose(odom - mPose0) 로 시작 자세를 원점에 놓는다(KartoSLAM.cpp:41,123). "
        "빼먹으면 전 궤적이 평행이동·회전한다 — 오라클 대조 실측: 위치차 mean 0.108 → 2.65 m",
    ),
    (
        "seer-param-travel-distance",
        "include/slam_karto_core/seer_mapper_config.hpp",
        "    double minimum_travel_distance = 0.01;",
        "    double minimum_travel_distance = 0.2;  // [MUTATED] 생성자 값(런타임에 덮이는 값)",
        "이동 게이트를 원본 런타임값 0.01 → 생성자 값 0.2 로 되돌리면 노드 밀도가 20배 달라진다 "
        "(실측: 노드 601→301, 간선 720→355)",
    ),
    (
        "seer-param-rssi-threshold",
        "include/slam_karto_core/seer_mapper_config.hpp",
        "constexpr double kRssiThreshold = 150.0;",
        "constexpr double kRssiThreshold = 0.0;  // [MUTATED] 초기 이식본의 임의값",
        "RssiThres 를 원본 150.0 → 0.0 으로 되돌리면 모든 빔이 반사판으로 분류된다",
    ),
    (
        "seer-tuning-loop-distance",
        "include/slam_karto_core/seer_mapper_config.hpp",
        "    double loop_search_maximum_distance = 20.0;",
        "    double loop_search_maximum_distance = 4.0;  // [MUTATED] 상류 stock 값",
        "★ Seer 튜닝을 상류 stock 으로 되돌리면 그래프 규모가 달라진다 "
        "(실측: Compute 1→4회, 간선 355→333)",
    ),
    (
        "no-strict-angle-check",
        "src/seer_slam_mapper.cpp",
        "        if (strict_angle_uniformity_ && last_angle_deviation_ > kAngleUniformityToleranceRad)",
        "        if (false)  // [MUTATED] 엄격 모드 검사 무력화",
        "엄격 모드를 무력화하면 비균일 입력이 그 모드에서도 통과한다",
    ),
    (
        "no-geometry-consistency",
        "src/seer_slam_mapper.cpp",
        "    if (laser_ready_ && !sameGeometry(geometry_, laser))",
        "    if (false)  // [MUTATED] 기하 일관성 검사 무력화",
        "도중 LaserGeometry 변경이 조용히 통과한다",
    ),
    (
        "range-normalization-reintroduced",
        "src/seer_slam_mapper.cpp",
        "        readings.push_back(std::isfinite(d) ? d : kNonFiniteRangeSentinelFactor * geometry_.max_range);",
        "        readings.push_back(std::isfinite(d) && d >= geometry_.min_range && d < geometry_.max_range\n"
        "                               ? d\n"
        "                               : geometry_.max_range);  // [MUTATED] 옛 정규화 복원",
        "범위 밖 거리를 max_range 로 정규화하면 Karto 필터(InRange, 상한 포함)를 통과해 "
        "무반사 빔이 유효 히트로 둔갑한다 — 오라클 대조 실측: 점군 81,948 → 101,074",
    ),
    (
        "no-length-check",
        "src/seer_slam_mapper.cpp",
        "    if (rec.beam_dist.size() != rec.beam_angle.size())",
        "    if (false)  // [MUTATED] 길이 검사 무력화",
        "빔 배열 길이 불일치가 조용히 통과한다",
    ),
]

# 합성 궤적으로는 **도달할 수 없는** 돌연변이. 미검출이지만 공백이 아니다 —
# 시험 입력이 그 코드 경로를 밟지 않기 때문이다(미검출 ≠ 커버리지 부재).
# 실측 근거를 각 항목에 적는다. 이 목록은 exit code 를 좌우하지 않고 **경고로 출력**한다.
# 이것들을 실제로 잡으려면 원본 실 로그 재생이 필요하다
# (References/seer/slam_mapping/rawmaps/*.rawmap 26개, Tools/seer_rawmap/ 로 디코드).
UNREACHABLE = [
    (
        "seer-tuning-response-coarse",
        "include/slam_karto_core/seer_mapper_config.hpp",
        "    double loop_match_minimum_response_coarse = 0.35;",
        "    double loop_match_minimum_response_coarse = 0.8;  // [MUTATED] 상류 stock 값",
        "합성 스캔은 벽까지 정확히 레이캐스트한 값이라 상관 응답이 사실상 1.0 이다. "
        "coarse 게이트를 0.35 → 0.8 로 조여도 전부 통과한다 — 실측: 솔버 계측이 완전 동일. "
        "실측 잡음이 있어야 게이트가 의미를 갖는다.",
    ),
    (
        "information-identity",
        "src/g2o_solver.cpp",
        "            info(r, c) = k_inv(r, c);",
        "            info(r, c) = (r == c) ? 1.0 : 0.0;  // [MUTATED] 공분산 무시",
        "합성 데이터에서는 모든 제약이 거의 무모순이라 가중을 균일하게 줘도 해가 거의 같다. "
        "제약 간 충돌이 있는 실 데이터라야 가중치 차이가 결과로 나타난다.",
    ),
    (
        "block-ordering",
        "src/g2o_solver.cpp",
        "    linear_solver->setBlockOrdering(false);",
        "    linear_solver->setBlockOrdering(true);  // [MUTATED] 원본은 false",
        "CSparse fill-reducing 순서 전략만 바뀐다 — 해는 대수적으로 같고 반올림 차이만 생긴다. "
        "비트 대조 시험이 있어야 잡힌다(현재 없음).",
    ),
    (
        "max-iterations",
        "include/slam_karto_core/g2o_solver.hpp",
        "    int max_iterations_ = 50;",
        "    int max_iterations_ = 100;  // [MUTATED] 원본 실측은 50",
        "시험이 `setMaxIterations(50)` 을 명시 호출해 기본값을 덮는다. "
        "기본값 회귀를 잡으려면 명시 호출 없는 경로의 시험이 필요하다.",
    ),
]

BUILD_TIMEOUT_S = 600
TEST_TIMEOUT_S = 900


def run(cmd, timeout):
    """명령을 돌리고 (returncode, 합쳐진 출력) 을 준다."""
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def build_and_test():
    """빌드 후 시험 실행. (built, passed) 를 준다. 빌드 실패도 '검출' 로 친다."""
    rc, out = run(["cmake", "--build", BUILD, "-j6"], BUILD_TIMEOUT_S)
    if rc != 0:
        return False, False
    rc, out = run([os.path.join(BUILD, "test_slam_mapping")], TEST_TIMEOUT_S)
    return True, rc == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="돌연변이 목록만 출력")
    ap.add_argument("--only", help="이름이 일치하는 돌연변이 하나만 실행")
    args = ap.parse_args()

    if args.list:
        for name, path, _, _, why in MUTATIONS:
            print(f"{name:32s} {path:40s} {why}")
        return 0

    targets = [m for m in MUTATIONS if not args.only or m[0] == args.only]
    if not targets:
        print(f"[ERROR] '{args.only}' 와 일치하는 돌연변이가 없다")
        return 2

    if not os.path.isdir(BUILD):
        print(f"[ERROR] 빌드 디렉터리가 없다: {BUILD}\n"
              f"  먼저: cmake -B build -S . && cmake --build build -j6")
        return 2

    # 기준선 — 무돌연변이 상태에서 반드시 통과해야 한다.
    print("=== 기준선 (돌연변이 없음) ===")
    built, passed = build_and_test()
    if not (built and passed):
        print("[ERROR] 기준선이 통과하지 않는다 — 돌연변이 검사가 무의미하다")
        return 2
    print("[OK] 기준선 통과\n")

    undetected = []
    anchor_missing = []
    for name, rel, old, new, why in targets:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            original = f.read()
        if original.count(old) != 1:
            anchor_missing.append((name, rel, original.count(old)))
            print(f"[ANCHOR] {name:30s} 앵커 {original.count(old)}회 등장 (1이어야 함) — {rel}")
            continue

        backup = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        backup.write(original)
        backup.close()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(original.replace(old, new))
            built, passed = build_and_test()
            if not built:
                print(f"[검출] {name:30s} 빌드 실패로 검출 — {why}")
            elif passed:
                undetected.append((name, why))
                print(f"[미검출] {name:30s} 망가뜨렸는데 통과 — {why}")
            else:
                print(f"[검출] {name:30s} 시험 실패로 검출 — {why}")
        finally:
            shutil.copyfile(backup.name, path)
            os.unlink(backup.name)

    # 원본 복원 상태로 다시 빌드해 둔다(다음 작업이 돌연변이 바이너리를 쓰지 않도록).
    run(["cmake", "--build", BUILD, "-j6"], BUILD_TIMEOUT_S)

    if not args.only:
        print("\n=== 합성 데이터로 도달 불가한 돌연변이 (미검출 ≠ 커버리지 부재) ===")
        for name, _, _, _, why in UNREACHABLE:
            print(f"[한계] {name}\n        {why}")
        print("  → 이 항목들은 실 로그 재생(References/seer/slam_mapping/rawmaps/) 이 있어야 검증된다.")

    print()
    if anchor_missing:
        print(f"앵커 불일치 {len(anchor_missing)}건 — 소스가 바뀌었다. 돌연변이 정의를 갱신할 것:")
        for name, rel, n in anchor_missing:
            print(f"  - {name} ({rel}, {n}회)")
    if undetected:
        print(f"미검출 {len(undetected)}건 — 시험이 이 결함을 잡지 못한다:")
        for name, why in undetected:
            print(f"  - {name}: {why}")
    if anchor_missing or undetected:
        return 1
    print(f"전 {len(targets)}건 검출 — 시험은 실제로 결함을 잡는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
