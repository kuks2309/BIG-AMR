# 부채 registry (Debt Registry)

기술·이해·의도 부채의 등록·추적. **항목은 append, 해결도 기록(덮어쓰기 금지).** 코드 마커는 여기 `id` 를 참조한다 (`# TODO(debt-001): ...`).

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| debt-001 | 기술 | (예시) src/foo.py:42 | 임시 하드코딩 상수 | 2026-01-01 | 미해결 | 설정 파일로 이전 |
| debt-002 | 기술 | src/Sensors/IMU/iahrs_driver_ros2/iahrs_driver/launch/iahrs_driver.py:44 | base_link→imu_link static TF 마운트값 (-0.37, 0, 0.29)이 TR-AMR 실측값 — Big-AMR 차체와 다름. 이식 시 원본 그대로 가져옴(bit-identical) | 2026-07-26 | 미해결 | Big-AMR 실제 IMU 장착 위치 실측 후 arguments(--x/--y/--z, 필요시 회전) 갱신. 사용자 나중에 입력 예정 |
| debt-003 | 이해 | src/Actuators/motor_control/motor_control/backend.py:272-300 | freewheel servo-off(0x6040=0x05)를 1회만 assert하고 Node Guarding RTR은 계속 폴링 — 드라이브가 guarding 활동으로 서보를 조용히 재-enable/재기동하지 않는다는 가정이 코드로 확인 불가(HW/펌웨어 거동). ADR은 실측 §8 "무재초기화 재개" 인용하나 벤치 미확인 | 2026-07-26 | 미해결 | 실 Tongyi 드라이브 벤치: freewheel 유지 동안 서보가 Switch-On-Disabled 유지·노드 alive 확인. 조용히 재-enable되면 `fw_active` 중 주기적 `CW_DISABLE` 재-assert 추가 |
| debt-004 | 이해 | src/Actuators/motor_control/config/tongyi_amr.yaml:15 `kin_steer_sign: 1  # ⚠ 가정` | 조향 counts 증가가 물리적으로 CCW(+θ)인지 CW(−θ)인지 미확정. 두 실측(홈 raw음수=전진 / +90°counts+raw양수=좌)은 **CW 일 때 정합**하므로 `kin_steer_sign=-1` 이 시사되나 직접 관측으로 확인되지 않았다. 영향 범위는 `driver_node` 의 twist→모듈 변환·오도메트리 경로이며, raw 언어로 직접 지령하는 `Tool/amr_test_gui` 는 무관 | 2026-07-27 | 미해결 | 잭업 상태에서 조향 +90° counts 지령 후 바퀴 회전방향을 육안 확인(CCW/CW) → `kin_steer_sign` 확정하고 config 주석의 `⚠ 가정` 해제. 확정 전까지 `driver_node` 의 crab/스핀 twist 사용 금지 |
| debt-005 | 기술 | Tool/amr_test_gui/amr_test_gui/panda_can_bus.py | `TongyiSdoBackend` + `PandaCanBus` 통합 경로가 relay 경유 실구동으로 검증된 적 없음(어댑터 작성만). backend 브링업(선판독·init 시퀀스)이 intercept 중 판다 read 로 정상 완주하는지 미확인 | 2026-07-27 | 미해결 | ADR 검증계단 ①dry-run → ②잭업 조향만 순서로 실행하고 결과를 docs/issues_and_fixes/issues_and_fixes.md 에 기록. 브링업 실패 시 선판독 재시도/타임아웃 파라미터 조정 |
| debt-006 | 이해 | Tool/amr_test_gui/amr_test_gui/panda_can_bus.py:send | 판다는 RTR 송신 불가라 backend 의 Node Guarding RTR(20 Hz)을 skip 한다. intercept 중 Seer 의 guard RTR 이 게이트로 forward 되어 모터의 GuardTime(500 ms)×LifeFactor(1) 감시를 대신 만족시킨다는 가정이 코드로 확인 불가 | 2026-07-27 | 미해결 | 잭업 상태에서 intercept 유지 5분 이상 구동하며 노드 HALT 미발생·`snapshot()` last_seen 갱신 지속 확인. HALT 발생 시 펌웨어에 PC-요청 guard RTR 생성 경로 추가 검토 |

<!-- 새 부채는 위 표에 행 추가. 유형: 기술 / 이해 / 의도. 상태: 미해결 / 해결(해결일·커밋 병기). -->
