# 2026-08-15 — 이 세션 코드의 주석 전면 재작성 + 검출력 검사기 정직화

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md` §4, `hooks/coding-comment-gate.py`).
> 약어: DI(Digital Input) · SOP(Standard Operating Procedure)

- 사용자 지시: 2026-08-15 「주석은 거짓이 많고 그것 때문에 엉터리 소스가 나와서 기술 부채가
  엄청납니다. 이 세션과 관련된 코드의 주석은 모두 삭제하고 다시 만들어야 합니다. 규칙에 맞도록」
- 등록 부채: `debt-075`(지능, `debt-071` 재발) · `debt-076`(기술, 검사기 거짓 초록)

## 무엇이 거짓이었나

`can_relay/home_and_zero.py` 모듈 docstring 이 드라이버 동작을 단정했다 —
「드라이버는 호밍 실패를 조향 게이트로 막지 않는다. `homed_effective()` 가 `0x6041` bit15
만으로도 True 를 돌려준다」. 그러나 그 파일을 커밋하기 전에 커밋 `54ceea4` 가 드라이버에
`_home_failed` 래치를 넣어 이미 막고 있었다. **작성 시점에 이미 거짓**이었다.

원인은 워크트리 base(`27360f5`, 05:54)를 최신화하지 않은 채 그 시점의 관측을 현재형 사실로
적은 것이다. `54ceea4` 는 11:40 이었다.

같은 파일군에 이력 서술도 있었다 — `test_steer_zero_return.py` 의
「종전에는 … 육안에 위임했다. 그 문장이 사실이 아니었던 것이 이 작업의 출발점이다」.

## 무엇을 했나

주석을 **삭제하고 다시 썼다**(덧붙여 정정하지 않았다). 규칙은 conventions §4 —
현재 코드의 사실, 단위·근거·비자명한 의도만. 6파일:

| 파일 | 걷어낸 것 | 남긴 것 |
| --- | --- | --- |
| `can_relay/can_relay/home_and_zero.py` | 드라이버·펌웨어 동작 단정 전량(모듈 docstring 12줄) | 이 클라이언트가 무엇을 호출·발행·판정하는지, `client` 계약, 종료코드 |
| `can_relay/test/test_home_and_zero.py` | 타 계층 단정, 상수 이름 `GOZERO_OFFSET_DEG` | 고정하는 계약 5개, `SETTLE_OFFSET_DEG` |
| `can_relay/mutation_check.py` | — | 도구 동작 서술만 |
| `Tools/amr_test_gui/gui.py` | `STEER_ZERO_TOL_DEG` 주석의 펌웨어 정착값 인용 | 허용치의 단위와 **선택값임을 명시** |
| `Tools/amr_test_gui/test/test_steer_zero_return.py` | 이력 서술, 타 계층 단정, 폐기된 시험명 참조 | 계약 7개(타 세션이 추가한 ⑤⑥⑦ 포함), `SETTLE_COUNTS` |
| `Tools/amr_test_gui/mutation_check.py` | — | 도구 동작 서술만 |

기계 검증: `Tools/comment_check/check_comments.py --checks anchor,path,symbol,const,history`
→ 6파일 **불일치 0건**. (`history` 는 기본 미포함 옵션이라 이번에 명시적으로 켰다.)

## 검사기 정직화 (`debt-076`)

`Tools/amr_test_gui/mutation_check.py` 가 두 가지 거짓 초록을 냈다.

1. **기준선 실패 무시** — 검출을 `pytest` 종료코드로만 판정해, 선존재 실패가 1건이라도 있으면
   모든 돌연변이가 `✅ 검출` 로 찍힌다. 워크트리 실측 기준선은 7건이었다.
2. **0건 선택** — 없는 id 를 주면 아무것도 돌지 않고 `✅ 0개 항목 전부 검출` 을 냈다.

고친 뒤: 원본 상태의 실패 집합을 먼저 재고 **새로 깨진 시험이 있을 때만** 검출로 인정한다.
선택 0건은 `검사 불가`로 `exit 1`. 즉시 효과가 나왔다 — 종전이면 `✅` 였을 `M5` 가 미검출로 드러난다.

## `gui.py` 0° 복귀의 검출력 공백을 메웠다

`Tools/amr_test_gui/mutation_check.py` 에 0° 복귀 항목이 **없었다**. 코드(`64dac9e`)와
회귀(`test_steer_zero_return.py`)는 `main` 에 있으나 돌연변이 항목은 미병합 브랜치에만 있었다.
`Z1`~`Z5` 를 추가했다.

```
⚠ 기준선 실패 7건 — 이 시험들은 검출 판정에서 제외한다: …
✅ 검출  Z1   호밍 뒤 0° 복귀 호출 제거
✅ 검출  Z2   0° 지령을 빼고 대기만 함
✅ 검출  Z3   0° 도달 판정 허용치를 사용자 정착 허용치 수준으로 넓힘
✅ 검출  Z4   0° 미도달을 완료로 적음
✅ 검출  Z5   0° 복귀 전에 호밍 게이트를 내리지 않음
✅ 5개 항목 전부 검출
```

## 검증

```
Tools/amr_test_gui        156 passed / 7 failed   ← 순정 origin/main 과 동일(선존재, 워크트리 환경)
can_relay test_home_and_zero.py   10 passed
can_relay mutation_check.py       Z1~Z5 5/5 검출
comment_check (5종)               6파일 0건
```

`Tools/amr_test_gui` 실패 7건은 순정 `origin/main` 에서도 같은 7건이다 — 이 워크트리에 미추적
자산(panda 라이브러리 등)이 없어 생기는 환경 실패이며 본 변경과 무관하다.

## 범위 밖 — 발견만 보고한다

conventions §4 에 따라 이번 수정이 닿지 않는 선언의 주석은 고치지 않았다.

| 위치 | 내용 |
| --- | --- |
| `can_relay/ui/backend_direct.py:51` | `[path]` 인용 경로 `src/Tools` 가 저장소에 없다 |
| `can_relay/ui/backend_direct.py:263` | `[history]` 「종전에는 …」 이력 서술 |
| `Tools/amr_test_gui/gui.py:34` | 펌웨어 GOZERO 상수를 단정하는 주석(커밋 `836b0c2` 소유) |

`Tools/comment_check` 의 `history` 검사는 현재 트리에 기존 42건이 걸려 **옵트인**이다
(`debt-070`). 이번 6파일은 그 검사를 켠 상태로 0건이다.
