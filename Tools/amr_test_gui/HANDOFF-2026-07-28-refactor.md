# 이관 — `gui.py` 리팩터링 계획 (2026-07-28 → 다음 세션)

- 작성: 2026-07-28 (KST) · sess 56a709a5 · 사용자 지시로 세션 중단하며 인계
- 대상: [`Tools/amr_test_gui/gui.py`](gui.py) — Tongyi 4축 AMR 구동 테스트 GUI (실기 전용)
- 사용자 요청 원문: *"연동후 스파케티 코드 없애고 리펙토링 필요할 것 같음"* (2026-07-28 20:5x)

> **이 문서만 읽고 시작해도 되게 썼다.** 배경은 [README.md](README.md),
> 구 패키지 폐기 경위는 [ADR 2026-07-28-old-gui-removal](../../docs/adr/2026-07-28-old-gui-removal.md).

## 1. 지금 상태 (측정값, 2026-07-28 21:2x)

| 항목 | 값 |
| --- | --- |
| `gui.py` | **1,142 줄**, 단일 파일 |
| `MainWindow` 메서드 | **46 개** (+ `WheelView` 5, 모듈 함수 5) |
| 테스트 | 5 파일 · 59 함수 → **88 케이스 통과** (하드웨어·화면 없이 실행) |

`MainWindow` 하나가 **네 가지 책임**을 함께 진다:

| 책임 | 해당 메서드 |
| --- | --- |
| ① 위젯 구성 | `_build_connect` `_build_jog` `_build_wheel_adj` `_build_settings` `_build_motors` `_build_seer` `_build_status` `_build_wheel` `_build_log` `_motor_table` |
| ② CAN 프로토콜·지령 | `_sdo_write` `_drive` `_steer_axis` `_steer_to` `_jog_run` `_homing_run` `_wait_homed` `_wait_settle` `_loop` |
| ③ Seer 네트워크 | `_seer_loop` `_on_seer_data` `_on_seer_status` `_fmt_alarm` `_on_clear_fatal` `_set_alarm_color` |
| ④ 스레드·수명주기 | `scan` `_on_usb` `_on_take` `safe_release` `closeEvent` (+ 모듈 `main` 의 4 종료경로 배선) |

### 왜 고쳐야 하는가 (근거 — 이번 세션의 실제 사고 2건)

1. **주석 오염** — 20 에이전트 line-by-line 감사에서 확정 18건. 삭제된 파일을 가리키는 인용,
   폐기된 절차를 현재 동작으로 쓴 서술, 코드가 보장하지 않는 과장이 뒤섞여 있었다.
   책임이 안 갈려 있으니 "어디를 봐야 하는지" 가 코드에 드러나지 않았다.
2. **슬라이더 먹통** — 원인은 UI 레이아웃(78×20 px)이었는데, CAN 계층에서 네 번 오진했다
   ([claude-mistake 2026-07-28-014](../../docs/claude-mistake/2026-07-28-014_ui-diagnosed-without-looking-at-screen.md)).
   UI 와 프로토콜이 한 클래스에 있으니 증상이 어느 층인지 가리지 못했다.

## 2. 목표 구조 (제안 — 확정 아님, 다음 세션에서 재검토할 것)

```
Tools/amr_test_gui/
  gui.py              MainWindow — 위젯 배치와 시그널 배선만
  tongyi_can.py       TongyiCan   — SDO 인코딩·조향/구동 지령·호밍 시퀀스·폴링 (Qt 무의존)
  seer_status.py      SeerStatus  — 1040/1050 폴링·알람 (네트워크 전담, Qt 무의존)
```

**분할 기준은 "테스트가 이미 가리키는 경계"** 다. 지금 테스트가 무엇을 잡고 있는지 보면
경계가 드러난다 — `test_gui_math.py`(순수 환산)·`test_homing.py`(SDO 프레임)는 이미
Qt 없이 도는 로직을 시험하고 있고, 이것이 곧 `TongyiCan` 의 표면이다.

### 각 모듈이 가져갈 것

- **`TongyiCan`** — `_sdo_write` `_drive` `_steer_axis` `_steer_to` `_wait_settle`
  `_homing_run` `_wait_homed` `_loop`, 모듈 함수 `steer_counts` `drive_units`,
  상수 `COUNTS_PER_DEG` `STEER_HOME` `VEL_*` `STEER_LIMIT_DEG` `_ABORT`.
  판다 핸들을 주입받고, 결과는 콜백 또는 큐로 낸다(**Qt 시그널을 알지 못해야 한다**).
- **`SeerStatus`** — `_seer_loop` `_fmt_alarm` `_on_clear_fatal` 의 네트워크 부분,
  상수 `SEER_IP` `SEER_GUI`.
- **`MainWindow`** — `_build_*`, `_on_*` 핸들러, 시그널 정의, `safe_release`·`closeEvent`.

## 3. 이관 순서 (안전한 순서 — 이대로 할 것)

한 번에 다 옮기지 말 것. **각 단계마다 88건이 통과해야 다음으로 간다.**

1. **`TongyiCan` 추출** — 가장 안전하다. 순수 환산(`steer_counts`·`drive_units`)이 이미
   모듈 함수이고 테스트가 붙어 있다. `_sdo_write`·`_steer_axis`·`_drive` 를 옮기고
   `MainWindow` 은 위임만 한다. 이 단계에서 **CAN 바이트가 바뀌면 안 된다** — `test_homing.py`
   가 프레임을 바이트로 고정하고 있으니 어긋나면 즉시 실패한다.
2. **`SeerStatus` 추출** — 네트워크는 이미 독립적이다. 창 파괴 뒤 emit 하던 경쟁을 이번에
   고쳤으니(`RuntimeError` 조용한 종료) 그 처리를 **콜백 경계로 옮기는 것**이 핵심이다.
3. **`MainWindow` 정리** — 남은 것은 위젯과 배선뿐. `_build_*` 가 10 개라 그룹별로 묶을지
   그대로 둘지는 그때 판단.
4. **실기 재검증** — 리팩터 후 반드시 실기에서 ① 제어권 획득 ② 슬라이더 조향 ③ 조그 구동
   ④ 호밍까지 한 번씩 돌린다. **테스트 88건 통과는 실기 검증을 대신하지 못한다.**

## 4. 절대 바꾸지 말 것 (실기로 확인된 것)

바꾸면 로봇이 다치거나 동작이 죽는다. 리팩터는 **위치만 옮기고 값·순서는 보존**한다.

| 항목 | 값 / 순서 | 확인 |
| --- | --- | --- |
| 조향 지령 프레임 | `0x607A`(4B) + `0x6040=0x3F`(2B) — Seer 프레임과 바이트 동일 | 2026-07-28 캡처 대조 |
| 조향 counts | `STEER_HOME[n] + deg × 57344`, **±90° 클램프** | `test_gui_math.py` |
| 호밍 | 조향축 3·4 만 · `0x6040=0x86` → `0x6099:00=2500` → `0x60FB:04=1` | 실기 캡처 |
| 호밍 완료 판정 | `0x6041` bit15 의 **0→1 전이**(1 만 보면 오판) | `test_homing.py` |
| `0x6098` | **쓰지 않는다** — 덮으면 리셋 모드가 꺼진다 | Handbook + 캡처 |
| crab 순서 | 구동 0 → 조향 → **양축** 정착 확인 → 구동 | `_jog_run` |
| 호밍 중 `0x6064` | 실위치가 아니라 0 — 각도 갱신을 멈춘다 | 실기 캡처 |
| 종료 4경로 | 전부 `safe_release()` 로 모인다(멱등) | `test_safe_release.py` |
| 슬라이더 | **실측을 되쓰지 않는다.** 되먹이면 먹통이 된다 | `test_slider.py` |
| 슬라이더 크기 | 폭 ≥240 px · 높이 ≥24 px · 1 px ≤1° | `test_slider.py` |
| 판다 | **1 PC 1대 원칙** — 선택 UI 를 두지 않는다 | 사용자 결정 |
| 소프트 E-STOP | **두지 않는다** — 하드웨어 E-STOP 이 권위 | 사용자 결정 |
| dry-run·시뮬레이터 | **없다** — 실기 전용 | 사용자 결정 |

## 5. 함께 정리할 것 (선택)

- **주석 규율** — 이번에 세운 기준을 유지한다: 코드 주석에 외부 인용(파일:줄·캡처 이름·
  mistake id)을 쌓지 않는다. 근거는 [README.md](README.md) 가 든다. 저장소가 바뀔 때마다
  코드가 같이 썩는 것이 이번 오염의 원인이었다.
- **`_build_*` 10 개** — 위젯 구성이 `MainWindow` 을 길게 만드는 주범이지만, 쪼개면
  오히려 배치를 읽기 어려워질 수 있다. 쪼갤지 말지는 실제로 옮겨본 뒤 판단할 것.

## 6. 미해결 부채 (리팩터와 별개, 그대로 이관)

| id | 내용 |
| --- | --- |
| debt-007 | `STEER_HOME` 기준계 미판정 — **값은 실측 없이 바꾸지 말 것** |
| debt-010 | 조향 추종 실패 시 FAULT 래치 없음 — 그 회차 구동만 취소되고 재시도가 안 막힌다 |
| debt-011 | 실기 상호작용(실제 CAN 왕복·Seer 응답) 자동 검증 없음 |
| debt-012 | Node Guarding RTR 을 PC 가 못 보낸다 — Seer guard 가 대신 만족시킨다는 가정 미확인 |

**미검증 항목 하나 더** — `_redraw_wheel` 이 제어권 없을 때 쓰는 **Seer position 의 부호**가
판다 실측과 같은 방향인지 확인되지 않았다. 두 축 모두 0° 인 상태에서만 대조했다.
Seer 로 한쪽 조향을 틀어 두 표의 부호를 대조할 것.

## 7. 이번 세션에서 배운 함정 (다음 세션이 같은 데 빠지지 않도록)

1. **UI 증상은 화면을 먼저 캡처한다.** 코드만 보고 네 번 오진했다. 캡처는 수 초,
   내가 택한 우회는 25 만 프레임 파싱 + 계측 삽입 + 재시작 3회였다.
   `~/.claude/capture_screen.py --mode window --window-id <id>` 로 즉시 볼 수 있다.
2. **같은 증상을 두 번째로 들으면 진단 수단을 바꾼다.** 같은 층을 더 깊게 파지 말 것.
3. **위젯 크기는 눈이 아니라 `geometry()` 로 잰다.** 이 세션에서만 같은 종류의 레이아웃
   결함이 2건 나왔다(버튼 겹침 · 슬라이더 78 px).
4. **`pkill -f 'gui[.]py'` 는 반드시 단독 호출로.** 다른 명령과 묶으면 패턴이 자기
   명령줄에 걸려 셸을 죽인다(이 세션에서 2회 발생).
5. **공유 워킹트리에서 `git checkout -b` 금지** — HEAD 가 전역 이동해 다른 세션을 끌고 간다.
   `git worktree add` 로 별도 트리에서 커밋할 것
   ([2026-07-28-009](../../docs/claude-mistake/2026-07-28-009_shared-tree-head-moved-by-checkout.md)).

## 8. 시작 전 확인

```bash
cd Tools/amr_test_gui
QT_QPA_PLATFORM=offscreen python3 -m pytest test/ -q      # 88 passed 확인 후 착수
can_relay                                                  # 실기 기동 (~/.bashrc alias)
```

⚠ 리팩터 중에도 **다른 세션이 같은 워킹트리에서 `gui.py` 를 편집할 수 있다.**
이 세션에서 실제로 다른 세션이 `safe_release` 를 이 파일에 추가했다. 착수 전
`git status` 로 확인하고, 커밋은 세션 브랜치에 격리할 것.
