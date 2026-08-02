# Navigation — Seer 2D MCL 라이다 위치추정 (이식본)

Seer Robotics rbk 3.4.5.20 `libMCLoc.so`(2D Monte Carlo Localization 파티클필터 모드)를
리버스 엔지니어링해 재구현한 코드의 이식본.
원본 저장소: `amap-1:/home/amap/Project/Seer_Analysis` (이식 2026-07-28).

## 구성 (저장소 배치 규약 준수 — 루트 README '디렉토리 배치 규약' 참조)

| 경로 | 역할 | colcon |
| --- | --- | --- |
| `mcl2d_core/` | 프레임워크-독립 순수 C++17 코어 (의존성 0). MotionModel2D + ObservationField(Seer 관측우도 충실 포팅, 원본 대조 비트일치 245/245·듀얼 라이다 125/125 Δ=0) + ParticleFilter2D + SkidDetector | 무시(package.xml 없음) |
| `mcl2d_map/` | Seer `.smap` 맵 로더 | 무시 |
| `mcl2d_ros2/` | ROS2 Humble 어댑터 노드 (`/scan`+`/odom` → `/mcl_pose`+TF). 코어를 직접 컴파일 | **패키지** |
| (루트) `Tools/mcl2d_standalone/` | 비-ROS2 어댑터(`Mcl2dLocalizer` 파사드)+데모 — 규약대로 Tools/ 배치 | 불요 |
| `icp_odometry_bringup/` | 휠 오도 부재 대체 — `rtabmap_odom/icp_odometry` 를 `/scan_merged` 위에서 구동해 `/odom` 공급 ([ADR](../../docs/adr/2026-07-28-icp-odometry-bringup.md)) | **패키지** |

주의: `mcl2d_ros2`는 `../../../Tools/mcl2d_standalone/src/mcl2d_localizer.cpp`(파사드)를
함께 컴파일한다 — src↔Tools 교차 참조 1건 (파사드가 ROS2·비ROS2 공용이기 때문).

## 빌드 (이 장비 검증됨: aarch64 / gcc 11.4 / cmake 3.22 / Humble)

```bash
# ROS2 노드 — 루트 colcon 워크스페이스에서
cd ~/Project/Ford-CATL-AMR/Big-AMR
source /opt/ros/humble/setup.bash
colcon build --packages-select mcl2d_ros2
source install/setup.bash && ros2 run mcl2d_ros2 mcl2d_localization_node

# 코어 + .smap 로더 단위테스트 (2건: test_mcl2d, test_smap)
cd src/Navigation/mcl2d_core && cmake -B build -S . && cmake --build build -j6 && ctest --test-dir build

# 실제 Seer 맵으로 로더를 추가 검증하려면(맵 파일은 저장소 미포함) — test_smap_realmap 1건 추가 등록
cmake -B build -S . -DMCL2D_TEST_SMAP=$PWD/../../../map/260709_test.smap && cmake --build build -j6 && ctest --test-dir build

# 비-ROS2 데모
cd Tools/mcl2d_standalone && cmake -B build -S . && cmake --build build -j6 && ./build/mcl2d_non_ros_demo
```

## 원본(Seer_Analysis) 대비 원격 수정사항

코드(.cpp/.hpp) 무수정. CMake 경로/목록만 수정:

1. `mcl2d_standalone/CMakeLists.txt` — stale 소스 목록 수정(`observation_field.cpp`·`skid_detector.cpp` 추가) + `CORE_DIR` 재배치 경로
2. `mcl2d_ros2/CMakeLists.txt` — `NONROS` 경로 재배치 반영
3. 디렉터리 재배치: 원본 `src/mcl2d_*`+`non-ros-src` → 규약 준수 평탄 배치(위 표)

## 검증 기록 (2026-07-28, 이 장비)

- 루트 colcon `mcl2d_ros2` 빌드 성공 + 노드 기동 스모크 정상
- `test_mcl2d` 1/1 PASS · 비-ROS2 듀얼 라이다 데모 PASS(최종 오차 0.008 m)
- RE 원본 대조 오라클(`test_obs_field_oracle`)은 원본 libMCLoc.so 자산 필요 → 분석 장비 전용

### 2026-07-31 — 모션모델을 원본 구조와 동일하게 재작성 (RE 제1원칙 적용)

원본 `libMCLoc.so` 를 직접 디스어셈블해(분석 장비 `amap@amap-1` 의 63G 원본 하드) 예측 경로를 재구성했다.
기존 이식본은 근거 문서의 "디스크 산포" 서술을 따랐는데 **그 서술 자체가 원문 대조에서 반증**됐다.

- **예측(kMove)은 노이즈가 없다** — 노이즈 스케일이 `supplyControlVar` 2번째 인자 `d` 에 비례하는데
  호출지 2곳(`pfLoc.cpp:465`·`:492`) 모두 리터럴 `0.0`.
- **산포는 별도 액션(kExtraMove)** 이고, 크기는 매 주기 **6개 모드**로 재선택된다
  (이동량 20mm · 회전량 1° · 신뢰도 0.8 임계 3축).
- **정지(`is_stop`)면 kMove 자체를 건너뛴다**(원본 `DoMoveAction` @0x3d7d13) — ROS2 노드는 `/odom` 의
  twist 크기를 `MotorStopThreshold`(0.02) 와 비교해 대체 배선.
- 근거: [ADR](../../docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md) ·
  [대조 문서](../../docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md) ·
  1차 산출물 `references/seer/libMCLoc/*.asm` · 함수표 [mcl2d_core/docs/function_table.md](mcl2d_core/docs/function_table.md)
- 검증(이 장비): `ctest` **4/4 PASS**(신규 `test_motion_model` 포함, 변이 검증으로 실패 가능성 확인) ·
  비-ROS2 데모 최종 오차 **0.007 m** · `colcon build --packages-select mcl2d_ros2` 성공.
- 남은 위험: 모드 판정에 쓰는 우도 스케일이 원본과 같은지 미검증 → `docs/debt/registry.md` **debt-031**.

### 2026-07-28 추가 — .smap 로더 회귀 테스트 등록 + assert 무력화 수정

- `test_smap` 을 CMake 타깃·ctest 로 등록. 이전에는 소스만 있고 **어느 CMakeLists 에도 없어 한 번도 실행되지 않았다.**
  외부 자산 없이 돌도록 자체 픽스처(생략좌표=0 규칙·명명점·반사판·실패경로 3종) 기반으로 재작성.
- **assert 컴파일아웃 수정**: 기본 빌드타입 Release(`-DNDEBUG`)라 `test_mcl2d` 의 assert 3개가 전부 사라져
  있었다(`nm` 로 `__assert_fail` 부재 확인 = 어떤 결함이든 무조건 PASS). `-UNDEBUG` 를 테스트 타깃에 부여해 복구.
  신규 `test_smap` 은 NDEBUG 와 무관한 자체 `CHECK` 매크로를 쓴다.
- 결과: `ctest` 3/3 PASS (`test_mcl2d`, `test_smap`, 실맵 `test_smap_realmap` — Seer `260709_test`,
  장애물 19,744점 / 우도장 0.52 s / 장애물점 PDF>200 200/200).
- 변이(mutation) 검증: `smap.cpp` 의 `m.valid` 판정을 고의로 망가뜨리면 `test_smap` 이 exit=1 로 죽는 것 확인
  (테스트가 실제로 실패할 수 있음을 증명).
