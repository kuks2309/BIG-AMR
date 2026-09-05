# open_karto — 동봉본 안내

이 폴더는 **상류 소스 그대로**다. 우리가 쓴 코드가 아니다.

## 출처

| | |
|---|---|
| 저장소 | https://github.com/ros-perception/open_karto |
| 브랜치 | `melodic-devel` |
| 커밋 | `922db5042af83f8634c830349226b270bb155554` (2024-07-22) |
| 라이선스 | **LGPL-3.0** — 전문은 이 폴더의 [LICENSE](LICENSE) |
| 원저작자 | Michael A. Eriksen · Benson Limketkai (SRI International) — [Authors](Authors) |

## 왜 여기 있나

원본 RoboshopPro 의 `LaserSLAM.dll` 안 `KartoSLAM` 이 쓰는 바로 그 OpenKarto 다. 우리는 알고리즘을 **다시 쓰지 않고 이것을 바인딩한다** — 이유는 [ADR-009](../../docs/architecture/decisions/ADR-009_KartoSLAM은-원본-C++를-바인딩한다.md).

받아서 빌드하지 않고 동봉하는 이유:

- **LGPL-3.0 이 소스 제공을 요구한다.** 우리가 배포하는 바이너리에 대응하는 소스가 함께 가야 한다.
- **빌드가 네트워크에 의존하면 안 된다.** 상류가 사라지거나 태그가 움직이면 어제 되던 빌드가 오늘 안 된다.

## 고치지 말 것

**이 폴더의 파일은 수정하지 않는다.** 고치는 순간 "원본과 같은 코드" 라는 근거가 사라진다 — 그 근거 하나 때문에 재구현 대신 바인딩을 택했다.

고쳐야 할 것이 생기면 **패치 파일로 분리**해 무엇을 바꿨는지 보이게 하고, 이 파일에 그 사실을 적는다.

### 적용된 패치 (1건)

`../patches/0001-use-measured-per-beam-angles.patch` — **2026-08-09, Big-AMR 저장소에서 적용**

| | |
|---|---|
| 대상 | `include/open_karto/Karto.h` 2개소 (`LaserRangeScan` 멤버·접근자 / `LocalizedRangeScan::Update()`) |
| 내용 | per-beam 각도 배열(`m_AngleReadings`)을 저장하고, 있으면 `Update()` 가 점 좌표 계산에 **그 값을 그대로** 쓴다. 비어 있으면 상류 동작(`minimumAngle + i * angularResolution`)이 **그대로 유지**된다 |
| 왜 | **Seer 의 포크가 그렇게 동작한다.** Seer 는 `LaserRangeScan` 에 `m_pAngleReadings` 를 추가하고 3벡터 `SetRangeReadings(range, angle, rssi)` 를 쓴다. 상류 방식을 쓰면 원본과 다른 지도가 나온다 |
| 근거 | ① 원본 `LaserRangeFinder` 의 min/maxAngle 이 **±pi/2 기본값 그대로**인데(오라클 실측 `oracle_params.json`), 재생성 방식이면 521빔이 −90°~+170° 를 덮어야 한다 — 실제 원본 점군은 −130°~+130° 기하다. ② 원본 직접 구동 오라클과의 대조에서 **최초 분기 스캔(idx 20)이 최초 비균일 스캔(idx 20)과 정확히 일치**했다 |
| 효과 (실측) | 원본 대비 포즈 위치차 **max 1.83 m → 0.026 m**, 방위차 **0.793 rad → 0.0073 rad** |
| 되돌리기 | `patch -R -p1 < ../patches/0001-use-measured-per-beam-angles.patch` (역적용 확인 완료) |

상류를 갱신할 때는 이 패치를 **재적용**해야 한다. `Update()` 의 각도 계산부가 바뀌었으면 충돌하므로 수동 병합이 필요하다.

상류를 갱신할 때는 커밋 해시를 위 표에 갱신하고, 바뀐 내용이 바인딩에 영향을 주는지 확인한다.

## 빌드가 요구하는 것

`CMakeLists.txt` 확인 결과:

```cmake
add_library(karto SHARED src/Karto.cpp src/Mapper.cpp)
target_link_libraries(karto ${Boost_LIBRARIES})
```

- **Boost** (thread) — 실제로 링크하는 유일한 라이브러리
- **Eigen3** — 헤더 전용

⚠ `package.xml` 과 `CMakeLists.txt` 에 `catkin`·`sparse_bundle_adjustment` 가 보이지만 **`karto` 라이브러리 자체는 링크하지 않는다.** ROS 포장과 `samples/`(SPA 솔버 예제)를 위한 것이다. **따라서 ROS 없이 빌드된다** — 브릿지가 로봇마다 설치되는 것을 생각하면 이 사실이 방안의 성립 여부를 갈랐다.

`samples/` 는 빌드하지 않는다. 상류 소스를 온전히 남기려고 함께 두었을 뿐이다.

## 빌드 방법

상류의 `CMakeLists.txt` 는 **쓰지 않는다** — catkin 을 요구하기 때문이다. 우리 빌드 파일은 [native/CMakeLists.txt](../../native/CMakeLists.txt) 에 있고 이 폴더의 소스를 읽어 간다. 이 폴더를 고치지 않기 위한 배치다.

### 준비물 (Windows, 2026-08-02 실측)

| | 확인된 버전 | 설치 |
|---|---|---|
| C++ 컴파일러 | MSVC 19.44.35228 (x64) | `winget install Microsoft.VisualStudio.2022.BuildTools` + `--add Microsoft.VisualStudio.Workload.VCTools` |
| CMake | 3.31.6 | **Build Tools 에 딸려 온다** — 따로 깔 필요 없다 |
| Boost (thread) | 1.91.0 | vcpkg |
| Eigen3 | 5.0.1 | vcpkg |

vcpkg 는 프로젝트 폴더 **밖**에 둔다(저장소 오염 방지). 예: `C:\Users\<user>\vcpkg`.

```bash
git clone --depth 1 https://github.com/microsoft/vcpkg.git
cd vcpkg && ./bootstrap-vcpkg.bat -disableMetrics
./vcpkg.exe install boost-thread:x64-windows eigen3:x64-windows
```

### 빌드 (저장소 루트에서)

```bash
cmake -S native -B build/native \
      -DCMAKE_TOOLCHAIN_FILE=<vcpkg>/scripts/buildsystems/vcpkg.cmake \
      -DVCPKG_TARGET_TRIPLET=x64-windows -A x64
cmake --build build/native --config Release
```

산출물: `build/native/out/karto.dll` (실측 221 KB). `build/` 는 `.gitignore` 대상이다 — 소스에서 재생성되는 것이고, 배포용 바이너리는 릴리스에 올리지 저장소에 넣지 않는다.

**받아 쓰는 쪽은 빌드하지 않는다.** 컴파일은 개발 기계에서 한 번만 하고, 로봇 PC(Personal Computer) 에는 만들어진 `.dll` 만 간다.

## 파라미터에 대해 (미해결)

원본이 Karto 에 **어떤 값을 넣는지 아직 모른다.**

확인한 것: 원본 설치본에 2D Karto 파라미터를 담은 설정 파일이 **없다.** `appInfo/setting/` 전체에서 `MinimumTravelDistance`·`UseScanMatching`·`LoopSearch*`·`Correlation*` 을 찾았으나 0건이고, 유일한 SLAM 설정인 `3DSlamConfig.cfg` 는 3D 점군의 높이 절단용이지 Karto 파라미터가 아니다.

따라서 원본의 2D 는 **내장 기본값으로 돈다** — Karto 자신의 기본값이거나 `LaserSLAM.dll` 안에 박힌 값이다. 후자라면 역어셈블 없이는 읽을 수 없다.

**그래서 우리는 상류 기본값을 그대로 쓴다.** 가장 가까운 출발점이고, 실제로 같은 지도가 나오는지는 원본과 나란히 돌려 대조해야 확인된다. 그 전까지 "같은 결과" 라고 말하지 않는다.
