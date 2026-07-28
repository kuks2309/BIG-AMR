# BIG-AMR

**Foil_A082 AMR retrofit — driving a vendor-locked AMR with your own autonomy stack.**

[English](#english) · [한국어](#한국어)

📐 **[ARCHITECTURE.md](ARCHITECTURE.md)** — full system architecture with diagrams,
from job planning down to the wheels. Start there if you are new to the project.

> Proprietary and confidential. © 2026 T-Robotics. Internal, unreleased.

---

## English

### What this is

Foil_A082 is a working factory AMR (Autonomous Mobile Robot). Its command chain is:

```
ACS  →  PLC  →  Seer (SRC) controller  →  CAN bus  →  Tongyi wheel motors
```

That chain is production equipment and is treated as **untouchable** — the Seer
controller cannot be reflashed, rewired, or reconfigured.

This project adds a second, independent source of motion to that robot **without
modifying any part of the existing chain**. It does so by splicing a small board
inline into the CAN cable between the Seer controller and the motors, and running
a ROS 2 autonomy stack on an on-board PC (Jetson Orin NX / Neousys).

### How the retrofit works

A **Black Panda** board sits in the middle of the Seer ↔ motor CAN link
(`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h`).

By default it is a transparent relay — Seer drives the robot exactly as before.

When `pc_authority` is enabled, the gate does three things at once:

1. **Blocks** Seer's SDO writes to the motors, and **synthesises fake ACKs** so
   Seer believes its commands were applied.
2. **Covers the transition** — during the ~150 ms the relay takes to switch, it
   answers Seer's reads and node-guard requests from a cache, preventing motor
   timeout (`52111`) and odometry-lost (`52106`) alarms.
3. **Freezes the readback** — it snapshots the motor state at the moment of
   takeover and keeps replaying that snapshot. While the PC actually drives the
   robot, Seer reads "stopped, wheels unmoved", so following error stays at zero
   and no `55602` warning is raised.

On release, the gate returns to passthrough and Seer resumes normally.

### The robot

| Property | Value | Source |
|---|---|---|
| Platform | 2WS inline dual-steer (Seer class: `multisteer`) | Seer live API 1000 |
| Wheels | W1 Front `(+0.6039, −0.0014)`, W2 Rear `(−0.5961, −0.0014)` | `robot_geometry_2ws.yaml` |
| Wheelbase | 1.200 m | measured, 2-source cross-check |
| Wheel radius | 0.125 m | measured |
| Steering limit | ±90° | `spin_params.yaml` |
| Sensors | 2× SICK 2D safety scanner, iAHRS IMU | `src/Sensors/` |
| Seer controller | `192.168.44.82`, WiFi only, API ports 19204–19207 / 19301 | `docs/network/` |

Both wheels sit on the centreline and can swivel ±90°, so the robot can drive
forward, rotate in place, and translate directly sideways (**crab**).

### Repository layout

```
src/
  Control/Motion_Control/
    QD/      trnav_{msgs,interfaces,motion_core,qd_kinematics,motion_qd,motion_action_server}
             Quad-Drive diagonal stack, ported from upstream TR_Nav
    2WS/     trnav_2ws_*  — same stack refactored for the measured inline geometry
  Sensors/
    IMU/     iahrs_driver_ros2 (driver + interfaces)
    Lidar/2D sick_safetyscanners2, dual_laser_merger, lidar_calibration_2d, seer_lidar_tf
  Actuators/
    motor_control          CANopen SDO master (docs only in this repo)
  Sim/                     Gazebo simulation (see "Simulation" below)
Tools/Can_Relay/           Black Panda firmware patch (the CAN gate)
References/Seer-Driver/    Seer Robokit TCP/IP API notes + official SDK
docs/                      ADRs, issue log, debt registry, SW structure analyses
```

Motion is exposed as **9 action servers** — spin, turn, translate forward/reverse,
crab_linear, yaw_control (±), mpc (±) — all publishing `trnav_2ws_msgs/WheelSetArray`
on `/motion/wheel_cmd/<action>`.

### Current status

**Working**
- CAN relay gate, verified on the real robot (endurance run: 76 cycles, PASS)
- 2WS motion stack builds clean; `TwoWsDualSteerIK` output matches Seer's own
  `chassis_kinematics.py` to 4 decimal places
- Sensor drivers for IMU and 2D lidar
- Gazebo simulation of the full platform

**Not yet connected**
- The **mux** that routes `/motion/wheel_cmd/*` into the motor driver does not
  exist in this repo. Nothing subscribes to `wheel_cmd`, and no server implements
  `/select_motion_source`. The motion domain and the drive domain are therefore
  not joined on real hardware — `imu/data` is the only topic crossing between them.
- `motor_control` source is not in this repo (documentation only).
- Empty stubs: `Comm/CAN/can_relay`, `Control/Seer`, `Safety`, `Sensors/Lidar/3D`,
  `Control/Motion_Control/{4IS,DD}`.

**Known issue** — the 9 params files in `trnav_2ws_action_server/config/` still
carry Carrier AGV geometry (`w1_x: 0.330`, `wheel_radius: 0.080`). Only
`robot_geometry_2ws.yaml` holds the measured Foil_A082 values, and no launch file
references it. These must be reconciled before the action servers command the real
robot or the simulation meaningfully.

### Simulation

The Gazebo model replaces everything below the wheel-command interface, so the
real motion stack runs unchanged:

| Real robot | Simulation |
|---|---|
| action servers → `WheelSetArray` | unchanged |
| mux → `motor_control` → CANopen → motors | `wheel_cmd_bridge` → `ros2_control` |
| SICK scanners, iAHRS IMU | Gazebo ray + IMU plugins, same topic names |
| `motor_control` odometry | `wheel_odometry` (forward kinematics) |

The Black Panda / Seer gate is **not** simulated — it lives below the physics
boundary.

**Build and run**

```bash
cd ~/Desktop/BIG-AMR
source /opt/ros/humble/setup.bash
colcon build --packages-select trnav_2ws_description trnav_2ws_gazebo
source install/setup.bash

ros2 launch trnav_2ws_gazebo sim.launch.py
```

Launch arguments: `gui:=false` (headless), `steer_lag:=0.8` (model a slow
steering servo), `x:= y:= yaw:=` (spawn pose), `rviz:=true`.

**Drive it**

```bash
bash src/Sim/trnav_2ws_gazebo/scripts/run_gui.sh      # PyQt5 control panel
# or
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

The control panel gives a 9-button direction pad (forward, reverse, crab left and
right, rotate both ways, two diagonals, stop), speed sliders, an E-STOP that
publishes `/estop`, and a live top-down view of both steering modules drawn from
`/joint_states`.

**Stop everything**

```bash
bash src/Sim/trnav_2ws_gazebo/scripts/stop_sim.sh
```

Leftover `gzserver` / `gzclient` processes block the next launch with
`bind: Address already in use`; this script clears them.

### Requirements

- Ubuntu 22.04, ROS 2 Humble
- Gazebo Classic 11 with `gazebo_ros2_control`, `position_controllers`,
  `velocity_controllers`
- `python3-pyqt5`, `python3-numpy` (control panel and odometry)

### Two things to know before you run

**Non-ASCII in the URDF breaks `gazebo_ros2_control`.** The plugin passes the whole
robot description to `controller_manager` as a `--param` CLI override, and `rcl`'s
parameter-rule parser fails on non-ASCII bytes — Korean comments or em-dashes are
enough to kill it. The controller manager then never starts and the spawners hang
forever. `sim.launch.py` strips XML comments before handing the description to ROS.

**Snap terminals break PyQt5.** If launched from a terminal inside a snap (the VS
Code snap is the common case), snap's `GTK_PATH` and friends point Qt at core20's
bundled glibc, which fails with `undefined symbol: __libc_pthread_init`.
`run_gui.sh` unsets those variables; it is a no-op from a normal terminal.

### Documentation

| Path | Contents |
|---|---|
| `docs/adr/` | Architecture decision records |
| `docs/issues_and_fixes/` | Field problem → root cause → fix log |
| `docs/can_relay/test-process.md` | **Mandatory** procedure before any real-robot drive test |
| `docs/debt/registry.md` | Technical debt register |
| `docs/network/` | How to reach the Seer controller |
| `docs/sw_structure/` | Code-level structure analyses (verified against `file:line`) |
| `References/Seer-Driver/` | Seer Robokit TCP/IP API guide |

⚠ Before driving the real robot, read `docs/can_relay/test-process.md`. Testing
from a contaminated state (mid re-homing, uncleared alarms) produces meaningless
results and is unsafe — an unverified steering command has already jammed a
steering axis at 137°, outside its ±90° range.

---

## 한국어

### 개요

Foil_A082 는 현장에서 가동 중인 공장용 AMR(자율이동로봇)이다. 기존 명령 체인은
다음과 같다.

```
ACS  →  PLC  →  Seer(SRC) 컨트롤러  →  CAN 버스  →  Tongyi 구동 모터
```

이 체인은 **불가침**(운영 중인 설비)으로 취급한다. Seer 컨트롤러는 펌웨어 변경도,
배선 변경도, 설정 변경도 할 수 없다.

본 프로젝트는 **기존 체인을 전혀 건드리지 않고** 이 로봇에 독립적인 두 번째
주행원(driving source)을 추가한다. 방법은 Seer 컨트롤러와 모터 사이의 CAN 케이블
중간에 소형 보드를 인라인 삽입하고, 온보드 PC(Jetson Orin NX / Neousys)에서 ROS 2
자율주행 스택을 구동하는 것이다.

### 리트로핏 동작 원리

**Black Panda** 보드가 Seer ↔ 모터 CAN 링크 중간에 위치한다
(`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h`).

평상시에는 투명 중계(passthrough) — Seer 가 종전과 동일하게 로봇을 구동한다.

`pc_authority` 가 켜지면 게이트는 세 가지를 동시에 수행한다.

1. Seer 의 모터 SDO 쓰기를 **차단**하고 **가짜 ACK 를 합성**해 응답한다. Seer 는
   자기 명령이 반영된 것으로 인식한다.
2. **전환 구간을 커버**한다 — 릴레이 스위칭에 걸리는 약 150 ms 동안 캐시된 값으로
   Seer 의 읽기·node guard 에 대신 응답해 모터 타임아웃(`52111`)·오도메트리
   상실(`52106`) 알람을 예방한다.
3. **정지값을 고정(freeze)** 한다 — 인수 시점의 모터 상태를 스냅샷으로 잡아 계속
   같은 값을 응답한다. PC 가 실제로 로봇을 구동하는 동안에도 Seer 는 "정지, 휠
   무변화" 로 읽으므로 추종오차가 0 으로 유지되고 `55602` 경고가 뜨지 않는다.

release 하면 게이트는 투명 중계로 복귀하고 Seer 가 정상적으로 이어받는다.

### 로봇 사양

| 항목 | 값 | 근거 |
|---|---|---|
| 플랫폼 | 2WS inline dual-steer (Seer 분류: `multisteer`) | Seer live API 1000 |
| 휠 위치 | W1 앞 `(+0.6039, −0.0014)`, W2 뒤 `(−0.5961, −0.0014)` | `robot_geometry_2ws.yaml` |
| 축간거리 | 1.200 m | 실측, 2 source 교차확인 |
| 휠 반경 | 0.125 m | 실측 |
| 조향 한계 | ±90° | `spin_params.yaml` |
| 센서 | SICK 2D 안전스캐너 2대, iAHRS IMU | `src/Sensors/` |
| Seer 컨트롤러 | `192.168.44.82`, 무선 전용, API 포트 19204–19207 / 19301 | `docs/network/` |

두 휠 모두 차체 센터라인에 있고 ±90° 조향이 가능하므로, 전진·제자리 회전에 더해
**크랩(crab, 횡방향 평행이동)** 이 가능하다.

### 저장소 구조

```
src/
  Control/Motion_Control/
    QD/      trnav_{msgs,interfaces,motion_core,qd_kinematics,motion_qd,motion_action_server}
             upstream TR_Nav 에서 이식한 Quad-Drive 대각 스택
    2WS/     trnav_2ws_*  — 실측 inline 기하로 리팩터한 동일 스택
  Sensors/
    IMU/     iahrs_driver_ros2 (드라이버 + 인터페이스)
    Lidar/2D sick_safetyscanners2, dual_laser_merger, lidar_calibration_2d, seer_lidar_tf
  Actuators/
    motor_control          CANopen SDO 마스터 (본 저장소에는 문서만 존재)
  Sim/                     Gazebo 시뮬레이션 (아래 "시뮬레이션" 참조)
Tools/Can_Relay/           Black Panda 펌웨어 패치 (CAN 게이트)
References/Seer-Driver/    Seer Robokit TCP/IP API 조사자료 + 공식 SDK
docs/                      ADR, 이슈 기록, 부채 registry, SW 구조 분석
```

모션은 **9종 액션 서버**(spin, turn, translate forward/reverse, crab_linear,
yaw_control ±, mpc ±)로 노출되며, 모두 `/motion/wheel_cmd/<action>` 에
`trnav_2ws_msgs/WheelSetArray` 를 발행한다.

### 현재 상태

**동작 확인됨**
- CAN 릴레이 게이트 — 실 로봇 검증 완료(내구 76 사이클 PASS)
- 2WS 모션 스택 빌드 error 0. `TwoWsDualSteerIK` 출력이 Seer 원본
  `chassis_kinematics.py` 와 소수 4자리까지 일치
- IMU·2D 라이다 센서 드라이버
- 전체 플랫폼의 Gazebo 시뮬레이션

**아직 연결되지 않음**
- `/motion/wheel_cmd/*` 를 모터 드라이버로 잇는 **mux 가 본 저장소에 없다.**
  `wheel_cmd` 구독자 0, `/select_motion_source` 서버 0. 따라서 모션 도메인과 구동
  도메인은 실 하드웨어에서 연결되어 있지 않다 — 두 도메인이 공유하는 유일한 토픽은
  `imu/data` 뿐이다.
- `motor_control` 소스는 본 저장소에 없다(문서만 존재).
- 빈 stub: `Comm/CAN/can_relay`, `Control/Seer`, `Safety`, `Sensors/Lidar/3D`,
  `Control/Motion_Control/{4IS,DD}`.

**알려진 문제** — `trnav_2ws_action_server/config/` 의 params yaml 9개가 여전히
Carrier AGV 기하(`w1_x: 0.330`, `wheel_radius: 0.080`)를 담고 있다. 실측
Foil_A082 값은 `robot_geometry_2ws.yaml` 에만 있고, 이를 참조하는 launch 파일이
없다. 액션 서버가 실 로봇이나 시뮬레이션을 의미 있게 구동하려면 먼저 이 값을
정합시켜야 한다.

### 시뮬레이션

Gazebo 모델은 휠 명령 인터페이스 **아래** 계층 전체를 대체한다. 따라서 실제 모션
스택은 수정 없이 그대로 돌아간다.

| 실 로봇 | 시뮬레이션 |
|---|---|
| 액션 서버 → `WheelSetArray` | 동일 |
| mux → `motor_control` → CANopen → 모터 | `wheel_cmd_bridge` → `ros2_control` |
| SICK 스캐너, iAHRS IMU | Gazebo ray·IMU 플러그인 (토픽명 동일) |
| `motor_control` 오도메트리 | `wheel_odometry` (정기구학) |

Black Panda / Seer 게이트는 물리 경계 아래에 있으므로 **시뮬레이션하지 않는다.**

**빌드 및 실행**

```bash
cd ~/Desktop/BIG-AMR
source /opt/ros/humble/setup.bash
colcon build --packages-select trnav_2ws_description trnav_2ws_gazebo
source install/setup.bash

ros2 launch trnav_2ws_gazebo sim.launch.py
```

launch 인자: `gui:=false`(headless), `steer_lag:=0.8`(느린 조향 서보 재현),
`x:= y:= yaw:=`(스폰 포즈), `rviz:=true`.

**조작**

```bash
bash src/Sim/trnav_2ws_gazebo/scripts/run_gui.sh      # PyQt5 조작 패널
# 또는
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

조작 패널은 9버튼 방향 패드(전진·후진·좌우 크랩·좌우 회전·대각 2종·정지), 속도
슬라이더, `/estop` 을 발행하는 E-STOP, 그리고 `/joint_states` 기반 조향 모듈
실시간 상면도를 제공한다.

**종료**

```bash
bash src/Sim/trnav_2ws_gazebo/scripts/stop_sim.sh
```

잔여 `gzserver` / `gzclient` 프로세스가 남으면 다음 기동이
`bind: Address already in use` 로 실패한다. 이 스크립트가 정리한다.

### 요구 환경

- Ubuntu 22.04, ROS 2 Humble
- Gazebo Classic 11 + `gazebo_ros2_control`, `position_controllers`,
  `velocity_controllers`
- `python3-pyqt5`, `python3-numpy` (조작 패널·오도메트리)

### 실행 전 알아둘 두 가지

**URDF 의 비-ASCII 문자는 `gazebo_ros2_control` 을 죽인다.** 이 플러그인은
robot_description 전체를 `controller_manager` 노드에 `--param` CLI 오버라이드로
넘기는데, `rcl` 의 파라미터 규칙 파서가 비-ASCII 바이트를 처리하지 못한다. 한글
주석이나 em-dash 하나만 있어도 실패하며, 그러면 controller_manager 가 아예 뜨지
않아 스포너가 무한 대기한다. `sim.launch.py` 는 ROS 로 넘기기 전에 XML 주석을
제거한다.

**snap 터미널에서는 PyQt5 가 죽는다.** snap 내부 터미널(주로 VS Code snap)에서
실행하면 snap 의 `GTK_PATH` 등이 Qt 를 core20 번들 glibc 로 유도해
`undefined symbol: __libc_pthread_init` 로 실패한다. `run_gui.sh` 가 해당 변수를
해제하며, 일반 터미널에서는 아무 영향이 없다.

### 문서

| 경로 | 내용 |
|---|---|
| `docs/adr/` | 아키텍처 결정 기록 |
| `docs/issues_and_fixes/` | 현장 문제 → 원인 → 해결 기록 |
| `docs/can_relay/test-process.md` | 실 로봇 구동 테스트 전 **필수** 절차 |
| `docs/debt/registry.md` | 기술 부채 registry |
| `docs/network/` | Seer 컨트롤러 접속 방법 |
| `docs/sw_structure/` | 코드 레벨 구조 분석 (`file:line` 실측 검증) |
| `References/Seer-Driver/` | Seer Robokit TCP/IP API 가이드 |

⚠ 실 로봇 구동 전 반드시 `docs/can_relay/test-process.md` 를 읽을 것. 오염된
상태(재호밍 중, 미해결 알람)에서의 테스트는 결과가 무의미하고 위험하다 — 검증되지
않은 조향 지령으로 조향축이 가동범위(±90°) 밖인 137° 에 물리적으로 갇힌 사례가
이미 있다.
