# motion_chain_check — 모션→모터 체인 계약 대조

`2WS 액션 서버 → trnav_motion_mux → amr_motor_cmd_translator → can_relay → CAN` 체인에서
**단위·배선 계약이 서로 맞는지** config 에서 다시 계산해 대조한다.

```bash
python3 Tools/motion_chain_check/check_chain_contract.py            # 대조 (불일치 시 exit 1)
python3 Tools/motion_chain_check/check_chain_contract.py --selftest  # 검사기 검출력 회귀 13건

# 독립 계측기(Seer) 대조 — 로봇을 움직이지 않고 원점·스케일·부호 동시 확인
python3 Tools/motion_chain_check/check_chain_contract.py \
    --seer-capture Log/steer_xcheck_reboot_0deg.jsonl
```

## 왜 있는가

같은 물리량이 네 곳에 흩어져 있고 서로를 모른다.

| 위치 | 담는 값 |
| --- | --- |
| `amr_motor_cmd_translator/config/amr_motor_cmd_translator_qd.yaml` | `gear_steer` `wheel_radius_m` `gear_walk` `pulses_per_rev` |
| `can_relay/config/machine/foil_a082.yaml` | `steer_counts_per_deg` `drive_units_per_mmps` |
| `trnav_2ws_action_server/config/*_params.yaml` ×9 | `wheel_radius` `gear_walk` (2WS 안에서는 RPM 표시용) |
| `qd_action_server_base.hpp:189-194` | 위 값들의 코드 default |

QD(Carrier AGV) 스택에서 2WS 로 이식할 때 상류 값이 그대로 남아, translator 가
**48,332.8 c/deg** 로 환산하는데 이 기체 드라이브는 **57,344.0 c/deg** 였다(90° 지령 → 실제
75.86°). 값을 한 번 고쳐도 다음 이식에서 같은 일이 되풀이되므로, 문서에 적힌 숫자를 믿지 않고
**매번 config 에서 다시 계산해 대조**한다.

## 검사 항목

| id | 대조 | 판정 |
| --- | --- | --- |
| C1 | `ppr × gear_steer / 360` ↔ `steer_counts_per_deg` | 불일치 시 FAIL (필요한 `gear_steer` 를 함께 출력) |
| C2 | `60×gear_walk×10 / (2π×r) / 1000` ↔ `drive_units_per_mmps` | 불일치 시 FAIL (허용 ±0.01% — config 표기 반올림 흡수) |
| C3 | translator `motor_id_*` ↔ can_relay `drive_nodes`/`steer_nodes` | 불일치 시 FAIL |
| C4 | can_relay `steer_limit_deg` ↔ **IK 반원 정규화 90°** | 불일치 시 FAIL. ±90° 는 하드웨어 한계가 아니라 **유일해 구속**이다(ADR `2026-07-26-qd-ik-pm90-unique-solution.md`) — IK 임계는 `normalizeAngle` 의 `M_PI/2` 로 코드에 박혀 config 로 안 바뀐다. 2WS params 의 같은 키는 **2WS 코드가 읽지 않아** 대조에서 뺀다 |
| C6 | 2WS `<action>_params` 9종 기하 ↔ 정본 `robot_geometry_2ws.yaml` | 파일별 FAIL. 실행 시 로드되는 것은 params 쪽이고 정본은 **어떤 launch 도 읽지 않아** 갈라질 수 있다 |
| C5 | **Seer 실측 캡처** ↔ can_relay 가 상류로 올릴 보고각 (`--seer-capture` 지정 시) | 차 > ±0.01° 면 FAIL |

C5 는 `Tools/docking_field_kit/orin_steer_crosscheck.py` 캡처를 쓴다 — 판다 SAFETY_SILENT
passthrough(제어권 미취득·CAN 송신 0)에서 CAN `0x6064` 와 Seer API 1040 각도를 동시 기록한
것이라 두 경로가 독립이다. **원점·스케일·조향 부호를 한 번에** 확인하며, 로봇을 움직이지
않는다. 출력에 「원점 미적용이었다면 몇 도로 읽혔는지」(137.27°)를 함께 찍어 회귀를 눈에
보이게 한다.

WARN 은 exit 코드에 영향을 주지 않는다.

## 허용오차를 그렇게 정한 이유

`foil_a082.yaml:24` 이 `drive_units_per_mmps: 24.447` 로 **5 유효숫자 반올림** 표기라, 정확한
재도출값 24.44619… 와 상대차 3.3e-5 가 항상 남는다. C2 만 ±1e-4 를 쓴다 — 그 반올림을
흡수하면서 검출 대상 크기(이식 잔재 −2.3%)보다 230배 작아 검출력을 잃지 않는다.
`--selftest` 가 이 경계를 함께 지킨다(「표기 반올림 → PASS」 + 「0.1% 어긋남 → FAIL」).

## 한계 (정직 고지)

- **config 끼리의 정합만 본다.** 두 config 가 사이좋게 틀렸으면 통과한다 — 절대 정확도는
  실기 측정의 몫이다.
- 조향 **원점**(홈 counts)은 검사 대상이 아니다. translator 는 원점을 더하지 않고 can_relay 가
  클램프 경계로만 쓰는 상태이며, 그 설계 결정은 별도 ADR 소관이다
  (`docs/code_review/motion-canrelay-chain/2026-08-05.md` Critical 항목).
- 2WS `<action>_params.yaml` 의 `wheel_radius`·`gear_walk` 는 **C1/C2 가 아니라 C6** 이 본다 —
  그 값은 translator 의 SI→raw 환산에 들어가지 않고(2WS 안에서 `drive_rpm` 표시용), 대신
  **정본과 갈라졌는지**가 쟁점이기 때문이다. 실제로 Carrier AGV 값이 남아 휠베이스가
  0.660 m(실측 1.200 m)로 들어가 있었고, 2026-08-05 에 정본 값으로 맞췄다.
- C6 은 **값이 정본과 같은지**만 본다. 정본 자체가 맞는지는 실측의 몫이다.
