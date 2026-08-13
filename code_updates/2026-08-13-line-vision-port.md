# 2026-08-13 — `src/AI/line_vision` 신설 (라인 추종 인식 계층 이식) + `ai_msgs/LineError` 추가

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: AMR(Autonomous Mobile Robot) · HAL(Hardware Abstraction Layer) ·
> MJPEG(Motion Joint Photographic Experts Group) · SSOT(Single Source Of Truth) ·
> QoS(Quality of Service) · AGPL(Affero General Public License)

- 사용자 지시: 2026-08-13 "목적 ; line following 개발 / 내 깃허브 3d_slam 에서 라인 following
  기능 조사 후 이식 준비" → "AI 기능은 `src/AI` 에 이식" → "직진시는 전방 카메라 후진시에는
  후방 카메라 사용" → "현재 프로젝트 구조 분석후에 카메라 관련 HAL 구조 이용할 것"
- ADR: `docs/adr/2026-08-13-line-following-ai-port.md`
- 인벤토리(코딩 SOP §2 선행 산출물, 신규 파일이라 계획 단계에서 작성):
  `docs/code_review/ai-line-vision/2026-08-13.md`(루트 정본) +
  `src/AI/line_vision/docs/code_review/ai-line-vision/2026-08-13.md`(패키지 병기)
- 구조: `docs/sw_structure/ai-line-vision/2026-08-13.md` + 패키지 병기
- 루트 집계 인덱스: `docs/sw_structure/function_table.md` 에 모듈 1행 추가
- 패키지 병기 이력: `src/AI/line_vision/docs/line_vision_code_updates.md`

## 무엇을 만들었나

| 파일 | 상태 | 내용 |
| --- | --- | --- |
| `src/AI/line_vision/line_vision/centerline.py` | 신규 (112줄, 함수 2 + dataclass 1) | 스캔라인 무게중심 + `cv2.fitLine(DIST_L2)` 중심선 피팅. ROS·ultralytics 무의존 |
| `src/AI/line_vision/line_vision/line_seg_node.py` | 신규 (242줄, 함수 2 + 클래스 1(메서드 8)) | YOLOv8-seg 추론 → `/line/error` 발행, 전후방 카메라 전환 |
| `src/AI/line_vision/launch/line_seg.launch.py` | 신규 (91줄, 함수 4) | 로스터에서 카메라 이름 유도 |
| `src/AI/line_vision/config/line_seg_params.yaml` | 신규 | 파라미터 기본값 |
| `src/AI/line_vision/test/test_centerline.py` | 신규 | 단위테스트 17 |
| `src/AI/ai_msgs/msg/LineError.msg` | 신규 | `header`·`detected`·`offset`·`angle`·`confidence`·`camera` |
| `src/AI/ai_msgs/CMakeLists.txt` | 수정 (1줄) | `rosidl_generate_interfaces` 에 `LineError.msg` 등재 |

출처는 `kuks2309/TR_3D_Nav_ros2_ws` 의 `src/AI/YOLOv8/tr_line_vision`(작업 사본이 이 장비의
`/home/nvidia/Project/kkw/TR-Nav3d_ros2_ws` 에 있다). 제어 계층(2WD 차동 + `Twist` 기반
액션 서버)은 이식 범위에서 뺐다 — 이 기체는 인라인 듀얼스티어 2WS 이고 mux 가 `Twist` 가
아니라 wheel 명령을 받으므로 재작성 대상이다.

## 왜 원본을 그대로 옮기지 않았나

**① 카메라 퍼블리셔를 버렸다.** 원본 `tr_camera` 는 `cv2.VideoCapture` 로 `/dev/video0` 를
직접 연다. 이 저장소에는 카메라 HAL 이 3단으로 서 있고(`config/camera/camera_common.yaml`
로스터 SSOT → `Tools/camera_service/camera_params.py` 해석 → `usb_cam_publisher` 드라이버,
카메라 1대당 systemd 인스턴스 1개), 그 퍼블리셔가 이미 장치를 점유한다. 원본을 그대로
가져오면 장치를 **이중 open** 하고 로스터를 우회한다. 그래서 토픽만 구독한다 —
`dataset_collector`·`yolo_detector` 가 이미 따르는 규약이다.

카메라 이름도 노드 기본값이 아니라 **런치가 로스터에서 유도**한다. 하드코딩하면 위치 기준
개명 때 없는 토픽을 구독해 **에러 없이 검출 0** 이 된다 — 2026-07-30 개명에서 실제로 그
경로를 밟았다(`docs/issues_and_fixes/issues_and_fixes.md:1750`,
ADR `2026-07-30-camera-position-naming`).

**② `cv_bridge` 결합을 없앴다.** 로스터의 `publish_mode` 가 `compressed`(MJPEG 패스스루)이고
이 값은 바꾸지 않는다 — 바꾸면 CCTV·뷰어 전체의 대역 전제가 무너진다(6대 환산 24 → 498 MB/s).
추론에는 픽셀이 필요하므로 `cv2.imdecode` 로 인식 노드 안에서 1회 디코드하고, 디버그 영상은
`sensor_msgs/Image` 를 직접 조립해 발행한다. 원본은 opencv 5.x ↔ `cv_bridge` 비호환
(KeyError 16)으로 버전을 못 박아야 했는데, 그 결합 자체를 제거했다.

**③ 인터페이스 패키지를 늘리지 않았다.** 원본은 전용 `tr_line_interfaces` 를 뒀으나 이
저장소에는 `ai_msgs` 가 이미 있다. `LineError` 를 거기 넣고, 원본에 없던 `camera` 필드를
하나 더했다 — 방향 전환의 결과를 소비자가 메시지만 보고 확인할 수 있어야 한다.

## 방향별 카메라 전환 (사용자 요구)

직진 = `cam_f`(전면), 후진 = `cam_r`(후면). 노드를 둘 띄우지 않고 `direction` 파라미터
(`forward`|`reverse`)로 구독을 갈아탄다 — 세그멘테이션 모델을 두 벌 GPU 에 올리지 않기
위해서다. 전환 시 구독을 파기·재생성하므로 **오차 발행이 잠시 끊긴다**. 제어 계층이 이를
「입력 두절」로 읽을 수 있어 전환은 정지 상태에서만 하도록 운용 규칙으로 둔다.

`offset` 의 부호 의미는 두 카메라에서 같다 — 후방 카메라는 광축이 `-x_robot` 이라 영상
오른쪽이 로봇 기준 왼쪽이고, 후진 중에는 그것이 곧 진행방향 기준 오른쪽이다. 따라서 좌우
반전 보정이 필요 없다. **다만 이는 「카메라가 정상 자세로 장착됐다」는 전제 위의 기하
추론이며 `[미검증]` 이다.** 원본 기체는 카메라가 뒤집혀 장착돼 180° 회전 보정이 필요했고,
상하만 뒤집어 좌우 거울상이 남은 탓에 **라인에서 멀어지는 방향으로 조향한 실사고**가 있었다.
그래서 방향별 `flip_180` 파라미터를 남기되 기본은 `false` 로 두고, 실기에서 좌우 부호를
확인하기 전에는 주행 금지로 한다.

## 의존성

신규 설치 **0건**이다 — torch 2.4.0a0+nv24.07 · ultralytics 8.4.95 · opencv 4.10.0 ·
numpy 1.26.4 가 이미 설치돼 있고, 원본 ADR 이 고정한 조합과 정확히 일치한다(실측 확인).
`ultralytics` 의 AGPL-3.0 은 `yolo_detector` 로 이미 이 저장소에 존재하는 조건이며 본 변경이
새로 들여오는 위험이 아니다 — 다만 상용 배포·네트워크 서비스 제공 시 소스 공개 의무 또는
Enterprise License 가 필요하다는 사실은 그대로 유효하다.

## 검증

| 항목 | 결과 |
| --- | --- |
| 단위 테스트 | 17 passed |
| `src/AI` 전체 회귀 | 76 passed (`dataset_collector` · `yolo_detector` · `line_vision`) |
| colcon 빌드 | `ai_msgs` · `line_vision` 오류 0 |
| 런치 로스터 유도 | 로스터 6대 발견, forward→`cam_f` / reverse→`cam_r` |
| 합성 프레임 end-to-end | 발행 140 → `/line/error` 104, 전부 `detected=True`, conf 최대 0.95 |
| `offset` 부호·정규화 | 라인 x=340 → −0.470, x=925 → +0.445 (기대 −0.469 / +0.445) |
| 방향 전환 | `direction:=reverse` 후 `cam_r` 59건 수신, 같은 시각 `cam_f` 입력 0건(구 구독 파기) |

**미검증**: 실카메라 영상·실라인·실주행. 합성 프레임은 배선과 부호 규약만 증명한다.
가중치 `/home/nvidia/models/line_seg_v1.pt` 는 원본 학습본 복사(md5 동일)이나 **타 기체
(640×480 4:3, 다른 장착 자세, 58장 단일주행) 학습본이라 이 기체(1280×720 16:9)에서 검출률은
보장되지 않는다** — 실사용 전 `dataset_collector` 로 재수집·재학습이 필요하다.
원본의 미해결 부채도 그대로 따라온다: 현 모델은 near-vertical 라인만 인식해 교차·분기에서
방향을 고를 수 없다.

최종 verdict 는 저자가 찍지 않는다 (`coding.md:89` never-self-approve).
