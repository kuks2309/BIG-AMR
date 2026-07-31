# orbbec_multi_bringup — surround depth 카메라 6대 bringup

Big-AMR 차체 둘레의 Orbbec Gemini E 6대를 **depth 전용**으로 기동하고, `base_link` 기준 정적
마운트 TF 를 함께 발행한다. 로컬 3D 점유맵(W6)의 입력단이며 전역 SLAM 이 아니다.

- 설계 근거: [docs/adr/2026-07-31-surround-depth-occupancy.md](../../../../../docs/adr/2026-07-31-surround-depth-occupancy.md)
- 벤더 드라이버(`OrbbecSDK_ROS2/orbbec_camera`)는 **수정하지 않는다** — 상류 갱신 시 충돌 방지.

## 실행

```bash
# 1. RGB 스택을 먼저 내린다 (배타 운용 — 같은 물리 카메라다)
pkill -f usb_cam_publisher_node
#    Tools/camera_service systemd 유닛이 설치돼 있으면 먼저:
#    sudo systemctl stop usb-cam.target

# 2. 기동
ros2 launch orbbec_multi_bringup surround_depth.launch.py
```

### launch 인자

| 인자 | 기본값 | 설명 |
| --- | --- | --- |
| `roster_file` | 저장소 `config/camera/camera_common.yaml` | 카메라 시리얼 로스터 |
| `extrinsics_file` | 저장소 `config/camera/extrinsics.yaml` | `base_link` 기준 마운트 값 |
| `stream_config_file` | 패키지 `config/surround_depth.yaml` | depth 구동점 |
| `allow_rgb_conflict` | `false` | `true` 면 `/dev/video` 점유자가 있어도 강행(진단용) |
| `require_all_connected` | `true` | `false` 면 일부 카메라 미연결도 경고만 하고 기동 |
| `use_single_container` | `false` | `true` 면 6대를 한 컨테이너에 넣는다 (**미검증**) |

## 발행 인터페이스

카메라마다 자기 이름의 네임스페이스를 쓴다 (`cam_f` `cam_lf` `cam_lr` `cam_r` `cam_rr` `cam_rf`).

| 토픽 | 타입 | 비고 |
| --- | --- | --- |
| `/<cam>/depth/image_raw` | `sensor_msgs/Image` | Y11, QoS `SENSOR_DATA`(best-effort) |
| `/<cam>/depth/camera_info` | `sensor_msgs/CameraInfo` | 장치 펌웨어 intrinsic |

TF 는 두 구간으로 나뉜다:

| 구간 | 발행 주체 |
| --- | --- |
| `base_link` → `<cam>_link` | **본 launch** 의 `static_transform_publisher` (extrinsics.yaml) |
| `<cam>_link` → `<cam>_depth_optical_frame` | `orbbec_camera` 드라이버 (`publish_tf=true`) |

## 기하 — 방위 60° 등간격, 사각 0°

수평 시야 79° 카메라 6대가 60° 간격이라 **인접 쌍마다 19° 겹침으로 360° 가 사각 없이 덮인다.**
그 19° 가 W5 겹침 정합(ICP)의 정합 여유이기도 하다.

| 카메라 | 방위 | pitch (양수가 하향) | USB 호스트 컨트롤러 |
| --- | --- | --- | --- |
| `cam_f` | 0° | +12° | PCIe `0004:03:00.0` (무선 NIC·UART·panda CAN 과 공유) |
| `cam_lf` | +60° | 0° | **SoC tegra-xusb (cam_r 과 공유)** |
| `cam_lr` | +120° | 0° | PCIe `0004:06:00.0` (전용) |
| `cam_r` | 180° | +12° | **SoC tegra-xusb (cam_lf 와 공유)** |
| `cam_rr` | −120° | 0° | PCIe `0004:05:00.0` (전용) |
| `cam_rf` | −60° | 0° | PCIe `0004:04:00.0` (전용) |

pitch 가 양수인 것이 하향이다 — ROS 의 RPY 는 y 축 회전에 오른손 법칙을 쓰므로 `Ry(θ)` 가
x̂ 을 `(cosθ, 0, −sinθ)` 로 보낸다. 도면의 "하향 12°" 를 −12° 로 옮기면 카메라가 위를 본다.

호스트 컨트롤러가 5개인데 카메라는 6대라 **한 곳은 반드시 2대가 공유**한다. 공유쌍의 대역이
모자라면 그 2대만 해상도·FPS 를 낮추는 비대칭 구동점이 되며, `config/surround_depth.yaml` 의
`per_camera` 로 지정한다.

## 함수표 (launch/surround_depth.launch.py)

| 함수 | 역할 | 인자 | 반환 | 부수효과 |
| --- | --- | --- | --- | --- |
| `_find_repo_config` | 저장소 루트 `config/camera/<basename>` 탐색 | `basename` | 절대경로 `str` | 없음. 못 찾으면 `FileNotFoundError` — **패키지 로컬 사본으로 대체하지 않는다** |
| `_load_yaml` | YAML 읽기 | `path` | `dict` | 파일 읽기 |
| `_connected_depth_serials` | 연결된 Orbbec depth 인터페이스 시리얼 조회 | 없음 | `set[str]` | `/sys` 읽기. 장치를 열지 않는다 |
| `_video_device_holders` | `/dev/video*` 점유 프로세스 조회 | 없음 | `list[(pid, comm, dev)]` | `/proc` 읽기 |
| `_assert_exclusive_mode` | 배타 운용 강제 | `allow_rgb_conflict` | 없음 | 위반 시 `RuntimeError` |
| `_assert_roster_connected` | 로스터 시리얼 연결 확인 | `cameras`, `require_all_connected` | 없음 | 미연결 시 `RuntimeError` 또는 경고 출력 |
| `_depth_params` | 카메라 1대의 드라이버 파라미터 생성 | `defaults`, `driver`, `override` | `dict` | 없음(순수 함수) |
| `_camera_composable_node` | `ComposableNode` 서술 생성 | `camera_name`, `serial`, `params` | `ComposableNode` | 없음 |
| `_static_mount_tf` | `base_link`→`<cam>_link` static TF 노드 생성 | `camera`, `parent_frame` | `Node` | 없음. deg→rad 변환 수행 |
| `_launch_setup` | 인자 확정 후 노드 목록 구성 | `context` | `list[Action]` | 위 검사들을 호출 |
| `generate_launch_description` | launch 진입점 | 없음 | `LaunchDescription` | 기본값 계산 시 `_find_repo_config` 호출 |

### 전역(모듈 상수)

가변 전역은 없다. 아래는 전부 불변 상수이며 **바꾸는 주체 없음**(read-only).

| 이름 | 값 | 용도 |
| --- | --- | --- |
| `ORBBEC_VENDOR_ID` | `"2bc5"` | sysfs 벤더 판정 |
| `ORBBEC_DEPTH_PRODUCT_ID` | `"065c"` | depth 인터페이스 판정 (RGB 는 `055c`) |
| `ROSTER_BASENAME` | `"camera_common.yaml"` | 로스터 파일명 |
| `EXTRINSICS_BASENAME` | `"extrinsics.yaml"` | 외부파라미터 파일명 |
| `RGB_PUBLISHER_PROCESS` | `"usb_cam_publisher_node"` | 오류 메시지의 `pkill` 안내 문자열 |

## 설계상 의도적으로 하지 않은 것

- **조용한 축소 기동 금지** — 로스터 6대 중 하나라도 미연결이면 기본값에서 **중단**한다.
  기존 `usb_cam_cctv.launch.py` 는 공용 설정을 못 찾으면 4대짜리 구 설정으로 떨어져 경고 없이
  4대만 뜨는 결함이 있었다
  ([2026-07-28_six_camera_connectivity.md:30-31](../../../../../docs/usb_cctv/performance/2026-07-28_six_camera_connectivity.md)).
  방위 60° 등간격 구성에서는 한 대가 빠지면 그 60° 섹터가 통째로 비고 다른 카메라가 메우지 못한다.
- **`usb_port` 로 식별하지 않음** — 재배선·재부팅으로 바뀐다. 시리얼은 불변이고 드라이버에서
  `usb_port`·`device_num` 보다 우선한다(`ob_camera_node_driver.cpp:293-301`).
- **URDF 미도입** — 이 저장소에는 차체 URDF 가 없고 기존 센서 TF 는 전부
  `static_transform_publisher` 방식이다. 차체 URDF 신설은 라이다·IMU 마운트까지 옮기는 별개
  결정이라 본 패키지 범위 밖이다 (ADR §D7).
- **드라이버 포인트클라우드 생성 안 함** — 역투영은 W6 단일 노드에서 decimation 을 걸어 일괄
  처리한다. 카메라마다 만들면 CPU 6배이고 이 장비는 이미 포화 상태다 (ADR §D5).

## 검증 상태

**2026-07-31 시점 — 실기(카메라 개방) 검증 0.** 아래는 장치를 열지 않고 확인한 것뿐이다.

| 항목 | 결과 | 방법 |
| --- | --- | --- |
| `colcon build` | 통과 | `colcon build --packages-select orbbec_multi_bringup` |
| 배타 운용 가드 | `/dev/video` 점유 6건 탐지 → 기동 차단 | RGB 스택 가동 중 `ros2 launch` 실행, exit 1 |
| 로스터 ↔ 외부파라미터 이름 정합 | 6/6 일치 | 헬퍼 직접 호출 |
| 로스터 시리얼 연결 확인 | 6/6 연결됨 | `_connected_depth_serials()` 대조 |
| depth 파라미터 생성 | 640×480@30 Y11 `SENSOR_DATA`, color/IR/PC off | `_depth_params()` 호출 |
| 카메라별 재정의 | 480×360@15 적용됨 | `_depth_params(..., override)` |
| static TF 생성 | `cam_lf` yaw 60° → 1.0472 rad | `_static_mount_tf()` |

**미검증 (실기 필요)**

- 6대 depth 동시 개방 가능 여부, 카메라별 실 FPS — 저장소 실측은 4대까지이고 그때는 한
  컨트롤러에 몰린 조건이었다
  ([depth/2026-07-22_depth_640x480.md](../../../../../docs/usb_cctv/performance/depth/2026-07-22_depth_640x480.md))
- `enable_ir=false` 가 IR 스트림을 실제로 끄는지
- `use_single_container:=true` 경로 (드라이버 다중 인스턴스 내성)
- 무선 트래픽이 `cam_f` 에 주는 영향
- 마운트 값 자체의 정확도 — 도면 판독값이며 W5 캘리브가 확정한다
