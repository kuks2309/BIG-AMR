# ROS 실행기 정체 주입 실기 검증 — 2026-09-05 (세션 67ed5a48, 검토 #5)

도구 `orin_ros_stall_test.py`(실노드 spin 중단으로 정체 주입, 도메인 126). 판다 4e002c(펌웨어 md5 c04e7b07), 배포 사본 host(main 301d453 + 검토 #5 수정).

| 단계 | 관측 |
|---|---|
| engage → 홈 확인 | homed_effective True(전원 유지로 어제 홈 잔존) |
| 조향 +5° 3 s | 실측 3: 5.000°·4: 5.000°, 0x607A 120건(20 Hz×2축), 펌웨어 safety 30·pc_authority 1 |
| 정체 주입 → 심박 중단 | 2.1 s 뒤 `ROS 계층 정체 2.1s (임계 2.0s)` |
| 중단 뒤 0x607A 송신 | **0건**(200→200, 12.7 s 동안) |
| 펌웨어 | safety_mode 0(SILENT)·ho_state IDLE·source 2(failsafe)·result 1(reached)·pc_authority 0 |
| 조향 실측 | 3: 0.00014°·4: −0.00003° (Seer 목표 0° 로 복원) |
| Seer API | steer_angles [−0.0, 0.0] rad·52111 없음 |
| 반환 | `제어권 반환 — passthrough` 정상 |

판정: **PASS 6/6** — 심박 중단 시 조향 재송신이 멈추고(호스트 수정 실증), 펌웨어 fail-safe 가 Seer 목표로 복원한 뒤 권한을 놓는다. 원자료 `logs/orin_ros_stall_test.json`.
