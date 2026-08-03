# ADR — 카메라 전송을 MJPEG 패스스루로 바꾸고 표시를 웹으로 옮김

- **Status**: Accepted — 2026-08-03 구현·실기 검증 완료
- 대상: `src/Sensors/Camera/USB/usb_cam_publisher`, `src/Sensors/Camera/USB/ui/cctv_webview`(신설),
  `src/AI/yolo_detector`, `config/camera/camera_common.yaml`, `Tools/usb_cam_bench`
- 관련: [usb_cctv ADR 0001](../usb_cctv/adr/0001-usb-cctv-architecture.md),
  [위치 기준 개명](2026-07-30-camera-position-naming.md),
  [소크 8h 문제정리](../usb_cctv/performance/2026-07-28_soak_8h_issues.md)

## 배경 — 무거운 곳이 렌더가 아니었다

사용자 제기: "cctvview CPU 점유율이 매우 높은데… 차라리 web 에서 표시하면 어떨까?"

기존 경로는 카메라의 MJPEG 를 **퍼블리셔가 디코드**해 `bgr8` raw 로 발행하고, 뷰어가 그것을
받아 다시 QImage 로 바꿔 그렸다. 종전 실측에서 아무것도 그리지 않는 카운트 전용 구독자도
CPU 55% 를 썼다는 기록이 이미 있었다 — **렌더가 아니라 디코드·전송이 비용의 본체**라는 신호다.

## 측정 (2026-08-03, 카메라 1대, 1280x720@30, 각 8초 x 2회, `/dev/video8`)

| 경로 | FPS | 프레임당 CPU | 프레임 크기 | 대역 | grab 실패 |
| --- | --- | --- | --- | --- | --- |
| 디코드(종전) | 29.72 | **6.55 ms** | 2,700 KB | 78.4 MB/s | 0 |
| 패스스루 | 29.72 | **0.15 ms** | **131 KB** | **3.8 MB/s** | 0 |

**CPU 44배 · 대역 20.7배** 절감. 두 회차가 6.52/6.55, 0.16/0.15 로 일치했다.

선행 확인 — UVC MJPEG 는 허프만 테이블이 빠진 경우가 있어 디코더가 못 읽을 수 있는데,
이 하드웨어는 **DHT 포함**(마커 `SOF0 DQT DHT SOS`)이고 `cv2.imdecode` 가 성공했으며
버퍼 패딩도 0%(30/30 프레임)였다. 즉 브라우저가 그대로 읽는 정상 JPEG 다.

## 결정

1. **퍼블리셔가 디코드하지 않는다.** `publish_mode` 파라미터 신설(`compressed` 기본 / `raw` / `both`).
   `compressed` 는 `CAP_PROP_CONVERT_RGB=0` 으로 드라이버 버퍼를 받아
   `sensor_msgs/CompressedImage` 로 `<cam>/image_raw/compressed` 에 그대로 흘린다.
2. **표시는 웹으로.** 신설 `cctv_webview` 노드가 압축 토픽을 구독해 **디코드 없이**
   multipart MJPEG 로 서빙한다(`http://<host>:8080/`). 디코드는 보는 사람의 브라우저가 한다.
3. **탐지기는 자기가 쓰는 프레임만 디코드한다.** `image_transport` 파라미터(기본 `compressed`)로
   압축 토픽을 구독하고, 라운드로빈으로 **실제 추론하는 프레임에서만** `imdecode` 한다.
   종전에는 30 Hz 전량이 디코드돼 있었고 실제 추론은 카메라당 약 5 Hz 였다.

`raw` 모드는 지웠지 않고 남겼다 — 픽셀이 필요한 소비자(캘리브레이션·녹화 등)가 생기면
그 소비자만 `both` 로 되돌리면 된다.

## 검증 (실기, 카메라 6대)

- 토픽 `/cam_*/image_raw/compressed` 6개 발행, 캡처 **29.70~29.73 fps · grab_failures 0**
- 웹: `/status` 6대 수신(124~142 KB/프레임), `/snapshot/<cam>` **HTTP 200 image/jpeg** 정상 이미지,
  `/stream/<cam>` 6개 동시 수신에서 각 **정확히 10.0 fps**(총 60 fps, 8.11 MB/s)
- 탐지기: 압축 구독으로 `/cam_rr/detections` **4.99 Hz**(목표 5 Hz), 변환 실패 0
- 단위 시험: `cctv_webview` 11 passed, `soak_stats` 15 passed

### CPU — 표시 경로 4.4배 절감

| 구성 | 종전(raw + Qt 뷰어) | 현재(compressed + 웹) |
| --- | --- | --- |
| 퍼블리셔 6개 | 138.1% | **25.0%** |
| 표시 | 71.9% (Qt 뷰어) | **22.9%** (웹 서버) |
| 합계 | **210.0%** | **47.9%** |

종전 값은 `Log/usb_cctv_run_2026-07-30/soak_samples.csv` 표본 1,330개의 중앙값,
현재 값은 `/proc` jiffies 차분 8초 측정(웹 스트림 6개 x 10 Hz 수신 중)이다.
AI 탐지기는 별도로 103.8% 를 쓰며 이는 대부분 YOLO 추론이다(전송 방식과 무관).

## 파급 — 로스터를 안 읽거나 로그 형식을 가정한 곳

개명 때와 같은 종류의 조용한 결합을 미리 끊었다.

1. `Tools/usb_cam_bench/soak_stats.py` — 캡처 FPS 로그 정규식이 `(grab_failures=N)` 로 **닫는
   괄호까지** 고정돼 있었다. 퍼블리셔가 `decode_failures` 를 덧붙이면서 깨질 상태였으므로
   닫는 괄호 요구를 없애고 회귀 시험을 추가했다.
2. `src/AI/yolo_detector` — raw 전용이었다. compressed 기본 전환과 함께 바꾸지 않으면
   **에러 없이 검출 0** 이 된다(2026-07-30 개명 때와 같은 실패 형태).
3. `cctv_webview` 런치는 처음부터 공용 로스터에서 토픽을 파생한다.

## 화면 배치와 AI 오버레이 (2026-08-03 추가)

사용자 요청으로 웹 화면을 **차량을 위에서 내려다본 배치**로 놓는다 — 화면 왼쪽이 차량 왼쪽,
위가 전방이라 방향을 바꿔 생각할 필요가 없다. 가운데는 비우지 않고 차체(▲ Big AMR)를 표시해
배치가 무엇을 뜻하는지 드러낸다.

```
          전면 F
  좌전 LF  [차체]  우전 RF
  좌후 LR  [차체]  우후 RR
          후면 R
```

- 세 열은 **같은 폭**(`repeat(3,1fr)`)이다. 처음엔 가운데를 `0.5fr` 로 좁혔더니 전면·후면
  타일만 절반 크기가 되어 사용자가 지적했다 — 배치가 크기 차이를 만들면 안 된다.
- 로스터가 여섯 위치를 모두 담을 때만 이 배치를 쓰고, 아니면 순서대로 흐르는 격자로
  물러난다. **위치를 모르는 카메라를 임의 자리에 놓으면 방향을 오독**하기 때문이다.
- 좁은 화면(<860px)에서는 배치를 포기하고 한 줄씩 세운다.

AI 검출도 웹에 표시한다. 단 **서버는 영상에 그리지 않는다** — `/cam_*/detections` 의 좌표를
`/detections` JSON 으로 넘기고 **박스는 브라우저가 그린다**. 서버가 박스를 구우려면 JPEG 를
디코드·재인코딩해야 하므로 이 ADR 의 전제가 무너진다. 박스 나이 기준은 Qt 뷰어와 같다
(신선 <150 ms 초록 실선 / 낡음 150~400 ms 노란 점선 / 만료 >400 ms 미표시).

## 결정된 것 / 남은 것

- **`vision_guard`(Qt 뷰어)는 유지한다**(사용자 결정 2026-08-03). 폐기하지 않는다.
  `image_transport:=compressed` 로 계속 동작하며, 프레임마다 파이썬에서 `imdecode` 하므로
  웹 뷰어보다 무겁다는 점만 알고 쓰면 된다.
- 웹 스트림은 인증이 없다. `bind` 기본값이 `0.0.0.0` 이므로 같은 망에서 누구나 본다.
  운용 망 정책이 정해지면 `bind:=127.0.0.1` 또는 역방향 프록시를 검토한다.
- 타일 6개가 세로로 길어 **후면 R 이 스크롤 아래로 내려간다**(1080p 창 기준). 뷰포트 높이에
  맞춘 축소는 아직 넣지 않았다.

## Rollback Plan

`config/camera/camera_common.yaml` 의 `capture.publish_mode` 를 `raw` 로 되돌리고
탐지기를 `image_transport:=raw` 로 띄우면 종전 경로로 완전히 복귀한다(코드 되돌림 불필요).
웹 뷰어는 종료만 하면 되고, Qt 뷰어는 그대로 동작한다.
