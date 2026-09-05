# 2026-09-05 — 바뀐 펌웨어(핸드오버 시퀀서·보드 이름·래치 제거)에 맞춰 Tools/Can_Relay 재검증·수정 (세션 17186a5f)

## 대조 기준

`panda-firmware/board/usb_comms.h`·`safety_seer_gate.h` 의 현행 소스(미커밋 diff, 빌드 `c04e7b07…` 32,384 B, 10:37) 와
`board/main.c`(미추적). 장치는 다른 세션(67ed5a48)이 100사이클 실기 시험(`e3_100.py`, 11:10 시작)으로 점유 중이라
**USB 를 열지 않고 정적 대조 + 모의 핸들 시험**으로 검증했다. 실기 1회 확인은 그 시험이 끝난 뒤 남는다.

## 검증 결과(도구별)

| 도구 | 펌웨어 계약 대조 | 판정 |
| --- | --- | --- |
| `board_name.py` | 0xed(길이=이름)·0xee(짝수 idx, lo\|hi<<8)·0xef(0x5AA5→resp[0]) 일치. 형식 정규식 = 펌웨어 `board_name_stage_valid` | 일치. 커밋 가드 3조건 중 도구는 safety_mode 만 봤음 → **수정** |
| `flash_new_board.py` | 0xd6 `#<name>` 접미(세션 67ed5a48 이 이미 제거 대조로 수정) · 통상 경로 erase 섹터 1~3 · DFU 경로 3주소 → 섹터 4 보존 | 일치. 보존 확인 출력 없음 → **수정** |
| `flash_dfu_direct.py` | 서명 대조만(버전 미대조) · erase 3주소 | 일치. 보존 확인 출력 없음 → **수정** |
| `ui/flash_backend.py`·`ui/flash_gui.py` | USB 프로토콜 미사용(열거만) | 변경 불요 |
| `seer_can_monitor.py` | Seer API 전용 | 변경 불요 |
| `docs/function_table.md` | `relay_off_latched`(제거됨) 2곳·`seer_handover_request/tick/finish` 서술 구판·`board_name_stage_valid` 미등재 | **수정** |
| `fw_backups/` | 09-04·05 이미지 8종에 매니페스트 없음, 7종이 같은 버전 문자열 | **매니페스트 신설** |

## 무엇을 바꿨나

- `board_name.py` — `ho_status()` 신설(0xec → (state, pc_authority), 구펌웨어 빈 응답이면 None). `set` 경로가 safety_mode 0 에
  더해 시퀀서 IDLE·pc_authority 0 을 확인해 거부 사유를 낸다(펌웨어 `board_name_commit` 가드와 동일 3조건). 읽기 경로도 같은 값을
  출력한다. 왜: 반환 복원(최대 8.5 s) 중에 `set` 을 부르면 펌웨어가 조용히 0 을 돌려주는데 도구는 "safety_mode 0" 만 보고 이유를 못 알렸다.
- `flash_new_board.py` — `read_board_name()` 신설, verify 단계에 `board_name='…'` 출력. 왜: 섹터 4 레코드가 재플래시를 넘어 보존되는지
  플래시 직후 눈으로 확인할 자리가 없었다(예외·구펌웨어는 빈값).
- `flash_dfu_direct.py` — step D 에 같은 출력.
- `docs/function_table.md` — 위 신규 함수·전역 등재, 시퀀서 3함수 서술 현행화, 래치 서술 정정, `board_name_stage_valid` 등재,
  **USB 제어 요청표**(0xd6/0xdc/0xe8/0xe9/0xea/0xeb/0xec/0xed~0xef) 신설, 버전 문자열 함정 주석.
- `fw_backups/README-2026-09-05.md` 신설 + `README.md` 에 일자별 매니페스트 링크. 8종 md5·크기·내부 버전·변경 요지·롤백 짝.
- `tests/test_board_name_flash_tools.py` 신설 — 하드웨어 없이 모의 핸들로 검사(최종 17항목).

## 2차(14:1x) — 구형 펌웨어 허용 제거 (사용자 결정 "구형 펌웨어는 더 이상 사용하지 않는다")

- `board_name.py set` — `0xec` 응답이 없으면(핸드오버 시퀀서 미탑재 = c04e7b07 이전 이미지) 커밋을 시도하지 않고 거부한다. 읽기 경로도 "현행 펌웨어 아님" 으로 표시.
- `flash_new_board.py`(`read_ho_status()` 신설)·`flash_dfu_direct.py` — verify 에 `0xec` 응답을 넣어 **서명 일치 ∧ 버전 일치 ∧ 0xec 응답** 이어야 OK. 이전 이미지를 굽더라도 RESULT 는 MISMATCH.
- `fw_backups/README-2026-09-05.md` — "롤백 짝" 절을 "운용 이미지는 c04e7b07 하나, 나머지는 보관본" 으로 교체. `README.md` 머리말에도 같은 선언(+ 08-29 매니페스트 링크 누락 보완). 바이너리는 지우지 않았다.
- `panda-firmware/docs/rewrite-guide.md` S6 — "한 번 끊으면 래치" 추천 규칙에 현행 펌웨어는 래치 대신 시퀀서로 처리한다는 사실을 병기.
- `docs/function_table.md` — 위 변경 반영("구펌웨어" 표현 제거, `read_ho_status` 등재, 줄 앵커 갱신).

## 검증

- `python3 -m py_compile` 4파일 PASS.
- `python3 Tools/Can_Relay/tests/test_board_name_flash_tools.py` → 17/17 PASS (읽기·스테이징 16회 idx·NUL 패딩·형식 거부·
  0xec 3상태·시퀀서 중 커밋 거부·이름 판독 예외 흡수·`read_ho_status` 3상태·버전 접미 대조). 세션 워크트리에는 판다 파이썬
  라이브러리(`panda-firmware/python`, git 미추적)가 없어 공유 트리의 것을 `PYTHONPATH` 로 빌려 실행했다.
- 실기(2026-09-05 11:30, 다른 세션의 100사이클 시험 100/100 PASS 종료 직후, 읽기 전용 2회 개방):
  `board_name.py` → `serial=4e002c…` `fw=DEV-8dcca835-DEBUG#trworks-t3-1` `safety_mode=0` `board_name='trworks-t3-1' handover=state=0 pc_authority=0`.
  장치 서명(0xd3/0xd4) = `board/obj/panda.bin.signed` = `panda-c04e7b07-boardname-validate_2026-09-05.bin.signed` (백업 8종 중 유일 일치, sigtail md5 `687b16ea…`).
  → 0xd6 접미·0xed·0xec 계약이 실기에서 도구 해석과 일치.

## 호스트 측 호환 확인(수정 없음)

- 노드 `link.py` `_rollback`(0xe8=0 → 0xe9=0 → SILENT)은 현행 펌웨어에서 시퀀서 요청 → 재요청 → 보류 SILENT 로 처리되어 호환된다.
  `release()` 가 즉시 반환하므로 health `safety_mode` 는 최대 8.5 s 뒤에야 0 이 된다. link.py docstring·ADR 의 옛 래치 서술은
  세션 67ed5a48 이 main 에서 이미 정정했다(`link.py:24` "별도 래치는 없다", ADR §Decision 3 "09-05 에 제거").
