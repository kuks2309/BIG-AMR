# slam_karto_core

Seer legacy `libSlaMapping.so` 의 **2D 그래프 SLAM 지도생성**을 리버스 엔지니어링으로 확정한 구조
(**Open Karto 프런트엔드 + g2o 백엔드**)대로 조립한 프레임워크-독립 C++17 모듈.

- 조사·리뷰: [`docs/code_review/seer-slam-mapping/2026-08-08.md`](../../../docs/code_review/seer-slam-mapping/2026-08-08.md)
- 함수표·전역표: [`docs/function_table.md`](docs/function_table.md)

## 원본이 무엇인지 (근거)

원본 `libSlaMapping.so`(rbk 3.4.5.20, md5 `a925b68b…`)는 `with debug_info, not stripped` 라 빌드 원본 경로가 남아 있다:

```
$ readelf --debug-dump=info libSlaMapping.so | grep -oaE "/root/workspace/[^ \")]*" | sort -u | grep -i karto
/root/workspace/3.4.5.20/plugins/SlaMapping/src/./karto/{Karto.cpp,Karto.h,KartoSLAM.cpp,Mapper.cpp,g2o_solver.cpp}
```

Cartographer·hector·gtsam·slam_toolbox·ICP/NDT/CSM 은 심볼·문자열 0건으로 배제됐다(조사 범위: `libSlaMapping.so` 단일 파일의 `strings -a` 전체 및 `nm -C` 전체 symtab).

**재구현이 아니라 채용이다.** 위치추정(`mcl2d_core`, 의존성 0 비트 재구현)과 달리, 거동 재현의 핵심은
스캔매처 비트복원이 아니라 **Seer 튜닝 파라미터 + G2OSolver 구성**을 그대로 적용하는 것이다.

### ★ Seer 튜닝 — 상류 원문과 대조 확인

상류 `third_party/open_karto/src/Mapper.cpp` 의 `Mapper::InitializeParameters()` 원문과 대조했다:

| 파라미터 | 상류 stock | Seer | 근거 등급 |
| --- | --- | --- | --- |
| `LoopSearchMaximumDistance` | 4.0 | **20.0** | [실측] 독립 2회 재현 |
| `LoopMatchMinimumResponseCoarse` | 0.8 | **0.35** | [실측] |
| `LoopMatchMinimumResponseFine` | 0.8 | **0.6** | [실측] |
| `LoopSearchSpaceDimension` | 8.0 | **6.0** | [실측] |
| `ScanBufferSize` | 70 | **100** | [실측] `e2136: movl $0x64,0x48(%r15)` |

나머지 23개는 상류와 같은 값으로 실측됐다. `applySeerParams` 는 **같은 값도 생략하지 않고 전량 명시 설정**한다 —
동봉 Karto 판본이 바뀌면 조용히 달라지기 때문이다.

**추출 실패 0건** — 28개 파라미터 전부 이름·타입·값을 확정했고, 3.4.5.20 과 3.4.8 판본의 같은 함수를
명령 스트림으로 대조해 **1,925개 중 차이 0건**을 확인했다.

### 컴파일 기본값이 아니라 **런타임 override** 인 것 3개 — 여기가 함정이다

`karto::Mapper::InitializeParameters()` 만 보면 틀린다. `SlaMapping::run()` 이 매 메시지마다
`MapConfigData` 를 리터럴로 덮어쓰고, `KartoSLAM::Process` 가 그중 2개를 Mapper 에 적용한다:

| 값 | 컴파일 기본값 | **실제 적용값** | 근거 |
| --- | --- | --- | --- |
| `MinimumTravelDistance` | 0.2 | **0.01 m** | `.rodata:0x1033d0` low = 0.01 → `ca9b1: call setParamMinimumTravelDistance` |
| `MinimumTravelHeading` | 0.174533 (10°) | **0.05 rad** | `.rodata:0x1033e0` low = 0.05 → `ca9c2: call setParamMinimumTravelHeading` |
| `RssiThres` | (초기화 안 됨) | **150.0** | `70495: mov %rax,0x38(%rsi)`, `0x4062C00000000000` |

⚠ **초기 이식본은 생성자 값 0.2 를 채택했다 — 노드 밀도가 20배 달랐다.**
라이브러리 전체에 `Mapper::setParam*` 호출은 위 **2개뿐**이므로, 나머지는 컴파일 기본값이 맞다.

Mapper 파라미터가 아닌 실측값 2개도 `seer_runtime` 네임스페이스에 박아 두었다 —
출력 맵 해상도 **0.02 m**, `LaserRangeFinder` range threshold **30.0 m**(`laser_range_max` 40.0 이 아니다).

## 구조

| 파일 | 내용 |
| --- | --- |
| `types.hpp` | `MapLogRecord`(입력, Seer `Message_MapLogData` 대응) · `MapResult`(출력, `Message_Map` 대응) · `ProcessResult` · `SolverStats` |
| `seer_mapper_config.*` | Seer 파라미터 29개 + `applySeerParams`. **값마다 근거 등급 주석**([실측]/[상류]/[선택]) + 런타임 override 3개 |
| `g2o_solver.*` | `G2OSolver : karto::ScanSolver`. `SparseOptimizer` + `LinearSolverCSparse<BlockSolverX::PoseMatrixType>` + `BlockSolverX` + LM. 첫 노드 fixed |
| `seer_slam_mapper.*` | 파사드. 입력 검증 → `LocalizedRangeScan` → `Mapper::Process` → 보정 포즈 점군 산출 |
| `third_party/open_karto/` | 상류 소스(커밋 `922db50`, LGPL-3.0) + **패치 1건**(per-beam 각도). 임의 수정 금지, 변경은 패치 파일로만 — [VENDORED.md](third_party/open_karto/VENDORED.md) |
| `third_party/patches/` | `0001-use-measured-per-beam-angles.patch` — Seer 포크가 per-beam 각도 배열을 쓰는 것을 재현. 역적용 확인 완료 |

### 왜 Karto 를 동봉하는가

- `ros-humble-open-karto` 가 **없다** — 이 장비 실측: `apt-cache policy ros-humble-open-karto` 출력 0줄,
  `apt-cache search --names-only karto` 출력 0줄.
- **LGPL-3.0 이 대응 소스 제공을 요구**한다. 동봉이 배포 조건에도 맞는다.
  → `karto_vendored` 를 **공유 라이브러리로 분리 빌드**한다(정적 링크 금지).
- `slam_toolbox` 의 `karto_sdk` 는 `ScanSolver::Configure(rclcpp::Node::SharedPtr)` 가 순수가상이라
  **프레임워크-독립 코어 원칙과 충돌**한다. 그래서 상류 open_karto 를 택했다.

g2o 는 apt 로 이미 있다 — `ros-humble-libg2o 2020.5.29-4jammy`, `/opt/ros/humble/lib/aarch64-linux-gnu/` 에 28개 `.so`.

## 빌드 / 검증 (이 장비 실측: aarch64 / gcc 11.4 / cmake 3.22 / Humble)

```bash
cd src/Navigation/slam_karto_core
cmake -B build -S . && cmake --build build -j6
ctest --test-dir build --output-on-failure
```

의존성이 없으면 **`FATAL_ERROR` 로 멈춘다**(옵트인 `-DSLAM_KARTO_ALLOW_MISSING_DEPS=ON` 으로만 건너뛴다).
조용한 미빌드는 "테스트 0개 통과"를 만들기 때문이다.

### g2o 링크 함정

`libg2o_types_slam2d.so` 는 `libg2o_opengl_helper.so` 를 `NEEDED` 로 갖는데 **자기 RUNPATH 가 없다**
(`readelf -d` 확인). DT_RUNPATH 는 전이되지 않으므로 우리 RUNPATH 로는 해석되지 않고
`error while loading shared libraries` 로 죽는다. `CMakeLists.txt` 가 `-Wl,--disable-new-dtags` 로
**DT_RPATH**(전이됨)를 내도록 해 두었다.

## 검증 현황

### ★ 원본 직접 구동 오라클과 대조 (2026-08-09) — 가장 강한 검증

원본 `libSlaMapping.so` 를 amap-server(x86_64)에서 `dlopen` 으로 직접 구동해
(rbk 플러그인 프레임워크 없이 `karto::` 심볼만 `dlsym`), **같은 실 로그**를 양쪽에 먹여 대조했다.

기준 입력: `robokit_2023-08-10_05-41-41.rawmap` (빔 521개 균일 단일 스윕, 스캔 213개, 실이동 7.6 m)

| 항목 | 결과 |
| --- | --- |
| 스캔 채택 판정 (`added`) | **213/213 완전 일치** (194 채택 / 19 게이트 거부) |
| 스캔 식별자 (`unique_id`) | **전부 일치** |
| 점군 개수 | **81,948 완전 일치** |
| 보정 포즈 위치차 | max **0.026 m** · mean **0.0084 m** · p50 **0.0084 m** |
| 보정 포즈 방위차 | max **0.0073 rad**(0.42°) · mean **0.0019 rad**(0.11°) |
| bbox 차 | 1~5 cm |
| 점 좌표 | 최초 상이가 3번째 줄, 차이 **2e-16**(ULP 수준) |

**비트 동일은 목표가 아니다** — 오라클은 x86-64/clang 원본, 우리는 aarch64/GCC 다.
아키텍처·libm·FMA 차이로 마지막 비트는 원리적으로 달라진다. 목표는 **수치 동등**이고 위가 그 결과다.

도구: `Tools/seer_rawmap/replay/` (`replay_ours` + `compare.py`).
설계 결정: [`docs/adr/2026-08-09-seer-karto-oracle-harness.md`](../../../docs/adr/2026-08-09-seer-karto-oracle-harness.md).

#### 대조가 잡아낸 이식본 결함 4건 (전부 반영)

| 결함 | 원본 실측 | 효과 |
| --- | --- | --- |
| `SetCorrectedPose(odom − mPose0)` 누락 | `mPose0` = 첫 레코드 오도, 시작 자세를 원점으로 (KartoSLAM.cpp:41,123) | 위치차 mean **2.65 → 0.108 m** |
| per-beam 각도 미사용 | Seer 포크는 실측 각도 배열을 쓴다 | 위치차 max **1.83 → 0.026 m** |
| 거리 정규화가 무반사를 유효 히트로 둔갑 | 원본은 원시값(9999.999) 그대로 넘겨 필터가 거른다 | 점군 **101,074 → 81,948** |
| `min_range` 0.05 | `SetMinimumRange(0.001)` 하드코딩 (KartoSLAM.cpp:32) | — |

### 합성 궤적 시험 (`ctest`)

```
[OK] 입력 검증 4종 (비균일 각도는 기본 허용 / 엄격 모드에서만 거부)
[OK] 무효 거리 정규화
궤적 630 스텝 → 그래프 노드 601개 (게이트로 29개 폐기)
맵: normal=216360, rssi=2404, 경계 x[-4.12,36.11] y[-4.10,26.19]
솔버: Compute 호출 1회, 노드 601, 간선 720, 기각 0, 직전 반복 22
[PASS] 전 검사 통과
```

맵 경계가 방 `[0,40]×[0,30]` 이 아니라 `[-4,36]×[-4,26]` 인 것은 정상이다 —
**첫 자세(pose0) 기준 원점 이동** 좌표계이기 때문이다(원본과 동일).

**검증 매크로는 `assert` 가 아니다.** 기본 빌드타입이 Release(`-DNDEBUG`)라 `assert` 는 사라진다 —
이 저장소는 그 사고를 이미 겪었다(`src/Navigation/README.md:74-76`). `test/check.hpp` 의 `CHECK` 를 쓴다.

### 검출력 — `test/mutation_check.py`

「시험을 추가했다」 ≠ 「시험이 검출한다」. 소스를 한 곳씩 망가뜨려 시험이 실제로 죽는지 확인한다:

```bash
python3 test/mutation_check.py          # 전체 (약 25분 — 노드 601개)
python3 test/mutation_check.py --list   # 목록만
```

**10/10 검출**. 오라클이 잡아준 결함 3건도 돌연변이로 잠갔다 —
`no-pose0-origin-shift` · `range-normalization-reintroduced` · `seer-param-rssi-threshold`.

⚠ 그 과정에서 **시험의 공백이 두 번 드러났다.**
① 반사판 점군을 `!empty()` 로만 단언했더니 `RssiThres` 를 0 으로 되돌려 전 빔이 반사판이 돼도 통과했다.
② 점군을 `map.valid` 로만 단언했더니 무반사 빔이 유효 히트로 섞여도 통과했다.
둘 다 **개수를 못박는 단언**으로 바꿔서야 잡혔다 — "비어 있지 않다"·"유효하다"는 검증이 아니다.

### ⚠ 합성 데이터로 **도달 불가**한 4건 (미검출 ≠ 커버리지 부재)

| 항목 | 왜 못 밟는가 (실측) |
| --- | --- |
| `seer-tuning-response-coarse` | 합성 스캔은 벽까지 정확히 레이캐스트한 값이라 상관 응답이 사실상 1.0. 게이트를 0.35 → 상류 0.8 로 조여도 **솔버 계측이 완전 동일** |
| `information-identity` | 제약이 거의 무모순이라 가중을 균일하게 줘도 해가 거의 같다 |
| `block-ordering` | CSparse 순서 전략만 바뀐다 — 해는 대수적으로 같고 반올림 차이만 생긴다 |
| `max-iterations` | 시험이 `setMaxIterations(50)` 을 명시 호출해 기본값을 덮는다 |

이것들은 **실 로그 재생 회귀**(`Tools/seer_rawmap/replay/`)를 ctest 에 붙여야 잡힌다 — debt-093.

## 원본 대조 — 자산은 확보됐다

RE 문서와 이전 구현본은 공통으로 "Seer 실 로그 확보 시 `.smap` 대조가 다음 단계"라며 합성 검증에 머물렀다.
그 로그가 원본 하드에 있었고, 회수 완료했다:

| 자산 | 수량 | 위치 |
| --- | --- | --- |
| `.rawmap` (원시 스캔+오도 로그) | 26개 / 55 MB | `References/seer/slam_mapping/rawmaps/` |
| `.smap` (완성 지도) | 15개 / 6.3 MB | `References/seer/slam_mapping/maps/` |
| `.proto` (스키마 정본) | 6개 / 659줄 | `References/seer/slam_mapping/proto/` |

`References/` 는 `.gitignore:12` 로 미추적이다. 디코더는 [`Tools/seer_rawmap/`](../../../Tools/seer_rawmap/).

## 알려진 격차 — 역어셈블로 정량화됨 (2026-08-08)

**Seer 의 Karto 는 "약간 고친 상류"가 아니다.** DWARF 라인테이블로 잰 원본 소스 규모:
`Mapper.cpp` **2,701줄 (상류 2,168 → +533, +24.6%)**, `Karto.h` **6,792줄 (상류 6,636 → +156)**.
무개조 상류를 동봉한 이상 아래가 그대로 격차다.

| # | 격차 | 근거 | 영향 |
| --- | --- | --- | --- |
| 1 | **RSSI 가 스캔매칭 응답에 관통 배선** — `ScanMatcher::m_pRssiGrid` 가 상시 할당·상시 스미어되고, 응답 계산이 전량 `GetResponseWithRssi` 로 대체됐다. 상류 `GetResponse` 는 **호출자 0건으로 사장**됐다 | `Create`@`0xdb48f/0xdb4b8` 2회 할당 · `AddScan`@`0xdddc8/0xdddeb` 2회 스미어 · `CorrelateScan`@`0xdc609/0xdc666` | **조건부.** `ΣvID > nPoints && nPoints < pointSize` 일 때만 RSSI 가중이 걸리고, 아니면 상류와 **수치 동일**. 활성 빈도는 불명 |
| 2 | **스캔 자료구조 3채널화** — `LaserRangeScan(name, range, angle, rssi)`. 각도까지 실측 배열로 보존한다 | `Karto.h:5025/5037`, 멤버 `m_pAngleReadings`·`m_pRssiReadings` | 비균일 각도 라이다에서 유의미 |
| 3 | **`doSubmapLoop` 3번째 bool** — `MatchScan`·`CorrelateScan`·`ComputeOffsets` 로 전파. `Mapper::Process` 경로에서만 `mLoopNotFind` 값이 들어간다 | `0xe4b01/0xe4b69 push %rbx`, `rbx ← Mapper+0x58` | 루프폐쇄 실패 시 매칭 동작이 바뀐다 |
| 4 | **점유격자 RSSI 레이어 + 카운터 8비트화** — `m_pCellRssi`, `RayTrace(+isRssiValid)`, `UpdateCell(kt_int8u,…)` (상류는 `kt_int32u`) | `0xd8a60`/`0xd8d20` | 255 포화 — 장시간 매핑에서 점유확률에 영향 |
| 5 | **후처리 미구현** — `OccupancyGrid` 0.02 m 래스터화, `HTLine`(Hough 벽각 보정)·`mapAngle`, `ComputeBoundingBox` 기반 다중 서브맵 저장 | `KartoSLAM::SaveMap`@`0xcce29` | 지도 정렬·저장 형태가 다르다 |
| 6 | **역방향 — 동봉 상류가 더 신형** | 상류엔 `m_pMinimumTimeInterval` 이 있고 Seer 에는 없다 | Seer 의 Karto 기반은 그 파라미터 도입 **이전** 버전이다 |

**동일 확인된 것** — `ComputePositionalCovariance`·`ComputeAngularCovariance` 는 줄 수·시그니처 완전 동일이고,
**Mapper 파라미터 27종에 Seer 가 추가한 튜너블은 0개**다. 즉 파라미터 집합 자체는 상류와 같고 **값만 맞추면 되는 문제**로 좁혀진다.

⚠ **이전 조사 단서의 절반은 오판이었다.** `doRefineMatch`·`doingFineMatch`·`coarseSearchResolution`·
`candidateScanNum`·`frontScanPose`·`accumulatedVarianceXX`·`doSmear` 는 **상류에 그대로 있는 지역변수**다
(`debug_info` 빌드라 지역변수 이름까지 DWARF 에 실려 "신규 심볼"로 오인됐다). 상류 소스에 직접 grep 해 확인했다.

## 원본 지도 생성 주체는 미확정

실기 로그에서 매핑 명령 `6100`/`6101` 은 `OnlineMapLogger` 로 라우팅되고 완성 `.smap` 은
PC 툴(Roboshop)이 만들어 `4010` 으로 업로드했다. 온보드 Karto+g2o 경로는 `[존재]` 이며
이 장비의 열람 범위에서 `[동작]` 근거는 얻지 못했다. 우리는 **알고리즘**을 재현한 것이고,
원본의 **지도 생산 경로**와 같다는 근거는 아직 없다(debt-094).
