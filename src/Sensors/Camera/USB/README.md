# USB CCTV — 6대 카메라 구동·표시

Orbbec Gemini E RGB 6대를 ROS2 로 발행하고 PyQt5 그리드 뷰어(AMR VisionGuard)로
동시에 띄운다. 상세 배경·성능 기록은 `docs/usb_cctv/` 참조.

| 구성 | 경로 |
| --- | --- |
| 퍼블리셔(C++) | `src/Sensors/Camera/USB/usb_cam_publisher` |
| 뷰어(Python/PyQt5) | `src/Sensors/Camera/USB/ui/vision_guard` |
| 카메라 로스터(SSOT) | `config/camera/camera_common.yaml` |
| 벤치·내구 도구 | `Tools/usb_cam_bench` |

## 한 줄 실행

퍼블리셔 6대 + 뷰어(2x3)를 한 번에 띄운다 — **터미널 1개로 충분**:

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch usb_cam_publisher usb_cam_cctv.launch.py & sleep 10 && DISPLAY=:0 ros2 launch vision_guard vision_guard.launch.py layout:=2x3
```

터미널을 나눠 쓰는 편이 로그를 읽기 쉽다:

```bash
# 터미널 1 — 퍼블리셔 (로스터에 등록된 전 카메라, 현재 6대)
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch usb_cam_publisher usb_cam_cctv.launch.py

# 터미널 2 — 뷰어 (2x3 그리드)
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch vision_guard vision_guard.launch.py layout:=2x3
```

종료: 각 터미널 `Ctrl+C`. **`kill -9` 금지** — SIGKILL 로 뷰어를 죽이면 FastDDS 공유메모리
잔재로 일부 카메라가 영구 "No Signal" 이 되고 퍼블리셔 캡처 FPS 까지 떨어진다
(`docs/issues_and_fixes/issues_and_fixes.md` 2026-07-27 [Diag] 항목). SIGKILL 했다면 퍼블리셔도 재기동한다.

## 빌드

```bash
cd /home/nvidia/Project/Ford-CATL-AMR/Big-AMR && source /opt/ros/humble/setup.bash && colcon build --packages-select usb_cam_publisher vision_guard && source install/setup.bash
```

## 확인

```bash
ros2 topic list | grep image_raw          # /cam0~/cam5
ros2 topic hz /cam0/image_raw             # 수신율
```

퍼블리셔 로그의 `capture FPS: 29.7 (grab_failures=0)` 이 캡처 실측이고, 뷰어 화면의 FPS
표기는 지수이동평균이라 실측 렌더율보다 높게 보인다(성능 근거로는 실측 렌더율 사용).

## 카메라 추가·교체

로스터가 단일 근원이다 — `config/camera/camera_common.yaml` 만 고치면 퍼블리셔·뷰어가
함께 따라간다(뷰어 토픽 목록은 이 파일에서 파생, 하드코딩 없음).

```bash
ls /dev/v4l/by-id/    # usb-..._Orbbec_Gemini_E_RGB_Camera_<SERIAL>-video-index0
```

`cameras:` 에 `- name: "camN"` / `serial: "<SERIAL>"` 을 추가한다.

> 참고: `docs/usb_cctv/README.md` 의 "RGB 최대 4대" 제약은 원본 호스트(tr-orin-22, 단일
> USB 2.0 컨트롤러) 기준이며 **이 Tegra 호스트에는 해당하지 않는다** — 6대 동시 구동에서
> 전 카메라 29.7fps·grab_failures 0 을 8.4시간 실측했다
> (`docs/usb_cctv/performance/2026-07-28_soak_8h_issues.md`).

## 내구(soak) 테스트

`Tools/usb_cam_bench/README.md` 참조.
