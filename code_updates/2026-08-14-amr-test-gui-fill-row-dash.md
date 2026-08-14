# 2026-08-14 — 원본 GUI 모터 값 표: `None` 을 `—` 로 덮어쓰기 (표시 규칙 통일)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md` §4).
> 약어: GUI(Graphical User Interface)

- 사용자 지시: 2026-08-14 "코드를 이식본에 맞출지, docstring 을 코드에 맞출 <-어떤 내용인지
  알려주세요" → 설명 후 선택: **안 A(코드를 이식본에 맞춤)**
- 발견 경위: 같은 날 코드 리뷰 **F2**(`docs/code_review/can_relay_ui/2026-08-14.md`)
- 대상: `Tools/amr_test_gui/gui.py` · `Tools/amr_test_gui/test/test_gui_tables.py`

## 무엇을 바꿨나 — 1줄

```python
# Tools/amr_test_gui/gui.py:625  MainWindow._fill_row
- if val is not None:
-     table.item(r, c).setText(fmt.format(val))
+ table.item(r, c).setText("—" if val is None else fmt.format(val))
```

docstring 도 사실에 맞춰 「`None` 인 칸은 `—` 로 **덮어쓴다**」로 고치고, 그 이유(값이 없을 때
칸을 두면 직전 숫자를 현재 값으로 읽는다)를 함수 설명에 넣었다.

## 왜

값이 `None` 이 되어도 칸을 건드리지 않아 **직전 숫자가 화면에 남았다.** 화면만 보고는
「현재 값」과 「멈춘 옛 값」을 구분할 수 없다. `None` 이 들어오는 경로는 예외가 아니라 상시다
(`gui.py` `_on_motor_data`):

| 상황 | 종전 화면 | 지금 |
| --- | --- | --- |
| 호밍 중(약 35 초, 위치 무효) | 호밍 직전 각도가 그대로 — 축은 100°+ 도는 중 | `—` |
| 폴링 스레드 사망 | 마지막 값에 얼어붙음 | `—` |
| 폴 응답에 그 객체 누락(간헐) | 직전 값 유지 | `—` (깜빡일 수 있음) |

이식본 `src/Comm/CAN/can_relay/can_relay/ui/app.py:397` 은 이미 `—` 로 덮어쓰고 있어
**두 GUI 의 표시 규칙이 갈려 있었다.** 이제 같다.

⚠ **남는 부작용(의도된 것)**: 회전·전류 칸은 폴 응답에서 그 객체가 간헐적으로 빠지면 잠깐
`—` 로 바뀔 수 있다. 실기에서 거슬리면 각도 칸만 덮는 절충으로 좁힌다.

## 시험 — 종전 회귀는 이 동작을 고정하지 못했다

`test_none_leaves_the_cell_untouched` 는 **빈 표**(초기값이 이미 `—`)에서 한 번만 채워 판정해
**덮어쓰기·건너뛰기 두 동작 모두 통과**했다. 이름과 주석만 「덮어쓰지 않는다」였다.

- **T7** `test_none_overwrites_the_cell_with_a_dash` — 숫자를 먼저 써 넣은 뒤 `None` 을 주어
  두 동작이 갈라지게 했다.
- **T7a** `test_both_guis_render_missing_values_the_same` — 이식본과 같은 규칙인지 소스 대조.

## 검증

| 항목 | 결과 |
| --- | --- |
| `Tools/amr_test_gui` 전체 회귀 | **155 passed** (종전 154 + 신규 2 − 대체 1) |
| 돌연변이 — 옛 동작(`if val is not None`) 복원 | **T7·T7a 2건 실패** → 검출 확인, 원복 완료 |

## 후속 갱신

- 함수표 `#21 MainWindow._fill_row` — 기능 서술을 코드에 맞추고 줄 앵커를 `gui.py:615-626` 으로
  갱신(루트 정본 + 패키지 병기). ⚠ **표는 원래 「`None` 은 `—`」로 적혀 있었다** — 즉 표가 맞고
  코드가 틀린 상태였다.
- `test_gui_tables.py` 함수표(T1~T9) 신설 — 인벤토리 게이트가 이 파일 수정을 막아, 우회하지 않고
  `docs/code_review/can_relay_ui/2026-08-14.md` §3-1 에 등재한 뒤 진행했다.
- 이슈 로그 `docs/issues_and_fixes/issues_and_fixes.md` 최상단 prepend.
