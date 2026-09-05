# 2026-09-05 — HIL 도구 2종 신설: ROS 정체 주입·감시자 복귀 E2E (세션 67ed5a48)

- **`orin_ros_stall_test.py`** (신설): 실노드 `CanRelayNode` 를 하네스가 spin 하다 멈춰 실행기 정체를 재현. 심박 중단 뒤 0x607A 송신 0·펌웨어 failsafe 복원·Seer 0° 를 판정. 왜: 검토 #5 호스트 수정(`_hb_suppressed` 시 조향 재송신 중단)을 실기로 증명하기 위해. 결과 PASS 6/6(`docs/2026-09-05-ros-stall-field-test.md`).
- **`orin_supervisor_e2e.py`** (신설): 배포 유닛을 그대로 두고 노드 프로세스를 SIGKILL 해 A(드라이버 사망→자동 복귀)·B(드라이버+감시자 동시 사망→pid 추론 복귀)·C(감시자만 재기동→비복귀) 를 관측. 왜: 검토 #16 수정(진단 `pid` 대조)의 배포 환경 검증. 관측 토픽은 `/diagnostics`(드라이버)·`/relay_supervisor/status`(감시자) — 두 발행자 모두 기본 QoS(RELIABLE·VOLATILE, depth 10)라 구독도 기본값으로 맞춘다. 저널 접두 정규식·pgrep 패턴(`^/usr/bin/python3 .*lib/can_relay/relay_supervisor`)은 실 프로세스 명령줄에 맞춰 정정.
