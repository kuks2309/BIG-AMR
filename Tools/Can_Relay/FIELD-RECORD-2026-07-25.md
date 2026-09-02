# CAN Relay 현장 기록 — Ford-CATL-orin-nx (Big-AMR)

> 작성 2026-07-25 (KST) · 대상 로봇 PC: **Ford-CATL-orin-nx** (Jetson Orin NX, aarch64/Ubuntu22.04/py3.10, `ssh nvidia@100.92.214.74`)
> 성격: 이 로봇의 **현장 배치·검증 기록**(field record). 심층 설계 근거(ADR·설계문서)는 `T-Driver-Analysis/docs/` 및 GitHub `kuks2309/CAN-Relay` 저장소 원본을 정본으로 참조.
> 표기 규칙: `[실측]`=명령/로그로 관측 확인, `[가설]`=미확증 추정(확정 금지).
>
> ⚠ **2026-07-27 기록 감사(A09) 적용본** — 아래 본문에는 원문을 지우지 않고 `⚠ 정정`/`⚠ 조건`/`⚠ 미판정 모순`
> 주석을 **append** 했다. 대상 줄: §5-2(:47 폴 레이트·단절모델), §5-4(:49 "항상 재호밍"), §6(:53 heartbeat 임계),
> §8(:71 "[확정]"), §11(:92 debt id), §13(:123-125 11ms), §14(:137 "완전 해결", :139 "물리 모션 없음").
> 값·숫자·결론 문장은 **변경하지 않았다**(실측 없이 값 변경 불가). 정정문의 근거는 모두 `파일:줄` 로 인용한다.
> ⚠ 정정문 안의 **자기-참조 `:NN` 은 감사 전(원본) 줄번호** 기준이다(정정 append 로 현재 줄번호는 밀렸다).
> 절 번호(§n)를 함께 적었으니 **절 기준으로 찾을 것**. 외부 파일 인용(`docs/…`, `board/…`)은 2026-07-27 시점 현재 줄번호다.
>
> ⚠ **쌍둥이 문서 주의** — 이 파일은 감사 착수 시점(2026-07-27) `docs/can_relay/field-record-orin-nx-2026-07-25.md` 와
> **바이트 동일본**이었다(diff 0). 이번 감사에서 담당 영역(`Tools/Can_Relay/`)만 정정했고, 같은 시각 다른 담당자가
> 그 사본을 별도로 정정했으므로 **두 사본은 이미 갈라져 있다**(양쪽 정정을 합쳐 읽을 것).
> 다른 문서가 `docs/can_relay/field-record-orin-nx-2026-07-25.md:47,137` 식으로 인용할 때는 이 사본의 정정을 함께 볼 것
> (예: `docs/issues_and_fixes/issues_and_fixes.md:70`). 동기화는 별도 작업.

---

## 1. 이식 완료 상태 (2026-07-25) [실측]

- 킷 위치(둘 다 복사): `~/Project/Ford-CATL-AMR/T-Driver-Analysis/tools/docking_field_kit/` + `~/Project/CAN-Relay/docking_field_kit/`
- 의존성: `libusb-1.0-0`(apt, 기설치) + `libusb1`(pip 3.4.0, `python3 -m pip`로 설치 — `pip3` 명령은 PATH 밖)
- udev: `/etc/udev/rules.d/12-panda-all.rules` = `idVendor==bbaa` 전체 0666 (사용자 원격컴 직접 적용). sudo는 비밀번호 필요.
- 판다: `bbaa:ddcc`(앱모드), serial `1e003e001351333033383534`(판다 #2, 우리 펌웨어). 펌웨어 버전 **DEV-26524538-DEBUG 일치**(재플래시 안 함 — `flash_panda.py`는 무조건 재플래시 구조라 버전만 읽음), safety_mode 0.
- 시계: RTC/NTP 동기 정상(진단 시점의 1970 아님).

## 2. 현재 가동 — passthrough 릴레이 상시 + 워치독 [실측]

- 판다 safety_mode 0 = SILENT/passthrough. Seer↔모터 하드웨어 중계 상시 가동.
- 라이브 트래픽 ~3200fps, Seer 폴링 ≈ 모터 응답 1:1. `amap2_canhealth.py`: **bus0·bus2 per-bus 에러 0, esr=0x0**(수시간 무재발). 종단 60Ω 정상(Seer 끝 120Ω 확인, MIGRATION §4).
- 워치독 `amap2_canhealth_watchdog.py` setsid 상주, 로그 `~/docking_reliability/`.
- 운영 팁: 워치독을 pkill 할 때 `pkill -f amap2_canhealth_watchdog` 는 **패턴이 자기 명령줄에 포함돼 자기 셸까지 죽여 SSH가 끊긴다.** 브래킷 트릭 사용: `pkill -f "amap2_canhealth_wat[c]hdog"`.

## 3. HIL 검증 (실차, 정차·attended) — 단계·결과 [실측]

공통 중단조건: per-bus 에러 / Seer 재호밍(homing write) / 모터응답 끊김 → 즉시 passthrough 복귀.

| 단계 | 명령 | 결과 |
|---|---|---|
| **H0 베이스라인** | `amap2_monitor.py monitor 20` (SILENT 리슨) | ✅ 정상. Seer폴링 29193/응답 29192, 재호밍 0·구동 0·누출 0, 정차 position-hold. |
| **H1 투명 릴레이 삽입** | `amap2_monitor.py gate 20` (intercept + auth=Seer 투명) | ⚠ **점검필요 → 인시던트(§8).** intercept 전환 순간(t+2s) Seer가 node3·node4에 HOMING설정(0x6099=2500) 2건 발행. 응답 25912(폴링 26343보다 431 적음=전환구간 손실). 사후 per-bus 에러 0(버스·종단 정상). |
| H2 게이트 차단 | (미실행) | H1 인시던트로 **HIL 전면 중단.** |
| **오늘 앞선 gatecheck** | `amap2_monitor.py gatecheck 15` (intercept+auth=PC, 무구동) | Seer write(0x2B controlword=0x3F, 0x23 target_position)가 모터측 누출. 게이트가 활성 유지 못하고 passthrough fall-back한 것으로 추정([가설]). |

## 4. 두 구현 대비 (기록 근거)

| 구현 | 게이트(쓰기차단+가짜ack) 검증 상태 | 근거 |
|---|---|---|
| **PCAN 2채널 하이브리드** (리눅스 PC + PCAN-USB Pro FD 2ch, SocketCAN) | **실 Seer+실 모터 실차 도구로 성숙**(drive_gui 실주행·E-STOP·2단계발진·에코차단 `-f 600~780`·가짜ack). ADR Accepted. 평시 통과=**커널 can-gw(μs, 무중단)**. | `T-Driver-Analysis/tools/can_relay/README.md`, `T-Driver-Analysis/docs/adr/2026-07-09-relay-authority-arbitration.md`, 원본킷 `.../experiements/2026-07-08_pcan-relay-linux-handoff/` |
| **판다 펌웨어 #C seer_gate** (PCAN 게이트를 STM32 펌웨어로 포팅) | **가짜노드 PCAN 벤치 40만회 0실패**(reliability-24h Run1/2). **실차 미검증** — 오늘 실차서 §3·§8 문제. | `CAN-Relay/docs/adr/2026-07-20-panda-docking-firmware.md`, `CAN-Relay/docs/can_relay/reliability-24h-results.md`, `CAN-Relay/docs/can_relay/relay-separation-design.md` |

게이트 스펙은 두 구현 동일: Seer 쓰기(0x23/27/2B/2F) drop + 가짜ack(0x580+N) + 읽기(0x40)·guard RTR 통과 + PC 명령 에코 역차단. 이 스펙은 PCAN 쪽에서 **실차로 검증**됨.

## 5. Seer 실측 교훈 (PCAN 구현 기록에서) [실측 기록]

1. **유저스페이스 릴레이 지연 p99 57ms → Seer "motor is calibrating" 루프 유발** → 평시 통과는 반드시 커널 can-gw(μs급). Seer는 지연 민감.
2. **Seer 단절 감지 모델**: STM32 Seer는 고정레이트 fire-and-forget 폴링(조향 0x6064 읽기 100Hz·guard RTR 80Hz 불변, 쓰기만 47→8/s 축소). → **읽기·guard 응답만 유지되면 Seer는 단절 미인지·재호밍 안 함.** 정상 SDO 왕복 0.9ms(p99 1.2ms).
   - ⚠ **미판정 모순 (0x6064 폴 레이트)** — 본 줄 `100Hz` vs `docs/verified_facts/2026-07-27.md:78` 실측 **노드당 약 227~243Hz**(12초 집계에서 node1 2920·node2 2908·node3 2720·node4 2718 회, 절차는 같은 문서 :70-71 "비트레이트 정합 후 12초간 판다 RX bus0 0x601~0x604 cmd 0x40 집계", 재현 스크립트 명시). 약 2.3~2.4배 차이. **어느 값도 이번 감사에서 고치지 않았다** — 본 줄은 PCAN 구현 시절 기록이라 측정 조건(비트레이트·펌웨어·intercept 여부)이 문서에 없고, 두 측정이 애초에 다른 조건일 가능성을 배제할 근거가 없다.
     **판정에 필요한 측정**: ① 동일 조건(250kbps 정합·제어권 미획득·passthrough)에서 60초 bus0 `0x40` 프레임 노드별 계수, ② intercept/게이트 유지 중 동일 계수(= "불변" 주장 검증 — 현재 "불변"의 근거는 어느 쪽 문서에도 없다), ③ guard RTR(`0x70x`) 계수(80Hz 주장은 양쪽 모두 계수 데이터 없음 → 판정 불가).
   - ⚠ **근거 미첨부 + 확장 오용 이력 ("읽기·guard 응답만 유지되면 … 재호밍 안 함")** — 이 절은 `[실측 기록]` 라벨이지만 이 문장에 붙은 원시 근거(캡처·로그·`파일:줄`)가 이 저장소에 없다(모델 서술). 그럼에도 하중을 받는 근거로 재사용된다: `docs/issues_and_fixes/issues_and_fixes.md:70` 이 "근거모델: field-record …:47,137" 로 인용.
     오용 사례(반증 확정): `docs/claude-mistake/2026-07-26-001_emulate-stopvalue-false-claim.md:14-19` — 이 줄(§L47)만 믿고 "emulate 펌웨어가 이미 요구(정지값 송신)를 충족" 이라 확정했다가, 실구동에서 **55602(motor following warning)** 발생 + 소스 확인 결과 emulate 는 정지값이 아니라 **실위치를 그대로 relay** 함이 드러남(정지값 고정 로직 부재). 문서 분석("재호밍 안 함")과 요구("정지로 인식")를 동일시한 논리 비약이 원인이라고 같은 문서 :40-41 이 기록.
     또한 **"재호밍 안 함" 은 응답 유지가 실제로 성립할 때만** 참이다. 전환 순단 시에는 성립하지 않는다 — `docs/issues_and_fixes/issues_and_fixes.md:69-70`(첫 engage 전환 순간 수초 모터 통신 순단 → 52111/52106 → 자동 재호밍 54301).
     ※ `docs/claude-mistake/2026-07-26-001…:6-8,44-45` 는 "field-record 에 emulate 실동작 정정을 기록" 을 `reflected_assets` 로 약속했으나 대상 문서에 반영돼 있지 않았다(`emulate`/`55602`/`정지값` 문자열 0건, 2026-07-27 확인) → 본 감사에서 위와 같이 정정 기록으로 대신 남긴다. 모델·값 자체는 재측정 전까지 변경 금지.
3. 가짜 ack는 Seer가 자기 쓰기 ack 소실을 감시할 경우 대비한 2단계 보완으로 실제 채택.
4. **[실측·현장 → ⚠정정: 현장 관측 1회·보수적 가정] Seer는 리셋되면 복구 시 항상 재호밍(steering re-home)** 한다 = 리셋 유발은 반드시 조향 물리 이동을 동반(안전 직결).
   - ⚠ **라벨 정정** — "항상"(전칭)인데 근거는 §8(:68-70)의 2026-07-25 14:29 현장 관측 **1회**뿐이고, 그 관측조차 ":70 사용자 \"정상복구됨\" 확인" 수준으로 **재호밍 자체의 로그·알람 코드가 인용돼 있지 않다**. 반대로 재호밍이 로그로 포착된 사례는 리셋이 아니라 **통신 순단 경로**다 — `docs/issues_and_fixes/issues_and_fixes.md:70`(52111 motor timeout·52106 odo lost → 54301 calibrating → 52954). 즉 트리거가 "리셋" 하나로 단정돼 있다.
   - 결론(안전측)은 **유지**한다: 재호밍 트리거는 리셋뿐 아니라 **모터 응답/guard 상실**도 포함하므로 오히려 범위가 넓다. 반증 전까지 "리셋·통신 상실 시 조향 물리 이동 가능"을 보수적 가정으로 둔다.

## 6. 미해결 / 다음 단계

- **[가설] 판다 게이트 실차 누출 원인**: 게이트가 실차에서 활성 유지 못하고 passthrough로 fall-back(누출 프레임이 게이트 drop 대상에 정확히 포함 → 게이트 활성 시 차단됐어야 함). 확증은 실차 로그 필요. 문서상 후보: heartbeat(`0xf3`) 유지 실패 시 5s fail-safe → passthrough (relay-separation-design §4), relay_malfunction (`safety.h:245` `stock_ecu_detected`, §5).
  - ⚠ **조건 누락 (5s 단정)** — 펌웨어 임계는 **점화(ignition) 상태에 따라 갈린다**: `Tools/Can_Relay/panda-firmware/board/main.c:164-165` `HEARTBEAT_IGNITION_CNT_ON 5U` / `HEARTBEAT_IGNITION_CNT_OFF 2U`, 판정은 :233 `heartbeat_counter >= (check_started() ? ON : OFF)`. **본 실기는 ignition off 기준 = 2s** (같은 문서 §12:102 가 "임계 2s@ignition off" 로 기록). 원출처 `docs/can_relay/relay-separation-design.md` 도 :85 에서는 "hb손실 5s(ON)/2s(OFF)" 로 조건을 붙였으나 :90,:92 에서는 "5s" 만 남아 있어 같은 누락이 있다.
  - ⚠ **이 후보 진단 자체가 정정됨** — 본 문서 §12:106 "앞선 §3·§6·§8의 heartbeat 2초 레이스/주기 진단은 부정확했음. 진짜 원인은 **0xf3 전송이 fail-safe 를 되살려 릴레이를 passthrough 로 내림**". 본 줄(§6)에는 그 정정 표시가 없었으므로 여기 명시한다.
  - → PC heartbeat 주기 설계는 **2s 기준**으로 재확인할 것(5s 가정 금지).
- **[실측·확정] 판다 intercept 전환은 이 실차 Seer를 교란**(§8) — 전환 글리치가 Seer homing → 리셋 유발. **현 상태 판다 intercept/게이트 방식은 실차 비안전.**
- **검증된 fallback**: 실 로봇 도킹이 필요하면 **PCAN 2채널 하이브리드가 실차 검증된 안전 경로**(무중단 커널 can-gw).
- 실모터 구동(`docking_drive.py`)·추가 intercept는 원인 규명(라이브 개입 없이 설계·기록 분석) 전까지 보류. 실 구동 전 사용자 확인 필수.

## 7. 근거 문서 인덱스

- 이식 가이드: `docking_field_kit/MIGRATION-orin-nx.md`
- 판다 펌웨어 설계: `CAN-Relay/docs/adr/2026-07-20-panda-docking-firmware.md`, `.../relay-separation-design.md`
- 24h 벤치 결과: `CAN-Relay/docs/can_relay/reliability-24h-results.md`
- 종단 이슈: `CAN-Relay/docs/issues_and_fixes/issues_and_fixes.md`(2026-07-24 Seer끝 120Ω)
- PCAN 하이브리드: `T-Driver-Analysis/tools/can_relay/README.md`, `T-Driver-Analysis/docs/adr/2026-07-09-relay-authority-arbitration.md`

## 8. 인시던트 — HIL H1 intercept → Seer 리셋 (2026-07-25 ~14:29) [실측]

- **경위**: H0 통과 후 H1(`amap2_monitor.py gate 20`, intercept+auth=Seer 투명) 실행. intercept 전환 순간 Seer가 node3/4 HOMING설정 발행(§3) → **Seer 리셋 발생**(사용자 현장 관측 보고).
- **대응**: 판다 즉시 강제 passthrough(auth=Seer·relay off·safety 0) → Seer 직결 복원. HIL 전면 중단. canhealth 6s = per-bus 에러 0, Seer 재폴링 확인. 워치독 재상주(읽기전용).
- **복구**: 사용자 "정상복구됨" 확인. 워치독 14:33 로그 3279fps·누적이상 0. **단, Seer는 복구 시 항상 재호밍(§5-4) → 조향 물리 이동 동반됨.**
- **결론**: [확정 → ⚠정정: 실측 1회·조건부] **판다 intercept 전환은 이 실차 Seer를 리셋시킬 만큼 교란한다.** 원인은 전환 글리치([가설]: 스위칭 순간 프레임 손실/지연). per-bus 에러 0이므로 종단·물리신호 문제 아님. → 실차 intercept/게이트는 **전환 무중단화(커널 can-gw 수준) 확보 전까지 금지.**
  - ⚠ **라벨 정정 — 무조건 아님(조건부·간헐)**: 표본은 §8 14:29 **1회**다. 같은 문서 :80 은 "표본 2회(1 나쁨/1 좋음)"로 **[가설] intercept 전환 글리치는 간헐적**이라 하고(**반례 존재**: :79-80 의 2차 8s 전환은 신규 알람 0·재호밍 0·Δ8 무교란), :123 은 메커니즘을 "**in-flight SDO 트랜잭션이 깨지면** … in-flight 없으면 무사(=간헐성)"로 조건부라 밝힌다. 즉 "전환하면 리셋된다"가 아니라 "**전환 순간 in-flight SDO 가 있을 때**"다.
  - 안전 결론(전환 무중단화 전까지 금지)은 **유지**한다. 간헐이라는 사실은 위험을 낮추지 않는다(1회로 실차 리셋·물리 재호밍 발생).
  - 같은 표본을 승계하는 §6:54 "[실측·확정] … 현 상태 판다 intercept/게이트 방식은 실차 비안전" 도 동일하게 **1회 표본 기반**임에 유의.
- **교훈**: 실차 릴레이 검증은 라이브 intercept로 시행착오하지 말 것. 우선 (a) 설계·기록 기반 원인 규명, (b) 검증된 PCAN 무중단 경로 활용.

## 9. Seer API 직접 모니터 + 릴레이 재검증 2차 (2026-07-25 ~14:55) [실측]

- **Seer TCP API 접속**: 192.168.44.82(orin wlan0 192.168.44.30/24), ping ~5ms, SEER Robokit API 포트(19204 status 등) 전부 open. 로봇 **Foil_A082, RBK v3.4.5.22**.
- **CAN 개입 없이 Seer 알람 직접 조회**: SEER API **1050**(`robot_status_alarm`, 포트 19204) → fatals/errors/warnings/notices. 근거: `~/T-Robot_seer_gui`(github kuks2309/T-Robot_seer_gui) `seer_core/client.py`(16B 헤더 0x5A+JSON, 응답=요청+10000) + `T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md`(타 저장소)(SEER wiki https://seer-group.feishu.cn/wiki/ 추출).
- **도구 신규**: `docking_field_kit/seer_can_monitor.py` — API 1050 폴링(0.4s), CAN/모터 알람코드(52111 motor driver connection error, 52106 odo, 52116 network break, 52130~52135 모터폴트, 52136 chassis speed timeout 등) 신규 발생 실시간 포착. 읽기 전용(제어권 미취득). (주의: "can" 부분매칭 오탐 방지 위해 단어경계 정규식 사용.)
- **재검증 2차 (Seer 모니터 병행)**: `seer_can_monitor.py 25` 백그라운드 + `amap2_monitor.py gate 8`(intercept 8s). 결과 **모두 정상** — 신규 CAN/모터 알람 **0건**, 재호밍 **0**, 모터응답 손실 **Δ8**(경미), 최종 Seer fatals 0·모터errors 0·e-stop 없음(잔존 errors=레이저 52102/52103, 별개 이슈).
- **[가설] intercept 전환 글리치는 간헐적**: 1차(14:28, 20s, Δ431 → Seer 리셋·재호밍) vs 2차(14:55, 8s, Δ8 → 무교란). 표본 2회(1 나쁨/1 좋음). 신뢰 안전엔 전환 무중단화(PCAN 커널 can-gw 수준) 필요.
- **소득**: 앞으로 릴레이 검증 시 "Seer CAN 오류 없음"을 **Seer 자체 API로 실측 판정** 가능(CAN 재호밍 추론보다 강한 근거).

## 10. 펌웨어 소스 이중화 (2026-07-25) [실측]

- **원본**: amap-1 `amap@100.116.195.65:~/T-Robotics/CAN_Relay/panda` (브랜치 `can-relay-docking`, HEAD `08c23b53` "도킹 릴레이 firmware (RTR+릴레이분리+SEER_GATE+can_health)", base commaai/panda 26524538).
- **git bundle**(`--all`, 전체 이력·브랜치 완전 보존, md5 `8ea779dc5dd32e5d00cd29012df4bb99`)로 이중화: amap-1(원본) · 로컬저장소 `Tools/firmware/panda-canrelay.bundle` · orin `Big-AMR/Tools/Can_Relay/`(번들 + 작업트리 `panda-firmware/`).
- **복원**: `git clone panda-canrelay.bundle panda && cd panda && git checkout can-relay-docking`. 빌드: `scons -j4 board` → `board/obj/panda.bin.signed`(git 미추적, 배포본은 `docking_field_kit/panda.bin.signed`).
- 참고: `relay_ctrl.h` 없음 — `relay_intercept`/`pc_authority` 상태변수는 다른 파일에 통합(근본원인 분석 대상).

## 11. 부채 등록 (정공법, 2026-07-25)

`docs/debt/registry.md`: **debt-002**(이해 — intercept 전환 글리치 간헐적, main.c relay 스위치) · **debt-003**(이해 — 게이트 누출 원인, safety_seer_gate.h). 상환계획 = 소스 근거 원인규명 → ADR → 벤치검증 → 플래시(승인). 라이브 intercept 시행착오 금지.

⚠ **미판정 모순 (debt id 불일치, 2026-07-27 확인)** — 현행 `docs/debt/registry.md` 의 같은 id 는 **전혀 다른 항목**이다: :8 `debt-002` = IMU `base_link→imu_link` static TF 마운트값, :9 `debt-003` = motor_control freewheel servo-off 가정, :10 `debt-004` = `kin_steer_sign` 가정. 즉 본 절이 주장하는 debt-002/003 과 §12:104 의 "debt-004 신규(docking_drive heartbeat)" 는 레지스트리에 **존재하지 않으며**, CAN relay 부채(전환 글리치·게이트 누출·docking_drive heartbeat)는 **등록 자체가 확인되지 않는다**.
동일한 id 참조가 `Tools/Can_Relay/fw_backups/safety_seer_gate.h.freeze_v1_wholecache:1,4,7` 주석("전환 커버(debt-002)")과 현행 소스 `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h` 주석에도 박혀 있다.
어느 번호가 정본인지는 **이 감사로 판정 불가**(레지스트리가 재작성됐는지 애초에 미등록이었는지 이력이 없음) → **번호를 임의로 바꾸지 않았다.**
유력 가설(미확정): 이 기록이 **다른 저장소(`CAN-Relay`)의 registry** 를 지칭했을 가능성 — 같은 문서의 쌍둥이 사본 `docs/can_relay/field-record-orin-nx-2026-07-25.md` §11 에 다른 담당자가 같은 취지의 정정을 남겼다(2026-07-27).
**판정에 필요한 조치**: registry 의 id 이력(git log `docs/debt/registry.md`) 확인 → CAN relay 부채가 미등록이면 **신규 id 로 append 등록**(기존 debt-002/003/004 덮어쓰기 절대 금지) → 등록 후 본 절과 위 주석의 참조를 신규 id 로 갱신.

## 12. 단위기능 검증 + 게이트 누출 근본원인 확정·수정 (2026-07-25) [실측]

**검증 (2방법):**
- **amap-1 PCAN 벤치**(가짜 Seer/모터): `seer_gate_bench.py` **T1~T5 PASS**(passthrough·쓰기차단·가짜ack·읽기통과·guard RTR). T6(PC구동)·`hb_compare`는 **벤치 판다(#1) 불안정**(LIBUSB_BUSY 지속 + BAD SEND MANY)로 미확정.
- **실차 orin**(실 Seer/모터, `orin_gate_nohb.py`): **0xf3 미전송 + 2s 정착 후 정상상태 bus2 누출 = 0** (2874 쓰기 전량 차단). 잔여누출 = 전환 초기 2s 버스트(366) = debt-002. Seer 알람 0, 리셋 없음.

**게이트 누출 근본원인 [확정, debt-003]:**
- `set_safety_mode(mode, disable_checks=True)`(python 라이브러리 기본) → `0xf8` → **heartbeat_disabled=true**(fail-safe OFF). 벤치(40만회·24h)는 이 상태 유지로 게이트 동작.
- **amap2_monitor가 `0xf3`(heartbeat) 전송** → `heartbeat_disabled=false`로 되살림(usb_comms.h:448). 이후 별도 스레드 controlWrite(0xf3)가 메인 can_recv와 USB 단일핸들 경합으로 못 대면 → fail-safe(main.c:248, 임계 2s@ignition off) → `set_intercept_relay(false)`(main.c:88) → **물리 릴레이 OFF(passthrough)** → 게이트 물리 우회 → 누출.
- **수정**: amap2_monitor 게이트/gatecheck 경로 `hb_on=False`(0xf3 미전송). 배포·검증 완료.
- **debt-004 신규**: docking_drive는 PC사망 안전상 heartbeat 유지 필요하나, 별도 스레드 0xf3 전송이 USB 경합으로 실패 가능 → 단일스레드 인터리브/전송확인 재설계 필요.

**정정**: 앞선 §3·§6·§8의 "heartbeat 2초 레이스/주기" 진단은 부정확했음. 진짜 원인은 "0xf3 전송이 fail-safe를 되살려 릴레이를 passthrough로 내림". **heartbeat는 게이트 동작에 불필요(오히려 미전송이 정답).**

## 13. debt-002 원인 판별·전환 갭 실측 (2026-07-25) [실측]

**판별 실험(사용자 제안 — 아주 중요)**: intercept를 **15초 유지**하며 Seer 알람+resp 동시 측정:
- 유지 t=1.5~15.1s 전 구간 **Seer CAN오류 0**(52111/52106 없음), resp 안정(~965/1.5s). → **intercept 유지 중 데이터 전달 정상.**
- 즉 원인은 **스위칭 순간 갭**이지 "Seer가 intercept에서 데이터 못 받음"이 아님.

**하나씩 실측 배제 (가설 3개 기각):**
- 종단(§4) 아님 — intercept 중 per-bus CAN 에러 **0**(REC/TEC=0, lec=no-err).
- STM32 속도 아님 — **fwd_errs=0**(forwarding 드롭 없음).
- steady 데이터전달 아님 — 15초 유지 무오류.

**전환 갭 실측**: 프레임 도착 촘촘 기록 + 0xe8 토글:
- 정상 도착간격(중앙값) 0.47ms.
- **ENGAGE(pass→intc) 갭 11.8ms · DISENGAGE(intc→pass) 갭 11.0ms** (정상의 ~25배). 판다 μs 타임스탬프 없어 Python 시각 기준(실제 물리 갭은 다소 짧을 수 있음). 물리 릴레이 Panasonic TX2 = Form C break-before-make.

**메커니즘(확정)**: 릴레이 물리 스위칭 ~11ms outage 중 **in-flight SDO 트랜잭션이 깨지면** Seer가 노드 상실 판단 → 간헐적 ~1s 모터 dropout → Motor timeout(52111)/odo lost(52106)/Motor is calibrating(54301). in-flight 없으면 무사(=간헐성). **PCAN은 스위치 자체가 없어(항상 커널 can-gw forwarding) 이 11ms 갭이 없음.**

⚠ **정정 — 함의 철회**: '메커니즘(확정)' 라벨과 '딱 ~11ms 만 메우면 도킹 가능' 결론은 미성립. 11.8ms/11.0ms 측정치 자체는 KEEP(유지), 해석만 §14:168 의 150~220ms 로 대체. 이미 append 된 §13:160-164 ⚠ 정정은 삭제 금지·유지.

⚠ **정정 (§13 메커니즘·함의 — 다음 절 §14 가 뒤집음)** — 값(11.8ms/11.0ms 측정치)은 그대로 두되 해석을 보정한다.
- 이 ~11ms 는 **Python 시각 기준 릴레이 outage** 이며(:121 이 "판다 μs 타임스탬프 없어 Python 시각 기준"이라 스스로 단서 표기), **실제 버스 교란 구간이 아니다.** 실제 교란은 접점 바운스로 **150~220ms** — §14:129 "engage 시 bus2 RX 수신에러(REC 100~237)→error_passive→~150~220ms 회복(릴레이 접점 바운스로 프레임 다수 깨짐)".
- 그래서 실제 대책도 11ms 커버가 아니라 **300ms 커버**로 구현됐다 — §14:133, `Tools/Can_Relay/fw_backups/safety_seer_gate.h.freeze_v1_wholecache:10` `#define SEER_COVER_US 300000U`.
- 따라서 **"딱 ~11ms 만 메우면 도킹 가능" 은 성립하지 않는다.** 결론부도 미성립: §14:139 는 **disengage 가 300ms 커버로도 미해결**이라 기록한다.
- :123 의 "메커니즘(확정)" 라벨도 **11ms outage 전제**로 쓰인 것이므로, 교란 폭에 관한 한 §14:129 로 대체된 것으로 읽을 것(in-flight SDO 파손 → 노드 상실 판단이라는 인과 자체는 유지).

## 14. FW 전환 커버 구현·검증 (2026-07-25~26) [실측]

**추가 규명(고속 can_health 샘플)**: engage 시 **bus2 RX 수신에러(REC 100~237)→error_passive→~150~220ms 회복**(릴레이 접점 바운스로 프레임 다수 깨짐). 첫 모터응답 ~30ms. 종단 아님(정상 시 REC 0)·STM32 속도 아님(fwd_errs 0). **원인 = 스위치 순간 bus2 신호 교란(접점 바운스), 변동 심도가 간헐성.**

**해결 = 판다 펌웨어 "전환 커버"** (`board/safety/safety_seer_gate.h` + `usb_comms.h` 0xe8, git 08c23b53 위 재빌드):
- Seer가 폴링하는 SDO 객체(node1~4 × 0x6000/603F/6041/**6064위치**/6078)와 nodeguard 응답을 fwd훅에서 **최신 캐시(경량 8B)**.
- `0xe8`(relay 전환) 시 `seer_cover_until_us = now + 300ms` → 커버 윈도우 동안 Seer read는 **캐시 응답 즉답**, write는 가짜 ack, guard는 캐시 응답 (모터 회복 대기 없이). Seer(CAN0)는 항상 판다 bus0 연결이라 가능.
- 빌드: scons(-Werror) PASS. 플래시 hash `8a7cd6eb`(v3), version `DEV-08c23b53-DEBUG`.

**검증 [실측]:**
- **engage(도킹 진입) = 완전 해결**: 반복 8/8 + 지속 intercept에서 **52111 Motor timeout / 52106 odo lost = 0**(커버 전엔 매번 발생, 리셋/재호밍 유발하던 치명 문제). 지속 intercept 중 Seer 무오류·bus REC=0·재calibrating 없음.
  - ⚠ **"완전 해결" 표현 철회 (반증됨, 2026-07-27 감사)** — 이 결과는 **커버 v3(플래시 hash `8a7cd6eb`, `DEV-08c23b53-DEBUG`, :134) 표본 8/8 한정**이다.
    **반증**: `docs/issues_and_fixes/issues_and_fixes.md:69-70` — 2026-07-26 09:05~13:00 emulate 내구(engage 180s/diseng 5s) 중 **첫 engage 전환(09:08) 순간 수초간 모터 통신 순단** → **동시각 52111 motor timeout·52106 odo lost·54022 stuff**(`seermon_endur.log` 09:08:42~43) → **자동 재호밍(54301)** → **52954 zeroing timeout(09:29)** = 물리 재호밍까지 진행. 즉 커버 이후 빌드에서도 engage 에서 52111/52106 가 실제 발생했다. 해당 항목의 해결란은 같은 문서 :71 **"[미확정·검증대기]"**.
    **커버로 덮을 수 없는 폭**: 커버 창은 `Tools/Can_Relay/fw_backups/safety_seer_gate.h.freeze_v1_wholecache:10` `SEER_COVER_US 300000U`(**300ms**)이므로 "수초" 순단을 덮지 못한다.
    → **engage 는 "해결됨"이 아니라 매 세션 재검증 대상**이다. (다만 위 내구는 emulate 펌웨어 조건이었고 본 줄은 커버 v3 조건이라, 빌드 차이인지 조건 차이인지는 미판정 — **판정에 필요한 측정**: 동일 펌웨어에서 engage 전환 직후 모터 무응답 지속시간(ms) 계측 + 52111/52106 동시 관측.)
- **6시간 내구 테스트 가동**(orin_6h_engage.py, dwell 180s×~110cyc): 지표 engage 중 52111=0.
  - ⚠ **표본 주의** — 이 줄은 "**가동**"(진행 중) 시점 기록이며 **완주 결과가 인용돼 있지 않다**. 위 8/8 과 함께 읽어 "완전 해결"의 근거로 쓰지 말 것.
- **disengage = 미해결**: 모터가 브릿지로 복귀하며 바운스가 모터 컨트롤러 교란, 판다 루프 밖이라 커버 한계(300ms 고정·자동종료 둘 다 실패). **단 Seer 직결 안전상태로 복귀 방향 + 물리 모션 없음(사용자 확인)**. 실사용은 도킹 종료 1회뿐. 향후: 모터 회복시간 측정→커버 확장 or 그레이스풀 핸드오버.
  - ⚠ **조건 누락 — "물리 모션 없음" 은 무조건이 아니다** (표본 1회·사용자 육안 확인, 회수·조건 미기록: 정차 여부·`pc_authority` 해제 순서·Seer 리셋 발생 여부).
    성립 조건: **해당 disengage 에서 Seer 리셋/재호밍이 발생하지 않은 경우에 한함.** 리셋 시에는 본 문서 §5-4(:49)대로 **조향 물리 이동을 동반**하며, 재호밍은 리셋뿐 아니라 **모터 응답/guard 상실**로도 촉발된다(`docs/issues_and_fixes/issues_and_fixes.md:70` — 통신 순단 → 52111/52106 → 54301 calibrating).
    → **disengage 시에도 조향 가동범위 클리어·E-stop 상비**를 전제로 할 것.

**롤백**: `docking_field_kit/panda.bin.signed.bak_0724`(구 검증본). 소스 롤백: /tmp/fw_backup(amap-1) + git.
