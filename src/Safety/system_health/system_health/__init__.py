"""AMR 본체 PC 자원·소프트웨어 건강 감시 (`system_health`).

Phase 1 은 **비-ROS 상주 샘플러**다. 본 패키지의 Phase 1 모듈(`sysfs`·`ringlog`·`thresholds`
·`sampler`)은 `rclpy` 를 import 하지 않는다 — ROS 가 죽은 순간에도 자원 로그가 남아야 하기
때문이다(ADR `docs/adr/2026-07-28-system-health-monitor.md` §Decision 2).

Phase 2 의 ROS `/diagnostics` 브리지는 같은 패키지에 별도 모듈로 추가되며, 그 모듈만 `rclpy` 에
의존한다. 따라서 **본 `__init__` 에서는 어떤 모듈도 자동 import 하지 않는다** — 여기서
브리지를 끌어오면 Phase 1 의 ROS 무의존이 깨진다.
"""
