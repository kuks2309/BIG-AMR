# camera_service — 함수표 (모듈 권위본)

> 대상: `Tools/camera_service/` — 카메라 systemd 배포 계층(카메라별 독립 기동·자동 복구 + 관리자 상주).
> 코드 계층은 별개: 퍼블리셔 `src/Sensors/Camera/USB/usb_cam_publisher`, 관리자 `src/Sensors/Camera/USB/camera_manager`.

## 함수표 — camera_params.py (로스터 → 실행 파라미터, 순수 로직)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `load_roster` | `load_roster(config_path: str) -> dict` | 공용 yaml 파싱(`by_id_prefix`·`cameras` 필수 키 검증) | camera_params.py:30 |
| `device_path` | `device_path(by_id_prefix: str, serial: str) -> str` | 시리얼 → by-id 심링크 경로 | camera_params.py:51 |
| `camera_names` | `camera_names(config: dict) -> list[str]` | 로스터의 논리 이름 목록(install.sh 의 인스턴스 enable 근원) | camera_params.py:60 |
| `flipped_cameras` | `flipped_cameras(config: dict) -> list[str]` | 로스터 `flip: true` 카메라 목록 — 180° 장착 보정은 디코드하는 소비자(webview CSS·yolo cv2.flip) 몫 | camera_params.py:65-73 |
| `camera_params` | `camera_params(config: dict, name: str) -> dict` | 카메라 1대분 파라미터 해석(capture 기본값 + 행 재정의) | camera_params.py:65 |
| `ros_run_argv` | `ros_run_argv(name: str, params: dict) -> list[str]` | `ros2 run usb_cam_publisher …` argv 조립 | camera_params.py:95 |
| (내부) `_literal` | `_literal(value) -> str` | 파라미터 값 → ros2 CLI 리터럴 표기 | camera_params.py:111 |
| `default_config_path` | `default_config_path(repo_root: str) -> str` | 저장소 루트 → 공용 설정 경로 | camera_params.py:118 |

## 함수표 — exec_camera_node.py (카메라 1대 진입점)

| 함수 | 시그니처 | 용도 | 위치 |
| --- | --- | --- | --- |
| `main` | `main(argv: list[str]) -> int` | 로스터 해석 → 장치 심링크 검사(부재 exit 3=재시도 대상, 미등재 exit 2=설정 오류) → 노드 exec | exec_camera_node.py:31 |

## 스크립트·유닛 표

| 파일 | 용도 | 위치 |
| --- | --- | --- |
| `run_camera.sh` | systemd 용 래퍼 — ROS 환경 source 후 exec_camera_node.py 실행 | run_camera.sh:1 |
| `run_manager.sh` | systemd 용 래퍼 — ROS 환경 source 후 `ros2 run camera_manager manager_node` 실행(CAMERA_CONFIG 기본 지정) | run_manager.sh:1 |
| `install.sh` | 유닛 4종+sudoers 설치 → daemon-reload → 로스터 기반 인스턴스 enable → (기본) 즉시 기동 | install.sh:1 |
| `usb-cam@.service` | 카메라 1대용 템플릿 유닛(%i=로스터 논리 이름). Restart=always·RestartSec=5·무한 재시도 | usb-cam@.service:1 |
| `usb-cam.target` | 전 카메라 일괄 제어 묶음(Wants= 로스터 이름 하드코딩 — 카메라 증감 시 직접 갱신) | usb-cam.target:1 |
| `amr-camera-manager.service` | 카메라 관리자 상주 유닛 — 감시 대상과 독립 | amr-camera-manager.service:1 |
| `sudoers-camera-manager` | `usb-cam@*` 3동사만 무암호 허용(→ /etc/sudoers.d/camera-manager, visudo 검증 후) | sudoers-camera-manager:1 |
| `dataset-collector.service` | 수집기 유닛(기본 미등록 — 디스크 소모) | dataset-collector.service:1 |
| `test_camera_params.py` | camera_params 단위 테스트 18개 | test_camera_params.py:1 |
