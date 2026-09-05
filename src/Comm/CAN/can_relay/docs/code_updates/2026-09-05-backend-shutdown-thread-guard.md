# 2026-09-05 — `backend.shutdown()`/`start()` 제어 스레드 이중 기동 가드 (세션 67ed5a48)

- **무엇을**: `shutdown()` 이 `join(1.5)` 뒤 스레드가 살아 있으면 참조를 지우지 않고 경고를 남긴다. `start()` 는 살아 있는 이전 스레드가 있으면 `RuntimeError` 로 거부한다.
- **왜**: 참조를 무조건 `None` 으로 지우면 다음 `start()` 가 두 번째 `_loop` 를 띄워 bus2 writer 가 둘이 된다(15인 검토 #14).
- **검증**: `py_compile` PASS, 패키지 pytest 513 passed / 10 skipped(ROS 소싱).
