# usb_comms.h 빌드 복구 + 새 베이스라인 수립 (2026-09-03)

## 발단
제어권 획득(pc_authority) 시 Seer↔모터 완전 단절을 위한 fwd_hook 수정을 검토하다가,
**현재 커밋된 펌웨어 소스가 컴파일되지 않음**을 빌드로 확정했다.

```
board/usb_comms.h:408: error: 'seer_cover_until_us' undeclared
board/usb_comms.h:426: error: 'seer_block_homing' undeclared
```

## 원인 — 불완전 리팩터 (2ad9a99)
`2ad9a99`(2026-07-28, "커버 랩어라운드 수정·0xec 제거")가 `safety_seer_gate.h` 에서
`seer_cover_until_us`·`seer_block_homing` **선언을 제거**하면서, 이를 **사용**하는
`usb_comms.h` 의 두 지점(0xe8 커버 무장·0xec 케이스)을 **함께 고치지 않았다**
(2ad9a99 diff 에 usb_comms.h 미포함). 그 결과 HEAD 가 빌드 불가 상태로 커밋돼 있었다.

## 무결성 발견 — flash 검증본이 커밋 소스로 재현 불가
- flash 된 검증본 athome_fix(`board/obj/panda.bin.signed`, md5 `91fe428287da0e96adb0944de03073c9`,
  version `DEV-cc5e0491-DEBUG`, 30,488 B)는 **2026-08-03 빌드**로, 당시 git HEAD=`cc5e0491`(07-31)
  **+ 커밋 안 된 로컬 변경**(athome 처리 등)에서 나왔다.
- 빌드 복구(아래) 후 clean 재빌드해도 구 검증본과 **−24 B·6342바이트** 다르다 —
  버전 문자열(18 B)을 초과하므로 코드가 다르다. board/ 상당수가 git 미추적이고 경로 이동 이력이
  있어 **Aug-3 정확 소스의 재현은 사실상 불가**. ⇒ 로봇 펌웨어와 일치하는 커밋 소스가 없었다.
- 참고: Aug-3 검증본 `panda.bin`(unsigned, 보존됨)을 재서명하면 md5 가 `91fe428…` 로 **정확히 재현**된다
  (서명은 결정론적 — 재현 방법론 자체는 유효).

## 조치 — 빌드 복구
`docs/adr/2026-07-28-cover-wraparound-fix.md` 가 명시한 0xe8 처리를 그대로 적용:
```c
/* 0xe8 (usb_comms.h) */
seer_cover_start_us = microsecond_timer_get();
seer_cover_armed = true;
```
그리고 0xec 케이스(seer_block_homing)를 제거(ADR `2026-07-28-0xec-rationale-void.md` — 2ad9a99 가
safety 측에서 이미 제거한 것과 정합). `seer_block_homing` 은 usb_comms.h 2줄에만 있었으므로 완전 제거.
빌드 통과(`-Werror`)·서명까지 확인.

## 새 베이스라인
사용자 결정(2026-09-03): 옛 flash 와 bit 동일을 쫓는 대신, **컴파일되는 이 커밋 소스를 정본 베이스라인**으로
삼고 로봇에 flash → 기본기(호밍·passthrough·조그) **재검증**한다. 이렇게 하면 로봇 펌웨어의
version 문자열이 그 소스 커밋 해시를 가리켜 **재현성이 확보**된다(무결성 공백 해소).

⚠ 이 베이스라인은 구 검증본과 −24 B 다르다(committed athome 로직 vs Aug-3 미커밋 athome 로직 추정,
위치 미확정). 따라서 flash 후 재검증 전까지 「검증됨」으로 인용 금지.

## 상태
- [x] 빌드 복구 커밋(usb_comms.h)
- [ ] clean 빌드 → 새 베이스라인 바이너리(version = 이 커밋 해시)
- [ ] 로봇 flash (사용자 별도 확인 후)
- [ ] 기본기 재검증(호밍·passthrough·조그)
- [ ] 재검증 후에만 「신 베이스라인 검증됨」 확정

관련: `docs/adr/2026-07-28-cover-wraparound-fix.md` · `2026-07-28-0xec-rationale-void.md` ·
[[biguamr-canrelay-flash-new-board]] · `safety_seer_gate.md`(같은 폴더)
