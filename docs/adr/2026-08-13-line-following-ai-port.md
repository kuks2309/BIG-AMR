# ADR 2026-08-13 — 라인 추종 인식(AI) 계층 이식 — `line_vision` 신설, 카메라 HAL 경유

- **Status**: Proposed — 2026-08-13 (사용자 지시로 착수. 최종 verdict 는 저자가 찍지 않는다 —
  `coding.md:89` never-self-approve)
- **대상**: `src/AI/line_vision/`(신규) · `src/AI/ai_msgs/`(메시지 1종 추가)
- **범위**: **인식 계층만.** 제어 계층(라인 추종 액션 서버)은 본 ADR 범위 밖 — 별건.

## Context

사용자 지시(2026-08-13): ① 라인 following 기능을 `kuks2309/TR_3D_Nav_ros2_ws` 에서 조사·이식,
② AI 기능은 `src/AI` 에 배치, ③ **직진 시 전방 카메라, 후진 시 후방 카메라** 사용,
④ **카메라 관련 HAL 구조를 이용할 것**.

### 원본 자산 (조사 결과)

원본 저장소의 라인 추종은 4개 계층이며, 그 작업 사본이 **이 장비에 그대로 있다**
(`/home/nvidia/Project/kkw/TR-Nav3d_ros2_ws`, `git remote` 로 동일 저장소 확인).

| 계층 | 원본 | 본 이식 |
| --- | --- | --- |
| 카메라 | `tr_camera` (Python cv2 퍼블리셔) | **이식 안 함** — 본 저장소 카메라 HAL 로 대체(§D1) |
| 인터페이스 | `tr_line_interfaces/LineError.msg` | `ai_msgs/LineError.msg` 로 흡수(§D2) |
| 인식 | `tr_line_vision`(centerline·line_seg_node) | `src/AI/line_vision`(§D3) |
| 제어 | `amr_motion_control_2wd/line_follow_*`(C++, 2WD Twist) | **본 ADR 범위 밖** (2WS 재작성 필요) |

원본 실주행 근거: 1.0 m/s 로 실라인 약 10 m 완주, 검출률 100%, 평균 `|offset|` 0.050,
라인 종료 감지 후 설계대로 정지(원본 `docs/experiments/line_following/2026-07-15-1ms-full-line.md`).
결정적 요인은 게인이 아니라 **카메라 30 fps 확보**였다(인식 14 → 26 Hz).

### 이 장비의 유리한 조건 (실측 2026-08-13)

- ML 스택이 원본 ADR 의 고정 조합과 **정확히 일치**: torch 2.4.0a0+3bcc3cddb5.nv24.07
  (`cuda.is_available()=True`) · torchvision · ultralytics 8.4.95 · numpy 1.26.4 · opencv 4.10.0.
  → torchvision 소스빌드(30분~1시간) 불요, 추가 설치 0.
- 학습 가중치 `best.pt`(6.78 MB)와 데이터셋(58장)이 로컬에 존재. **원본 git 에는 없다**
  (원격 tree 조회 결과 `runs/`·이미지 0건) — GitHub 만 봤으면 못 찾는 자산이다.

## Decision

### D1. 카메라는 이식하지 않는다 — 기존 카메라 HAL 을 구독한다

원본 `tr_camera` 를 가져오면 이 저장소의 3단 카메라 HAL 을 우회하게 되고, `/dev/video*` 를
**이중 open** 하게 된다(usb_cam_publisher 가 이미 점유). 따라서 인식 노드는 **장치를 열지 않고
토픽만 구독**한다 — `dataset_collector`·`yolo_detector` 가 이미 따르는 규약이다.

| HAL 단 | 자산 | 본 노드가 지키는 것 |
| --- | --- | --- |
| 로스터 SSOT | `config/camera/camera_common.yaml` | 카메라 이름·토픽을 **로스터에서 유도**, 코드 하드코딩 금지 |
| 해석 | `Tools/camera_service/camera_params.py` | (배포 계층 — 본 노드 비관여) |
| 드라이버 | `usb_cam_publisher` | `/<name>/image_raw/compressed`(SensorDataQoS) 구독 |

런치는 `yolo_detector/detect.launch.py:44-56` 의 idiom 을 복제해 로스터에서 이름을 읽는다.
하드코딩하면 위치 기준 개명 때 **에러 없이 검출 0** 이 된다(2026-07-30 실사고,
ADR `2026-07-30-camera-position-naming`).

**전송은 compressed 기본, 디코드는 인식 노드가 한다.** 로스터의 `publish_mode` 는
`compressed`(MJPEG 패스스루)이고 이를 바꾸지 않는다 — 바꾸면 CCTV·뷰어 전체의 대역 전제가
무너진다(6대 환산 24 → 498 MB/s). 추론에는 픽셀이 필요하므로 `cv2.imdecode` 를 인식 노드
안에서 1회 수행한다(`detector_node.py:140-142,212` 와 동일 방식). 720p 디코드 실측 6.55 ms 로
추론 23 ms 대비 부수적이다.

### D2. `LineError` 는 신규 인터페이스 패키지 대신 `ai_msgs` 에 넣는다

원본은 전용 패키지 `tr_line_interfaces` 를 뒀으나, 본 저장소에는 AI 인터페이스 패키지
`ai_msgs`(Detection·DetectionArray)가 **이미 있다**. 패키지를 하나 더 만들 이유가 없다.

```
# ai_msgs/msg/LineError.msg
std_msgs/Header header      # 원본 이미지 stamp 승계 (지연 판단용)
bool    detected            # 검출 여부 (미검출 프레임도 발행 — 소실 감지용)
float32 offset              # 제어 기준행 횡오차, 정규화 [-1,1], + = 라인이 화면 오른쪽
float32 angle               # 라인 기울기 [rad], 수직 = 0, + = 위쪽이 오른쪽으로 기움
float32 confidence          # seg 신뢰도 (미검출 시 0)
string  camera              # 이 오차를 만든 카메라 논리명 (cam_f / cam_r) — 신규 필드
```

원본 대비 **`camera` 필드 1개 추가**(§D4 의 방향 전환을 소비자가 확인할 수 있어야 한다).
미검출 프레임도 발행한다 — 제어기가 라인 소실을 즉시 감지해야 하므로 침묵은 정지 신호가
될 수 없다(원본 ADR `2026-07-14-line-seg-interface` 계승).

발행 토픽: `/line/error`, 디버그 오버레이 `/line/debug_image`(구독자 있을 때만).

### D3. 패키지 이름은 `line_vision` — `src/AI/line_vision/`

`tr_` 접두는 원본 저장소 관례이고 본 저장소는 접두 없는 이름을 쓴다(`yolo_detector`·
`dataset_collector`·`ai_msgs`). 따라서 `tr_line_vision` → **`line_vision`**.

| 파일 | 역할 |
| --- | --- |
| `line_vision/centerline.py` | 중심선 피팅 순수 로직 (ROS·ultralytics 무의존, 단위테스트 대상) |
| `line_vision/line_seg_node.py` | ROS2 노드 — 구독·추론·오차 발행·디버그 오버레이 |
| `config/line_seg_params.yaml` | 파라미터 기본값 |
| `launch/line_seg.launch.py` | 로스터 유도 런치 |
| `test/test_centerline.py` | 단위테스트 |

`centerline.py` 는 원본을 그대로 가져온다(알고리즘 변경 없음). 원본 자체가 사용자 지정 참조
`Welding_Robot_Ros2_ws/seam_tracking` 의 `fit_seam_centerline`(C++) 포팅이다 — 스캔라인별 전경
무게중심 수집 후 `cv2.fitLine(DIST_L2)` 직선 피팅, bbox 종횡비로 주방향 판정.

**원본 데이터 수집 노드(`data_collector`)는 이식하지 않는다** — 본 저장소 `dataset_collector`
가 같은 일을 더 낫게 한다(디스크 가드·중복 억제·6대 동시). 재학습 데이터는 그것으로 모은다.

### D4. 방향별 카메라 전환 — 파라미터 1개, 노드 1개

직진 = `cam_f`, 후진 = `cam_r`(사용자 지시). 노드를 2개 띄우지 않고 **`direction` 파라미터**
(`forward`|`reverse`)로 구독을 갈아탄다 — 추론 모델을 두 벌 GPU 에 올리지 않기 위해서다.
런타임 파라미터 콜백으로 전환하며, 전환 시 구독을 파기·재생성하고 발행 메시지의 `camera`
필드로 현재 소스를 노출한다.

**부호 규약**: 후방 카메라는 광축이 `-x_robot` 이므로 영상의 오른쪽이 로봇 기준 **왼쪽**이고,
후진 중에는 그것이 곧 **진행방향 기준 오른쪽**이다. 따라서 `offset` 의 의미는 두 카메라에서
동일하게 "진행방향 기준 라인이 오른쪽이면 +" 가 된다 — 좌우 반전 보정은 **불필요**하다.
단 이는 「카메라가 정상 자세(상하 정립)로 장착됐다」는 전제 위의 **기하 추론이며
`[미검증]`** 이다. 원본 기체에서는 카메라가 뒤집혀 장착돼 180° 회전 보정이 필요했고,
상하만 뒤집어 좌우 거울상이 남은 탓에 **라인에서 멀어지는 방향으로 조향한 실사고**가 있었다
(원본 `camera_params.yaml` 주석, 2026-07-15 실측). 그래서 방향별 `flip_180` 파라미터를
남기되 기본은 `false` 로 두고, **실기에서 좌우 부호를 확인하기 전에는 주행 금지**로 한다.

### D5. 모델 가중치는 저장소 밖 `/home/nvidia/models/` 에 둔다

`yolo_detector` 가 이미 `/home/nvidia/models/yolov8n.pt` 를 기본값으로 쓰는 관례가 있다.
동일하게 `line_seg` 가중치를 `/home/nvidia/models/line_seg_v1.pt` 로 배치하고 파라미터
기본값으로 삼는다. 6.78 MB 바이너리를 git 에 넣지 않는다(원본도 넣지 않았다).

⚠ **이 가중치는 다른 기체에서 학습됐다** — 640×480 4:3, 카메라 높이·부각·광택 바닥, 빨간
테이프, 단일 주행 58장. Big-AMR 은 1280×720 16:9 이고 장착 자세가 다르므로 **검출률은
보장되지 않는다.** 파이프라인 배선을 먼저 검증하는 용도이며, 실사용 전 `dataset_collector`
로 재수집·재학습이 필요하다.

### D6. 의존성

| 의존성 | License | 취약점 | 대안(배제 사유) |
| --- | --- | --- | --- |
| ultralytics 8.4.95 (기설치) | **AGPL-3.0** ⚠ | 알려진 치명 CVE 없음 (로컬 추론, 신뢰경계 비횡단) | YOLOv8-seg 직접 구현(공수 과다) |
| torch / torchvision (기설치, NVIDIA Jetson 휠) | BSD-3 | 없음 | 없음 (이미 `yolo_detector` 가 사용) |
| opencv-python 4.10.0.84 (기설치) | Apache-2.0 | 없음 | 시스템 cv2 (동일) |
| `line_vision` → `ai_msgs` | Apache-2.0 (자체) | 해당 없음 | 표준 msg 조합(필드 의미 불명확) |

**신규 설치는 0건이다** — 전부 `yolo_detector` 가 이미 쓰고 있는 것과 동일 버전이다.

⚠ **ultralytics AGPL-3.0 은 이미 이 저장소에 존재하는 조건이다**(`yolo_detector`). 본 ADR 이
새로 들여오는 위험은 아니나, 상용 배포·네트워크 서비스 제공 시 소스 공개 의무 또는
Ultralytics Enterprise License 가 필요하다는 사실은 그대로 유효하다.

## Consequences

- (+) 카메라 HAL 단일 근원 유지 — 장치 이중 open 없음, 위치 개명에 자동 추종
- (+) 신규 패키지 1개뿐(인터페이스 패키지 추가 없음), 신규 의존성 설치 0
- (+) `centerline.py` 가 ROS 무의존이라 gtest 없이 pytest 로 단위검증 가능
- (−) 인식 노드가 JPEG 디코드를 떠안는다(720p 6.55 ms/frame) — 추론 대비 부수적이나 0 은 아님
- (−) `direction` 전환 시 구독 재생성 공백 동안 오차 발행이 끊긴다 → 제어 계층이
  「입력 두절」로 읽을 수 있다. 전환은 **정지 상태에서만** 하도록 운용 규칙으로 둔다
- (−) 이식 가중치의 검출 성능 미보장(§D5) — 재학습 전까지 실주행 근거로 쓸 수 없다
- ⚠ 원본의 미해결 부채가 그대로 따라온다: 현 모델은 **near-vertical 라인만** 인식해
  교차·분기에서 방향 선택이 불가하다(원본 debt-018). T자 교차의 가로 테이프는 인식되지 않는다

## Rollback Plan

git 가역: `src/AI/line_vision/` 디렉터리 삭제 + `ai_msgs/msg/LineError.msg` 삭제 +
`ai_msgs/CMakeLists.txt` 의 해당 1줄 원복 + `colcon build --packages-select ai_msgs` 재빌드.
`/home/nvidia/models/line_seg_v1.pt` 는 저장소 밖 파일이므로 삭제만 하면 된다.
영속 상태·스키마·펌웨어 비관여. 기존 카메라·CCTV·`yolo_detector` 는 **무변경**이므로
되돌림이 다른 스택에 영향을 주지 않는다.
