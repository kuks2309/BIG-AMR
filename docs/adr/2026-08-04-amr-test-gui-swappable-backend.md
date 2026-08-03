# ADR 2026-08-04 — 시험 GUI 를 UI 1벌 + 교체 가능한 백엔드 2종으로 재구성

- **Status**: Accepted — 2026-08-04 (사용자 요구: 「기존 UI 구성과 100% 동일하고 BACKEND만 선택해서
  ROS2 와 기존 python 으로 구동」 · 「호밍 취소 기능은 사용안함」). **실기 검증 0** — 실기 비교는 사용자가 수행.

## Context

`docs/adr/2026-08-03-amr-test-gui-ros2-port.md` 로 ROS2 이식본을 만들었고, 원본
`Tools/amr_test_gui/gui.py` 는 비교 기준선으로 존치 중이다(debt-039). 그런데 **UI 가 2벌**이라
실기에서 차이가 나와도 그것이 **백엔드 차이인지 UI 차이인지 가릴 수 없다.**

사용자가 실기 비교를 직접 수행하기로 했고, 조건을 정했다 — **UI 는 기존과 100 % 동일**하게 두고
**백엔드만 골라서** ROS2 경유 / 판다 직결로 돌릴 것.

경계는 이미 그어져 있다(2026-08-03 인벤토리):

| | 원본 `gui.py` (1,157줄) | 이식본 `gui_node.py` (1,010줄) |
|---|---|---|
| CAN·판다를 직접 만지는 함수 | **11개** | 0개 |
| 화면만 만드는 함수 | 16개 | 동일 구성 |
| 백엔드 경계 | 없음(섞임) | **있음** — `RelayClient` |

## Decision

**① UI 1벌 + 백엔드 2종.** `can_relay/ui/` 를 넷으로 나눈다:

| 파일 | 역할 |
|---|---|
| `backend_base.py` | 인터페이스 + **capability 선언** |
| `backend_ros2.py` | 드라이버 경유(현행 `RelayClient` 이전) |
| `backend_direct.py` | 판다 직결(원본 `gui.py` 의 11개 함수 이식) |
| `app.py` | `MainWindow` — 위젯 트리 **원본과 동일**, 백엔드 주입 |

```bash
ros2 run can_relay can_relay_gui --backend ros2      # 드라이버 경유
ros2 run can_relay can_relay_gui --backend direct    # 판다 직결
```

**② 호밍 취소 버튼을 만들지 않는다 — 취소에 얻는 이득이 없기 때문이다.**

사용자 판단: 「실제 호밍이 필요해서 하는데 왜 취소를? 해서 얻는 이득이 뭔지? **만들었지만 사용은
안하도록**」. 호밍은 조향 0° 기준을 세우려고 **필요해서** 하는 동작이고, 중간에 끊으면 축이
어중간한 위치에 남아 **어차피 다시 호밍해야 한다** — 취소의 산출물이 「다시 해야 하는 상태」뿐이다.
소요도 10회 실측 **35.0 s**(편차 0.17 s)로 짧다(debt-034).

⚠ 드라이버의 `~/home_cancel` **서비스와 회귀는 남긴다**(만들었지만 안 쓴다). **UI 에 노출만 안 한다.**

⚠ **정직한 부기 — 이 결정은 2026-08-03 H1 수정의 명분을 약화시킨다.** 그 수정(콜백 그룹 분리 +
MultiThreadedExecutor)의 가장 강한 근거가 「호밍 중 `~/home_cancel` 이 도달해야 한다」였다
(`docs/adr/2026-08-03-can-relay-node-concurrency.md` §Context H1). 취소를 안 쓰면 남는 이득은
**호밍 중에도 진단·`joint_states` 발행이 계속되고 `~/stop`·`estop`·`~/engage false` 가 소비된다**는
것으로 좁아진다. 그래도 되돌리지 않는다 — 이미 구현·회귀돼 있고 유지 비용이 0이며, 되돌리면
「호밍 180 s 동안 노드가 아무 콜백도 처리 못 한다」로 돌아가기 때문이다.

**③ 연결부 3버튼(판다 검색·USB 연결·제어권)은 원본 그대로 두고, capability 로 처리한다.**

| 버튼 | direct | ros2 |
|---|---|---|
| 판다 검색 | 동작(열거) | **비활성** — "드라이버가 소유" |
| USB 연결 | 동작(개방) | **비활성** — "드라이버가 소유" |
| 제어권 | safety 30 → auth → intercept | `~/engage` |

근거: 검색·USB 개방은 **CAN 프레임을 한 장도 만들지 않는다**(USB 열거·장치 개방뿐). 따라서
실기 **바이트 비교에 영향이 없다.** 반대로 이것을 진짜로 동작시키려면 드라이버에 `~/scan`·`~/open`
**공개 서비스 2개**를 신설해야 하는데, 얻는 것 대비 공개 표면만 늘어난다.

**④ 원본 `Tools/amr_test_gui/gui.py` 는 건드리지 않는다.** 비교 기준선이자 현재 유일하게
실기에서 돌아 본 코드다(debt-039). 대신 **`backend_direct` 가 원본과 같은 바이트를 내는지**
회귀로 고정한다(`test_port_equivalence.py` 확장).

## Alternatives (기각)

- **드라이버에 `~/scan`·`~/open` 신설** — 진짜 3버튼 동작. 공개 인터페이스 2개 증가에 비해
  비교 정확도 이득이 0(프레임 무관)이라 기각. 필요해지면 ③만 뒤집으면 된다.
- **원본 `gui.py` 를 리팩터해 백엔드를 끼우기** — UI 가 1벌이 되지만 **비교 기준선이 사라진다.**
  기준선을 고치면서 그 기준선으로 비교할 수는 없다. 기각.
- **UI 를 백엔드별로 분기(if backend == …)** — 위젯 트리가 갈려 「100 % 동일」이 깨진다. 기각.

## Consequences

**이득**: 실기에서 차이가 나오면 **백엔드 탓으로 단정**할 수 있다(UI 가 같으므로). 무엇이 다른지가
화면에 드러난다(비활성 버튼 + 사유 툴팁).

**비용 · 남는 위험**:
- 시험 GUI 코드가 **3벌**이 된다(원본 / 통합-direct / 통합-ros2). 원본↔direct 바이트 동일성을
  회귀로 묶어 드리프트를 막지만, **원본을 언제 폐기할지는 여전히 미결**(debt-039).
- `backend_direct` 는 원본 로직의 **이식**이므로 원본의 알려진 결함을 함께 옮길 수 있다 —
  특히 원본 High 4건(정착 신선도 부재 · heartbeat 락 밖 · 단발 송신 · 취소 부재,
  `docs/code_review/amr-test-gui/2026-08-03.md`). **이식하면서 고치지 않는다** — 고치면
  「원본과 같은 바이트」가 깨져 비교 목적이 무너진다. 대신 **알려진 결함으로 표기**하고
  `--backend direct` 를 시험 전용으로 둔다.
- 실기 검증 0. 비교 실행은 사용자 몫이며, 이 ADR 은 그 도구를 만드는 것까지다.

## Rollback

가역. ① `setup.py` entry point 를 이전 상태로 되돌리고 ② `can_relay/ui/{backend_*,app}.py` 삭제,
③ `gui_node.py` 를 2026-08-03 판(단일 파일 ROS2 GUI)으로 복원. 드라이버(`driver_node`·`backend`·
`link`·`protocol`)는 **손대지 않으므로** 영향 없음. 원본 `Tools/amr_test_gui/gui.py` 도 무영향(④).

## Verification

구현 산출물: `can_relay/ui/` — `backend_base.py`(118) · `backend_direct.py`(352) ·
`backend_ros2.py`(286) · `app.py`(717) · `gui_node.py`(108, 진입점).

**게이트 1 — 빌드 + 무회귀 ✅**

```
$ colcon build --packages-select can_relay --symlink-install
Finished <<< can_relay [3.19s]
$ PYTHONPATH=.:$PYTHONPATH python3 -m pytest test -q     # ROS2 소싱
342 passed in 29.10s                                     # 재구성 전 306 → +36
$ PYTHONPATH=. python3 -m pytest test -q                 # 미소싱
325 passed, 4 skipped
```

**게이트 2 — 두 백엔드가 같은 계약 ✅** (`test/test_backend_swap.py`)
16개 메서드 존재 · `capabilities` 비어있지 않음 · **검색/USB 는 direct 에만, 조작 7종은 양쪽 공통** ·
`CAP_HOME_CANCEL` 이 **존재하지 않음**(취소 미노출을 상수 수준에서 고정).

**게이트 3 — `direct` ↔ 원본 바이트 동일 ✅** (같은 파일, 장치 미개방 — `_send` 가로채기)

| 대조 | 건수 |
| --- | --- |
| 축별 조향(노드 2 × 각도 7) | 14 |
| 전축 조향(crab) | 3 |
| 구동 속도·부호·상한 | 5 |
| **조그 8방향 전체**(원본 `JOG` 표 사용) | 8 |
| 호밍 3프레임 시퀀스(+ 선행 구동 0) | 1 |
| 상수 일치(홈·counts/도·환산·상한·safety·버스) · UI `JOG` 표 일치 | 2 |

⚠ 호밍 대조는 **기대값을 두 번 만에 맞췄다** — 원본이 호밍 **전에 구동 0 을 먼저 보내는 것**
(`gui.py:954`)을 빠뜨렸다가 시험이 잡았다. 구현이 아니라 기대값이 틀렸던 것이다.

**게이트 4 — 양쪽 오프스크린 기동·종료 ✅**

```
--backend ros2   : 기동 확인 → SIGTERM → 0.50 s 종료 (해제 사슬 로그 정상)
--backend direct : 기동 확인 → SIGTERM → 0.25 s 종료
                   검색 — 판다 검출: 1e003e001351333033383534   ← 열거만, USB 미개방
```

⚠ 구현 중 결함 1건: `backend_direct._KIT` 를 `dirname` 6회로 계산해 `.../src/Tools/...` 를 가리켰고
`ModuleNotFoundError: No module named 'panda'` 가 났다. **오늘 세 번째 같은 off-by-one** 이라
`link.py:_find_repo_root`(마커 탐색)로 교체했다.

**게이트 5 — ❌ 실기 비교는 이 ADR 범위 밖** — 사용자가 수행한다. 권장 방법은 코드 로그가 아니라
**송신 0건 수동 CAN 탭**으로 양쪽 실행을 각각 캡처해 바이트 대조하는 것이다
(`Tools/docking_field_kit/orin_steer_crosscheck.py` 계열).
