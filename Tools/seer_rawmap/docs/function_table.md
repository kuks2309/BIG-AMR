# `Tools/seer_rawmap` 함수표 · 전역변수표 (권위본)

> `coding.md:41-47` §2/§6 이중 기록 중 **모듈 로컬 권위본**. 루트 집계 인덱스는
> [docs/sw_structure/function_table.md](../../../docs/sw_structure/function_table.md).
> 최초 작성 2026-08-08 (신규 파일 — coding.md:45 「신규 파일은 계획 단계에서 표를 생성」).
> 상태: **전수** (공개·비공개 함수 전부 등재).

## 함수표 — `rawmap_decode.py`

| 함수 | 위치 | 인자 → 반환 | 용도 | 부수효과 |
| --- | --- | --- | --- | --- |
| `read_varint` | rawmap_decode.py:175-204 | `(bytes, int)` → `(int, int)` | base-128 varint 1개 판독 | 없음 |
| `iter_fields` | rawmap_decode.py:207-257 | `bytes` → `Iterator[(int,int,object)]` | 메시지 1개의 top-level 필드 순회 | 없음 (제너레이터) |
| `unpack_doubles` | rawmap_decode.py:260-279 | `bytes` → `List[float]` | packed repeated double 해제 | 없음 |
| `_as_double` | rawmap_decode.py:282-284 | `bytes(8)` → `float` | fixed64 → binary64 | 없음 |
| `_as_float` | rawmap_decode.py:287-289 | `bytes(4)` → `float` | fixed32 → binary32 | 없음 |
| `_collect_doubles` | rawmap_decode.py:292-306 | `(int, object, List[float])` → `None` | packed·비-packed 양쪽 수집 | `sink` 리스트를 in-place 확장 |
| `Header.timestamp_sec` | rawmap_decode.py:327-335 | `self` → `float` [s] | `data_nsec`→없으면 `pub_nsec` | 없음 (property) |
| `LaserPose.install_yaw_rad` | rawmap_decode.py:362-374 | `self` → `float` [rad] | **함정 ①** 해소: 필드11 우선, 없으면 필드3 | 없음 (property) |
| `ScanRecord.timestamp_sec` | rawmap_decode.py:401-403 | `self` → `float` [s] | 스캔 시각 | 없음 (property) |
| `ScanRecord.beam_count` | rawmap_decode.py:406-408 | `self` → `int` | 빔 개수 | 없음 (property) |
| `MapLog.scan_count` | rawmap_decode.py:498-500 | `self` → `int` | 스캔 개수 | 없음 (property) |
| `MapLog.time_range_sec` | rawmap_decode.py:502-512 | `self` → `Optional[(float,float)]` [s] | 스캔 시각 범위 | 없음 |
| `MapLog.odometry_bounds` | rawmap_decode.py:514-525 | `self` → `Optional[(f,f,f,f)]` [m] | 오도 궤적 AABB | 없음 |
| `MapLog.beam_counts` | rawmap_decode.py:527-529 | `self` → `List[int]` | 빔 수 종류(오름차순) | 없음 |
| `_is_header_shaped` | rawmap_decode.py:546-563 | `bytes` → `bool` | `Message_Header` 형태 판정 | 없음 |
| `_is_localization_shaped` | rawmap_decode.py:566-592 | `bytes` → `bool` | `Message_Localization` 형태 판정 | 없음 |
| `classify_field20` | rawmap_decode.py:595-612 | `Sequence[bytes]` → `SchemaVariant` | **함정 ②** 스키마 판별 | 없음 |
| `_decode_header` | rawmap_decode.py:616-630 | `bytes` → `Header` | 헤더 디코드 | 없음 |
| `_decode_scan` | rawmap_decode.py:633-654 | `bytes` → `ScanRecord` | `Message_MapLogData` 디코드 | 없음 |
| `_decode_odo` | rawmap_decode.py:657-680 | `bytes` → `OdoRecord` | `Message_MapOdo` 디코드 (ts=double, 자세=float) | 없음 |
| `_decode_localization` | rawmap_decode.py:683-704 | `bytes` → `LocalizationRecord` | 필드20 Localization 디코드 | 없음 |
| `decode_maplog_bytes` | rawmap_decode.py:728-807 | `(bytes, str)` → `MapLog` | 메모리 버퍼 디코드 (공개) | 없음 |
| `decode_maplog` | rawmap_decode.py:810-826 | `str` → `MapLog` | 파일 디코드 (공개 정문) | 파일 read |

### 자료형 (dataclass / enum / 예외)

| 이름 | 위치 | 용도 |
| --- | --- | --- |
| `RawmapDecodeError(ValueError)` | rawmap_decode.py:158-159 | wire 파싱 실패 |
| `SchemaVariant(str, Enum)` | rawmap_decode.py:162-171 | `LOCAL_MAP_LOG` / `MAP_LOG` / `AMBIGUOUS` |
| `Header` | rawmap_decode.py:311-335 | pub/data nsec·seq·frame_id |
| `LaserPose` | rawmap_decode.py:339-374 | 장착 x·y·pos_z_raw·height·yaw·pitch·roll |
| `ScanRecord` | rawmap_decode.py:378-408 | odo 3 + dist/angle/rssi + header |
| `OdoRecord` | rawmap_decode.py:412-431 | ts·x·y·w·vx·vy·vw |
| `LocalizationRecord` | rawmap_decode.py:435-454 | header·x·y·angle·confidence·correction_errs |
| `MapLog` | rawmap_decode.py:458-529 | 파일 1개 전체 |

## 함수표 — `rawmap_info.py`

| 함수 | 위치 | 인자 → 반환 | 용도 | 부수효과 |
| --- | --- | --- | --- | --- |
| `collect_rawmap_paths` | rawmap_info.py:46-69 | `List[str]` → `List[str]` | 파일/디렉터리 → `.rawmap` 경로 | 디렉터리 listdir |
| `summarize` | rawmap_info.py:72-114 | `MapLog` → `Dict` | JSON 직렬화 가능 요약 | `os.path.getsize` |
| `_file_size` | rawmap_info.py:117-122 | `str` → `Optional[int]` | 크기 조회(실패 시 None) | stat |
| `_fmt_beams` | rawmap_info.py:125-131 | `List[int]` → `str` | 빔 수 축약 표기 | 없음 |
| `_fmt_bbox` | rawmap_info.py:134-139 | `Optional[List[float]]` → `str` | bbox 표기 | 없음 |
| `format_table` | rawmap_info.py:142-183 | `List[Dict]` → `str` | 고정폭 표 렌더 | 없음 |
| `_sort_rows` | rawmap_info.py:186-194 | `(List[Dict], str)` → `List[Dict]` | 정렬 | 없음 |
| `main` | rawmap_info.py:197-252 | `Optional[List[str]]` → `int` | CLI 진입점 | stdout/stderr 출력 |

## 함수표 — `rawmap_to_jsonl.py`

| 함수 | 위치 | 인자 → 반환 | 용도 | 부수효과 |
| --- | --- | --- | --- | --- |
| `scan_to_record` | rawmap_to_jsonl.py:40-57 | `ScanRecord` → `Dict` | 재생 레코드 1개 생성(키 순서 계약) | 없음 |
| `iter_records` | rawmap_to_jsonl.py:60-76 | `(MapLog, int)` → `Iterator[Dict]` | stride 적용 순회 | 없음 |
| `build_meta` | rawmap_to_jsonl.py:79-119 | `(MapLog, int, int)` → `Dict` | 사이드카 메타 | 없음 |
| `write_jsonl` | rawmap_to_jsonl.py:122-138 | `(MapLog, IO[str], int)` → `int` | 스트림에 JSONL 기록 | 스트림 write |
| `_open_output` | rawmap_to_jsonl.py:141-145 | `(str, bool)` → `IO[str]` | 평문/gzip 출력 열기 | 파일 생성 |
| `main` | rawmap_to_jsonl.py:148-221 | `Optional[List[str]]` → `int` | CLI 진입점 | 파일 write, stdout |

## 전역변수표

**가변 전역 0개.** 전부 모듈 상수(불변)이며 writer 없음 — 런타임에 재대입하는 코드가 없다
(`grep -nE '^(WIRE_|_|[A-Z])[A-Z_0-9]* *=' *.py` 로 열거, 함수 내 재대입 0건).

| 이름 | 위치 | 값/의미 | 누가 바꾸나 |
| --- | --- | --- | --- |
| `WIRE_VARINT`/`WIRE_FIXED64`/`WIRE_LENGTH_DELIMITED`/`WIRE_START_GROUP`/`WIRE_END_GROUP`/`WIRE_FIXED32` | rawmap_decode.py:59-64 | protobuf wire type 0·1·2·3·4·5 | 없음(상수) |
| `_VARINT_PAYLOAD_MASK`·`_VARINT_CONTINUATION_BIT`·`_VARINT_SHIFT_PER_BYTE`·`_VARINT_MAX_BYTES` | rawmap_decode.py:66-69 | 0x7F·0x80·7·10 | 없음 |
| `_TAG_WIRE_TYPE_MASK`·`_TAG_FIELD_NUMBER_SHIFT` | rawmap_decode.py:70-71 | 0x07·3 | 없음 |
| `_FIXED64_SIZE`·`_FIXED32_SIZE` | rawmap_decode.py:73-74 | 8·4 [byte] | 없음 |
| `_NSEC_PER_SEC` | rawmap_decode.py:76 | 1e9 [ns/s] | 없음 |
| `_MapLogField`·`_MapLogDataField`·`_MapOdoField`·`_HeaderField`·`_LocalizationField` | rawmap_decode.py:80-155 | 필드 번호 네임스페이스(`.proto` 인용) | 없음 |
| `_HEADER_WIRE_SHAPE`·`_LOCALIZATION_REQUIRED_DOUBLES` | rawmap_decode.py:533-543 | 스키마 판별 기준 | 없음 |
| `_MODELLED_TOP_LEVEL_FIELDS` | rawmap_decode.py:708-725 | 디코더가 모델링한 top-level 필드 집합 | 없음 |
| `RAWMAP_SUFFIX`·`_DEG_PER_RAD`·`_BYTES_PER_MIB`·`_SORT_KEYS`·`_TABLE_COLUMNS` | rawmap_info.py:22-43 | CLI 표기 상수 | 없음 |
| `_DEG_PER_RAD`·`META_SUFFIX`·`GZIP_SUFFIX`·`DEFAULT_STRIDE` | rawmap_to_jsonl.py:34-37 | 내보내기 상수 | 없음 |

## 의존성

표준 라이브러리만: `struct`·`dataclasses`·`enum`·`typing`(decode), `argparse`·`json`·`math`·`os`·`sys`(info),
`+gzip`(jsonl). 외부 패키지 0 — `protobuf` 런타임 불요.
