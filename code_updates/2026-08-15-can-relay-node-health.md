# 2026-08-15 — `can_relay` ROS2 노드 health 감시 · 상태 기록 · 복귀

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md`, `hooks/coding-comment-gate.py`).
> 약어: OOM(Out Of Memory) · PID(Process Identifier) · RTR(Remote Transmission Request) ·
> QoS(Quality of Service) · SOP(Standard Operating Procedure) · ADR(Architecture Decision Record)

- 사용자 지시(sess:fc61fd67): "can relay health 관리 방법 … 이 노드가 죽을 경우 큰 문제가
  있어서 별도로 관리해야 하고 동작이 멈출 경우 재 가동을 해야 합니다" →
  "can relay firmware는 항상 살아있고 ros2 와 통신 노드의 역활을 나누어야 함" →
  "재기동은 전 상태에 따라서 그대로 복귀입니다. 그것은 감시 노드가 기록을 해야 합니다"
- 사전승인: `docs/adr/2026-08-15-can-relay-node-health-supervision.md` (Status: Proposed)
- 인벤토리: `src/Comm/CAN/can_relay/docs/function_table.md` (**신규** — 이 패키지 최초) +
  루트 집계 `docs/sw_structure/function_table.md` 등재

---

## 0. 조사가 설계를 바꾼 지점 3건

착수 전 펌웨어·캡처를 실물로 확인했고, 그 결과가 설계를 바꿨다.

**① 노드 사망은 폭주가 아니다 — 이미 펌웨어가 세운다.**
심박 상실 1~2 s(점화 off 기준 1 Hz 틱 × 2) 뒤 `seer_stop_drives()` 가 구동 노드에
`0x60FF=0` 을 3회 쓰고 릴레이를 연다(`board/main.c:213-237`,
`board/safety/safety_seer_gate.h:554-559`). ⇒ 「재기동」의 목적은 안전 확보가 아니라
**미션 복귀**다. 그 인식이 아래 ③(재engage 분리)으로 이어졌다.

**② 재호밍이 불필요하다.** `homed_effective()`(`backend.py:212`)가 드라이브의 `0x6041`
bit15 를 신선한 피드백 조건으로 인정한다. 전원이 유지되는 한 재기동 직후 조향이 열린다
⇒ 복귀 비용이 35 s·100° 스윙이 아니라 **서비스 콜 1회**다.

**③ 조향은 펌웨어 fail-safe 대상이 아니다.** `seer_stop_drives()` 의 순회 범위가
`SEER_DRIVE_NODE_LO(1) ~ HI(2)` 로 못박혀 조향축 node3·4 를 건드리지 않는다. 릴레이 개방
후 조향의 운명은 Seer 의 `0x607A` 가 정한다. 저장소 캡처 6종(38만 프레임)을
`Tools/docking_field_kit/master_command_census.py` 로 전수 확인한 결과 Seer 는 「현 위치
유지」 패턴이며(`|목표−실측| ≤ 200 c` 가 5개 캡처 100 % · 1개 95.9 %, Halt bit8 사용 0회),
`0x607A` 를 ~36 Hz 로 상시 스트림한다. **다만** intercept 중 Seer 가 읽는 값은 engage 시점
동결본이다(`safety_seer_gate.h:88-93` · `:136-138` — `pc_authority` 상승 에지에서
`seer_freeze_snapshot()`). ⇒ 개방 직후 조향 거동은 **미확정**이며, 본 변경은 그것을
가정하지 않는다(§4 대조 로그가 운용 중 답을 쌓는다).

---

## 1. 역할 분리 — 정지는 펌웨어, 프로세스는 systemd, 상태는 감시 노드

| 층 | 담당 | 죽을 수 있는가 |
| --- | --- | --- |
| 펌웨어 | 정지(구동 0 → 릴레이 개방) | 아니오 |
| systemd | 프로세스 재기동 | — |
| `relay_supervisor` | 상태 기록·복귀 지시·좀비 검출 | 예 (**제어 경로 밖**) |

감시 노드에 정지 책임을 주지 않는 것이 핵심이다. 주면 감시자가 죽는 순간 정지 수단이
사라진다.

## 2. 사각지대 ③(좀비)을 ①(프로세스 소멸)로 환원 — `backend.py`

노드가 죽는 형태는 셋인데, 펌웨어가 볼 수 있는 것은 「백엔드 스레드가 도는가」뿐이다
(심박을 그 스레드가 내므로). ROS 실행기만 정체하면:

- `/motor/low_cmd` 미수신 → 워치독이 **구동은 0** (`backend.py` 워치독)
- 그러나 조향 setpoint 는 계속 재송신되고, `~/stop`·`estop` 은 도달하지 못한다
- 심박은 계속 나가 **펌웨어가 개입하지 않고**, 프로세스가 살아 있어 **systemd 도 안 나선다**

새 장치를 만들지 않고 기존 `tx_fail_halt` 경로를 확장했다.

| 추가 | 위치 |
| --- | --- |
| `RelayConfig.ros_alive_timeout_s`(기본 2.0, **0=판정 안 함**) | `backend.py` |
| `RelayBackend.mark_ros_alive()` · `ros_alive_age()` | `backend.py` |
| `_hb_block_reason()` — 두 사유(송신 실패·ROS 정체)를 한 곳에서 판정 | `backend.py` |
| `_hb_block_note` · `ros_alive_age` 를 `snapshot()` 에 노출 | `backend.py` |
| `start()` 가 표시를 1회 찍는다 | `backend.py` |

`start()` 에서 찍는 이유: `start()` 는 `~/engage` 콜백에서만 불리므로 그 시점 ROS 는 살아
있다. 안 찍으면 첫 진단 타이머 전에 표시가 낡은 것으로 읽혀 **기동 직후 심박이 끊긴다**.

락을 걸지 않았다. float 단일 대입/읽기는 GIL 아래에서 찢어지지 않고, 락을 걸면 제어
스레드가 ROS 콜백을 기다리게 되어 **정지 경로가 ROS 정체에 묶인다** — 막으려는 그 상황이다.

## 3. 생존 표시와 진단 노출 — `driver_node.py`

- `_on_diag_timer()` 가 **발행보다 먼저** `mark_ros_alive()` 를 찍는다(발행이 실패해도
  실행기 자체는 돌고 있었으므로).
- 진단 level 우선순위 최상위에 **심박 중단**을 추가 — 「곧 펌웨어가 세운다」는 어떤 사유보다 위다.
- KeyValue 3개 추가: `estop` · `homed_effective` · `hb_suppressed`.
  감시 노드가 `/diagnostics` **하나만 보고** 판정하려면 필요하다. 종전 `estop` 은 message
  문자열로만 드러나 파싱이 취약했다 — 문구를 고치는 순간 감시가 깨진다.
- 파라미터 `ros_alive_timeout_s` 신설 + **기동 시 결합 검증**:
  `ros_alive_timeout_s ≥ 2 / diag_hz` 가 아니면 `ValueError` 로 기동을 막는다. 표시를 찍는
  것이 진단 타이머이므로 임계가 그 주기보다 짧으면 정상 동작 중에도 심박이 끊긴다.

## 4. 감시 노드 신설 — `health.py`(순수) + `supervisor.py`(ROS 껍데기)

판정을 `health.py` 로 분리했다. `safety.py` ← `backend.py` 와 같은 배치이며, 이유는
`conftest.py` 가 규정한 **미소싱 회귀**다 — rclpy 뒤에 판정이 갇히면 설치 없이 전 분기를
검증할 수 없다. (초안은 한 파일이었고, 시험이 `ModuleNotFoundError: rclpy` 로 수집 실패해
분리했다.)

**기록 대상과 복원 대상이 다르다:**

| 항목 | 기록 | 복귀 시 | 이유 |
| --- | --- | --- | --- |
| `engaged` | ✅ | **복원** | 「전 상태 그대로」의 본체 |
| 조향 목표 | ✅ | **복원 안 함 — 대조만** | 죽어 있는 동안 Seer 가 축을 움직였을 수 있다(§0 ③) |
| 구동 속도 | ✅ | **항상 0** | 재기동이 곧 재출발이 되면 안 된다 |
| E-stop | ✅ | 복원 불요 · **engage 게이트** | `LATCHED_QOS`(TRANSIENT_LOCAL)가 자동으로 준다 |
| `homed` | ✅ | 복원 불요 | 드라이브 bit15 로 자동 복구(§0 ②) |

**기록은 `/run/can_relay/state.json`(tmpfs) + `boot_id` 대조.** 조향 홈은 전원이 켜져 있는
동안만 유효하므로, 전원 사이클을 넘긴 기록으로 복귀하면 기준 없이 제어권을 잡는다. tmpfs 가
그 사고를 구조적으로 막고 `boot_id` 가 예외 상황을 거른다. 저장은 임시파일 + `os.replace`
원자 교체 — 반쪽 JSON 은 다음 기동에서 「기록 없음」으로 읽혀 복귀가 조용히 사라진다.

**수동 해제와 재기동을 가르는 신호는 `was_down`(진단 두절 경험)이다.** 진단이 끊긴 적 없이
제어권만 내려갔다면 사람이 내린 것이므로 되돌리지 않는다 — 감시자가 운용자와 싸우면 안 된다.

**복귀 차단 3중**: `restore_enabled=false` · E-stop 인가 · 창(120 s) 내 복귀 3회 초과.
마지막이 crash-loop 방어다 — 반복 engage/release 는 그때마다 Seer 에게서 버스를 뺏었다
놓는 것이라 죽은 채 있는 것보다 나쁘다.

**부수 효과(의도)**: 복귀 시 「사망 직전 조향 목표 ↔ 복귀 시점 실측」을 로그로 남긴다.
§0 ③ 의 미확정 항목이 별도 시험 없이 운용 로그로 답을 쌓는다.

## 4-1. 자동 재기동이 지우는 안전 래치를 이어받는다 (커밋 직전 발견·수정)

**본 작업이 만든 결함이다.** 커밋하려고 `origin/main`(26커밋 앞섬) 위에 이식하다 상류
`54ceea4` 를 읽고 드러났다.

상류가 막은 사고: 호밍이 `ERR_GOZERO` 로 끝나면 축이 −리밋에 선 채 `0x6041` bit15 는 1 로
남는다. 그 자리에서 0° 지령을 받으면 **≈136.7° 움직인다.** 그래서 `_home_failed` 래치를
넣어 「끝을 못 본 호밍 뒤에는 bit15 를 조향 근거로 쓰지 않는다」로 닫았다.

그 래치는 **인스턴스 변수**다. 상류 시점에는 자동 재기동이 없어 충분했으나, 본 작업이
재기동을 자동화하면:

| 단계 | 결과 |
| --- | --- |
| 호밍 실패 | `_home_failed=True` · 조향 차단 (의도된 안전 상태) |
| 노드 사망 → systemd 재기동 | 새 프로세스 `_home_failed=False` |
| `homed_effective()` | 드라이브 bit15=1 → **조향 열림** |
| 감시자 자동 복귀 | 제어권까지 얹음 → **136.7° 스윙 경로 완성** |

⇒ 상류가 이미 `home_failed` 를 진단 KeyValue 로 내므로(`60cfbd6`) 감시자가 그것을 기록하고
**E-stop 과 같은 등급의 복귀 차단**으로 쓴다(`health.py` `decide()`). 자동 해제 경로는 두지
않았다 — 해제는 `~/home` 재수행뿐이고 그것은 100°+ 스윙을 동반하는 사람의 판단이다.

회귀 3건 추가(`test_home_failed_holds_restore` · `test_home_failed_false_does_not_block` ·
`test_parse_diag_reads_home_failed`). **돌연변이 2종 전부 검출** — 게이트 제거 / `parse_diag`
미판독 각각에서 1 failed.

⚠ **교훈**: 낡은 기준 위에서 작업하면 상류가 방금 닫은 구멍을 다시 연다. 이 결함은
「이식하다 상류 커밋을 읽어서」 드러났지 설계 검토로 드러난 것이 아니다.

## 5. 배포 — systemd 2 유닛

`src/Safety/system_health/install_service.sh` 의 규율을 따랐다(경로 유도 · 자리표시자 템플릿 ·
0644 설치 · 명시 실행 시에만 설치).

| 유닛 | Restart | 근거 |
| --- | --- | --- |
| `amr-can-relay.service` | `on-failure` + **3회/120 s 차단** | 무한 재기동은 버스를 뺏었다 놓기를 반복한다 |
| `amr-can-relay-supervisor.service` | `always` | 제어 경로 밖이라 살아나는 쪽이 순이득 |

드라이버 유닛의 자동 재기동은 `launch/can_relay.launch.py` 주석의 「재기동은 사람이
판단한다」와 충돌하지 않는다 — 그 결정의 취지는 **제어권 획득**이고, 되살아난 노드는
대기 상태이며 `PandaLink` 는 engage 이전에 USB 를 열지도 않는다.

감시자 유닛에 `RuntimeDirectoryPreserve=restart` 가 **필수**다. 없으면 감시자가 재기동될
때마다 systemd 가 `/run/can_relay` 를 지워 기록이 사라지고 복귀 기능이 무력화된다.

`config/system_health/thresholds.json` 의 `expected_processes` 에 두 프로세스를 등록했다.
그 목록은 지금까지 **빈 채로 잠들어 있었다**(Phase 3a 의 핵심 기능이 미사용 상태였다).

---

## 검증

| 항목 | 결과 |
| --- | --- |
| 신규 회귀 | `test_ros_alive_gate.py` 6건 + `test_supervisor.py` 24건 = **30 passed** |
| 패키지 전체 (ROS 소싱) | 3회 실행 — **445 passed** / **444 passed·1 failed** / **443 passed·2 failed** |
| ⚠ **「445 passed」를 증거로 쓰지 말 것** | 같은 스위트가 `test_gui_node.py` 의 2건에서 **20~30 % 확률로 실패**한다. 첫 실행의 전량 통과는 운이었다 |
| 그 간헐 실패의 귀속 | **본 변경과 무관.** `backend.py`·`driver_node.py` 만 stash 해 10회씩 대조 — **변경본 7/3 · baseline 8/2**(통과/실패). baseline 도 같은 비율로 깨진다 → **debt-078** 로 등록 |
| 인과 경로 부재(코드 대조) | 재발행 함수 `ui/backend_ros2.py:179 _republish_drive` 는 진단 level·`link_status` 를 **보지 않고** 무조건 발행한다. 본 변경이 건드린 것(진단 level·KeyValue·심박 억제)이 재발행을 막을 통로가 없다. 심박 억제도 `MockLink` 에서는 카운터만 바꾼다 |
| 패키지 전체 (미소싱) | **421 passed · 4 skipped · 4 failed** — 실패 4건은 `test_backend_swap.py` 의 `rclpy` 부재이며 **변경 전 baseline 에서도 동일**(git stash 대조). 환경 조건이지 결함이 아니다 |
| ⚠ 계측 실수 2건 | ① 첫 시도의 `PYTHONPATH=.` 가 ROS 경로를 **덮어써** 소싱을 무효화했다(`.:$PYTHONPATH` 로 정정). ② 대조 스크립트의 `set -u` 가 `/opt/ros/humble/setup.bash` 를 깨뜨려 첫 대조가 **0회 실행된 채 성공처럼 끝났다** — 빈 출력을 결과로 읽지 말 것 |
| systemd | 렌더 후 자리표시자 잔존 **0** · `systemd-analyze verify` **exit 0** |
| 설치 스크립트 | `bash -n` 통과 · dry-run 이 이 장비 경로/계정을 정확히 가리킴 |
| 임계값 설정 | `Thresholds.from_mapping` 로드 OK — `('can_relay_node', 'relay_supervisor')` |
| `system_health` 회귀 | 설정 변경 후 `python3 -m pytest test -q` → **226 passed in 12.74s** |
| 함수표 앵커 | 삽입으로 밀린 `파일:줄` 앵커 전량 재도출 · 범위 밖 앵커 **0건**(기계 대조) |

**시험이 잡은 것 1건**: 초기 `test_marking_alive_restores_heartbeat` 는 임계 0.2 s 에 표시를
단발로 찍어 실패했다. 심박 슬롯이 0.2 s 주기라 갱신 직후 슬롯을 놓치면 영원히 낡은 값으로
읽힌다. 이는 결함이 아니라 **설계가 배제한 설정**이며(§3 의 `ttl ≥ 2/diag_hz` 검증이 그
영역을 막는다), 시험을 실기 조건(주기적 갱신)으로 고쳤다.

## 6. 병합 후 — SIL 이 잡은 결함 5건 (같은 날 후속)

`main` 병합(`196c40b`) **직후 실험을 붙이자 기능이 0이라는 것이 드러났다.** 위 §검증의
「447 passed」는 참이지만, 그 447건 중 **감시자를 프로세스로 띄운 것은 하나도 없었다.**

| # | 결함 | 위치 | 증상 |
| --- | --- | --- | --- |
| 1 | `DiagnosticStatus.level` 은 rclpy 에서 `bytes` 한 바이트인데 `int()` | `health.py` `parse_diag` | 첫 진단에 크래시 |
| 2 | rclpy 로거는 **호출 지점마다 severity 고정** | `supervisor.py` `_on_tick` | 첫 `DEAD` 로그에 크래시 |
| 3 | `_prev` 미승격(기동 시 파일 1회 로드뿐) | `supervisor.py` `_on_tick` | **복귀 전면 무동작** |
| 4 | `home_failed` 게이트가 `cur` 만 검사 | `health.py` `decide` | **재기동이 지우는 값을 게이트가 따라감** — 막으려던 그 소실. ⚠ 적용 범위는 **진단 1회 도달 이후**다(아래 경계) |
| 5 | `_was_down` 을 서비스 응답으로 내림 + 판정 이름으로만 세움 | `supervisor.py`·`health.py` | 복귀 1회만 / 빠른 재기동은 표시 미발생 |

⚠ **5번의 절반은 자초분**이다 — 4번을 고치며 넣은 좀비 유예(`zombie_after_s`)가 새 구멍을
열었다. 「빠른 재기동이 유예 `WAIT` 로만 덮여 `DEAD` 를 안 거친다」는 경로를 보지 못했다.

**공통점: 5건 전부 순수 판정이 아니라 ROS 껍데기·실물 타입 경계에 있었다.** 판정을
`health.py` 로 분리한 설계는 옳았으나 **그 분리가 껍데기를 시험 사각지대로 만들었다.**
그래서 결함이 나올 때마다 판정에 해당하는 부분을 순수 모듈로 옮겼다 —
`as_level()` · `next_prev()` · `next_was_down()` · `is_outage()`. 껍데기에 남은 것은
타이머·구독·서비스 호출·파일 입출력뿐이다.

### SIL 하니스 (`Tools/can_relay_sil/sil_health.py`)

`link:=mock` 으로 드라이버·감시자를 **실제 프로세스로** 띄우고 죽이거나 멈춰 8종을 판정한다.
판다도 로봇도 필요 없다. 단위 회귀가 `decide()` 를 함수로 부른다면, 이쪽은 **프로세스 경계·
파일 기록·서비스 호출·재기동**을 실물로 통과시킨다.

| # | 실험 | 결과 |
| --- | --- | --- |
| 1 | 프로세스 소멸 → 재기동 → 제어권 복귀 | PASS |
| 2 | 실행기 정체(`SIGSTOP`) → `ZOMBIE` 판정 | PASS |
| 3 | 호밍 중 사망 → 복귀 차단 | PASS |
| 4 | 반복 재기동 → crash-loop 차단 | PASS |
| 5 | E-stop 인가 중 복귀 차단 | PASS |
| 6 | 수동 해제는 되돌리지 않음 | PASS |
| 7 | `boot_id` 불일치 → 기록 폐기 | PASS |
| 8 | 기록 원자성(반쪽 JSON 없음) | PASS |

회귀 33 → **46건**. 돌연변이 2종(게이트 제거·`parse_diag` 미판독) 검출 확인.

### 감시자 게이트의 적용 하한 (실험 9 — 경계 관측)

`home_failed` 복귀 차단은 **감시자가 그 래치를 최소 1회 관측한 뒤**에만 적용된다. 래치는
호밍 개시 순간 서지만 진단은 1 Hz 이므로, 개시 후 1초 안에 노드가 죽으면 감시자는 래치를
본 적이 없어 차단하지 못한다(실측 확인). **관측하지 못한 것을 기억할 수는 없으므로 설계상
그렇고, 결함이 아니다.**

⚠ **이것을 「구멍」으로 읽지 말 것** — 호밍 중단 자체는 3중으로 닫혀 있다:

| 층 | 수단 | 호스트 생사 |
| --- | --- | --- |
| 펌웨어 | `seer_homing_tick()` 이 `!pc_authority` 를 매 틱 확인 → `seer_home_cancel_frames()` + `ERR_ABORT` | **무관하게 성립** |
| 드라이버 | `_home_failed` 래치가 프로세스 안에서 bit15 를 조향 근거로 못 쓰게 한다 | 프로세스 생존 시 |
| 감시자 | 관측한 래치를 복귀 차단 사유로 — 재기동을 넘어 유지 | 진단 1회 도달 이후 |

세 번째 층의 하한이 위 1초다. 앞의 두 층은 그 구간에도 그대로 유효하며, 자동 재engage 는
조향을 **움직이지 않는다**(상위가 지령을 따로 줘야 한다). 상류가 같은 항목을 부채로 등록하지
않고 이력에만 남긴 판단(`code_updates/2026-08-15-failed-home-latch.md`)이 옳다 — 여기서도
부채로 올리지 않는다.

### 부수 정정 2건

**주석** — `debt-071` 판정 지점(「이 문장이 1년 뒤에도 참인가」)으로 이번 세션 주석을 감사해
**거짓 1 · 이력 3 · 과장 3** 을 제거했다. 거짓은 `~/home_cancel` 을 「실제로 일어나는 경로」라고
쓴 것으로, **저장소 결정과 정면으로 어긋났다**(「호밍 취소 기능은 사용안함」 —
`docs/adr/2026-08-04-amr-test-gui-swappable-backend.md` §②). 실수 기록
`docs/claude-mistake/2026-08-15-001` 에 등재했고, 시험 경로를 실측 실패(호밍 중 사망)로 교체했다.
⚠ 고친 뒤 **또 거짓이 나왔다**(「3분 걸린다 — 시한 180 s 가 실패 조건」 — 실제 래치는 개시
순간에 선다). 두 번 다 「검증 가능한 사실 주장을 검증 없이 주석에 쓴」 같은 형태다.

**함수표** — 코딩과 **같은 단위에서** 갱신하지 않아 사용자 지적을 받았다(§6 위반).
이후 `as_level`·`next_prev`·`next_was_down`·`is_outage` 를 추가할 때마다 표를 함께 닫았다
(64 → **68함수**, `SupervisorConfig` 4 → 5, 앵커 전량 재도출).

## 7. 실기 검증 (2026-08-15 21:16~21:45, Foil_A082 접지 상태)

**SIL 이 아니라 실판다·실드라이브·실 Seer 로 돌렸다.**

| 단계 | 결과 |
| --- | --- |
| 드라이버 기동 | ✅ 기체 `Foil_A082` 인식, 대기 상태 |
| 감시자 진단 판독·기록 | ✅ — **결함 1번(`bytes` level)이 여기서 걸렸을 지점** |
| `~/engage` | ✅ 「제어권 획득 — 판다 intercept, fail-safe 무장」 |
| `homed_effective` | ✅ `true` — Seer 가 호밍해 둔 상태를 bit15 로 인정. **재호밍 불요 실증** |
| `kill -9` → 사망 판정 | ✅ `RUNNING → DEAD` (두절 3.2 s) |
| 재기동 → **자동 복귀** | ✅ `RESTORE → 복귀 완료 → RUNNING`, `engaged: true` |
| `~/engage false` | ✅ 「제어권 반환 — passthrough」 |

### 조향 거동 — debt-076 해소, 그리고 내 경고가 과장이었음

조향 `[−90.0°, +90.0°]`(±90° = **최대 조건**)에서 `kill -9`. Seer API 1005 를 0.15 s 주기로
계측한 결과 `steer_angles: [1.571, -1.571]` **전 구간 불변 · 변화점 0건**.

⇒ 「릴레이 개방 시 engage 시점 동결본으로 되돌아간다」는 가설은 **반증**됐다. 캡처 분석이
시사한 「Seer 현 위치 유지」가 실기에서 확인됐다.

⚠ **세션 중 「0° 지령 시 ≈136.7° 스윙 가능」으로 경고한 것은 과장이었다.** 그 값은 상류가
관측한 `ERR_GOZERO` 사고(축이 −리밋에 선 채)의 크기이지 **정상 개방 시 거동이 아니다.**
두 상황을 구분하지 않고 최대값을 일반 경고로 썼다.

### 실기에서만 드러난 것 2건

**① 판다 라이브러리가 worktree 에 없다.** `Tools/docking_field_kit/panda` 는 **git 미추적**
(`git ls-files` → 0건, gitignore 도 아님 — 그냥 추가된 적이 없다)이라 새 worktree·클론에
딸려오지 않는다. 첫 `~/engage` 가 `LinkError` 로 **깨끗이 거부**되고 노드는 살아남았다(정상
거동). 다만 상주 서비스로 설치해 놓고 첫 호출에서야 알게 되므로, `install_service.sh` 에
설치 시점 경고(`warn_if_no_panda_lib`)를 넣었다. **추적 여부 자체는 벤더 코드 정책이라
사용자 결정 사항으로 남긴다.**

**② `zombie_after_s` 6 s 가 실기 기동 시간보다 짧았다.** 실기 재기동은 프로세스 등장 →
첫 진단까지 **30 s** 가 걸려(오버레이 소싱 포함) 그 구간이 `ZOMBIE — ROS 계층 정체` 로
분류됐다. 동작은 옳았으나(복귀 성공) **문구가 오해를 부른다.** 기본값을 **45 s** 로 올리고
`WAIT` 문구를 「기동 중일 수 있다」로, `ZOMBIE` 문구를 「기동 지연이 아니라 정체로 본다」로
고쳤다. SIL 은 mock 기동이 빨라 이 특성을 못 봤다.

## 8. 복귀 영구 차단 결함 (2026-08-16)

사용자 지적: 「이건 심각한 결함임, 이상이있으면 자동으로 복귀하게 해야 하는 것임」

`_restore()` 의 중복 방지 가드가 `self._pending.done()` 만 본다. `rclpy` 의 `call_async`
future 는 **응답이 와야만** 완료되고 **자체 시한이 없다** — 대상이 죽으면 `done()` 이
영원히 False 라 **이후 모든 복귀가 조용히 차단**된다. crash-loop 이 정확히 「복귀 직후
다시 죽는」 상황이라 발생 조건이 현실적이다.

`health.py` 에 `restore_call_expired()` 를 두고(`restore_call_timeout_s`, 기본 10 s),
껍데기는 호출 시각을 기록해 시한 초과 시 future 를 버리고 재시도한다.

### 시험을 세 번 다시 만들었다

| 차수 | 방식 | 왜 무효였나 |
| --- | --- | --- |
| 1 | 복귀 지시 로그 직후 `kill` | 그 시점엔 응답이 이미 도착(실기 engage ~7 ms) — **수정을 빼도 통과** |
| 2 | 스텁을 실드라이버와 병행 | 같은 서비스명을 공유해 실드라이버가 8 ms 에 응답 — **조건 미형성** |
| 3 | 감시자 `target_node` 를 스텁 전용 이름으로 | 성립 |

3차에서 **수정본 PASS · 수정 제거 FAIL** 을 확인하고서야 「고쳤다」고 판단했다.
1차를 그대로 뒀다면 **결함이 있는 채로 초록 시험**을 갖게 됐을 것이다.

### 부수 — 하니스가 실패 로그를 지우고 있었다

`--keep` 없이 돌린 실험이 실패하면 임시 디렉토리가 삭제된다. 진단하려고 최신 디렉토리를
집으면 **이전 실행분**이 잡히고 그 로그가 그럴듯해 잘못된 결론으로 간다 — 같은 세션에서
**3회** 발생했다(그중 한 번은 「판정 쪽이 틀렸다」로 결론낼 뻔했다). 실패 시엔 `--keep`
여부와 무관하게 보존하고 경로를 출력하도록 고쳤다.

### 남은 개선 3건 (미착수)

- `_restarts_in_window` 가 조회하면서 `_restore_stamps` 를 잘라낸다(부작용)
- 기록을 변화 없이도 2 Hz 로 쓴다(하루 172,800회)
- 판다 라이브러리 부재가 `~/engage` 때만 드러난다 — `link:=panda` 면 기동 시 import 검사 가능

## 9. 모델 교체 후 재검토 (2026-08-16) — 신규 결함 2건 + 하니스가 잡은 제품 결함 1건

사용자 지시로 검토 주체를 교체하고 코드 전체를 처음부터 재검토했다.

**R1 — 버린 future 의 늦은 콜백 경합.** `_on_restore_done` 첫 줄이 무조건
`_pending_since = None` 이라, 시한 초과로 버린 호출의 콜백(태스크로 미뤄질 수 있음)이
**새 호출의 송신 시각을 지운다** — §8 에서 닫은 영구 차단이 다른 문으로 되살아난다.
신원 검사(`future is not self._pending`)로 닫았다. 현재 humble 에서 인라인 실행이라
증상이 안 났던 것은 구현 우연이다.

**R2 — 항상 None 을 찍는 대조 로그.** `self._cur = None` **직후에 그 값을 읽어**
`복귀 시점 None°` 만 찍을 수 있는 죽은 로직. 실기에서 안 드러난 건 `was` 도 None 이라
로그 자체가 안 찍혔기 때문. 「죽은 동안 축이 움직였는지」는 목표값 비교로 알 수 없으므로
(재기동 직후 목표는 지령 전까지 None 이 정상) 기록된 목표만 남기게 축소했다.

**R3 — 재기동 직후 latched E-stop 도착 전 복귀 (제품 결함, 보강된 하니스가 검출).**
보강 후 처음으로 10종이 전부 실행된 회차에서 실험 5 가 FAIL — 로그가
`ZOMBIE → RESTORE → 복귀 완료` 를 estop 발행 중에 보여 줬다. 첫 진단이 latched 재전달보다
빨라 `estop=False` 로 판정된 것. `restore_settle_s`(기본 3 s) 안정화 창을 `RESTORE` 허가
직전에만 두어 닫았다 — 차단 게이트는 안정화 전에도 동작한다(막는 쪽은 항상 안전).
이전의 실험 5 통과들은 전달 타이밍 운이었다.

곁들여: 실험 1 의 CLI 시한(부하 시 discovery 20 s 초과)은 하니스 결함이라 40 s + 1회
재시도로 보강. 실험 4 는 안정화가 주기를 늘리므로 복귀창을 20 → 30 s 로.

교훈은 §6·§8 과 같다 — **보강된 하니스(실패 시 로그 보존·전 실험 완주·실패 재출력)가
아니었으면 R3 는 또 우연히 통과했을 것이다.**

## 10. 품질 정리 3건 (2026-08-16)

§8 에서 미착수로 남긴 개선을 닫는다.

- **조회 부작용 제거** — `_restarts_in_window()` 가 세면서 목록을 잘라내던 것을 분리:
  잘라내기는 순수 `prune_stamps()`(원본 불변, 새 목록 반환)로 틱에서 명시 수행, 조회는
  `len()` 만. 판정 입력을 만드는 함수가 상태를 바꾸면 호출 순서에 결과가 달라진다.
- **변화 시에만 기록** — 무변화 상태를 2 Hz 로 재기록하던 것(하루 172,800회)을 내용
  지문(`cur` 항목 + 복귀 시각 목록, `saved_at` 제외) 비교로 생략.
- **판다 라이브러리 기동 시점 점검** — `panda_library_error()`(link.py, USB 미개방) 를
  드라이버 기동 시 호출해, 부재 시 `~/engage` 에서야 드러나던 것을 기동 로그 ERROR 로
  앞당긴다. 기동은 막지 않는다 — 크래시는 systemd 재기동 루프가 되고, 진단·대기 상태는
  그 자체로 유효하다.

## 11. main 병합 (2026-08-16)

`session/fc61fd67-sil` → `main`. 다른 세션이 같은 기간 **구 supervisor** 를 병행 수정해
(main `134b093`·`03149a9`) 충돌 4건이 났고, 다음과 같이 해소했다.

| 파일 | 해소 |
| --- | --- |
| `can_relay/supervisor.py` | **세션 판 채택**(순수 `health.py` 분리 + §6~§10 수정 전부). main 병행 수정 중 겹치는 결함(첫 전이 사망·복귀 1회 한정·복귀 미발동)은 세션 판이 이미 다른 형태로 덮는다. main 에만 있던 `_tick_guarded`(틱 예외 가드)는 세션 판에 **이식**해 유지 |
| `docs/debt/registry.md` | ID 충돌 — 양쪽이 서로 다른 부채에 `debt-079` 를 배정. main 쪽 079~086 유지, 세션 쪽(단위 회귀가 ROS 껍데기를 못 덮음)은 **debt-087 로 개번**(세션 쪽 참조는 registry 1곳뿐임을 전수 확인) |
| `docs/issues_and_fixes/issues_and_fixes.md` | 합집합 + main 쪽 2건에 「supervisor 코드 부분은 채택판으로 대체, `_tick_guarded` 만 이식 유지」 주기 |
| `docs/sw_structure/function_table.md` | 집계 행 재산정 — 93함수(+전역 8·RelayConfig 26필드·SupervisorConfig 7필드), 범위에 `home_and_zero` 포함 |

패키지 함수표는 자동 병합 결과에 **`prune_stamps`(53d)·`_tick_guarded`(56a) 행 추가** 및
supervisor 앵커 8건 갱신. main 쪽 배선 시험 1건(`test_restore_eligibility_survives_a_failed_attempt`)은 안정화 창을 몰라 실패 —
창 안 보류 0회 확인을 추가하고 창 경과를 모사하도록 적응(의도인 「재시도 영구 포기 금지」는 유지).
병합 트리 검증: colcon build OK · 단위 485 passed/9 skipped · SIL 10/10 PASS.

## 12. 실행기 정체 실기 실험 → 참여자 재생성 (2026-08-16)

debt-075 ②(실행기 정체) 실기 검증(SIGSTOP 60 s+ 주입)에서 ZOMBIE 판정은 PASS 했으나,
기상 후 **감시자가 영구 무수신으로 ZOMBIE 에 고착**되는 결함을 발견했다(신규 구독자는
수신 — 동결됐던 상대와의 DDS 참여자 세션만 사망). 판별 실험으로 엔드포인트 재구독이
무효임을 확인(같은 참여자 안 신규 구독도 무수신)하고, 수정을 **참여자 재생성**으로 올렸다:

- `health.py`: `SupervisorConfig.recycle_after_s`(15 s, 채택값) + 순수 `recycle_due()`.
- `supervisor.py`: `main()` 을 재구축 루프로 — `_recycle_wanted` 가 서면 컨텍스트·노드를
  허물고 `export_carry()` 승계(`prev`·`was_down`·stamps·`_last_diag`·판정·기록 지문)로
  재생성. 진행 중 복귀 future 는 옛 컨텍스트 소속이라 승계하지 않는다.
- 1차 구현은 이월이 `_last_saved` 초기화 전에 접근해 AttributeError 사망 — launch respawn
  이 가려서 성공처럼 보였다. 초기화 순서 정정 + carry 왕복 배선 시험 추가
  (`test_carry_roundtrip_preserves_watch_state`).

검증: 단위 487 passed · SIL 10/10 · 실기 65 s 동결 재현에서 재생성 4회 승계 연속,
ZOMBIE 45.4 s 정확, SIGCONT +1.6 s 자가 회복. 실험 기록은
`docs/verified_facts/2026-08-16-can-relay-zombie-freeze-field.md`.

## 13. systemd 실장비 검증 1차 — 드라이버 유닛 소생 결함 (2026-08-16)

debt-075 ③ 실장비 검증 중 발견: 노드 `kill -9` 시 `ros2 launch` 가 exit 0 으로 내려가
`Restart=on-failure` 가 발동하지 않고 유닛이 `inactive` 로 끝난다. 드라이버 유닛을
`Restart=always` 로 정정(수동 `systemctl stop` 은 영향 없음, crash-loop 차단은
StartLimit 유지). 유닛은 main 고정 배포 워크트리(`~/Project/Ford-CATL-AMR/Big-AMR-deploy`)
에서 설치한다 — 본 저장소 워크트리는 세션 브랜치에 서 있어 overlay 가 낡는다(실측:
감시자 실행 파일 부재로 crash-loop). 최종 검증 결과는 §14 와 verified_facts 에.

## 14. systemd 실장비 최종 검증 (2026-08-16)

배포 워크트리(`~/Project/Ford-CATL-AMR/Big-AMR-deploy`, main 고정) 기반 재설치 후 전 체인
실기 PASS — kill → `Restart=always` 소생 4 s → 감시자 DEAD → 안정화 → 자동 복귀, 총 9.6 s.
수동 해제 불개입·유닛 미-engage 기동·RuntimeDirectory 기록도 확인. 유닛 도메인은 설치
시점 셸의 `ROS_DOMAIN_ID`(이 기체 125)로 구워진다 — CLI 조작 시 명시 필요.
debt-075 는 ①②③ 전 항목 상환, 잔여는 펌웨어 fail-safe 버스 수준 직접 관측 1건.
상세: `docs/verified_facts/2026-08-16-can-relay-systemd-field.md`

## 15. 펌웨어 fail-safe 버스 수준 직접 관측 (2026-08-16) — debt-075 종결

판다가 양쪽 버스 수신 전 프레임을 호스트로 올리는 것을 이용해 별도 캡처 장비 없이
단독 도구(`Tools/can_relay_field/hb_failsafe_capture.py`)로 관측: 심박 중단 +1.60 s
(점화 off 임계 1~2 s 정합)에 드라이브 노드 1·2 의 0x60FF=0 SDO ACK 연발(펌웨어
`seer_stop_drives` 실증) + bus2 수신율 923→1485/s(릴레이 개방·Seer 전면 통과).
이로써 debt-075 의 모든 항목이 실기 상환됐다. 상세:
`docs/verified_facts/2026-08-16-can-relay-hb-failsafe-bus-field.md`

## 16. 부채 상환 — SIL 실험 11 + home_and_zero 5건 (2026-08-16)

- SIL 하니스에 실험 11(장기 두절 → DDS 참여자 재생성 → 승계 복귀) 추가.
  `RECYCLE_AFTER_S=2.5` 를 감시자 파라미터로 전달(전 시간 파라미터 명시 규칙 준수).
  돌연변이 검사: 재생성 비활성(0) 시 FAIL 확인. 전체 11/11 PASS ×2. → debt-087 축소.
- `home_and_zero` 재작성(212→314줄): monotonic 시계·파라미터 주입·멱등 재발행·
  미수용/무효/미확인 종료코드(5·6·7)·confirm 게이트. 시험 20종. → debt-084 해결.

## 17. GUI 에 감시 상태 표시 (2026-08-16)

can_relay 가 상시 감시·자동 복귀 체계로 바뀌었으므로 운용 GUI 가 그것을 보여야 한다
(사람이 누르지 않은 engage 가 화면에서 「감시 전이」로 설명되게).

- `backend_base.supervisor_status()` 계약 신설 — 기본 `None`(미지원, 직결 백엔드).
- `backend_ros2`: `/relay_supervisor/status` 구독 + 순수 `parse_supervisor_status`
  (verdict 는 KeyValue 정본), `(verdict, message, age_s)` 조회.
- `app`: 하단 상태 바 3번째 칸 — 판정별 색(7종), 미수신·두절(5 s) 구분 표시,
  판정 전이를 GUI 로그로 기록.
- 검증: 순수 파서 시험 3종 · 패키지 494 passed · 실장비 가동 중 감시자 유닛에서
  수신 확인(IDLE). ⚠ 표시 렌더링 자체는 화면 실행으로만 확인 가능 — GUI 재시작 필요.

## 18. 타 PC 이식 — lgit-c6-4 · amap-server (2026-08-16)

- `install_service.sh` 에 `MACHINE_YAML` 오버라이드 신설(유닛 ExecStart 에
  `machine_file:=` 주입) — 타 기체 설치의 전제.
- lgit-c6-4(같은 Foil_A082 의 팔 PC, QD 주행계·판다 실재): 코어를 정본 2026-08-16 판으로
  갱신(감시자·home_and_zero·SIL·field 도구 포함), 포크 유지 경계 확정(config·app·
  backend_direct·기체 결합 시험). 판다 라이브러리는 패키지 동봉 vendor 를 Tools 경로로
  링크. 검증: 표적 282 passed · **SIL 11/11 PASS**. 유닛 설치는 sudo 라 사용자 몫.
- 포크에서 정본으로 역이식: `wheel_axis`(바퀴 그림 좌우반전 결함 수정 — 정본에 실재하던
  거울 결함) + 화면 규약 시험. 정본 512 passed.
- amap-server 의 정본 저장소(`LGIT-C6-Cobot`)에 이식 커밋 `0c2a3de`.
- 적용 가이드: `docs/deployment/2026-08-16-can-relay-supervision-deploy.md` (3개 PC).
- UI 포크 분기는 debt-100 으로 등록.

## 미검증 · 후속 (부채 등록 완료)

| id | 유형 | 내용 |
| --- | --- | --- |
| **debt-075** | 기술 | **실기 미검증** — 전량 mock/순수 함수 회귀로만 확인했다. 잭업에서 ① `kill -9`(형태 ①) ② 실행기 정체 주입(형태 ③) ③ `systemctl restart` 후 복귀를 실측할 것 |
| **debt-076** | 이해 | **릴레이 개방 직후 조향 거동 미확정**(§0 ③). 되돌아간다면 crash-loop 이 조향 스윙 반복이 되므로 `StartLimitBurst` 가 유일 방어선이 된다 |
| **debt-077** | 이해 | **임계 3종이 채택값**(3회/120 s · `diag_timeout_s` 3.0 · `ros_alive_timeout_s` 2.0). 주기 배수에서 유도했을 뿐 실측 분포 기반이 아니다 — 「실측」으로 인용 금지 |
| **debt-078** | 기술 | **`test_gui_node.py` 2건이 20~30 % 간헐 실패**(본 변경 이전부터). 이 패키지 회귀 결과를 증거로 인용할 수 없게 만든다 — 본 작업이 발견했을 뿐 원인은 아니다 |

- **자기승인 없음** — 본 변경의 적정성 판정은 저자가 찍을 수 없다(coding SOP §5
  never-self-approve). 외부 리뷰 lane 대기. ADR 은 `Status: Proposed` 로 둔다.
