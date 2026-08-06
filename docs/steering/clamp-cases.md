# 조향각 클램프 — 케이스별 정리

> 조향 한계가 **8개 계층**에 흩어져 있어 「어느 기동에서 어느 클램프가 무는가」를 눈으로
> 쫓기 어렵다. 본 문서는 그 지도이며, 숫자는 전부
> `Tools/motion_chain_check/steer_clamp_cases.py` 가 **설정·소스에서 재도출**한다.
> 값이 바뀌면 문서가 아니라 그 도구 출력이 정본이다.

```bash
python3 Tools/motion_chain_check/steer_clamp_cases.py            # 케이스 표
python3 Tools/motion_chain_check/steer_clamp_cases.py --selftest  # 계산 규칙 회귀
```

## 1. 계층 지도 (상류 → 하류)

| # | 계층 | 값 | 어디에 | 성격 |
| --- | --- | --- | --- | --- |
| ① | IK 정규화 | **±90°** | `qd_inverse_kinematics.cpp` `normalizeAngle` 의 `M_PI/2` | **코드 고정** — config 로 안 바뀐다 |
| ② | 크랩 wrap 임계 | **±115°** | `qd_crab_inverse_kinematics.cpp` `WRAP_MARGIN = 25°` | 경계 chattering 회피 히스테리시스 |
| ②' | 크랩 cruise | **initial ± 25°** | 같은 파일 `CLAMP_MARGIN` | Phase 0 자세 기준 보정 폭 |
| ③ | 액션 δ 한계 | translate·mpc·crab **45°** / yaw_control **25°** | `<action>_params.yaml` | bicycle 경로의 조향 포화 |
| ④ | **translator** | 클램프 **없음**. `offset −1.676°` 를 빼고 `×57,344 c/°`, `×dir(−1)` | `amr_motor_cmd_translator_qd.yaml` | 여기서 **비대칭**이 생긴다 |
| ⑤ | can_relay | 체인 **±115°** / 벤치 **±90°** | `machine/foil_a082.yaml` · `can_relay.yaml` | counts(홈 기준)로 판정 |
| ⑥ | 코드 기본 | 90° | `safety.STEER_LIMIT_DEG` | config 미설정 시의 보수적 값 |
| ⑦ | GUI | 90° | `ui/app.py` 슬라이더 · `ui/backend_direct.py` | **config 를 안 읽는 자체 상수** |
| ⑧ | 기구 −리밋 | **±137.1°** | 호밍이 매번 실측 (`SEER_HOME_ZERO / counts_per_deg`) | 물리 한계 |

**±90° 는 하드웨어 한계가 아니라 유일해(canonical) 구속**이다 — 등가해
`(θ,+v) ≡ (θ∓180°,−v)` 를 반원으로 묶어 지령을 하나로 결정한다
(ADR `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md`).

## 2. 반드시 알아야 할 것 — 영점 오프셋이 클램프를 비대칭으로 만든다

translator 는 `raw = (θ − offset)` 을 counts 로 만든다(`offset = −1.676°`). 즉

```
θ = +89.87°  →  raw = 91.54°     (1.676° 커진다)
θ = −89.87°  →  raw = 88.19°     (1.676° 작아진다)
```

can_relay 는 **counts 로** 판정하므로 **같은 |θ| 라도 부호에 따라 잘리는지가 갈린다.**
비대칭 폭은 `2 × |offset| = 3.35°` 다.

> 이 때문에 「IK 가 ±90° 안에 묶으니 90° 클램프면 충분하다」는 추론이 **틀린다.**
> 실제로 2026-08-06 전 체인 SIL 에서 관측된 조향 지령이 `−91.54°`(counts 상)였다.

## 3. 케이스별 표 (현행 체인 클램프 ±115°)

| 기동 | 계층 | IK \|θ\| | raw(+θ) | raw(−θ) | 판정 |
| --- | --- | --- | --- | --- | --- |
| translate_forward / reverse | bicycle | 45.00° | 46.68° | 43.32° | 통과 |
| mpc / mpc_reverse | bicycle | 45.00° | 46.68° | 43.32° | 통과 |
| yaw_control / _reverse | bicycle | 25.00° | 26.68° | 23.32° | 통과 |
| **spin** | free IK | 89.87° | **91.54°** | 88.19° | 통과 |
| **turn** (R→0, 미세보정) | free IK | 89.87° | **91.54°** | 88.19° | 통과 |
| **crab Phase 0** | 크랩 wrap | 115.00° | **116.68°** | 113.32° | ⚠ **+쪽 1.68° 잘림** |
| **crab cruise** | 크랩 cruise | 115.00° | **116.68°** | 113.32° | ⚠ **+쪽 1.68° 잘림** |

`spin`·`turn` 의 89.87° 는 **기하가 정한다** — inline 2WS 는 `y ≈ 0` 이라 제자리 회전이
구조상 ±90° 를 요구한다(`atan2(x_i, −y_i)`).

### 종전 ±90° 였다면 (2026-08-05 이전)

| 기동 | +θ | −θ |
| --- | --- | --- |
| spin · turn | **1.54° 잘림** | 0 |
| crab Phase 0 · cruise | **26.68° 잘림** | 23.32° 잘림 |

크랩만이 아니라 **spin·turn 도 잘렸다.** 「90° 를 넘겨 요구하는 것은 crab 뿐」이라는
종전 결론은 **IK 출력 각 기준**이었고, 영점 오프셋을 거친 raw 기준으로는 다르다.

## 4. 미해결 — 현행 115° 로도 크랩 최대 자세에서 1.68° 잘린다

클램프를 115° 로 연 근거는 「크랩의 보정 여유(`WRAP_MARGIN 25°`)를 자르지 않는다」였다.
그런데 그 여유를 **끝까지 쓰는 자세**(θ = +115°)는 오프셋을 거치면 raw 116.68° 가 되어
**여전히 1.68° 잘린다.**

일관되게 하려면

```
체인 클램프 ≥ (90° + WRAP_MARGIN) + |steer_offset| = 115 + 1.676 = 116.68  →  117°
```

기구 −리밋 137.1° 대비 여유는 **20.1°** 로 충분하다. **미결 — 사용자 판단 대기.**

⚠ 이 잘림은 **한쪽 방향에서만** 일어난다(+θ). 크랩 보정이 방향에 따라 비대칭이 된다는 뜻이다.

## 5. 경로별 요약 — 누가 무엇을 자르나

| 지령 경로 | 적용 클램프 | 비고 |
| --- | --- | --- |
| 모션 체인 `/motor/low_cmd` | **체인 ±115°** | 액션 → mux → translator → can_relay |
| 벤치 `~/steer_deg` · `~/steer_axis_deg` | **벤치 ±90°** | 사람이 손으로 넣는 값 — 넓히지 않는다 |
| GUI 직접 백엔드 | **90°(자체 상수)** | `config` 를 읽지 않는다 — 바꾸려면 코드 수정 |
| 호밍 `~/home` | 클램프 무관 | 펌웨어 시퀀서가 −리밋까지 구동 |

can_relay 가 지령 출처를 모르므로(raw counts 만 받는다) 「크랩일 때만 열기」는 판정 불가다.
그래서 **경로**로 나눈다.

## 6. 잘릴 때 무슨 일이 일어나는가

거부가 아니라 **클램프 후 그대로 지령된다**(`backend.py:392` → `:409` → 재송신 루프).
경고 로그(`target_pos … 클램프`)는 남지만 바퀴는 잘린 각으로 간다.

잘린 각으로 가면 상위가 의도한 운동과 달라진다. 크랩에서는 **CTE 보정 여유**를 잃고,
그 여유가 모자라면 제어기가 대안 해(등가해)로 넘어가려 하는데 그것은 **구동 부호 반전**이다 —
순항 0.2 m/s·50 Hz 에서 0.40 m/s 계단 = 20 m/s²(2.0 g). 3톤 차체가 따를 수 없다.

## 7. 근거

| 주장 | 근거 |
| --- | --- |
| ±90° = 유일해 구속 | `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md` · `foil_a082.yaml:162-166` |
| 크랩 마진은 chattering 회피 | `qd_crab_inverse_kinematics.cpp:20-35` (「motor saturate」 전제 명시) |
| 기구 −리밋 137° | 호밍 Home 1(−리밋 탐색) · `safety_seer_gate.h:212-213` `SEER_HOME_ZERO` |
| 부호 반전 대가 2.0 g | `Tools/motion_chain_check/simulate_steer_clamp.py` ⑥ |
| raw 91.54° 실측 | 2026-08-06 전 체인 SIL, `/motor/low_cmd` 149 메시지 (예측과 1 count 차) |
| 크랩 yaw 권한 1/13 | `Tools/motion_chain_check/measure_crab_yaw_authority.py` |

⚠ **실기 검증 0건** — 위 전부 정적 분석·계산·SIL(Software In the Loop)이다.
