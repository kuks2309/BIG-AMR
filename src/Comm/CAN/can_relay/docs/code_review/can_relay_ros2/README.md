# can_relay ROS2 패키지 — 리뷰 타임라인

정본: `docs/code_review/can_relay_ros2/` · 병기: `src/Comm/CAN/can_relay/docs/code_review/can_relay_ros2/`

⚠ **이름 주의** — 여기서 `can_relay` 는 `src/Comm/CAN/can_relay` **ROS2 드라이버**를 가리킨다.
판다 **펌웨어** 리뷰는 `docs/code_review/can_relay_firmware/` 이며 별개다(debt-015).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| 2026-07-29 | `88cd633` (main, 워킹트리) | REQUEST CHANGES | 10인 감사 + 3인 적대적 심문. High 4건은 전부 기존 코드 지적이며 신설 패키지가 코드로 차단. 인코더 28종이 실측 캡처와 바이트 동일 |

- 신설 결정: `docs/adr/2026-07-29-can-relay-ros2-package.md`
- 등록 부채: debt-015(이름 충돌) · debt-016(조향 홈 상수) · debt-017(브링업 미검증) ·
  debt-018(두 구동 패키지 배타 장치 부재) · debt-019(gui.py 신선도 게이트 소실)
