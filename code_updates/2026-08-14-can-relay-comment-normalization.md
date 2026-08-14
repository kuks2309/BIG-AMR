# 2026-08-14 — can_relay 주석을 함수 설명만 남기도록 정비 + 모터 값 표 표시 규칙 통일

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md` §4).
> 약어: AST(Abstract Syntax Tree) · GUI(Graphical User Interface) · PC(Personal Computer)

- 사용자 지시: 2026-08-14 "주석 오류 수정, 주석은 오직 함수 설명만되어 있어야 합니다"
  → 보존 방식 **Option A(함수 설명에 흡수)** · 범위 **can_relay 패키지 전체**
- 이어진 지시: "원격을 기준으로 다시 고치고" — 처음 작업은 4일 낡은 기반에서 했고,
  `origin/main` 이 **70 커밋** 앞서 있어 **원격 최신 위에서 다시 적용**했다.

## 규칙

| | |
| --- | --- |
| **지운다** | 날짜·수정 이력, 리뷰 항목번호(`리뷰 Medium ①`), 사용자 지시 인용, 실측 로그 파일명, 부채 id, 타 구현 줄번호 인용 |
| **남긴다(함수 설명 안으로)** | 단위·좌표계·부호 규약, 하드웨어/프로토콜 순서, 클램프 범위, 신선도 규약 — 코드에서 재도출 불가능한 것 |

## 대상 11파일

`can_relay/{backend,driver_node,link,protocol,safety}.py` ·
`can_relay/ui/{app,backend_base,backend_direct,backend_ros2,gui_node}.py` ·
`Tools/amr_test_gui/gui.py`

## 코드 무변경 보증

docstring 을 벗긴 AST 를 전후 비교하는 검사기로 확인했다. 주석은 AST 에 없고 docstring 은
벗겨 내므로, 통과는 곧 「실행 의미 불변」이다.

- 주석만 바뀐 10파일 → **10 / 10 「코드 동일」**
- `gui.py` → `_fill_row` **한 곳만** 의도된 코드 변경임을 검증(그 한 줄을 원래대로 되돌리면
  「코드 동일」이 뜨는 것으로 확인)

검사기가 실제로 사고를 1건 잡았다 — `backend.py` 의 `(debt-038)` 을 주석으로 오인해 지웠는데
그것은 **로그 문자열**(코드)이었다. 검사기가 걸러 원복했다.

## 원격 최신 위에서 다시 하며 확인한 것

원격이 이 파일들에 먼저 넣은 안전장치를 **보존**하고 그 주석까지 함께 정비했다:

| 원격이 넣은 것 | 처리 |
| --- | --- |
| `DirectBackend._write_bringup` — 구동축 브링업 | 보존. 이전 주석의 「DirectBackend 는 아직 보내지 않는다」는 원격이 이미 정정했고 그 정정을 살렸다 |
| `CMD_TTL_S` 지령 워치독 | 보존 + 주석 정비 |
| `can_recv()` 를 `_can_lock` 안으로 | 보존 |
| `set_engaged` 멱등 가드 · 재획득 시 지령 초기화 | 보존 |

## 모터 값 표 — `None` 을 `—` 로 덮어쓴다

```python
# Tools/amr_test_gui/gui.py  MainWindow._fill_row
- if val is not None:
-     table.item(r, c).setText(fmt.format(val))
+ table.item(r, c).setText("—" if val is None else fmt.format(val))
```

값이 `None` 이 되어도 칸을 건드리지 않아 **직전 숫자가 화면에 남았다.** 화면만 보고는
「현재 값」과 「멈춘 옛 값」을 구분할 수 없다. `None` 이 들어오는 경로는 상시다:

| 상황 | 종전 화면 | 지금 |
| --- | --- | --- |
| 호밍 중(위치 무효) | 호밍 직전 각도가 그대로 — 축은 100°+ 도는 중 | `—` |
| 폴링 스레드 사망 | 마지막 값에 얼어붙음 | `—` |

이식본 `can_relay/ui/app.py` 는 이미 `—` 로 덮어써 **두 GUI 의 표시 규칙이 갈려 있었다.**
이제 같다. ⚠ 회전·전류 칸은 폴 응답에서 그 객체가 간헐적으로 빠지면 잠깐 `—` 로 바뀔 수 있다.

**종전 회귀는 이 동작을 고정하지 못했다** — `test_none_leaves_the_cell_untouched` 는 빈 표
(초기값이 이미 `—`)에서 한 번만 채워 판정해 **두 동작 모두 통과**했다. 숫자를 먼저 써 넣은 뒤
`None` 을 주는 시험(T7)과 이식본과의 규칙 일치를 소스 대조로 고정하는 시험(T7a)으로 대체했다.

## 검증

| 항목 | 결과 |
| --- | --- |
| AST 코드 무변경 | **10 / 10** (+ `gui.py` 는 `_fill_row` 한 곳만) |
| `can_relay` 회귀 | **401 passed · 9 skipped** |
| `Tools/amr_test_gui` 회귀 | **137 passed** (실패 6건은 아래 참조) |
| 주석 위반 패턴 잔량 | **0** |

⚠ **`Tools/amr_test_gui` 의 실패 6건은 이 변경 이전부터 있던 것이다.** 이 브랜치의 변경을
걷어낸 순수 `origin/main` 에서도 같은 6건이 실패한다(136 passed · 6 failed → 이 브랜치
137 passed · 6 failed, 늘어난 1건은 신규 시험 T7a). 그 시험들이 요구하는 `gui.py` 수정이
커밋되지 않은 채 개발 PC 의 공유 트리에만 있다 — 시험은 올라갔는데 대상 코드가 안 올라갔다.

## 범위 밖 — 이 브랜치에 담지 않은 것

- **호밍 후 조향 0° 복귀** — 본체(ADR·`RelayBackend.steer_to_zero`·`gui.py._steer_zero_return`)가
  원격에 없다. 그 위에 얹은 이식만 올리면 direct 경로만 달라지므로 제외했다.
- **코드 리뷰 문서** — 낡은 기반으로 쓴 것이라 원격 기준으로 다시 써야 한다.
