# 2026-09-03 — 디코드 직후 장착 보정(180° 회전) — 로스터 flip 연동

## 무엇을

- detector_node: `flipped_cameras` 파라미터 신설([""] sentinel 필터), `_decode` 에서
  해당 카메라 프레임을 `cv2.flip(frame, -1)` 로 180° 회전(line_vision 의 flip_180 관례와 동일).
  이후 추론·검출 좌표는 전부 정립 프레임 기준 → 웹 오버레이와 자동 정합.
- detect.launch.py: 로스터 `flip: true` 파생 `_flipped_cameras()` 신설·주입.

## 왜

T3-1 카메라 6대 전부 180° 뒤집힌 장착(스냅샷 판독 확정), UVC 하드웨어 flip 컨트롤 부재.
뒤집힌 입력으로 추론하면 검출 좌표가 물리 방향과 반대가 된다.

## 검증

- 단위 테스트 36 PASS
- T3-1 배포·재기동: "탐지 시작 — 카메라 6대 … device cuda" 정상, 추론 재개
