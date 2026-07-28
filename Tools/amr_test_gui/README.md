# amr_test_gui — Tongyi 4축 AMR 구동 테스트 GUI

PC(Personal Computer)가 CAN relay(판다) 경유로 Tongyi 4축 AMR(Automated Guided Vehicle)의
조향·구동·crab 을 제어하고, 노드 상태·Seer 알람을 실시간 표시하는 **독립 PyQt5 앱**(비-ROS).

ADR: [docs/adr/2026-07-27-amr-test-gui.md](../../docs/adr/2026-07-27-amr-test-gui.md) ·
구조·함수표: [docs/sw_structure/amr-test-gui/2026-07-27.md](docs/sw_structure/amr-test-gui/2026-07-27.md)

## 핵심 설계

- **프로토콜 정본 재구현 0** — `src/Actuators/motor_control/`(protocol·backend·kinematics)을 그대로 import 한다.
  본 툴이 새로 만든 것은 램프·모드표·UI·판다 어댑터뿐이다.
- **부호 투명 전송** — backend 를 `drive_sign=+1`·`steer_sign=+1` 항등으로 구성해
  조향 counts = `steer_home + deg×57344`, 구동 raw = 실측 units(0.1 rpm) 와 1:1 이 되게 했다.
  방향 의미는 전부 [`modes.py`](amr_test_gui/modes.py) 의 **인용 테이블**이 소유한다.
- **단계 램프가 구조적 인터록** — ±90° 하드 클램프 + ≤30° 단계 + 단계별 실측 추종 확인 +
  미추종 시 FAULT 래치(홈 강제·구동 금지). 2026-07-27 node4 급점프 사고 유형을 코드로 봉쇄한다.

## 실행

```bash
cd Tools/amr_test_gui

python3 run_gui.py --dry-run          # ① 시뮬레이터 (판다·모터 무접촉)
python3 run_gui.py                    # 실기 판다 relay  ⚠ 실로봇이 움직인다
python3 run_gui.py --seer-ip 192.168.44.82   # Seer 알람 폴링 대상(무선망)
```

의존: PyQt5(시스템 기설치). `python-can`·`rclpy` **불요**.
Seer 알람 패널은 접속 실패 시 자동 비활성 — 제어에는 영향 없다.

## 테스트

```bash
pytest Tools/amr_test_gui/test -q      # 하드웨어 무접촉

# 수집 건수는 고정 숫자로 적지 않는다 — 아래로 직접 확인한다.
QT_QPA_PLATFORM=offscreen python3 -m pytest Tools/amr_test_gui/test --collect-only -q
```

> ⚠ 정정(2026-07-27 감사): 종전 서술 "49건"은 **반증**됐다. 위 `--collect-only -q` 재계수 결과
> **87건**이다(test_constants 13 / test_controller 21 / test_modes 24 / test_ramp 16 /
> test_safety_regressions 13). 아래 목록도 5개 파일 중 3개만 적어 `test_modes.py`·
> `test_safety_regressions.py` 를 누락하고 있었다 — 추가한다. (원 서술은 이력으로 남긴다)

- `test_ramp.py` — 램프 상태기계(클램프·단계·FAULT 래치·양 부호 대칭)
- `test_controller.py` — SimBus 로 backend 를 실제 브링업해 **CAN 프레임 수준** 검증
  (조향 counts 항등 · 구동 raw 부호 · 정착 전 구동 0 · 고착 노드 FAULT · 브링업 실패 시 버스 release)
- `test_constants.py` — 인용 상수를 정본 파일에서 **재도출**해 드리프트 차단
- `test_modes.py` — 모드 테이블·8방위 도출(부호 근거 `basis` 포함)
- `test_safety_regressions.py` — 코드리뷰 지적 사항의 회귀 고정
  (피드백 신선도 게이트 · USB 연결↔제어권 획득 분리·순서 강제 · E-STOP 비해제 등)

## ⚠ 안전 절차 (검증 계단 — 순서 고정)

| 단계 | 내용 | 통과 조건 |
| --- | --- | --- |
| ① | `--dry-run` 으로 UI·램프·FAULT 경로 확인 | 램프가 0→30→60→90 단계로 전진, 정착 전 raw 0 |
| **②-0 (선행, 2026-07-27 추가)** | **조향 홈 기준 확인** — 브링업 직후 node3·4 의 0x6064 **원시값**(상태표 `pos` 열)과 바퀴 물리각(육안)을 대조해 홈이 참인지 확인한다 | 원시값이 config 홈(7,871,815 / 7,840,086)에 가깝고 **동시에** 바퀴가 물리적으로 직진. 불일치하면 **진행 금지**<br>⚠ 정정 (2026-07-27): 호밍 후 드라이브가 실제로 정착시키는 직진 자세는 **node3 7,882,020 / node4 7,859,062**(config 대비 +10,205 / +18,976 counts = +0.178° / +0.331°)다 — `Log/homing_capture_220350.jsonl` t≈49.14 지령→수렴. **두 값 모두 "직진 후보"로 허용**하되, 판정은 육안 물리각을 우선한다 |
| ② | **잭업(바퀴 뜬 상태)** 실기 연결 → 조향만 ±30 → ±60 → ±90 | 각 단계에서 node3·4 실측이 지령을 추종 |
| ③ | 저속(≤50 mm/s) 직진 1회 | 방향이 예상과 일치(육안) |
| ④ | 저속 crab 1회 | 방향이 예상과 일치(육안) |

각 단계의 실측 확인 전에 다음 단계로 넘어가지 않는다.

> ⚠ **②-0 을 왜 넣었나** (2026-07-27 감사 — 조건누락 정정)
> 램프의 지령각은 전부 **홈 기준 상대각**이다(`controller.py:186-188` `_deg()` =
> `(counts − steer_home)/COUNTS_PER_DEG`). 그런데 종전 계단에는 그 홈이 참인지 확인하는 단계가
> 없었다. 홈이 틀린 채 계단 ②를 수행하면 "±30° 지령"이 물리적으로는 −107°~+167° 스윙이 될 수
> 있다 — `controller.py:62-63` 이 계산한 "0° 지령 = 137° 스윙"과 **같은 메커니즘**이며,
> 이것이 `docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md:18-23`
> 의 node4 물리 갇힘 사고다.
> 홈 신뢰도에 대해 코드 자신은 `controller.py:66` 에서 런타임 표기를
> `home_source="config(전원사이클 불변 가정 — 반증됨, 확인 필요)"` 로 두고 있다.
> **현재 GUI 에는 홈 캡처 버튼이 없다** — `controller.capture_home()`(controller.py:190-224,
> "운전자가 바퀴가 물리적으로 직진임을 확인한 뒤에만 호출")은 구현돼 있으나 `ui_main.py` 에
> 호출부가 없다(grep 0건; `btn_home`(ui_main.py:249-257)은 **모드 전환**일 뿐 홈 캡처가 아니다).
> 따라서 ②-0 은 현재 **육안·원시값 대조로만** 수행할 수 있다.
> 홈 상수 자체의 신뢰도는 **미판정 모순** 상태다 →
> [구조문서 §3 `STEER_HOME_COUNTS`](docs/sw_structure/amr-test-gui/2026-07-27.md) 참조.

**상시 준비**: 하드 E-stop 을 손에 · 이동 구역 클리어 · 속도 상한은 검증 전 50 mm/s 유지.

**GUI 안전 장치**

- `E-STOP` 최상단 버튼 + **Space 키** (Esc = 정지). backend E-stop 래치를 그대로 사용한다.
- 조향 **지령각**은 소프트웨어 하드 클램프로 ±90°(**홈 기준 상대각**)를 넘지 않는다
  (`ramp.py:66-68` `_clamp()` = `max(-limit, min(limit, deg))`; 슬라이더 범위 `ui_main.py:208`
  `sld.setRange(-90, 90)` 도 위젯 설정일 뿐이다).
  > ⚠ 정정(2026-07-27 감사 — 근거없음): 종전 서술 "±90° 를 **물리적으로** 넘을 수 없다"는 성립하지
  > 않는다. 이 클램프는 물리 스토퍼가 아니라 **소프트웨어 산술**이고, 그 각도는 `steer_home` 기준
  > 상대각이다(`controller.py:186-188`). 홈 기준이 틀리면 ±90° 지령이 물리적으로 ±90° 를 넘는다 —
  > `controller.py:62-63` 이 "0° 지령 = 137° 스윙"이 되는 경우를 명시하고, 실제로 node4 가
  > 137°(±90° 밖)로 밀려 물리 갇힘이 발생했다
  > (`docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md:18-23`).
  > 클램프 값(90.0)은 변경하지 않았다 — 서술만 정정한다.
- `콜드 브링업 허용` 체크박스 — 조향이 홈에서 5° 이상(`HOMING_TOL_DEG`, `constants.py:38`) 벗어난
  상태(콜드)의 브링업은 기본 **거부**된다.
  체크는 조향 물리 스윙을 허용하므로 **잭업/주변 확보 후에만**.
  > ⚠ 보강(2026-07-27 감사 — 조건누락). 값 변경 없음:
  > ① ~~체크 시 조향이 config 홈까지 최대 **137.3°** 물리 스윙할 수 있다
  >   (`docs/ros2_driver/2026-07-09-design-inputs.md:56` "0에서 홈까지 3.3 s 물리 스윙(+137.3°)").~~
  >   5° 는 **판정 임계**일 뿐 스윙 폭이 아니다.
  >   > ⚠ 정정 (2026-07-27 실기 검증): **「137.3°」 단일값은 존재하지 않는다 — 두 축이 다르다.**
  >   > 브링업은 조향축에 드라이브 호밍(**Home 1** — 음(−)의 리밋 트리거, 전 노드 `0x6098 = 1`
  >   > 실기 판독)을 개시하며, 조향은 **원점(−리밋)까지 전 범위를 훑은 뒤 조향 0°(물리 직진)로
  >   > 복귀**한다. 복귀 목표 실측은 **node3 7,882,020 (+137.45°) / node4 7,859,062 (+137.05°)**
  >   > (57344 counts/°; EasyDRIVE `steerOffset` 138.000 / 137.250 과 대응).
  >   > 본 GUI 의 config 홈(`STEER_HOME_COUNTS` = 7,871,815 / 7,840,086)을 기준으로 하면
  >   > **node3 +137.27° / node4 +136.72°** 다. 어느 조합으로도 137.3° 는 나오지 않는다.
  >   > ⚠ **최대 스윙 폭은 137° 대가 아니라 「현재 자세 → −리밋 → 직진」 전 범위**임에 주의.
  >   > 근거: `Log/homing_capture_220350.jsonl`(Seer 주도 호밍 253,510 프레임) ·
  >   > [Handbook V7.0 §6.9 page 171 `0x60FB.4 = RstStart`] ·
  >   > `References/motor_configuration/frontsteer2.png` · `realsteer2.png` ·
  >   > `docs/verified_facts/2026-07-27.md:215-218`.
  > ② ~~같은 문서(:52,:56)는 부팅 시 0x6064≈0 이 정상이라 하므로, **전원 재인가 후에는 사실상 항상
  >   '콜드'로 판정**된다 — 드문 예외가 아니다.~~
  >   > ⚠ 정정 (2026-07-27): 「부팅 시 0x6064≈0」은 **미판정**으로 되돌린다.
  >   > `Log/homing_capture_220350.jsonl` 은 캡처 시작 시점(t=0~5.16) 조향 0x6064 가
  >   > 7,882,014 / 7,859,058(= 홈 부근)이었고, **0 이 되는 구간은 호밍 진행 중**
  >   > (`0x60FB.4=1` 이후 ~ 완료 전, t≈17.93~49.18)뿐임을 보인다
  >   > (`src/Actuators/motor_control/motor_control/backend.py:264-272` 도 같은 취지).
  >   > ⇒ 「전원 재인가 후 항상 콜드」로 단정하지 말고, **판독 시각이 호밍 구간인지**
  >   > (`0x6041` bit15 = 0) 먼저 확인할 것. 어느 쪽이든 아래 ④ 때문에 안전 절차는 동일하다.
  > ③ 판정 기준이 되는 홈 자체(`constants.py:35` `STEER_HOME_COUNTS`)가 **미판정 모순** 상태다
  >   ([구조문서 §3](docs/sw_structure/amr-test-gui/2026-07-27.md) · `controller.py:60-66`).
  >   → 잭업·주변 확보 + 위 계단 **②-0 홈 기준 확인** 후에만 체크할 것.
  > ④ (2026-07-27 추가) **이 체크박스(게이트)는 물리 호밍 스윙 자체를 막지 못한다.** 게이트가 보는
  >   것은 「홈 대비 편차 > 5°」뿐이고, **게이트를 통과한 뒤**의 init 시퀀스가 조건 없이
  >   `0x6099=2500` → `0x60FB.4=1`(RstStart, 호밍 개시)을 송신한다
  >   (`src/Actuators/motor_control/motor_control/backend.py:363-368`, 코드 자신도 `:30`·`:319`
  >   에서 명시). 즉 **조향이 홈 ±5° 안에 있는 "웜" 상태에서도 브링업은 전 범위 호밍을 일으킨다.**
  >   체크 해제는 "스윙 없음"이 아니라 "브링업 자체 거부"일 뿐이다 — **잭업·주변 확보는 체크
  >   여부와 무관하게 항상 선행**한다.
- 창을 닫거나 프로세스가 죽으면 제어권이 반환된다 — 명시 `release`, 또는 heartbeat 소실 시
  (0.4 s 주기 기준 **약 2~5 회 누락 후**; `panda_can_bus.py:55` `HEARTBEAT_S = 0.4`,
  `Tools/Can_Relay/panda-firmware/board/main.c:164-165` `HEARTBEAT_IGNITION_CNT_ON 5U` /
  `..._OFF 2U`, :233 임계 비교) 펌웨어가 `SAFETY_SILENT` 로 복귀하며
  `set_intercept_relay(false)`+`pc_authority=false` 를 수행한다 (2026-07-27 펌웨어 수정).
  하네스 릴레이가 물리 통과라 Seer↔모터 버스는 그대로 유지된다.
  > ⚠ 조건 보강(2026-07-27 감사 — 조건누락). 종전 서술은 **즉시성**과 **배포 자산** 두 조건을
  > 빠뜨려 "죽으면 곧바로 안전"으로 읽혔다:
  > (a) **즉시성 아님** — 위 카운터 임계 도달 후에만 실행되므로, 프로세스 급사 후 **수 초 동안
  >   intercept·auth=PC 가 유지된다**.
  > (b) **플래시 미대조** — 인용한 펌웨어 코드(`main.c:257-259`
  >   `set_intercept_relay(false); pc_authority = false;`)는 소스에 **[존재]함**이 확인될 뿐이다.
  >   해당 ADR `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:3` 은 `Status: Proposed`
  >   이고, 같은 ADR Decision 4(펌웨어 소스 git 커밋)는 미이행이다
  >   (`git ls-files --error-unmatch Tools/Can_Relay/panda-firmware/board/main.c`
  >   → "did not match any file"). **실제 판다에 그 빌드가 플래시됐는지 대조할 근거가 저장소에 없다.**
  > → 이 fail-safe 는 **2026-07-27 패치 빌드가 실제로 플래시된 경우에만** 유효하다고 가정하라.
  >   그 전까지는 프로세스 급사 후 수 초간 intercept 가 유지된다고 보고 **하드 E-stop 을 우선**한다.

## 미해결 항목

| id | 내용 |
| --- | --- |
| `debt-004` | `kin_steer_sign`(조향 +counts 가 CCW 인지 CW 인지) 미확정. **본 GUI 는 영향 없음**(raw 언어로 직접 지령) — `driver_node` 의 twist·오도메트리 경로 소관 |
| `debt-005` | backend + PandaCanBus 통합 relay 실구동 미검증 → 검증 계단 ①② 로 해소 |
| `debt-006` | guard RTR 을 판다가 못 보내므로 Seer guard forward 에 의존 — 잭업 5분 구동으로 HALT 미발생 확인 필요 |

## 환경 주의

- Seer 는 **무선망(192.168.44.x)** 에만 있다 — 유선 eth0 에 44 대역 IP 를 붙이지 말 것.
- PC 와 Seer 는 전원을 공유한다(Seer 리부팅 = PC 리부팅).
- 판다 플래시 시에는 `sudo systemctl stop ModemManager` 필요(LIBUSB_BUSY).
