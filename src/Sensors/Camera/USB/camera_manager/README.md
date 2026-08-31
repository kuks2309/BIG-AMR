# camera_manager — 카메라 관리 모드

카메라 6대(Orbbec Gemini E 의 RGB/CCTV 경로)의 **프레임 생존을 감시하고, 정체 시
usb-cam@ systemd 유닛을 자동 재시작**하는 상주 노드 + `camctl` CLI.
설계: [ADR 2026-08-30](../../../../docs/adr/2026-08-30-camera-management-mode.md) ·
배포: [Tools/camera_service](../../../../Tools/camera_service/README.md)

## 동작

- 카메라별 `<cam>/image_raw/compressed` 도착 시각만 기록(디코드 없음 — MJPEG 패스스루 원칙).
- 1Hz 판정: 정체(기본 10초) 지속 시 `sudo -n systemctl restart usb-cam@<cam>` —
  쿨다운 30초·(재)기동 유예 20초로 폭주 방지.
- **자동 개입 억제 3조건**: depth 경로 점유 중(배타) · 장치 심링크 부재(usb-cam@ 의
  5초 재시도 루프가 대기) · 유닛 의도적 정지.
- 상태는 `/diagnostics`(DiagnosticArray) 1Hz. 자동 재시작 토글은 `~/set_auto`(SetBool).

## 사용

```bash
camctl status               # 장치·유닛·프레임 수신율·depth 점유
camctl restart cam_f        # 수동 재시작 (all = 전체)
camctl start cam_f | stop cam_f
camctl auto on|off          # 자동 재시작 토글
```

설치(systemd 유닛·sudoers): `cd Tools/camera_service && sudo ./install.sh`

## 표

함수표·전역변수표·토픽 표: [docs/function_table.md](docs/function_table.md)
