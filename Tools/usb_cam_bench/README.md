# usb_cam_bench — USB 카메라 벤치·내구 도구

ROS2 없이도 도는 비-ROS 도구 모음. 카메라 구동·표시는
`src/Sensors/Camera/USB/README.md` 참조.

| 파일 | 역할 |
| --- | --- |
| `usb_cam_benchmark.py` | V4L2 직접 캡처 성능 측정(해상도·대수별), CSV+markdown 산출 |
| `bench_stats.py` | 벤치 통계 순수 함수(하드웨어 무관, 테스트 있음) |
| `soak_monitor.py` | 장시간 내구 감시자 — 로그·프로세스 자원을 주기 표본화 |
| `soak_stats.py` | 내구 로그 파싱·요약 순수 함수(하드웨어 무관, 테스트 있음) |
| `apply_camera_controls.sh` | `exposure_dynamic_framerate` 등 V4L2 컨트롤 정규화 |

## 한 줄 실행 — 24시간 내구 감시

퍼블리셔·뷰어를 먼저 띄운 뒤(→ `src/Sensors/Camera/USB/README.md`) 감시자를 붙인다.
감시자는 **구독자를 새로 만들지 않고** 로그만 따라 읽으므로 시험 대상에 부하를 더하지 않는다.

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && LOGDIR=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/usb_cctv_soak_$(date +%F) && mkdir -p $LOGDIR && python3 soak_monitor.py --pub-log $LOGDIR/pub.log --viewer-log $LOGDIR/viewer.log --out-dir $LOGDIR --duration-h 24 --interval 30
```

퍼블리셔·뷰어·감시자를 세션 밖에서 24시간 돌리려면 `setsid nohup` 을 쓴다(터미널이 닫혀도 생존):

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && LOGDIR=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/usb_cctv_soak_$(date +%F) && mkdir -p $LOGDIR && setsid nohup ros2 launch usb_cam_publisher usb_cam_cctv.launch.py > $LOGDIR/pub.log 2>&1 < /dev/null & sleep 12; setsid nohup env DISPLAY=:0 ros2 launch vision_guard vision_guard.launch.py layout:=2x3 > $LOGDIR/viewer.log 2>&1 < /dev/null & sleep 12; cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && setsid nohup python3 soak_monitor.py --pub-log $LOGDIR/pub.log --viewer-log $LOGDIR/viewer.log --out-dir $LOGDIR --duration-h 24 --interval 30 > $LOGDIR/monitor.log 2>&1 < /dev/null &
```

산출물(`--out-dir` 아래):

| 파일 | 내용 |
| --- | --- |
| `soak_samples.csv` | 표본 1행/주기 — 캡처·표시 FPS, RSS·CPU, 프로세스 생존 수, 공유메모리 세그먼트 |
| `soak_report.md` | 완주 후 자동 생성 — 카메라별 min/mean fps, 정지 구간, RSS 증가량 |
| `pub.log` / `viewer.log` | 원시 로그(감시자 입력) |

> **주의**: `soak_report.md` 는 `--duration-h` 를 **완주해야** 생성된다. 중간에 끊기면
> CSV·로그로 수동 재분석해야 한다(2026-07-28 전원 상실 사례).

## 중단된 로그 수동 재분석

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && python3 -c "
import sys; sys.path.insert(0,'.')
from soak_stats import parse_capture_line, parse_display_line, summarize_capture, summarize_display
L='/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/usb_cctv_soak_2026-07-27/'
cap=[p for l in open(L+'pub.log',errors='replace') if (p:=parse_capture_line(l))]
dis=[p for l in open(L+'viewer.log',errors='replace') if (p:=parse_display_line(l))]
print(summarize_capture(cap)); print(summarize_display(dis))"
```

## 벤치마크

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && python3 usb_cam_benchmark.py                        # 640x480/720p/1080p, solo + concurrent
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && python3 usb_cam_benchmark.py --resolutions 1280x720 --duration 8
```

## 테스트 (하드웨어 불필요)

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/usb_cam_bench && python3 -m pytest test_soak_stats.py test_bench_stats.py -q
```
