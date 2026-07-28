# 판다 릴레이 펌웨어 재작성 브리프 (Rewrite Brief)

- **Status**: Proposed — 2026-07-28 00:35 예정 적대적 검사 20명 투입의 입력 사양
- **작성**: 2026-07-27 23:37 (사용자 지시: "전체 펌웨어에 대해서 20명 투입해서 적대적 검사를 하고 다시 작성")
- **사용자 진단**: "매번 버그 나올때마다 고치니 스파게티 코드가 되었음" — 동의함(근거 §1)

## 1. 왜 재작성인가 (근거)

- `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h` 가 약 700줄이고 **관심사 5개**가 한 파일에
  섞여 있다: 게이트/포워딩 정책 · Seer 응답 캐시 · freeze 스냅샷 · 호밍 시퀀서 · USB 명령 표면.
- 파일 앞 100줄이 대부분 `⚠ 감사 정정 (2026-07-27, A06)` 주석이다. 원문 주석 → 그 아래 "위 서술은
  부정확하다" 정정 9건. **코드 파악에 철회된 주장을 먼저 읽어야 한다.**
- 캐시에 **축출·TTL(Time To Live)이 없다**. `seer_cache_store_resp()` 의 `valid` 는 한 번 1이 되면
  내려가지 않아 모터 무응답 시에도 마지막 값을 무기한 응답한다(감사 항목 (9)).
- `seer_is_motion_obj()` 의 `0x606C` 포함 여부를 두 문서가 다르게 결정해 **미판정**으로 남아 있다(감사 항목 (8)).
- `_write_init_sequence` 가 Seer 캡처의 프레임 재생이었고 **그중 `0x60FB.4` 가 뭔지 아무도 몰랐다** —
  그게 2026-07-27 "제어권 획득할 때마다 137° 스윙" 사고의 원인이었다.
- 2026-07-27 추가분(호밍 시퀀서 + Seer 필터 + USB 0xea/0xeb/0xec)도 **같은 파일에 덧붙이기만** 했다.

## 2. 범위

**대상 (우리가 쓴 것):**
- `board/safety/safety_seer_gate.h` — 5개 관심사로 분리
- `board/usb_comms.h` 의 CAN-Relay 명령(0xe8·0xe9·0xea·0xeb·0xec·0xc3)
- `board/main.c` 의 CAN-Relay 훅(heartbeat fail-safe, `seer_homing_tick()`)

**제외 (comma.ai upstream, 손대지 않는다):** 드라이버·USB 스택·CAN·부트스텁·crypto.

## 3. 반드시 유지해야 하는 제약

- **앱 영역 49,152 B** — 호스트 flasher 가 섹터 1~3 만 소거한다
  (`Tools/docking_field_kit/panda/python/__init__.py:295-297`). 초과 시 서명검증 실패 → 부트스텁 갇힘(실증).
  현재 30,268 B. 차량 safety 모드 16종은 이미 제거됨(사용자 승인).
- **롤백**: `Tools/Can_Relay/fw_backups/panda.bin.signed.pre_homing_2026-07-27` (48,620 B).
- **fail-open**: heartbeat 상실 시 `set_intercept_relay(false)` + `pc_authority=false`.
- **버전 문자열로 신·구 구분 불가** — `panda-firmware/` 가 git 미추적이라 hash 가 안 바뀐다. 대책 필요.

## 4. 재작성이 반드시 처리할 결함

| # | 결함 | 위치 |
|---|---|---|
| ① | 램프가 호밍 중 `0x6064=0` 을 추종 실패로 오판 → 허위 FAULT | `controller._axis_measurement` 가 `NodeState.status` bit15 를 안 봄. 수정안: bit15==0 이면 `ramp.freeze()` (E-STOP 과 동일 취급) |
| ② | `ui_main._fault_announced` 자동 리셋 없음 → 2회차부터 FAULT 가 조용히 발생 | `Tools/amr_test_gui/amr_test_gui/ui_main.py` |
| ③ | Seer 응답 캐시에 TTL·축출 부재 | `seer_cache_store_resp()` |
| ④ | `seer_is_motion_obj()` 의 `0x606C` 미판정 | 두 문서 결정 불일치 |
| ⑤ | frozen 미매치 시 실시간 캐시로 **조용히 폴백** (실위치 누설 경로) | `seer_cache_reply()` |
| ⑥ | 인쇄쪽/PDF쪽 혼용 인용 오류 | §5 참조 |
| ⑦ | `Tool/`(단수) 경로 인용 잔재 — 정본은 `Tools/` | 전역 |

## 5. 인용 정정표 (2026-07-27 적대적 검증 결과)

| 내용 | 잘못 쓴 것 | 정본 |
| --- | --- | --- |
| §6.9 Home | page 171 | 인쇄쪽 171 = **PDF 173** |
| statusword 비트표 | page 150 | 인쇄쪽 **151** = PDF 153 |
| Bit10 Target reached | page 151 | 인쇄쪽 **152** = PDF 154 |
| Appendix I 오브젝트 표 | page 194 | 인쇄쪽 194 = **PDF 196** |
| Home 36/37 "2s" | §4.6 page 122 | 인쇄쪽 122 (확인됨) |

원문: `References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf`
(표지·파일명 V7.0 이나 본문 러닝헤더는 V5.6 — 판본 상충 주의).

## 6. "존재할 이유가 있나" 패스 (필수)

freeze/캐시 기계 상당 부분이 **`0x60FB.4` 가 뭔지 모르던 시절의 전제** 위에 세워졌다. 그 전제가
2026-07-27 에 바뀌었으므로 각 기능에 대해 다음을 먼저 묻는다:

- 이 기능이 막으려던 사고가 지금도 발생 가능한가?
- 그 사고의 원인 진단이 지금 사실관계로도 유효한가?
- 더 단순한 수단으로 대체 가능한가?

특히 **호밍 중 31.17초 동안 마스터의 `0x6040`·`0x607A` 쓰기가 0건**이라는 실측(2026-07-27 적대적 검증)은
freeze/emulate 설계 전제를 다시 볼 근거다.

## 7. 주석 정책 (변경)

정정을 인라인에 계속 쌓지 않는다. **정정된 사실을 한 번만 진술**하고, 변경 이력은 본 `docs/adr/` 와
`docs/issues_and_fixes/` 로 뺀다. 코드 주석에는 "무엇이 참인가" 와 그 근거 인용만 둔다.

## 8. 검증 요구

- `arm-none-eabi-gcc -Werror` 양 타깃(STM32F4·STM32H7) 클린 + 서명 크기 < 49,152 B
- 플래시 전 롤백 바이너리 존재 확인
- 실기: ① 제어권 획득·반환 시 호밍 0건(2026-07-27 23:31 기준선 재현) ② `호밍` 버튼 왕복 성공
- 적대적 검사는 **읽기 전용**으로 시작하고, 재작성 적용은 사용자 승인 후

## Rollback Plan

`Tools/Can_Relay/fw_backups/panda.bin.signed.pre_homing_2026-07-27` 로 재플래시하면 호밍 기능
도입 이전 상태로 복귀한다(단, 차량 safety 모드 제거 이전 빌드이므로 크기 48,620 B). 재작성본이
부트스텁 갇힘을 유발하면 `Panda.recover()` 후 이 바이너리로 복구한다(2026-07-27 실증 절차).
