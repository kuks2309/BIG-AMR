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

## 미검증 · 후속 (부채 등록 완료)

| id | 유형 | 내용 |
| --- | --- | --- |
| **debt-075** | 기술 | **실기 미검증** — 전량 mock/순수 함수 회귀로만 확인했다. 잭업에서 ① `kill -9`(형태 ①) ② 실행기 정체 주입(형태 ③) ③ `systemctl restart` 후 복귀를 실측할 것 |
| **debt-076** | 이해 | **릴레이 개방 직후 조향 거동 미확정**(§0 ③). 되돌아간다면 crash-loop 이 조향 스윙 반복이 되므로 `StartLimitBurst` 가 유일 방어선이 된다 |
| **debt-077** | 이해 | **임계 3종이 채택값**(3회/120 s · `diag_timeout_s` 3.0 · `ros_alive_timeout_s` 2.0). 주기 배수에서 유도했을 뿐 실측 분포 기반이 아니다 — 「실측」으로 인용 금지 |
| **debt-078** | 기술 | **`test_gui_node.py` 2건이 20~30 % 간헐 실패**(본 변경 이전부터). 이 패키지 회귀 결과를 증거로 인용할 수 없게 만든다 — 본 작업이 발견했을 뿐 원인은 아니다 |

- **자기승인 없음** — 본 변경의 적정성 판정은 저자가 찍을 수 없다(coding SOP §5
  never-self-approve). 외부 리뷰 lane 대기. ADR 은 `Status: Proposed` 로 둔다.
