# can_relay 함수표 · 변수표 (모듈 로컬 권위본)

> 양식 권위는 `docs/claude_guideline/code_review/review.md` §Core 인벤토리 3·4.
> 이중 기록 — 루트 집계는 `docs/sw_structure/function_table.md`.
> 생성 사유: 2026-08-15 노드 health 감시 작업의 coding SOP §2 선행조사.
> 그전까지 `can_relay` 는 루트 집계에 **미등재**였고 `coding-inventory-gate.py` 가 빈 통과했다.
>
> **범위 한정** — 본 표는 `can_relay/backend.py` · `driver_node.py` · `health.py` ·
> `supervisor.py` · `home_and_zero.py` 를 담는다. 같은 패키지의 `link.py` · `protocol.py` ·
> `safety.py` · `ui/` 는 **미작성**이며, 그 파일들에 대해서는 게이트가 여전히 빈 통과한다.
> 등재는 별도 작업. 패키지 루트의 `mutation_check.py` 는 런타임 코드가 아니라 개발 도구라
> 본 표의 대상이 아니다.
>
> ### 앵커 권위 — `파일:줄` 은 **본 문서**가 정본이다
>
> 같은 파일의 함수표를 담은 문서가 저장소에 더 있으나 전부 **날짜=버전 스냅샷**이며,
> 그 `파일:줄` 앵커는 각 리뷰 시점 기준이라 현행 코드와 맞지 않는다. 스냅샷은 그 시점의
> 사실이므로 **소급 수정하지 않는다** — 대신 어디를 봐야 하는지를 여기서 못박는다.
>
> | 문서 | 그 시점 `backend.py` | 현행 | 앵커 상태 |
> | --- | --- | --- | --- |
> | `docs/code_review/can_relay_ros2/2026-08-03.md` (+패키지 사본) | 844줄 | 1,089줄 | 낡음 — **본 문서 이전부터** |
> | `docs/code_review/can_relay_ros2/2026-07-29.md` (+패키지 사본) | 그 이전 | 1,089줄 | 낡음 |
> | `docs/sw_structure/can_relay_ros2/2026-07-31.md` | 그 이전 | 1,089줄 | 낡음 |
>
> ⚠ 「낡음」의 시작점은 본 작업이 아니다. 2026-08-03 리뷰가 기록한 844줄과 본 작업 **착수
> 시점** 1,014줄 사이에 이미 170줄이 벌어져 있었다 — 그 구간의 변경들이 표를 갱신하지
> 않았고, 그때 `can_relay` 에 모듈 로컬 함수표 자체가 없었다(루트 집계가 「미등재」로 명시).
> 본 문서가 그 공백을 메우는 첫 표이며, 이후 변경은 §6 이중 기록으로 **여기를** 갱신한다.

## 목적

comma.ai panda 릴레이를 경유해 Tongyi 4축 서보(구동 node1·2 / 조향 node3·4)를 구동하는
rclpy 드라이버. Seer 마스터가 붙어 있는 상태에서 릴레이 intercept 로 주도권을 가져와 지령을
덮어쓴다. 정지의 근간은 **심박(`0xf3`) 상실 → 펌웨어 fail-safe**(구동 0 → 릴레이 개방)이며,
호스트가 guard RTR(Remote Transmission Request)를 낼 수 없어 그 경로가 유일하다.

---

## 1. `backend.py` — 제어 스레드 (1,089줄)

### 1-1. `NodeState` (dataclass, `:39`)

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 1 | `NodeState.fresh` | `now`, `ttl` | `bool` | `last_seen` 이 `ttl` 안인가 = 피드백 신선도 | `backend.py:52` |
| 2 | `NodeState.stationary` | `tol` | `Optional[bool]` | 연속 두 표본이 `tol` 안이면 정지. **표본 부족은 `None`(모름)** — 모름을 정지로 치지 않는다 | `backend.py:55` |

### 1-2. `RelayBackend` (`:130`)

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 3 | `__init__` | `link`, `cfg`, `log` | — | 노드 상태 dict·락·카운터 초기화. 스레드는 만들지 않는다 | `backend.py:137` |
| 4 | `start` | — | — | 제어 스레드 기동. 이미 기동/제어권 없음이면 `RuntimeError`. `allow_bringup` 이면 구동축 init 선송신 | `backend.py:181` |
| 5 | `shutdown` | — | — | **정지 먼저 → 스레드 내림** 순서 고정. 재진입 안전 | `backend.py:198` |
| 5a | `mark_ros_alive` | — | — | **ROS 실행기가** 생존을 찍는다. 제어 스레드가 부르면 의미가 없다 — 실행기가 도는지를 보는 유일한 신호다 | `backend.py:219` |
| 5b | `ros_alive_age` | `now=None` | `Optional[float]` | 생존 표시가 몇 초 낡았는가. 한 번도 안 찍혔으면 `None`(모름) | `backend.py:228` |
| 5c | `_hb_block_reason` | `now` | `Optional[str]` | 심박을 끊을 사유(송신 연속 실패 · ROS 계층 정체). 둘의 결론은 같다 — **펌웨어에 정지 위임** | `backend.py:234` |
| 6 | `set_drive_mmps` | `mmps`, `sign` | — | 구동 속도 지령. 비유한 값 거부 + **워치독 미갱신** | `backend.py:250` |
| 7 | `homed_effective` | — | `bool` | 조향 지령 허용 판정. ①우리가 호밍 ②**드라이브가 bit15=1 보고**(Seer 호밍 포함, 신선한 피드백 한정). ⚠ **`_home_failed` 가 서 있으면 ②를 인정하지 않는다** — bit15 는 「원점을 잡았다」이지 「0° 에 서 있다」가 아니다 | `backend.py:261` |
| 8 | `_not_homed_reason` | — | `str` | 조향 거부 사유. `_home_failed` 일 때는 **노드별 bit15 를 나열하지 않는다** — 전부 1 로 보이는 것이 정확히 그 래치가 있는 이유다 | `backend.py:293` |
| 9 | `set_steer_deg` | `deg` | — | 전 조향축 동일각. ±limit **클램프**(거부 아님) | `backend.py:318` |
| 10 | `set_steer_axis_deg` | `node`, `deg` | `float` | 한 축만. 반환 = 클램프 적용각 | `backend.py:345` |
| 11 | `set_motor_cmds` | `cmds` | `list[str]` | 모터 계층 raw 지령(`MotorCmdArray` 계약). 반환 = 항목별 거부 사유 — 호밍 거부 시 `_not_homed_reason()` 전문을 싣는다 | `backend.py:383` |
| 12 | `motor_states` | — | `list[dict]` | `MotorStateArray` 용 raw 피드백. 신뢰 불가 값을 감추지 않는다 | `backend.py:490` |
| 13 | `release_steer_target` | `reason` | `bool` | **우리 조향 목표를 놓는다**(프레임 미송신 = 드라이브가 마지막 목표 유지) | `backend.py:520` |
| 14 | `stop` | `reason` | — | 구동 정지. **어떤 상태에서도 수용** | `backend.py:546` |
| 15 | `stop_all` | `reason` | `bool` | 구동 0 + 조향 목표 재송신 중단 | `backend.py:569` |
| 16 | `estop` | `engage` | — | 소프트 E-stop 래치. ⚠ 하드웨어 E-STOP 대체 아님 | `backend.py:585` |
| 17 | `_home_method35` | `poll_s`, `timeout_s` | `(bool, str)` | CiA402 homing method 35. **취소 불가 경로라 기본 미채택**. 축이 움직이는 지점에서 `_home_failed` 를 세우고 **성공한 완주만** 푼다 | `backend.py:598` |
| 18 | `cancel_home` | — | `(bool, str)` | 펌웨어 시퀀서에 취소(`0x60FB:04=0`) 요청 | `backend.py:706` |
| 19 | `home` | `speed`, `poll_s`, `timeout_s` | `(bool, str)` | 조향 호밍. **물리 스윙 100°+**. 펌웨어 시퀀서(`0xea`) 경유. 개시 시 `_home_failed=True`, terminal 이 `DONE` 일 때만 해제 | `backend.py:729` |
| 20 | `snapshot` | — | `dict` | 전 상태 1회 스냅샷(락 안). 진단·감시의 **단일 창구**. `home_failed`·`hb_block_note`·`ros_alive_age` 포함 | `backend.py:794` |
| 21 | `halt_note` | — | `str` | 직전 `release_steer_target` 이 놓을 목표가 없던 사유 | `backend.py:838` |
| 22 | `bus_fault` | — | `Optional[str]` | bus_off → error_passive → error_warning 우선순위 1줄 | `backend.py:842` |
| 23 | `steer_angles_deg` | — | `dict[int, Optional[float]]` | 축별 실측각. **믿을 수 없는 축은 `None`**(0 으로 채우지 않음) | `backend.py:861` |
| 24 | `settled` | — | `bool` | 전 조향축이 목표 ±`settle_tol_deg` 안인가 | `backend.py:882` |
| 25 | `_drive_frames` | `units` | `list[Frame]` | dict 면 노드별, 정수면 전 노드 동일 | `backend.py:892` |
| 26 | `_send` | `frames` | — | 링크 송신 + `tx_count` 누적 | `backend.py:904` |
| 27 | `_write_bringup` | — | — | 구동축 init 시퀀스. **조향축 제외**(fault reset 이 0° 기준을 지운다) | `backend.py:911` |
| 28 | `_loop` | — | — | **제어 스레드 본체**. 심박·워치독·지령 재송신·폴링·수신·버스헬스를 한 스레드에서 인터리브 | `backend.py:939` |
| 29 | `_poll_bus_health` | — | — | `0xc3` 읽기 전용. 기능 부재(영구 비활성) ↔ 일시 실패(재시도) 구분 | `backend.py:1025` |
| 30 | `_drain` | — | — | 수신 처리. 판다는 fwd 여부와 무관하게 전 프레임을 올린다 | `backend.py:1058` |

**중복/유사 함수**: `stop` ↔ `stop_all` 은 의도적 분리다 — 전자는 구동만, 후자는 조향 목표
재송신까지 멈춘다. `homed` ↔ `homed_effective` 도 분리 유지(전자는 우리 호밍 여부, 후자는
드라이브 보고 포함).

### 1-3. `_loop` 내부 단계 (제어 1주기 = `1/cmd_hz` = 50 ms)

| 순서 | 동작 | 안전상 의미 | 위치 |
| --- | --- | --- | --- |
| ① | 심박(`0xf3`) — `_hb_block_reason` 이 사유를 내면 **의도적 중단** | 심박 중단 = 펌웨어에 정지 위임. 「송신이 죽었는데 심박만 뛰는」·「ROS 가 멈췄는데 심박만 뛰는」 두 상태를 막는다 | `backend.py:953-965` |
| ② | 워치독 — `cmd_timeout_s` 초과 시 구동 0 + `watchdog_trips++` | 지령원이 사라져도 드라이브가 마지막 값을 물지 않는다 | `backend.py:968-981` |
| ③ | 구동 프레임 생성 | | `backend.py:983` |
| ④ | 조향 setpoint 재송신 — **호밍 중·E-stop 중에는 안 보낸다** | E-stop 중 `0x607A` 송신 0 을 회귀가 고정 | `backend.py:966-968` |
| ⑤ | 폴링 프레임(`poll_hz`) | | `backend.py:991-994` |
| ⑥ | 송신 — 실패만 `tx_fail_streak` 로 따로 센다 | 수신·진단 예외를 섞으면 읽기 오류가 로봇을 세운다 | `backend.py:997-1002` |
| ⑦ | 수신 처리 → 버스 헬스 | | `backend.py:1003-1006` |

---

## 2. `driver_node.py` — ROS2 진입점 (550줄)

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 31 | `CanRelayNode.__init__` | — | — | 파라미터 검증(캘리브레이션 불일치 시 `ValueError` 로 기동 거부) → 링크·백엔드 → 토픽·서비스·타이머 | `driver_node.py:60` |
| 32 | `_load_msgs` | — | `(3 타입 또는 None×3)` | `trnav_msgs` 대여. 실패 시 저수준 경로를 **열지 않는다**(조용한 대체 금지) | `driver_node.py:250` |
| 33 | `_on_low_cmd` | `MotorCmdArray` | — | raw 지령 전달. 환산·기구학 없음 | `driver_node.py:268` |
| 34 | `_on_low_state_timer` | — | — | `MotorStateArray` 발행(`low_state_hz`) | `driver_node.py:290` |
| 35 | `_on_steer_deg` | `Float64` | — | 벤치 직접 조향(전축 동일각) | `driver_node.py:303` |
| 36 | `_on_steer_axis_deg` | `Float64MultiArray` | — | `[node, deg]` 축 하나. 길이·정수 검증 | `driver_node.py:310` |
| 37 | `_on_drive_mmps` | `Float64` | — | 벤치 직접 구동속도 | `driver_node.py:328` |
| 38 | `_on_estop` | `Bool` | — | E-stop 래치 전달 | `driver_node.py:335` |
| 39 | `_reject` | `why` | — | 거부 1건 계수 + 1초 throttle 경고 | `driver_node.py:339` |
| 40 | `_srv_engage` | `SetBool` | `SetBool.Response` | 참=open·acquire·start / 거짓=shutdown·release·close. 전 예외를 응답에 싣는다 | `driver_node.py:345` |
| 41 | `_srv_stop` | `Trigger` | `Trigger.Response` | 구동 0 + 조향 유지. 유지 실패 사유 전달 | `driver_node.py:370` |
| 42 | `_srv_home` | `Trigger` | `Trigger.Response` | 호밍(⚠ 물리 스윙). 결과를 응답·로그 양쪽에 | `driver_node.py:381` |
| 43 | `_srv_home_cancel` | `Trigger` | `Trigger.Response` | 진행 중 호밍 취소 | `driver_node.py:396` |
| 44 | `_on_state_timer` | — | — | `joint_states` 발행. **믿을 수 없는 축은 발행 안 함** | `driver_node.py:405` |
| 45 | `_on_diag_timer` | — | — | `snapshot()` → `DiagnosticArray` 1건. level 은 심각한 것부터 선택 | `driver_node.py:421` |
| 46 | `destroy_node` | — | — | 정지 → 제어권 반환 → 닫기 | `driver_node.py:514` |
| 47 | `main` | `args` | — | **MultiThreadedExecutor** 진입점 — 단일 스레드면 취소가 도달 못 함 | `driver_node.py:526` |

### 2-1. 콜백 그룹 배치 (취소·정지가 호밍에 묶이지 않게)

| 그룹 | 소속 | 이유 |
| --- | --- | --- |
| `_cbg_home` | `~/home` | terminal/timeout 까지 반환하지 않는 긴 콜백 |
| `_cbg_safety` | `estop` · `~/stop` · `~/home_cancel` | 유일한 취소 수단이 호밍 중 죽으면 안 된다 |
| `_cbg_engage` | `~/engage` | 스레드 join 대기 |
| (기본) | `/motor/low_cmd` · 타이머 전부 | |

⚠ 그룹 분리만으로는 부족하고 `main()` 의 `MultiThreadedExecutor` 와 **한 쌍**이다.

---

## 3. `health.py` — 감시 판정 (순수, 208줄)

ROS·하드웨어·파일쓰기 무의존. `safety.py` ← `backend.py` 와 같은 배치이며, 분리한 이유는
`conftest.py` 가 규정한 **미소싱 회귀**다 — rclpy 뒤에 판정이 갇히면 설치 없이 전 분기를
검증할 수 없다. 읽기(`/proc`·`boot_id`)는 두되 쓰기는 두지 않는다.

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 48 | `boot_id` | `path` | `str` | 부팅 식별자. 실패 시 `""`(대조를 포기하되 기록은 계속) | `health.py:75` |
| 49 | `default_state_dir` | — | `str` | tmpfs 우선 기록 위치. `XDG_RUNTIME_DIR` → `/run` → `tempdir` | `health.py:84` |
| 50 | `proc_alive` | `name`, `proc_root` | `Optional[bool]` | `/proc/*/comm` 검색. **15자로 잘라 비교**(안 그러면 긴 이름이 항상 미스 → 좀비를 사망으로 오판). 순회 실패는 `None`(모름) | `health.py:103` |
| 51 | `_as_bool` | `text` | `bool` | `"true"/"1"/"yes"` 판정 | `health.py:126` |
| 52 | `_as_float` | `text` | `Optional[float]` | 실수 변환, 실패 시 `None` | `health.py:130` |
| 53 | `parse_diag` | `values`, `level`, `message` | `dict` | KeyValue → 상태 dict(`engaged`·`estop`·**`home_failed`**·`homed_effective`·`hb_suppressed`·`steer_target_deg`·`drive_units`). **빠진 키는 넣지 않는다** — 기본값으로 채우면 「관측 못 함」과 「거짓 관측」이 구분되지 않는다 | `health.py:137` |
| 54 | `decide` | `prev`, `obs`, `cfg` | `(판정, 사유)` | **이 노드의 모든 판단.** 순서가 곧 우선순위 | `health.py:165` |

### 3-1. `decide` 판정표 (시험이 이 표를 고정한다 — `test_supervisor.py`)

| 조건 | 판정 | 행동 |
| --- | --- | --- |
| 진단 없음 · 한 번도 못 받음 | `WAIT` | 대기 |
| 진단 없음 · 경과 ≤ `diag_timeout_s` | `WAIT` | 한 주기 놓친 것을 사망으로 치지 않는다 |
| 진단 두절 · 프로세스 **있음** | `ZOMBIE` | 경보. 정지는 백엔드 심박 억제가 처리 |
| 진단 두절 · 프로세스 없음 / **확인 불가** | `DEAD` | 기록 보존. 재기동은 systemd 소관 |
| `engaged=true` | `RUNNING` | 상태 기록만 |
| `engaged=false` · **두절 없음** | `IDLE` | **수동 해제로 본다 — 되돌리지 않는다** |
| `engaged=false` · 두절 있음 · 직전 기록도 미획득 | `IDLE` | 되돌릴 것이 없다 |
| 위 + `restore_enabled=false` | `HOLD` | 복귀 비활성 |
| 위 + `estop=true` | `HOLD` | 해제 후 복귀 |
| 위 + **`home_failed=true`** | `HOLD` | **재기동이 `_home_failed` 래치를 지운다** — 자동 복귀 금지 |
| 위 + 창 내 복귀 ≥ `restart_limit` | `HOLD` | crash-loop |
| 위 전부 통과 | `RESTORE` | `~/engage true` 1회 |

## 4. `supervisor.py` — 감시 노드 (ROS 껍데기, 307줄)

**제어 경로 밖이다** — CAN 에 쓰지 않고 판다를 열지 않는다. 구독·서비스 호출만 한다.
따라서 이 노드가 죽어도 정지 보증에는 영향이 없다(정지는 펌웨어 소관). 판정은 여기 없다.

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 55 | `RelaySupervisor.__init__` | — | — | 파라미터 → 기록 경로 확보 → 구독(`/diagnostics`)·클라이언트(`<target>/engage`)·타이머 | `supervisor.py:54` |
| 56 | `_on_diag` | `DiagnosticArray` | — | 접두가 맞는 status 1건만 뽑아 현재 상태로. 다른 발행자는 무시 | `supervisor.py:112` |
| 57 | `_on_tick` | — | — | 관측 조립 → `decide` → 기록·복귀·발행. **프로세스 순회는 두절일 때만** | `supervisor.py:122` |
| 58 | `_restarts_in_window` | — | `int` | 복귀 창 안의 시도 횟수(창 밖은 버린다) | `supervisor.py:159` |
| 59 | `_restore` | — | — | `~/engage true` 1회. 진행 중 호출이 있으면 재호출하지 않는다(제어권 조작 중복 방지) | `supervisor.py:165` |
| 60 | `_on_restore_done` | `future` | — | 응답 처리 + **조향 대조 로그**(기록 목표 ↔ 복귀 시점 실측. 복원하지 않는다) | `supervisor.py:187` |
| 61 | `_save` | `state` | — | 임시파일 + `os.replace` **원자 교체**. 반쪽 JSON 은 다음 기동에서 「기록 없음」이 되어 복귀가 조용히 사라진다 | `supervisor.py:210` |
| 62 | `_load` | — | `Optional[dict]` | **`boot_id` 불일치면 폐기** — 전원 사이클을 넘긴 기록으로 복귀하면 조향 홈 기준이 없다 | `supervisor.py:237` |
| 63 | `_publish` | `verdict`, `why`, `obs` | — | 감시자 자신의 판정을 `~/status` 로 — 감시자가 도는지 밖에서 보이게 | `supervisor.py:259` |
| 64 | `main` | `args` | — | 진입점. 제어 경로 밖이라 단일 스레드 실행기로 충분 | `supervisor.py:290` |

**중복/유사 함수**: 없음. `health.py` 와 이름이 겹치는 함수도 없다(판정은 전부 위임).

---

## 5. `home_and_zero.py` — 호밍 → 조향 0° 복귀 운용 CLI (212줄)

`ros2 run can_relay home_and_zero`. `~/home` 을 호출하고 **성공한 응답을 받은 경우에만**
`~/steer_deg` 에 0.0 을 발행한 뒤 `joint_states` 로 도달을 확인한다. 판정 로직
(`ZeroReturnGuard`)은 ROS 를 import 하지 않으며 입출력을 `client` 로 주입받는다.

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 65 | `steer_angles_from_joint_states` | `names,positions,steer_nodes` | `dict` | `joint_states` 한 장 → 축별 각도(도). **실리지 않은 축은 `None`** — 매 장마다 재구성하고 누적하지 않는다 | `home_and_zero.py:25` |
| 66 | `fresh_or_none` | `angles,age_s,ttl_s` | `dict` | 마지막 수신이 `ttl_s` 를 넘거나 수신 이력이 없으면 전 축 `None` | `home_and_zero.py:47` |
| 67 | `ZeroReturnGuard.__init__` | `client,tol_deg,timeout_s,nodes` | — | 판정 파라미터 보관. `tol_deg`·`timeout_s` 기본값은 **선택값이며 실측 근거 없음** | `home_and_zero.py:74` |
| 68 | `ZeroReturnGuard.run` | — | `int` | 서비스 유무 → 호밍 → 0° 지령 → 도달 확인. **호밍 실패면 0° 를 발행하지 않는다** | `home_and_zero.py:81` |
| 69 | `ZeroReturnGuard._await_zero` | — | `int` | 두 축이 0°±`tol_deg` 안에 들어올 때까지 대기. 실측 없는 축은 도달로 치지 않는다 | `home_and_zero.py:98` |
| 70 | `_RosClient.__init__` | `node,steer_nodes` | — | `~/home` 클라이언트 · `~/steer_deg` 발행자 · `joint_states` 구독 생성 | `home_and_zero.py:124` |
| 71 | `_RosClient._on_joint_states` | `msg` | — | 받은 한 장으로 각도를 **통째 교체** + 수신 시각 기록 | `home_and_zero.py:138` |
| 72 | `_RosClient.start_clock` | — | — | 0° 대기 시계 기점(호밍 종료 시점) | `home_and_zero.py:146` |
| 73 | `_RosClient.elapsed` | — | `float` | 기점 이후 경과(초) | `home_and_zero.py:149` |
| 74 | `_RosClient.service_available` | — | `bool` | `~/home` 서비스 대기(5 s). 부재는 호밍 실패와 다른 종료코드로 갈린다 | `home_and_zero.py:154` |
| 75 | `_RosClient.call_home` | — | `(bool,str)` | `~/home` 비동기 호출·완료 대기(300 s). 반환 직후 대기 시계 기점을 찍는다 | `home_and_zero.py:157` |
| 76 | `_RosClient.send_steer_zero` | — | — | `~/steer_deg` 에 `0.0` 1회 발행(응답 없음) | `home_and_zero.py:168` |
| 77 | `_RosClient.steer_angles_deg` | — | `dict` | `spin_once` 후 `fresh_or_none` 적용값 | `home_and_zero.py:172` |
| 78 | `_RosClient.sleep` | `seconds` | — | `spin_once` 로 대기(콜백을 굶기지 않는다) | `home_and_zero.py:180` |
| 79 | `_RosClient.log` | `msg` | — | 노드 로거 | `home_and_zero.py:184` |
| 80 | `main` | `argv` | `int` | 파라미터(`tol_deg`·`timeout_s`) 선언 → 경고 → `run()` 종료코드 반환 | `home_and_zero.py:188` |

### 5-1. 종료코드

| 코드 | 이름 | 조건 |
| --- | --- | --- |
| 0 | `EXIT_OK` | 0° 도달 확인 |
| 2 | `EXIT_HOME_FAILED` | 호밍 실패 — **0° 를 발행하지 않는다** |
| 3 | `EXIT_ZERO_UNREACHED` | 0° 지령은 나갔으나 `timeout_s` 안에 도달 미확인 |
| 4 | `EXIT_NO_SERVICE` | `~/home` 서비스 부재 — 호밍도 0° 도 요청하지 않는다 |

## 전역변수표

### 모듈 전역

| 이름 | 파일 | 형 | 값/근거 | 쓰기 주체 |
| --- | --- | --- | --- | --- |
| `LATCHED_QOS` | `driver_node.py:51` | `QoSProfile` | depth1·KEEP_LAST·RELIABLE·**TRANSIENT_LOCAL**. E-stop 은 래치라 늦게 붙은 구독자도 현재값을 받아야 한다. 재기동한 노드가 구독 즉시 현재 E-stop 을 받는 근거이기도 하다 | 없음(상수) |
| `BOOT_ID_PATH` | `health.py:39` | `str` | `/proc/sys/kernel/random/boot_id` | 없음(상수) |
| `PROC_ROOT` | `health.py:40` | `str` | `/proc`. 시험이 가짜 트리를 주입하는 지점 | 없음(상수) |
| `COMM_MAX` | `health.py:41` | `int` | 15 — `/proc/<pid>/comm` 길이 한계. `system_health` 의 `expected_processes` 와 같은 제약 | 없음(상수) |
| `WAIT`·`RUNNING`·`IDLE`·`DEAD`·`ZOMBIE`·`RESTORE`·`HOLD` | `health.py:44-50` | `str` | `decide()` 판정값 7종 | 없음(상수) |

| `STEER_NODES` | `home_and_zero.py:19` | `tuple` | `(3, 4)` — 조향 노드 | 없음(상수) |
| `EXIT_OK`·`EXIT_HOME_FAILED`·`EXIT_ZERO_UNREACHED`·`EXIT_NO_SERVICE` | `home_and_zero.py:20` | `int` | `0·2·3·4` (§5-1) | 없음(상수) |
| `FEEDBACK_TTL_S` | `home_and_zero.py:21` | `float` | `1.0` — 실측을 인정하는 최대 나이(초). ⚠ 선택값이며 실측 근거 없음 | 없음(상수) |

`backend.py`·`supervisor.py` 의 모듈 전역은 **0개**다(상수는 `safety.py`·`link.py`·`health.py` 소유).

### `SupervisorConfig` 필드 (`health.py:45`)

| 필드 | 기본값 | 의미 | 비고 |
| --- | --- | --- | --- |
| `diag_timeout_s` | 3.0 | 진단 두절 판정 임계 | ⚠ `ros_alive_timeout_s`(2.0)보다 **길어야 한다** — 짧으면 감시자가 먼저 두절을 선언하고 정지는 아직 안 걸린 구간이 생긴다 |
| `restore_enabled` | `True` | 복귀 수행 여부 | `false` 면 기록·경보만 |
| `restart_limit` / `restart_window_s` | 3 / 120.0 | crash-loop 차단 | 반복 engage/release 는 그때마다 Seer 에게서 버스를 뺏었다 놓는다 |

### `RelaySupervisor` 인스턴스 상태

| 이름 | 의미 | 비고 |
| --- | --- | --- |
| `_boot` | 이 부팅의 `boot_id` | 기록 대조 기준 |
| `_prev` | 직전 기록(폐기되면 `None`) | 복귀 판단의 근거 |
| `_cur` | 현재 진단에서 뽑은 상태 | 두절이면 `None` |
| `_last_diag` | 마지막 진단 수신 시각(monotonic) | |
| `_was_down` | 두절을 겪었는가 | **수동 해제 ↔ 재기동을 가르는 유일한 신호** |
| `_restore_stamps` | 복귀 시도 시각(wall) | 기록에 실려 감시자 재기동을 넘어 유지된다 |
| `_verdict` | 직전 판정 | 변화 시에만 로그 |
| `_pending` | 진행 중 engage future | 중복 호출 방지 |

### `RelayConfig` 필드 (배선·한계·주기 — 값 정본은 `config/machine/<기체>.yaml`)

| 필드 | 기본값 | 의미 | 비고 |
| --- | --- | --- | --- |
| `drive_nodes` / `steer_nodes` | `(1,2)` / `(3,4)` | 노드 배치 | 펌웨어 `SEER_DRIVE_NODE_LO/HI` 와 일치해야 한다 |
| `cmd_hz` / `poll_hz` | 20 / 5 | 재송신·폴링 주기 | |
| `cmd_timeout_s` | 0.3 | 워치독 | 초과 시 구동 0 |
| `feedback_ttl_s` | 1.0 | 피드백 신선도 | `homed_effective` 가 이것을 쓴다 |
| `steer_limit_deg` / `steer_limit_bench_deg` | 90 / 90 | 체인용 / **벤치용** 상한 | 경로로 나눈다 — 사람이 넣는 경로는 넓히지 않는다 |
| `steer_home` | `{}` | 조향 홈 counts | **비면 조향 거부.** 코드 기본값을 두지 않는 것이 설계 |
| `allow_bringup` | `False` | 구동축 init 송신 | ⚠ 코드 기본은 False 지만 배포 YAML 은 true |
| `homing_method` | `"firmware"` | 호밍 경로 | `"35"` 는 제어권 반환 시 Seer 오독 유발이라 미채택 |
| `require_homed_for_steer` | `True` | 호밍 전 조향 차단 | |
| `tx_fail_halt` | 10 | 연속 **송신** 실패 임계 | 초과 시 **심박 중단** = 펌웨어에 정지 위임 |
| `ros_alive_timeout_s` | 2.0 | **신설** — ROS 계층 생존 표시가 이보다 낡으면 심박 중단 | `tx_fail_halt` 와 같은 계층의 장치 |

### `RelayBackend` 인스턴스 상태 (락 `_lock` 보호)

| 이름 | 의미 | 비고 |
| --- | --- | --- |
| `_drive_units` / `_drive_units_by_node` | 구동 raw 속도(전체 / 노드별) | 워치독이 0 으로 만든다 |
| `_steer_counts` | 노드별 조향 목표 절대 counts | 비면 조향 프레임을 안 보낸다 |
| `_steer_target_deg` | 마지막 조향 목표각 | 진단·감시 노출용 |
| `_last_cmd_time` | 워치독 기준 시각 | **유효 지령만** 갱신 |
| `_estop` / `_homing` / `_homed` | 래치·진행·완료 | |
| `_home_failed` | **우리가 건 호밍이 축을 움직여 놓고 끝을 못 봤는가** | 서 있으면 `homed_effective()` 가 bit15 를 근거로 쓰지 않는다. ⚠ **인스턴스 변수라 재기동으로 사라진다** — 그 구간은 감시자가 `home_failed` 관측을 복귀 차단으로 이어받는다(`health.py` `decide()`) |
| `_fault` | 마지막 루프 예외 1줄 | `None` = 정상 |
| `_running` / `_thread` | 제어 스레드 수명 | |
| `_tx_fail_streak` | 연속 송신 실패 | 심박 중단 판단 |
| `_loop_fail_streak` | 송신 외 루프 예외 연속 | 심박에 영향 없음 |
| `_hb_suppressed` | 심박을 의도적으로 끊은 상태 | 진단에 노출 |
| `_ros_alive_ts` | **신설** — ROS 계층이 마지막으로 살아 있음을 찍은 시각 | `mark_ros_alive()` 가 갱신 |
| `tx_count` / `rx_count` / `watchdog_trips` | 누적 카운터 | 락 밖 읽기 허용(진단용) |

---

## 미등재 (본 표가 덮지 않는 범위)

| 파일 | 규모 | 비고 |
| --- | --- | --- |
| `link.py` | 561줄 | 판다 전송·심박·호밍 시퀀서 USB 계약 |
| `protocol.py` | 271줄 | CAN 프레임 생성 28종 |
| `safety.py` | 167줄 | 순수 안전 게이트 |
| `ui/` 5파일 | 2,343줄 | GUI(별도 code_review 문서 보유) |

이 파일들에 대해서는 `coding-inventory-gate.py` 가 여전히 빈 통과한다.
