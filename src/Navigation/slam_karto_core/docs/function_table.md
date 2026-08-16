# slam_karto_core — 함수표 / 전역변수표

코딩 SOP §2(계획 전 선독)·§6(후속 갱신)의 대상 표. 코드를 고치면 **이 표를 함께 갱신**한다.

동봉 `third_party/open_karto/` 는 상류 소스이므로 이 표의 대상이 아니다. 단 **패치 1건**이 적용돼 있다
(`third_party/patches/0001-use-measured-per-beam-angles.patch` — `LaserRangeScan` 에 실측 각도 배열 저장 +
`LocalizedRangeScan::Update()` 가 그 값 사용). 상세는 `third_party/open_karto/VENDORED.md`.

- 코드 버전: 2026-08-09 (원본 직접 구동 오라클 대조 반영본)
- 리뷰: [`docs/code_review/seer-slam-mapping/2026-08-08.md`](../../../../docs/code_review/seer-slam-mapping/2026-08-08.md)
- 오라클 설계: [`docs/adr/2026-08-09-seer-karto-oracle-harness.md`](../../../../docs/adr/2026-08-09-seer-karto-oracle-harness.md)

## 함수 리스트

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `G2OSolver::G2OSolver` | — | — | g2o 스택 조립(LinearSolver→BlockSolverX→LM) + **`setBlockOrdering(false)`**(원본 실측 `0xeb7cf`) | g2o_solver.cpp:38 |
| 2 | `G2OSolver::~G2OSolver` | — | — | `= default` | g2o_solver.cpp:53 |
| 3 | `G2OSolver::setMaxIterations` | `int n` | void | LM 반복 상한. 0 이하는 무시 | g2o_solver.cpp:55 |
| 4 | `G2OSolver::AddNode` | `karto::Vertex<LocalizedRangeScan>*` | void | `VertexSE2`(id=UniqueId, est=CorrectedPose) 추가. 첫 노드 `setFixed(true)`. 삽입 순서를 `vertex_order_` 에 보관 | g2o_solver.cpp:63 |
| 5 | `G2OSolver::AddConstraint` | `karto::Edge<LocalizedRangeScan>*` | void | `EdgeSE2` 추가. 정보행렬 = **`karto::Matrix3::InverseFast(inv, 1e-14)`**(원본과 동일 알고리즘). 특이해도 간선을 버리지 않고 계측만 | g2o_solver.cpp:99 |
| 6 | `G2OSolver::Compute` | — | void | 정점 ≥2 이면 `initializeOptimization` + `optimize`. corrections 를 **삽입 순서**로 수집(정렬 없음 — 원본과 동일) | g2o_solver.cpp:167 |
| 7 | `G2OSolver::GetCorrections` | — | `const IdPoseVector&` | 삽입 순서 corrections 반환 | g2o_solver.cpp:195 |
| 8 | `G2OSolver::Clear` | — | void | **상류 계약: corrections 만 버린다.** 그래프 불변 — `CorrectPoses()` 가 루프클로저마다 호출하므로 | g2o_solver.cpp:200 |
| 9 | `G2OSolver::Reset` | — | void | 세션 재시작 — 그래프·`vertex_order_` 소거 + `first_node_ = true` + 계측 초기화. Karto 는 호출하지 않는다 | g2o_solver.cpp:206 |
| 10 | `G2OSolver::stats` | — | `const SolverStats&` | 인라인 getter | g2o_solver.hpp:77 |
| 11 | `applySeerParams` | `karto::Mapper*`, `const SeerMapperParams&` | void | Karto setter **29회 전량 호출**(상류 기본값과 같아도 생략하지 않는다) | seer_mapper_config.cpp:8 |
| 12 | `normalizeAngle` (익명 ns) | `double a` | `double` | 각도를 (-pi, pi] 로. 원본이 `SetCorrectedPose` heading 에 적용 | seer_slam_mapper.cpp:39 |
| 13 | `nearlyEqual` (익명 ns) | `a, b, tol` | `bool` | 절대 오차 비교 | seer_slam_mapper.cpp:52 |
| 14 | `sameGeometry` (익명 ns) | `const LaserGeometry&` ×2 | `bool` | 기하 6필드 일치 판정(`angular_resolution` 제외 — 유도값) | seer_slam_mapper.cpp:57 |
| 15 | `SeerSlamMapper::SeerSlamMapper` | `const SeerMapperParams&` | — | Mapper/Dataset/G2OSolver 생성, `applySeerParams`, `SetScanSolver` | seer_slam_mapper.cpp:68 |
| 16 | `SeerSlamMapper::setMaxIterations` | `int n` | void | solver_ 로 위임 | seer_slam_mapper.cpp:84 |
| 17 | `SeerSlamMapper::solverStats` | — | `const SolverStats&` | 최적화 계측 노출 | seer_slam_mapper.cpp:89 |
| 18 | `SeerSlamMapper::validate` (private) | `const MapLogRecord&`, `const LaserGeometry&` | `bool` | 길이 일치 · 유한성 · range 구간 · 기하 일관성 검사. **각도 비균일은 관측만**(엄격 모드에서만 거부) | seer_slam_mapper.cpp:94 |
| 19 | `SeerSlamMapper::processRecord` | `const MapLogRecord&`, `const LaserGeometry&` | `ProcessResult` | 검증 → (첫 호출 시) LaserRangeFinder 구성 → **`pose0` 원점 이동** → per-beam 각도 전달 → `Mapper::Process` → rssi 끝점 적재 | seer_slam_mapper.cpp:177 |
| 20 | `SeerSlamMapper::buildMap` | — | `MapResult` | 전 스캔 보정포즈 점군(**`GetPointReadings(true)` 필터본**) + 경계 + rssi 월드변환 | seer_slam_mapper.cpp:318 |
| 21 | `SeerSlamMapper::setRssiThreshold` | `double t` | void | 인라인 setter. 기본 150.0(원본 실측) | seer_slam_mapper.hpp:85 |
| 22 | `SeerSlamMapper::numScans` | — | `int` | 인라인 getter | seer_slam_mapper.hpp:97 |
| 23 | `SeerSlamMapper::lastScanId` | — | `int` | 직전 추가 스캔의 Karto uniqueId (없으면 `kNoScanId`). **오라클 대조용** | seer_slam_mapper.hpp:109 |
| 24 | `SeerSlamMapper::lastCorrectedPose` | — | `const Pose2D&` | 직전 `Process` **직후**의 보정 포즈. 이후 `CorrectPoses` 가 과거 포즈를 덮기 전 값 | seer_slam_mapper.hpp:122 |
| 25 | `SeerSlamMapper::lastError` | — | `const std::string&` | 직전 `kInvalidInput` 사유 | seer_slam_mapper.hpp:128 |
| 26 | `SeerSlamMapper::setStrictAngleUniformity` | `bool` | void | 각도 비균일을 거부 사유로 쓸지. 기본 `false` = 원본 충실 | seer_slam_mapper.hpp:145 |
| 27 | `SeerSlamMapper::lastAngleDeviation` | — | `double` | 직전 레코드의 각도 간격 최대 편차 (rad) | seer_slam_mapper.hpp:151 |

`~SeerSlamMapper` 는 mapper_ → dataset_ → solver_ 순 명시 파괴(mapper 가 solver 를 참조).

### 시험 (test/)

| # | 함수 | 기능 | 위치 |
| --- | --- | --- | --- |
| T1 | `makeScan` | 사각방 벽 레이캐스트로 360빔 합성(rssi 기저 50 / 반사판 200 — 원본 실측 규모) | test_slam_mapping.cpp |
| T2 | `makeLaser` | 시험용 라이다 기하 | 〃 |
| T3 | `makeTruthPath` | 닫힌 사각 궤적 + 정지 구간(이동 게이트 검증용) | 〃 |
| T4 | `testInputValidation` | 길이 불일치·비유한 오도·기하 변경 거부 + **비균일 각도는 기본 허용/엄격 모드에서만 거부** | 〃 |
| T5 | `testRangeNormalization` | 무효 빔(0·NaN·inf·음수) 처리 + **점군 개수 단언**(무반사가 유효 히트로 섞이는 것 차단) | 〃 |
| T6 | `testMappingPipeline` | 게이트·루프클로저·앵커·특성값·경계·보정 단언 | 〃 |
| T7 | `main` | 3개 시험 실행 후 `CHECK_SUMMARY()` | 〃 |

`test/check.hpp` = NDEBUG 무관 매크로. `test/mutation_check.py` = 검출력 검사기(10/10 검출, 도달 불가 4건 명시).

## 전역 변수 / 모듈 상수

**가변 전역 상태 없음.** 상태는 전부 `SeerSlamMapper`·`G2OSolver` 멤버로 캡슐화돼 있다.

| # | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- |
| G1 | #19 | `kSensorName = "SeerLaser"` — Karto `SensorManager` 조회 키 **(상수)**, 익명 ns | seer_slam_mapper.cpp:19 |
| G2 | #18 | `kAngleUniformityToleranceRad = 1e-4` — **엄격 모드에서만** 거부 임계 **(상수)** | seer_slam_mapper.cpp:23 |
| G3 | #14 | `kGeometryMatchTolerance = 1e-9` **(상수)** | seer_slam_mapper.cpp:26 |
| G4 | #19 | `kFallbackAngularResolutionRad = M_PI/180` **(상수)** | seer_slam_mapper.cpp:29 |
| G5 | #18·#19 | `kMinBeamsToDeriveResolution = 2` **(상수)** | seer_slam_mapper.cpp:32 |
| G6 | #19 | `kNonFiniteRangeSentinelFactor = 2.0` — 비유한 거리를 임계 밖으로 밀어낸다. **유한값은 손대지 않는다**(정규화하면 무반사가 유효 히트로 둔갑) **(상수)** | seer_slam_mapper.cpp:36 |
| G7 | #5 | `kCovarianceInverseTolerance = 1e-14` — 원본 실측(`0xebe10`) **(상수)** | g2o_solver.cpp:34 |
| G8 | #1 | `using BlockSolver = g2o::BlockSolverX` **(타입 별칭)**, 익명 ns | g2o_solver.cpp:24 |
| G9 | #1 | `using LinearSolver = LinearSolverCSparse/LinearSolverEigen` — `SLAM_G2O_USE_CSPARSE` 분기 **(타입 별칭)** | g2o_solver.cpp:25-29 |
| G10 | 빌드 전역 | `SLAM_G2O_USE_CSPARSE` — CSparse 가용 시에만 부여 | CMakeLists.txt |
| G11 | #11 기본인자 | `SeerMapperParams` 29 필드 기본값 **(상수)**. 값마다 근거 등급 주석 | seer_mapper_config.hpp |
| G12 | 이식 참조 | `seer_runtime::{kOutputMapResolutionM 0.02, kLaserRangeThresholdM 30.0, kRssiThreshold 150.0}` — **Mapper 파라미터가 아닌** 원본 실측값 **(상수)** | seer_mapper_config.hpp |
| G13 | types.hpp | `kNoScanId = -1` — "스캔 식별자 없음" 표식 **(상수)** | types.hpp |

**필요성 평가**: 전부 상수 또는 타입 별칭이며 지역화·주입으로 대체할 실익이 없다. **불필요한 가변 전역 0건.**
