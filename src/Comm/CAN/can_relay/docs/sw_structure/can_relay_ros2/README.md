# can_relay (ROS2) — SW 구조 분석 타임라인

대상: `src/Comm/CAN/can_relay/` — 판다 릴레이 경유 Tongyi 4축 모터 구동 ROS2 드라이버.

⚠ **이름 주의**: `Tools/Can_Relay/` 의 판다 **펌웨어** 프로젝트와 이름을 공유한다.
이 폴더는 **호스트 측 ROS2 드라이버** 전용이다(`package.xml:8-18` 의 동일 경고 참조).
펌웨어 쪽 구조 문서는 `docs/sw_structure/panda-relay-firmware/` 다.

| 날짜 | 문서 | 범위 | 계기 |
|---|---|---|---|
| 2026-07-31 | [2026-07-31.md](2026-07-31.md) | 전체 5모듈 + ROS2 인터페이스(토픽 4구독·2발행·3서비스·22파라미터) | Python → C++ 포팅 사전 구조 파악 |

## 동반 다이어그램 (2026-07-31)

- ① 파일 의존 그래프 — [2026-07-31-file-graph.drawio](2026-07-31-file-graph.drawio)
- ② 클래스 관계도 — [2026-07-31-class.drawio](2026-07-31-class.drawio)
- ③ 시퀀스 다이어그램 — [2026-07-31-sequence.drawio](2026-07-31-sequence.drawio)

## 이중 기록

- 루트 정본: `docs/sw_structure/can_relay_ros2/`
- 패키지 병기: `src/Comm/CAN/can_relay/docs/sw_structure/can_relay_ros2/`

## 관련 산출물

- 코드 리뷰(결함·severity): `docs/code_review/can_relay_ros2/`
- 본 SOP 는 **연결만** 보여준다. 품질 판정은 code_review 소관.
