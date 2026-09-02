# 도킹 릴레이 펌웨어 24시간 신뢰성 테스트 결과

> 스크립트: `Tools/panda_bench/reliability_24h.py` (amap-1 벤치: 판다 #1 + PCAN 2ch, 클론 핀맵 CAN2_H=pin23).
> 각 사이클(~0.5s): 게이트 5항목(쓰기차단·가짜ack / 읽기통과 / guard RTR / 모터응답전달 / PC구동+에코차단)
> + 주기적 릴레이 intercept↔passthrough 토글(엔듀런스) + 지연·CAN 에러 감시.

## Run 1 — 2026-07-21 00:10 ~ 2026-07-22 00:10 (24.00h 완주) ✅

| 지표 | 값 |
| --- | --- |
| 경과 | **24.00h / 24h (100%)** |
| 사이클 | **40,779** |
| 총 검증 | **203,895** |
| **실패** | **0 (100.0000% pass)** |
| G1 쓰기차단+가짜ack | 40779 / 0 |
| G2 Seer 읽기통과 | 40779 / 0 |
| G3 guard RTR 통과 | 40779 / 0 |
| G4 모터응답 → Seer 전달 | 40779 / 0 |
| G5 PC구동 도달 + 에코차단 | 40779 / 0 |
| 릴레이 토글(엔듀런스) | **288회** (전부 정상) |
| 예외 / 재연결 | 0 / 0 |
| 지연(Seer읽기→모터, 측정오버헤드 포함) | avg 21.45ms · min 21.13 · max 23.31 (24h 드리프트 없음) |
| CAN 에러카운터 | can0 tx1 rx0 · can1 tx0 rx1 (**무누적**) |

**판정: 24시간 20만 회 검증 무결점.** 게이트·릴레이 전환·에러 무누적 모두 안정. 펌웨어 신뢰성 입증.
※ 지연 21ms는 python/SocketCAN/USB 폴링 측정 오버헤드 — ~~실제 게이트 포워딩은 커널 fwd_hook μs급~~. 핵심 지표(pass율·에러·드리프트) 모두 정상.

> **⚠ 2026-07-27 조건 보완 — 위 판정의 적용 범위** (수치·판정 원문은 변경 없음)
> **조건 ①** 대상은 **가짜 Seer/모터 PCAN 벤치**다(본 문서 머리말 :3 "amap-1 벤치: 판다 #1 + PCAN 2ch"). `docs/can_relay/field-record-orin-nx-2026-07-25.md:40` "**가짜노드 PCAN 벤치 40만회 0실패**(reliability-24h Run1/2). **실차 미검증**".
> **조건 ②** 이 결과는 **fail-safe 를 끈 상태**에서 얻었다 — 같은 파일 `:101` "`set_safety_mode(mode, disable_checks=True)`(python 라이브러리 기본) → `0xf8` → **heartbeat_disabled=true**(fail-safe OFF). **벤치(40만회·24h)는 이 상태 유지로 게이트 동작.**"
> **조건 ③** 실차에서는 동일 안정성이 관측되지 않았다 — 같은 파일 `:123` "릴레이 물리 스위칭 ~11ms outage 중 **in-flight SDO 트랜잭션이 깨지면** Seer 가 노드 상실 판단 → 간헐적 ~1s 모터 dropout → Motor timeout(52111)/odo lost(52106)/Motor is calibrating(54301)", `:129` "engage 시 **bus2 RX 수신에러(REC 100~237)→error_passive→~150~220ms 회복**(릴레이 접점 바운스)".
> → 위 `:20` "릴레이 토글(엔듀런스) 288회 (전부 정상)"·`:23` "CAN 에러카운터 … **무누적**"은 **가짜노드 벤치에 한정된 결과**다. **본 판정을 실차 안전 근거로 인용하지 말 것.**
> **⚠ 위 ※ 의 "커널 fwd_hook μs급"은 근거 없음 → 정정**: `fwd_hook` 은 커널이 아니라 **판다 STM32 펌웨어의 RX 인터럽트**다(`docs/can_relay/usb-can-mapping-table.md:179-180` "`typedef int (*fwd_hook)(int bus_num, CANPacket_t *to_fwd);` — `board/safety_declarations.h:92` … `can_rx()` 인터럽트에서 호출 … (`bxcan.h:190`)"). 본 문서에서 실제 측정된 값은 21.13~24.22 ms 뿐이며(:22, :39) **실 포워딩 지연은 미측정**(추정 μs~수백 μs). 판다 경로의 유일한 시간 지표는 `field-record-orin-nx-2026-07-25.md:120-121` "정상 도착간격(중앙값) 0.47ms · **ENGAGE 갭 11.8ms · DISENGAGE 갭 11.0ms**". "μs 급"은 별개 구현인 **PCAN 하이브리드의 커널 can-gw** 성질이다(같은 파일 `:39` "평시 통과=**커널 can-gw(μs, 무중단)**", `:46`) — 본 펌웨어의 실측이 아니다.

## Run 2 — 2026-07-22 20:37 ~ 2026-07-23 20:37 (24.00h 완주) ✅

| 지표 | 값 |
| --- | --- |
| 경과 | **24.00h / 24h (100%)** |
| 사이클 | **40,742** |
| 총 검증 | **203,710** |
| **실패** | **0 (100.0000% pass)** |
| G1~G5 | 각 40742 / 0 |
| 릴레이 토글(엔듀런스) | **287회** (전부 정상) |
| 예외 / 재연결 | 0 / 0 |
| 지연(측정오버헤드 포함) | avg 21.51ms · min 21.13 · max 24.22 (드리프트 없음) |
| CAN 에러카운터 | can0 ACTIVE(tx1 rx0) · can1 ACTIVE(tx0 rx1) (**무누적**) |

**판정: Run2도 24시간 20만 회 검증 무결점.** Run1+Run2 = 총 **40만+ 회 검증 0실패**.
결과 보존: `~/docking_reliability/run2_result.txt`.

> **⚠ 2026-07-27 조건 보완 (Run 2 · Run 3+ 동일 적용)**: Run 1 아래 조건 블록과 동일 — 가짜 Seer/모터 PCAN 벤치, `heartbeat_disabled=true`(fail-safe OFF, `field-record-orin-nx-2026-07-25.md:101`), **실차 미검증**(`:40`). 실차 engage 에서는 ~11ms 전환 갭·bus2 REC 100~237 error_passive 가 관측됐다(`:123`, `:129`). **본 판정을 실차 안전 근거로 인용하지 말 것.**

## Run 3+ — 연속 진행 (2026-07-23 저녁~)

연속 러너 도입: `~/run_reliability_loop.sh` 가 `reliability_24h.py` 를 24h마다 **자동 반복**(Run3, Run4, …).
- 각 완주 결과 보존: `~/docking_reliability/run{N}_result.txt` / `run{N}_summary.json`
- 진행 로그: `~/docking_reliability/loop.log`, 실시간: `~/docking_reliability/live_status.txt`
- 러너가 시작 시 기존 실행을 대기 후 진행(판다 단일 점유).
