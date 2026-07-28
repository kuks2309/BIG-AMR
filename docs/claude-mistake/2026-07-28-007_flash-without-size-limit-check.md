---
id: 2026-07-28-007
type: mistake
category: wrong-assumption
status: closed
reflected_assets:
  - docs/adr/2026-07-27-panda-fw-rewrite-brief.md §3 (앱 영역 49,152 B 한계·근거 file:line·초과 시 증상 명시)
  - .claude memory biguamr-panda-fw-homing-gate (한계·롤백 바이너리 경로·복구 절차 기록)
  - Tools/Can_Relay/fw_backups/panda.bin.signed.pre_homing_2026-07-27 (롤백 바이너리 신규 생성)
---

# 2026-07-27 22:40 (KST) — 앱 영역 한계 미확인 플래시로 판다가 부트스텁에 갇힘

## 무엇을 했는가

조향 호밍 시퀀서를 추가한 펌웨어(서명본 50,052 B)를 판다에 플래시했다. 플래시 직후 장치가
앱 PID(`0xddcc`)가 아니라 **부트스텁 PID(`0xddee`)** 로 재등장했고 버전이
`v1.7.5-EON-unknown-DEBUG`(부트스텁)로 읽혔다 — 앱이 기동하지 못하는 상태였다.

## 무엇이 잘못이었나

앱 영역 크기 한계를 **확인하지 않고** 플래시했다. 한계는 두 곳에 명시돼 있었다.

- `Tools/docking_field_kit/panda/python/__init__.py:295-297` — `for i in range(1, 4)` 로
  **섹터 1~3 만 소거**. STM32F413 의 섹터 1~3 = 각 16 KB → 앱 영역 `0x08004000`~`0x0800FFFF`
  = **49,152 B**.
- `Tools/Can_Relay/panda-firmware/board/usb_comms.h:4` — `extern int _app_start[0xc000];`
  주석 `// Only first 3 sectors of size 0x4000 are used`.

50,052 B 는 이를 900 B 초과했고, 초과분이 소거되지 않은 섹터 4 에 기록돼 서명 검증에 실패했다.

## 사용자 지적

직접 지적은 없었다(내가 즉시 인지·보고). 다만 사용자는 직전에 "플래쉬해" 로 승인했으므로,
승인 전에 한계를 확인해 알렸어야 했다.

## 원인 분석

`wrong-assumption` — **"빌드가 통과했으니 플래시 가능"** 이라고 가정했다.
`arm-none-eabi-gcc -Werror` 는 링커 스크립트상 FLASH 128 K 를 기준으로 하므로 통과했고,
실제 제약은 **호스트 flasher 의 소거 범위**라는 별개 계층에 있었다. 두 계층을 대조하지 않았다.

빌드 산출물 크기가 커지는 것을 로그에서 보고도(49,380 → 49,880 → 49,916 → 50,052 B) 임계값과
비교하지 않았다.

## 재발 방지

지식 보강:

- 재작성 브리프 §3 "반드시 유지해야 하는 제약" 첫 항목에 한계·근거 file:line·초과 시 증상
  (부트스텁 갇힘)·현재 크기를 기록.
- 메모리 `biguamr-panda-fw-homing-gate` 에 한계와 복구 절차를 기록 —
  `Panda.recover()` 후 롤백 바이너리 재플래시.
- **롤백 바이너리를 신규 생성**했다. 사고 당시 직전 운영본 바이너리가 재빌드로 덮여 있었고
  `panda-firmware/` 는 git 미추적이라 복구 수단이 없었다. 호밍 기능을 제거해 재빌드한 결과가
  48,620 B 로 문서상 직전 빌드 크기와 일치해 충실성을 확인한 뒤 `fw_backups/` 에 보존했다.
- 브리프 §8 검증 요구에 "서명 크기 < 49,152 B" 와 "플래시 전 롤백 바이너리 존재 확인" 을 넣었다.
