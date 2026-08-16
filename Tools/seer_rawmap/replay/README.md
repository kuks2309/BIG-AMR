# seer_rawmap/replay — 우리 이식본으로 원본 로그 재생 + 오라클 대조

원본 Seer 매핑 로그(`.rawmap`)를 **우리 이식본** `slam_karto_core` 로 재생하고,
원본 `libSlaMapping.so` 를 직접 구동하는 **오라클**과 바이트 단위로 대조할 수 있는 규격으로 출력한다.

- 코어: `src/Navigation/slam_karto_core/`
- 디코더: `Tools/seer_rawmap/rawmap_to_jsonl.py`
- 원본 로그: `References/seer/slam_mapping/rawmaps/*.rawmap` (`.gitignore` 로 미추적)

## 파일

| 경로 | 내용 |
|---|---|
| `replay_ours.cpp` | JSONL → `SeerSlamMapper` 재생 CLI |
| `json_min.hpp` | 최소 JSON 리더 (헤더 온리, 표준 라이브러리만) |
| `sha256.hpp` | FIPS 180-4 SHA-256 (헤더 온리) — `sha256sum(1)` 과 동일 출력 |
| `CMakeLists.txt` | `slam_karto_core` 를 `add_subdirectory` 로 끌어와 링크 |
| `compare.py` | 오라클 출력 ↔ 우리 출력 대조 |

## 빌드

```bash
cd Tools/seer_rawmap/replay
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
```

`slam_karto_core` 의 의존성(Eigen3 / Boost(thread,system) / g2o)이 그대로 필요하다.
경로가 다르면 `-DSLAM_KARTO_CORE_DIR=<경로>`.

### ⚠ g2o RPATH 함정

g2o 는 `/opt/ros/humble/lib/aarch64-linux-gnu/` 에 있고 그 경로는 `ldconfig` 캐시에 없다.
게다가 `libg2o_types_slam2d.so` 는 `libg2o_opengl_helper.so` 를 `NEEDED` 로 갖는데 **자기 RUNPATH 가 없다**.
`DT_RUNPATH` 는 그 객체의 직접 `NEEDED` 에만 적용되고 **전이되지 않으므로** 그대로 두면 실행 시
`error while loading shared libraries` 로 죽는다.

`CMakeLists.txt` 는 코어(`src/Navigation/slam_karto_core/CMakeLists.txt:94-118`)와 **같은 방식**으로
`-Wl,--disable-new-dtags` 를 걸어 `DT_RUNPATH` 대신 **전이되는 `DT_RPATH`** 를 낸다. 새 실행 파일을
추가할 때도 이 처리를 빠뜨리지 말 것.

## 사용법

### 1) rawmap → JSONL

```bash
cd Tools/seer_rawmap
python3 rawmap_to_jsonl.py \
  ../../References/seer/slam_mapping/rawmaps/robokit_2023-08-10_05-41-41.rawmap \
  -o ../../References/seer/slam_mapping/ours/robokit_2023-08-10_05-41-41/log.jsonl
```

`log.jsonl`(한 줄 = 한 스캔)과 `log.jsonl.meta.json`(파일 단위 상수) 두 개가 나온다.

### 2) 재생

```bash
OUT=References/seer/slam_mapping/ours/robokit_2023-08-10_05-41-41
Tools/seer_rawmap/replay/build/replay_ours --log $OUT/log.jsonl --out-dir $OUT
```

옵션:

| 옵션 | 기본값 | 뜻 |
|---|---|---|
| `--log PATH` | (필수) | 입력 JSONL |
| `--out-dir DIR` | (필수) | 출력 디렉터리 (미리 존재해야 한다) |
| `--meta PATH` | `<log>.meta.json` | meta 사이드카 |
| `--limit N` | 전부 | 앞의 N개만 재생 |
| `--g2o-iterations N` | `50` | LM 반복 상한 (원본 실측, `g2o_solver.hpp:90-91`) |
| `--rssi-threshold V` | `150.0` | 반사판 판정 임계 (원본 실측, `seer_mapper_config.hpp:111-114`) |
| `--min-range M` | `0.05` | 라이다 최소 거리 (`LaserGeometry` 기본값) |
| `--max-range M` | `30.0` | 라이다 최대 거리 (**원본 실측**, 아래 함정 ② 참조) |
| `--angle-mode` | `as-is` | 빔 각도 처리. 기본은 로그 실측 각도 그대로 (아래 함정 ③) |

### 3) 대조

```bash
python3 Tools/seer_rawmap/replay/compare.py \
  References/seer/slam_mapping/oracle/robokit_2023-08-10_05-41-41/oracle_out.jsonl \
  References/seer/slam_mapping/ours/robokit_2023-08-10_05-41-41/ours_out.jsonl \
  --oracle-points .../oracle_points.jsonl --ours-points .../ours_points.jsonl
```

종료 코드: `0` 차이 없음 / `1` 차이 있음 / `2` 오류.
차이가 있으면 **최초로 갈라지는 스캔 `idx`** 를 찍는다 — 원인 추적은 거기서 시작한다.

## 출력 규격

오라클도 **똑같은 규격**으로 낸다. 키 순서까지 고정이며, 부동소수는 전부 `%.17g`
(**17자리 왕복 무손실**)이다. 반올림하면 대조가 무의미해진다.

### `ours_out.jsonl`

한 줄 = 한 레코드. 스캔 줄이 입력 순서대로 나오고, 마지막에 summary 한 줄.

```
{"type":"scan","idx":<0-based 입력 순번>,"added":<true|false>,"unique_id":<int|-1>,
 "odom":[x,y,theta],"corrected":[x,y,theta]}
{"type":"summary","num_scans":<int>,"num_points":<int>,"num_rssi":<int>,
 "bbox":[min_x,min_y,max_x,max_y],"points_sha256":"<hex>"}
```

- `odom` = 입력 오도메트리 (x,y 는 m, theta 는 rad).
- `corrected` = `processRecord` **직후** 그 스캔의 보정 포즈. `added=false` 면 `unique_id=-1`,
  `corrected` = `odom`.
- `points_sha256` = `ours_points.jsonl` **파일 내용**의 SHA-256.

### `ours_points.jsonl`

장애물 점군. `[x,y]` 한 줄씩, **스캔 순서 → 빔 순서**. 단위 m, 맵(월드) 프레임.

### `ours_rssi.jsonl` (규격 외 보조)

반사판 점군. 대조 규격에는 없지만 `num_rssi` 가 어긋났을 때 들여다볼 자료로 남긴다.

### `ours_params.json`

실제로 적용된 파라미터 전량(`SeerMapperParams` 29필드 + `LaserGeometry` + rssi 임계 + g2o 반복 수
+ `angle_mode`). 오라클도 같은 형식으로 남기므로, 출력이 다를 때
**"설정이 달랐던 것인지 알고리즘이 달랐던 것인지"** 를 먼저 가를 수 있다.

## ⚠ 함정

### ① `laser_pos_z` 는 높이가 아니라 **설치 yaw** 다

`References/seer/slam_mapping/proto/message_map.proto:44`:

```
double laser_pos_z = 3;//由于版本原因里面设置是激光安装yaw角，取激光高度数据从laser_install_height
```

높이는 `laser_install_height`(field 8) 쪽이다. 오독하면 라이다 자세가 통째로 틀어진다.
이 도구는 meta 의 `laser_install_yaw_rad` 를 쓴다 — 디코더가 field 11 우선 → field 3 폴백으로
이미 해소해 둔 값이다(`rawmap_decode.py:361-374`).

### ② `max_range` 는 헤더의 `laser_range_max`(40.0)가 아니라 **30.0** 이다

원본은 생성자가 넣은 `laser_range_max` 를 `SlaMapping::run()` 이 `.rodata` 리터럴 30.0 으로 덮은 뒤
`SetRangeThreshold` 에 넣는다. 근거는 `slam_karto_core/seer_mapper_config.hpp:105-109`
(`seer_runtime::kLaserRangeThresholdM`).

### ③ 빔 각도 배열의 비균일 — `--angle-mode` (기본 `as-is`)

**Seer 의 Karto 는 per-beam 각도 배열을 쓴다.** 상류 무개조본은 점 좌표를 만들 때
`angle = scanPose.GetHeading() + minimumAngle + beamNum * angularResolution` 로 각도를 **재생성**하지만
(`third_party/open_karto/.../Karto.h`, `LocalizedRangeScan::Update()`), Seer 포크는
`LaserRangeScan::m_pAngleReadings` 에 실측 배열을 저장하고 그 값을 그대로 쓴다.

근거 2중 (원본 직접 구동 오라클 대조, 2026-08-09):
- 원본 `LaserRangeFinder` 의 min/maxAngle 이 **±π/2 기본값 그대로**다(`oracle_params.json`).
  재생성 방식이면 521빔이 −90°~+170° 를 덮어야 하는데 실제 원본 점군은 −130°~+130° 기하다.
- **최초 분기 스캔(idx 20)이 최초 비균일 스캔(idx 20)과 정확히 일치**했다.

그래서 동봉 Karto 에 패치를 적용해 같은 경로를 넣었고
(`third_party/patches/0001-use-measured-per-beam-angles.patch`), **기본값은 `--angle-mode as-is`** 다 —
로그의 실측 각도를 **그대로** 넘긴다. 효과(실측): 포즈 위치차 max **1.83 m → 0.026 m**.

`--angle-mode uniform` 은 각도를 `min_angle + i * laser_step` 격자로 **대체**한다.
지금은 **원본에서 멀어지는 쪽**이므로 진단용으로만 쓴다(패치 전후 거동 비교 등).

비균일 자체는 거부 사유가 아니다 — 코어는 기본적으로 관측만 하고 통과시킨다
(`SeerSlamMapper::setStrictAngleUniformity(true)` 로 엄격 모드를 켤 수 있다).
실측: 이 로그 213 스캔 중 **90개**가 비균일이고 최대 편차 0.0268 rad(≈1.54°)다.

콘솔 첫 줄에 `grid_replaced_records` 와 `grid_max_deviation_rad` 를 찍어 **조용한 데이터 변경을 막는다.**

### ④ `min_angle` 은 헤더에 없다 — 첫 스캔의 첫 빔 각도를 쓴다

`Message_MapLog`/`Message_LocalMapLog` 에는 `laser_step`(field 4)만 있고 최소 각도 필드가 없다
(`message_map.proto:41-62, 64-...`). 그래서 첫 레코드의 `angle[0]` 을 `min_angle` 로 확정한다.
⚠ 이 로그에서는 스캔마다 `angle[0]` 이 조금씩 다르다(첫 스캔 `-2.2689235751201808` rad,
159번 스캔 `-2.2882431105907743` rad). 원본도 `LaserRangeFinder` 를 한 번만 설정하므로 같은 성질을
갖지만, **오라클이 어느 스캔의 값을 채택하는지**는 확인해서 맞춰야 한다.

### ⑤ `SeerMapperParams` 는 손대지 않는다

기본값이 이미 원본 디스어셈블 실측값이다(`seer_mapper_config.hpp` 참조). 이 도구는 어떤 값도
덮어쓰지 않고, 적용된 전량을 `ours_params.json` 에 기록만 한다.

## 검증

```bash
# 1) 자체 SHA-256 구현이 sha256sum 과 같은가
sha256sum $OUT/ours_points.jsonl
tail -1 $OUT/ours_out.jsonl        # points_sha256 필드와 대조

# 2) 재실행 결정성 + compare.py 자체 건전성 (자기 출력끼리 → 0 차이)
python3 compare.py $OUT/ours_out.jsonl $OUT/ours_out.jsonl \
  --oracle-points $OUT/ours_points.jsonl --ours-points $OUT/ours_points.jsonl

# 3) 코어 시험 (검증 매크로는 CHECK — assert 는 Release 에서 사라진다)
./build/slam_karto_core_build/test_slam_mapping
```
