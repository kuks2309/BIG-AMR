# amr_test_gui — Tongyi 4축 AMR 구동 테스트 GUI

PC(Personal Computer)가 CAN relay(판다) 경유로 Tongyi 4축 AMR(Autonomous Mobile Robot)의
조향·구동·crab 을 저속 시험 지령하고, 모터 값·Seer 알람을 실시간 표시하는
**독립 PyQt5 앱**(비-ROS). 구현은 단일 파일 [`gui.py`](gui.py) 하나다.

> ## ⚠ 실기 전용 — 누르면 실제 로봇이 움직인다
>
> 시뮬레이터·dry-run 은 **없다**(사용자 결정, 2026-07-28). 판다는 USB 장치 하나이므로
> 검출 여부로 확인된다. 실행 전 **E-STOP 상비 · 이동구역 클리어 · 저속부터**.
>
> 화면에 소프트 E-STOP 버튼을 두지 않는다 — **하드웨어 E-STOP 이 권위**다(사용자 결정).

ADR: [2026-07-28-old-gui-removal.md](../../docs/adr/2026-07-28-old-gui-removal.md)
(구 패키지 폐기·대체표) · 원 ADR [2026-07-27-amr-test-gui.md](../../docs/adr/2026-07-27-amr-test-gui.md)
(**구현 결정은 Superseded**, 안전 원칙만 유효)

## 실행

```bash
DISPLAY=:0 python3 gui.py
```

순서: **판다 USB 연결 → 제어권 획득 → 조그/슬라이더**.
제어권을 잡기 전에는 조향 지령이 거부된다(로그에 사유 표시).

## 화면 구성

```
┌ CAN-Relay 연결 ─────┬ 2 ───────────────┬ 3 ────────────────┐
│ 연결(판다목록·USB·  │ 로봇 조그 3×3    │ 차량 바퀴 상태     │
│      제어권 토글)   │ 모터 값(판다 직독)│  top-view 그림     │
│ 로그                │ Seer 값(비교)     │ 앞뒤 바퀴 조정     │
│ Seer 로그           │ 설정              │  슬라이더 ×2       │
│  [Fatal 오류 리셋]  │                   │                    │
└─────────────────────┴───────────────────┴────────────────────┘
 Seer 192.168.44.82 · 연결됨 · 모터 4축 · 갱신 HH:MM:SS
```

## 동작 규칙

- **crab 순서** — 조그는 `구동 0 → 조향 지령 → 정착 확인 → 구동` 순이다(`_jog_run`).
  정착은 **두 축(N3·N4) 모두** 허용치 안에 들어와야 통과하며, 실패하면 구동을 취소한다.
- **가동범위 클램프 ±90°** — 실측 검증 범위 밖은 보내지 않는다(`steer_counts`).
  기구 한계는 ±140° 이나 그 값은 Roll_A084 config 이고 본 기체 실측이 아니다.
  범위 밖 지령으로 node4 가 물리적으로 갇힌 사고가 있었다
  ([claude-mistake 2026-07-27-002](../../docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md)).
- **단계 램프는 쓰지 않는다** — 시스템의 방식이 아니다. 실기 캡처에서 Seer 는 최종 절대 목표를
  반복 송신할 뿐이고 이동 프로파일은 드라이브가 수행한다
  ([2026-07-28-003](../../docs/claude-mistake/2026-07-28-003_invented-steer-ramp-mechanism.md)).
- **슬라이더 지령은 손을 뗄 때 1회** — 끄는 동안 매 틱 보내면 버스가 지령으로 찬다.
- **바퀴 그림 출처 우선순위** — ① 제어권 보유 → 판다 직독 ② 제어권 없음 + Seer 폴링 생존 →
  Seer 1040 ③ 실측 없음 → 슬라이더(미리보기). 실측이 항상 슬라이더를 이긴다.
- **폴링은 읽기 전용** — `0x6064`·`0x606C`·`0x6078` 만 읽는다. 지령은 조그·슬라이더 경로에서만 나간다.

## 주요 상수 (정본 인용)

| 상수 | 값 | 출처 |
| --- | --- | --- |
| `COUNTS_PER_DEG` | 57,344 | design-inputs §3 (16384×4×315/360), 홈↔90° Δ=5,160,960 실측 일치 |
| `STEER_HOME` | N3 7,871,815 / N4 7,840,086 | `config/tongyi_amr.yaml` — ⚠ **debt-007 미판정**, 기준값은 추후 조정 |
| `VEL_PER_MMPS` / `VEL_MAX_UNITS` | 24.447 / 4,889 | docking_field_kit 실측 (±2445 = 0.10 m/s) |
| `STEER_LIMIT_DEG` | 90.0 | 실측 검증 범위 |
| `SEER_GATE` / `CAN_KBPS` / `HEARTBEAT_S` | 30 / 250 / 0.4 | 판다 safety_mode·버스·하트비트 |

## 테스트

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest test/ -q
```

[`test/test_gui_math.py`](test/test_gui_math.py) 37건 — 조향 counts 환산·±90° 클램프·
구동 속도 환산과 상한·조그 방향표 정합. 하드웨어·창 없이 돈다.

⚠ **CAN 송신 경로와 UI 상호작용은 아직 자동 검증이 없다**(debt-011 잔여).

## 알려진 부채

| id | 내용 |
| --- | --- |
| debt-007 | `STEER_HOME` 기준계 미판정 — 값은 실측 없이 바꾸지 않는다 |
| debt-010 | 조향 추종 실패 시 **FAULT 래치 없음** — 그 회차 구동만 취소되고 재시도가 막히지 않는다 |
| debt-011 | 테스트 부분 상환(순수 환산 37건) — 송신 프레임·UI 경로 미검증 |
| debt-012 | Node Guarding RTR 을 PC 가 보내지 못한다(판다 제약). Seer guard 가 대신 만족시킨다는 가정 미확인 |
