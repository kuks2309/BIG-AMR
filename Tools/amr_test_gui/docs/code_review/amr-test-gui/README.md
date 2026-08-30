# amr_test_gui — 리뷰 타임라인

정본: `docs/code_review/amr-test-gui/` · 병기: `Tools/amr_test_gui/docs/code_review/amr-test-gui/`

대상: `Tools/amr_test_gui/gui.py` (PyQt5 단일 파일, ROS2 미경유 · 판다 USB 직접 구동).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-03](2026-08-03.md) | `gui.py` md5 `7a043e4c` (1,157줄, repo HEAD `cc5e049` 워킹트리) | REQUEST CHANGES | **최초 인벤토리** — 함수 56 전수(#1~#53 + inner 3) · 전역 G1~G15 · 전체 흐름도. High 4(정착 판정 신선도 부재 · heartbeat 락 밖 · 단발 송신 워치독 부재 · 호밍 취소 불가) |

⚠ **2026-08-03 이전에는 날짜 문서가 없었다** — 이 폴더에 `2026-07-27-flow.drawio` 만 있었다.
그 drawio 는 그 시점 구조의 기록으로 남겨 두고, 현행 대조 대상은 `2026-08-03-flow.drawio` 다.

- 작성 목적: **ROS2 동일 구현의 대조 기준선.** 이식 설계는 `docs/adr/2026-08-03-amr-test-gui-ros2-port.md`.
- ⚠ **이식본이 실재한다** — `src/Comm/CAN/can_relay/can_relay/ui/gui_node.py`(`ros2 run can_relay can_relay_gui`).
  원본은 실기 대조(ADR §Verification 게이트 4) 전까지 존치하며, 두 벌 유지의 위험은 **debt-039** 로 추적한다.
  본 문서의 High 4건 중 3건은 이식본에서 구조적으로 해소됐고, **원본에는 그대로 남아 있다.**
- 관련: `docs/code_review/can_relay_ros2/`(이식 대상 드라이버) · debt-019(gui.py 신선도 게이트 소실)
