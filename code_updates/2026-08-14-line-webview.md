# 2026-08-14 — 라인 인식 실카메라 확인 + `line_webview` 웹 뷰어 신설

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: HAL(Hardware Abstraction Layer) · MJPEG(Motion Joint Photographic Experts Group) ·
> QoS(Quality of Service) · SVG(Scalable Vector Graphics) · DOM(Document Object Model)

- 사용자 지시: 2026-08-14 "이제 후방 카메라를 구동해서 라인 인식 여부를 확인해주세요" →
  "web gui 만들어서 구동 인식 하도록 해봅시다"
- 인벤토리: `docs/code_review/ai-line-webview/2026-08-14.md`(루트 정본) + 패키지 병기
- 신설 패키지: `src/AI/ui/line_webview/` (ament_python)

## 1. 실카메라 라인 인식 확인 — 요청한 후방은 불가, 전방으로 대체

**후방 카메라(`cam_r`, AY4EC5400J3)가 물리적으로 연결돼 있지 않다.** 로스터 6대 중 3대만
붙어 있다(`cam_rf`·`cam_rr`·`cam_f`). `cam_lf`·`cam_lr` 도 빠졌다. 소프트웨어 문제가 아니다.

연결된 전방 카메라로 같은 파이프라인을 돌린 결과:

| 항목 | 실측 |
| --- | --- |
| 카메라 | 1280×720@26.5 FPS, `grab_failures=0` |
| 인식률 | **24.4 Hz · detected 100%** (489/489), GPU 91% |
| 신뢰도 | conf 0.97~0.98 |
| offset | −0.155 (기준행 y=576 에서 라인 x≈540px → `(540−640)/640 = −0.156` 과 일치) |
| angle | +0.20 rad (11.5°) |

**이식한 가중치가 전이됐다.** 타 기체에서 640×480 으로 학습한 모델이 이 기체 1280×720
화각에서 바닥 테이프를 잡는다. 영상이 정립이므로 이 카메라는 `flip_180: false` 가 맞다.

⚠ **처음 잰 2.3 Hz 는 계측 아티팩트였다** — 계측기가 `/line/debug_image` 를 구독하는 순간
인식 노드가 720p 오버레이를 재인코딩한다. 구독을 끊으니 24.4 Hz. 뷰어를 그 경로로 만들면
안 된다는 근거가 됐다(§2).

## 2. `line_webview` — 브라우저로 보는 라인 인식

`cctv_webview` 의 규약을 그대로 따른다: 카메라가 준 JPEG 를 **디코드 없이** multipart MJPEG
로 흘리고, 오버레이는 **브라우저가 SVG 로** 그린다. 서버가 그리면 §1 에서 실측한 그 비용
(24.4 → 2.3 Hz)을 그대로 문다.

| 파일 | 내용 |
| --- | --- |
| `line_webview/line_state.py` (87줄) | 최신 오차·수신율 보관 + 오버레이 좌표 계산 (ROS 무의존) |
| `line_webview/server.py` (267줄) | HTTP — `/` · `/stream/<cam>` · `/line` · `/status` · `POST /direction` |
| `line_webview/app.py` (170줄) | ROS 노드 — 카메라 2대·`/line/error` 구독, 인식 노드 파라미터 전환 |
| `launch/line_webview.launch.py` · `test/test_line_state.py` (14건) | 기동·시험 |

- **프레임 저장은 `cctv_webview.frame_store.FrameStore` 재사용** — 같은 자료구조를 두 벌 두면
  갈라진다. 스트리밍 핸들러는 화면 구성이 달라(타일 격자 vs 단일 영상+오버레이) 공유하지 않았다
- 화면에서 **전진/후진 카메라를 전환**한다 — 인식 노드의 `direction` 파라미터를
  `rcl_interfaces/SetParameters` 로 바꾼다. 제어(`line_follow` 의 `reverse` goal)에는 관여하지 않는다
- 오차 나이가 500 ms 를 넘으면 「낡음」으로 표시하고 오버레이를 숨긴다 — 멈춘 값이
  현재처럼 보이면 안 된다

## 시각 확인이 찾아낸 결함 1건 (수정 완료)

`angle` 은 **픽셀 좌표계** 기울기인데 정규화(0~1) 좌표로 옮기면서 종횡비 보정을 빠뜨렸다.
16:9 화면에서 `tan(angle)` 을 그대로 쓰면 기울기가 **1.78배** 가팔라져, 제어점에서만 맞고
위로 갈수록 라인에서 벌어진다. `centerline_points` 에 `aspect` 인자를 넣어
`tan(angle)/aspect` 로 고치고 노드 파라미터 `image_aspect`(기본 1280/720)로 배선했다.

**수치만 봤으면 못 잡았다** — `/line` JSON 의 offset·angle·conf 는 전부 정상이었고, 제어점
좌표도 맞았다. 실프레임에 그려 보고서야 선이 어긋난 것이 보였다.

## 검증

| 항목 | 결과 |
| --- | --- |
| colcon 빌드 | `line_webview` 오류 0 |
| 단위 테스트 | **14 passed** (종횡비 보정·나이·수신율·클램프 포함) |
| `/line` | 실측치 반환 (detected · offset −0.155 · conf 0.974 · hz 24.8 · age 20.8 ms + geom) |
| `/stream/<cam>` | HTTP 200 multipart, JPEG 패스스루 |
| 방향 전환 | `POST /direction reverse` → `{"ok":true,"camera":"cam_r"}`, 인식 노드 전환 확인. `cam_r` 프레임이 없어 오차 나이 3,019 ms → UI 「낡음」. `forward` 복귀 시 25 Hz |
| 오버레이 기하 | 브라우저와 같은 식으로 실프레임 렌더 후 육안 대조 — 보정 전 어긋남 / 보정 후 일치 |

**브라우저 동작은 사용자가 확인했다(2026-08-14, 「잘되네요」)** — 저자는 이 호스트에서
확인할 수 없었다(firefox 가 snap 이라 헤드리스 캡처가 `cap_dac_override not found` 로 막힌다).
DOM·SVG 오버레이·스트림·수치판이 사람 관찰로 검증됐다.

**미검증**: 후방 카메라 표시 — 장치 미연결로 전환 경로만 확인했다. 주행 중 검출률도 별개다.

최종 verdict 는 저자가 찍지 않는다 (`coding.md:89` never-self-approve).
