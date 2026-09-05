# 2026-09-05 — `backend.shutdown()` 이 버스 헬스 상태를 지운다 (세션 67ed5a48)

- **무엇을**: 제어 루프를 내릴 때 `_bus_health`·`_health_error` 를 비운다. 회귀 `test_shutdown_clears_stale_bus_fault`.
- **왜**: 반환(`~/engage false`) 뒤에는 헬스 폴링이 멈추는데 마지막 BUS-OFF/error-passive 가 남아 진단이 「CAN 버스 이상」을 영구히 올렸다(15인 검토 #15).
- **검증**: 패키지 pytest 514 passed / 10 skipped(ROS 소싱).
