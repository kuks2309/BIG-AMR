# 2026-09-05 — `ui/backend_direct.py` `_release_steps()` 의 `P_` 미정의 수정 (세션 67ed5a48)

- **무엇을**: `_release_steps()` 첫 줄에 `P_ = self._cls` 를 추가했다. 람다 세 개 중 0xE8=0·0xE9=0 두 단계가 이 이름을 참조한다.
- **왜**: 스코프에 `P_` 가 없어 NameError 가 나고, 단계별 예외 흡수 설계 때문에 조용히 `set_safety_mode(0)` 만 나갔다. 새 펌웨어는 단독 SILENT 도 복원 뒤 적용하도록 보강했지만(ADR 2026-09-04-canrelay-handover-restore-sequencer 09-05 절) 호스트 결함 자체는 고쳐야 한다. 15인 적대적 검토 쟁점 #2.
- **검증**: `python3 -m py_compile` PASS. 함수 시그니처 변화 없음(함수표 갱신 불요). 배포 사본은 main 병합 후 재빌드 필요.
