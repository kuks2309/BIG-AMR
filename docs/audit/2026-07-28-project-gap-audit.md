# Project Gap Audit — 2026-07-28

Full-repository audit of BIG-AMR looking for gaps, inconsistencies and blockers.
Every finding below was **verified by running the check**, not inferred from
documentation. Commands used are given so each can be re-run.

Scope: `src/` (20 ROS 2 packages), `Tools/`, `docs/`, `References/`, build system,
dependency declarations, git hygiene.

**Summary: 19 findings — 3 blockers, 5 integration gaps, 5 traceability gaps,
6 process/quality gaps.**

---

## A. Blockers — these break correctness or the build

### A-1. 2WS action-server params carry the wrong robot's geometry (CRITICAL)

All 9 params files in `trnav_2ws_action_server/config/` still hold **Carrier AGV**
values. The 2WS refactor updated only `trnav_2ws_core/config/robot_geometry_2ws.yaml`.

| Parameter | Measured Foil_A082 (SSOT) | In the 9 params files | Error |
|---|---|---|---|
| `w1_x` | 0.6039 | 0.330 | −45% |
| `w1_y` | −0.0014 | **+0.135** | wrong sign **and** 96× magnitude |
| `w2_x` | −0.5961 | −0.330 | −45% |
| `w2_y` | −0.0014 | **−0.135** | 96× magnitude |
| `wheel_radius` | 0.125 | 0.080 | −36% |
| `gear_walk` | 32.0 | 20.0 | −38% |
| `body_length` | (unknown) | 1.1974 | **shorter than the 1.200 m wheelbase — physically impossible** |

**Why this is the worst finding.** `w1_y`/`w2_y` are not a small error — they change
the *platform topology*. `±0.135` describes a **diagonal** wheel layout; the real
robot is **inline on the centreline** (`≈0`). The IK computes each wheel's velocity
as `v_iy = vy + omega*x_i`, `v_ix = vx − omega*y_i`, so a non-zero `y` injects a
lateral velocity component that does not exist on this robot. Spin and crab would
be wrong in *shape*, not merely in scale. On top of that, `wheel_radius` 0.080 vs
0.125 mis-scales every commanded speed by 56%.

- Verify: `grep -E "w1_x|w1_y|wheel_radius" src/Control/Motion_Control/2WS/trnav_2ws_action_server/config/spin_params.yaml`
- Affected: all 9 files (`spin`, `turn`, `translate_forward`, `translate_reverse`,
  `crab_linear`, `yaw_control`, `yaw_control_reverse`, `mpc`, `mpc_reverse`)
- Contrast: the QD stack is **self-consistent** (core and params both 0.330/0.135/0.080/20).
  Only the 2WS copy drifted — evidence the refactor was left incomplete.
- Compounding: **no launch file references `robot_geometry_2ws.yaml` at all**
  (`grep -rn "robot_geometry_2ws" --include=*.py src/` → 0 hits). The measured
  values are therefore dead config; the action servers load only the wrong ones.
- The ADR predicted this: *"run-time parameter caution: confirm the launch geometry
  param path points at robot_geometry_2ws.yaml at deploy time."* It was never done.

**Fix**: propagate the six measured values into all 9 params files, or make the
action servers load the core SSOT and delete the duplicated geometry block.
Until then, neither the real robot nor the simulation is being commanded correctly.

### A-2. The workspace does not build from a clean checkout

`colcon build` fails on this machine:

```
CMake Error at CMakeLists.txt:55 (find_library):
  Could not find NLOPT_LIB using the following names: nlopt
Summary: 8 packages finished, 1 failed (trnav_2ws_motion), 1 aborted
         (trnav_interfaces), 8 not processed
```

Only 8 of 20 packages built. `rosdep check` lists four further unsatisfied deps:

```
apt  ros-humble-pcl-ros
apt  liburdfdom-tools
apt  ros-humble-sick-safetyscanners-base
apt  ros-humble-sick-safetyscanners2-interfaces
```

This contradicts the 2WS ADR's claim: *"build: 6/6 finished, error 0"*. That result
was presumably obtained on the Jetson where the deps were already present, and is
not reproducible on a fresh machine. There is no bootstrap script and no README
setup step listing these packages (the README I wrote lists requirements but not
this exact apt set — worth adding).

- Verify: `colcon build` ; `rosdep check --from-paths src --ignore-src -r`

### A-3. `<depend>nlopt</depend>` is an invalid rosdep key

`trnav_2ws_motion/package.xml:20` and `trnav_motion_qd/package.xml:20` declare
`nlopt`, with a comment asserting *"rosdep key 'nlopt' → libnlopt-cxx-dev/libnlopt-dev"*.
That mapping does not exist:

```
$ rosdep resolve nlopt
ERROR: no rosdep rule for 'nlopt'
$ rosdep resolve libnlopt-dev
#apt
libnlopt-dev
```

So `rosdep install` **fails** on these packages rather than installing the library —
the declaration looks correct but does nothing. The comment states the intent
accurately; the key itself is simply wrong.

**Fix**: change both to `<depend>libnlopt-dev</depend>`.

---

## B. Integration gaps — parts that do not connect

### B-1. The mux does not exist; 16 launch files are unrunnable

Five packages are referenced by launch files but are absent from the repository:

| Missing package | Role |
|---|---|
| `trnav_motion_mux` | routes `/motion/wheel_cmd/*` → `/motor/wheel_cmd` |
| `trnav_motion_supervisor` | selects the active motion source |
| `translate_sim_odom` | SIL odometry simulator |
| `amr_safety_watchdog` | safety gating |
| `sil_pose_adapter` | SIL pose bridge |

Consequently **16 launch files cannot run** — 8 in `trnav_2ws_action_server/launch/`
and 8 in `trnav_motion_action_server/launch/` (all `sil_*` and `hil_*` variants).
These are inherited from upstream TR_Nav and were never pruned or ported.

- Verify: `grep -rl "trnav_motion_mux\|translate_sim_odom\|amr_safety_watchdog" --include=*.py src/`

This is the same gap the SW-structure verification pass already confirmed from the
other direction: no in-repo subscriber for `wheel_cmd`, no server for
`/select_motion_source`.

### B-2. `motor_control` has no source code

`src/Actuators/motor_control/` contains **only** `docs/`. The CANopen SDO master —
described throughout the docs as the component that owns `/cmd_vel`, `/odom`,
`/estop` and the CAN link — is not in this repository. The full-project SW structure
doc analyses it in detail at `file:line` level, so it existed when that analysis ran.

### B-3. Empty stubs still unimplemented

`Comm/CAN/can_relay`, `Control/Seer`, `Safety`, `Sensors/Lidar/3D`,
`Control/Motion_Control/{4IS,DD}` — all zero code files. Notably `Comm/CAN/can_relay`
is empty even though the Panda firmware exists under `Tools/Can_Relay/`, so the
directory structure implies a ROS 2 package that was never created.

### B-4. No camera anywhere

No camera package, no camera code, no camera in any config
(`grep -rniE "camera|realsense|aruco|image_raw" src/` → 0 hits outside my sim).
Flagging this because the sibling project `docking_gui_dist` achieves precision
docking entirely through ArUco visual servoing. If Big-AMR is eventually meant to
dock, the sensor it would need is absent. **This is inference, not a stated
requirement** — no document in this repo says docking is a goal.

### B-5. Simulation runs on placeholder physical values

The Gazebo model I added uses guesses for chassis length/width/height (1.6 × 0.9 ×
0.5 m), mass (250 kg), caster positions, and both lidar mount points. Only the wheel
geometry is real. Dynamics-sensitive results from this sim are therefore not
trustworthy yet; kinematic results are.

---

## C. Traceability gaps — evidence cited but not present

The repo's documentation convention is strong (`file:line` for every claim). These
break that chain:

| Cited path | Cited by | Status |
|---|---|---|
| `Tools/Kinematics/chassis_kinematics.py` | 2WS ADR, as **source 1 of 2** for the measured geometry | **missing** |
| `src/Actuators/motor_control/config/tongyi_amr.yaml` | 2WS ADR, as **source 2 of 2** | **missing** |
| `docs/sw_structure/system-architecture/2026-06-27.md` | the architecture of record, cited by nearly every doc (D1–D17) | **missing** |
| `docs/claude_guideline/sw_structure/structure.md` | the SOP the SW-structure docs claim to follow | **missing** |
| `docs/can_relay/field-record-orin-nx-2026-07-25.md` | `safety_seer_gate.h` comments, as the basis for the transition-cover design | **missing** |
| `CLAUDE.md` | referenced by the handoff doc | **missing** |

**Impact**: the 2WS ADR's headline justification is a *"2-source cross-check"* of the
measured geometry — and **neither source is in the repository**. The numbers in
`robot_geometry_2ws.yaml` cannot be independently verified from this repo alone.
Given finding A-1 turns on exactly which geometry is correct, this matters.

- Verify: `ls Tools/Kinematics/chassis_kinematics.py src/Actuators/motor_control/config/tongyi_amr.yaml`

---

## D. Process and quality gaps

### D-1. Zero automated tests

No test file exists in any of the 20 packages (`find src -name "test_*.py" -o -name
"*_test.cpp"` → empty). For a system that drives a 250 kg machine and has already
physically damaged a steering axis, the kinematics at minimum deserve unit tests —
they are pure functions with known-good reference outputs from `chassis_kinematics.py`.

### D-2. No CI

No `.github/` directory. Nothing catches the build break in A-2, the invalid rosdep
key in A-3, or config drift like A-1.

### D-3. QD and 2WS are a 50-file copy, not a shared library

`trnav_2ws_*` is a mechanical rename of `trnav_*`. Verified: after substituting
`two_ws→qd`, `TwoWs→Qd`, `trnav_2ws→trnav`, `qd_inverse_kinematics.cpp` is
**byte-identical** except the include path. ~50 source files are duplicated.

The ADR argues this deliberately (independence, no cross-build coupling) and that is
a legitimate trade. But A-1 is precisely the failure mode duplication invites: a fix
applied to one copy silently not applied to the other. Any future kinematics fix must
be applied twice, by hand, with nothing checking that it was.

### D-4. `.gitignore` missing on `main`

Added on `feature/gazebo-2ws-sim`, not yet on `main`. Until that merges, `build/`,
`install/` and `log/` are untracked-but-visible and easy to commit by accident.

### D-5. Open technical debt

`debt-002` — the IMU `base_link→imu_link` static TF is `(−0.37, 0, 0.29)`, a **TR-AMR**
measurement carried over verbatim. Big-AMR's real IMU mount was never measured. Any
IMU-referenced computation inherits this error. Still open.

### D-6. Unresolved field problems

From `docs/can_relay/test-process.md` and `docs/issues_and_fixes/`:

- **Steering locks at −116°** after repeated flash/re-homing cycles and stops
  responding to PC position commands. Marked *"homing method needs re-establishing
  — separate diagnosis"*. Unresolved.
- **Seer alarm 52954** (re-homing timeout) diagnosis is explicitly *"reproduction not
  performed — next session must resume"*. The power-cycle test was armed twice and
  never actually executed, so the zeroDI-hardware hypothesis is neither confirmed nor
  ruled out.
- Related: `docs/claude-mistake/2026-07-27-002` records a steering axis physically
  jammed at 137° (outside ±90°) by an unverified command. A-1 is a standing invitation
  to repeat that class of incident.

---

## Recommended order of work

1. **A-1** — reconcile the 2WS geometry. Nothing downstream is meaningful until the
   action servers command the robot they are actually attached to.
2. **A-3** then **A-2** — fix the rosdep key, document the apt set, get a clean
   checkout building.
3. **C** — recover or vendor the two geometry source files, so A-1 can be closed
   against evidence rather than assumption.
4. **D-1** — unit-test the IK against `chassis_kinematics.py` reference outputs. This
   is the cheapest guard against A-1 recurring, and it is the one component with a
   known-correct oracle.
5. **B-1** — implement the mux, or delete the 16 dead launch files so the working set
   is honest.

---

## What is in good shape

Worth stating plainly, since the above is all problems:

- The CAN relay gate is real, field-tested, and passed a 76-cycle endurance run.
- The kinematics **logic** is verified correct against Seer's own implementation to
  4 decimal places — the flaw in A-1 is in configuration, not in the algorithm.
- The documentation discipline is unusually strong: ADRs with rejected alternatives,
  `file:line` evidence, an independently-verified structure analysis (173/178 claims
  confirmed), a debt register, and a mistake log. Most of this audit's findings were
  possible *because* the project documents itself so carefully.
- The engineering record in `issues_and_fixes.md` (missing 120 Ω terminator, cp949
  hook failures) is genuinely high quality root-cause work.
