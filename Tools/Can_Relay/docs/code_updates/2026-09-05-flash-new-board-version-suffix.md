# 2026-09-05 — `flash_new_board.py` 버전 대조가 보드 이름 접미를 무시하도록 수정 (세션 67ed5a48)

- **무엇을**: 검증 단계의 `ver.strip() == want` 를 `ver.strip().split('#', 1)[0] == want` 로 바꿨다(:114).
- **왜**: 펌웨어 0xd6 가 보드 이름이 기록된 보드에서 `DEV-…-DEBUG#trworks-t3-1` 을 돌려주므로 사이드카 등호 대조가 MISMATCH 를 냈다(15인 검토 쟁점 #7, 렌즈 7개 지적).
- **검증**: `python3 -m py_compile` PASS. 실기 대조는 다음 플래시 때 확인.
