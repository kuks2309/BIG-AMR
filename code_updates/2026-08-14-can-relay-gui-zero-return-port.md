# 2026-08-14 — can_relay 통합 GUI 점검 + 호밍 후 조향 0° 복귀 이식·판정 결함 수정

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md`, `hooks/coding-comment-gate.py`).
> 약어: GUI(Graphical User Interface) · ADR(Architecture Decision Record) · TTL(Time To Live)

- 사용자 지시: 2026-08-14 "목적 ; can relay gui 기능 점검 / 현재 can relay 통합(ros, non ros) 구현 확인 부탁"
  → 점검 결과 보고 후 사용자 선택: 「① 0° 복귀 이식」
- 대상: `src/Comm/CAN/can_relay/can_relay/ui/backend_direct.py` · `Tools/amr_test_gui/gui.py`
  + 회귀 2파일 · ADR 부기 · 인벤토리(이중 기록)
- 결정 근거: ADR `docs/adr/2026-08-08-steer-zero-return-after-homing.md` (§2026-08-14 부기)

## 점검 결과 — 통합은 이미 되어 있다

`ros2 run can_relay can_relay_gui` 기본값이 `--backend both` 이며 **한 창에 탭 2개**다
(`ui/gui_node.py`). 위젯 트리는 `ui/app.py` 1벌이고 백엔드만 갈아 끼운다 —
`Ros2Backend`(드라이버 경유·운용) / `DirectBackend`(판다 USB 직결·시험).
판다 동시 점유는 `RelayTabs` 가 탭 잠금으로 막고, Seer 폴링은 보이는 탭만 돈다.

검증(2026-08-14): 회귀 `can_relay` **410 passed** · `Tools/amr_test_gui` **152 passed**(수정 전),
오프스크린 기동 스모크에서 두 탭 생성 · direct 탭 판다 검출(`400025001751323139343439`) ·
SIGTERM 정상 해제. 설치는 심볼릭(egg-link → build → src)이라 소스가 곧 실행본이다.

## 무엇을 고쳤나 — 2건

| # | 파일 | 문제 | 조치 |
| --- | --- | --- | --- |
| 1 | `ui/backend_direct.py` | ADR 2026-08-08 의 **0° 복귀가 이 경로에만 없었다** — 완료 메시지도 폐기된 「조향 0° 복귀까지 확인하세요」(육안 위임) 그대로. 같은 창에서 **탭만 바꿔도 호밍 후 축이 서는 자리가 달라졌다** | `_steer_zero_return()` 신설 + `home()` 에 연결. 상수 `STEER_ZERO_TOL_DEG=0.1`·`STEER_ZERO_TIMEOUT_S=10.0` 은 원본과 같은 값(회귀 고정) |
| 2 | 위 + `Tools/amr_test_gui/gui.py` | 호밍 플래그를 `finally` 에서만 내려, **0° 복귀 판정 구간이 그 플래그 안에 들어 있었다.** 흡수부가 호밍 중 0x6064 를 각도로 반영하지 않으므로(그 구간의 값은 실위치가 아니라 0) 판정이 볼 실측이 **영원히 없다** ⇒ 지령은 나가지만 **항상 시한 만료·「미확인」** | 원점 신호 직후, 0° 복귀 **전에** 플래그를 내린다. `finally` 해제는 멱등이라 그대로 둔다 |

### 2번의 실측 근거 (offscreen, 원본 `gui.py`)

```
_homing=True  → _meas_angle [None, None] · _wait_settle(0°, 0.1°, 0.3s) = False
_homing=False → _meas_angle [0.0, 0.0]   · _wait_settle(0°, 0.1°, 0.3s) = True
```

같은 피드백(`_on_motor_data({n: {0x6064: STEER_HOME[n]}})`)을 넣고 플래그만 바꾼 결과다.

## 왜 종전 회귀가 못 잡았나

`Tools/amr_test_gui/test/test_steer_zero_return.py` 는 실측을 `_set_meas` 로 **직접** 세운다 —
그 자리는 흡수부의 호밍 게이트 **아래**라, 게이트가 판정을 막고 있어도 시험에는 보이지 않는다.
`test_backend_swap.py::test_direct_homing_frames_match_original` 은 **앞 8프레임만** 대조하므로
그 뒤에 0° 지령이 있든 없든 통과한다.

⇒ 새 회귀는 `_on_motor_data`·`_absorb` 를 **통과시켜** 넣는다.

## 검증

| 항목 | 결과 |
| --- | --- |
| `can_relay` 전체 회귀 | **415 passed** (58.8 s, 신규 5건 포함) |
| `Tools/amr_test_gui` 전체 회귀 | **154 passed** (36.7 s, 신규 2건 포함) |
| 돌연변이 — 플래그 해제 1줄 제거 | direct **2건**(`..._commands_the_canonical_zero`·`..._clears_the_homing_gate_before_judging`) + gui **1건**(`test_homing_flag_is_cleared_before_the_zero_return`) 실패 → 검출됨 |

신규 회귀 7건: direct `test_backend_swap.py`(0° 지령 바이트 · 게이트 해제 시점 · 실측 부재는
완료 아님 · GOZERO 정착값은 0° 아님 · 상수 원본 일치) · gui `test_steer_zero_return.py`
(흡수 게이트 기전 · 판정 시점).

## 남는 것 (이번 범위 밖 — 점검에서 확인된 것)

- **실기 미검증** — ADR Status 의 ⚠ 는 그대로다. 첫 실기는 잭업 또는 이동구역 확보 후.
- **종료 지연 ~10 초**(드라이버 부재 시) — `Ros2Backend.shutdown` 이 `stop`·`engage` 를
  서비스 탐색 기본 5 s 로 각각 시도한다. 2026-08-04 리뷰 기록은 `SIGTERM 0.50 s`.
- ~~**실사용 진입점 불일치**~~ — **철회(2026-08-14, 사용자 확인)**. `~/.bashrc` 의
  `alias can_relay` 가 단독 `Tools/amr_test_gui/gui.py` 를 띄우는 것은 **의도된 배치**이며,
  그날 실기로 검증한 것이 바로 그 GUI 다. 결함이 아니므로 bashrc 는 바꾸지 않는다.
- **`can_relay/README.md` 에 GUI 실행법 0건** — 사용법이 code_review 문서에만 있다.
