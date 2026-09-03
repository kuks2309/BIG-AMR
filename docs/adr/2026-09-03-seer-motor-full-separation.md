# ADR 2026-09-03 — 제어권 획득 시 Seer↔모터 완전 분리 (fwd_hook)

- Status: Accepted (실기 검증 대기 — flash 후 호밍/passthrough/조그 재검증)
- 관련: `docs/adr/2026-07-20-panda-docking-firmware.md`(seer_gate 설계) ·
  `Tools/Can_Relay/panda-firmware/docs/history/build-fix-and-baseline-2026-09-03.md`(새 베이스라인)

## Context
`seer_gate_fwd_hook`(safety_seer_gate.h)은 `emulate`(=cover ∥ pc_authority) 구간에서 Seer 의 bus0
읽기(0x40)·가드(0x701-4 RTR)·그 외 프레임을 **bus2(모터)로 포워딩**(`bus_fwd=2`)하고, bus2 의 그 외
프레임을 **bus0(Seer)로 포워딩**(`bus_fwd=0`)했다. 사용자 설계는 **제어권 획득(pc_authority) 시 Seer 와
모터 제어기가 완전히 분리**되는 것 — Seer 는 PC 가 만든 대리응답만 받고, 모터는 PC 명령(bus2 직결)만
받으며 둘 사이에 아무 프레임도 건너지 않는다.

별개 관측(원인 미확정): 2026-09-03 intercept engage 중 host `can_send` 가 `USBErrorTimeout` 을 냈다.
이는 heavy Seer 트래픽(~1700/s)이 판다 USB 를 포화시킨 것으로, **주범은 「받은 프레임의 USB 큐잉」**이고
포워딩은 MCU 부하를 더할 뿐이라 **can_send 타임아웃의 원인으로 증명되지 않았다.** 따라서 이 분리를
「USB 수리」로 정당화하지 않는다 — 아래 Decision 의 근거는 오직 설계(완전 분리)다.

## Decision
`emulate` 구간의 bus0↔bus2 포워딩을 **pc_authority 일 때만** 차단한다(전환커버·passthrough 는 불변):

| 위치(safety_seer_gate.h fwd_hook) | 전 | 후 |
|---|---|---|
| bus0 Seer 읽기(0x40) | `bus_fwd=2` | `pc_authority ? -1 : 2` |
| bus0 Seer 가드(0x701-4) | `bus_fwd=2` | `pc_authority ? -1 : 2` |
| bus0 그 외(SYNC 등) | `bus_fwd=2` | `pc_authority ? -1 : 2` |
| bus2 모터 그 외 | `bus_fwd=0` | `pc_authority ? -1 : 0` |

- Seer 대리응답 생성(`seer_cache_reply`·`seer_fake_ack`·가드 응답)은 **유지** — Seer 는 frozen/캐시
  응답을 받아 fault 하지 않는다. 끊는 것은 bus2 로의 전달뿐이다.
- Seer 쓰기(drop+fake ack), bus2 모터 응답(0x581-4/가드 drop)은 이미 분리돼 있어 변경 없음.
- **passthrough(pc_authority=false·emulate=false)** 와 **전환커버(disengage 시 pc_authority=false·cover=true)**
  는 `pc_authority=false` 라 종전대로 브리지된다 — 제어권 반납 handback 이 매끄럽게 유지된다.

## Consequences
- (의도) 제어권 획득 시 Seer↔모터 물리·논리 완전 분리. 모터는 PC 명령만.
- (부수·미확정) bus2 로의 Seer 폴 재전송 제거로 MCU 부하·bus2 트래픽은 준다. 그러나 intercept USB
  포화의 주범은 「받은 Seer 프레임 USB 큐잉」이라 **can_send 타임아웃 완화는 보장되지 않는다 — flash 후
  실측으로만 판정**. USB 는 이 결정의 근거가 아니다.
- (주의) pc_authority 중 Seer 는 frozen 스냅샷만 봄 — 실제 로봇 상태와 어긋남(설계 의도, engage 동안만).

## Rollback
가역. 되돌리려면 위 4개 `pc_authority ? -1 : N` 을 원래 상수(`2`,`2`,`2`,`0`)로 되돌려 재빌드 후,
검증본/직전 베이스라인을 DFU 직접경로로 재flash. 직전 베이스라인 unsigned 바이너리·구 검증본은
`/tmp/athome_fix_verified.bin*` 및 커밋 `e998179`(빌드 재현 가능)로 복원 가능.

## 검증 (flash 후)
- [ ] 빌드 통과(-Werror)·서명
- [ ] DFU 직접 flash + 서명 device==file
- [ ] engage 중 host `can_send` USB 타임아웃 재현 여부(완화 확인)
- [ ] 호밍 DONE 도달(조향 node3·4)
- [ ] passthrough(비engage) Seer↔모터 브리지 정상·rx_err 0
- [ ] 조그 방향 정합
