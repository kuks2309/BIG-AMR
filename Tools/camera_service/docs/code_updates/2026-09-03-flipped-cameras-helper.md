# 2026-09-03 — 로스터 flip 필드 + `flipped_cameras()` 헬퍼

## 무엇을

- 로스터 스키마에 선택 필드 `flip: true` 추가(부재=정상 장착). 정본 주석은
  `config/camera/camera_common.yaml` 로스터 절.
- `camera_params.py` 에 `flipped_cameras(config) -> list[str]` 신설 — 소비자
  (cctv_webview CSS 회전·yolo_detector 디코드 직후 회전)가 이 목록을 근거로 보정한다.
  퍼블리셔는 MJPEG 패스스루라 불변.
- 단위 테스트 2개 추가(부재 시 빈 목록·true 만 등재 순).

## 왜

T3-1 기체 카메라 6대가 180° 뒤집힌 장착. UVC 하드웨어 flip 컨트롤 부재(v4l2-ctl 확인).

## 검증

test_camera_params.py 18 PASS (16→18)
