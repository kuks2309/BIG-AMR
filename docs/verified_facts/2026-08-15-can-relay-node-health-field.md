# 2026-08-15 실기 검증 — `can_relay` 노드 health 감시·복귀

> 실험 기록. **결론만이 아니라 조건·원자료·반증된 가설까지 남긴다.**
> 코드 주석은 이 문서를 근거로 삼되 수치 서사를 복제하지 않는다(`conventions.md` §4).
> 관련 변경 이력: `code_updates/2026-08-15-can-relay-node-health.md`
> 관련 설계: `docs/adr/2026-08-15-can-relay-node-health-supervision.md`

## 조건

| 항목 | 값 |
| --- | --- |
| 기체 | Foil_A082, **접지 상태**(잭업 아님), 주변 비움 |
| 시각 | 2026-08-15 21:16~21:45 (KST) |
| 코드 | `session/fc61fd67-sil` @ `1d264a4` 시점 |
| 실행 트리 | `Big-AMR-sil`(worktree). 판다 라이브러리는 공유 트리에서 심볼릭 링크 |
| 판다 | `lsusb` `bbaa:ddcc comma.ai panda` |
| Seer | 응답함(192.168.44.82). **작업 유휴** — `task_status: 0`, `target_id: ""` |
| 초기 자세 | 위치 x=−13.3745 y=12.8474 angle=−3.1392 · **조향 node3 −90.0° / node4 +90.0°** |
| 동시 실행 | mcl2d_localization · sick 라이다 2 · dual_laser_merger · icp_odometry · can_relay_gui(판다 미점유) |

⚠ **조향이 ±90°(제자리 회전 자세)였다.** 이것이 이 실험을 「최대 조건」으로 만든다 —
릴레이 개방 시 조향이 0° 로 되돌아간다면 양 축 90° 씩 움직여야 한다.

## 절차

1. `ros2 launch can_relay can_relay.launch.py` (드라이버, 대기 상태)
2. `ros2 launch can_relay relay_supervisor.launch.py state_dir:=/tmp/relay_field`
3. `~/engage true` — 제어권 획득
4. Seer API 1005 를 **0.15 s 주기로 45 s** 계측 시작(조향각 궤적)
5. `kill -9 <can_relay_node>` — 심박 상실 유도
6. 드라이버 재기동(수동) → 감시자 자동 복귀 관측
7. `~/engage false` → 프로세스 정리 → 상태 원복 확인

## 관측

### O1. 조향은 릴레이 개방에도 움직이지 않는다

Seer API 1005 `steer_angles` 를 45 s 동안 0.15 s 주기로 표본.

| | 값 |
| --- | --- |
| 전 구간 | `[1.571, -1.571]` |
| **변화점** | **0건** |

`kill -9` 전·후·재기동 후 모두 동일. 우리 노드의 `/joint_states` 도 복귀 후
`-1.5707954 / +1.5707957 rad` 로 kill 전과 일치(1e-6 rad 이내).

### O2. 감시·복귀 전 경로 동작

```
IDLE → RUNNING                    (~/engage true 직후)
RUNNING → DEAD                    진단 두절 3.2 s · 프로세스 없음
DEAD → ZOMBIE                     진단 두절 30.2 s · 프로세스는 살아 있다
ZOMBIE → RESTORE                  직전 상태가 제어권 보유였다
복귀 지시 → 복귀 완료             /can_relay_node/engage true
RESTORE → WAIT → RUNNING          제어권 보유
```

기록 파일(`state.json`): `engaged: true` · `home_failed: false` ·
`homed_effective: true` · `hb_suppressed: false` · `message: 정상`.

### O3. 재호밍 없이 조향이 열렸다

`~/engage` 직후 `homed_effective: true`. 우리가 호밍한 적이 없으므로 근거는
**드라이브가 보고하는 `0x6041` bit15**(Seer 가 호밍해 둔 상태)다.

### O4. 재기동 소요 — **프로세스 등장 → 첫 진단 30 s**

`DEAD`(두절 3.2 s) 이후 `ZOMBIE`(두절 30.2 s)를 거쳐 복귀했다. 즉 새 프로세스가
`/proc` 에 보이기 시작한 뒤 진단이 나오기까지 **약 30 s**. `ros2 launch` +
오버레이 소싱 + 노드 초기화가 포함된 값이다.

### O5. 판다 파이썬 라이브러리가 worktree 에 없다

첫 `~/engage` 가 실패:

```
success=False, message='LinkError: panda 라이브러리를 찾지 못했다 —
  .../Tools/docking_field_kit/panda: 없음 / .../Tools/Can_Relay/panda-firmware/python: 없음'
```

`git ls-files Tools/docking_field_kit/panda` → **0건**(gitignore 도 아니고 추가된 적 없음).
노드는 죽지 않고 대기 상태를 유지했다. 공유 트리에서 심볼릭 링크 후 재시도해 성공.

## 판정

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| 릴레이 개방 시 조향 거동 | **움직이지 않는다** | O1 (±90° 최대 조건, 변화점 0/300 표본) |
| 감시·복귀 경로 | **동작** | O2 |
| 재호밍 필요성 | **불필요** | O3 |
| 펌웨어 fail-safe 실효성 | **미판정** | 아래 참조 |

## 반증된 가설

**「릴레이 개방 시 조향이 engage 시점 동결본으로 되돌아간다」 — 반증됐다.**

근거였던 것: 펌웨어가 `pc_authority` 상승 에지에서 `seer_freeze_snapshot()` 을 돌리고
intercept 중 motion 객체(`0x6064` 등)에 동결본을 돌려준다(`safety_seer_gate.h`). 여기서
「Seer 가 동결된 위치를 목표로 삼다가 개방 시 그리로 되돌린다」를 추론했다.

실측은 그 추론을 지지하지 않는다 — 개방 후에도 조향은 그 자리에 있었다.

⚠ **「0° 지령 시 ≈136.7° 스윙 가능」이라는 경고는 과장이었다.** 그 값은 상류가 관측한
`ERR_GOZERO` 사고(축이 −리밋에 선 채 bit15=1)의 크기이지 **정상 개방 시 거동이 아니다.**
두 상황을 구분하지 않고 최대값을 일반 경고로 쓴 것이 잘못이다.

## 미판정으로 남는 것

- **심박 억제 경로 단독 검증** — 이번은 프로세스가 소멸해 심박이 **자연히** 끊겼다.
  `ros_alive_timeout_s` 에 의한 **의도적 억제**가 fail-safe 를 부르는지는 별개 조건이다.
- **펌웨어가 실제로 `0x60FF=0` 을 썼는가** — 관측 수단이 없었다(우리 노드가 죽어 CAN 을
  못 읽고, Seer API 는 조향각만 준다). 구동이 0 이었다는 것은 로봇이 안 움직인 것으로만 안다.
- **ROS 실행기 정체 주입**(좀비 재현) · **systemd 유닛 실장비 기동**.

## 원자료

`/tmp/relay_field/`(**휘발** — tmpfs 아님이나 재부팅·정리로 사라진다):
`steer_trace.jsonl`(조향 궤적) · `driver.log` · `supervisor.log` · `state.json`.

⚠ 보존하지 않았다. 재현하려면 위 §절차를 다시 수행해야 한다.
