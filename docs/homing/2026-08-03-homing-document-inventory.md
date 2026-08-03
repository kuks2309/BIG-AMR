# 호밍 관련 문서 전수 목록 · 정확도 판정 (2026-08-03)

> ## ❌ 통합 재정정 2026-08-03 17:30 — 아래 15:40 블록의 수치·판정을 **원자료 재계산**으로 정정한다
>
> 원문은 삭제하지 않는다. 재검증: `python3 Tools/docking_field_kit/verify_homing_claims.py --docs`
> (`Log/` 원자료 재계산 — 문서를 근거로 문서를 고치지 않는다)
>
> - **E1** 「13회 연속 성공」 → **12회**. 2026-08-03 은 **시도 13 / 성공 12 / 실패 1**(09:58 `ERR_TIMEOUT`).
>   15:33 실행의 `baseline` 은 호밍이 아니라 **레지스터 스냅샷**이다 — 회차로 세지 말 것.
>   ⚠ **「10회 연속 10/10」 자체는 유효**하다.
> - **E2** 「`0x6064`=0 은 1회 관측·재현 안 됨」 → **[거짓] 재현된다.** `0x6041` bit15=1 인 채로 0 이 나온
>   캡처가 **6개**다. ⚠ **인과는 양쪽 미판정** — 0 이 관측된 직후 호밍이 성공한 회차가 있으므로
>   「0 이면 호밍 실패」도 성립하지 않는다. **「호밍 중(bit15=0)의 0」은 별개의 유효 관측**이다.
> - **E3** 「WAIT 31.7 s」 → WAIT(state 4) **체류 31.30 s**. 31.7 s 는 개시~RESTORE **절대시각**.
> - **E4** 「35.0 s」 → 15:33 10회 **평균 35.07 · 중앙 35.05**(34.99~35.16, 폭 0.17).
> - **E5** 「counts/° = 57,344」 → node3 **57,344.0** / node4 **57,344.3**. 「기울기 1.000000」은 node3 한정.
> - **E6** 「σ≈3 counts」는 **모표준편차** 기준 — node3 **2.80** / node4 **3.21**(표본 2.95 / 3.38).
> - **E7** 「결함이 아니라 **설계 동작**」 → **과잉 확정.** 실측이 보증하는 것은 **재현되는 정착 동작**까지이며
>   펌웨어 상수의 **적정성은 별건**이다 — `debt-016` 이 같은 편차를 「영구 미검출 오프셋」으로 등록 중이라 충돌한다.
> - **E8** 조향 0° `[7871815, 7840086]` — **값은 정본 유지**, 근거는 **공학적 채택값**(역산식이 항등식).
>   「실측 확정」 표현 금지.
> - **E9** `seer_home_cancel_frames()` = **`safety_seer_gate.h:312-316`**(`:307-311` 은 `seer_home_digital_in()`).
> - **E10 ★** 「**물리 직진 앵커 부재**」·「**물리 직진 미확인**」 → **거짓.** 앵커는 **실재한다** —
>   Seer 1005/1040 은 EasyDRIVE `steerOffset` 으로 **교정된** 조향각이고, 사용자가 바퀴 직진 상태에서
>   Seer 앞바퀴 2축 **0° 를 육안 확인**했다(can_relay GUI 표시로도 동일). 부족한 것은 **앵커가 아니라
>   정밀도**(육안 ≈**±1° = ±57,344 counts**)다 — 다툰 193 c(0.0034°)의 약 **297배**라 counts 소수 자리를
>   분해하지 못한다. ⇒ 「非-Seer 계측 필요」는 **「counts 소수 자리까지 판정하려면」** 조건부로만 참이다.
>   ⚠ 단 **(a) 역산식이 항등식이라 육안 확인이 counts 값 결정에 기여하지 않는다**는 판정은 **유지**된다 —
>   무효인 것은 (a) 뿐이고, **(b) 「Seer 0° = 물리 직진」은 성립**한다. 이 둘을 뭉개지 말 것.


> **목적**: "호밍과 관련된 잘못된 문서로 계속 엉터리 코드를 생성한다"(사용자 지시 2026-08-03 08:02)는
> 문제에 대해, 저장소 내 **호밍을 서술하는 모든 문서와 소스 주석**을 전수 열거하고 각각을
> 실측 확정 사실(§0 기준선)과 대조해 판정한다.
>
> **조사 방법**: 20인 병렬 감사(에이전트 20개). 각 담당이 배정 문서를 전문 Read 하고,
> 모든 호밍 주장을 실제 코드·설정·캡처 로그와 `파일:줄` 단위로 대조했다.
>
> **탐색 범위**: `homing|호밍|원점 복귀|resetByDriver|0x60FB|0x6098|STEER_HOME|home_offset|homed|0x6041|bit15`
> 로 저장소 전수 grep → **문서 72개 파일(이중기록 8쌍 병합 시 64건)** + **소스 37개 파일**.

---

## §0 판정 기준선 — 실측 확정 사실 10항

> ❌ **재정정 2026-08-03 17:00 — 이 기준선 표에 오류 2건(E5·E9)이 있다. 아래 §0-★ 가 우선한다.**
> 원문은 이력으로 그대로 두고 해당 행 아래에 `❌ 재정정 2026-08-03 17:00:` 표시를 인접 배치했다.
> 정본은 `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0-0**(같은 시각 재정정).

### §0-★ ❌ 재정정 2026-08-03 17:00 — 15:40 기준선에서 퍼진 오류 (원자료 재계산)

아래는 전부 `Log/**` 원자료·소스 파일을 **직접 파싱/재계산**한 값이다(문서 근거 아님).
**이 문서에 실제로 들어 있는 오류는 E5·E9 이며, 나머지는 인용 시 오염 방지용으로 함께 적는다.**

| # | 15:40 판 (틀림) | ❌ 재정정 17:00 | 이 문서 내 위치 |
|---|---|---|---|
| **E1** | 「12회 연속 성공」 | **12회 연속.** 오늘 시도 **13** / 성공 **12** / 실패 **1**(09:58 `ERR_TIMEOUT`). 「15:33 기준선」은 호밍이 아니라 **레지스터 스냅샷**(`orin_home_experiment.py:390`, `snapshot()` `:259-275` 는 판독만). **「10회 연속 10/10」 자체는 유효** | (본 문서에 없음) |
| **E2** | 「`0x6064`=0 은 09:58 1회·재현 안 됨」 | **재현된다** — 09:19 `home_experiment_260803_091956.jsonl` node3 **50/50**, 09:58 `…_095815.jsonl` **12,220/12,220**, 10:08 `seer_homing_260803_100813.jsonl` **10,327/10,327**(`0x6041`=37968=`0x9450` bit15=1 전량). 11:38 리부팅 후 14:43 `homing_edge_260803_144305_can.jsonl` 에도 node3 **2/74**. **인과는 양쪽 다 미판정** | 기준선 #3 과 인접(아래 주 참조) |
| **E3** | 「WAIT 31.7 s」 | **WAIT(state 4) 체류 = 평균 31.30 s**(31.21~31.38). **31.687 s 는 개시 t=0 → state 8 관측까지의 절대 시각** | 기준선 #3 「0 고정(≈31 s)」 |
| **E4** | 「35.0 s」 | **평균 35.07 s · 중앙 35.05 s**(범위 34.99~35.16, 폭 0.17) | (본 문서에 없음) |
| **E5** | 「57,344 counts/°」 단일값 | **node3 57,344.00 / node4 57,344.28**(`Log/steer_two_phase_260803_131305.jsonl` A국면 −5~+5° 5점 최소제곱). 설정값 `steer_counts_per_deg: 57344.0` 은 유효 | **기준선 #6** |
| **E6** | 「σ 2.8 / 3.2」 | **모표준편차(population) 기준 2.80 / 3.21**. 표본표준편차는 **2.95 / 3.38** | (본 문서에 없음) |
| **E7** | 「이 편차는 결함이 아니라 설계 동작이다」 | **과잉 확정** — 실측 보증은 「축이 `SEER_HOME_ZERO_N3/N4`(`safety_seer_gate.h:212-213`)에 **1~3 c 로 재현성 있게 정착**」까지. **상수 적정성은 실측 밖**(별건 · **debt-016 과 충돌**) | (본 문서에 없음 — 기준선 #6 은 「정착값」 라벨만 씀) |
| **E8** | 조향 0° 근거 = 「1040 역산 2회 재현 · Seer 가 실시간 `0x607A` 로 지령」 | **값 `[7871815, 7840086]` 은 유지**하되 근거는 **「공학적 채택값(Seer 좌표계 정합)」**. `Log/homing_capture_220350.jsonl` 전수에서 node3 `0x607A`=7,871,815 는 **145 프레임(2.24 %)**, **7,882,020 이 6,319 프레임(97.76 %)**. **「실측 확정」 표현 금지** | 기준선 #6 값 인용 |
| **E9** | `seer_home_cancel_frames()` = `safety_seer_gate.h:307-311` | **`:312-316`.** `:307-311` 은 `seer_home_digital_in()`(파일 직접 확인) | **기준선 #9** |

**E9 추가 확인(줄번호 — 실제 파일 대조)**: 기준선 #6 이 값 정본으로 인용한
`src/Comm/CAN/can_relay/config/machine/foil_a082.yaml:126` 는 **현재 주석 줄이다.**
`steer_home_counts` 실제 위치는 **`:134`**이고 값은 **`[7871815, 7840086]`**,
`steer_counts_per_deg: 57344.0` 은 **`:20`** 이다. (§7 값 대조표 `:171` 의 같은 인용도 같은 이유로 낡았다.)

이 10항과 어긋나는 서술이 아래 표의 "오류"다.

| # | 확정 사실 | 1차 근거 |
|---|---|---|
| 1 | homing method 는 **전 노드 `0x6098` = 1**(Home 1, 음의 리밋 트리거). 실기 판독. | `Tools/docking_field_kit/orin_read_homing_params.py:5-7,15-17` · Handbook V7.0 §4.6 p.116 |
| 2 | **Seer 는 `0x6098` 에 쓰지 않는다** — 253,510 프레임 전수 write 0건. 드라이브 저장값 사용. | `Log/homing_capture_220350.jsonl` 전수 파싱(2회 독립 재현) |
| 3 | 개시 = `0x6040=0x86` → `0x6099=2500` → **`0x60FB` sub4 = 1(RstStart)**. 완료 = **`0x6041` bit15 0→1**. 호밍 중 `0x6064` 는 **0 고정(≈31 s)**. | 같은 캡처 · Handbook §6.9 p.171 |
| 4 | **리밋 스위치 실재** (`0x6000` **sub1** bit3 = −Limit). `zeroDI/upLimitDI/downLimitDI = -1` 은 스위치 부재가 아니라 **서보 드라이브 DI 직결**(`resetMode = resetByDriver`). | 캡처 t=47.025 bit3 0→1 · Handbook Appendix I p.197 |
| 5 | **"Home 36/37 기계 하드스톱" 가설은 틀렸다** — 접촉 시 전류가 상승이 아니라 감소. **재제기 금지**. | 캡처 전류 −113→−69 |
| 6 | **★ 2026-08-02 종결**: 조향 홈(0°) = **`[7871810, 7839894]`**. `7882020 / 7859062` 는 **홈이 아니라 「호밍 후 정착값」**으로 0°에서 **+0.178° / +0.331°** 벗어남. **이 둘을 모두 "홈"이라 부른 것이 4주 재실험 반복의 원인.** 57,344 counts/°. | `docs/verified_facts/2026-08-02-steer-home-closed.md` · 값 정본 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml:126` |
| 7 | `0x6098=35`(현위치 재영점)는 **RstMode 를 0 으로 리셋**해 Seer 주도 호밍을 죽인다. **2026-08-01 실기 기각**(재영점 후 제어권 반환 시 Seer 가 130.55° 오차로 3톤 차체를 4.9°/s 능동 구동). 현재 `homing_method: "firmware"`. | `docs/adr/2026-08-01-can-relay-home-calibration-method35.md` · `foil_a082.yaml:36-46` |
| 8 | **구동축(node 1·2)은 호밍하지 않는다.** 조향축(node 3·4)만. | 캡처 · `safety_seer_gate.h:203-205` |
| 9 | **조향 호밍은 취소 가능하다** — `0x60FB:04=0`. "호밍은 멈출 수 없다"는 **오류**. | `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:307-311` `seer_home_cancel_frames()` · USB `0xea` wValue=0 (`usb_comms.h:411-414`) · `link.py:213-218` · `driver_node.py:194` `~/home_cancel` |
| 10 | 호밍 속도 `0x6099` 는 **거부**(클램프 아님) 방식으로 100~3000 범위 강제. | `safety_seer_gate.h:206-208,338-340` · `link.py:75,478-481` |

> ❌ **재정정 2026-08-03 17:00 — 위 기준선 표의 행별 정정**(원문 유지, 인용 시 아래를 함께 읽을 것):
> - **기준선 #3** 「호밍 중 `0x6064` 는 0 고정(**≈31 s**)」 — **E3**: 15:33 10회 실측에서 **WAIT(state 4) 체류는
>   평균 31.30 s**(31.21~31.38)이고, **31.687 s 는 개시 t=0 부터 state 8 관측까지의 절대 시각**이다. 「≈31 s」 자체는 맞다.
>   덧붙여 **E2**: `0x6064`=0 은 **호밍 중에만 나오는 것이 아니다** — 09:19·09:58·10:08 캡처는 **정지 상태에서
>   node3/node4 전량(50/50 · 12,220/12,220 · 10,327/10,327)이 0** 이었다. ⇒ **`0x6064`=0 을 「호밍 중」의 증거로 쓰지 말 것.**
> - **기준선 #6** — **E5**: 「57,344 counts/°」는 **node4 가 누락**됐다 → **node3 57,344.00 / node4 57,344.28**.
>   **E8**: 조향 0° 정본은 현재 **`[7871815, 7840086]`**(`foil_a082.yaml:134`)이고 여기 적힌 `[7871810, 7839894]` 은
>   2026-08-03 에 **raw 판독값이었다고 재정정**됐다. 그 값의 근거는 **「공학적 채택값(Seer 좌표계 정합)」**이며
>   **「실측 확정」이 아니다**(→ §0-★ E8). 인용 줄번호 `:126` 도 낡았다(→ §0-★ E9 추가 확인).
> - **기준선 #9** — **E9**: `seer_home_cancel_frames()` 는 **`safety_seer_gate.h:312-316`** 이다.
>   여기 적힌 **`:307-311` 은 `seer_home_digital_in()`**(파일 직접 확인). **「취소 가능하다」는 판정 자체는 유효**하다.

### §0-1 기준선 자체에 남은 미확정 (감사 중 발견)

- **기준선#1 의 raw 근거 파일이 저장소에 없다.** `0x6098=1` 은 실기 직접 read 결과인데, 그 판독 출력이 어떤 파일에도 저장돼 있지 않다(`orin_read_homing_params.py` 는 stdout 전용). 캡처 로그에는 `0x6098` 프레임이 0건이므로 캡처는 이를 뒷받침하지 못한다(`docs/verified_facts/2026-07-27.md:568-577` 이 이 구분을 정확히 기록).
- **debt-009 미상환**: `Log/homing_capture_220350.jsonl` 의 출처가 UNVERIFIABLE(`phase` 필드 전건 `baseline`, 파일명이 캡처 스크립트 규칙과 불일치) — 기준선 #2·#3·#4·#5 의 공통 근거 파일이다.
- **기준선#6 의 node4 잔차**: 종결 문서 자신의 공식대로면 node4 0° = 7,840,095 로 정본값과 201c(0.0035°) 차이. 거동 영향은 없으나 "진짜 0°"라는 라벨은 이 유보를 지운다.
- **기준선#6 vs 「호밍 = 0° 복귀」**: 설계 의도(0° 복귀)와 실측 정착 정밀도(+0.178°/+0.331° 잔차)를 구분하는 문장이 어느 문서에도 없다.

---

## §1 판정 요약

| 구분 | 건수 |
|---|---|
| 호밍 서술 문서 (파일 기준) | **72** |
| 이중기록 병합 후 고유 문서 | **64** |
| 오염위험 **상** (즉시 정정 대상) | **17** |
| 오염위험 중 | 21 |
| 오염위험 하 / 무관 | 26 |
| 소스 코드 내 오류 서술 | **14곳** (§4) |
| 이중기록 불일치 쌍 | **2쌍** (§5) |
| 미이행 사용자 지시 | **3건** (§6) |

**한 줄 진단**: 값 정본(`foil_a082.yaml:126`)은 일원화됐으나, **① 상단 배너가 본문·표까지 닿지 않는 구조**(정정이 머리에만 붙고 본문 인용문은 그대로)와 **② 코드 주석·펌웨어 상수가 문서보다 낡은 것**이 반복 오염의 두 축이다. 특히 **펌웨어 `SEER_HOME_ZERO_N3/N4` 만 구값**이라, 실제 로봇을 움직이는 최종 목표값이 문서·파이썬 전 계층과 다르다.

---

## §2 전수 목록 — 오염위험 **상** (17건, 즉시 정정)

| # | 경로 | 종류 | 최종수정 | 핵심 문제 | 판정 |
|---|---|---|---|---|---|
| 1 | [docs/can_relay/test-process.md](../can_relay/test-process.md) | 시험절차 | 2026-07-26 | **정정 블록이 하나도 없는 유일한 문서**이면서 "매번 지킨다"는 실행 절차서. `:7` "호밍 = 조향을 홈(0°)으로", `:8` "0x6064 리드백으로 홈 도달 검증"(완료 판정은 bit15이고 호밍 중 0x6064=0), `:25` "호밍 방식 재확립 필요"(확정됨). **주변 확보 경고·취소 수단 부재** | 오류 |
| 2 | [docs/adr/2026-07-27-amr-test-gui.md](../adr/2026-07-27-amr-test-gui.md) | ADR(Superseded) | 2026-08-02 | `:187-191` 이미 **삭제된** backend `0x60FB.4=1` 무조건 write 를 근거로 게이트 논증. `:107-108` 정착값을 조향 0° 로. debt-007 "미판정" 잔존 | 혼재 |
| 3 | [docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md](../claude-mistake/2026-07-27-002_node4-unverified-command-damage.md) | 실수기록 | 2026-08-02 | **배너와 본문 정면 충돌**. 본문 `:69-70` `STEER_HOME=[7871815,7840086]`, `:145,:169` "정착값 = 조향 0°" 가 확정형으로 잔존. debt-007 종결로 `allow_homing_motion` 게이트 근거가 공중에 뜸 | 오류잔존 |
| 4 | [docs/code_review/can_relay_firmware/2026-07-28.md](../code_review/can_relay_firmware/2026-07-28.md) ↔ Tools/…/(동일) | 코드리뷰 | 2026-08-02 | 호밍 언급 80건(최대 밀도). `:380` **폐기된 "Seer 재초기화 → 137° 왕복"** 이 §5 표에 사실로 잔존(배너 사정권 밖). `#221·222` 정착값을 "차량별 실측 상수"로. **줄번호 인용 약 317건이 3중 dangling — 헤더의 정정 안내조차 낡음** | 혼재 |
| 5 | [docs/code_review/can_relay_ros2/2026-07-29.md](../code_review/can_relay_ros2/2026-07-29.md) ↔ src/…/(동일) | 코드리뷰 | 2026-08-03 | 함수표 78항 전체가 무효. `HomingJudge`(死코드)·`homing_frames` 3-SDO 를 현행 호밍 경로로 제시. `~/home_cancel` 누락 | 혼재 |
| 6 | [docs/code_review/motor_control/2026-07-26.md](../code_review/motor_control/2026-07-26.md) | 코드리뷰 | 2026-08-02 | `:43,:69` 정착값 = "실측 목표"·"조향 0°". `:63-64` 삭제된 write 인용. `:65-66` **코드에 없는 문장을 코드 인용으로 제시** | 혼재 |
| 7 | src/Actuators/motor_control/docs/code_review/motor_control/2026-07-26.md | 코드리뷰(사본) | 2026-08-02 | **루트 대비 낡음** — 2026-07-27 감사 정정 4블록 미반영. `:43` "콜드부팅 조향스윙 게이트" 오명칭, `:174` 구 홈값 | 오류 |
| 8 | [docs/ros2_driver/2026-07-09-design-inputs.md](../ros2_driver/2026-07-09-design-inputs.md) | 설계입력 | 2026-08-03 | **다른 문서들이 근거로 인용하는 원천**. `:86-87` 정착값을 "조향 0°… 이것이 **정본**"이라 선언, `:139`·`:166-167`·`:209` 반복. 헤더 건너뛰고 절 본문만 인용하면 그대로 오염 | 혼재 |
| 9 | [docs/sw_structure/can_relay_ros2/2026-07-31.md](../sw_structure/can_relay_ros2/2026-07-31.md) ↔ src/…/(동일) | 구조문서 | 2026-08-02 | 문서 목적이 **"C++ 포팅 사전 구조 파악"**. 서비스 3개로 기재(`~/home_cancel` 누락 = **기준선#9 상실**), 死코드 `HomingJudge` 를 의존으로, 호밍 파라미터 8개 전부 누락, 제거된 `cmd_vel` 경로 잔존 | 혼재 |
| 10 | [docs/debt/registry.md](../debt/registry.md) | 부채대장 | 2026-08-02 | debt-016 상환계획 열 미정정, debt-014/022 인용 낡음. **미등록 부채 5건**(§3-2) | 혼재 |
| 11 | [docs/issues_and_fixes/issues_and_fixes.md](../issues_and_fixes/issues_and_fixes.md) | 이슈기록 | 2026-08-02 | `:131-170` **기각된 method 35 가 supersede 배너 없이 "완료"로 잔존**. `:154` debt-026 오참조, `:209` 존재하지 않는 debt-027. `:266-282` "호밍 멈출 수 없다 정정 완료"인데 **재발** | 혼재 |
| 12 | [src/Actuators/motor_control/README.md](../../src/Actuators/motor_control/README.md) | README | 2026-08-03 | 호밍 언급 36건(README 최대). `:153-155` 정착값 = 복귀 목표. **`:102`·`:105`·`:112`·`:138` 인용 4건이 grep 0 — 근거 사슬 전부 끊김**(tongyi_amr.yaml 이 295→48줄 재작성) | 혼재 |
| 13 | [src/Comm/CAN/can_relay/README.md](../../src/Comm/CAN/can_relay/README.md) | README | 2026-08-03 | `:86` **폐기값 7871815/7840086 + "debt-007/016 미판정"** 을 현재 상수표로 제시(자기 배너와 모순). `:49-58` **「쓰는 법」이 실행 불가** — `require_homed_for_steer` 기본 True 라 `~/home` 없이 `~/steer_deg` 는 반드시 거부 | 혼재 |
| 14 | [Tools/amr_test_gui/README.md](../../Tools/amr_test_gui/README.md) | README | 2026-08-03 | `:99-100` **"중단 수단은 하드웨어 E-STOP 뿐"**(기준선#9 위배). `:107` 구 홈값 + 부재 경로(`config/tongyi_amr.yaml`) 출처 | 혼재 |
| 15 | [Tools/Can_Relay/panda-firmware/docs/rewrite-guide.md](../../Tools/Can_Relay/panda-firmware/docs/rewrite-guide.md) | 재작성지침 | 2026-07-28 | **신규 펌웨어 정본인데 2026-08-02 종결 헤더가 없다.** `:54` "137° = 조향 0° 복귀". **§5 기능·검증 목록에서 조향 호밍 FSM 이 통째로 누락**(7항목 중 0) → 재작성 시 호밍 경로 소실 위험 | 혼재 |
| 16 | [Tools/docking_field_kit/NEXT-SESSION-PROMPT.md](../../Tools/docking_field_kit/NEXT-SESSION-PROMPT.md) | 프롬프트 | 2026-08-03 | **기계 복붙용 산출물**인데 복붙 블록 `:49,52,54,55` 안에 철회된 호밍 근거 4종이 정정 없이 생존. 머리 정정표에 3건 누락 → 새 세션이 통째로 재수입 | 오류 |
| 17 | [docs/adr/2026-08-01-can-relay-home-calibration-method35.md](../adr/2026-08-01-can-relay-home-calibration-method35.md) | ADR | 2026-08-03 | 헤더는 기각 선언, **본문 `:100` 표는 "35(기본)"** 로 잔존. `:83-85` "홈 상수가 코드에서 사라진다"(반대로 유일 정본으로 남음). **기준선#1·#2 가 ADR 전체에 한 줄도 없음 — 「덮어쓰면 무엇이 죽는가」 미검토가 실기 사고의 뿌리** | 혼재 |

---

## §3 전수 목록 — 오염위험 중 (21건)

| # | 경로 | 종류 | 최종수정 | 핵심 문제 | 판정 |
|---|---|---|---|---|---|
| 18 | [docs/adr/2026-07-09-motor-control-ros2-package.md](../adr/2026-07-09-motor-control-ros2-package.md) | ADR | 2026-08-02 | `:70-72` 정착값 = 조향 0°(배너가 정정). `:92-94` 삭제된 `0x60FB.4` write 인용(줄번호도 어긋남) | 혼재 |
| 19 | [docs/adr/2026-07-27-panda-fw-rewrite-brief.md](../adr/2026-07-27-panda-fw-rewrite-brief.md) | ADR | 2026-07-28 | `:26,:32` 제거된 `0xec` 를 유지 대상으로. `:66` "Home 36/37" 이 기각된 하드스톱 가설 잔재로 표에 생존 | 혼재 |
| 20 | [docs/adr/2026-07-28-0xec-rationale-void.md](../adr/2026-07-28-0xec-rationale-void.md) | ADR | 2026-08-02 | 무효화 판정 자체는 정확. `:48` 정착값을 조향 0° 로(배너가 정정) | 혼재 |
| 21 | [docs/adr/2026-07-28-homing-speed-clamp.md](../adr/2026-07-28-homing-speed-clamp.md) | ADR | 2026-07-28 | 상수·조건·subindex 는 코드와 **100% 일치**. 단 `:28,:69` "기계적 정지면"(기준선#5 재발 벡터), 파일명·`:81` **"클램프" 오칭**(실제는 거부), `:87` "호스트: 없음"(현재 `link.py:75` 이중검증) | 혼재 |
| 22 | [docs/adr/2026-07-29-can-relay-ros2-package.md](../adr/2026-07-29-can-relay-ros2-package.md) | ADR | 2026-08-03 | `:92` S9 사고근거 **"호밍은 시작하면 SW 가 못 멈춘다" — 헤더 정정 사정권 밖에 남은 유일한 무정정 호밍 오서술** | 혼재 |
| 23 | [docs/can_relay/field-record-orin-nx-2026-07-25.md](../can_relay/field-record-orin-nx-2026-07-25.md) | 필드기록 | 2026-08-03 | `:55` "0° 복귀" ↔ `:11` 헤더 "0°에 정확히 놓지 않는다" **동일 파일 내 충돌**. `:71,:73` 전칭 명제("항상 재호밍") 미검증 | 혼재 |
| 24 | [docs/can_relay/usb-can-mapping-table.md](../can_relay/usb-can-mapping-table.md) | 매핑표 | 2026-08-03 | `:150` ④ **"호밍 후 0x6064 리드백을 정본으로"** — 따르면 정착값을 홈으로 굳힘(헤더가 뒤집었으나 인라인 표시 없음). `:203-222` "RTR 불가"는 이미 구현됨(`can_definitions.h:5`) | 혼재 |
| 25 | [docs/claude-mistake/2026-07-27-001_freeze-object-list-guessed.md](../claude-mistake/2026-07-27-001_freeze-object-list-guessed.md) | 실수기록 | 2026-07-27 | **신규 발견**: freeze 집합에 넣은 `0x6041` 이 **호밍 완료 비트(bit15)를 포함** → `pc_authority` 구간에서 Seer 가 호밍 완료 전이를 못 봄. 이 부작용이 어느 문서에도 검토돼 있지 않음 | 혼재 |
| 26 | [docs/claude-mistake/2026-07-28-004_standard-procedure-omitted-by-design.md](../claude-mistake/2026-07-28-004_standard-procedure-omitted-by-design.md) | 실수기록 | 2026-07-27 | `:41` 정착값을 "조향 0° 복귀"로(배너와 충돌). `:42-43` 후건부정을 대우로 오칭. **③ E-STOP 항목이 세 파일 어디에도 미반영인데 추적 안 됨**(단, §6 참조 — 사용자가 E-STOP 제거를 지시했으므로 실제로는 미반영이 정답) | 혼재 |
| 27 | [docs/claude-mistake/2026-07-28-005_negative-assertion-without-verification.md](../claude-mistake/2026-07-28-005_negative-assertion-without-verification.md) | 실수기록 | 2026-07-27 | **정정본이 폐기된 코드 위에 서 있다** — 해결책으로 제시한 `0xec` 는 2026-07-28 제거됐고, 전제("제어권 반환이 재호밍 트리거")도 기각. `reflected_assets: []` | 오류잔존 |
| 28 | [docs/claude-mistake/2026-07-29-001_structural-impossibility-reassertion.md](../claude-mistake/2026-07-29-001_structural-impossibility-reassertion.md) | 실수기록 | 2026-07-29 | 정정본 `:42` "`0x60FB.3` 로 각도 경로가 존재한다"가 **[존재]를 [동작]으로 확대한 같은 유형의 위반**. 실제로는 호밍 중 `0x60FB.2/.3`·`0x6064` 전부 0(debt-014) | 혼재 |
| 29 | [docs/claude-mistake/2026-07-29-003_audit-claims-overturned…md](../claude-mistake/2026-07-29-003_audit-claims-overturned-and-negative-assertion-relapse.md) | 실수기록 | 2026-08-02 | `:43` B2 판정이 배너에 다시 뒤집혔는데 표는 원문 그대로. **자기가 정정한 "호밍은 멈출 수 없다"가 `gui.py:936`·`link.py:68` 에서 재발** — S6 lint 통과 중 | 혼재 |
| 30 | [docs/claude-mistake/2026-08-01-001_reopened-settled-scope…md](../claude-mistake/2026-08-01-001_reopened-settled-scope-without-reading-own-records.md) | 실수기록 | 2026-08-01 | 문서 전제가 "`homing_method: 35` 설계 후"인데 method 35 는 같은 날 기각. `reflected_assets: []`, status open | 오류잔존 |
| 31 | [docs/claude-mistake/INDEX.md](../claude-mistake/INDEX.md) | 색인 | 2026-08-02 | **2026-08-02 조향 홈 종결이 색인에 전혀 반영 안 됨**. 2026-07-27-002 가 open 으로 남아 구값이 든 문서로 유도 | 혼재 |
| 32 | [docs/verified_facts/2026-07-27.md](../verified_facts/2026-07-27.md) | 검증사실 | 2026-08-03 | §A-8(캡처 전수 파싱)은 **독립 재파싱으로 전건 재현 확인 — 저장소 최고 신뢰 근거**. 위험은 §B-1(250여 줄) 뿐: debt-007 미판정 서사·"(a) 판다 read 오염 지지"가 폐기됐는데 **본문에 폐기 표시 없음** | 혼재 |
| 33 | [docs/sw_structure/amr-test-gui/2026-07-27.md](../sw_structure/amr-test-gui/2026-07-27.md) ↔ Tools/…/(동일) | 구조문서 | 2026-08-03 | 대상 코드(11모듈)가 통째로 삭제됨 → 함수표·의존그래프 전 행 dangling. `:178` 구 홈값 + "미판정" | 폐기 |
| 34 | [src/Actuators/motor_control/docs/2026-07-09-inventory.md](../../src/Actuators/motor_control/docs/2026-07-09-inventory.md) | 인벤토리 | 2026-08-03 | `:62-63` 두 함수 설명이 「브링업이 호밍한다」는 폐기 모델 유지 → 안전 게이트 실효성 과대평가 | 혼재 |
| 35 | [Tools/amr_test_gui/HANDOFF-2026-07-28-refactor.md](../../Tools/amr_test_gui/HANDOFF-2026-07-28-refactor.md) | 핸드오프 | 2026-08-03 | 「절대 바꾸지 말 것」 표라는 강한 프레이밍. `:97` `0x6098` 금지 사유 과일반화, `:119` 종결된 debt-007 금지 잔존 | 혼재 |
| 36 | [Tools/Kinematics/README.md](../../Tools/Kinematics/README.md) | README | 2026-08-03 | `:143` **자기 코드(`chassis_kinematics.py:79`)와 다른 구값을 "실측"으로** 제시. `:157` "판정 전 실차 절대 조향 지령 금지"가 종결된 전제로 이 스택 실차 승급을 계속 봉쇄 | 혼재 |
| 37 | [Tools/Can_Relay/FIELD-RECORD-2026-07-25.md](../../Tools/Can_Relay/FIELD-RECORD-2026-07-25.md) | 필드기록 | 2026-07-28 | 관측은 유효. `:60,:68,:94` 전칭 명제("항상 재호밍")가 타 문서에 안전근거로 인용 중. `:61-62` 폴레이트 미판정 주석이 stale(반증됨) | 혼재 |
| 38 | [Tools/Can_Relay/panda-firmware/docs/history/safety_seer_gate.md](../../Tools/Can_Relay/panda-firmware/docs/history/safety_seer_gate.md) | 이력문서 | 2026-08-03 | **이미 삭제된 함수(`seer_is_homing_write`)의 "미수정 결함 + 수정안"** 이 현재상태 라벨로 잔존 → 신규 펌웨어에 없는 결함 복원 위험. 이관표 인용 전부 현행 파일에 대응 없음 | 혼재 |
| 39 | [Tools/docking_field_kit/HANDOFF-amap2.md](../../Tools/docking_field_kit/HANDOFF-amap2.md) | 핸드오프 | 2026-08-03 | `:100` "홈은 불변 상수가 아니다", `:103` **"호밍 후 0x6064 리드백을 정본으로"** — **이 지시가 실제로 펌웨어 `SEER_HOME_ZERO_*` 오염의 문서적 출처**. `:115-119` 폐기된 측정 절차가 Seer 노드 상실→재호밍(물리 이동)을 유발할 수 있음 | 혼재 |
| 40 | [Tools/docking_field_kit/RUNBOOK.md](../../Tools/docking_field_kit/RUNBOOK.md) | 런북 | 2026-07-27 | **2026-08-02 종결 미반영**. §0 킷 목록에 호밍 스크립트 4개가 하나도 없음. `:118` `home` = "조향 홈 + 정지"인데 실제는 **클램프·램프 없는 직접 점프**(137° 갇힘 사고 재현 경로). 드라이브 호밍 vs 홈 이동 용어 미분리 | 혼재 |

---

## §3-1 전수 목록 — 오염위험 하 / 호밍 무관 (26건)

| 경로 | 종류 | 판정 | 비고 |
|---|---|---|---|
| [docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md](../adr/2026-07-26-qd-ik-pm90-unique-solution.md) | ADR | 혼재(경미) | 137° 를 좌표계 없이 "정상 범위 밖"으로 — 리밋 기준으로 읽으면 정상 자세를 FAULT 로 |
| [docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md](../adr/2026-07-27-panda-boot-bitrate-and-failsafe.md) | ADR | **정확** | 기준선#1·#4·#8 과 전부 일치. Handbook 쪽번호만 원문 대조 전 확정 금지 |
| [docs/adr/2026-07-28-can-transport-abstraction.md](../adr/2026-07-28-can-transport-abstraction.md) | ADR | **정확** | 호밍은 기각 사유 방증으로만 등장 |
| [docs/adr/2026-07-28-old-gui-removal.md](../adr/2026-07-28-old-gui-removal.md) | ADR | 혼재(경미) | `:40-41` "상이값 4개"는 node3+node4 합집합(node3 단독 2개) — 노드 스코프 혼선, 논지 무해 |
| [docs/adr/2026-07-31-can-relay-cpp-motor-layer.md](../adr/2026-07-31-can-relay-cpp-motor-layer.md) | ADR | 혼재 | `:217` 구 홈값, `:208-209` 종결된 debt-007/016 참조(헤더가 정정) |
| [docs/can_relay/2026-07-07-design-inputs.md](../can_relay/2026-07-07-design-inputs.md) | 설계입력 | **정확** | 오류 2건 모두 인접 정정 블록으로 무력화 |
| [docs/can_relay/drive-stop-config-2026-07-28.md](../can_relay/drive-stop-config-2026-07-28.md) | 설정기록 | **정확** | **기준선#1·#9 의 1차 근거**(4노드 `0x6098=1` 판독표). 구동축 `0x6099` 행에 "미호밍" 주석 부재 |
| [docs/claude-mistake/2026-07-26-001_emulate-stopvalue-false-claim.md](../claude-mistake/2026-07-26-001_emulate-stopvalue-false-claim.md) | 실수기록 | 혼재 | 호밍은 인용 1건. 원본 문서가 이미 조건부로 정정한 내용이 역반영 안 됨 |
| [docs/claude-mistake/2026-07-28-003_invented-steer-ramp-mechanism.md](../claude-mistake/2026-07-28-003_invented-steer-ramp-mechanism.md) | 실수기록 | **정확** | 정정 완료, 코드도 램프 삭제·클램프 대체 확인 |
| [docs/claude-mistake/2026-07-28-006_errata-v1-condemned-correct-citations.md](../claude-mistake/2026-07-28-006_errata-v1-condemned-correct-citations.md) | 실수기록 | **정확** | v1 → v2 교체·차단 표기. `0x6000` DI 번호 충돌은 debt-008 로 이관 |
| [docs/claude-mistake/2026-07-28-007_flash-without-size-limit-check.md](../claude-mistake/2026-07-28-007_flash-without-size-limit-check.md) | 실수기록 | **정확** | 호밍 기술 주장 없음(도구 제약 사건) |
| [docs/claude-mistake/2026-07-28-008_stale-process-state-reported.md](../claude-mistake/2026-07-28-008_stale-process-state-reported.md) | 실수기록 | 무관 | 호밍은 맥락뿐 |
| [docs/claude-mistake/2026-07-28-011_device-state-claimed-from-staging-file.md](../claude-mistake/2026-07-28-011_device-state-claimed-from-staging-file.md) | 실수기록 | **정확** | 정정 완료. `0xea` 실기 탑재 확인이 기준선#9 의 방증 |
| [docs/code_review/canrelay-fw-s4-s6/2026-07-29.md](../code_review/canrelay-fw-s4-s6/2026-07-29.md) ↔ Tools/…/(동일) | 코드리뷰 | **정확** | 호밍 주장 2건 모두 정확, dangling 1건뿐 |
| [docs/code_review/can_relay_firmware/README.md](../code_review/can_relay_firmware/README.md) ↔ Tools/…/ | 리뷰색인 | 혼재 | md5 `c35daf53`(475줄) 표기가 현행(497줄, `0a109609`)과 불일치 |
| [docs/code_review/motor_control-can-consistency/2026-07-26.md](../code_review/motor_control-can-consistency/2026-07-26.md) | 코드리뷰 | 혼재 | `:45` 구 홈값·`yaml:20` 오참조. 주1 "값 고치지 말 것"이 정본 갱신 롤백 유인 |
| src/Actuators/motor_control/docs/code_review/motor_control-can-consistency/2026-07-26.md | 코드리뷰(사본) | 혼재 | **양방향 divergence**(§5). `:82` 반증된 "조향축 0x86 제거 권장" 잔존 → 따르면 브링업 파괴 |
| [docs/verified_facts/2026-07-28-errata.md](../verified_facts/2026-07-28-errata.md) | 정오표 | **정확** | **문서군에서 오염도 최저**. 값 주장 0건, 근거 없는 항목 0건, UNVERIFIABLE 자기 선언 |
| [docs/verified_facts/2026-08-02-steer-home-closed.md](../verified_facts/2026-08-02-steer-home-closed.md) | 검증사실(정본) | **정확**(유보 있음) | 판정은 옳고 코드 잠금 견고. §0-1 의 3건(88샘플 근거강도·debt-009·node4 201c)을 §6「열려 있는 것」에 미승계 |
| [docs/user_instructions/user_instructions.md](../user_instructions/user_instructions.md) | 지시로그 | 참조 | 호밍 지시 52건. **인용은 반드시 이 파일로**(§6) |
| [docs/user_instructions/session_log.md](../user_instructions/session_log.md) | 지시로그(뷰) | 참조 | **독립 교차검증원 아님** — 661/661 인용 완전 일치. 500자 절단본이라 증거 인용 부적합 |
| [src/Actuators/motor_control/docs/issues_and_fixes/issues_and_fixes.md](../../src/Actuators/motor_control/docs/issues_and_fixes/issues_and_fixes.md) | 이슈기록 | 혼재 | `:24` "emulate 가 zeroDI 피드백 미제공"은 기준선#4 위배(드라이브 DI 직결이라 릴레이가 개입 불가) → 잘못된 하드웨어 점검으로 현장 시간 소모 |
| [src/Control/…/trnav_qd_kinematics_code_updates.md](../../src/Control/Motion_Control/2WS/trnav_2ws_kinematics/docs/trnav_qd_kinematics_code_updates.md) | 이식기록 | 폐기 | `:48-52` "조향 절대 원점 미판정"이 2WS 배선 작업을 불필요하게 보류시킴 |
| [Tools/Can_Relay/fw_backups/README-2026-07-28.md](../../Tools/Can_Relay/fw_backups/README-2026-07-28.md) | 백업README | **정확** | 속도 범위·0xec 제거 이력, 인용 전부 실재 |
| [Tools/Can_Relay/fw_backups/README.md](../../Tools/Can_Relay/fw_backups/README.md) | 백업README | 무관 | freeze 집합 언급 1건 |
| [Tools/Can_Relay/panda-firmware/docs/history/safety_seer_gate-claims-verified.md](../../Tools/Can_Relay/panda-firmware/docs/history/safety_seer_gate-claims-verified.md) | 이력문서 | **정확** | 8행 전부 1차 데이터 + 재현 스크립트 동봉. 폴레이트 3자 충돌만 미정본 |

---

## §4 코드 오염 실물 — 문서가 아니라 **코드 안**에 있는 오류 서술 14곳

> 사용자 문제의식("잘못된 문서로 엉터리 코드 생성")의 **가장 직접적인 발현 지점**.
> 문서 배너로는 덮이지 않는다.

| # | 파일:줄 | 원문(축약) | 무엇이 틀렸나 | 심각도 |
|---|---|---|---|---|
| C1 | `Tools/amr_test_gui/gui.py:936-937` | "시작한 뒤에는 이 프로그램이 중간에 멈출 수 없습니다 / 중단은 하드웨어 E-STOP 뿐입니다" | 기준선#9 위배. **운전자가 읽는 확인 대화상자**. 취소는 `0x60FB:04=0` 한 줄(`gui.py:841` 이 `sub` 인자 보유) | 최상 |
| C2 | `src/Comm/CAN/can_relay/can_relay/link.py:68` | "SDO 로 `0x60FB:04=1` 을 직접 보내면 … 소프트웨어가 멈출 수 없다" | **바로 다음 줄 `:69` 가 스스로 반증**(펌웨어도 SDO 로 취소). 이 문장이 4곳에 복제됨(`backend.py:19-23,504-508,530-535`, `driver_node.py:303-305`) | 최상 |
| C3 | `src/Actuators/motor_control/motor_control/backend.py:246` | "조향 0° 는 절대 ≈+137°(7,882,020/7,859,062 counts)이며 설계된 원점 오프셋이다" | 기준선#6 위배. **`BringupRefused` 예외 메시지 = 런타임 출력**. 같은 파일 `:42` 가 정반대로 정확히 적어 **자기모순** | 상 |
| C4 | `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:212-213` | `SEER_HOME_ZERO_N3 7882020` / `_N4 7859062` | **주석이 아니라 값.** 이름은 ZERO 인데 0° 가 아니다. GOZERO 가 이 값으로 이동 → **펌웨어 호밍은 항상 0°+0.178°/+0.331° 에 정착**. 허용오차 `SEER_HOME_ZERO_TOL 57344`(=1°)라 펌웨어가 스스로 검출 불가 | 상 |
| C5 | `src/Comm/CAN/can_relay/can_relay/safety.py:100-115` | "호밍(method 35) 시작 전 …" / "(debt-007 — **아직 측정되지 않았다**)" / "재현성 **미측정**" | 기준선#7(기각) + debt-007 종결(재현성 3회 실측). 이 docstring 을 읽고 재현성 시험을 다시 설계하는 낭비 발생 | 상 |
| C6 | `src/Actuators/motor_control/test/test_backend.py:24-25` | "실기 호밍 완료 후 Seer 가 정착시킨 **조향 0° 는** 7,882,020 / 7,859,062" | 정착값을 0° 로 라벨 | 상 |
| C7 | `motor_control/backend.py:6-7,24,218,234` · `driver_node.py:152-153` · `config/tongyi_amr.yaml:13,41` (7곳) | "조향 홈 기준·호밍 거동은 **미판정** — debt-007 … **종결 금지**" | debt-007 종결(2026-08-02) 후에도 현재형. 같은 yaml `:25` 는 "✅ 해소 2026-08-02" → **한 파일 안에서 상충** | 상 |
| C8 | `motor_control/kinematics.py:65-68` | "직진(θ=0)이 node3 +137.45° / node4 +137.05°" | 직진(0°)은 +137.28°/+136.72°. 인용값은 정착값 | 중상 |
| C9 | `motor_control/test/test_backend.py:141` | "브링업은 `0x60FB.4=1` 을 **조건 없이 송신한다**(backend.py:368, :294-296)" | 현재 backend 는 RstStart 를 **전혀 송신하지 않는다**(`:269` 주석처리). 인용 좌표도 dangling | 중상 |
| C10 | `Tools/amr_test_gui/gui.py:934` | "조향 2축을 원점(리밋)으로 보낸 뒤 **0° 로 복귀시킵니다**" | GUI 는 SDO 직접 경로라 드라이브 Home 1 루틴만 돈다. **`0x607A`(0° 복귀)를 보내지 않는다** | 중상 |
| C11 | `foil_a082.yaml:79-81` | "정착값 7,882,001/7,859,065 … +10,197c(+0.178°) / +19,370c(+0.338°)" | 같은 파일 `:125` 와 값 불일치 + 산술 오류(실제 +10,210c / +19,168c = +0.331°) | 중 |
| C12 | `can_relay/protocol.py:44-50` | "method 35 … ① 호밍 후 `0x6064`≈0 이 직진 ② 전원 사이클마다 재호밍" | 기각된 경로(기준선#7)를 기각 표기 없이 현재형 사양으로 서술 | 중 |
| C13 | `Tools/docking_field_kit/orin_homing_capture.py:5-6, :281-282` | "Home 36/37 (기계 하드스톱, **리밋 스위치 없음**)" | 기준선#5 위배. 반증은 `:16-18`·`:283` 에 **뒤늦게** 붙어 상단이 먼저 읽힘 | 중 |
| C14 | `Tools/docking_field_kit/orin_homing_run.py:8,:25` | docstring "조향 0° 로 복귀한다" / `5: "DONE(0° 복귀완료)"` | 펌웨어 GOZERO 목표는 정착값(C4) → 0° 아님 | 중 |

### §4-1 하드코딩 홈 상수 산재 — **"정본 1곳" 선언과 실제 6곳**

| 파일:줄 | 값 | 기준선#6 대조 |
|---|---|---|
| `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml:126` | `[7871810, 7839894]` | ✅ **정본** |
| `Tools/amr_test_gui/gui.py:46` | `{3:7871810, 4:7839894}` | ✅ (config 미연동 사본) |
| `src/Actuators/motor_control/config/tongyi_amr.yaml:40` | `[7871810, 7839894]` | ✅ (사본) |
| `motor_control/driver_node.py:71` | `[7871810, 7839894]` | ⚠ 코드 기본값 존재 자체가 debt-032 |
| `Tools/Kinematics/chassis_kinematics.py:79` | `{3:7871810, 4:7839894}` | ✅ (사본) |
| **`safety_seer_gate.h:212-213`** | **`7882020 / 7859062`** | ❌ **구값 — 실제 로봇을 움직이는 최종 목표값만 미갱신** |
| `motor_control/backend.py:44` | `steer_home: int = 0` | ❌ YAML 미로드 시 0 이 `0x607A` 로 → 바퀴 ≈−137.28° 회전 |
| 테스트 픽스처 5곳 (`mc/test_backend.py:28`, `mc/test_protocol.py:28`, `cr/test_backend.py:282`, `cr/test_protocol.py:135`, `cr/test_safety.py:78`) | 구값/정착값 | ⚠ 폐기값이 회귀로 고정 → 재확산 경로 |

**구조 결함**: `can_relay` 가 채택한 「코드 기본값 없음 + 미설정 시 거부」 패턴(`safety.py:42 DEFAULT_STEER_HOME = {}`)이 **motor_control·gui.py·펌웨어에는 미적용**.

### §4-2 기각된 method 35 코드 경로 — **전부 생존, 실행 가능**

`protocol.py:41-47`(상수) · `:210 home35_move_frames()` · `:227 home35_set_frames()` · `:236 home35_reached()` · `backend.py:397 _home_method35()` · `:510,:547` 분기 · `driver_node.py:120-121`(파라미터 검증이 `"35"` 를 **명시적으로 허용**) · `test_backend.py:591-724` 회귀 스위트.

→ **YAML 2줄**(`homing_method: "35"`, `homing_enabled: true`)이면 3톤 차체에서 기각된 재영점이 실행된다. **기각 사유(Seer desync)에 근거한 런타임 차단이 없다.** registry 미등록.

---

## §5 이중기록 불일치 — 어느 쪽도 정본이 아닌 쌍 2건

| 쌍 | 상태 |
|---|---|
| `docs/code_review/motor_control/2026-07-26.md` ↔ `src/Actuators/motor_control/docs/…` | **루트가 최신** — 2026-07-27 감사 정정 4블록이 루트에만. 패키지본에는 "콜드부팅 조향스윙 게이트" 오명칭·구 홈값이 무정정 잔존. 반대로 패키지본에만 md5/divergence 정정 1블록 |
| `docs/code_review/motor_control-can-consistency/2026-07-26.md` ↔ `src/…` | **양방향 divergence** — 루트에만 2026-08-03 크랩 정정·0x86 반증 블록, 패키지본에만 `yaml:20→:32` 좌표정정. **완전 동기화된 쪽이 없음** |

동일 확인된 쌍 6건: `can_relay_firmware/2026-07-28.md`, `can_relay_firmware/README.md`, `canrelay-fw-s4-s6/2026-07-29.md`, `can_relay_ros2/2026-07-29.md`, `sw_structure/amr-test-gui/2026-07-27.md`, `sw_structure/can_relay_ros2/2026-07-31.md`.

---

## §6 사용자 지시 대조 (`docs/user_instructions/user_instructions.md`)

### 확정 — 재론 금지

| 쟁점 | 결정 | 근거 |
|---|---|---|
| **호밍의 정의** | 리밋 원점 경유 후 **조향 0° 복귀까지가 호밍**. 원점에 머무는 것이 아님 | `:2649`(07-27 22:36), 재확인 `:2631` |
| **소프트 E-STOP** | **없앤다.** 정지수단 = 릴레이 해제 | `:2625` → `:2595` → `:2565` (3회) |
| **CAN 종단 60Ω** | 확인 완료, **다시 묻지 말 것** | `:3087` |
| **호밍 중 CAN 각도 판독** | 경로 없음 — 사용자 본인이 철회, debt-014 로 이관(**새 방법은 사용자가 제공 예정**) | `:891` |
| **호밍 취소** | 구현 지시됨 → 이행 완료(`~/home_cancel`) | `:207`(08-01 08:37) |

> ⚠ **§3 #26 의 "E-STOP 미반영" 은 결함이 아니다** — 사용자가 명시적으로 제거를 지시했다.
> `2026-07-28-004` 의 ③ 항목은 사용자 결정으로 종결 처리해야 한다.

### 뒤집힌 지시

- **method 35**: `:177`(08-01 09:33) "진행해봅시다" **명시 승인** → 같은 날 실기 기각. **"사용자가 승인했었다"만 인용하면 오판.**
- **홈 재측정**: `:135`(08-01 17:21) "뭘 또 하겠다는거지?" → `:117`(18:10) **"호밍할거면 해도 됨"** → `:27`(08-02 21:46) "실 로봇에서 진행 — 호밍 확정 실험". **금지 대상은 재측정이 아니라 「기존 실측 로그를 안 보고 새로 시작하는 것」**(`:81`, `:171`).

### 미이행 지시 3건

| 지시 | 위치 | 상태 |
|---|---|---|
| **리밋 백오프** — "리미트 스위치가 홈을 거치면 인지하고 살짝 뒤로가서 꺼지게 해야지, 아니면 리미트 스위치에 걸리면 안 움직일 수도 있잖아" | `:2661` (07-27 22:28) | **답변조차 기록 없음.** 펌웨어·ADR·debt 전수 grep 0건 |
| **히스테리시스 측정** — "히스테리시스 등등 추가로 측정해봐야 함" | `:2583` (07-27 23:15) | `docs/` 전수 grep 0건. debt-007 종결은 재현성만 확인 |
| **"결론 ; 해결 / 미해결?"** | `:3` (08-03 07:14) | 미응답 |

> ⚠ **`user_instructions.md` 의 호밍 매칭 66줄 중 22줄은 task-notification 자동 로그**(에이전트 출력이 사용자 발화 위치에 기록됨). `:1959`, `:1977`, `:2007` 등의 수치를 "사용자가 말했다"로 인용하면 **사용자가 `:81` 에서 지적한 「오기록된 문서로 오판」이 정확히 그 구조로 발생**한다.

---

## §7 미등록 부채 (신규 제안 6건)

| # | 내용 | 근거 |
|---|---|---|
| N1 | **「호밍은 멈출 수 없다」 절대형 단정 재발** (기준선#9 위배, 재발 부채) | `gui.py:936-937`, `Tools/amr_test_gui/README.md:99-100`, `link.py:68` |
| N2 | **기각된 method 35 경로가 코드에 통째로 잔존** — YAML 2줄로 부활, 런타임 차단 없음 | §4-2 |
| N3 | **펌웨어 `SEER_HOME_ZERO_N3/N4` 만 구값** — debt-016 상환 7곳 목록에서 펌웨어만 빠진 사유가 어디에도 없음 | `safety_seer_gate.h:212-213` vs `registry.md:259-264` |
| N4 | **`safety.home_search_allowed()` docstring 이 종결 사실을 현재형으로 부정** | `safety.py:104,117` vs `registry.md:237-238` |
| N5 | **폐기값이 테스트 픽스처로 고정** — 정본 갱신을 되돌리는 회귀 | §4-1 하단 5곳 |
| N6 | **`amap2_monitor.py` 가 `0x60FB.04` 분기 부재로 실차 호밍 미탐** — 2026-07-27 식별 후 미해결인데 3개 문서가 이 검출기 판정을 인용 | `amap2_monitor.py:183-185` |
| N7 | **debt id 오참조 2건 실발생** — debt-015 가 예고한 재상신 조건 충족 | `issues_and_fixes.md:154`(debt-026↔016), `:209`(debt-027 부재↔017) |

---

## §8 권고 조치 순서

1. **코드부터** (문서 배너로 안 덮인다): C1·C2 (기준선#9 위배, 운전자 노출) → C3·C4 (홈 값) → C5·C7 (종결 부채 현재형)
2. **정정 블록 0인 실행 절차서**: `docs/can_relay/test-process.md`, `Tools/docking_field_kit/RUNBOOK.md`, `Tools/docking_field_kit/NEXT-SESSION-PROMPT.md`(복붙 블록 내부 직접 수정)
3. **신규 산출물 정본**: `rewrite-guide.md`(2026-08-02 헤더 + 호밍 FSM 절 신설), `docs/sw_structure/can_relay_ros2/2026-07-31.md`(C++ 포팅 전)
4. **인용 원천**: `docs/ros2_driver/2026-07-09-design-inputs.md:86-87,139,166-167,209` 인라인 정정
5. **이중기록 2쌍 병합** (§5)
6. **미등록 부채 7건 등록** (§7), **미이행 지시 3건 처리** (§6)

---

*작성: 2026-08-03 · 20인 병렬 감사 · 문서 72파일 + 소스 37파일 전수*
*정정 시 본 문서를 갱신하고, 종결 항목은 취소선이 아니라 삭제 + 종결 근거 링크로 처리할 것.*
