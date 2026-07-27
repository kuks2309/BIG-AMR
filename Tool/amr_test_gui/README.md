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
cd Tool/amr_test_gui

python3 run_gui.py --dry-run          # ① 시뮬레이터 (판다·모터 무접촉)
python3 run_gui.py                    # 실기 판다 relay  ⚠ 실로봇이 움직인다
python3 run_gui.py --seer-ip 192.168.44.82   # Seer 알람 폴링 대상(무선망)
```

의존: PyQt5(시스템 기설치). `python-can`·`rclpy` **불요**.
Seer 알람 패널은 접속 실패 시 자동 비활성 — 제어에는 영향 없다.

## 테스트

```bash
pytest Tool/amr_test_gui/test -q      # 49건, 하드웨어 무접촉
```

- `test_ramp.py` — 램프 상태기계(클램프·단계·FAULT 래치·양 부호 대칭)
- `test_controller.py` — SimBus 로 backend 를 실제 브링업해 **CAN 프레임 수준** 검증
  (조향 counts 항등 · 구동 raw 부호 · 정착 전 구동 0 · 고착 노드 FAULT · 브링업 실패 시 버스 release)
- `test_constants.py` — 인용 상수를 정본 파일에서 **재도출**해 드리프트 차단

## ⚠ 안전 절차 (검증 계단 — 순서 고정)

| 단계 | 내용 | 통과 조건 |
| --- | --- | --- |
| ① | `--dry-run` 으로 UI·램프·FAULT 경로 확인 | 램프가 0→30→60→90 단계로 전진, 정착 전 raw 0 |
| ② | **잭업(바퀴 뜬 상태)** 실기 연결 → 조향만 ±30 → ±60 → ±90 | 각 단계에서 node3·4 실측이 지령을 추종 |
| ③ | 저속(≤50 mm/s) 직진 1회 | 방향이 예상과 일치(육안) |
| ④ | 저속 crab 1회 | 방향이 예상과 일치(육안) |

각 단계의 실측 확인 전에 다음 단계로 넘어가지 않는다.

**상시 준비**: 하드 E-stop 을 손에 · 이동 구역 클리어 · 속도 상한은 검증 전 50 mm/s 유지.

**GUI 안전 장치**

- `E-STOP` 최상단 버튼 + **Space 키** (Esc = 정지). backend E-stop 래치를 그대로 사용한다.
- 조향 슬라이더는 ±90° 를 물리적으로 넘을 수 없다(하드 클램프).
- `콜드 브링업 허용` 체크박스 — 조향이 홈에서 5° 이상 벗어난 상태(콜드)의 브링업은 기본 **거부**된다.
  체크는 조향 물리 스윙을 허용하므로 **잭업/주변 확보 후에만**.
- 창을 닫거나 프로세스가 죽으면 제어권이 반환된다 — 명시 `release`, 또는 heartbeat 소실 시 펌웨어가
  `SAFETY_SILENT` 로 복귀하며 `set_intercept_relay(false)`+`pc_authority=false` 를 수행한다
  (2026-07-27 펌웨어 수정). 하네스 릴레이가 물리 통과라 Seer↔모터 버스는 그대로 유지된다.

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
