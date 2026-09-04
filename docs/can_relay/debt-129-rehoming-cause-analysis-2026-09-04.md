# debt-129 재호밍 원인 분석 — 2026-09-04 (세션 67ed5a48)

> 목적: "재호밍이 왜 일어나는가" 를 근거 라벨([실측]·[코드]·[문서]·[추정])로 분리해 확정한다.
> 코드 변경 없음. 실기 실험은 §4 승인 후.

## 0. 결론

**재호밍(조향 137° 스윙) = Seer 의 조향 드라이버 재init 시퀀스
`0x6040=0x86 → 0x6099=2500 → 0x60FB:04=1(RstStart)` 가 실모터에 도달할 때 일어난다.**
Seer 는 engage 중 이 시퀀스를 **매 사이클, ~3.4 s 주기로 반복 발행**하며(PASS 회차 포함) 판다가 흡수한다.
release 순간 **진행 중이던 시퀀스가 실모터로 새는 회차**가 FAIL(잔여 ~13 %)이다.
"PASS/FAIL 의 Seer 명령이 같다" 는 이관 문서의 관찰은 맞고, 그 이유는 Seer 가 항상 재init 을 시도하고 있기 때문이다.

## 1. 사슬

| 층 | 내용 | 근거 |
|---|---|---|
| L0 드라이브 | `0x60FB:04=1` 이면 −Limit 탐색(≈31 s) 후 Seer 가 0° 로 복귀시킴 = 137° 스윙. 이미 리밋 위치면 무동작 즉시 완료 | [문서] Handbook V7.0 §4.6 "already in the resetting position … directly outputs the resetting end signal" · [실측] 07-27 캡처, `docs/homing/2026-08-03-…` §0 |
| L1 Seer 재init | `cw=0x86 → 0x100C=500 → 0x100D=1 → 0x6060=1 → 0x6099=2500 → 0x60FB:04=1` 를 node3·4 에 발행. engage 후 0.07 s 첫 발행, 이후 3.17·3.52·11.2 s 간격 재발행, 시퀀스 길이 0.17~0.95 s | [실측] 25 s engage 모니터(00:08, `englong`) · hs_ 4사이클(13:46): PASS 회차에도 cw=0x86 2~11회·60FB=1 2~6회/4 s |
| L2 흡수 | write 는 fake-ack 후 drop, 릴레이 절체로 실모터 격리 | [코드] `safety_seer_gate.h:230-238` · [실측] 13:16 격리(0.5 s 뒤 bus0 모터 0건) |
| L3 누설 | release = `0xe9=0 → 0xe8=0 → SILENT`; SILENT 뒤 판다는 응답·흡수 모두 중단, 릴레이 복귀 수 ms. 그 뒤 Seer 가 이어 보내는 시퀀스는 실모터 도달 | [코드] `orin_home_experiment.py:219-232`, `link.py:428-450`, `main.c:80-90` |
| FAIL 실측 | rel8 cyc5: 버스에 node4 `cw=0x86 → 0x6099 → 0x60FB:04=1` 이 실리고 node4 pos→0(리밋), node3 은 `0x100C` 한 건만 = **시퀀스가 release 를 걸쳐 잘린 형태** | [실측] `Log/rel8_260904_134736.jsonl` seg5 |
| 확률 | 시퀀스 0.2~0.9 s / 주기 ~3.4 s ≈ 6~25 % ↔ 실측 13~25 % | [추정] |

## 2. 미확정 — L1 의 트리거 (Seer 가 engage 중 왜 재init 을 반복하는가)

후보(택일 미확정):
- (a) engage 전이 글리치로 첫 재init(0.07 s) → Seer 재연결 타이머 재시도. 단 emulate 응답이 만족스러우면 재시도가 멈춰야 하는데 안 멈춤 → emulate 의 어떤 응답이 Seer 주기 검사(`_checkOperationalT`)를 못 넘긴다 [추정].
- (b) node4 EMCY `0x8110`(CAN overrun) 폭주: 오늘 릴레이 fix 이후 런 중 **FAIL 회차 chunk 에서만 56건**, PASS 회차 0건. 과거 intercept soak 에서도 node4 0x8110 다수(soak_10_10 340건·tab2 181건). EMCY(0x084)는 bus2→bus0 로 포워딩된다 [코드 fwd_hook bus2 분기] → Seer 가 이를 보고 node4 재init 을 결심했을 수 있다 [실측+추정].
- (c) 실드라이브 statusword 는 정상 운전 중에도 `0x9450/0x1050/0x1450/0x0050` 을 오가는데 emulate 는 상시 `0x9450` [실측 오늘 로그 분포] — Seer 검사와의 관계 미확인.

확정 방법: engage 25 s 동안 bus0 전 프레임(요청·응답 쌍, 판다 `can_recv` bus 필터 없이) + 매 재init 직전 Seer 가 읽은 객체·값 + `get_alarms()` 타임라인.

## 3. 새로 확인한 교란 — 하네스 방향이 부팅마다 랜덤

- [코드] `harness_init()` 이 부팅 시 PC0/PC3 ADC 로 방향을 판정한다(`harness.h:54-66`, 임계 2500). 이 보드는 PC0=CAN3_EN, PC3=미연결이라 결과가 부팅마다 흔들린다 — 이전 세션이 "1/2 로 흔들림" 을 관찰했고, **지금 health `car_harness_status=2`(FLIPPED)** 다(14:4x 판독, 펌웨어 903a9b3, SILENT idle).
- FLIPPED 일 때 두 가지가 동시에 일어난다:
  1. `black_init()` 이 `can_flip_buses(0,2)` → 논리 bus0↔bus2 교체(`black.h:166-168`, `can_common.h:167-172`). emulate 응답(bus0 송신)이 **모터측 트랜시버**로 나가고 Seer 요청은 bus2 로 들어와 `bus2 && 0x600~0x604 → drop`. Seer 는 무응답.
  2. `0xe8` 의 `set_intercept_relay()` 가 **PC10**(릴레이핀)을 `!intercept` 로 구동(`harness.h:29-31`, `black.h:179-180`) → engage 시 LOW(릴레이 OFF), release 시 HIGH. `set_safety_mode` 의 push-pull 제어와 정반대.
- NORMAL(1) 이면 `set_intercept_relay` 는 **PC11** 을 구동하는데 도면상 PC11 은 미연결(`CAN RELAY R02.pdf`: RELAY 넷은 PC10 만) → 무해. NC(0) 면 아무 것도 안 함.
- ⇒ 이관 문서의 "**0xe8 의 set_intercept_relay 가 cut 에 필수**" 는 **미검증**이다. 근거였던 e8 실험(0/8)은 ① set_intercept_relay 제거 ② release cover 제거를 **동시에** 바꿨고 ③ 플래시 재부팅으로 방향이 바뀌었을 수 있다.
  `Log/e8_260904_135849.jsonl` 은 8사이클 전부 bus2 에 **Seer 요청만 있고 모터 프레임 0**(다른 런은 모터 응답·guard 가 보임) — FLIPPED 부팅에서 bus2 가 Seer 선에 붙은 서명과 일치한다 [실측].
- 예측: **현재 부팅(FLIPPED)에서 커밋 펌웨어로 engage 하면 cut/emulate 가 깨져 재호밍 ~100 %** 일 것. 이관 문서의 "~13 %" 통계는 NORMAL/NC 부팅에서만 얻은 값이다.

## 4. 다음 단계 (실기 — 승인 후)

- E1 현재 FLIPPED 부팅 그대로 1사이클(take 4 s → release) → health·bus2 서명·steer 로 §3 예측 검증. (재호밍 1회 각오)
- E2 engage 시간 3.3 / 4.0 / 6.0 s × 8회 → FAIL 률이 engage 시간에 따라 달라지면 L3(straddle) 확정, 무관하면 release 전이 자체가 트리거.
- E3 bus0+bus2 연속 캡처(bus 필터 없이, 2 ms 폴) + 매 사이클 `get_alarms()` → §2 트리거 택일.
- 수정 방향(제안, 승인 전): ① 방향 판정 무력화(`car_harness_status` 를 NC 로 고정 또는 flip·relay 호출 제거) — 교란 제거가 선행; ② release 를 "Seer 재init write 미관측 300 ms" 조건에서만 수행(펌웨어가 `0x6099/0x60FB/0x6040=0x86` 을 보고 판단) — L3 차단; ③ L1 트리거 확정 후 emulate 보정.

## 5. 이 분석이 쓴 자료
- `Log/{rel,rel2,hs,rel8,sw8,sw16,e8,rv4}_260904_*.jsonl`(Rig bus2 RX 로그, drain 시각 타임스탬프 — 순서만 신뢰)
- 이전 세션(44fa6711) 실험 출력(25 s engage 모니터·hs_ 4사이클·e8/rv4 결과)
- `Tools/Can_Relay/panda-firmware/board/{safety/safety_seer_gate.h, usb_comms.h, main.c, drivers/harness.h, boards/black.h, drivers/can_common.h}`, `python/__init__.py`
- `Tools/Can_Relay/R02/CAN RELAY R02.pdf`, Handbook V7.0 §4.6, `docs/homing/2026-08-03-can-relay-homing-assets.md`

## 6. E1 실기 결과 (2026-09-04 15:26, 현재 FLIPPED 부팅, 로그 `Log/e1_all_260904_152648.jsonl`)

- **재호밍 판정 2.396 rad, 신규 알람 52106·52111(Motor[1][2][3][4])** — §3 예측대로 FLIPPED 부팅에서 intercept 가 깨졌다.
- engage 4 s 캡처(양 버스, bus 필터 없음): 같은 프레임이 bus0·bus2 **양쪽에 RX** = 두 트랜시버가 한 선(절체 없음).
  0xe8=1 이 FLIPPED 에서 PC10 을 LOW 로 되돌려 릴레이가 안 붙었다.
  판다는 브리징 상태(emulate 미작동)라 bus0→bus2→bus0 로 **자기 포워딩 루프**가 생겨 `0x582` 응답 4016건·node4 EMCY `0x8110` 3937건이 4 s 동안 순환(≈1000 f/s) → 버스 포화 → Seer 요청은 53건만 통과 → 52111.
- release 뒤 캡처: bus2 에 Seer 요청 1000 f/s·guard RTR 만 있고 응답 0, bus0 무음 = **Seer↔모터 절단 상태**.
  원인 = `main.c` SILENT 분기가 `set_gpio_output(PC10,false)` 뒤에 `set_intercept_relay(false)` 를 불러 FLIPPED 에선 PC10 이 다시 **HIGH(릴레이 ON=절체)** 가 된다.
- **정정:** 이 절단은 E1 이 만든 것이 아니다. E1 전 baseline 알람에 52111 `Motor[1][2][3][4]` 가 **14:01:32 부터 활성**이었고 steer [0.0,0.0] 은 Seer 의 stale 값이었다. 즉 이전 세션이 "SILENT idle 로 안전하게 두었다" 고 한 14:09 부팅(FLIPPED) 이후 로봇은 계속 Seer 와 분리돼 있었다.
- 복구 수단(FLIPPED 부팅 한정): SILENT 상태에서 USB `0xe8 wValue=1` → `set_intercept_relay(true)` → PC10 LOW → 릴레이 OFF → passthrough. 판다 리셋은 방향이 다시 랜덤이라 보장 없음. 근본 수정 = 펌웨어에서 방향 판정·`set_intercept_relay` 를 이 보드용으로 무력화(승인 필요).

## 7. 근본 수정 (2026-09-04 17:12 빌드 완료, 플래시·검증 대기)

- ADR: `docs/adr/2026-09-04-canrelay-harness-orientation-neutralize.md`.
- `board/boards/black.h`(git 미추적) 변경 3곳 — 재적용용 원문:
  1. `harness_init();` → `car_harness_status = HARNESS_STATUS_NC;` (주석: 이 보드는 하네스 없음, 판정 생략·NC 고정, 릴레이 PC10 은 set_safety_mode 만 제어)
  2. `black_init()` 말미의 `if (car_harness_status == HARNESS_STATUS_FLIPPED) { can_flip_buses(0, 2); }` 삭제
  3. `black_harness_config.has_harness = true` → `false`
- 빌드: `scons -u -j4` PASS(-Werror), `board/obj/panda.bin.signed` 31,172 B, md5 `1f9fe50b348c346d3925818e725ace65`.
- 롤백 이미지: `Tools/Can_Relay/fw_backups/panda-903a9b3-pushpull-flipped_2026-09-04.bin.signed` (md5 `8aa53270…`).
- 플래시: `python3 <scratchpad>/flash_dfu_direct.py` (4e002c 앱모드 가드) — 세션 권한 분류기가 차단해 사용자 실행 필요.

## 8. 근본 수정 후 실측 (2026-09-04 17:16~17:23, 펌웨어 DEV-8dcca835 = black.h 하네스 판정 NC 고정)

- 플래시 직후: health harness=0·safety=0, 양 버스에 요청·응답 동시 관측(passthrough), Seer 오류 0, 조향 2.396→0 rad 30 s 복귀. 리셋 2회 뒤에도 harness=0.
- 1사이클(`Log/e1_all_260904_172049.jsonl`): engage 중 bus0 = Seer 요청 2888·guard 320 만, bus2 = 모터 응답 1762·guard 320 만, EMCY 0, 루프 0. release 뒤 passthrough·알람 0·재호밍 없음.
- 사이클 런(`Log/e2_events_260904_{172209,172446,172735}.jsonl`): 4 s engage 8+16회, 6 s engage 8회 = **32/32 PASS**, engage 중 Seer 조향 재init 쓰기(0x86/0x6099/0x60FB/0x6060/0x100C/0x100D) **0건**, EMCY 0, 신규 알람 0. 1사이클 캡처 포함 **누적 33/33**.
  ⇒ 종전 13~25 % FAIL 률이면 33연속 PASS 확률 ≈ 1 % 미만. 이전 부팅에서 매 사이클 보이던 L1 재init 시도(§1)가 이 펌웨어에서는 관측되지 않는다.
- [미확정] 왜 사라졌는가: 코드상 NORMAL 부팅과 NC 의 CAN 경로 차이는 없다(`ignition` 은 heartbeat 임계·USB 전원만 가른다).
  이전 런은 부팅별 health 를 기록하지 않아 그 부팅들이 실제로 NORMAL 이었는지 확인할 수 없다. engage 4 s/6 s 모두 0건이라 §1 L3 의 straddle 가설은 검증 대상이 사라졌다(재init 시도 자체가 없음). 종결 조건: 24 h 내구 런에서 재호밍 0.
- 스크립트 주의: `e2_cycles.py` 의 `leak` 카운터(≈330/사이클)는 take 직전 RX 큐 backlog(bulk read 1,100건 한도로 flush 미완)라 실제 누설이 아니다. 실제 분리 여부는 위상 분리 캡처(`Log/e1_all_260904_172049.jsonl` eng 단계: bus0 응답 0·bus2 요청 0)로 확인했다.
- **100사이클 확인 런(17:32~17:51, `Log/e2_events_260904_173240.jsonl`, 4 s engage)**: **100/100 PASS**, 재init 쓰기 0, EMCY 0, 신규 알람 0, 매 사이클 release 뒤 passthrough 복귀 확인(요청·응답 동시 관측)·harness=0·safety=0. 누적 **133/133**.
  종결 판정: 사용자 기준(100회)을 충족해 debt-129 해결. 24 h 내구는 선택 과제로 남긴다.

## 9. bus2 로봇 제어기(배포 ROS2 노드) 단계 검증 (2026-09-04 17:55~18:03)

배포 노드 `can_relay_node`(Big-AMR-deploy 05c77ed, 도메인 125)로 판다 bus2 를 통해 PC 가 모터를 구동했다. 펌웨어 DEV-8dcca835.

| 단계 | 조작 | 관측 |
|---|---|---|
| hold | `~/engage true` 13.5 s(구동축 브링업 10프레임·0x60FF=0 20 Hz·폴 5 Hz) → `~/engage false` | Seer 알람 0, release 뒤 재호밍 0 |
| 조향 | `~/steer_deg` 10.0 → 0.0 | m3/m4 fb_pos −5/−297 → **573,435/573,143**(10°×57,344=573,440) → −5/−297. Seer steer_angles 는 0.0 유지(emulate 가 가림) |
| 구동 | `~/drive_mmps` 50 @10 Hz 1.2 s → `~/stop` | m1/m2 fb_vel **1298/1246**(0.1 rpm; 50 mm/s×24.447≈1222), pos +187k counts. 워치독 만료 로그 정상 |
| 반환 | 조향 0°·구동 0 확인 후 `~/engage false` | Seer 알람 0, 재호밍 0, Seer 포즈 x −7.1745 → −7.2422 m(=−6.8 cm, 레이저 측위가 실제 이동을 반영) |

⇒ 릴레이 절체·emulate·bus2 구동·반환이 배포 노드 경로에서 성립한다. 조향 지령 거부 0건(`require_homed_for_steer=True`, 드라이브 bit15 신선 판정 통과).
남는 관찰 과제: Seer 는 engage 중 이동을 오도메트리로 보지 못하므로 반환 뒤 측위가 보정될 때까지 포즈가 튄다(설계상 예상). 도킹 시나리오에서는 반환 전 조향 0°·정지가 필수.

## 10. bus2 제어기 확장 검증 — 전진·후진·크랩 좌우·호밍 (2026-09-04 18:05~18:12, 배포 노드)

| 묶음 | 조작 | 관측 |
|---|---|---|
| A 전진·후진 | 조향 0°, `drive_mmps` −50 1.5 s → +50 1.5 s | m1/m2 vel −1225/−1211 → +1231/+1233(0.1 rpm), pos 347k→120k→347k(왕복 정합). raw 음수=전진(2단계 +50 단독 이동에서 Seer x −6.8 cm 로 확인) |
| B 크랩 좌우 | 조향 30→60→90°(각 1~2 s 도달, m3/m4 5,160,654/5,160,355 ≈ 90°×57,344), +50 1.5 s → −50 1.5 s, 60→30→0° 복귀 | 구동 pos +228k → −227k 왕복, 조향 0° 복귀 m3 −5/m4 −297 counts. 좌우 방향 라벨은 [[biguamr-motor-node4-sign-crab]](+90°+양수=+y 왼쪽) 기준, 이번엔 왕복이라 Seer 포즈로 미측정 |
| C 호밍 | `~/home`(펌웨어 시퀀서, 기본 2500) | ENABLE→SET_SPEED→WAIT 31 s→RESTORE→GOZERO_W→DONE, 39 s, reached_mask=0x03. 직후 low_state m3 +10,206(정착값 +0.178° 정합), m4 −7,840,092 는 **raw 0 일시 샘플**(수동 판독으로 raw 7,840,091 = 홈 +5 counts 확인) |
| 각 반환 | `~/engage false` | 세 묶음 모두 Seer 알람 0·재호밍 0, 반환 뒤 Seer 가 정착값을 0° 목표로 되돌림(수동 판독 node3 +8·node4 +5 counts, sw 0x9450) |

⇒ 사용자 요청 범위(4방 크랩·전진·후진·호밍) 전부 배포 노드 경로에서 성립. 주의: engage 중 Seer 포즈는 갱신되지 않고 반환 뒤 레이저 측위로 보정된다.

## 11. 핸드오버 복원 시퀀서 (펌웨어, 2026-09-04 18:16 플래시 md5 639b4654…)

사용자 결정으로 "반환 전 획득 시 포즈(Seer 마지막 목표) 복원" 을 펌웨어가 소유한다(ADR 2026-09-04-canrelay-handover-restore-sequencer).

| 검증 | 결과 |
|---|---|
| (a) 노드로 조향 +30° 뒤 `~/engage false` | 0xec: RESTORE(src=host, SILENT 보류) → 2.0 s 도달(res=1) → SETTLE → IDLE·auth 0·safety 0. 조향 raw 홈 +0.000°. Seer 알람 0·재호밍 0 |
| (b) Rig engage 후 heartbeat 중단(release 없음) | 1.2 s 뒤 fail-safe 가 시퀀서 요청(src=2) → 1.4 s 도달 → SETTLE → SILENT·auth 0. 조향 홈 +0.000°. Seer 알람 0. (사전 변위는 node4 +4.8° 만 확인됨 — Rig 단발 SDO 쓰기 유실 가능) |
| (c) hold 10사이클 회귀 | 10/10 PASS, 재init 0·EMCY 0·알람 0, 매 사이클 passthrough 복귀·safety 0 |
| (d) 반환 0.5 s 뒤 재engage(가드 펌웨어 md5 0eee6d66…) | engage 성공·권한 8 s 유지·정상 반환 시 홈 복원. RESTORE 중 중단 경로는 타이밍상 미재현 |
| (e) 회귀 3사이클 | 3/3 PASS |
