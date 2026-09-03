# ADR 2026-09-03 — Seer 가짜모터 emulator 분리 + node guarding 토글 자체 생성

- Status: Accepted (구현·빌드 완료 후 실기 검증 대기 — flash 시 engage 에서 Seer 단절·재호밍 0)
- 관련: `docs/debt/registry.md` debt-127 · `docs/adr/2026-07-20-panda-docking-firmware.md`(seer_gate 설계) ·
  `Tools/Can_Relay/panda-firmware/docs/history/safety_seer_gate.md`

## Context
「완전 분리」의 올바른 정의(사용자 확언 2026-09-03): 제어권 획득 시 **모터는 PC 명령만** 따르되,
**판다가 Seer 에게 「완전한 가짜 모터」를 emulate** 해 Seer 가 「정상 모터와 통신 중」으로 알고
연결·정상 상태를 유지하게 한다. 즉 분리는 **제어권의 분리**이지 Seer 와의 통신 단절이 아니다.

기존 `seer_gate_fwd_hook` 은 emulate(읽기 대리·guard 대리·fake ack)와 포워딩 결정을 한 함수에
뒤섞어 두었고, node guarding 응답은 `seer_guard_data` **정적 캡처값을 그대로 replay** 했다.
전달(forward)이 있을 땐 모터의 새 guard(토글 진행)가 캐시를 갱신해 문제없었으나, 완전분리로
전달을 끊으면 캐시가 갱신되지 않아 **토글이 정지** → Seer node guarding 실패 → 단절·재호밍(조향 스윙).
어제(2026-09-02) **bus0 단독(모터 없이) emulate 실험**이 「판다가 가짜 모터를 내면 Seer 가 붙어 있다」를
검증했고, 본 결정은 그 실험을 펌웨어로 옮긴다.

## Decision
1. **emulate 를 별도 함수로 분리** — `seer_gate_emulate_bus0(addr, req)` 가 Seer 의 bus0 폴을 유형별로
   처리(읽기 0x40→frozen 대리응답, 쓰기→fake ack, guard RTR→node guarding 응답). fwd_hook 은
   포워딩 결정(`bus_fwd`)만 남기고 emulate 는 이 함수에 위임.
2. **판다가 node guarding 토글을 스스로 생성** — `seer_guard_reply(gn)`:
   pc_authority 면 `(캡처 상태 & 0x7F) | 판다가 매 응답 반전시킨 토글비트(0x80)` 를 Seer(bus0)로 송신.
   cover(전환) 면 종전대로 캡처값 replay. 형식은 실측 캡처(상태 `0x7F`, 토글 `0x7F`↔`0xFF`) 그대로.
3. **freeze(engage) 시 토글 위상 초기화** — `seer_guard_tgl[gn]` 을 모터 마지막 토글값으로 세워
   전환 순간 위상 점프(Seer 오류)를 막는다.
4. pc_authority 시 bus0↔bus2 전달은 계속 차단(완전 분리 유지).

## Consequences
- 전달 없이도 Seer node guarding 이 살아 있어 engage 시 단절·재호밍이 사라진다(기대 — flash 후 실측 확정).
- emulate 가 한 함수에 모여 fwd_hook 가독·유지보수 개선(debt-127 상환).
- (한계) 지금은 node guarding 토글만 자체 생성한다. Seer 가 신선함을 요구하는 다른 객체가 있으면
  추가 emulate 가 필요할 수 있다 — 실기 검증에서 남은 단절 신호가 있으면 그때 확장.

## Rollback
가역. 되돌리려면 이 커밋을 revert(emulator 분리·토글 생성 제거, 종전 정적 replay 복원) 후 재빌드,
직전 베이스라인/구 검증본을 DFU(Device Firmware Update) 직접경로로 재flash. 구 검증본 md5
`91fe428287da0e96adb0944de03073c9` 는 `/tmp/athome_fix_verified.bin.signed` 및 커밋 `e998179`(빌드 재현).

## 검증 (flash 후)
- [ ] 빌드 통과(-Werror)·서명
- [ ] flash diff 사용자 검토
- [ ] DFU 직접 flash + 서명 device==file
- [ ] passthrough(비engage) Seer↔모터 브리지 정상·rx_err 0 (회귀 없음)
- [ ] **engage 시 Seer node guarding 유지 — 단절·재호밍(조향 스윙) 0** (핵심)
- [ ] engage 중 PC 로 모터 소량 구동 → 실주행 방향 확인
