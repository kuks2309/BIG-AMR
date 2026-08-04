# can_relay/ui — 리뷰 타임라인

정본: `docs/code_review/can_relay_ui/` · 병기: `src/Comm/CAN/can_relay/docs/code_review/can_relay_ui/`

대상: `src/Comm/CAN/can_relay/can_relay/ui/` — 백엔드 교체형 시험 GUI(5 파일 1,634줄).
`--backend ros2`(드라이버 경유) · `--backend direct`(판다 직결) 가 **같은 위젯 트리**를 쓴다.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-04](2026-08-04.md) | md5 app `e1e82409` · base `5a2e0c62` · direct `85d0da1c` · ros2 `eb02fc3d` · gui_node `c87b627e` (브랜치 `session/7021d760` `aae992a`) | COMMENT | **최초 인벤토리** — 함수 115 전수 · 전역 G1~G14 · ros2 A-1~A-7 · concurrency B-1~B-3 · embedded C-2~C-4. Medium 4(scan 대수 소실 · STEER_HOME 사본 · E-stop 죽은 경로 2) |

⚠ **이 코드는 코딩 SOP §2 를 어기고 만들어졌다** — 「신규 파일은 계획 단계에서 함수표를 생성한다」
(`coding.md:43-44`)를 건너뛰고 코드부터 썼다. 본 문서는 사용자 지적으로 **사후 작성**된 것이다.

- 설계: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`
- 원본 대조 기준선: `docs/code_review/amr-test-gui/2026-08-03.md`
- 드라이버: `docs/code_review/can_relay_ros2/`
