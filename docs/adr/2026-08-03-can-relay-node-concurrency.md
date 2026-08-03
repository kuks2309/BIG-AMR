# ADR 2026-08-03 — can_relay 노드 동시성: 콜백 그룹 분리 + 다중 스레드 실행기 + USB 핸들 단일 직렬화

- **Status**: Accepted — 2026-08-03 (회귀 검증 완료 · **실기 검증 0** — 장치 접속·판다 플래시·실모터 구동 없음)

## Context

`docs/code_review/can_relay_ros2/2026-08-03.md` delta 리뷰가 High 2건을 냈고, 둘 다 **회귀로 재현**됐다.

**H1 — 호밍이 노드 전체를 붙잡는다.** `driver_node.py` 는 「진행 중 취소는 `~/home_cancel` 로 한다」를
계약으로 적어 두었고, `backend.home()` 의 docstring 은 취소 가능성을 **펌웨어 시퀀서 경로를 쓰는
유일한 이유**로 든다. 그런데

- 진입점이 `rclpy.spin(node)` = **단일 스레드 실행기**였고(`grep -rn "Executor\|callback_group" can_relay/*.py` → 0건),
- `~/home` 콜백은 `backend.home()` 의 폴링 루프에서 terminal 이나 `timeout_s`(기본 180 s)까지 반환하지 않는다.

⇒ 호밍이 도는 동안 `~/home_cancel`·`~/stop`·`estop` 이 **하나도 소비되지 않는다.** 문서화된 유일한
취소 수단이 정작 호밍 중에만 죽는다. 재현: `test/test_node_concurrency.py` 3건이 수정 전 전부 실패
(취소 서비스 5 s 무응답, 실패 경로 소요 187 s).

**H2 — `heartbeat` 만 락 밖이었다.** `link.py` 상단은 「heartbeat 를 별도 스레드에서 보내면 폴링과 USB
핸들을 경합해 실패한 이력이 있다. 그래서 송수신과 같은 스레드에서 인터리브한다」고 적는다. 그 전제는
**모든 USB 접근이 제어 스레드 하나**일 때만 성립했는데, 호밍 시퀀서(0xea/0xeb)가 들어오면서
`home()`·`cancel_home()` 이 **서비스 콜백 스레드**에서 `homing_status`·`_homing_cmd` 를 호출하게 됐다.
`send`·`recv`·`can_health`·`_homing_cmd`·`homing_status` 는 `self._lock` 안이었으나 `heartbeat` 는 밖이었다.
재현: `test/test_link_concurrency.py` 3건이 수정 전 실패(같은 핸들에 동시 전송 2건 관측).

심박 실패는 펌웨어 fail-safe(구동 0 + 릴레이 개방)로 이어진다 — 안전 방향이지만 **주행 중 예고 없는 정지**다.

## Decision

**① 콜백 그룹을 3개로 나눈다** (`driver_node.py` `CanRelayNode.__init__`):

| 그룹 | 담당 | 이유 |
|---|---|---|
| `_cbg_home` | `~/home` | 최대 180 s 잡는다 — 혼자 둔다 |
| `_cbg_safety` | `~/home_cancel` · `~/stop` · `estop` 구독 | 정지 계열은 호밍 중에도 반드시 소비돼야 한다 |
| `_cbg_engage` | `~/engage` | 스레드 join(최대 1.5 s) 대기가 있어 정지 계열과 분리 |

**② `main()` 이 `MultiThreadedExecutor` 를 쓴다.** ①과 **한 쌍**이다 — 그룹만 나눠도 단일 스레드
실행기에서는 순차 처리라 취소가 여전히 막히고, 실행기만 바꿔도 같은 상호배타 그룹이면 막힌다.

**③ USB 제어 전송을 `_ctrl()` 한 곳에서 잠근다.** `PandaLink._ctrl()` 이 `self._lock` 을 직접 잡고,
락은 `threading.RLock` 으로 바꾼다(이미 잠근 구간에서 `_ctrl()` 을 부를 수 있으므로). `heartbeat` 한
곳만 고치지 않은 이유는 `acquire`/`release`/`_rollback` 도 같은 핸들을 쓰기 때문이다 — **진입점을
막지 않고 호출자마다 막으면 다음에 추가되는 경로가 또 새어 나간다.**

**④ 심박 중단 카운터를 송신 전용으로 좁힌다.** `_tx_fail_streak` 은 `self._send()` 실패만 세고,
그 외 루프 예외는 `_loop_fail_streak` 로 분리한다(`snapshot()` 에 둘 다 노출).

## Alternatives (기각)

- **`home()` 을 비동기화**(백그라운드 진행 + 상태 조회) — 인터페이스가 바뀌어 상류 계약과 회귀를
  같이 흔든다. 지금 필요한 것은 "취소가 도달하는 것"뿐이라 채택하지 않았다. 다시 검토할 값은 있다.
- **`ReentrantCallbackGroup`** — 취소·정지는 재진입이 필요 없다. 같은 서비스가 겹쳐 들어오는 것을
  허용할 이유가 없어 각자 상호배타 그룹으로 뒀다.
- **`heartbeat` 만 락으로 감싸기** — ③의 이유로 기각.

## Consequences

**이득**

- 호밍 진행 중 `~/home_cancel`·`~/stop` 이 응답한다(회귀로 고정). 실패 경로 시험 소요 187 s → 2.8 s.
- USB 핸들 동시 전송 0 — `heartbeat` ↔ `homing_status`/`0xea`/`can_send` 조합 전부 직렬화.
- 수신 경로의 일시 오류가 더 이상 로봇을 세우지 않는다(원인 표기도 "루프"/"송신"으로 분리).

**비용 · 남는 위험**

- 실행기가 다중 스레드가 되면서 **콜백 동시 실행이 가능해졌다.** 백엔드 상태는 `RelayBackend._lock`
  으로 보호되지만, 노드 계층에 새 상태를 추가할 때는 그룹 배치를 함께 정해야 한다.
- **실기 검증 0.** 위 이득은 전부 mock 링크·rclpy 실행기 위 회귀다. 실제 판다 USB 에서의 동시 접근은
  측정하지 않았다 — HIL 게이트 전까지 「실기에서 겹치지 않는다」로 인용 금지.
- `profile_vel` 은 여전히 미반영이다(고지만 한다) → **debt-038**.

## Rollback

가역. 되돌리는 절차:

1. `driver_node.py` — `callback_group=` 인자 4곳 제거, `_cbg_*` 3줄 제거,
   `main()` 의 `MultiThreadedExecutor` 를 `rclpy.spin(node)` 로 환원.
2. `link.py` — `_ctrl()` 의 `with self._lock:` 제거, `RLock` → `Lock` 환원.
3. `backend.py` — `_loop_fail_streak` 제거 후 `except` 를 단일 카운터로 환원.
4. 되돌리면 `test/test_node_concurrency.py`·`test/test_link_concurrency.py`·
   `test_recv_failure_does_not_suppress_heartbeat` 가 다시 실패한다 — **그것이 되돌림의 대가다.**

펌웨어·영속 상태·스키마 변경 없음.

## Verification

```
$ cd src/Comm/CAN/can_relay && PYTHONPATH=. python3 -m pytest test -q
227 passed, 1 skipped in 8.83s          # ROS2 미소싱 (노드 회귀 skip)

$ source /opt/ros/humble/setup.bash && source install/setup.bash
$ PYTHONPATH=.:$PYTHONPATH python3 -m pytest test -q
230 passed in 10.40s                    # 노드 회귀 3건 포함

$ colcon build --packages-select can_relay --symlink-install
Finished <<< can_relay [3.01s]
```

수정 전 실패 근거(같은 회귀): H1 3건 실패(187 s) · H2 3건 실패(동시 전송 2건 관측).

**하지 않은 것**: 장치 접속 0 · 판다 플래시 0 · 실모터 구동 0 · 실차 주행 0.
