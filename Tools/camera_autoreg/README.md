# camera_autoreg — 카메라 자동 등록 (마커 기반 위치 식별)

카메라 6대의 **장착 위치를 ChArUco 보드로 자동 판별**해 로스터·USB(udev) 규칙의
초기 설정을 만드는 도구. 1단계 = 보드 생성(`generate_boards.py`),
2단계 = 인식·매핑·규칙 생성(`register_cameras.py`).

**시리얼은 카메라 개체의 영속 식별자다** — 위치명(cam_f 등)은 장착이 바뀌면 따라
바뀌지만 시리얼은 카메라를 따라간다. 향후 시리얼별 내부 파라미터 캘리브레이션
파일 매칭도 이 키를 쓴다(구현 예정).

## 번호 규약 (사용자 결정 2026-08-31)

ROS2 좌표계처럼 **전방 = 1, 반시계 방향**:

| 보드 | 카메라 | 위치 | 마커 ID 대역 |
| --- | --- | --- | --- |
| 1 | cam_f | 전방 | 500..517 |
| 2 | cam_lf | 좌전방 | 520..537 |
| 3 | cam_lr | 좌후방 | 540..557 |
| 4 | cam_r | 후방 | 560..577 |
| 5 | cam_rr | 우후방 | 580..597 |
| 6 | cam_rf | 우전방 | 600..617 |

마커 하나만 검출돼도 `(ID−500)÷20+1 = 보드 번호`. ID 500 미만은 캘리브레이션
보드(`Tools/CameraCalibration/charuco_boards/`, 전부 ID 0 시작) 몫이라 등록
판정에서 자동 배제된다 — 시야에 캘리브레이션 보드가 남아 있어도 오인하지 않는다.

## 보드 생성·인쇄

```bash
python3 Tools/camera_autoreg/generate_boards.py    # boards/ 에 PDF 6장 + 자가 검증
```

- ChArUco 6×6칸, 칸 30mm(보드 180mm) — A4 세로, **배율 100%(맞춤 없음)로 인쇄**.
  인쇄 후 하단 스케일바가 자로 100mm 인지 확인.
- 사전 `DICT_5X5_1000` — 캘리브레이션 보드와 동일(검출기 설정 한 벌).
- 개별 마커 21.6mm: 720p 기준 **약 1m 이내**에 보드를 놓아야 안정 검출.
- 각 장 하단에 큰 번호·카메라명 라벨 — 현장에서 몇 번인지 눈으로 확인.

## 등록 절차 (2단계 — register_cameras.py)

1. 보드 6장을 각 카메라 앞(≤1m)에 번호 규약대로 배치(주변에 다른 보드가 겹쳐
   보이지 않게).
2. 인식 실행:

```bash
python3 Tools/camera_autoreg/register_cameras.py            # 판정 + 제안 파일(dry-run)
python3 Tools/camera_autoreg/register_cameras.py --apply    # 로스터 백업 후 실제 갱신
```

- 기본 소스는 **ROS 토픽**(usb-cam@ 가 장치를 잡고 있어도 동작 — 로스터가 틀려도
  이름↔시리얼 대응만 쓰므로 무방). 퍼블리셔가 꺼져 있으면
  `--source device` 로 by-id 장치를 직접 스캔·개방한다(신품·교체 카메라 등록 경로).
- 판정: 카메라별 N프레임(기본 10)에서 마커 득표, 최다 보드(임계 3표·동률 불가).
  미검출·중복·누락이 하나라도 있으면 오류 목록을 내고 `--apply` 를 거부한다.
- **장착 방향도 같은 프레임에서 판별한다** — 마커 코너의 정준 순서로 180° 뒤집힘을
  득표 판정(보드를 바로 세워 둔다는 전제). 결과는 로스터 `flip: true` 필드로 반영되고,
  뒤집기 보정은 소비자(cctv_webview CSS 회전·yolo_detector 디코드 직후 회전) 몫이다.
  위치가 확정됐는데 방향이 불확정이면 오류로 `--apply` 를 거부한다.
3. 산출물(`out/`):
   - `camera_common.proposed.yaml` — 제안 로스터(주석·구조 보존, serial 만 교체).
     `--apply` 시 원본을 `.bak-일시` 로 백업 후 갱신 → `camctl restart all` 로 반영.
   - `99-amr-cameras.rules` — 시리얼 기반 `/dev/camera/<위치명>` 심링크 udev 규칙.
     설치(sudo): `sudo cp out/99-amr-cameras.rules /etc/udev/rules.d/ &&
     sudo udevadm control --reload-rules && sudo udevadm trigger`

함수표: [docs/function_table.md](docs/function_table.md)
