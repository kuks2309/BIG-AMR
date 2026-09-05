# 2026-09-05 — 감시자 재기동 뒤 두절 추론(pid 대조) (세션 67ed5a48)

- **무엇을**: `driver_node` 진단에 `pid` 추가. `health.parse_diag` 가 `pid` 를 보존하고 `restart_inferred(prev, cur)` 를 신설. `supervisor` 는 기동 뒤 첫 진단에서 한 번 대조해 기록 engaged·pid 변경이면 `_was_down=True`(carry 에 `identity_checked` 승계).
- **왜**: 감시자 프로세스 재기동이 두절 이력을 지워 복귀가 사라졌다(15인 검토 #16). `was_down` 영속은 수동 해제와 구분 못 해 채택하지 않음 — ADR 2026-08-15 보강 절 참조.
- **검증**: 패키지 pytest 518 passed / 10 skipped(ROS 소싱). 배포 사본은 다음 동기화 때 반영(구판 드라이버는 pid 부재 → 종전 보수 동작).
