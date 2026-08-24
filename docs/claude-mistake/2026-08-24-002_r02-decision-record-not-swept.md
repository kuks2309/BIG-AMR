---
id: 2026-08-24-002
type: mistake
category: context-missing
status: closed
reflected_assets:
  - docs/can_relay/R02-schematic-review-2026-08-24.md
  - /home/nvidia/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-canrelay-custom-board-bus-wiring.md
---

# 2026-08-24 18:26 (KST) — R02 검토에서 「R02 배선 확정」 기록 자체를 안 열었다 — CN4=IMU 를 "예비"로 서술

## 무엇을 했는가

사용자가 「CAN RELAY R02.pdf 수정된 회로도 검토 바람. **기존 기록 함께 검토할 것**」이라 지시했다.
나는 기존 기록으로 메모리(`biguamr-canrelay-custom-board-bus-wiring`)·클론보드 핀맵 실측 문서
(`docs/can_relay/clone-board-U3P-pinmap-findings.md`)·펌웨어 소스(black.h 등)를 읽고 검토를 완료해,
CN4/bus1 을 **"예비(+5V)"** 로 서술한 검토 문서를 작성·보고했다.

## 무엇이 잘못이었나

**R02 검토의 가장 직접적인 기존 기록 — R02 배선을 확정한 결정 기록 자체를 열지 않았다.**
`Tools/Can_Relay/fw_backups/README-2026-08-23.md:75-87` 에 「**R02 배선 확정 (2026-08-23, 예비
CAN=IMU 용도로 결정)**」 표가 이미 있었다(Seer=CN2/bus0, 모터=CN3/bus2, **IMU=CN4(+5V)/bus1** +
IMU 후속 확인 3건). 그 결과 ① CN4 역할을 "예비"로 오서술, ② 확정 기록 대비 정합 검증(검토의 원래
기준선이어야 할 것)을 누락, ③ 기록이 명시한 IMU 미결 3건을 검토 산출물에서 빠뜨렸다.
결함 판정(커넥터 라벨 3건) 자체는 유효했으나, "기존 기록 함께 검토" 지시를 실질로는 부분 이행했다.

## 사용자 지적

> "CN4는 imu용이고 이미 기록에 있을 것인데 기록 검토 안했지? 분명히 하라고 했는데"

## 원인 분석

category = **context-missing** (보유 원자료를 조사 후보에 넣지 않음 — INDEX §메타 패턴
「보유 원자료」 계열, 2026-08-07-002 의 **다섯 번째** 재발). "기존 기록" 의 탐색 범위를 **내가 이미
아는 곳**(메모리 인덱스 + `docs/can_relay/` 목록 + 메모리가 인용한 파일)으로 한정했고, **검토 대상의
이름("R02")으로 저장소를 전수 검색하는 단계가 없었다.** `grep -rn "R02"` 한 번이면 나왔다 —
실제로 사용자 지적 후 `grep -rni "CN4"` 로 수 초 만에 발견했다. 메모리 파일이 R02 요구 위상을 요약
하고 있었기에 "기록은 이미 확보했다"고 조기 종결한 것이 직접 원인이다. 요약(메모리)은 원기록의
전부가 아니다 — 메모리에는 CN4=IMU 가 없었다(당시 세션 이후 확정된 내용이 원기록에만 추가됨).

## 재발 방지

지식·컨텍스트 보강(반영 완료):

1. **검토 문서 v2 정정** — `docs/can_relay/R02-schematic-review-2026-08-24.md`: 정정 이력 v1→v2 명시,
   확정 기록을 비교 기준선으로 승격(헤더 인용), CN4=IMU 전면 반영, §3.1 IMU 미결 3건 추가,
   OBD 모드 지적을 "IMU 버스 단절"로 상향.
2. **메모리 갱신** — `biguamr-canrelay-custom-board-bus-wiring` 에 CN4=IMU(확정 기록 경로 포함) 반영
   → 다음 세션은 메모리만 읽어도 CN4 용도를 틀리지 않는다.
3. **절차 교훈(이 entry 가 기록)** — 산출물 X(회로도 판번호·보드명·부품명)를 검토할 때는 착수 전에
   **X 의 식별자(“R02”·커넥터명·넷명)로 저장소 전수 grep** 을 1회 수행해 결정 기록·확정 표를 수집
   목록에 넣는다. 메모리 요약이 있어도 원기록 sweep 을 생략하지 않는다(요약은 확정 이후 갱신분을
   놓칠 수 있음).
