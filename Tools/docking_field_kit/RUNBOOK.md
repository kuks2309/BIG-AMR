# 현장 도킹 릴레이 런북 (amap-2) — 2026-07-21 현장용

> 대상: amap-2 + 판다(#2, `1e003e...`, 우리 펌웨어 플래시됨) + 실 Seer + 실 모터.
> 목적: 노드이동(Seer 구동) ↔ 도킹(PC 구동, Seer 속임) ↔ 반환.
> ⚠ 실로봇. 안전구역·E-STOP 상비. 저속부터.

## 0. 킷 위치
`~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit/`

> **[2026-07-27 정정 — 경로]** 위 경로는 **amap-2 기준(구)** 이며 현 로봇 PC(Ford-CATL-orin-nx)에는
> 존재하지 않는다(`ls -d ~/Project/T-Robotics` → No such file or directory, 2026-07-27 확인).
> 현 장비의 실제 사본은 `docs/can_relay/field-record-orin-nx-2026-07-25.md:11` 기준
> `~/Project/Ford-CATL-AMR/T-Driver-Analysis/tools/docking_field_kit/` 와
> `~/Project/CAN-Relay/docking_field_kit/` 두 곳(둘 다 존재 확인). 본 저장소 정본은
> `Big-AMR/Tools/docking_field_kit/` 다 — 아래 `cd` 지시(§3 등)도 이 경로로 읽을 것.
> ⚠ 사본이 3벌이라 편집이 갈릴 수 있다. **정본 = 저장소 `Tools/docking_field_kit/`**.
- `flash_panda.py` — 펌웨어 플래시(필요 시)  · `panda.bin.signed` — 펌웨어
- `seer_gate_bench.py` · `docking_scenario_bench.py` — 벤치 검증(PCAN)
- `docking_drive.py` — 실 도킹 드라이버(PC→모터)
- `PINMAP.md` — ⚠ 핀맵(CAN2_H=pin23!)  · `reliability_24h.py` — 내구시험

## 1. 사전 준비 (1회)
```bash
pip3 install --user python-can libusb1      # 이미 있으면 생략
# udev (비루트 USB) — 이미 설정돼 있을 수 있음
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="bbaa", MODE="0666"' | sudo tee /etc/udev/rules.d/11-panda.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## 2. 배선 (⚠ PINMAP.md 준수 — CAN2_H=pin23, CAN0_L=pin5)
```
Seer  → 26핀 CAN0: H=pin4,  L=pin5      ← L은 pin5 권장(pin6도 같은 넷). pin5=릴레이 passthrough 브릿지 지점
모터  → 26핀 CAN2: H=pin23, L=pin24     ← H는 pin23! pin22(死핀) 아님
전원  → 12VIN=pin12/14, GND=pin1/26 에 +12V
```
- 종단: **2026-07-24 해결 완료(Seer 끝 DB9 2–7 에 120Ω 추가 → 전체 60Ω)**. 상시 점검 항목 아님 —
  CAN 오류가 보여도 종단을 원인 후보로 올리지 말 것(2026-07-27 확인: 잔류 오류의 정체는 판다 부팅
  비트레이트 500 kbps 였고 펌웨어에서 250 kbps 로 정정됨). 배선을 새로 손댔을 때만 재측정.
  > **[2026-07-27 조건 보강]** 위 "종단은 상시 점검 항목 아님 / 원인 후보로 올리지 말 것" 은
  > **passthrough(릴레이 OFF) 구성에 한한다.** 근거가 된 사용자 지시·종결 기록도 그 맥락이다
  > (`docs/issues_and_fixes/issues_and_fixes.md:86`). **intercept(도킹) 상태에서는 종단 요건이
  > 아직 해결되지 않았다** — 판다가 각 세그먼트의 안쪽 끝이 되어 세그먼트별 종단이 필요해지나
  > 상시 장착 시 passthrough 과종단이 되므로 릴레이 연동 스위칭 종단이 별도로 필요하다
  > (`PINMAP.md:68-70`(§5 종단 교훈 말미), `MIGRATION-orin-nx.md:99`(§4) — 둘 다 미해결로 남겨둔 상태).
  > 즉 본 런북은 도킹(=intercept) 절차서인데 그 상태의 종단 설계는 미완이다.
- **pin5 주의**: CAN0_L이며 릴레이 passthrough(fail-safe)의 L 브릿지 지점(pin5↔pin24). Seer L은 pin5에 연결 권장.

## 3. 펌웨어 확인/플래시

> ## ⛔ [2026-07-27 정정 — 이 절 그대로 실행하지 말 것] ⛔
> 아래 원문의 기대 버전 `DEV-26524538-DEBUG` 와 이 킷 폴더의 `panda.bin.signed` 는 **구버전**이다.
> 원문대로 하면 정상 펌웨어를 "버전 불일치"로 판정 → 구버전으로 되돌려 **2026-07-27 에 고친 결함이
> 되살아난다.**
>
> - **기대 버전 = 현행 빌드**. 현행 빌드 산출물의 버전 문자열은
>   `Tools/Can_Relay/panda-firmware/board/obj/version` = `DEV-d98bc1a5-DEBUG` 다.
>   (이 문자열은 빌드 시점 git HEAD 로 생성되므로 재빌드하면 바뀐다 — `board/SConscript:89-92`.
>   따라서 **문자열을 외우지 말고 그때의 `obj/version` 을 읽어 대조할 것.**)
> - 현행 빌드에만 들어있는 것: (a) 부팅 기본 250 kbps
>   (`board/drivers/can_common.h:174-176` `can_speed = 2500U`) (b) heartbeat 상실 시 릴레이 fail-open
>   (`board/main.c:257-258` `set_intercept_relay(false); pc_authority = false;`).
>   플래시·실증 기록: `docs/verified_facts/2026-07-27.md` §A-1(수정 후 재검증 — 비트레이트 미설정
>   상태에서 8초 29,625프레임, Seer `errors=[]`), `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`
>   Decision 1·2.
> - **이 킷 동봉 `Tools/docking_field_kit/panda.bin.signed` 는 2026-07-23 자 구버전이므로 플래시 금지.**
>   (md5 `d4188e02…` ≠ 현행 빌드 `174e136c…`, 2026-07-27 확인. 두 수정이 들어가기 전 바이너리다.)
>   구버전을 그대로 플래시하면 부팅 기본값이 500 kbps 로 돌아가 **250 kbps 버스를 파괴한다**
>   (verified_facts §A-1).
> - 재플래시가 정말 필요하면 현행 빌드 산출물
>   `Tools/Can_Relay/panda-firmware/board/obj/panda.bin.signed` 를 쓸 것.
> - 바이너리 파일 자체는 이력 보존을 위해 교체하지 않았다(경고만 추가).

```bash
cd ~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit
python3 flash_panda.py         # 버전 DEV-26524538-DEBUG 확인 (이미 맞으면 재플래시 불필요)
# 부트스텁 갇힘 시: python3 flash_panda.py --recover
```

## 4. 도킹 전 게이트 검증 (선택 — PCAN 있으면)
```bash
# can0/can1 250k up 후:
python3 seer_gate_bench.py          # 게이트 T1~T6 (기대 6/6)
python3 docking_scenario_bench.py   # 속임수 시나리오 (기대 6/6)
```
※ 벤치는 PCAN 필요. 실 Seer/모터만 있으면 5단계로.

## 5. 실 도킹 절차 (docking_drive.py)

> ## ⛔ [2026-07-27 정정 — 이 절차는 현재 **보류**. 실행 금지] ⛔
> 아래 절차는 **승인된 절차가 아니라 2026-07-23 시점의 이력**이다. 2026-07-25 실차에서 이 절차의
> 첫 단계(`take` = intercept 전환)에 해당하는 시험이 인시던트로 끝났다:
> - `docs/can_relay/field-record-orin-nx-2026-07-25.md:31` — intercept 전환 순간(t+2s) Seer 가
>   node3·node4 에 HOMING 설정(`0x6099=2500`) 2건 발행.
> - 같은 문서 `:68-71` — **[확정] 판다 intercept 전환은 이 실차 Seer 를 리셋시킬 만큼 교란한다
>   → 전환 무중단화(커널 can-gw 수준) 확보 전까지 실차 intercept/게이트 금지.**
> - 같은 문서 `:49` — **Seer 는 리셋되면 복구 시 항상 재호밍(steering re-home) = 조향 물리 이동을
>   동반한다(안전 직결).**
> - 같은 문서 `:54` — 현 상태 판다 intercept/게이트 방식은 **실차 비안전**.
> - 같은 문서 `:56` — 실모터 구동(`docking_drive.py`)·추가 intercept 는 **원인 규명 전까지 보류.
>   실 구동 전 사용자 확인 필수.**
>
> ⇒ 전환 무중단화 확보 **및** 사용자 승인 전까지 아래를 실행하지 말 것.
> (참고로 같은 문서 `:79-80` 은 2차 재검증(8s)에서는 무교란이었음을 기록하며 글리치가 간헐적이라는
> [가설]을 남긴다 — 즉 "한 번 잘 됐다"는 안전 근거가 되지 못한다.)
> 실 도킹이 필요하면 실차 검증된 대안 경로는 PCAN 2채널 하이브리드다(같은 문서 `:55`).

```bash
python3 docking_drive.py
```
대화형 명령:
| 명령 | 동작 |
| --- | --- |
| `take` | 주도권 PC 취득 (intercept+게이트, Seer 속임 시작) |
| `enable` | 모터 enable (구동 0x86, 조향 0x3F) |
| `f [mmps]` | 전진 (기본 50 mm/s, 저속) |
| `b [mmps]` | 후진 |
| `steer [deg]` | 조향각 (홈 기준) |
| `home` | 조향 홈 + 정지 |
| `s` / `stop` | **즉시 정지 (E-STOP)** |
| `release` | 주도권 Seer 반환 (passthrough) |
| `q` | 종료 (자동 release) |

**권장 순서**(⛔ **보류 — 위 §5 머리 경고 참조. 실행 가능한 절차가 아니다**):
`take` → `enable` → 저속 `f 30`으로 방향 확인 → 도킹 동작 → `stop` → `release`.

## 6. 안전·주의
- **저속부터**(기본 50mm/s, 첫 확인은 30). 방향(전/후·조향)이 예상과 다르면 즉시 `stop`.
- ~~**heartbeat 자동**: docking_drive.py가 죽거나 USB 끊기면 판다가 ~5초 후 fail-safe passthrough(릴레이 OFF) 복귀 → Seer 직결.~~
  > **[2026-07-27 정정 — 위 서술은 부정확]** (`docs/verified_facts/2026-07-27.md` §A-5 가 이 문구를
  > 명시적으로 "부정확"으로 판정)
  > 1. heartbeat 상실 시 펌웨어가 하는 일은 **`SAFETY_SILENT` 복귀**다 — `board/main.c:248-249`
  >    `if (current_safety_mode != SAFETY_SILENT) { set_safety_mode(SAFETY_SILENT, 0U); }`
  >    (이어서 `:260-262` power save 진입). "passthrough 복귀"가 아니다.
  > 2. **릴레이 해제(`set_intercept_relay(false)` + `pc_authority = false`)는 2026-07-27 에 비로소
  >    같은 블록에 추가된 것**이다 — `board/main.c:257-258`,
  >    `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md` Decision 2.
  >    **이 킷이 플래시하도록 지시하는 `panda.bin.signed`(2026-07-23)에는 없다**(§3 경고 참조).
  >    구버전이 올라가 있으면 heartbeat 가 끊겨도 릴레이는 intercept 로 남는다.
  > 3. **"~5초" 는 조건부다**: `board/main.c:164-165` `HEARTBEAT_IGNITION_CNT_ON 5U` /
  >    `HEARTBEAT_IGNITION_CNT_OFF 2U`, `:233` 이 `check_started()` 로 분기 ⇒ ignition on 5s /
  >    **ignition off 2s**.
  > 4. 다만 릴레이는 부팅 기본이 물리 통과이므로(`board/drivers/harness.h:91`, verified_facts §A-3)
  >    intercept 를 건 적이 없다면 버스 자체는 유지된다.
  > (값·상수는 변경하지 않았다. ADR Decision 5 는 정정 대상 파일을 열거하면서 이 RUNBOOK 을
  >  누락했으므로 여기에 직접 정정을 남긴다.)
- **release 필수**: 도킹 끝나면 반드시 `release`로 Seer에 반환해야 Seer가 다음 노드로 이동.
- **모터 호밍**: 전원 재인가 후 모터 자체 호밍 완료 뒤 enable할 것(호밍 전 명령 시 조향 잠김처럼 보임).
- 조향 부호·노드매핑은 저속 실차 확인 후 신뢰(DirectDriver 실측 기준 이식).

## 7. 문제 시
| 증상 | 확인 |
| --- | --- |
| CAN2/모터 불통 | **핀맵! CAN2_H=pin23** (pin22 死핀) — PINMAP.md |
| 모터 무응답 | 12V 인가? **판다 비트레이트 250 kbps?**(부팅 기본값 — 2026-07-27 펌웨어로 정정) 호밍 완료? *(종단은 2026-07-24 종결 — 후보 아님)* |
| Seer가 "calibrating" 루프 | 게이트 지연 — 벤치 지연 확인. (커널 게이트라 통상 μs) |
| 판다 인식 안 됨 | udev 규칙, USB 재연결, `flash_panda.py --recover` |
| 전진=크랩 | 조향 controlword 매사이클 재전송 확인(드라이버 내장) |
