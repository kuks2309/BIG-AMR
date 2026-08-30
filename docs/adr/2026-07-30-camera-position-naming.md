# ADR — USB CCTV 카메라 이름을 장착 위치 기준으로 개명

- **Status**: Accepted — 2026-07-30
- 대상: `config/camera/camera_common.yaml`(로스터 SSOT), `src/Sensors/Camera/USB/**`, `src/AI/yolo_detector/launch/**`, `Tools/usb_cam_bench/**`
- 관련: [usb_cctv ADR 0001](../usb_cctv/adr/0001-usb-cctv-architecture.md), [CCTV AI 오버레이 토글](2026-07-28-cctv-ai-overlay-toggle.md)

## 배경

카메라 6대가 `cam0`~`cam5` 로 이름 붙어 있었다. 이름은 **발견 순서**(장착 순서도 아니다)라서
화면·토픽·로그를 보고 어느 방향 카메라인지 알 수 없었다. 특히 2x3 뷰어 그리드가 로스터 순서로
그려지므로 화면 배치가 물리 배치와 어긋났다(`RF LF RR / F R LR`).

사용자가 2026-07-30 장착 위치별 시리얼 표를 확정했다(전면 1 / 후면 1 / 좌 2 / 우 2).

## 결정

로스터의 `name` 을 **장착 위치 코드**로 바꾼다. 토픽·frame_id·노드명이 모두 여기서 파생된다.

| 종전 | 위치 | 표기 | 시리얼 | 새 이름 |
| --- | --- | --- | --- | --- |
| cam0 | 우측 전방 | RF | AY4EC5400HL | `cam_rf` |
| cam1 | 좌측 전방 | LF | AY4EC5400H0 | `cam_lf` |
| cam2 | 우측 후방 | RR | AY4EC5400NR | `cam_rr` |
| cam3 | 전면 | F | AY4EC5401F4 | `cam_f` |
| cam4 | 후면 | R | AY4EC5400J3 | `cam_r` |
| cam5 | 좌측 후방 | LR | AY4EC5401BT | `cam_lr` |

**로스터 순서는 바꾸지 않는다 — 이름만 바꾼다.** 뷰어 2x3 그리드가 로스터 순서로 그려지므로
화면 배치는 현재와 동일하게 유지된다(`RF LF RR / F R LR`). 물리 배치와 어긋나는 이 순서 문제는
**사용자 결정으로 향후 별건 수정**한다(2026-07-30). 개명만으로도 각 칸에 위치가 표시되므로
어느 방향인지는 화면에서 바로 읽힌다.

향후 적용할 순서(참고):

```
cam_lf   cam_f   cam_rf
cam_lr   cam_r   cam_rr
```

### 이름 형식을 `cam_<위치>` 로 한 이유

사용자 표기는 `F`/`RF`/… 이지만 토픽에는 접두사를 붙였다.

- ROS 2 토픽·노드명 관례가 소문자다. `/F/image_raw` 는 유효하지만 관례에서 벗어난다.
- 접두사가 있어야 `ros2 topic list | grep cam` 이 계속 동작한다(기존 절차·문서가 이 패턴을 쓴다).
- `/r/image_raw`(후면) 처럼 한 글자 토픽은 `/rr`(우후)과 눈으로 구분하기 어렵다.

## 대안과 기각 사유

- **`cam0~5` 유지 + 표시명만 위치로** — 토픽·로그·bag 은 그대로라 호환성이 가장 좋지만, `ros2 topic hz`·
  rosbag 재생 같은 **도구 경유 관측에서는 여전히 방향을 알 수 없다**. 사용자가 토픽까지 개명을 선택했다.
- **`/F/image_raw` (접두사 없음)** — 위 이름 형식 사유로 기각.

## 파급 (개명이 조용히 깨뜨리는 곳)

로스터에서 파생되는 구성요소는 자동으로 따라오지만, **로스터를 읽지 않는 곳**이 있었다.

1. `src/AI/yolo_detector` — `detector_node.DEFAULT_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]`
   이고 `detect.launch.py` 가 `camera_topics` 를 넘기지 않았다. 개명 후에도 탐지기는 없는 토픽을
   구독해 **에러 없이 검출 0** 이 된다. → 런치가 공용 로스터를 읽어 `camera_topics` 를 넘기도록 수정.
2. `Tools/usb_cam_bench/soak_stats.py` — 로그 파서 정규식이 `cam\d+` 로 이름 형식을 가정했다.
   → 임의 이름(`[A-Za-z0-9_]+`)을 받도록 일반화. `soak_monitor.py` 도 `cam{i}` 생성 대신
   **로스터에서 이름을 읽는다**.
3. `src/Sensors/Camera/USB/ui/vision_guard/launch/vision_guard.launch.py` 의 `_FALLBACK_TOPICS`
   (로스터 미발견 시 사용) — 새 이름으로 갱신.

## 남긴 것 (의도적)

- `src/Sensors/Camera/USB/usb_cam_publisher/config/cameras.yaml`(레거시 4대 fallback) 은 손대지 않았다.
  공용 로스터가 있으면 사용되지 않는 경로이고, 소유 세션이 다르다. 이 파일이 쓰이는 상황이면
  4대만 뜨는 기존 위험이 그대로다(그 위험은 `vision_guard.launch.py:7` 이 이미 경고한다).
- 과거 기록·보고서의 `cam0~cam5` 표기는 **그 시점 사실**이라 고치지 않는다. 대응표는 위 표가 정본이다.

## Rollback Plan

로스터의 `name` 6개를 종전 값(`cam0`~`cam5`)으로 되돌리고 순서를 복원한 뒤 재기동하면 원상복구된다.
`detect.launch.py`·`soak_stats.py`·`soak_monitor.py` 변경은 이름 형식과 무관하게 동작하므로
되돌릴 필요가 없다(로스터를 읽는 쪽이 더 안전한 구조다).

## 시리얼 표기 확인 1건

사용자 표의 `LF = AY4EC5400HD` 는 실제 장치와 일치하지 않는다. `by-id` 심링크와 `udevadm`
두 경로 판독 결과 모두 **`AY4EC5400H0`** 이며 `HD` 로 끝나는 장치는 연결돼 있지 않다. 나머지 5개는
표와 정확히 일치한다. 숫자 `0` 을 `D` 로 옮겨 적은 것으로 보아 `H0` 을 채택했다 —
**브래킷 실물 표기 확인이 남았다.**
