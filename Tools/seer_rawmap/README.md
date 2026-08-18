# seer_rawmap — Seer `.rawmap` 디코더 · 재생 내보내기

Seer 로봇이 SLAM 매핑 중 남기는 `.rawmap`(원시 매핑 로그, `Message_MapLog` protobuf)을
**표준 라이브러리만으로** 디코드하고, 재생용 JSONL 로 내보내는 비-ROS2 독립 도구.

- `protobuf` 파이썬 패키지 **불요**. `.proto` 컴파일 단계 **없음**. protobuf *wire format* 만 직접 구현.
- ROS2 패키지가 아니므로 저장소 규약대로 `Tools/` 아래에 둔다
  (`CLAUDE.md` §저장소 디렉토리 배치 — 「비-ROS2 독립 도구 → `Tools/<도구명>/`」).

## 파일

| 파일 | 줄 | 역할 |
| --- | --- | --- |
| `rawmap_decode.py` | 826 | wire 파서 + 자료구조. `decode_maplog(path) -> MapLog` |
| `rawmap_info.py` | 256 | CLI 요약표(파일/디렉터리, `--json`, `--sort`) |
| `rawmap_to_jsonl.py` | 225 | 재생용 JSONL 내보내기(`--stride`, `--gzip`) + 메타 사이드카 |
| `test/test_rawmap_decode.py` | 539 | 회귀 시험 33개(합성 27 + 실자산 6) |
| `docs/function_table.md` | 94 | 함수표·전역변수표(권위본). 루트 집계는 `docs/sw_structure/function_table.md` |

## 사용법

```bash
cd Tools/seer_rawmap

# 1) 요약 — 파일 하나 또는 디렉터리
python3 rawmap_info.py ../../References/seer/slam_mapping/rawmaps/
python3 rawmap_info.py <파일>.rawmap --json          # 기계 판독용
python3 rawmap_info.py <디렉터리> --sort scans        # name|scans|size|duration

# 2) 재생용 JSONL 내보내기
python3 rawmap_to_jsonl.py <파일>.rawmap -o out.jsonl
python3 rawmap_to_jsonl.py <파일>.rawmap -o out.jsonl --stride 10 --gzip

# 3) 시험
python3 -m unittest discover -s test -v
```

라이브러리로 쓸 때:

```python
import sys; sys.path.insert(0, "Tools/seer_rawmap")
from rawmap_decode import decode_maplog

log = decode_maplog("robokit_2024-05-31_18-20-43.rawmap")
log.laser_name          # 'SickSafe-UDP'  (MapLog 1개 = 라이다 1대)
log.laser_pose          # LaserPose — .install_yaw_rad 이 함정 ① 를 해소한 값
log.scans               # [ScanRecord]  .dist/.angle/.rssi/.odo_x/.timestamp_sec
log.odometry            # [OdoRecord]   .timestamp/.x/.y/.w
log.localization        # [LocalizationRecord] — LocalMapLog 스키마일 때만
log.schema_variant      # SchemaVariant.LOCAL_MAP_LOG | MAP_LOG | AMBIGUOUS
```

### JSONL 계약 (C++ 재생기 입력)

한 줄 = 한 스캔:

```json
{"odo":[x,y,w],"dist":[...],"angle":[...],"rssi":[...],"t":4460.29244434}
```

단위: `odo` x·y [m], w [rad] / `dist` [m] / `angle` [rad, 라이다 프레임] / `rssi` 무차원 /
`t` [s, **로그 클럭**(단조·부팅 기준) — UNIX epoch 아님].

파일 단위 상수(라이다 자세·각도 step·최대 거리·스키마 판정)는 한 줄 계약을 깨지 않도록
사이드카 `<출력>.meta.json` 으로 따로 쓴다(`--no-meta` 로 끌 수 있다).

## `.rawmap` 파일 구조

파일 전체가 **단일** 직렬화 protobuf 메시지다 — 매직 바이트·길이 프리픽스·프레이밍이
없다(회수한 26개 파일 전부 top-level 파싱 성공, 잔여 바이트 0). 메시지는
`rbk.protocol.Message_MapLog` 또는 `Message_LocalMapLog` 이며, 둘은 **필드 20 만 다르고
나머지 필드 번호·타입이 완전히 같다**.

### `Message_MapLog` / `Message_LocalMapLog`

출처: `References/seer/slam_mapping/proto/message_map.proto:41-62`(MapLog),
`:64-85`(LocalMapLog).

| # | 이름 | 타입 | 실자산에서 관측 | 비고 |
| --- | --- | --- | --- | --- |
| 1 | `laser_pos_x` | double | 0.879 (26/26) | 장착 x [m] |
| 2 | `laser_pos_y` | double | −0.579 / −0.581 | 장착 y [m] |
| 3 | `laser_pos_z` | double | −0.785398… | **높이 아님 → 장착 yaw** (함정 ①, `:44`) |
| 4 | `laser_step` | double | 0.008726637937593242 (=0.5°) | 빔 각도 간격 [rad] |
| 5 | `laser_range_max` | double | 40.0 | 최대 거리 [m] |
| 6 | `log_data` | repeated `Message_MapLogData` | 20–328 | 스캔 |
| 7 | `laser_name` | **string(스칼라)** | `SickSafe-UDP` | MapLog 1개 = 라이다 1대 (`:48`) |
| 8 | `laser_install_height` | double | 미출현(=0) | 높이 [m] — 함정 ① 의 정답 필드 |
| 9 | `odometer` | repeated `Message_MapOdo` | 60–4838 | 오도메트리 |
| 10 | `log_data3d` | repeated `Message_MapLogData3D` | 미출현 | 3D 라이다용 |
| 11 | `laser_install_yaw` | double | 미출현(=0) | 신버전 yaw 필드 |
| 12 | `laser_install_pitch` | double | 미출현 | |
| 13 | `laser_install_roll` | double | 미출현 | |
| 14 | `imu_data` | repeated `Message_IMU` | 미출현 | |
| 15 | `gnss_data` | repeated `Message_GNSS` | 미출현 | |
| 16 | `lasertype` | uint32 | 미출현(=0) | 1=RS16, 2=RS Helios, 3=Velodyne16 (`:57`) |
| 17 | `factor` | float | 미출현 | |
| 18 | `azimuthcorrection` | repeated float | 미출현 | |
| 19 | `verticalcorrection` | repeated float | 미출현 | |
| 20 | `all_gnss_data` **또는** `localization_data` | repeated | 20/26 파일에 존재 | **스키마 분기** (함정 ②) |

### `Message_MapLogData` (스캔) — `message_map.proto:11-19`

| # | 이름 | 타입 | 실자산 |
| --- | --- | --- | --- |
| 1 | `robot_odo_x` | double | 스캔 시점 오도 x [m] |
| 2 | `robot_odo_y` | double | 스캔 시점 오도 y [m] |
| 3 | `robot_odo_w` | double | 스캔 시점 헤딩 [rad] |
| 4 | `laser_beam_dist` | repeated double (**packed**) | 521/533/541/1041개, 미반사 sentinel `9999.999` |
| 5 | `laser_beam_angle` | repeated double (**packed**) | 예: −2.35619…~+2.35619… (±135°) |
| 6 | `rssi` | repeated double (**packed**) | 예: 50.0 |
| 7 | `header` | `Message_Header` | `frame_id` = 라이다 이름 |

proto3 `repeated double` 은 기본이 packed 이므로 디코더는 **packed(wire type 2)** 를 주 경로로
처리하고, 비-packed(wire type 1 반복) 인코딩도 함께 받는다(`_collect_doubles`).

### `Message_MapOdo` — `message_map.proto:20-28`

| # | 이름 | 타입 | 비고 |
| --- | --- | --- | --- |
| 1 | `timestamp` | **double** | [s], 로그 클럭 |
| 2–4 | `odo_x` / `odo_y` / `odo_w` | **float** | 타임스탬프만 double, 자세는 float32 — 혼동 주의 |
| 5–7 | `odo_vx` / `odo_vy` / `odo_vw` | float | 회수 자산 26/26 에서 **전부 미출현(=0)** — 속도는 기록되지 않았다 |

### `Message_Header` — `message_header.proto:3-8`

`pub_nsec`(1) · `data_nsec`(2) · `seq`(3) · `frame_id`(4). 시각은 **나노초**이며 값이
4.46e12 ns ≈ 4460 s 수준이라 **UNIX epoch 이 아니라 단조/부팅 클럭**이다. 같은 파일의
`Message_MapOdo.timestamp`(4460.278 s)와 같은 축이다.

### `Message_Localization` (필드 20, LocalMapLog) — `message_localization.proto:5-39`

`header`(1) · `x`(2) · `y`(3) · `angle`(4) · `confidence`(5) · `correction_errs`(6, packed double) ·
`reliabilities`(7) · `in_forbidden_area`(8) · `update_reason`(9) · `loc_state`(10) ·
`similarity`(11) · `loc_method`(12). 실자산에서는 1–6 만 출현한다.

## 함정 2건

### 함정 ① `laser_pos_z` 는 높이가 아니라 장착 yaw

`message_map.proto:44` 원문 주석:

```
double laser_pos_z = 3;//由于版本原因里面设置是激光安装yaw角，取激光高度数据从laser_install_height
```

("버전 사정으로 안에 설정된 것은 레이저 장착 yaw 각이고, 레이저 높이 데이터는
`laser_install_height` 에서 가져온다")

실측: 26개 파일 전부 필드 3 이 음수 라디안 —
`-0.7853981633974483`(= 정확히 −45°, 4개 파일) 또는 `-0.7854628926996793`(= −45.0037°, 22개 파일).
높이로 해석하면 라이다가 지면 아래 0.785 m 에 달린 셈이 되어 자세가 통째로 틀어진다.
같은 자산에서 `laser_install_height`(필드 8)와 `laser_install_yaw`(필드 11)는 **한 번도 출현하지 않는다**
(= proto3 기본값 0).

디코더 처리: `LaserPose.install_yaw_rad` 는 필드 11 이 0 이 아니면 그것을, 아니면 필드 3 을
반환한다. 원시 값은 `LaserPose.pos_z_raw` 로 별도 보존한다.

> 선행 지적: `docs/code_review/seer-slam-mapping/2026-08-08.md:457-462`.

### 함정 ② 필드 20 은 파일마다 스키마가 다르다

`Message_MapLog.all_gnss_data = 20`(`:61`) vs `Message_LocalMapLog.localization_data = 20`(`:84`).
두 메시지는 나머지 필드가 동일해 **파일 자체로는 어느 쪽인지 알 수 없다.**

디코더는 구조로 판별한다(`classify_field20`):

| 조건 | 판정 |
| --- | --- |
| 필드 20 부재 | `AMBIGUOUS` — 두 스키마가 바이트 단위로 동일하므로 판정 불가 |
| 모든 필드 20 페이로드가 `Message_Localization` 형태(필드 1 = Header 형 submessage, 필드 2·3·4 = fixed64) | `LOCAL_MAP_LOG` |
| 그 외 | `MAP_LOG` (= `all_gnss_data`), 페이로드는 `MapLog.raw_field20` 에 원시 보존 |

**`Message_AllGNSS` 정의는 회수되지 않았다.** 확인 범위:
`ls References/seer/slam_mapping/proto/` → `message_header/imu/laser/localization/map/odometer.proto`
6개뿐이며 `message_gnss.proto` 없음(`message_map.proto:8` 이 import 하지만 파일 부재).
따라서 GNSS 쪽은 **양성 식별이 불가**하고, "Localization 형태가 아니다"라는 음성 판정만 가능하다.

## 실측 결과 — 회수 자산 26개 전수 (2026-08-08)

실행:

```bash
cd Tools/seer_rawmap && python3 rawmap_info.py ../../References/seer/slam_mapping/rawmaps/
```

`scans`=`log_data` 개수, `odo`=`odometer` 개수, `loc`=필드 20(Localization) 개수,
`t`=`Message_Header.data_nsec` 기반 로그 클럭 [s], `odo bbox`=`odometer` 궤적 경계 [m].

| 파일 (`robokit_` 생략) | MiB | scans | beams | odo | loc | t0..t1 [s] | dur [s] | odo bbox x [m] | odo bbox y [m] | laser x,y [m] | yaw | schema |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023-08-09_04-27-34 | 2.00 | 149 | 541 | 1618 | 1451 | 4460.3..4510.7 | 50.4 | [22.19, 25.93] | [21.00, 25.09] | 0.879, -0.579 | -45.0° | LocalMapLog |
| 2023-08-09_04-30-13 | 3.19 | 236 | 541 | 2844 | 2564 | 4578.5..4668.1 | 89.7 | [21.63, 26.17] | [20.25, 25.21] | 0.879, -0.579 | -45.0° | LocalMapLog |
| 2023-08-09_16-06-00 | 3.07 | 226 | 533 | 3294 | 2781 | 286.8..390.5 | 103.8 | [-2.03, 2.89] | [-3.00, 2.82] | 0.879, -0.579 | -45.0° | LocalMapLog |
| 2023-08-09_16-10-16 | 3.68 | 273 | 533 | 3696 | 3142 | 527.2..646.5 | 119.4 | [-1.68, 2.77] | [-2.81, 3.10] | 0.879, -0.579 | -45.0° | LocalMapLog |
| 2023-08-10_05-27-14 | 2.15 | 166 | 521 | 2099 | 1409 | 115.6..167.6 | 52.0 | [-3.00, 4.36] | [-0.39, 0.50] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-27-22 | 0.24 | 20 | 521 | 60 | 0 | 189.3..189.9 | 0.6 | [-2.28, -2.28] | [0.50, 0.50] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2023-08-10_05-28-15 | 0.38 | 28 | 521 | 1509 | 103 | 195.8..199.4 | 3.6 | [-2.28, -1.44] | [0.50, 0.52] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-28-58 | 0.24 | 20 | 521 | 103 | 0 | 284.2..284.8 | 0.6 | [-1.44, -1.44] | [0.52, 0.52] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2023-08-10_05-29-57 | 0.70 | 54 | 521 | 1214 | 261 | 306.7..323.8 | 17.1 | [-1.44, 2.19] | [0.32, 0.53] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-30-14 | 0.30 | 24 | 521 | 235 | 118 | 355.6..360.8 | 5.2 | [2.18, 2.61] | [0.28, 0.32] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-31-14 | 0.40 | 28 | 521 | 1763 | 213 | 367.3..388.5 | 21.2 | [2.61, 3.37] | [-0.21, 0.28] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-36-20 | 0.78 | 59 | 521 | 1322 | 451 | 686.5..716.6 | 30.1 | [0.61, 3.37] | [-0.21, 0.01] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-08-10_05-40-00 | 0.29 | 20 | 521 | 1874 | 0 | 889.8..890.4 | 0.6 | [0.61, 0.61] | [0.01, 0.01] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2023-08-10_05-41-41 | 2.79 | 213 | 521 | 2976 | 2146 | 954.2..1048.6 | 94.4 | [-2.87, 4.74] | [-0.89, 0.82] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-12-11_22-06-13 | 5.23 | 206 | 1041 | 3518 | 2828 | 2450.2..2559.0 | 108.8 | [-4.42, -2.23] | [-6.02, 2.13] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-12-13_02-22-46 | 3.33 | 134 | 1041 | 1634 | 1054 | 37063.8..37114.0 | 50.2 | [4.91, 5.84] | [-9.80, -4.16] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-12-13_04-21-36 | 4.04 | 164 | 1041 | 1532 | 1114 | 3876.2..3922.5 | 46.3 | [-1.40, -0.79] | [0.01, 8.07] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2023-12-13_22-33-01 | 0.48 | 20 | 1041 | 90 | 0 | 21941.7..21942.2 | 0.6 | [-0.17, -0.17] | [-0.36, -0.36] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2023-12-13_22-34-42 | 4.77 | 194 | 1041 | 1455 | 1289 | 21997.9..22044.1 | 46.1 | [-4.14, 5.36] | [-1.15, -0.36] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2024-03-29_16-57-08 | 0.60 | 20 | 1041 | 4838 | 55 | 1588.7..1589.2 | 0.6 | [-6.79, -6.79] | [17.67, 17.67] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2024-03-29_16-57-22 | 0.49 | 20 | 1041 | 289 | 0 | 1750.9..1751.5 | 0.6 | [-6.79, -6.79] | [17.67, 17.67] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2024-03-29_17-11-42 | 8.26 | 328 | 1041 | 4827 | 4422 | 2461.7..2615.2 | 153.5 | [-13.35, -6.79] | [17.67, 27.84] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2024-04-03_21-31-24 | 3.89 | 157 | 1041 | 1977 | 1175 | 907.0..965.9 | 58.9 | [-5.73, -1.57] | [-0.01, 4.97] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2024-04-03_21-33-39 | 1.33 | 52 | 1041 | 1733 | 557 | 1050.9..1072.7 | 21.7 | [-3.46, -3.31] | [-0.02, 1.52] | 0.879, -0.581 | -45.0° | LocalMapLog |
| 2024-04-03_22-52-51 | 0.50 | 20 | 1041 | 949 | 0 | 5827.9..5828.5 | 0.6 | [-7.18, -7.18] | [0.41, 0.41] | 0.879, -0.581 | -45.0° | **ambiguous** |
| 2024-05-31_18-20-43 | 1.06 | 40 | 1041 | 1583 | 834 | 3081.7..3123.1 | 41.4 | [23.25, 24.43] | [21.67, 22.45] | 0.879, -0.581 | -45.0° | LocalMapLog |

전수 집계 (26 파일, 실패 0, 총 2.1 s):

- 스캔 **2,871** / 오도 **49,032** / localization **27,967**
- `laser_name` = `SickSafe-UDP` **단일** — 회수 자산 전부 라이다 1대분 로그다
- 빔 수 4종: **521 / 533 / 541 / 1041** (같은 파일 안에서는 항상 단일 값)
- `laser_step` = 0.008726637937593242 rad (0.5°) **단일**, `laser_range_max` = 40.0 m **단일**
- **1041빔 파일(12개)은 한 스캔 안에 두 블록이 이어 붙어 있다** — `laser_name` 이 스칼라인데도
  단일 라이다 스윕이 아니다. 실측(전 26파일, 첫 스캔 기준):

  | 빔 수 | 균일 0.5° 구간 | 각도 범위 | 나머지 |
  | --- | --- | --- | --- |
  | 521 (10파일) | 521 전부 | −130.0°..+130.0° | 0 |
  | 533 (2파일) | 533 전부 | −133.0°..+133.0° | 0 |
  | 541 (2파일) | 541 전부 | −135.0°..+135.0° | 0 |
  | 1041 (12파일) | 앞 **521** | −130.0°..+130.0° | 뒤 **520**, 비균일, 약 −180°..+180° |

  1041빔의 뒤쪽 520개는 각도 간격이 일정하지 않고(같은 각도가 연속 반복되는 구간 포함) 미반사
  샘플(`dist=9999.999`, `rssi=0`)이 다수다. 앞 521 블록만 `laser_step` 과 정합하므로,
  **재생기는 1041빔 스캔을 단일 스윕으로 다루면 안 된다.** 뒤 블록의 정체(2번째 라이다인지,
  병합 결과인지)는 `laser_name` 이 하나뿐이라 이 자산만으로는 확정할 수 없다 — 미해결 §5.
  회귀 고정: `test_beam_block_structure_matches_measurement`.
- `laser_pos_z`(= yaw) 2종: −0.7853981633974483(4파일) / −0.7854628926996793(22파일)
- 필드 8·11·12·13·16·17 은 26/26 에서 **미출현**, 미지 top-level 필드 **0건**
- **필드 20 이 있는 20개 파일은 전부 `Message_Localization` 형태다 — GNSS 형태(`Message_MapLog` 판정)로
  나온 실자산은 0건.** 나머지 6개는 필드 20 자체가 없어 `ambiguous`.
  즉 `MAP_LOG` 분기는 합성 시험으로만 검증되며 실자산 근거가 없다.

## 시험

```bash
cd Tools/seer_rawmap && python3 -m unittest discover -s test -v
```

- **합성 27개**: 외부 자산 없이 돈다. 시험 쪽에서 protobuf 바이트를 직접 만들어 왕복 검증
  (varint·wire type·packed/비-packed double·헤더·오도·잘림·미지 필드·함정 ①·함정 ②·JSONL 계약).
- **실자산 6개**: `References/seer/slam_mapping/rawmaps/` 가 있을 때만 돈다. 없으면 `skipped`.
  **skip 은 성공이 아니다** — 러너 출력의 `skipped=` 를 확인할 것.
  (`References/` 는 `.gitignore:12` 로 미추적이라 클린 체크아웃에서는 자동으로 skip 된다.)

포맷: `python3 -m black --check .` (4 files unchanged).

## 미해결 / 한계

1. `Message_AllGNSS` · `Message_GNSS` 스키마 미회수 → 필드 20 의 GNSS 분기는 **음성 판정만** 가능.
   해당 페이로드는 디코드하지 않고 `MapLog.raw_field20` 에 원시 바이트로 보존한다.
2. `Message_MapLogData3D`(필드 10)·`Message_IMU`(14)·`Message_GNSS`(15)·`azimuthcorrection`(18)·
   `verticalcorrection`(19) 디코드 미구현 — 회수 자산 26/26 에 출현하지 않아 검증 근거가 없다.
   출현 시 `MapLog.unknown_fields` 에 `(필드번호, wire type)` 으로 남는다(조용한 무시 아님).
3. 로그 클럭의 절대 기준(부팅 시각) 미상 — 파일 간 시각 비교는 불가하고 파일 내 상대 시각만 유효하다.
4. `.smap`(완성 지도, `Message_Map`) 디코드는 본 도구 범위 밖이다.
5. 1041빔 스캔의 뒤쪽 520개 블록 정체 미확정(위 실측 표 참조). `laser_name` 이 스칼라 1개
   (`SickSafe-UDP`)뿐이라 2번째 라이다인지 병합 결과인지 자산만으로는 가릴 수 없다.
   디코더는 블록을 나누지 않고 파일에 적힌 순서 그대로 노출한다 — 나눔은 소비자 책임.
6. `Message_MapOdo` 의 속도 3필드(5·6·7)가 26/26 에서 미출현이라 재생 시 속도는 위치 미분으로
   얻어야 한다.
