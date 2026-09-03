# can_relay ROS2 패키지 — 리뷰 타임라인

정본: `docs/code_review/can_relay_ros2/` · 병기: `src/Comm/CAN/can_relay/docs/code_review/can_relay_ros2/`

⚠ **이름 주의** — 여기서 `can_relay` 는 `src/Comm/CAN/can_relay` **ROS2 드라이버**를 가리킨다.
판다 **펌웨어** 리뷰는 `docs/code_review/can_relay_firmware/` 이며 별개다(debt-015).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-03](2026-08-03.md) | 리뷰 시점 md5 (backend `1500b715` · driver_node `4f0d833f` · link `91816934` · protocol `333f03cd` · safety `27de8c07`) → **조치 후** backend `b447f1ad` · driver_node `8f54b2f0` · link `4f0719a5` · protocol `de2c3521` | REQUEST CHANGES (조치 완료, 승인은 별도 lane) | delta — 함수 34행 추가(#79~#112) · 2행 삭제 · 전역 G14~G22. High 2(호밍 중 `~/home_cancel` 도달 불가 · `heartbeat` 만 락 밖) **둘 다 같은 날 조치** — ADR `docs/adr/2026-08-03-can-relay-node-concurrency.md`, 회귀 192→230 |
| [2026-07-29](2026-07-29.md) | `88cd633` (main, 워킹트리) | REQUEST CHANGES | 10인 감사 + 3인 적대적 심문. High 4건은 전부 기존 코드 지적이며 신설 패키지가 코드로 차단. 인코더 28종이 실측 캡처와 바이트 동일 |

⚠ **코드 버전 고정** — 이 패키지는 2026-08-03 리뷰 시점엔 git 미추적(→0건)이었고,
07-29 판은 리뷰 커밋 `88cd633` 으로 적었으나 패키지가 미커밋이라 그 해시가 이 패키지 코드를 고정하지 못했고(2026-08-03 §코드 버전이 지적, SOP 룰 12 미충족), 08-03 판부터 파일 md5 로 고정했다. 이후 2026-08-04 커밋 `e56cd38` 로 추적돼
(현재 `git ls-files` → 51건) 다음 판부터는 커밋으로도 고정 가능하다.

- 신설 결정: `docs/adr/2026-07-29-can-relay-ros2-package.md`
- 등록 부채: debt-015(이름 충돌) · debt-016(조향 홈 상수) · debt-017(브링업 미검증) ·
  debt-018(두 구동 패키지 배타 장치 부재) · debt-019(gui.py 신선도 게이트 소실)
