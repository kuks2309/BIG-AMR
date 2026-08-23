# `dock_control` 코어 함수표 (설계본)

M2 착수 전 **설계 단계에서 작성**한 표다 — 코딩 SOP §2 *"신규 파일(처음 작성) → 계획 단계에서
표를 생성한다(설계할 함수·전역변수를 표로)"*. 구현 후 실제 시그니처·줄번호로 갱신한다(§6).

- **작성**: 2026-08-12 (KST) · sess:10706d71
- **승인 근거**: 사용자 2026-08-12 *"M2 착수 — 순수함수 5종 + 골든"*
- **원본(정본)**: [`references/tc_docking/phase1_gui.py`](../../../../../references/tc_docking/phase1_gui.py) — **무수정 보존**
- **선행 정독**: [M0-8 worker 전문](../../docs/2026-08-10-M0-8-worker-full-read.md) ·
  [M0-9 crab 라인 리뷰](../../docs/2026-08-12-M0-9-crab-variants-line-review.md) ·
  [M0-4 상수표](../../docs/2026-08-10-M0-4-constant-table.md) ·
  [이식 계획 §3.2](../../docs/2026-08-10-docking-motion-port-plan.md)

## 0. 이 배치의 범위

계획 §3.2 의 코어 순수함수 **6종 중 5종** + 그 5종이 공유하는 PID 엔진 1종.
`precisionAssist` 는 **ADR-PRECISION 결재 대기**라 이번 배치에서 제외한다(빈 자리로 둔다).

`orbit_wheel_cmd`·`fwd_wheel_cmd` 는 **재구현하지 않는다** — 계획 §3.4(ADR-IK 안1′)에 따라
`trnav_qd_kinematics/src/qd_inverse_kinematics.cpp` 를 **소스로 편입**하고 md5 를 동결한다.
빌드 배선이 걸린 별도 단계라 이 배치 뒤에 붙인다.

## 1. 함수표

위치 = 이식본. 선언은 `dock_core.hpp`, 정의는 `dock_core.cpp`.

| # | 함수 | 선언 | 정의 | 정본 | 용도 | 부작용 |
|---|---|---|---|---|---|---|
| 1 | `distPidStep` | `dock_core.hpp:77-79` | `dock_core.cpp:24-52` | `phase1_gui.py:352-371` | **PID 엔진** — 거리·수평(δ)·자세가 모두 재사용. anti-windup 3중 + 부호교차 하드리셋 + 측정미분 LPF | `PidState&` 갱신(`i_term`·`d_filt`) — **유일한 가변 인자** |
| 2 | `phase4Delta` | `dock_core.hpp:93-96` | `dock_core.cpp:54-71` | `phase1_gui.py:1836-1846` | 카메라 수평오차 → 조향 보정 δ[rad] | `PidState&` 갱신 · `*out_e_px` 기록 |
| 3 | **`composePhase4Wheels`** | `dock_core.hpp:169-170` | `dock_core.cpp:99-110` | `phase1_gui.py:1877-1881` | **도킹전용 crab 합성** — 조향 동일·속도차로 yaw. 기존 `QdCrabIK` 로 표현 불가한 바로 그 지점 | 없음 (순수) |
| 3b | **`phase4Steer`** | `dock_core.hpp:152` | `dock_core.cpp:92-97` | `phase1_gui.py:1844-1845` | 크랩 기준각 `as·90°` 에 δ 를 얹어 클램프. **`as·(π/2−δ)`** — 정본 `as·π/2−δ` 와는 우측 접근에서만 갈린다 | 없음 (순수) |
| 3c | **`geomEntryDelta`** | `dock_core.hpp:113` | `dock_core.cpp:73-78` | — (이식본 신설) | **기하 진입** — 경유점을 직선으로 겨냥하는 `atan(cte_x/e_d)`. 이득이 없어 튜닝 대상이 아니고, `cte_x ∝ e_d` 라 경유점에서 수평이 정확히 0 | 없음 (순수) |
| 3c2 | **`geomEntryDeltaBiased`** | `dock_core.hpp:128` | `dock_core.cpp:80-90` | — (이식본 신설) | 기하각에 **과조향** 을 얹는다. 얹는 양은 `min(bias, |δ*|)` 이라 오차가 작으면 함께 작아진다. 실측 폐합률이 이론의 91% 라 순수 기하각은 계통적으로 덜 돈다 — **조기 전환과 짝** 으로만 쓴다 | 없음 (순수) |
| 3d | **`geomEntryTranslateNeed`** | `dock_core.hpp:123` | `dock_core.cpp:80-85` | — (이식본 신설) | 직선 진입 성립 판정 `\|cte_x\| ≤ tan(δmax)·e_d`. 밖이면 **선행 translate 로 줄여야 할 수평량**[m] | 없음 (순수) |
| 3e | **`phase4AxesReady`** | `dock_core.hpp:138` | `dock_core.cpp:87-90` | — (이식본 신설) | 관측 게이트 — **지령이 실제로 소비하는 축만** 요구. 자세축은 heading 이득이 살아 있을 때만 | 없음 (순수) |
| 4 | `phase4Vcap` | `dock_core.hpp:174` | `dock_core.cpp:112-116` | `phase1_gui.py:1812-1814` | 근접구간 속도 상한 하향 | 없음 (순수) |
| 6 | `imuAccumStep` | `dock_core.hpp:190` | `dock_core.cpp:118-130` | `phase1_gui.py:1854-1857` | IMU 표본을 **증분 누적**(`cum += wrapPm180(iy-prev)`). 매 스텝 wrap 이라 ±180 경계를 지나도 끊기지 않는다. 첫 표본은 기준만 잡는다 | `ImuAccum&` 갱신 |
| 7 | `imuRunaway` | `dock_core.hpp:196` | `dock_core.cpp:132-136` | `phase1_gui.py:1859` | Phase 4 하드캡 — `|cum| > cap`. **마커 이탈 전 정지**시키는 최후 방어선(v2 19° 회전 재발방지) | 없음 (순수) |
| 8 | `orbitOvershoot` | `dock_core.hpp:203` | `dock_core.cpp:138-143` | `phase1_gui.py:1272-1274` | 공전 오버슛 — 시작 기준 **단일 차분** `|wrapPm180(now-imu0)| > |dphi|+cap`. 누적이 아닌 이유: 공전 1회는 180° 미만 | 없음 (순수) |
| 5 | `dockLineYawError` | `dock_core.hpp:208` | `dock_core.cpp:145-149` | `phase1_gui.py:1864` | dock 면 법선각(±90 근방) → 제어 오차 e_yaw[°] | 없음 (순수) |
| 6 | `computeOrbitCenter` | `dock_core.hpp:216-217` | `dock_core.cpp:151-160` | `phase1_gui.py:1352-1356` | Phase 3-1 ICR 의 y 좌표 `c1y`. `\|nx\|<nx_min` → `nullopt` | 없음 (순수) |
| 9 | **`returnHomeAbort`** | `dock_core.hpp:289` | `dock_core.cpp:174-194` | `phase1_gui.py:2030-2045` | **원위치 중단 판정** — 순서: 관측낡음 → **marker(유예)** → 라이다(대기/초과) → FOV → timeout. ⚠ `MARKER_WAIT`·`LIDAR_WAIT` 는 중단이 아니라 **steer-hold 대기**다. marker 유예는 **정본 대응 없음**(정본은 1프레임 즉시 중단) — 근거는 `dock_core.hpp` 의 `marker_grace_s` 주석 | 없음 (순수) |
| 10 | **`returnHomeDone`** | `dock_core.hpp:297` | `dock_core.cpp:196-200` | `phase1_gui.py:2052` | **원위치 완료 — 거리 단독.** 함수로 떼어낸 이유가 축 추가 차단이다(`DockCommand.srv:12-13` 사용자 확정) | 없음 (순수) |
| 11 | **`homeErrPxTarget`** | `dock_core.hpp:304` | `dock_core.cpp:202-208` | `phase1_gui.py:2065` | 주입 수평오차[mm] → px 등가. `:2047` 정변환의 **역함수**. `z·fx≈0` 이면 0(무주입) | 없음 (순수) |
| — | ~~`precisionAssist`~~ | — | — | `phase1_gui.py:1724-1725`·`:1826-1827` | **ADR-PRECISION 결재 대기** — 미이식 시 `e_d≈6.7 mm` 에서 정지(`:1825`) | — |

### 보조 (같은 헤더, 정본 유틸 이식)

| 함수 | 선언 | 정의 | 정본 | 주의 |
|---|---|---|---|---|
| `wrapPm180` | `dock_core.hpp:60` | `dock_core.cpp:9-14` | `phase1_gui.py` 동형 | `(-180, 180]` |
| `wrapMod180` | `dock_core.hpp:64` | `dock_core.cpp:16-22` | `phase1_gui.py:265-271` | `(-90, 90]` — **`wrapPm180` 과 절대 혼용 금지**(dock line 180° 모호성 전용) |

### 자료형 (같은 헤더)

| 형 | 위치 | 용도 |
|---|---|---|
| `DockWheelCommand` | `dock_core.hpp:19-26` | wheel-level 출력 `{vf, af, vr, ar}` (ADR-CMD) |
| `PidGains` | `dock_core.hpp:28-34` | `{kp, ki, kd}` 주입 |
| `PidLimits` | `dock_core.hpp:36-42` | `{i_band, i_clamp, lpf_a}` — 축마다 값이 다르다 |
| `PidState` | `dock_core.hpp:44-49` | `{i_term, d_filt}` — 축마다 별도 인스턴스 |
| `PidOutput` | `dock_core.hpp:51-58` | `{u, u_p, u_i, u_d}` — 정본 5-튜플 대체 |
| `HomeAbort` | `dock_core.hpp:241-250` | 원위치 중단 사유 **7종**. ⚠ `MARKER_WAIT`·`LIDAR_WAIT` 는 **중단이 아니다** — steer-hold 정지로 복귀를 기다린다 |
| `HomeAbortInput` | `dock_core.hpp:254-274` | `returnHomeAbort` 입력 **11필드**(marker 유예 2개 추가). **인자 나열 대신 구조체** — 무타입 순서배열(`debt-055`)의 실패 양식을 코어로 복제하지 않는다 |

### 단위 검증 (test/unit — ROS 불요, 코어만 링크)

| 검사기 | 위치 | 대상 | 잡는 결함 |
|---|---|---|---|
| `phase4_steer_check.cpp` | `phase4_steer_check.cpp:44-123` | `phase4Steer` | 우측 접근에서 δ 가 오차를 **키우는** 방향으로 붙는 부호 오류 |
| `phase4_axis_gate_check.cpp` | `phase4_axis_gate_check.cpp:30-64` | `phase4AxesReady` | 게이트가 너무 느슨(잔류값 사용) / 너무 빡빡(쓰지 않는 축에 정지) 양방향 |
| `geom_entry_check.cpp` | `geom_entry_check.cpp:31-135` | `geomEntryDelta` · `geomEntryDeltaBiased` · `geomEntryTranslateNeed` | 아크탄젠트 이탈 · 클램프 누락 · **경유점에서 수평이 0 이 되지 않음**(적분 검증) · 통과 후 역부호 · **과조향의 방향·크기·비례 제한** |
| `return_home_check.cpp` | `return_home_check.cpp:80-215` | `returnHomeDone` · `returnHomeAbort` · `homeErrPxTarget` | 완료 게이트에 축이 끼어듦(거리 단독 파괴) · 경계 부등호 뒤집힘 · **중단 판정 순서 오류**(대기 중 timeout 이 대기를 이김 → 사유가 원인을 못 가리킴) · 역변환 왕복 불일치 · `z·fx≈0` 에서 inf/NaN 유출 · **marker 유예 소멸**(1프레임 즉시 중단으로 회귀) · 유예 경계 부등호 · marker 판정이 라이다보다 뒤로 밀림 |

## 2. 전역변수표

**전역변수 0개.** 정본의 `PHASE4_*` 상수는 전역이지만, 이식본은 **전부 인자 또는 주입 구조체**로 받는다
(계획 §3.5 기하 SSOT — 리터럴 금지, 하단 yaml 참조 강제 `⟦CI:dock-no-drive-constants⟧`).

| 이름 | 형 | 소유 | 비고 |
|---|---|---|---|
| `PidGains{kp,ki,kd}` | struct | 호출자 주입 | 정본은 GUI 스핀박스 주입(12종) |
| `PidLimits{i_band,i_clamp,lpf_a}` | struct | 호출자 주입 | 거리/수평이 값이 다르다(`PHASE4_I_BAND` vs `PHASE4_I_BAND_PX`) |
| `PidState{i_term,d_filt}` | struct | 호출자 소유 | 축마다 **별도 인스턴스** — 공유하면 거리·δ 적분이 섞인다 |
| `DockWheelCommand{vf,af,vr,ar}` | struct | 반환값 | wheel-level 출력(ADR-CMD) |
| `arm_m` | double | 인자 | `PHASE4_YAW_DV_ARM_M` — ⚠ 본 기체 실측 없음(tc 트림 유효값 0.356) |

## 3. 이식하면서 바뀌는 것 (의도적 차이)

| # | 정본 | 이식본 | 사유 |
|---|---|---|---|
| D1 | `e_prev=None` 을 `None` 으로 표현 | `const double*` (nullptr = 첫 cycle) | C++ 에 `None` 이 없다. `NaN` 은 `e*e_prev<0` 비교가 조용히 false 가 되어 **부호교차 리셋이 죽는다** |
| D2 | `dist_pid_step` 이 튜플 5개 반환 | `PidOutput` 구조체 + `PidState&` 갱신 | 반환 튜플을 호출자가 잘못 풀어 상태를 잃는 사고를 구조적으로 차단 |
| D3 | 상수 전역 참조 | 인자 주입 | 계획 §3.5 |
| D4 | `travel` 을 `phase4Delta` 안에서 계산 | 동일(안에서 계산) | `:1837-1838` 그대로. `composePhase4Wheels` 는 **travel 인자를 받지 않는다**(`:1875` 주석) |
| D5 | 수평 지령이 전 구간 PID | 경유점 밖은 `geomEntryDelta`(설정 `entry_geom_enable`, 기본 **off**) | 정본 이득은 시작 조건에서 기하 필요각의 **6.1배**(R=k_p·f_x·e_d/D)를 지령해 δ 가 즉시 포화한다. 포화 구간에서는 이득을 2.5배 올려도 궤적이 변하지 않는 것이 실측(kp 0.008→0.020, 정착 34.1s 동일). off 면 정본 경로 그대로 |
| D6 | 3축이 모두 유효해야 제어 | `phase4AxesReady` — 쓰는 축만 요구 | 무효 축의 잔류값을 쓰지 않는다는 원칙은 유지하되, **지령에 기여하지 않는 축**(heading 이득 0 일 때의 자세축)까지 요구하면 제어가 이유 없이 멈춘다. 검은 도크 배경에서 자세축 유효율 4.2% 실측 |

## 4. 골든 대조 (검증 계약)

정본과 이식본에 **같은 입력**을 먹여 출력을 대조한다. 원본은 파이썬이라 직접 링크할 수 없으므로,
정본 함수만 추출한 얇은 러너로 기준값(JSON)을 만들고 C++ 측이 그것을 읽어 비교한다.

| 함수 | 격자 | 필수 사분면 |
|---|---|---|
| `distPidStep` | `e × e_prev × d_raw × dt` | **부호교차**(`e·e_prev<0`) · 포화 동결(`\|u\|≥cap ∧ e·u>0`) · 적분분리 경계(`\|e\|=i_band`) |
| `phase4Delta` | `err_px × e_d × approach_sign` | `e_d<0`(후퇴, travel=−1) · `approach_sign=−1` · δ 포화 |
| `composePhase4Wheels` | `v_app × steer × w_deg × approach_sign` | `w_deg` 부호 양쪽 · `approach_sign` 양쪽 · `v_app=0` |
| `phase4Vcap` | `v_stage × e_d` | `\|e_d\|` 가 `near_zone` 경계를 **넘는 셀 필수** |
| `dockLineYawError` | `yaw_err_deg` 1축 | `±90` 근방 · `0` 근방 · `±180` 랩 |
| `computeOrbitCenter` | `mx × my × yaw_err_deg` | `\|nx\|<0.05` 실패 반환 · `nx` 부호 양쪽 |

허용오차는 ADR-PARITY 소관. 기본은 **비트 동일이 아니라 `1e-12` 상대오차**로 시작한다
(파이썬 `float` = C++ `double` 이고 연산 순서를 보존하므로 대부분 비트 동일이 나오지만,
`math.hypot`/`atan2` 의 libm 구현 차이를 허용오차로 흡수한다).

### 4.1 골든 신뢰도 2등급 — 섞어 읽지 말 것

| 등급 | 대상 | 방식 | 전사 오류 가능성 |
|---|---|---|---|
| **[A]** | `wrap_pm180` · `wrap_mod180` · `dist_pid_step` | 정본에 `def` 로 존재 → `ast` 로 **원문을 그대로 exec** | **원리적으로 0** |
| **[B]** | `phase4Delta` · `composePhase4Wheels` · `phase4Vcap` · `dockLineYawError` · `computeOrbitCenter` | 정본에서 `do_phase_dock`/`do_phase3` **본문에 인라인**이라 떼어낼 수 없음 → 줄을 옮겨 적음 | **있음** — 이 골든은 "정본과 동일"이 아니라 "정본 줄 인용과 동일" |

[B] 를 [A] 로 올리려면 정본을 리팩터링해야 하는데 정본은 **무수정 보존** 대상이다.
대신 `gen_golden.py --show-source` 가 인용 줄을 원문에서 다시 읽어 출력해 사람이 눈으로 대조한다.
**[B] 항목의 골든 통과는 "이식본이 내 전사와 일치"까지만 담보한다** — 이 한계를 보고서에 반드시 적는다.

### 4.2 골든 하네스 함수표

| 함수 | 위치 | 용도 |
|---|---|---|
| `load_canon` | `gen_golden.py:57-82` | 정본을 `ast` 파싱 → [A] 함수 exec + 모듈 상수 읽기. 상수·함수 누락 시 즉시 종료 |
| `REF_phase4Vcap` | `gen_golden.py:84-90` | [B] 정본 `:1812-1814` 재기술 |
| `REF_dockLineYawError` | `gen_golden.py:92-95` | [B] 정본 `:1864` 재기술 |
| `REF_imuAccumStep` | `gen_golden.py:97-103` | [B] 정본 `:1854-1857` 재기술 — 증분 누적. **입력은 갱신 전 상태**(갱신 후를 넣으면 증분 0 인 퇴화 벡터가 된다 — red 시연으로 발견) |
| `REF_imuRunaway` | `gen_golden.py:105-108` | [B] 정본 `:1859` 재기술 |
| `REF_orbitOvershoot` | `gen_golden.py:110-114` | [B] 정본 `:1272-1274` 재기술 — 시작 기준 단일 차분 |
| `REF_computeOrbitCenter` | `gen_golden.py:116-123` | [B] 정본 `:1352-1356` 재기술 |
| `REF_composePhase4Wheels` | `gen_golden.py:125-133` | [B] 정본 `:1877-1881` 재기술 |
| `REF_phase4Delta` | `gen_golden.py:135-145` | [B] 정본 `:1836-1846` 재기술 |
| `f` | `gen_golden.py:147-150` | 왕복 손실 없는 double 표기(`repr`) |
| `emit` | `gen_golden.py:152-155` | 골든 1행 조립 (`이름 TAB 입력들 TAB \| TAB 출력들`) |
| `build` | `gen_golden.py:157-265` | §4 격자 전개 |
| `main` | `gen_golden.py:266-` | CLI — 골든 생성 / `--show-source` |

전역 상수: `HERE`(`:30`) · `CANON`(`:31-32`, 정본 경로) · `REF_LINES`(`:35-42`, [B] 인용 줄) ·
`VERBATIM`(`:44`, [A] 목록) · `CONSTS`(`:47-50`, 정본에서 읽을 상수명).
**정본 상수를 이 파일에 값으로 적지 않는다** — 이름만 적고 값은 정본에서 읽는다.

### 4.3 골든 대조기 (C++) 함수표

| 함수 | 위치 | 용도 |
|---|---|---|
| `isDelegated` | `golden_check.cpp:30-33` | 코어가 아니라 **다른 하네스에 위임**한 함수(`orbitWheelCmd`·`fwdWheelCmd`) 판별. 조용히 통과시키지 않고 별도 집계 — 위임은 «검증 면제»가 아니라 «검증 주체가 다름» |
| `close` | `golden_check.cpp:44-51` | 상대오차 비교. 기대값 0 근처는 절대오차로 강등. NaN 쌍은 일치 취급 |
| `optArg` | `golden_check.cpp:53-56` | `nan` 센티널 → 정본의 `None`(nullptr) 복원 |
| `run` | `golden_check.cpp:59-119` | 행 이름으로 디스패치해 이식본 출력 생성. **미지의 이름 = 빈 벡터 → 미구현으로 집계** |
| `main` | `golden_check.cpp:123-` | TSV 파싱 · 대조 · 불일치 최대 10건 출력 · 미구현 0 이어야 exit 0 |

전역: `g_tol`(`golden_check.cpp:25`, 기본 `1e-12`, argv[2] 로 상향 가능) ·
`Row`(`golden_check.cpp:35-42`, `{name, in, want, lineno}`).

⚠ `run` 이 이름을 모르면 **조용히 통과시키지 않고 «미구현» 으로 집계**해 exit 1 을 만든다 —
골든에 있는데 코어에 없는 함수(예: `precisionAssist` 를 나중에 격자에 넣었을 때)가
"0 불일치"로 보고되는 것을 막는다.

## 6. 코어 SIL (`test/sil/dock_core_sil.cpp`)

이식한 코어를 **직접 링크**해 Phase 4 를 폐루프로 돌린다. 파이썬으로 다시 짜면 시험 대상이
이식본이 아니라 내 재구현이 되므로 C++ 로 둔다. ROS 미사용.

**상태는 전부 base_link 기준**이다 — 정본 `:152-153`(거리축 = base_link y / 수평축 = base_link x)과
`:20`·`:902-903`(로봇 회전 시 도크 좌표가 `R(−δ)`)을 따른다. 이 규약을 어기면 SIL 이 낙관적이 된다.

| 심볼 | 위치 | 용도 |
|---|---|---|
| `Plant` | `dock_core_sil.cpp:27-82` | 평면 기구학 플랜트. 상태 `{mx, my, yaw_deg}` = 도크의 base_link 좌표 + 도크면 법선각. 파라미터 `{arm, fx}` |
| `Plant::step` | `dock_core_sil.cpp:44-67` | ① 병진(`mx−vx·dt`, `my−vy·dt`) ② **회전 `R(−dθ)`** — `w_rad=(vf−vr)/(2·arm)` 은 `composePhase4Wheels` 의 역 ③ `yaw_deg −= dθ` |
| `Plant::errPx` | `dock_core_sil.cpp:72` | 카메라 관측 `err_px = mx·fx/z_cam` — 정본 `:1727` 의 역, **부호 조작 없음**. `z_cam ≈ \|my\|`(측면 카메라) |
| `Plant::range` | `dock_core_sil.cpp:75` | 라이다 거리 = `as·my` — 접근측 부호를 걷어낸 양의 거리 |
| `Consts` | `dock_core_sil.cpp:88-121` | 정본 `PHASE4_*` 의 **SIL 전용 사본**(코어에는 리터럴을 두지 않으므로 여기서 주입). **전 필드에 정본 `:줄` 주석 필수** — 게인 23종(수평·자세 PID, 속도 상한, 재접근 3종, 완료 게이트, **`converge_n` 3사이클**) |
| `Result` | `dock_core_sil.cpp:113-121` | `{ticks, d, x_mm, e_yaw, min_abs_v, converged, stop}` |
| `runPhase4` | `dock_core_sil.cpp:134-263` | 폐루프 1회. `phase4Vcap → distPidStep → phase4Delta → 조향합성 → dockLineYawError → composePhase4Wheels` + **재접근 상태기**(`retreating`·`reapproach`, 정본 `:220-223`) + **3사이클 연속 완료 게이트**(`conv` ≥ `converge_n`, 정본 `:176`) |
| `sweep` | `dock_core_sil.cpp:268-316` | **진입 조건 지도** — 거리 6 × 자세 7 × 수평 81(−200~+200 mm, 5 mm) = 3,402 회 실행 후 각 (거리, 자세) 칸의 **성공 수평오차 구간**을 출력 |
| `main` | `dock_core_sil.cpp:296-` | `--sweep` → `sweep()`, `-v` → 상세 추적, 기본 → 시나리오 7종. **판정하지 않는다**(합격선 = M1 수치 6종 결재 소관) |

### 이 SIL 이 담보하지 않는 것 (범위 선언)

- **FSM·진입 게이트·가드 없음** → M3
- **정밀도킹 없음** → `precisionAssist` 는 ADR-PRECISION 결재 대기. 마찰 모형이 없어 SIL 로는 판정 불가
- **재접근은 포함한다**(정본 `:220-223`) — 이것이 없으면 정본 거동을 재현하지 못한다
- **관측 노이즈·지연·라이다 stale 없음** → M4 `dock_sim`
- 따라서 결과는 *"도킹이 된다"* 가 아니라 **"3축 제어가 수렴한다"** 까지만 말한다.

## 8. IK 어댑터 (`dock_ik.hpp` / `dock_ik.cpp`) — ADR-IK 조건 구현

`QdDualSteerIK` 를 **도킹 계약(steer-hold)** 에 맞게 감싼다. 유일한 차이는
`qd_inverse_kinematics.cpp:42-49` 의 `spd < 1e-6 → steer_rad = 0` 조기반환을 덮는 것이다
(§7.1 실측: 그 구간에서만 56건 차이, 그 밖은 비트 동일).

| 심볼 | 선언 | 정의 | 용도 |
|---|---|---|---|
| `DockGeometry` | `dock_ik.hpp:22-30` | — | `{w1_x, w1_y, w2_x, w2_y, wheel_radius_m, gear_walk}`. **리터럴 금지**라 호출자가 `robot_geometry_qd.yaml` 에서 읽어 주입(계획 §3.5) |
| `SteerHoldIk` | `dock_ik.hpp:32-64` | — | **상태를 갖는 어댑터** — 직전 조향을 기억한다 |
| `SteerHoldIk::SteerHoldIk` | `dock_ik.hpp:39` | `dock_ik.cpp:8-14` | `hold_below` 는 IK 임계와 같은 값을 **주입**한다(리터럴로 박으면 상류 변경 시 어긋난다) |
| `SteerHoldIk::compute` | `dock_ik.hpp:49` | `dock_ik.cpp:30-56` | 공통 경로. **바퀴별로** 임계 판정 — 공전 중 ICR 에 가까운 한쪽만 임계 아래로 떨어지는 경우가 실재한다 |
| `SteerHoldIk::orbit` | `dock_ik.hpp:43` | `dock_ik.cpp:58-62` | 정본 `orbit_wheel_cmd`(`phase1_gui.py:274-296`) 대응. `vx = cy·ω, vy = −cx·ω` |
| `SteerHoldIk::forward` | `dock_ik.hpp:46` | `dock_ik.cpp:64-67` | 정본 `fwd_wheel_cmd`(`phase1_gui.py:298-301`) 대응 |
| `SteerHoldIk::resetHold` | `dock_ik.hpp:52` | `dock_ik.cpp:16-21` | **페이즈 진입 1회** — 이전 페이즈 조향이 새 페이즈로 새지 않게 |
| `SteerHoldIk::lastSteer` | `dock_ik.hpp:55` | `dock_ik.cpp:23-28` | 유지 중인 조향 조회(진단용) |

⚠ **ADR-IK 권고 변경 제안** — 계획 §3.4 는 *소스 편입 + md5 동결*(안1′)을 권고했다.
그 근거는 *"`find_package` 성공이 ROS source 를 요구하는데 M2 는 standalone 빌드를 요구"* 였다.
그러나 **standalone 요구는 코어(`dock_core.cpp`)에만 걸린다** — `orbit`/`fwd` 는 Phase 3 용이라
Phase 4 코어가 쓰지 않는다. 그리고 `trnav_qd_kinematics` 는 `package.xml` 이
*"Pure math (stdlib only, no ROS)"* 라 선언하고 `ament_export_targets` 로 정상 export 한다.
⇒ **정상 `find_package` + 링크로 충분**하며 소스 복제·md5 동결이 불필요하다.
소스 편입은 같은 목적코드가 워크스페이스에 2벌 생기는 ODR 위험까지 안는다.

## 7. ADR-IK 등가 검증 (`test/golden/ik_parity_check.cpp`)

「소스 편입」을 결정하기 **전에** 등가를 재도출한다. 계획서의 *"200k 샘플 max diff 0.0"* 은
남이 쓴 수치(내가 이전에 쓴 것 포함)라 1차 근거가 아니다.

| 심볼 | 위치 | 용도 |
|---|---|---|
| 기하 상수 | `ik_parity_check.cpp:26-29` | `W1(0.330, 0.135)`·`W2(−0.330, −0.135)` = 정본 `:88-89` `ORBIT_W1/W2`. `WHEEL_RADIUS`·`GEAR_WALK` 는 생성자 요구만 채우며 steer/speed 에 영향 없음(`drive_rpm` 전용) |
| `wheelToCanon` | `ik_parity_check.cpp:34-38` | `WheelOutput{speed≥0, direction}` → 정본의 **부호 포함 속도** `v = speed × direction` |
| `close` | `ik_parity_check.cpp:40-45` | 기본 허용오차 **0**(비트 동일 요구), argv[2] 로 완화 가능 |
| `main` | `ik_parity_check.cpp:49-` | 골든 TSV 의 `orbitWheelCmd`·`fwdWheelCmd` 행을 실제 `QdDualSteerIK` 로 재계산해 대조 |

⚠ **`computeWheel` 은 private** 이다 — 공개 표면은 `compute(VelocityCommand)`·`computeSpin` 뿐이다.
이 하네스는 `compute({cy·ω, −cx·ω, ω})` 로 호출하며, 바퀴별 분해(`vx_i = vx − ω·y_i`)는
`compute()` 내부(`qd_inverse_kinematics.cpp:23-28`)가 정본 `:283-284` 와 동일하게 수행한다.
**ADR-IK 의 편입 대상은 그 공개 표면**이지 `computeWheel` 이 아니다.

### 7.1 검증 결과 (2026-08-12 실측)

| 항목 | 값 |
|---|---|
| 대조 벡터 | **orbit 175 · fwd 13 = 188** |
| 허용오차 | **0 (비트 동일 요구)** |
| **임계 밖 불일치** | **0 건** ✅ 등가 확인 |
| `\|v\|<1e-6` 차이 | **56 건** — 아래 참조 |

계획서의 *"200k 샘플 max diff 0.0"* 주장을 **직접 재도출해 확인**했다(샘플 수는 다르지만
±90 flip 분기 양쪽·영속도 경계를 포함한 격자에서 비트 동일).

**불일치를 두 부류로 분리해 센다** — 이것이 이 하네스의 핵심이다:

| 부류 | 의미 |
|---|---|
| `임계 밖 불일치` | 진짜 등가 위반. **0 이어야 편입 가능** |
| `\|v\|<1e-6 차이` | `qd_inverse_kinematics.cpp:42-49` 의 `spd < 1e-6 → steer_rad = 0` 조기반환. **정본에는 이 임계가 없다** — 속도가 0 을 관통하는 순간(재접근 반전·완료 직전) 조향이 0° 로 복귀해 `:1749-1751` 이 금지한 밀림을 일으킨다. **래퍼가 「임계 미만도 직전 조향 유지」로 덮어야 한다**(ADR-IK 조건) |

골든 측 `orbit_wheel_cmd`·`fwd_wheel_cmd` 는 정본에 `def` 로 존재하므로 **[A] 등급**
(`ast` 로 원문 exec) — 전사 오류가 원리적으로 불가능하다.

## 5. 강제 태그

| 태그 | 검사 | 상태 |
|---|---|---|
| `⟦CI:dock-no-ros⟧` | 코어가 `rclcpp`·`ros` 심볼을 참조하지 않음 | 이 배치에서 신설 |
| `⟦CI:dock-port-only⟧` | 코어가 정본에 없는 로직을 넣지 않음(§3 표 밖 차이 0) | 이 배치에서 신설 |
| `⟦CI:dock-no-exact-ik⟧` | Phase 4 합성을 `QdDualSteerIK` 로 치환하지 않음 | ADR-IK 단계 |
| `⟦CI:dock-no-drive-constants⟧` | 기하·구동 상수 리터럴 금지 | ADR-GEOM 단계 |

⚠ 저장소에 pre-commit·CI 배선이 없어(`debt-036`) 위 4종은 현재 **`⟦권고⟧` 등급**이다 —
스크립트는 만들되 "통과 = 강제됨"으로 읽지 않는다.

### 5.1 검사 스크립트 (셸) 구성표

셸 스크립트라 함수 단위가 아니라 **단계(step) 단위**로 등재한다.

| 파일 | 단계 | 위치 | 검사 내용 |
|---|---|---|---|
| `dock-no-ros.sh` | 변수 초기화 | `dock-no-ros.sh:11-12` | `CORE=dock_control`, `rc=0` |
| | ① ROS 심볼 grep | `dock-no-ros.sh:14-22` (`HITS` `:15`) | `rclcpp\|rclpy\|rmw_\|ament_\|ros::\|rosidl` + ROS 메시지 include |
| | ② ROS 미source 단독 빌드 | `dock-no-ros.sh:23-35` (`OUT` `:24`) | `env -i` 로 ROS 환경 제거 후 `g++ -Werror` 컴파일 — **"우연히 source 돼 있어서 됐다" 배제** |
| `dock-port-only.sh` | 변수 초기화 | `dock-port-only.sh:13-16` | `CORE`·`TBL`·`GOLD`·`rc` |
| | 공개 함수 추출 | `dock-port-only.sh:19-21` (`EXPORTED`) | 헤더 선언에서 함수명 수집 |
| | ① 함수표 등재+앵커 | `dock-port-only.sh:23-30` | 각 함수가 표에 있고 `phase1_gui.py:N` 앵커 보유 — **앵커 없는 새 함수 차단** |
| | ② 골든 커버리지 | `dock-port-only.sh:32-45` | 각 함수가 골든에 ≥1행 — **검증 안 되는 함수 차단** |
| | ③ 골든 대조 | `dock-port-only.sh:46-54` (`BIN` `:47`) | 0 불일치 + 미구현 0 |

⚠ `dock-port-only.sh` 는 **완전 판정이 아니다.** "정본과 의미가 같다"는 자연어 대조라 기계가 못 센다.
이 스크립트가 세는 것은 «앵커 없는 함수 추가»·«골든 미커버 함수»·«대조 불일치» 3가지뿐이며,
통과는 그 3가지가 없다는 뜻이지 이식이 옳다는 뜻이 아니다.
