# cctv_webview — 브라우저로 보는 CCTV 뷰어

카메라가 준 JPEG 를 **디코드하지 않고** 그대로 브라우저에 흘린다. 디코드는 보는 사람의
브라우저가 하므로 로봇 PC 는 표시 비용을 거의 쓰지 않는다.

```
/<cam>/image_raw/compressed  ──(바이트 그대로)──>  HTTP multipart MJPEG  ──> 브라우저
```

설계 근거·실측은 [ADR 2026-08-03](../../../../../docs/adr/2026-08-03-mjpeg-passthrough-web-viewer.md).

## 한 줄 실행

퍼블리셔(압축 모드)가 먼저 떠 있어야 한다 — [상위 README](../../README.md) 참조.

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch cctv_webview cctv_webview.launch.py
```

퍼블리셔까지 한 번에:

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch usb_cam_publisher usb_cam_cctv.launch.py & sleep 12 && cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && ros2 launch cctv_webview cctv_webview.launch.py
```

브라우저에서 **http://localhost:8080/** (다른 PC 에서는 로봇 IP 로 접속).

## 화면 배치

차량을 위에서 내려다본 배치다 — **화면 왼쪽이 차량 왼쪽, 위가 전방**이라 방향을 바꿔 생각할
필요가 없다. 가운데는 차체(▲ Big AMR) 표시다.

```
          전면 F
  좌전 LF  [차체]  우전 RF
  좌후 LR  [차체]  우후 RR
          후면 R
```

여섯 장착 위치(`cam_f`·`cam_r`·`cam_lf`·`cam_lr`·`cam_rf`·`cam_rr`)가 로스터에 모두 있을 때만
이 배치를 쓴다. 카메라를 빼거나 이름이 다르면 순서대로 흐르는 격자로 물러난다 — 위치를 모르는
카메라를 임의 자리에 놓으면 방향을 오독하기 때문이다. 좁은 화면(<860px)에서는 한 줄씩 세운다.

## AI 검출 표시

헤더의 `AI 표시` 체크박스로 켜고 끈다(기본 켜짐). 탐지기(`yolo_detector`)가 발행하는
`/cam_*/detections` 를 구독해 **좌표만** 브라우저로 넘기고 **박스는 브라우저가 그린다** —
서버가 영상에 그리려면 JPEG 를 디코드·재인코딩해야 하므로 이 뷰어의 전제가 무너진다.

박스 나이 기준은 Qt 뷰어와 같다:

| 나이 | 표시 |
| --- | --- |
| < 150 ms | 초록 실선 |
| 150 ~ 400 ms | 노란 점선(낡음) |
| > 400 ms | 표시하지 않음 + 제목에 "검출 낡음" |

탐지기가 떠 있지 않으면 박스만 없고 영상은 정상이다.

## 옵션

```bash
ros2 launch cctv_webview cctv_webview.launch.py port:=8080 stream_hz:=15.0 bind:=127.0.0.1
```

| 인자 | 기본 | 뜻 |
| --- | --- | --- |
| `port` | 8080 | HTTP 포트 |
| `bind` | 0.0.0.0 | 접속 허용 범위. **기본값은 같은 망 누구나 접속 가능** — 로컬만 열려면 `127.0.0.1` |
| `stream_hz` | 10.0 | 시청자당 스트림 상한. 대역·부하를 정한다(실측 6대 x 10 Hz = 8.1 MB/s) |

구독 토픽은 공용 로스터(`config/camera/camera_common.yaml`)에서 파생하므로 카메라를
추가·개명해도 이 노드는 따라온다.

## 엔드포인트

| 경로 | 내용 |
| --- | --- |
| `/` | 카메라 격자 페이지(위치 이름 표시) |
| `/stream/<cam>` | multipart MJPEG 스트림 (예: `/stream/cam_lf`) |
| `/snapshot/<cam>` | 최신 프레임 1장 (JPEG) |
| `/status` | 카메라별 누적 수신·프레임 크기·마지막 수신 경과(JSON) |
| `/detections` | 카메라별 최신 검출 박스·원본 해상도·경과(JSON). 브라우저가 이걸 받아 그린다 |

확인:

```bash
curl -s http://localhost:8080/status | python3 -m json.tool
curl -s -o /tmp/snap.jpg -w "%{http_code} %{size_download}\n" http://localhost:8080/snapshot/cam_f
```

## 시험 (카메라 불필요)

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Sensors/Camera/USB/ui/cctv_webview && PYTHONPATH=. python3 -m pytest test -q
```

## 알아둘 것

- **인증이 없다.** 기본 `bind=0.0.0.0` 이라 같은 망의 누구나 볼 수 있다.
- 프레임은 카메라당 1장만 보관하고 덮어쓴다 — 느린 시청자가 있어도 메모리가 늘지 않는다
  (2026-07-27 Qt 뷰어 OOM(Out Of Memory) 선례를 되풀이하지 않기 위한 설계).
- 퍼블리셔가 `publish_mode: raw` 면 압축 토픽이 없어 화면이 비어 있다. `/status` 가 빈 `{}` 이거나
  노드 로그에 "아직 수신한 프레임이 없다" 경고가 나오면 그 경우다.
