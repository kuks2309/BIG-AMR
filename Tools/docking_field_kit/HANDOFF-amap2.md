# amap-2 현장 도킹 — 인수인계 (이어서 진행)

> 작성 2026-07-23 저녁(KST). 대상: amap-2(현장 PC) + 판다 #2(`1e003e...`, 우리 펌웨어) + 실 Seer + 실 모터.
> 목적: 다음 세션/내일 아침에 이 문서만 보고 바로 이어서 도킹 검증 진행.

## 0. 지금까지 확정된 상태 (검증됨)

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 판다 #2 펌웨어 | ~~✅ `DEV-26524538-DEBUG`~~ → **구버전(2026-07-27 기준)**. 현행 빌드 = `Tools/Can_Relay/panda-firmware/board/obj/version`(현재 `DEV-d98bc1a5-DEBUG`, 빌드 시 git HEAD 로 생성 — `board/SConscript:89-92`)이며 250 kbps 부팅 기본값(`board/drivers/can_common.h:174-176`)+heartbeat fail-open(`board/main.c:257-258`) 포함 | flash 확인(2026-07-23) / 정정 근거: `docs/verified_facts/2026-07-27.md` §A-1, ADR `2026-07-27-panda-boot-bitrate-and-failsafe.md` D1·D2 |
| 전원 | ✅ 12V (voltage 12344mV) | health |
| 배선(클론 핀맵) | ✅ CAN0 H4/L5, CAN2 **H23**/L24, 12V 12·14/GND 1·26 | 실트래픽 흐름으로 입증 |
| 실 Seer↔모터 통신 | ✅ **활성** — Seer 폴링 ~22.8k/15s, 모터 응답 ~22.8k/15s | `amap2_monitor.py monitor` |
| **Seer home신호 점검** | ~~✅ **정상**~~ → **⚠ 미판정(2026-07-27)** — 관측된 것은 `0x607A` **목표값** 고정 전송뿐. 그 값이 현재 위치인지는 미판정. HOMING 모드 진입 0 은 관측 사실. | 아래 §2 + 정정 |
| amap-1 24h 신뢰성 | ✅ Run1·Run2 각 100%(총 40만+ 검증 0실패), Run3+ 연속 진행중 | amap-1 |

## 1. 킷 위치 & 구성 (amap-2)
`~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit/`
> **[2026-07-27 정정 — 경로]** 위는 **amap-2 기준(구)** 이며 현 로봇 PC(Ford-CATL-orin-nx)에 없다
> (`ls -d ~/Project/T-Robotics` → No such file or directory). 현 장비 사본:
> `~/Project/Ford-CATL-AMR/T-Driver-Analysis/tools/docking_field_kit/` ·
> `~/Project/CAN-Relay/docking_field_kit/`(`docs/can_relay/field-record-orin-nx-2026-07-25.md:11`).
> **정본 = 저장소 `Big-AMR/Tools/docking_field_kit/`.** 아래 `cd` 지시(§3)도 이 경로로 읽을 것.
- `panda/`(lib) · `panda.bin.signed`(펌웨어) · `flash_panda.py`
- `docking_drive.py` — 실 도킹 드라이버(PC→모터 구동, Seer 속임)
- **`amap2_monitor.py`** — 신규. 신뢰성/안전 모니터 + **Seer home신호 이상 검출**(아래)
- `seer_gate_bench.py`·`docking_scenario_bench.py` — PCAN 벤치(현장엔 PCAN 없으면 생략)
- `PINMAP.md`(⚠CAN2_H=pin23) · `RUNBOOK.md`(현장 절차)

## 2. 핵심 발견 — Seer의 home지령 (반드시 이해)

`amap2_monitor.py monitor`로 실 트래픽을 디코드한 결과:
- **Seer가 steer 노드 3·4에 `0x607A`(Target_position) = 정확히 home 값(node3=7871815, node4=7840086)을 매 사이클 지속 전송.**
  (⚠ 2026-07-27: "`= home 값`" 중 **목표값이 곧 현재 위치라는 함의는 미판정 전제**다 — 아래 정정 블록 참조. 전송 사실·값 자체는 관측 그대로.)
- 값 종류 = 각 1개(변동 없음), 비home 이동·구동·~~HOMING모드(0x6060=6) 진입~~ **모두 0**.
- → ~~**정차 position-hold(정상). 작동이상 home신호 아님.**~~ (로봇이 서 있으니 Seer가 조향을 home에 붙잡아 두는 정상 서보 동작.)

> ### ⚠ 정정 (2026-07-27) — "`0x6060=6` 진입 0" 은 **호밍 부재의 증거가 아니다**
> 이 드라이브의 `0x6060` Modes_of_operation 유효값은 **1(PP)/3(PV)/4(PT)/7/8/9/10 뿐이고
> 6(CiA402 표준 Homing mode)은 지원하지 않는다** [Handbook V7.0 §6.6.3, page 152].
> 오히려 Home 1/2 는 **PP 모드(`0x6060=1`)** 에서만 유효하다 [같은 문서 §4.6, page 116].
> ⇒ `0x6060=6` 은 애초에 나올 수 없는 값이므로 그 부재는 아무것도 증명하지 않는다.
> **실차 Seer 의 실제 호밍 개시 트리거는 `0x60FB.04 = 1`(RstStart, "0-Reset off, 1-Reset on")**
> 이다 [Handbook V7.0 §6.9, page 171; Appendix I, page 196].
> 실측 시퀀스(`Log/homing_capture_220350.jsonl`):
> `0x6040=0x86` → `0x6099=2500`(t=17.918/17.919) → **`0x60FB.4=1`(t=17.925/17.926)**
> → `0x6041` bit15=0 최초 관측(t=17.956, ⚠ 전이 확정 구간 (5.138, 17.956]) → 탐색 ~29 s → `0x6000` sub 1 bit3(−Limit) 세트(t=47.025)
> → `0x6041` bit15 0→1(t=48.999/49.080) → `0x6060=1`(PP) → `0x6081=30000`/`0x6083=250`/`0x6084=250`
> → `0x607A`=조향 0° → `0x6040=0x3F`. 같은 캡처에서 `0x6098` 은 **write·read 모두 0건**이고
> 조향 controlword 는 0x3F/0x86 뿐(bit15 Reset Home 은 0건)이다.
> ⇒ 위 §0 표 :14 의 "HOMING 모드 진입 0 은 관측 사실" 및 아래 :40 의 동일 문구도 같은 이유로
> **호밍 부재 근거로 인용하지 말 것**. `amap2_monitor.py` 의 판정 집합에도 `0x60FB.04` 분기가 없어
> 실차 호밍을 미탐한다(같은 파일 docstring 정정 블록 참조 — 안전 직결).

> ## ⚠ [2026-07-27 정정 — 위 결론은 "정상 확정" 이 아니라 **미판정 모순**]
> **남는 관측 사실**(그대로 유효): Seer 가 node3·4 에 `0x607A` 목표값 `7871815`/`7840086` 을 매
> 사이클 **고정 전송**하며 값 종류는 각 1개, HOMING 모드(`0x6060=6`) 진입은 0.
>
> **취소되는 부분**: "= 정차 position-hold(정상)" 이라는 결론. 이 결론은 *그 목표값이 곧 현재 위치
> (home)* 라는 전제 위에 서 있는데, §2 가 실제로 본 것은 **목표값(`0x607A`)뿐이고 위치 피드백
> (`0x6064`)은 대조하지 않았다.** 그 전제 자체가 아직 갈리지 않은 모순으로 등록돼 있다:
> - `docs/verified_facts/2026-07-27.md` §B-1 표 — Seer 1040 encoder `−7,871,810` / `−7,840,091`
>   (position ≈ 0 rad, 운전자 육안 바퀴 0°) **vs** 판다 read node3 ≈ `−1,517` · node4 ≈ `+1,161`
>   counts. **조향 노드에서만 두 소스가 7.87M counts(=137°) 어긋난다 … 어느 쪽인지 미판정.**
>   (같은 시점 구동 노드는 부호만 반전되고 절댓값 일치.)
> - `docs/ros2_driver/2026-07-09-design-inputs.md:56,81` — ~~"부팅 시 `0x6064≈0` 이 **정상**, 홈 상수는
>   절대 목표(steerOffset **137.3°**)이며 **매 기동 시 스윙 필요**"~~.
>   > ### ⚠ 정정 (2026-07-27) — 위 인용 3조각이 실기 캡처로 갱신됨
>   > 근거: `Log/homing_capture_220350.jsonl`(Seer 주도 호밍, 253,510 프레임 수동청취) +
>   > `References/motor_configuration/motor-config-analysis.md:118-143` + EasyDRIVE 파라미터 스크린샷.
>   > - **"steerOffset 137.3°" 라는 값은 config 에 없다.** 축별 실값은 node3 **138.000000°** /
>   >   node4 **137.250000°** 다 (`motor-config-analysis.md:24-30`, `docs/verified_facts/2026-07-27.md:215`).
>   >   홈 counts 는 여기서 파생된다 — **(steerOffset + 괄호보정) × 57,344**:
>   >   node3 (138.000000 − 0.726422) × 57344 = **7,871,816**(상수 7,871,815, Δ≈1),
>   >   node4 (137.250000 − 0.529735) × 57344 = **7,840,087**(상수 7,840,086, Δ≈1)
>   >   ⇒ 각도로는 node3 **137.27°** / node4 **136.72°** (`motor-config-analysis.md:119-121`).
>   > - **"부팅 시 `0x6064≈0` 이 정상" 은 성립하지 않는다.** 이 캡처의 baseline(t≈0.034) `0x6064` 는
>   >   node3 7,871,818 / node4 7,840,084 로 이미 홈 부근이다. `0x6064` 가 정확히 0 이 되는 구간은
>   >   **호밍 진행 중(t≈18.0~49.2)뿐**이며 그 0 은 실위치가 아니다.
>   > - **"매 기동 시 스윙" 은 이상거동이 아니라 설계된 이동이다.** 조향축에는 리밋 스위치가 실재하고
>   >   호밍 방식은 **Home 1(음의 리밋 트리거)** — 전 노드 `0x6098 = 1` 실기 판독, Handbook 기본
>   >   RstMode 도 1 [Handbook V7.0 §4.6, page 115-116]. 호밍은 원점(리밋)을 경유한 뒤
>   >   **조향 0° 로 복귀하는 데까지가 한 절차**이며 원점에 머무르지 않는다
>   >   (실측: `0x6000` sub 1 bit3(−Limit) 세트 t=47.025 → `0x6041` bit15 0→1 t=49.00/49.08 →
>   >    복귀 이동 중 bit3 해제 t=49.422). ⇒ 「원인 미상」·「이상 스윙」·「Home 36/37 기계 하드스톱」
>   >   류 서술은 오류다.
>   > - ⚠⚠ **홈 counts 는 전원 사이클 불변 상수가 아니다.** 같은 세션 안에서 호밍 전/후 목표가 바뀐다 —
>   >   호밍 후(t≈49.14 전환) `0x607A` = node3 **7,882,020** / node4 **7,859,062** 로 t=180 까지 고정
>   >   (각 6,319 프레임). 호밍 전 값 대비 +10,205 / +18,976 counts = **+0.178° / +0.331°**.
>   >   ⇒ 절대 counts 를 하드코딩하지 말고 **매 기동 호밍 후 `0x6064` 리드백을 정본**으로 삼을 것.
>   > - 위 §2·§3 의 「`0x607A` = home 값을 **매 사이클 지속 전송**」(:33) 은 **호밍 전 구간에 한정**된
>   >   관측이다. 2026-07-27 캡처에서는 그 값이 t≈17.88 에 끝나고 이후 7,882,020 / 7,859,062 로 전환된다.
>   > - 잔여 미확정: 호밍 후 정착값이 EasyDRIVE steerOffset(138.000 / 137.250) 대비 각각
>   >   **−0.5485° / −0.1988°** 낮다. 「직진 자세 = 육안 0°」 여부는 미확인
>   >   (`motor-config-analysis.md:143-144`).
> - `docs/verified_facts/2026-07-27.md` 사용 규칙 2 — **§B 항목은 "확정"으로 인용하지 않는다.**
> - config 원본도 경고를 달고 있다: `src/Actuators/motor_control/config/tongyi_amr.yaml:91`
>   `steer_home_counts: [7871815, 7840086]  # ⚠ debt-007 판정 전까지 무비판 신뢰 금지`.
> - 같은 137° 가 실장비 손상 사고와 얽혀 있다(`docs/claude-mistake/2026-07-27-002`, node4 137°
>   범위이탈 갇힘 — 인과는 미확인).
>
> **판정에 필요한 측정**(verified_facts §B-1 "판정에 필요한 측정"):
> ① **제어권 미획득(intercept off)** 상태에서 판다로 조향 `0x6064` 를 여러 번 직접 read
> ② 같은 순간 Seer 1040 `encoder` 동시 조회
> ③ 두 값이 부호만 다르고 절댓값이 같으면 → 판다 read 오염(제어권 중에만) 확정 /
>    계속 어긋나면 → 호밍 후 기준 재설정 확정.
>
> 판정 전 안전 규칙: `allow_homing_motion` 게이트(홈 5° 이탈 시 브링업 거부)를 **끄지 말 것**
> (verified_facts §B-1). 숫자는 어느 것도 변경하지 않았다.

**함의(도킹 안전):** 도킹 중(PC 주도)에도 Seer는 이 home지령을 계속 쏜다. 게이트가 이를 **차단**하지 않으면
PC의 구동/조향 명령과 모터에서 충돌한다. 그래서 `SEER_GATE`(auth=PC 시 0x601–604 write 차단+가짜ack)가 필수.
→ 내일 도킹 전 **`gatecheck`로 이 차단을 실측 검증**할 것(§4-C).

## 3. amap2_monitor.py 사용법
```bash
cd ~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit
python3 amap2_monitor.py monitor 30      # A: passthrough 리슨(무개입/안전). Seer폴링·모터응답·home신호 판정
python3 amap2_monitor.py monitor 28800   # A 8시간(야간 무인 안전). 로그 append
python3 amap2_monitor.py gate 30         # B: intercept 투명중계(auth=Seer). 판다 삽입이 통신 교란 안 하는지 (attended)
python3 amap2_monitor.py gatecheck 30    # C: auth=PC 게이트가 Seer home지령을 모터측에서 차단하는지 (attended, 모터 안 움직임)
python3 amap2_monitor.py seq 30 30       # A→B 순차 후 자동 passthrough 복귀
```
- 판정: `정상` = Seer폴링+모터응답 활성 & HOMING재진입 0 & (gatecheck 시) 누출 0.
- 로그: `~/docking_reliability/amap2_monitor.log`
- **안전**: monitor(A)는 무개입(야간 OK). gate(B)/gatecheck(C)는 판다를 실버스에 삽입 → **반드시 지켜보는 상태**에서. 종료 시 자동 passthrough 복귀. ~~USB 끊기면 판다 heartbeat 타임아웃(~5s)으로 fail-safe passthrough.~~
  > **[2026-07-27 정정]** heartbeat 상실 시 펌웨어는 **`SAFETY_SILENT` 로 복귀**한다 —
  > `Tools/Can_Relay/panda-firmware/board/main.c:248-249`. "fail-safe passthrough 복귀"는 부정확
  > (`docs/verified_facts/2026-07-27.md` §A-5 가 이 문구를 명시적으로 부정확 판정).
  > 릴레이 해제(`set_intercept_relay(false)`+`pc_authority=false`)는 **2026-07-27 추가분**
  > (`board/main.c:257-258`, ADR `2026-07-27-panda-boot-bitrate-and-failsafe.md` Decision 2)이며,
  > 이 문서가 전제하는 2026-07-23 시점 펌웨어(`panda.bin.signed`, md5 `d4188e02…`)에는 **없다**.
  > 타임아웃도 조건부: ignition on **5s** / off **2s**(`board/main.c:164-165`, `:233`
  > `check_started()` 분기). 단 릴레이 부팅 기본은 물리 통과다(`board/drivers/harness.h:91`,
  > verified_facts §A-3).

## 4. 다음 세션/내일 아침 권장 순서

> ## ⛔ [2026-07-27 정정 — 아래 순서는 **2026-07-25 실행 결과로 반증됨. 보류**] ⛔
> 이 문서는 2026-07-23 작성(:3)이고, 그 뒤 실차에서 아래 단계들이 실제로 실행돼 실패했다
> (`docs/can_relay/field-record-orin-nx-2026-07-25.md`):
> - **A(`monitor`)** — `:30` H0 통과(✅ 정상). 무개입 리슨이므로 **이 항목만 유효**하다.
> - **B(`gate`)** — `:31` intercept 전환 순간 Seer 가 node3·4 에 HOMING 설정(`0x6099=2500`) 발행 →
>   `:68-71` **Seer 리셋 인시던트**로 종료, `:32` H2 미실행·**HIL 전면 중단**.
> - **C(`gatecheck`)** — `:33` Seer write(`0x2B` controlword=0x3F, `0x23` target_position)가 **모터측으로
>   누출**. 즉 §4-C 가 요구한 "누출 0" 이 **실패**했다.
> - **도킹** — `:56` 실모터 구동(`docking_drive.py`)·추가 intercept 는 **원인 규명 전까지 보류,
>   실 구동 전 사용자 확인 필수**. `:54` 현 상태 판다 intercept/게이트 방식은 **실차 비안전**.
> - 왜 중대한가: `:49` **Seer 는 리셋되면 복구 시 항상 재호밍 = 조향 물리 이동 동반(안전 직결)**.
>
> ⇒ **B·C·도킹은 보류.** 원문은 이력으로 남기되 실행 가능한 절차로 읽지 말 것.
> (`docs/verified_facts/2026-07-27.md` 사용 규칙 3 — 반증 시 원 기록에도 정정을 남긴다.)

- **A (안전, 지금/야간 가능)**: `monitor`로 실 통신 건전성 + home신호 정상 재확인.
- **B (attended)** ⛔**보류(2026-07-25 인시던트)**: `gate 30` — 판다 삽입(투명중계)이 Seer↔모터를 교란하지 않는지. Seer가 calibrating 루프/재호밍 안 뜨는지 확인.
- **C (attended, 도킹 직전 필수)** ⛔**보류(2026-07-25 누출 발생 = 게이트 차단 실패)**: `gatecheck 30` — auth=PC에서 Seer의 지속 home지령이 모터측(bus2)에 **누출 0**인지. (모터는 안 움직임.)
- **도킹 (attended, 안전구역+E-STOP)** ⛔**보류(field-record :56, 사용자 승인 필수)**: `python3 docking_drive.py` → `take`→`enable`→`f 30`(저속 방향확인)→도킹→`stop`→`release`. 상세 RUNBOOK.md §5–6(RUNBOOK §5 도 동일 사유로 보류 표기됨).

## 5. amap-1 병행 신뢰성 (참고)
- 연속 러너 `~/run_reliability_loop.sh` → `reliability_24h.py`를 24h마다 자동 반복(Run3,4,…). 결과 `~/docking_reliability/run{N}_result.txt`, 진행 `~/docking_reliability/loop.log`·`live_status.txt`.
- Run1·Run2 = 각 24h/100%(0실패). 저장소 기록: `docs/can_relay/reliability-24h-results.md`.

## 6. 주의(교훈)
- 클론 핀맵: **CAN2_H=pin23**(pin22 死핀). comma 표준 믿지 말 것.
- gate/gatecheck/도킹은 판다 삽입 → 사람이 볼 때만. monitor는 무개입이라 야간 OK.
- 도킹 종료 시 `release` 필수(Seer 반환). 아니면 Seer가 다음 노드로 못 감.
