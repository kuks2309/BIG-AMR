---
id: 2026-07-27-003
type: mistake
category: wrong-assumption
status: closed
reflected_assets:
  - docs/adr/2026-07-27-amr-test-gui.md#부호-정합-초안의-모순-판단은-철회
  - docs/debt/registry.md (debt-004 — '실측 2건 상호 배치' → 'kin_steer_sign 미확정'으로 정정)
  - Tools/amr_test_gui/amr_test_gui/modes.py (모듈 docstring §정합성 메모 + 각 모드 verified=True 복원)  # ⚠ 삭제됨(2026-07-28, docs/adr/2026-07-28-old-gui-removal.md) → 부호 정합 인용은 Tools/amr_test_gui/gui.py 의 JOG 딕셔너리가 계승
  - Tools/amr_test_gui/test/test_controller.py::test_crab_and_forward_share_one_motor_polarity  # ⚠ 삭제됨(2026-07-28) — 회귀 미보전, debt-011
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-motor-node4-sign-crab.md
---

# 2026-07-27 19:00 (KST) — 실측 2건을 "기하학적 모순"으로 오판, 확정된 방향을 미검증으로 격하

## 무엇을 했는가

AMR 구동 테스트 GUI 설계 중, 정본 `config/tongyi_amr.yaml` 과 필드 킷 `docking_drive.py` 를 대조하다가
아래 두 실측이 **동시에 참일 수 없다**고 사용자에게 보고했다.

- ① `drive_sign: -1` · `docking_drive.py:93` — 홈(조향 counts = home)에서 **raw 음수 = 전진**
- ② 2026-07-27 crab 실측 — 조향 **+90° counts** + **raw 양수(+2445)** → **왼쪽(+y)** (IMU ay 실증)

"θ=0 에서 raw 양수가 −x 라면 +90° 회전 후 raw 양수는 −y(오른쪽)여야 한다" 는 도출로 모순을 주장하고,
`debt-004` 를 "실측 2건 상호 배치, 어느 쪽이 오독인지 미확정"으로 등록했다. 나아가 GUI 의
`modes.py` 에서 전진·후진·crab 좌·우 **네 모드 전부를 `verified=False`** 로 표시하고, UI 버튼에
`⚠` 경고를, 테스트에는 "verified 로 표시되면 실패" 라는 단언까지 넣었다.

## 무엇이 잘못이었나

도출에서 자유도 하나를 누락했다 — **조향 counts 증가가 물리적으로 어느 방향 회전인가**(`kin_steer_sign`).
나는 이를 암묵적으로 `+counts = CCW(+θ)` 로 고정한 뒤 모순을 도출했다.

조향 **+counts 가 CW(−θ)** 이면 +90° counts 지령은 바퀴를 −y 로 향하게 하고, 모터 극성(홈에서
raw 음수가 전진 ⇒ raw 양수는 바퀴 지향의 반대)에 의해 이동은 **+y(왼쪽)** 가 된다 — **두 실측이
정확히 정합한다.** 즉 모순은 존재하지 않았고, 어느 실측도 오독이 아니었다.

결과적으로 (a) 지난 세션에 실측으로 **확정된** 방향 정보를 "미검증"으로 격하했고,
(b) 존재하지 않는 모순을 부채로 등록해 후속 세션에 잘못된 조사 과제를 남길 뻔했으며,
(c) UI·테스트에 근거 없는 경고를 심었다.

## 사용자 지적

> "이미 방향은 지난 세션에서 판단한거 아닌지?"

## 원인 분석

`wrong-assumption` — 코드·환경의 동작을 검증 없이 가정.

`kin_steer_sign` 은 정본 `config/tongyi_amr.yaml:15` 에 `kin_steer_sign: 1  # ⚠ 가정` 으로,
**그 값이 가정임이 파일에 명시**되어 있었다. 세션 지시에도 "kin_steer_sign 단정 금지(양 부호 됨)"
라는 경고가 있었다. 그럼에도 나는 두 실측을 대조하는 도출 과정에서 이 값을 **암묵적으로 +1 로
고정**했다 — 명시적으로 "kin_steer_sign 은 +1 이다" 라고 쓴 적이 없기 때문에, 스스로 가정을
세웠다는 사실 자체를 인지하지 못했다.

핵심 패턴: **모순을 주장하는 것도 단정이다.** "된다" 를 검증 없이 말하지 않도록 조심했으나,
"동시에 참일 수 없다" 는 부정형 단정에는 같은 기준을 적용하지 않았다. 부정형 주장은 모든 자유도를
소진했을 때만 성립하는데, 자유도 열거를 하지 않고 결론부터 냈다.

동일 세션의 [2026-07-27-001](2026-07-27-001_freeze-object-list-guessed.md)(freeze 오브젝트 목록 추측)과
같은 뿌리다 — 근거가 불완전한 상태에서 구조적 결론을 확정형으로 서술.

## 재발 방지

지식 자산에 **"부정형 주장 = 자유도 소진 의무"** 와 이번 도출의 정답을 박아, 다음 세션이 같은
대조를 다시 하지 않도록 한다.

1. **ADR 에 철회 기록 유지** — `docs/adr/2026-07-27-amr-test-gui.md` §부호 정합 절에 초안의 모순
   판단을 **철회한다고 명시**하고, 정합 도출(+counts=CW 이면 두 실측 일치)을 남겼다. 삭제가 아니라
   철회로 남긴 이유는 다음 세션이 같은 대조에서 같은 착각을 반복할 때 즉시 되짚을 수 있게 하기 위함.
2. **debt-004 재정의** — "실측 2건 상호 배치"(허위 전제) → "`kin_steer_sign` 미확정(조향 +counts 가
   CCW/CW). 영향 범위는 `driver_node` 의 twist·오도메트리 경로이며 raw 언어로 직접 지령하는
   `Tools/amr_test_gui` 는 무관" 으로 교체. 상환 방법도 "오독분 폐기" → "잭업 상태에서 조향 +90°
   지령 후 바퀴 회전방향 육안 확인" 으로 실행 가능한 형태로 바꿨다.
3. **코드에 정합 도출을 주석으로 고정** — `modes.py` 모듈 docstring 에 "두 실측은 +counts=CW 일 때
   정합하며, 본 GUI 는 raw 언어로 직접 지령하므로 `kin_steer_sign` 의 영향을 받지 않는다" 를 명시.
   네 모드의 `verified` 를 `True` 로 복원하고 UI 의 근거 없는 `⚠` 를 제거했다.
4. **회귀 테스트** — `test_crab_and_forward_share_one_motor_polarity` 를 추가해, 전진/후진과
   crab 좌/우의 raw 부호 대칭과 조향각 배치를 고정했다. 누군가 이 관계를 되돌리면 테스트가 깨진다.
5. **메모리 갱신** — `biguamr-motor-node4-sign-crab` 에 정합 도출 결과를 기록해, 다음 세션이
   "모순"으로 다시 오판하지 않도록 한다.
