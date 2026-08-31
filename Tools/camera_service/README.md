# camera_service — 카메라별 독립 기동·자동 복구 (systemd)

## 왜 만들었나

2026-07-27 18:48 에 시작한 24시간 내구 시험이 **2026-07-28 03:15(경과 8.44 h, 목표의 35%)에
배터리 방전으로 전원이 끊겨** 중단됐다(테스트 대상 결함 아님). 08:11 수동 전원 인가로 복귀했으나
**재부팅 후 카메라가 자동으로 뜨지 않아** 시험 재개가 또 지연됐다.

⚠ **전원 상실 구간(약 5시간)은 본 도구로 회복되지 않는다.** 본 도구가 없애는 것은 그 구간이
아니라 **재부팅 이후의 수동 재기동 의존**이다.

캡처 자체는 `grab_failures=0`(프레임 유실 0)이었으나, 25 fps 미만 저하가 **83건** 있었고
22:15 에 **6대가 동시에 저하**(최저 7.91 fps)했으며 **원인은 미확정**이다(소크 P2).
근거: [`docs/usb_cctv/performance/2026-07-28_soak_8h_issues.md`](../../docs/usb_cctv/performance/2026-07-28_soak_8h_issues.md)

구조적 문제는 둘이었다:

1. **부팅 자동기동 없음** — 카메라용 systemd 유닛이 아예 없었다.
2. **6대가 한 프로세스에 묶임** — `ros2 launch usb_cam_cctv.launch.py` 하나가 6개 노드를
   모두 들고 있어, 그 런치가 죽으면 6대가 동반 사망한다.

본 도구는 카메라 **1대당 systemd 인스턴스 1개**로 쪼개 두 문제를 함께 없앤다.
`usb_cam_publisher` 패키지는 수정하지 않는다(배포 계층만 추가).

## 구성

| 파일 | 역할 |
| --- | --- |
| `usb-cam@.service` | 카메라 1대용 템플릿 유닛. `%i` = 로스터 이름(cam_f·cam_r·cam_lf·cam_lr·cam_rf·cam_rr) |
| `usb-cam.target` | 6대 일괄 제어용 묶음 |
| `amr-camera-manager.service` | **카메라 관리자** 상주 유닛 — 프레임 정체 감시·자동 재시작 (`src/Sensors/Camera/USB/camera_manager`) |
| `sudoers-camera-manager` | `usb-cam@*` 3동사만 무암호 허용 (→ `/etc/sudoers.d/camera-manager`) |
| `dataset-collector.service` | 수집기 유닛 (**기본 미등록** — 디스크 소모 때문) |
| `run_camera.sh` / `run_manager.sh` | ROS 환경 source 후 진입점 실행 (systemd 는 환경이 비어 있다) |
| `exec_camera_node.py` | 카메라 1대 노드 실행. 장치 없으면 **비정상 종료** |
| `camera_params.py` | 로스터 → 파라미터 해석 (순수 로직) |
| `test_camera_params.py` | 단위 테스트 16개 |

카메라 로스터의 단일 근원은 `config/camera/camera_common.yaml` 이다. `camera_params.py` 와
`install.sh` 의 인스턴스 `enable` 목록은 그 파일만 읽는다 — 카메라를 늘리면 `install.sh` 를
다시 돌리면 된다.

⚠ **예외**: `usb-cam.target` 의 `Wants=` 는 로스터 이름 6개를 하드코딩한다(2026-08-30 개명
반영: cam_f·cam_r·cam_lf·cam_lr·cam_rf·cam_rr). 카메라를 늘리면 부팅 자동기동은 되지만
(`WantedBy=multi-user.target`) target 묶음에서는 빠지므로, `install.sh` 재실행과 **별개로
이 파일을 직접 갱신**해야 한다.

## 복구 동작

`exec_camera_node.py` 는 장치 심링크가 없으면 **즉시 exit 3** 으로 죽는다. 유닛이
`Restart=always` + `RestartSec=5` + `StartLimitIntervalSec=0` 이므로 systemd 가 5초마다
영원히 재시도한다. 결과:

- 부팅 직후 장치 열거가 늦어도 붙을 때까지 기다린다
- 카메라가 **빠진 상태에서 서비스가 기동**되면(부팅 시 열거 지연 포함) 붙을 때까지 재시도한다
- ⚠ **이미 떠 있는 노드에서 케이블을 뽑는 경우는 복구되지 않는다** — 장치 존재 검사는 기동
  시점 1회뿐이고(`exec_camera_node.py`), 캡처 루프에 재오픈 경로가 없어 노드는 살아있는 채
  프레임 0 이 된다. systemd 가 개입할 근거가 없으므로 `systemctl restart usb-cam@<cam>` 이
  필요하다 (아래 "프레임 정체" 절과 같은 한계)
- 한 대가 실패해도 나머지 다섯은 영향이 없다

장치가 없는데 노드를 띄우지 않는 것이 핵심이다 —
`usb_cam_publisher_node.cpp` 캡처 루프에는 재오픈 경로가 없어서
(`read()` 실패 시 5 ms 백오프 후 `continue` 뿐), 한번 잘못 뜨면 **노드는 살아있는 채 프레임만
0** 인 상태로 굳는다. 그 상태를 애초에 만들지 않는다.

## 설치

```bash
cd Tools/camera_service
sudo ./install.sh              # 유닛 설치 + 부팅 등록 + 즉시 기동
sudo ./install.sh --no-start   # 등록만
```

## 운용

```bash
camctl status                       # 장치·유닛·프레임 수신율·depth 점유 한눈에 (권장)
camctl restart cam_f                # 한 대 재시작 (all = 전체)
camctl auto off                     # 자동 재시작 잠시 끄기 (on 으로 복귀)

systemctl status 'usb-cam@*'        # systemd 관점 상태
systemctl stop usb-cam.target       # 전체 중지 (관리자는 의도적 정지로 보고 안 되살린다)
journalctl -u usb-cam@cam_f -f      # 특정 카메라 로그 추적
journalctl -u amr-camera-manager -f # 관리자(감시·자동 재시작) 로그

systemctl enable --now dataset-collector   # 수집 상시화(디스크 주의)
```

## 프레임 정체(stall) — 카메라 관리자가 덮는다 (2026-08-30)

카메라가 **죽지 않고 프레임만 멈추는** 장애(뽑았다 꽂음·펌웨어 wedge 포함)는 systemd 만으로는
복구되지 않는다 — 프로세스가 살아 있어 개입 근거가 없다. 이를 외부 감시자
`camera_manager`(`src/Sensors/Camera/USB/camera_manager`, `amr-camera-manager.service`)가 덮는다:
카메라별 `<cam>/image_raw/compressed` 도착을 감시해 정체 지속 시
`systemctl restart usb-cam@<cam>` 을 자동 실행한다(쿨다운·기동 유예 포함).
depth 경로(OrbbecSDK) 점유 중·장치 부재·의도적 정지에는 개입하지 않는다.
설계: [ADR 2026-08-30 카메라 관리 모드](../../docs/adr/2026-08-30-camera-management-mode.md)

## 검증 (2026-07-28)

| 항목 | 결과 |
| --- | --- |
| 단위 테스트 | 16 passed |
| 실제 로스터 해석 | 6대 등재(cam0~cam5), by-id 심링크 실재 확인 |
| 장치 부재 분기 | exit 3 — 재시도 대상으로 정상 분기 |
| 로스터 미등재 분기 | exit 2 — 재시도 무의미한 설정 오류로 분리 |
| 유닛 문법 | `systemd-analyze verify` 경고 없음 |

**미검증**: 실제 설치·기동·재부팅 생존은 확인하지 못했다 — `sudo` 가 암호를 요구해 설치를
실행할 수 없었다. 설치 후 재부팅 1회로 확인이 필요하다.
