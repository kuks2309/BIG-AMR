# ADR — 카메라 관리 모드: 카메라별 감시·자동 복구 + CLI 제어

- **Status**: Accepted — 2026-08-30 사용자 결정(자동+수동 병행 · CLI 도구) 반영, 구현 착수
- 대상: `src/Sensors/Camera/USB/camera_manager`(신설), `Tools/camera_service`(배포 계층 확장),
  `config/camera/camera_common.yaml`(읽기만 — 로스터 SSOT)
- 관련: [camera_service README](../../Tools/camera_service/README.md),
  [MJPEG 패스스루](2026-08-03-mjpeg-passthrough-web-viewer.md),
  [위치 기준 개명](2026-07-30-camera-position-naming.md),
  [surround-depth](2026-07-31-surround-depth-occupancy.md)

## 배경 — 요구와 구멍

사용자 요구(2026-08-30): "카메라 같은 경우 중요한 센서이므로 별도의 관리 모드를 만들어서
꺼졌을 경우 킬 수 있어야 함."

물리 카메라는 Orbbec Gemini E **6대**(cam_f·cam_r·cam_lf·cam_lr·cam_rf·cam_rr)이고, 한 대
안에서 RGB 스트림(UVC → `usb_cam_publisher` = CCTV 경로)과 depth 스트림(OrbbecSDK →
`surround_depth` 경로)이 갈리며 **두 경로는 같은 장치를 두고 배타**다.

이미 있는 것과 구멍:

| 층 | 자산 | 상태 |
| --- | --- | --- |
| 프로세스 사망·장치 부재·부팅 자동기동 | `Tools/camera_service` (usb-cam@ 인스턴스, Restart=always) | **작성됨·미설치**(2026-07-28 이후 방치, sudo 필요) + 로스터 개명 전 이름(cam0~5) 잔존 |
| 프레임 정체(stall)·뽑았다 꽂음 | 없음 | 노드가 산 채 프레임 0 — 캡처 루프에 재오픈 경로 없음([usb_cam_publisher_node.cpp:232-236](../../src/Sensors/Camera/USB/usb_cam_publisher/src/usb_cam_publisher_node.cpp)), systemd 는 개입 근거 없음 |
| 수동 켜기/끄기/재시작 수단 | 없음 | 설치 후에도 raw `systemctl` 뿐 |

## 결정 (사용자 결정 2건 포함)

1. **외부 감시자 방식** — 신설 ROS2 패키지 `camera_manager` 가 카메라별
   `<cam>/image_raw/compressed` 도착 시각을 구독으로 감시하고, stall 임계(기본 10초) 초과 시
   `sudo -n systemctl restart usb-cam@<cam>` 을 실행한다.
   - in-node 재오픈(퍼블리셔 수정) 대신 외부 감시자를 고른 이유: 퍼블리셔의 blocking V4L2
     `read()` 는 펌웨어가 굳은 장치에서 **프로세스 킬 말고는 못 빠져나온다**(소멸자 주석의
     실측 한계). 외부 재시작만이 사망·정체·펌웨어 wedge 를 한 수단으로 덮는다.
   - cctv_webview 통계 폴링 대신 자체 구독을 고른 이유: 뷰어 생존에 관리 기능이 종속되면 안
     된다. 패스스루라 구독 추가 비용은 카메라당 ~131KB×30Hz 로컬 전달뿐.
2. **자동 + 수동 병행**(사용자 결정): stall 지속 시 자동 재시작(어차피 검출 공백 상태라
   재시작이 손해가 아님) + CLI 수동 제어. 쿨다운(기본 30초)·기동 유예(기본 20초)로 재시작
   폭주를 막는다.
3. **CLI 도구 `camctl`**(사용자 결정 — UI 없음): `status`(장치 실재·유닛 상태·프레임 나이) /
   `start|stop|restart <cam>|all` / `auto on|off`.
4. **자동 개입을 억제하는 3조건** — ① 해당 카메라 depth 경로가 활성(`<cam>/depth/image_raw`
   퍼블리셔 존재)이면 **배타 관계의 의도적 사용**으로 보고 억제 ② 장치 심링크 부재면 재시작
   무익(usb-cam@ 의 exit-3 5초 재시도 루프가 이미 대기 중) — 상태만 보고 ③ 유닛이 inactive
   면 **사용자의 의도적 정지**로 보고 자동 기동하지 않는다.
5. **권한**: `/etc/sudoers.d/camera-manager` 에 `usb-cam@*` 유닛의 start/stop/restart 만
   무암호 허용(전 계정 아닌 `nvidia`, 전 명령 아닌 해당 유닛만). 상태 조회는 무권한.
6. **상태 발행**: `/diagnostics`(diagnostic_msgs/DiagnosticArray, 1Hz) — 기존 텔레그램
   노티파이어·system_health 와 같은 관례. 관리자 자신도 systemd 유닛
   (`amr-camera-manager.service`, Restart=always)으로 상주한다.
7. **배포 계층은 `Tools/camera_service` 에 통합** — 기존 관례(코드는 src/ 패키지, systemd
   유닛·설치는 Tools/camera_service) 유지. 낡은 cam0~5 표기를 현 로스터 이름으로 정정.

## 범위 밖 (이번에 안 함)

- **depth 경로 장애 복구** — OrbbecSDK 점유 해제 실패는 `modprobe -r uvcvideo` (root) 가
  필요해 별도 설계 대상. depth 는 억제 조건으로만 취급.
- 웹 UI 관리 패널(사용자 결정으로 CLI 만), 텔레그램 도메인 브리지, 퍼블리셔 in-node 재오픈.

## Rollback Plan

가역. ① `sudo systemctl disable --now amr-camera-manager` + `/etc/sudoers.d/camera-manager`
삭제 ② `src/Sensors/Camera/USB/camera_manager` 패키지 삭제(다른 패키지가 의존하지 않음)
③ `Tools/camera_service` 는 2026-07-28 상태로 되돌려도 단독 동작(관리자와 독립).

## 검증 계획

- monitor 순수 로직 단위 테스트(상태 전이·억제 3조건·쿨다운) — pytest
- 빌드: `colcon build --packages-select camera_manager`
- 실기(사용자 sudo 필요): install.sh → 케이블 뽑기/꽂기·`kill -STOP` 정체 재현 → 자동 복구
  확인 → 재부팅 생존 1회. **설치 전까지 camera_service 는 2026-07-28 과 같은 미설치 상태다.**
