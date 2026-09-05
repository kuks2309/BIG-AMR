# 2026-09-05 — `block_seer_homing()`(옛 USB 0xec) 제거 (세션 67ed5a48)

- **무엇을**: `panda_can_bus.py` 의 `block_seer_homing()` 과 `ui_main.py` 의 호출 2곳(USB 연결 시 ON, 종료 시 OFF)을 삭제. `FUNCTIONS.idx` 색인 갱신.
- **왜**: 펌웨어의 "Seer 호밍 트리거 차단" 0xec 는 2ad9a99 에서 제거됐고, 2026-09-04 부터 0xec 는 핸드오버 시퀀서 상태 조회(6 B)로 재할당됐다. 옛 호출은 상태 바이트를 "차단 ON/OFF" 로 오독해 로그를 오염시킨다(15인 검토 #10). Seer 재호밍 방지는 이제 펌웨어 핸드오버 복원 시퀀서가 담당한다.
- **검증**: `py_compile` PASS, 저장소 내 참조 0.
