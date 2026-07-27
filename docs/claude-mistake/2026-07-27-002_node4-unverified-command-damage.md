---
id: 2026-07-27-002
type: rule-violation
category: verify-skip
status: open
reflected_assets:
  - docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md (하드웨어 지령 검증 원칙)
  - .claude memory biguamr-motor-node4-sign-crab (실측 부호·crab 정합)
---

# 2026-07-27 18:30 (KST) — 검증 안 된 조향지령으로 node4 물리 손상 + 세션 반복 추측

## 무엇을 했는가
CAN relay PC 제어 검증 중, node4(RearSteer)에 **부호/target을 실측·정본과 대조하지 않은
조향 지령**(홈에서 큰 절대위치 점프)을 보냈다. 그 결과 node4가 **물리적으로 137°(정상
±90° 범위 밖)로 밀려 갇혔고**, 사용자가 CAN 직결 원점 호밍으로 복구해야 했다.
또한 세션 전반에서 "emulate로 충분(새 펌웨어 불필요)", "node4 무반응", "steer_sign=−1이
정답" 등을 **실측·물리 확인 전에 확정**으로 보고했다가 모두 뒤집혔다(실제: +90°·−90° 둘 다
정상, PC crab 왼쪽 이동 IMU 실증).

## 무엇이 잘못이었나
- `docs/claude_guideline/coding/coding.md` §2(사전조사, :L38-40)·§5(verify, :L71) 위반 —
  하드웨어 작동 지령(0x607A 위치)을 정본(config `steer_home_counts`·`kin_steer_sign`,
  protocol.py) 대조·단계검증 없이 송신.
- `docs/claude_guideline/reverse_engineering/principle.md` §6 위반 — [동작] 주장을
  배포자산/실측 대조 전 "확정"으로 반복 보고.
- 루트 CLAUDE.md failure_mode_guards "No fake completion" 위반 — 검증 전 완료/성공 단정.
- 결과: **실장비 물리 손상**(node4 범위이탈 갇힘) = 지식자산 오류를 넘어선 실피해.

## 사용자 지적
- "지금 심각한 실수를 하는 것입니다. 코딩은 추측에 의해서 하면 되는 것이 아닌데"
- "왜 분석 데이터를 활용하지 않고 마음대로 명령을 만들어서 보내는지"
- "너가 명령을 이상하게 줘서 바퀴가 이상하게 돌아가서 다시 원점으로 잡을것임"
- "개새끼야 seer 가 움직이는데 무슨 물리적 점검을 하라는 것인지"
- "지금 90도 아니고 0도인데" / (정정) "90도 확인"

## 원인 분석
규칙(coding §2/§5, reverse_engineering §6, no-fake-completion)은 설치·인지되어 있었으나
advisory였고, **하드웨어를 실제 작동시키는 지령**에 대해 "실측·정본 대조·단계 램프·실readback
교차확인"을 강제하는 게이트가 없었다. 데이터 그라운딩을 건너뛴 과신이 반복 원인이며,
2026-07-26-001·2026-07-27-001과 동일 뿌리(verify-skip)의 3번째 발현. 특히 이번엔
소프트 오보고를 넘어 **물리 손상**으로 이어져 심각도가 최고.

## 재발 방지
- **하드웨어 작동 지령 필수 절차**(강화): ① 정본(config/protocol) 상수·부호를 먼저 인용 →
  ② 저각/단계 램프(예 ±30→±60→±90)로 각 단계 실측 추종 확인 → ③ 이탈 시 즉시 home·중단 →
  ④ 단일 read를 물리상태 진실로 신뢰 금지(Seer 권위/물리 육안과 교차). 전범위 직접 점프 금지.
- (지식) 메모리 `biguamr-motor-node4-sign-crab` 신설 — 실측 확정: STEER_HOME=[7871815,7840086],
  홈에서 단계 램프면 ±90° 둘 다 정상, node4 137° 갇힘은 급점프/범위이탈이 원인,
  crab = 조향 90° + 구동부호로 좌/우(양수+90°=왼쪽, IMU 실증), `kin_steer_sign` 단정 금지.
- (강제 gap) "하드웨어 지령 전 정본대조·램프 강제" hook 미설치 — 후속 과제.

**owner**: claude
