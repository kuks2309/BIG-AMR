# Glossary — the vocabulary of this project

Every term you will hear in a meeting about Big-AMR, in the order you are likely to
need it. Written to be *memorised*, so entries are short.

> If a term is specific to **this** project rather than the industry, it is marked 🏠.
> Those are the ones nobody outside T-Robotics will know, and the ones people here will
> assume you already do.

---

## Contents

1. [The twenty that matter most](#1-the-twenty-that-matter-most)
2. [This project's own names](#2-this-projects-own-names) 🏠
3. [The industrial stack](#3-the-industrial-stack)
4. [CAN and motor control](#4-can-and-motor-control)
5. [ROS 2](#5-ros-2)
6. [Localisation and navigation](#6-localisation-and-navigation)
7. [Kinematics and motion](#7-kinematics-and-motion)
8. [Sensors](#8-sensors)
9. [Software architecture](#9-software-architecture)
10. [Industrial protocols](#10-industrial-protocols)
11. [Process and quality](#11-process-and-quality)
12. [Saying it out loud](#12-saying-it-out-loud)

---

## 1. The twenty that matter most

If you learn nothing else today, learn these. They will come up in the first hour.

| Term | One line |
|---|---|
| **AMR** | Autonomous Mobile Robot — navigates freely using a map, unlike an AGV |
| **AGV** | Automated Guided Vehicle — follows a fixed route: tape, wire, magnets |
| **MES** | Manufacturing Execution System — decides what work happens and tracks it |
| **ACS** | the fleet controller — picks which robot does a job and routes it |
| **Seer** 🏠 | the vendor controller already on this robot. Untouchable |
| **Panda gate** 🏠 | our board spliced into the CAN cable that lets us override Seer |
| **CAN** | the wired bus inside the robot that carries motor commands |
| **CANopen** | the language spoken over CAN. `SDO` = one request, one reply |
| **CiA 402** | the standard state machine every servo drive must be walked through |
| **statusword `0x6041`** | what the drive reports about itself. Freezing this is the whole trick |
| **ROS 2** | the robot software framework on our Jetson |
| **node / topic / action** | a program / a broadcast channel / a long job you can cancel |
| **TF** | the tree of coordinate frames — where everything is relative to everything |
| **odometry** | "how far have I moved?" Drifts forever |
| **localisation** | "where am I on the map?" Can be wrong, does not drift |
| **MCL** | Monte Carlo Localisation — the particle filter that answers the above |
| **FSM** | Finite State Machine — in exactly one state at a time, with defined doors |
| **2WS dual-steer** 🏠 | this robot: two wheels, both on the centreline, both steer ±90° |
| **crab** | driving sideways without the body rotating |
| **IK** | inverse kinematics — "body should move like this" → "each wheel does this" |

---

## 2. This project's own names 🏠

Nobody outside will know these. Everybody inside will assume you do.

| Term | What it is |
|---|---|
| **Foil_A082** | the robot. A working factory AMR we are retrofitting |
| **Carrier AGV** | a *different* robot — the QD platform. Its geometry is still wrongly present in some 2WS config files (see `docs/audit/`) |
| **Seer / SRC** | the vendor's controller, at `192.168.44.82`. Production equipment — cannot be reflashed, rewired or reconfigured |
| **Robokit** | Seer's TCP/IP API. Ports 19204 status · 19205 control · 19206 navigation · 19207 config · 19301 push |
| **Black Panda** | the board spliced inline into the CAN cable between Seer and the motors |
| **the gate** | the firmware on that board — `safety_seer_gate.h` |
| **`pc_authority`** | the mode where the gate stops passing Seer's commands and lets our PC drive |
| **freeze the readback** | the gate replays a snapshot of motor state so Seer believes the robot is parked while it is actually moving |
| **Tongyi** | the servo drives that turn the wheels. 4 axes: 2 drive, 2 steer |
| **Jetson Orin NX / Neousys** | the on-board computer running our ROS 2 stack |
| **`.smap`** | Seer's map file format |
| **mcl2d** | our re-implementation of Seer's localiser, reverse-engineered from `libMCLoc.so` |
| **the mux** | the component that would route motion commands into the motor driver. **Does not exist yet** — it is the missing link in the whole stack |
| **Mini MES** | the layer above the ACS that we are building |
| **CATL** | the customer. We are waiting on them for the equipment protocol |

**Two names people confuse, and it matters:**

| | `motor_control` | `can_relay` |
|---|---|---|
| Path | socketcan, direct | USB → panda → bus 2 |
| Seer | must be **disconnected** | must be **connected** |

Always say which one you mean. Mixing them up is a registered hazard (`debt-025`).

---

## 3. The industrial stack

The layers of a factory's software, top to bottom. This is **ISA-95**, the standard model.

```
L4  ERP    what to produce, when, for whom — business level
L3  MES    execute it: which order, which machine, track every unit   ← we are here
L2  SCADA / ACS   supervise and coordinate equipment
L1  PLC    the real-time controller wired to the machine
L0  the physical process itself
```

| Term | Meaning |
|---|---|
| **ERP** | Enterprise Resource Planning — SAP and friends. Orders, inventory, planning |
| **MES** | Manufacturing Execution System — turns a production order into actual work and records what happened |
| **ACS** | fleet controller for the robots. Assigns jobs, plans routes, reserves corridors so two robots do not deadlock, sends robots to charge |
| **PLC** | Programmable Logic Controller — the rugged industrial computer that actually runs a machine. Cycle times in milliseconds, extremely reliable |
| **SCADA** | Supervisory Control and Data Acquisition — the monitoring/HMI layer |
| **HMI** | Human-Machine Interface — the screen an operator uses |
| **traceability** | knowing which unit went through which machine, when. A core MES job |
| **throughput / takt time** | units per hour / the time budget per unit to hit demand |
| **WIP** | Work In Progress — material on the floor that is started but not finished |

**Why the Mini MES sits above the ACS.** The ACS knows about *robots*. It does not know
why anything is being moved. The MES knows about *work* — that a batch finished at
station 3 and must reach station 5 before the next operation. Someone has to hold that
knowledge, and it is not the fleet controller's job.

---

## 4. CAN and motor control

This is the layer the retrofit lives in. Worth knowing properly.

| Term | Meaning |
|---|---|
| **CAN bus** | a two-wire network inside vehicles and machines. Every node hears every message. No master needed — messages carry priority, and the lowest ID wins a collision |
| **CAN frame** | one message: an ID, up to 8 bytes of data, a checksum |
| **CANopen** | a standard *language* spoken over CAN — what the IDs and bytes mean |
| **SDO** | Service Data Object. One request, one confirmed reply. Used for configuration and for commands that must be acknowledged. Reliable, slow |
| **PDO** | Process Data Object. Broadcast, unconfirmed, fast, sent cyclically. Used for live data |
| **object dictionary** | the drive's table of everything you can read or write, addressed by index. `0x6041` is an address in it |
| **RTR** | Remote Transmission Request — a frame that *asks* a node to send its data rather than carrying data itself |
| **node guarding** | the master polls each node with RTR frames. Silence = something died |
| **heartbeat** | the inverse: each node announces itself periodically without being asked |
| **socketcan** | Linux's way of treating a CAN interface like a network socket (`can0`, `can1`) |

**The addresses you will hear:**

| Index | Meaning |
|---|---|
| `0x6040` | **controlword** — what you command the drive to do |
| `0x6041` | **statusword** — what the drive reports back. *The one the gate freezes* |
| `0x6060` | modes of operation — position mode, velocity mode, etc. |
| `0x607A` | target position |
| `0x60FF` | target velocity |
| `0x6064` | actual position (the encoder reading) |

**CiA 402** is the standard state machine every compliant servo drive implements. You
cannot just tell a drive to move — you must walk it through the sequence:

```
Not ready → Switch on disabled → Ready to switch on → Switched on → Operation enabled
                                                          ↕
                                                   Fault / Quick stop
```

Only in **Operation enabled** does the motor respond. Getting this wrong looks like "the
drive is ignoring me", and it is the single most common CANopen beginner problem.

| Term | Meaning |
|---|---|
| **servo-off / freewheel** | releasing the motor so it spins freely. Note the fixed bug: a *residual target velocity* left on the drive at servo-off meant a silent re-enable could lurch the robot away at the old speed |
| **following error** | the gap between commanded and actual position. A large one means the drive is not keeping up — Seer raises `55602` |
| **homing** | driving to a known reference position so the encoder has an origin |

---

## 5. ROS 2

The framework. If you know these ten, you can read almost any ROS 2 codebase.

| Term | Meaning |
|---|---|
| **node** | one program that does one thing. `mini_mes` is a node |
| **topic** | a named broadcast channel. Anyone can publish, anyone can subscribe, nobody waits. `/scan`, `/odom` |
| **message** | the typed data on a topic. `sensor_msgs/LaserScan` |
| **service** | a question with an immediate answer. Blocking, quick |
| **action** | a long job you can monitor and cancel. Has a goal, feedback, and a result. **Motion is always an action** |
| **parameter** | a setting a node reads at startup or runtime |
| **launch file** | a Python script that starts many nodes with the right settings |
| **TF / tf2** | the transform tree — where every coordinate frame sits relative to every other |
| **URDF / xacro** | the robot's description: links, joints, dimensions. `xacro` is URDF with macros so you do not repeat yourself |
| **ros2_control** | the standard framework between controllers and hardware |
| **colcon** | the build tool. `colcon build --packages-select <name>` |
| **package.xml** | declares a directory to be a ROS 2 package and lists its dependencies |
| **workspace / `src/`** | colcon only discovers packages under `src/` — which is why this repo's layout rule exists |
| **rclpy / rclcpp** | the Python and C++ client libraries |
| **executor** | the thing that decides which callback runs next |
| **QoS** | Quality of Service — per-topic settings: reliable vs best-effort, keep-last-N vs keep-all. Mismatched QoS is a classic "why is nothing arriving?" bug |
| **bag** | a recording of topics you can replay later. Invaluable for debugging |
| **RViz** | the 3D visualiser |
| **Gazebo** | the physics simulator |

**The TF tree you will see everywhere** (this is ROS convention **REP-105**):

```
map  ──►  odom  ──►  base_link  ──►  sensors
 └ published by localisation (mcl2d)
          └ published by odometry (icp_odometry)
```

`map → odom` corrects the drift; `odom → base_link` is the smooth-but-drifting part.
Splitting them is what lets localisation jump to a correction without the robot's
motion appearing to teleport.

---

## 6. Localisation and navigation

| Term | Meaning |
|---|---|
| **pose** | position **and** orientation together — `x, y, θ` in 2D |
| **odometry** | "how far have I moved since a moment ago?" Smooth, fast, **drifts forever** |
| **localisation** | "where am I on the map?" Slower, occasionally jumps, **does not drift** |
| **dead reckoning** | working out position purely by adding up movement. Another name for the drift problem |
| **SLAM** | Simultaneous Localisation And Mapping — building the map *and* locating yourself at once. Used to **make** the map; not what runs day to day |
| **MCL / AMCL** | Monte Carlo Localisation — the particle filter. `A` = adaptive, meaning it varies the particle count |
| **particle** | one hypothesis about where the robot is. Thousands are maintained; bad ones die |
| **ICP** | Iterative Closest Point — aligns two scans to find the movement between them |
| **scan matching** | using ICP on laser scans to get odometry that a slipping wheel cannot fool |
| **occupancy grid** | the map as a grid of cells: free, occupied, unknown |
| **costmap** | an occupancy grid plus inflation — cells near obstacles cost more, so the planner keeps clear |
| **covariance** | how *uncertain* an estimate is. A pose with large covariance means "roughly here" |
| **global vs local planner** | route across the whole map / avoiding what is in front of you right now |
| **potential field** | steering by attraction to the goal and repulsion from obstacles. What our `SimAcs` uses |
| **kidnapped robot problem** | someone picks the robot up and moves it. Good localisation notices and recovers |

---

## 7. Kinematics and motion

| Term | Meaning |
|---|---|
| **forward kinematics** | wheels are doing this → where does the body go? |
| **inverse kinematics (IK)** | body should do this → what must each wheel do? *This is the useful direction* |
| **holonomic** | can move instantly in any direction. A shopping trolley with omni wheels |
| **non-holonomic** | cannot. A car must roll forward to change position sideways |
| **differential drive** | two fixed wheels, steer by driving them at different speeds. A tank |
| **Ackermann** | car steering — front wheels turn, rear wheels do not |
| **2WS dual-steer** 🏠 | *this* robot: two wheels, both on the centreline, both able to steer ±90° |
| **crab** | both wheels to the same angle → the body slides sideways without rotating |
| **wheelbase** | distance between the two wheels. 1.200 m here |
| **twist** | the standard velocity message: linear `x, y, z` + angular `x, y, z` |
| **MPC** | Model Predictive Control — repeatedly simulate the next few seconds, pick the best steering, do the first step, repeat |
| **NLopt / SLSQP** | the optimisation library and algorithm MPC uses to solve that |
| **motion primitive** | one kind of movement exposed as an action: spin, crab, translate |
| **deadband / slew rate** | ignore commands below a threshold / limit how fast a command may change |

---

## 8. Sensors

| Term | Meaning |
|---|---|
| **lidar** | Light Detection And Ranging — spinning laser, measures distances |
| **2D lidar** | measures one horizontal plane only. **Blind to anything above or below it** |
| **safety scanner** | a lidar certified to stop machinery. Has a hardware output independent of software |
| **FOV** | field of view — the angular span it can see |
| **IMU** | Inertial Measurement Unit — accelerometers and gyroscopes |
| **AHRS** | Attitude and Heading Reference System — an IMU that also outputs orientation |
| **gyro drift** | the IMU's core weakness: it measures rate, so angles are integrated, so errors accumulate without bound |
| **depth camera / RGB-D** | every pixel is a distance; RGB-D adds colour |
| **point cloud** | a set of 3D points — what a depth camera produces |
| **voxel** | a 3D pixel. A cube of space marked occupied or free |
| **intrinsics** | a camera's own optical parameters — focal length, lens distortion |
| **extrinsics** | *where the sensor is mounted* relative to the robot. Getting this wrong misplaces everything it sees |
| **calibration** | measuring intrinsics or extrinsics rather than trusting the drawing |
| **sensor fusion** | combining sensors so each covers the other's weakness |
| **E-stop** | emergency stop. Must work regardless of software state |

---

## 9. Software architecture

The patterns this project is built on. Worth being able to name.

| Term | Meaning |
|---|---|
| **FSM** | Finite State Machine — the system is in exactly one state at a time |
| **state / transition / guard** | a situation / a door between two situations / the condition that must hold before the door opens |
| **`on_enter` / `execute` / `on_exit`** | run once on arrival / every tick while here / once on leaving. Acquire in enter, release in exit |
| **Active Object** | an object with its own thread and its own event to wait on. The pattern the whiteboard draws |
| **supervisor** | holds a list of state machines, starts them, watches the exit flag. **Contains no logic of its own** |
| **event-driven vs polling** | woken when something happens / asking repeatedly "anything new?" |
| **adapter pattern** | an interface in front of an external system so your logic never learns its protocol |
| **dependency inversion** | depend on an interface, not a concrete implementation. Why the unknown CATL protocol does not block us |
| **ABC** | Abstract Base Class — Python's way of declaring an interface |
| **mock** | a fake implementation used for testing |
| **asyncio / event loop / coroutine** | Python's single-threaded concurrency. Many tasks, one thread, switching whenever one waits |
| **race condition** | two things touching the same data at once, result depends on timing |
| **idempotent** | calling it twice has the same effect as calling it once |
| **backoff** | waiting longer between retries so you do not hammer a busy system |
| **failure domain** | how much dies when one thing dies. Splitting one loop into supervised FSMs shrinks it |

---

## 10. Industrial protocols

How factory equipment talks. We do not yet know which one CATL uses.

| Protocol | How to think about it |
|---|---|
| **Modbus TCP** | The oldest and simplest. Numbered registers — "read register 40001". *The register numbers mean nothing on their own*; you need a document telling you 40001 is a temperature. No discovery, no types, no security. Still everywhere because it always works |
| **OPC-UA** | The modern industrial standard. **Self-describing** — you can browse a machine and it tells you it has a "Temperature" in °C. Types, security, authentication built in. Heavier |
| **MQTT** | Publish/subscribe through a broker. A machine publishes to a topic and anyone interested subscribes. Very light, popular for IoT. No built-in meaning — you define the payload |
| **EtherCAT / PROFINET** | Real-time industrial Ethernet, for motion control at microsecond precision. Below our layer |
| **TCP / IP** | The general-purpose network stack. Seer's own API is raw TCP with a 16-byte header + JSON |

**Words that go with them:** *register*, *coil*, *tag*, *node* (OPC-UA sense), *broker*,
*QoS*, *polling*, *subscription*, *endianness* (byte order — Seer's header is big-endian).

---

## 11. Process and quality

The terms in this repo's own workflow.

| Term | Meaning |
|---|---|
| **ADR** | Architecture Decision Record — a short document saying what was decided and *why*, so nobody re-litigates it in six months |
| **technical debt** | a shortcut taken deliberately, tracked so it can be repaid. `docs/debt/registry.md` |
| **regression** | a bug that reappears, or a fix that breaks something that used to work |
| **regression test** | a test written specifically so a fixed bug cannot come back |
| **unit / integration test** | one piece in isolation / several pieces working together |
| **CI** | Continuous Integration — automated build and test on every commit. **Not installed in this repo** — see the notice at the top of `CLAUDE.md` |
| **code review** | someone else reads it before it lands |
| **reverse engineering** | working out how something works from its behaviour or its binary. Governed here by a strict rule: re-implementation output must be **100% identical**, not merely similar |
| **HIL / SIL** | Hardware In the Loop / Software In the Loop — testing with real hardware in the loop, or with it simulated |
| **smoke test** | the quickest check that the thing basically runs |

---

## 12. Saying it out loud

Small things that make you sound like you have been here a while.

| Written | Said |
|---|---|
| CAN | "can", like the tin |
| CANopen | "can-open" |
| SDO / PDO | letter by letter: "ess-dee-oh" |
| CiA 402 | "see-eye-ay four-oh-two" |
| `0x6041` | "six-oh-four-one" or "hex six-oh-four-one" |
| ROS 2 | "ross two" |
| rclpy / rclcpp | "R-C-L-pie" / "R-C-L-C-plus-plus" |
| tf | "T-F" |
| URDF | "you-are-dee-eff" |
| RViz | "R-viz" |
| MCL / AMCL | "M-C-L" / "A-M-C-L" |
| ICP | "I-C-P" |
| IMU | "I-M-U" |
| MPC | "M-P-C" |
| OPC-UA | "O-P-C U-A" |
| ISA-95 | "I-S-A ninety-five" |
| colcon | "coal-con" |
| Gazebo | "gah-ZEE-bo" |
| xacro | "ZAK-ro" |

---

## Related

| Document | Contents |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The plant level — Mini MES, ACS, order flow |
| [`ARCHITECTURE-ROBOT.md`](ARCHITECTURE-ROBOT.md) | The robot stack, and §10 explains every component |
| [`WORKFLOW.md`](WORKFLOW.md) | One order followed end to end |
