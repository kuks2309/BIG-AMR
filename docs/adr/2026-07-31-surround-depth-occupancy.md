# ADR 2026-07-31 — 6대 depth 카메라 surround 3D 점유맵 (로컬, base_link 기준)

**Status**: Proposed (설계 확정 · 구현 착수). **실기 검증 0** — 아래 Consequences §미검증 참조.
- Date: 2026-07-31
- 관련: docs/adr/2026-07-30-camera-position-naming.md (위치 기반 카메라 명명),
  docs/sw_structure/system-architecture/2026-06-27.md:293-303 (6 카메라 1차 목적 = 3D 충돌 회피),
  docs/usb_cctv/performance/depth/2026-07-22_depth_640x480.md (depth 대역 실측),
  docs/usb_cctv/design/0002-human-detection-rgb-depth-switching.md (baseline 이전 필요성)

## Context

Orbbec Gemini E 6대가 차체 둘레에 장착돼 있고, 현재는 **RGB 인터페이스만** `usb_cam_publisher`
(V4L2)로 쓰여 CCTV·YOLO 탐지에 소비된다. depth 인터페이스는 한 번도 운용 구성으로 쓰인 적이 없다.

목표는 **AMR 주변 로컬 3D 점유맵**이다. 전역 SLAM 이 아니다 — Gemini E 의 depth 유효거리가
0.2~2.5 m 라 전역 매핑 센서로 부적합하고, 저장소 아키텍처 문서가 6 카메라의 1차 목적을
"3D 충돌 회피"로 이미 규정했다(`system-architecture/2026-06-27.md:293-303`).

착수 전 실측으로 확정한 제약:

| 사실 | 근거 |
| --- | --- |
| 카메라 6대 전부 USB 2.0(480 Mbps)로 링크. USB3 허브에 꽂아도 장치가 USB2 전용이라 무효 | `lsusb -t`, `/sys/bus/usb/devices/*/speed` 전수 판독 |
| 호스트 컨트롤러는 5개 → **한 곳은 반드시 2대 공유**. 현재 공유쌍 = `cam_lf`(`1-2.1.x`) + `cam_r`(`1-3.1.x`), 둘 다 SoC 내장 tegra-xusb | 같은 판독 |
| `cam_f`(`3-1.1.x`)는 무선 NIC·CP2102 UART·panda CAN(`3-2.x`)과 같은 컨트롤러 | 같은 판독 |
| depth+RGB 4대 동시 구동 시 4번째 `uvc_open` 이 LIBUSB_ERROR_BUSY 로 실패 | `depth/2026-07-22_depth_640x480.md:43` |
| depth-only 4대는 각 ~14 fps 로 자기제한 | 같은 문서 `:44` |
| CPU 는 이미 포화(총 74.7~80.9%, load_avg 12.5/8코어) | `Log/health/health-2026-07-29.jsonl` |

⇒ **RGB CCTV·AI 와 depth 매핑은 동시에 성립하지 않는다.** 사용자 결정으로 **배타 운용**을 채택했다.

카메라 장착 기하는 사용자 제공 도면(`Ford_Camera_Test_260730.dwg`,
`KakaoTalk_20260730_110243308.jpg`)에서 확정했다. 방위각이 정확히 60° 간격이고 수평 시야가 79°라
**인접 쌍마다 19° 겹침으로 360° 가 사각 없이 덮인다.**

## Decision

### D1. 산출물은 로컬 점유맵 — 전역 SLAM 아님

`map`/`odom` 프레임을 쓰지 않는다. 모든 융합은 `base_link` 기준이며, 따라서 **검증되지 않은
오도메트리(ICP 미검증, 엔코더 DR 부호 3건 미판정)에 의존하지 않는다.** 이것이 이 설계의
가장 큰 리스크 회피다.

### D2. 배타 운용 — RGB 스택과 동시 기동 금지

depth 매핑 모드와 RGB CCTV 모드는 배타적이다. launch 가 기동 시 `usb_cam_publisher_node`
프로세스를 탐지하면 **오류로 중단**한다(조용한 축소 운전 금지). 근거: 같은 물리 장치의
다른 인터페이스라 `/dev/video` 점유와 USB 등시성 대역을 함께 다툰다.

`Tools/camera_service/` 의 systemd 유닛은 `Restart=always`/`RestartSec=5` 라 수동으로 죽여도
5초 뒤 부활한다(`usb-cam@.service:23-24`). 매핑 전 `systemctl stop usb-cam.target` 이 필요하며,
현재 그 유닛은 미설치 상태다(`/etc/systemd/system/` 확인).

### D3. 신규 패키지 `orbbec_multi_bringup` — 벤더 launch 를 쓰지 않는다

벤더 `multi_camera.launch.py` 는 2대 하드코딩 예제이고 `usb_port` 값이 3개 카메라에 중복
기재된 미완성본이다(`:33,45,57`). 또한 `gemini_e.launch.py` 에는 `sync_mode` 인자 자체가 없다.

배치는 `src/Sensors/Camera/RGBD/orbbec_multi_bringup/` — README 규약상 `package.xml` 보유
ROS2 패키지는 `src/<도메인>/` 아래다. 벤더 트리(`OrbbecSDK_ROS2/`)는 건드리지 않는다(상류 갱신
시 되돌아올 경로를 만들지 않기 위함).

식별은 **시리얼**로 한다(`usb_port` 아님). `usb_port` 는 재배선·재부팅으로 바뀌지만 시리얼은
불변이고, 로스터 SSOT 인 `config/camera/camera_common.yaml` 이 이미 시리얼 기반이다.

### D4. 카메라별 컨테이너 분리 (기본값)

벤더가 검증한 형태는 카메라 1대 = `ComposableNodeContainer` 1개다. 6대를 한 컨테이너에 합치면
프로세스·직렬화 비용이 줄지만, **드라이버가 한 프로세스 안 다중 인스턴스를 견디는지 확인된 바
없다.** 기본은 분리(6 컨테이너), 단일 컨테이너는 `use_single_container` 인자로 열어두되
**미검증으로 명시**한다. W1 대역 실측에서 둘 다 잰다.

### D5. 스트림 구성 — depth 만, 포인트클라우드는 드라이버에서 생성하지 않음

- `enable_color=false`, `enable_ir=false` — 대역 절감. (단 2026-07-22 실측 기록은 depth 요청 시
  IR 이 동반 강제됐다고 적고 있다(`:16-17`). `enable_ir=false` 가 실제로 IR 을 끄는지는 **미검증**,
  W1 에서 확인한다.)
- `enable_point_cloud=false` — 드라이버가 카메라마다 포인트클라우드를 만들면 CPU 비용이 6배다.
  역투영은 W6 의 단일 노드에서 decimation 을 걸어 한 번에 한다. CPU 포화 상태에서 이 선택이
  가장 큰 절감 요인이다.
- 해상도·FPS 는 launch 인자(기본 640x480@30). **확정값은 W1 실측 결과로 정한다** — 특히
  공유 컨트롤러의 2대는 비대칭 하향이 필요할 수 있다.

### D6. 외부 파라미터(extrinsic)는 `config/camera/extrinsics.yaml` 단일 파일

로스터가 루트 `config/camera/` 에 있는 선례를 따른다(비-ROS 도구
`Tools/CameraCalibration`·`Tools/camera_service` 도 같은 디렉터리를 읽는다).

초기값은 도면 실측이고, W5 캘리브가 **같은 파일을 덮어쓰는 것**을 산출 규약으로 삼는다.

| 카메라 | x (m) | y (m) | z (m) | yaw | pitch |
| --- | --- | --- | --- | --- | --- |
| `cam_f` | +1.01381 | 0 | 0.348 | 0° | **+12°** |
| `cam_lf` | +0.0666 | +0.72074 | 0.348 | +60° | 0° |
| `cam_lr` | −0.0666 | +0.72074 | 0.348 | +120° | 0° |
| `cam_r` | −1.01381 | 0 | 0.348 | 180° | **+12°** |
| `cam_rr` | −0.0666 | −0.72074 | 0.348 | −120° | 0° |
| `cam_rf` | +0.0666 | −0.72074 | 0.348 | −60° | 0° |

전·후면의 pitch 가 **양(+)** 인 것이 하향 틸트다. ROS 의 RPY 는 y 축 회전에 오른손 법칙을
쓰므로 `Ry(θ)` 가 x̂ 을 `(cosθ, 0, −sinθ)` 로 보낸다 — θ>0 이면 z 성분이 음수, 즉 아래를 본다.
초안에는 "하향"이라는 말에 이끌려 −12° 로 적었고, 그 상태에서는 카메라가 위를 보게 모델링된다.
합성 depth 프레임 시험이 이를 잡았다(`128 점 vs 192 점`으로 부호가 판별된다).

`cam_lf`/`cam_lr` 의 x 부호(±66.6 mm)는 도면의 광축 교차 여부가 모호해 **가정값**이다. W5 의
겹침 정합이 확정한다. 133 mm 오차는 19° 겹침 여유 안이라 정합 수렴을 방해하지 않는다.

### D7. TF 는 static_transform_publisher — URDF 는 도입하지 않는다

`base_link → cam_*_link` 6개를 launch 가 static TF 로 발행하고, 그 아래
`cam_*_link → cam_*_depth_optical_frame` 은 드라이버가 발행한다(`publish_tf=true`).

URDF/`robot_state_publisher` 를 쓰지 않는 이유: 이 저장소에는 차체 URDF 가 **하나도 없고**
(있는 것은 SICK·Orbbec 벤더 단품 모델뿐), 기존 센서 TF 는 모두 static_transform_publisher
방식이다(`iahrs_driver.py:41-49`, `seer_lidar_tf_launch.py:28-38`, `dual_sick_merger.launch.py:38-43`).
차체 URDF 신설은 라이다·IMU 마운트까지 함께 옮기는 별개의 아키텍처 결정이므로 이번 범위 밖이다.

### D8. 산출물 두 갈래 — 3D 점유 + 360° 가상 스캔 (W6, 본 ADR 은 인터페이스만 고정)

`base_link` 기준 3D 보셀 점유 격자와, 방위각별 최근접 거리를 담은 `LaserScan` 을 함께 낸다.
후자는 라이다와 형식이 같아 기존 소비자가 그대로 받는다. **SICK 라이다의 대체가 아니라 근접
보완**이다(유효거리 2.5 m 대 22.4 m).

## Consequences

### 얻는 것

- 오도메트리 품질과 무관하게 동작한다(D1). 현재 저장소에서 신뢰 가능한 자세 소스가 없다는
  제약을 우회한다.
- 방위각 사각 0°, 균일 19° 겹침 — 그 겹침이 W5 정합 여유로 그대로 쓰인다.
- 벤더 트리 무수정이라 상류 신버전 도입 시 충돌이 없다.

### 잃는 것 · 감수하는 것

- **RGB CCTV·YOLO 탐지가 매핑 중 정지한다**(D2). 두 기능은 영원히 배타이며, 동시 운용은
  하드웨어(USB 호스트 컨트롤러 증설 또는 USB3 카메라)로만 풀린다.
- 수직 커버리지가 방향별로 비대칭이다(전·후 하향 12° vs 측면 0°). 차체 옆 0.3 m 에서 높이 17 cm 미만
  물체는 측면 카메라 시야 아래로 벗어난다(계산값, 높이 348 mm·수직시야 62° 기준).
  전·후방은 같은 조건에서 7 cm 까지 본다. W10 에서 실측 확인 대상.
- 각 60° 섹터를 담당하는 카메라가 한 대뿐이라 **예비가 없다.** 한 대가 느려지면 그 방향
  갱신율이 그대로 떨어진다.

### 미검증 (이 ADR 의 어떤 문장도 실차 거동을 확정하지 않는다)

- 6대 depth 동시 구동 자체가 미검증. 기존 실측은 **4대까지**이고 그때는 한 컨트롤러에 몰린
  조건이었다. 현재 5-컨트롤러 분산에서 결과가 다를 수 있으나 **다를 것이라는 근거도 없다.**
- `enable_ir=false` 가 IR 스트림을 실제로 끄는지 미확인.
- 단일 컨테이너 6 인스턴스 동작 여부 미확인(D4).
- 무선 트래픽이 `cam_f` 에 주는 영향 미측정.
- 도면값 `348.42` 와 `353.86` 중 어느 쪽이 렌즈 광학중심인지 미확정(5.44 mm 차, W5 가 흡수).

## Rollback

전부 신규 파일이며 **기존 파일을 수정하지 않는다.** 되돌림은 아래 3개 경로 삭제로 완결된다:

```bash
rm -rf src/Sensors/Camera/RGBD/orbbec_multi_bringup
rm -rf src/Sensors/Camera/RGBD/depth_occupancy_3d
rm -f  config/camera/extrinsics.yaml
rm -rf build/orbbec_multi_bringup  install/orbbec_multi_bringup
rm -rf build/depth_occupancy_3d    install/depth_occupancy_3d
```

기존 RGB CCTV 스택(`usb_cam_publisher`·`vision_guard`·`yolo_detector`)은 이 변경으로 코드가
바뀌지 않으므로, 위 삭제 후 종전과 동일하게 기동한다. 영속 상태·스키마·펌웨어 변경 없음.

되돌림이 필요한 판정 기준: W1 대역 실측에서 **6대 depth 가 각 15 fps 를 넘지 못하면** 본 설계는
성립하지 않는다. 그 경우 해상도 하향 재시도 → 실패 시 하드웨어(컨트롤러 증설/USB3 카메라)로
결정을 되돌린다.
