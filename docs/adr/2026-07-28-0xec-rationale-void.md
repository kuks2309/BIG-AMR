# ADR 2026-07-28 — `0xec`(Seer 호밍 트리거 차단)의 존치 근거 무효화

## 상태

**Accepted — 2026-07-28. 사용자 결정으로 안 A(제거) 채택, 실기 플래시·검증 완료.**

| 단계 | 결과 |
|---|---|
| 제거 범위 | 전역 `seer_block_homing` · 함수 `seer_is_homing_write()` · 게이트 분기 1 · USB `0xec` 케이스 — 잔존 참조 0건 |
| 빌드 | 통과(`-Werror`), 30,188 B (−92 B) |
| 플래시 | 서명 md5 `5caa5cff5173e690…` 실기=빌드 일치 |
| 실기 확인 | `0xec` 요청 → **빈 응답**(핸들러 없음) = 제거 확인 |
| 부수 확인 | 호밍 완주 후 제어권 반환 시 Seer 가 자발적 호밍을 걸지 않음 — 원 근거 무효가 재확인됨 |

⇒ 아래 §결정의 3개 안 중 **A 채택**. B(존치+값 검사)가 지적한 `data[4]` 결함은 코드 자체가 사라져 소멸.

## 맥락

`board/safety/safety_seer_gate.h` 의 `seer_block_homing`(USB `0xec`)은 다음 주석을 근거로 만들어졌다.

> "제어권 반환 직후 Seer 가 자기 초기화로 `0x60FB.4=1`(RstStart)을 보내 조향축을 137° 왕복시킨다."

이 서술은 **세 군데가 틀렸다.**

### ① 제어권 반환은 트리거가 아니다

- 운영자 확인(2026-07-28): "절대 안 그럼".
- 실측: 제어권 조작 없는 정상 운전 8초 수동청취에서 **13,508 프레임 중 `0x60FB` 접근 0건**.
  `Log/dry_baseline_183437.jsonl` — `Tools/docking_field_kit/orin_homing_capture.py --dry`
  (CAN 송신 0, 릴레이 미조작).

### ② 137° 는 이상거동이 아니라 설계 동작이다

호밍은 원점(리밋)을 경유해 **조향 0° 로 복귀**하는 것까지가 한 동작이고, 그 복귀 이동이 약 137° 다.
목표 절대값 node3 = 7,882,020 / node4 = 7,859,062 counts (57,344 counts/°).
같은 파일의 "호밍의 정의" 절, `Tools/docking_field_kit/orin_homing_capture.py` 헤더,
메모리 `biguamr-steer-homing-architecture` 가 모두 이렇게 적고 있다 —
**즉 저장소 안에서 이 주석만 반대로 말하고 있었다.**

### ③ RstStart 가 실제 관측된 조건은 통신 단절 후 복구다

`Log/homing_capture_220350.jsonl` t=17.925 의 `0x60FB.4=1` 은 **intercept 로 CAN2 를 끊어
Node Guarding 타임아웃을 유발한 뒤** 관측된 재호밍이다(그 캡처의 수행 조건이 그것이다).
제어권 반환과는 다른 사건이다.

### 그 결과

- 막으려던 현상 자체가 존재하지 않았을 가능성이 크다.
- 호스트 호출처 **0건**(`grep -rn "0xec" --include=*.py Tools/` → 무결과) —
  기능이 한 번도 켜진 적 없다는 사실과 정합한다.

## 결정 (제안)

**본 ADR 은 "근거가 무효임"만 확정한다. 기능 처리는 셋 중 하나로 사용자가 결정한다.**

| 안 | 내용 | 비고 |
|---|---|---|
| A. 제거 | `seer_block_homing`·`seer_is_homing_write`·`0xec` 삭제 | 코드 약 20줄 감소. 되돌리려면 재구현 |
| B. 존치 + 결함 수정 | `seer_is_homing_write()` 에 값 검사 추가 | 아래 결함 참조 |
| C. 보류 | 현상태 유지 | 잠복 결함이 남는다 |

### B 를 택할 경우 반드시 함께 고칠 결함

`seer_is_homing_write()` 가 `data[4]`(값)를 보지 않아 **호밍 중단(`0x60FB.4 = 0`)까지 차단**한다.
같은 파일 설계 결정 (c)가 "중단은 `0x60FB.4 = 0` 으로 한다"고 선언한 바로 그 프레임이다.
차단이 켜진 상태에서 Seer 가 정지를 보내면 drop + 가짜 ack 되어 **Seer 는 정지가 수리된 줄 알고 축은 계속 간다.**

```c
if ((index == 0x60FBU) && (sub == 0x04U)) { return (f->data[4] != 0U); }  // 값 1(개시)만 차단
```

## Rollback Plan

| 항목 | 내용 |
|---|---|
| 제거 **전** 이미지 | `Tools/Can_Relay/fw_backups/panda.bin.signed.device_2026-07-28_b31d6789` (30,268 B, 서명 `b31d67899631bdf3`) — 단 이 이미지는 **속도 클램프도 없는** 오늘 변경 전 상태다 |
| 제거 **후**(현재 실기) | `…/panda.bin.signed.clamp_and_0xec_removed_2026-07-28_5caa5cff` (30,188 B, 서명 `5caa5cff5173e690`) |
| 되돌리는 법 | `flash_panda.py <제거 전 이미지>` 후 `0xd3`+`0xd4` 서명 md5 가 `b31d6789…` 로 복귀했는지 확인 |
| ⚠ 부분 롤백 불가 | `0xec` 만 되살리려면 소스에서 코드를 복원해 재빌드해야 한다 — 클램프-단독 중간 빌드는 보존에 실패했다(`fw_backups/README-2026-07-28.md`) |
| 되돌림 판단 | 막아야 할 현상(Seer 자발 호밍)이 실제로 관측되는 경우. 현재까지 관측 0건 |

## 부수 소득 — 주석 관행 문제

이 사건의 직접 원인은 **틀린 주석을 후속 세션이 1차 근거로 재인용**한 것이다(본 세션에서 실제 발생).

- 이 저장소의 주석 규칙은 `docs/claude_guideline/coding/conventions.md:24-27` **2줄이 전부**이고,
  "코드가 무엇을, 주석이 왜를 말한다 / 자명한 주석 금지" 외에 아무것도 없다.
- **정정 이력을 코드 주석에 누적하는 관행은 어느 가이드라인에도 없다** —
  `docs/adr/2026-07-24-canhealth-firmware.md`, `docs/adr/2026-07-20-panda-docking-firmware.md`,
  `docs/issues_and_fixes/issues_and_fixes.md`, `safety_seer_gate.h` 4개 파일에 퍼진 습관일 뿐이다.
- 그 결과 `safety_seer_gate.h` 는 주석 231줄 중 **정정블록이 108줄**이고,
  독자가 철회된 주장을 먼저 읽게 된다.

**제안**: 정정은 코드 주석이 아니라 ADR/리뷰 문서에 두고, 코드에는 **정본 1줄 + 문서 링크**만 남긴다.
본 ADR 이 그 첫 적용 사례다(해당 주석 18줄 → 1줄, 근거는 이 문서와
`Tools/Can_Relay/panda-firmware/docs/history/` 로 이관).

**후속**: 2026-07-28 사용자 지시로 펌웨어 **전체 주석 2,048건을 제거**했고(87개 파일),
`panda.bin`·`panda_h7.bin` 이 스트립 전과 **바이트 동일**함을 확인해 기능 무변경을 증명했다.
`cppcheck-suppress` 7건은 기능성이라 보존. 원본은 `docs/history/pre-strip-2026-07-28/` 에 있다.
⇒ 위 "주석 231줄 중 정정블록 108줄" 상태는 **해소됐다**.
