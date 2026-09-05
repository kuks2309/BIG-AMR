# 실기 첫 구동 런북 — 2WS 모션 체인

> **이 체인은 실기에서 한 번도 돌지 않았다.** 지금까지 검증은 전부 SIL(Software In the Loop)
> 이다. 본 런북은 「되는지 보는 것」이 아니라 **어디서 멈출지 미리 정해 두는 것**이 목적이다.
>
> 대상 체인: 2WS 액션 → `trnav_motion_mux` → `amr_motor_cmd_translator` → `can_relay` → 판다 → CAN

## 0. 전제 — 이 값들이 다르면 계획을 다시 짜야 한다

> ⚠ **이 절은 매 구동 전에 다시 측정한다.** 2026-08-07 초판 값은 **하루 만에 무효가 됐다** —
> 맵 md5 가 바뀌고 **스테이션이 전부 교체**됐다(LM3001·LM3002 → LM1~LM4).
> 「지난번 값」으로 시작하지 말 것.
>
> | | 2026-08-07 09:30 (무효) | 2026-08-08 07:40 (현행) |
> | --- | --- | --- |
> | 맵 md5 | `79e59a5ac112551ab7f1dea192230a94` | `a20cbe5cb35fe90bde5685174220ffd5` |
> | 스테이션 | LM3001(−12.5, 2.4) · LM3002(−16.5, 2.4) | LM1~LM4 (아래) |

2026-08-08 07:40 실측:

```
기체            model Foil_A082 · vehicle_id Foil_A082
맵              current_map 260709_test · md5 a20cbe5cb35fe90bde5685174220ffd5 (2026-08-08 관측 — §0 에서 재측정할 것, 2026-09-05 값은 0319831d…)
측위            x −11.988 · y 2.412 · angle 3.1413 rad(179.98°) · confidence 0.805 · loc_state 0
                in_forbidden_area False
작업            task_status 4 · task_type 3 · target_id LM1
알람            fatals 0 · errors 0 · warnings 1 (54029 ManualBlock is False, 08-07 22:54 발생)
스테이션        LM1(−15.927,  2.412)   LM2(−15.927, 15.572)
                LM3(−11.712, 15.572)   LM4(−11.988,  2.412)  r=3.1413
판다            연결됨 (bbaa:ddcc comma.ai panda, Bus 003 Device 009)
```

**로봇은 LM4 에 정확히 주차돼 있다**(좌표·각도 모두 일치). 이는 타 세션의 결정
`docs/adr/2026-08-07-…-idle robots must go home` 에 따른 홈 대기 상태다.

⚠ **구동은 로봇을 홈에서 이탈시킨다.** 다른 세션이 그 위치를 전제하고 있을 수 있으므로
시작 전 조율하고, 종료 시 LM4 로 되돌린다.

주행 대상: **LM4 → LM1** — 같은 y(2.412) 위 **−x 방향 3.939 m 직선**이고,
로봇이 **이미 그 방향을 보고 있다**(angle 179.98° ≈ −x). 즉 정면이 진행 방향이다.

## ⚠ 시작 전 반드시 아는 사실 4가지

| # | 사실 | 근거 | 운용상 의미 |
| --- | --- | --- | --- |
| 1 | **정지 지령 후 0.57~0.65 s 더 간다**(50 mm/s 기준) | `docs/verified_facts/2026-08-04-amr-test-gui-field-run.md:80-88` | `~/stop` 은 **급정지가 아니다.** 사람·장애물 앞 여유를 그만큼 더 잡는다 |
| 2 | **`~/stop` 은 조향을 세우지 않는다** | `backend.py:505-512` — 조향축엔 프레임이 안 나가고 드라이브가 직전 목표까지 계속 회전 | 조향 이상 시 정지만으로 안 멈춘다. **하드웨어 E-STOP 이 유일한 확실한 수단** |
| 3 | **호밍은 물리적으로 100° 이상 스윙한다** | `driver_node.py` `~/home` 주석, 기구 −리밋 137.1° | 주변 간섭물 치우고, 바퀴가 걸릴 것이 없는 상태에서만 |
| 4 | **액션의 `status 0` 은 정확도를 보증하지 않는다** | 4종 전부 `result->status = 0` 무조건, 오차 필드는 판정에 미사용 | **성공 코드를 믿지 말고 `final_lateral_error`·rviz 를 본다** |

## 안전 게이트 (물리)

- [ ] 하드웨어 E-STOP 이 **손 닿는 곳**에 있고 동작을 확인했다
- [ ] 진행 방향 **6 m 이상** 사람·장애물 없음 (4 m 경로 + 관성 여유 + 오차 여유)
- [ ] 로봇 주변 1 m 반경에 케이블·공구 없음 (호밍 스윙)
- [ ] 관찰자 1명이 E-STOP 을 잡고, 조작자와 **분리**

## 1단계 — 무동작 관측 (모터에 아무것도 안 나간다)

**목적**: 체인이 붙고 숫자가 맞는지, **움직이기 전에** 확인한다.

```bash
export ROS_DOMAIN_ID=0                     # 실 운용 도메인
ros2 launch seer_pose_publisher seer_pose.launch.py \
     expected_map_md5:=a20cbe5cb35fe90bde5685174220ffd5   # ⚠ §0 에서 재측정한 값으로
python3 Tools/seer_viz/seer_map_viz.py \
     --smap map/260709_test.smap --no-tf      # 정본 1개만 둔다(map/README.md)
rviz2 -d Tools/seer_viz/seer_map.rviz
```

> `--no-tf` 주의 — 실 브링업에서 `map→base_link` 를 내는 다른 노드가 있으면 켜지 말 것.
> 없으면 `--no-tf` 를 빼서 이 도구가 TF 를 내게 한다(rviz 가 Fixed Frame 을 찾는다).

**통과 기준**
- [ ] rviz 에 맵·스테이션·**로봇 화살표**가 보이고, 손으로 밀면(가능하면) 화살표가 따라온다
- [ ] `ros2 topic hz /robot_pose` ≈ 10 Hz
- [ ] 맵 게이트가 **통과**로 로그를 남긴다(md5 일치). ERROR 면 **여기서 중단** — 맵이 다르다
- [ ] `can_relay` 는 **아직 띄우지 않는다**

## 2단계 — can_relay 기동, 제어권 미획득

**목적**: 드라이버가 붙되 아무것도 못 보내는 상태를 확인한다.

```bash
ros2 launch can_relay can_relay.launch.py       # link: panda (config 기본값)
```

**통과 기준**
- [ ] 로그에 `can_relay 대기 — 제어권 미획득` 이 뜬다
- [ ] `/motor/low_state` 가 올라오고 `fb_pos` 가 4축 모두 갱신된다
- [ ] `/diagnostics` 에 거부 건수·노드별 상태가 보인다
- [ ] **바퀴가 전혀 움직이지 않는다**

**중단 기준** — CAN 에러, 노드 응답 없음, `fb_pos` 정지.

## 3단계 — 제어권 획득 + 조향 호밍

**목적**: 조향 원점을 잡는다. **여기서 물리 스윙이 일어난다.**

```bash
ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"
ros2 service call /can_relay_node/home   std_srvs/srv/Trigger {}     # ⚠ 100°+ 스윙
```

**통과 기준**
- [ ] 두 조향축이 −리밋까지 갔다가 **펌웨어 정착 위치**로 돌아온다(설계 동작 — 137° 스윙 후 복귀).
      ⚠ 그 위치는 조향 0° 가 **아니다** — 0° 에서 +0.178° / +0.331° 떨어진 지점이며,
      펌웨어에는 0° 로 보내는 동작이 없다. 0° 복귀가 필요하면 호스트가 별도로 지령해야 한다.
- [ ] `/motor/low_state` 의 조향 `fb_pos` 가 **홈 기준 0 근처**로 수렴 (절대 7.8M 이 보이면 상류가 원점을 잘못 더한 것)
- [ ] `home_comp` 가 참
- [ ] 바퀴가 **눈으로 봐서 직진**을 향한다

**중단 기준** — 호밍 timeout, 한쪽 축만 완료, 스윙 중 이상음·간섭.

## 4단계 — 조향만 (구동 0)

**목적**: 조향 지령→물리각 대응을 **바퀴가 안 굴러가는 상태에서** 확인한다.

벤치 지령은 **서비스가 아니라 토픽**이고, 드라이버 문서가 **「잭업 시험용」**이라고 명시한다
(`driver_node.py:24-25`). 지면 접지 상태에서 쓰면 바퀴가 비틀린다 — **가능하면 잭업 후** 수행.

```bash
# 전축 동일각
ros2 topic pub --once /can_relay_node/steer_deg std_msgs/msg/Float64 "{data: 10.0}"
# 축별 (전륜, 후륜) — 2WS 는 대칭 반대가 정상
ros2 topic pub --once /can_relay_node/steer_axis_deg \
  std_msgs/msg/Float64MultiArray "{data: [10.0, -10.0]}"
```

`10 → 30 → 45` 순으로 올리고, 매번 `/joint_states`(조향 실측각)와 눈으로 대조한다.
구동은 지령하지 않는다(`~/drive_mmps` 를 보내지 않으면 0).

**통과 기준**
- [ ] 지령 부호와 물리 회전 방향이 일치 (좌 지령 → 좌로)
- [ ] 각도기·눈금으로 ±45° 가 실제 45° 근처
- [ ] `steer_axis_deg [10, −10]` 에서 두 축이 **반대 방향**으로 (2WS 대칭 조향)
- [ ] `/joint_states` 의 실측각이 지령과 일치
- [ ] 벤치 클램프 **±90°**(`steer_limit_bench_deg`)를 넘겨 지령하면 클램프된다 —
      체인 클램프 115° 와 **다른 값**이다(벤치는 더 보수적)

**중단 기준** — 부호 반대, 한쪽만 움직임, 각도 오차 5° 초과.

> 여기까지가 **모션 스택 없이** 하는 확인이다. 이 단계를 건너뛰면 이후 오차가 조향인지
> 제어인지 구분되지 않는다.

## 5단계 — 첫 주행: 짧은 직진 0.5 m

**목적**: 체인 전체가 한 번 도는 것을 **가장 작은 동작**으로 본다.

```bash
ros2 launch trnav_2ws_action_server translate_forward.launch.py
ros2 action send_goal /amr_motion_translate_forward_abstract \
  trnav_2ws_interfaces/action/AMRMotionTranslateForward \
  "{start_x: -11.988, start_y: 2.412, end_x: -12.488, end_y: 2.412,
    max_linear_speed: 0.05, acceleration: 0.05, hold_steer: false,
    exit_steer_angle: 0.0, exit_speed: 0.0, entry_speed: 0.0, has_next: false,
    control_mode: 0, enable_localization_watchdog: true, skip_initial_pose_check: false}"
```

⚠ **속도 0.05 m/s** — 관성 0.6 s 면 정지 후 **3 cm** 만 더 간다.
⚠ **경로 pose orientation** — CLI 로는 orientation 을 못 넣는다. `translate_*` 는 시작·끝
좌표만 받으므로 무관하나, **`mpc` 계열은 경로 pose 의 orientation 을 직접 쓴다**
(`mpc_reverse_action_server.cpp:385`). identity 로 두면 후진 경로에서 180° 어긋난다
(2026-08-06 SIL 에서 실제로 겪었다 — `docs/claude-mistake/2026-08-06-004`).

**통과 기준**
- [ ] 실제로 0.5 m 전진하고 멈춘다
- [ ] rviz 화살표가 경로를 따라간다
- [ ] `final_lateral_error` **< 0.05 m** (status 0 은 근거가 아니다 — §⚠ 4번)
- [ ] 정지 후 추가 주행이 **5 cm 이내**

**중단 기준** — 횡방향으로 밀림, 조향이 흔들림, 오차 0.1 m 초과, 정지 안 함.

## 6단계 — 등록 경로 주행 LM4 → LM1 (3.94 m)

5단계 통과 후에만. 속도 0.1 → 0.2 m/s 로 **두 번에 나눠** 올린다.

**통과 기준**
- [ ] 종점이 LM1(−15.927, 2.412) 기준 **0.1 m 이내**
- [ ] 주행 중 `confidence` 가 0.5 아래로 떨어지지 않는다
- [ ] `/robot_pose` 끊김 없음 (0.5 s 넘게 끊기면 워치독이 액션을 중단시킨다 — 정상 동작)

## 7단계 — turn (이번 세션에서 고친 것)

**5·6단계가 모두 통과한 뒤에만.** 이 액션은 오늘 두 곳을 고쳤고 **SIL 만 검증**했다.

```bash
ros2 launch trnav_2ws_action_server turn.launch.py
# 목표 15° · R=2.0 m · 0.05 m/s 부터
```

**특별히 볼 것**
- [ ] 조향이 **원호각(R=2.0 m 에서 약 16.8°)** 을 넘지 않는다.
      **±90° 로 스윙하면 수정이 반영되지 않은 것** — 즉시 중단
- [ ] 목표각 대비 실제 회전 오차 (SIL 잡음 조건 예측 ≤0.3°, 실기는 미지)
- [ ] `actual_angle` 보고와 rviz 실제 회전의 차이 — 둘이 벌어지면 각도 계상 문제

**중단 기준** — 조향 45° 초과, 회전이 안 멈춤, 보고와 실제가 2° 이상 차이.

## 중단 시 행동 순서

1. **하드웨어 E-STOP** — 조향이 이상하면 이것뿐이다(§⚠ 2번)
2. `ros2 service call /can_relay_node/stop std_srvs/srv/Trigger {}` — 구동만 0
3. `ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: false}"` — 제어권 반환
4. 로그·bag 보존 후 원인 규명. **같은 단계를 원인 없이 재시도하지 않는다**

## 기록 (매 단계)

```bash
ros2 bag record -o drive_$(date +%H%M%S) \
  /robot_pose /seer/localization_confidence \
  /motion/wheel_cmd/* /motor/wheel_cmd /motor/low_cmd /motor/low_state /diagnostics /tf
```

단계별로 **통과/중단과 그 근거 수치**를 `docs/issues_and_fixes/issues_and_fixes.md` 에 남긴다.

## 이번 구동으로 확인되지 않는 것 (미리 적어 둔다)

- `mpc`·`mpc_reverse` — 경로 pose orientation 규약 때문에 CLI 로 목표를 만들기 어렵다. 별도 도구 필요
- `crab_linear` — 조향 ±115° 를 쓰는 유일한 기동. 클램프 여유가 **0.002°** 뿐이라 별도 계획 필요
- 장시간 무선 안정성 · `min_confidence` 임계값 · 20 Hz 제어가 10 Hz 자세를 쓸 때의 추종 오차
