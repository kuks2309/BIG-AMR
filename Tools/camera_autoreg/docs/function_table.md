# camera_autoreg — 함수표 (모듈 권위본)

> 대상: `Tools/camera_autoreg/` — 카메라 자동 등록(마커 기반 위치 식별) 도구.
> 1단계(본 표): ChArUco 보드 1~6 생성. 2단계(추후): 보드 인식 → 시리얼↔위치 매핑 → 로스터/udev 규칙 생성.
> 번호 규약(사용자 결정 2026-08-31): ROS2 좌표계처럼 전방=1, 반시계 —
> 1=cam_f(전방)·2=cam_lf(좌전방)·3=cam_lr(좌후방)·4=cam_r(후방)·5=cam_rr(우후방)·6=cam_rf(우전방).
> 매체 결정(사용자 2026-08-31): 단일 ArUco 가 아니라 **ChArUco**(체스보드+ArUco) — 식별 + 캘리브레이션 겸용.
> 자산 활용 결정(사용자 제안 2026-08-31): `Tools/CameraCalibration/make_charuco_pdf.py` 의 실치수 PDF
> 렌더 방식을 재사용(import). 단 기존 보드 6종은 **전부 ID 0 시작이라 보드 구분 불가** —
> 등록 전용 6장은 보드별 고유 ID 대역을 부여해 새로 뽑는다(같은 사전 DICT_5X5_1000 유지).

## 함수표 — generate_boards.py (ChArUco 보드 생성 + 자가 검증)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `board_marker_ids` | `board_marker_ids(board_no: int) -> np.ndarray` | 보드 n 의 마커 ID 대역 `500+(n-1)*20 .. +17` (18개, 캘리브레이션 보드 ID 0~84 와 분리) — 역산 규칙의 짝 | generate_boards.py:50-55 |
| `board_number_from_marker_id` | `board_number_from_marker_id(marker_id: int) -> int` | 검출된 마커 ID → 보드 번호(`(id-500) // 20 + 1`, 대역 밖·캘리브레이션 ID 는 0) — 2단계 인식 스크립트가 재사용할 단일 근원 | generate_boards.py:57-62 |
| `make_board` | `make_board(board_no: int) -> cv2.aruco.CharucoBoard` | 6×6칸·칸 30mm·마커 21.6mm(ratio 0.72, CameraCalibration 과 동일)·고유 ID 대역 보드 객체 | generate_boards.py:65-70 |
| `render_board_pdf` | `render_board_pdf(board_no: int, out_dir, dpi) -> str` | 보드 → 실치수 PDF(100% 인쇄 시 칸 30mm) + 큰 번호·카메라명 라벨 + 100mm 스케일바 (`make_charuco_pdf.mm_to_px` 재사용) | generate_boards.py:73-115 |
| `self_test` | `self_test(board_no: int) -> list[str]` | 보드 비트맵을 재생성해 CharucoDetector 로 재검출 — 마커 ID 전부 해당 대역·역산 보드 번호 일치·전수 검출 확인 | generate_boards.py:118-139 |
| `main` | `main(argv=None) -> int` | `--out`(기본 boards/)·`--dpi`(기본 300) → 6장 생성 → 자가 검증 → 결과 표 출력 | generate_boards.py:142-162 |

## 함수표 — register_cameras.py (2단계: 인식 → 매핑 → 로스터·udev 생성)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `detect_board_votes` | `detect_board_votes(gray) -> collections.Counter` | 한 프레임에서 마커 검출(DICT_5X5_1000) → `board_number_from_marker_id` 로 보드 번호 득표 집계(무소속 ID 0 은 버림) | register_cameras.py:44-55 |
| `decide_board` | `decide_board(votes: Counter, min_votes: int) -> int \| None` | 카메라 1대의 누적 득표 → 보드 판정(최다 득표, 임계 미만·동률이면 None) | register_cameras.py:58-68 |
| `build_mapping` | `build_mapping(observed: dict[str, int \| None]) -> tuple[dict[str, str], list[str]]` | 시리얼→보드 관측 → (위치명→시리얼 매핑, 오류 목록[중복 보드·미검출·미배정 위치]) | register_cameras.py:71-95 |
| `render_udev_rules` | `render_udev_rules(mapping: dict[str, str]) -> str` | 매핑 → udev 규칙 텍스트(`ATTRS{serial}`·`ATTR{index}=="0"` → `SYMLINK+="camera/<위치명>"`) | register_cameras.py:98-112 |
| `rewrite_roster_serials` | `rewrite_roster_serials(yaml_text: str, mapping) -> str` | 로스터 yaml 의 `- name:`/`serial:` 줄만 표적 치환(주석·구조 보존) — yaml.dump 재직렬화 금지 | register_cameras.py:115-132 |
| `grab_frames_topics` | `grab_frames_topics(cameras, frames_per_cam, timeout_sec) -> dict[str, list]` | 기본 소스 — 구동 중인 퍼블리셔의 `<name>/image_raw/compressed` 구독, 카메라별 N프레임 수집(JPEG 디코드는 여기서만) | register_cameras.py:141-178 |
| `discover_devices` | `discover_devices(by_id_prefix: str) -> list[str]` | `/dev/v4l/by-id/` 실스캔으로 **연결된 카메라의 시리얼을 직접 읽는다**(로스터 무의존 — 신품·교체 카메라도 등록 가능). 시리얼 = 개체 영속 키(향후 시리얼별 내부 캘리브레이션 파일 매칭 예정) | register_cameras.py:181-197 |
| `grab_frames_devices` | `grab_frames_devices(serials, by_id_prefix, frames_per_cam) -> dict[str, Counter]` | `--source device` — 발견된 장치 직접 개방(usb-cam@ 활성 시 중단 안내, EBUSY 방지) | register_cameras.py:200-229 |
| `main` | `main(argv=None) -> int` | 로스터 로드(camera_service/camera_params 재사용) → 프레임 수집 → 판정 표 출력 → `out/` 에 제안 로스터·udev 규칙 생성, `--apply` 시 로스터 백업 후 갱신 | register_cameras.py:232-304 |

## 테스트 표

| 파일 | 용도 | 위치 |
| --- | --- | --- |
| `test_register_cameras.py` | 순수 로직 검증 — 합성 보드 비트맵 검출 득표, 판정(임계·동률·미달), 매핑(정상 6대·중복 보드·미검출·누락 위치), udev 규칙 텍스트, 로스터 표적 치환(주석 보존·시리얼만 교체) | test_register_cameras.py:1 |

## 토픽 표 (register_cameras.py — 소비만, 발행 없음)

| 토픽 | 타입 | QoS | 방향 | 위치 |
| --- | --- | --- | --- | --- |
| `<로스터 name>/image_raw/compressed` ×6 | `sensor_msgs/CompressedImage` | sensor_data(best-effort) | 구독(등록 실행 중 한시) | register_cameras.py:141-178 |

## 전역변수표

| 이름 | 타입 | 용도 | 위치 |
| --- | --- | --- | --- |
| `BOARD_MAP` | `dict[int, tuple[str, str]]` | 보드 번호 → (카메라 논리명, 한글 위치) — 번호 규약의 단일 근원 | generate_boards.py:28-36 |
| `ARUCO_DICT_NAME` | `str` | `DICT_5X5_1000` — CameraCalibration 기존 보드와 동일 사전(혼용 대비), ID 1000개라 대역 충분. 2단계 인식도 이 값을 따라야 함 | generate_boards.py:39 |
| `SQUARES`·`SQUARE_MM`·`MARKER_RATIO` | `int`/`float` | 보드 기하 6×6·30mm·0.72 — 외곽 180mm(A4 세로 여유), 마커 21.6mm(≤1m 검출 전제) | generate_boards.py:40-42 |
| `IDS_PER_BOARD` | `int` | 보드당 ID 대역 폭 20(6×6 보드 마커 18개 + 여유 2) — 역산 나눗셈의 제수 | generate_boards.py:43 |
| `BOARD_ID_OFFSET` | `int` | 등록 보드 ID 시작점 500 — 캘리브레이션 보드(ID 0~84)와 완전 분리해 시야 오인 차단 | generate_boards.py:47 |
