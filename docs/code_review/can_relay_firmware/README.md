# CAN Relay firmware 코드 리뷰 타임라인

대상: `Tools/Can_Relay/panda-firmware/board/**` 중 **본 프로젝트 자작분**(comma.ai upstream `26524538` 기반 개조 — Seer 게이트 · 전환 커버 · freeze 스냅샷 · 조향 호밍 시퀀서 · can_health · RTR). 날짜=버전, 최신 위.

펌웨어 트리는 git 미추적이므로 코드 버전은 **파일 내용 md5** 로 고정한다.

| 날짜 | 코드 버전 | Verdict | 핵심 |
|---|---|---|---|
| [2026-07-28](2026-07-28.md) | `safety_seer_gate.h` md5 `6c0b1b05` (비-git, repo HEAD `cd7886d`) | REQUEST CHANGES | Critical 4 · High 21 · Medium 11 · Low 8 · Info 4 |

**⚠ 재리뷰 필요** — 리뷰 후 같은 날 코드가 두 번 바뀌었다(현행 `safety_seer_gate.h` md5 `c35daf53`, 475줄).
Critical 1건(C4 호밍속도)과 High 1건(H4 값검사)이 **해소**됐고, 줄번호 인용 약 317건이 어긋난다 — 상세는 리뷰 문서 상단 고지.

| 리뷰 후 적용 | ADR | 실기 |
|---|---|---|
| 호밍 속도 범위 검증 | `docs/adr/2026-07-28-homing-speed-clamp.md` | 플래시·경계값 검증 완료 |
| `0xec` 제거 | `docs/adr/2026-07-28-0xec-rationale-void.md` | 플래시·빈응답 확인 |
| 주석 2,048건 제거 | — | `panda.bin` 바이트 동일(기능 무변경) |

병기본: `Tools/Can_Relay/panda-firmware/docs/code_review/can_relay_firmware/`.
플로우차트: `2026-07-28-flow.drawio` (박스 184 / 화살표 268, dangling 0, mermaid 1:1 검증).

## 산출물 검증 (재현 가능)

```bash
# ① 플로우차트: XML well-formed · dangling 0 · mermaid↔drawio 1:1
python3 docs/code_review/can_relay_firmware/flow-src/verify.py

# ② 주장 품질: 인벤토리 결번 · severity 분포 · dangling 참조 · 검증기 하드코딩 경로 · 장치조회 없는 [동작] 확정
python3 docs/claude_guideline/code_review/checks/review-claim-lint.py \
        docs/code_review/can_relay_firmware/2026-07-28.md --advisory
```

두 스크립트 모두 실행 디렉터리와 무관하게 저장소 사본을 검증한다(경로가 스크립트 위치 기준).
②의 `--advisory` 는 '실측' 라벨 문장을 나열만 하며 FAIL 하지 않는다 — 각 수치의 1차 출처를 사람이 대조할 것.

배경: 2026-07-28 10-에이전트 감사가 이 산출물에서 잡은 실패 유형을 재발 검출하려고 만들었다
(`docs/claude-mistake/2026-07-28-011`·`-012`·`-013`).

