# 2026-08-30 — 카메라 관리 모드 신설 (camera_manager + camera_service 확장)

요구(사용자): "카메라 같은 경우 중요한 센서이므로 별도의 관리 모드를 만들어서 꺼졌을 경우
킬 수 있어야 함." 결정(사용자): 자동+수동 병행 · 인터페이스는 CLI.
설계: `docs/adr/2026-08-30-camera-management-mode.md`

## 신설 — `src/Sensors/Camera/USB/camera_manager` (ament_python)

| 파일 | 내용 |
| --- | --- |
| `camera_manager/monitor.py` | 카메라 1대 판정 상태기계(순수) — 상태 7종, 억제 3조건(depth 점유·장치 부재·의도적 정지), 정체 임계 10s·쿨다운 30s·기동 유예 20s |
| `camera_manager/roster.py` | 공용 로스터 로더(`config/camera/camera_common.yaml`, launch 와 동일 탐색 규칙) |
| `camera_manager/systemd_ctl.py` | systemctl 래퍼 — 조회 무권한, 제어는 `sudo -n`(usb-cam@ 3동사만) |
| `camera_manager/manager_node.py` | 상주 노드 — 압축 토픽 6개 구독(도착 시각만), 1Hz 판정, 재시작은 전용 스레드 큐(콜백 내 subprocess 금지), `/diagnostics` 발행, `~/set_auto` |
| `camera_manager/cli.py` | `camctl` — status(장치·유닛·수신율·depth)/start/stop/restart/auto |
| `test/` | 단위 테스트 27개(상태기계 14·로스터 6·systemctl 래퍼 7) |

## 수정 — `Tools/camera_service` (배포 계층)

- `amr-camera-manager.service`·`run_manager.sh`·`sudoers-camera-manager` 신설.
- `install.sh`: 관리자 유닛 + sudoers(설치 전 `visudo -cf` 검증) 설치·enable·기동 추가.
- `usb-cam.target` `Wants=`: 개명 전 이름(cam0~cam5) → 현 로스터 이름(cam_f·cam_r·cam_lf·cam_lr·cam_rf·cam_rr) 정정. `usb-cam@.service` 주석 동일 정정.
- `README.md`: 관리자 층·camctl 운용·"프레임 정체" 절을 현행화.
- `docs/function_table.md` 신설(배포 계층 표 부재였음).

## 검증 (2026-08-30)

- 단위 테스트: camera_manager 27 passed + 기존 camera_service 16 passed.
- 빌드: `colcon build --packages-select camera_manager` 성공.
- 실기 스모크: `manager_node` 기동 → 로스터 6대 인식 → `/diagnostics` 수신 확인 —
  cam_rf 등 4대 `stopped`(유닛 미설치라 정확), cam_lf·cam_lr `no_device`(심링크 실부재).
- `camctl status --no-measure` 실기 출력 정상. `bash -n`·`visudo -cf`·`systemd-analyze verify` 통과.

## 실설치·수정 (2026-08-30 저녁, 사용자 install.sh 실행 후)

- **[Fix] 래퍼 `set -u` × ROS setup.bash** — 설치 직후 유닛 7개 크래시 루프. 두 래퍼에서
  `-u` 제거(`set -eo pipefail`). 상세: `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-30 ·
  `docs/claude-mistake/2026-08-30-002`.
- **실설치 검증 완료**: 장치 실재 4대 `active`·~30Hz 스트리밍, 부재 2대(cam_lf·cam_lr)는
  설계된 exit-3 대기 루프. **자동 복구 전 체인 실증** — 실노드 `kill -STOP` 정체 주입 →
  11초 만에 감지(`정체 10.6s — 자동 재시작 1회째`) → sudoers 무암호 `systemctl restart` →
  새 PID·프레임 복귀(journal 21:02:06).
- ~~미검증 잔여~~ **→ 2026-08-31 전부 해소**:
  - cam_lf·cam_lr 부재 원인은 USB 전기 수준 부재(커널 로그: 부팅 후 두 포트 이벤트 0건, 둘 다
    좌측 카메라)로 확정 → 09:43 물리 재연결 즉시 usb-cam@ 재시도 루프가 **명령 0회로 자동 기동**.
  - 재부팅(09:49) 생존 확인 — 유닛 7개 부팅 자동기동, 6대 25~28Hz 스트리밍, 관리자 판정 ok 6/6.
  - 이로써 ADR §검증 계획 전 항목 완료(설치 · 정체 자동복구 · 재연결 자동복귀 · 재부팅 생존).
