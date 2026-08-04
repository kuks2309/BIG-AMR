# amr_motor_cmd_translator — code updates

2026-07-13 / 14:20 - c8f2e9f / **조향 영점(zero) 오프셋 보정 도입** — 실차 실측 δ0 = −1.676°

- **추가** `include/amr_motor_cmd_translator/amr_motor_cmd_translator_node.hpp:37-41` — 멤버 `steer_offset_front_`, `steer_offset_rear_` (rad). 의미 = **엔코더 raw 가 0 일 때의 실제 물리 조향각**.
- **추가** `src/amr_motor_cmd_translator_node.cpp:31-34` — 파라미터 `steer_offset_front_deg`, `steer_offset_rear_deg` 선언. **기본값 0.0 = 보정 없음** (기존 동작 완전 보존).
- **추가** `src/amr_motor_cmd_translator_node.cpp:59-62` — deg → rad 변환 후 캐시.
- **수정** `src/amr_motor_cmd_translator_node.cpp:142-150` `onWheelCmd()` — 조향 지령에 오프셋 차감:
  `target_pos = (s − steer_offset) * ppr * gear_steer / (2π) * dir`
  → cmd 0° 지령 시 raw 를 `−offset` 으로 보내 **물리 0°** 를 만든다.
- **수정** `src/amr_motor_cmd_translator_node.cpp:182-192` `onLowState()` — 조향 피드백에 오프셋 가산:
  `angle = raw * (2π) / (ppr * gear_steer) * dir + steer_offset`
  → 보고값이 **실제 물리각** 과 일치. `encoder_steer_*` (raw pulse) 는 **원본 유지** (보정 미적용).
- **수정** `config/amr_motor_cmd_translator_qd.yaml:19-27` — `steer_offset_front_deg: -1.676`, `steer_offset_rear_deg: -1.676` + 측정 근거 코멘트.

**근거 (실차 개루프 측정, `experiments/2026-07-13_steer_zero_calib/`)**
같은방향 연속 leg (캐스터 플립 배제) 로 드리프트를 두 성분으로 분해:
- 전진 정착 δ −1.216° / 후진 정착 δ −2.136°
- **δ0 = (δ_f + δ_r)/2 = −1.676°** (방향 따라 뒤집힘 = 조향 영점 오차)
- B = (δ_f − δ_r)/2 = +0.460° (안 뒤집힘 = 캐스터/측위)

**검증 주행 PASS** — δ0 **−1.676° → −0.089°** (95% 제거). 횡이동 전진 −3.04→+1.01cm, 후진 +5.36→+1.46cm.
**B 가 +0.460 → +0.493° 로 불변** = 오프셋이 반전 성분만 정확히 상쇄했다는 독립 검증.

**Pre-impact-search** (`angle_front`/`angle_rear` 소비처 전수):
| 소비처 | 영향 |
|--------|------|
| `trnav_fused_odometry` FK (`bodyDisplacement`) | 물리각 입력 → **정확도 개선** |
| motion/jog steer-align 게이트 (cmd ↔ fb 비교) | cmd·fb 가 **함께** 시프트 → 비교 유효성 유지 |
| UI 조향각 표시 | 실제 물리각 표시 → **개선** |
| `encoder_steer_*` 소비처 | raw 유지 → **무영향** |

`colcon build --packages-select amr_motor_cmd_translator` PASS. 실차 재기동 후 `ros2 param get` 로딩 확인 + 조향 피드백 −1.676° (raw 0 → 물리각 노출) 확인.
