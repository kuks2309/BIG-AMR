---
id: 2026-08-19-001
type: mistake
category: verification-gap
status: closed
reflected_assets:
  - src/Sim/trnav_2ws_gazebo/launch/fleet.launch.py
  - src/MES/csm/csm/sim_node.py
---

# 2026-08-19 — I verified a launch argument was DECLARED, not that it ARRIVED

## What I did

I added four charging arguments to `fleet.launch.py` and passed each to the MES
node as two tokens:

    '--low-battery', LaunchConfiguration('low_battery'),

with `default_value=''` meaning "leave the CSM's own default alone". I then
verified the work with `ros2 launch ... --show-args`, saw all four listed with
their descriptions, and reported them as working.

## What was wrong

**launch drops an empty-string argument.** So an unset threshold did not arrive
as an empty value — it did not arrive at all, and the process actually received:

    --robots 3 --battery-scale 1.0 --low-battery --charge-to
    --critical-battery --start-battery 20 --ros-args

Every flag was left with the next flag as its value. I only found this by
reading the command line printed in a `process has died` message during an
unrelated shutdown — not from any check I ran.

`--show-args` proves an argument is DECLARED. It says nothing about what
reaches the process. I checked the half of the path I had just written and
treated it as covering the whole path.

This is the same shape as the UI failure on 2026-08-18: every check I ran was
on the half that worked, and I never loaded the page.

## Why it did not blow up

Pure luck. The run I reported as successful applied `start_battery 20` correctly
because that argument had a non-empty value and sat last. Had the user set only
`charge_to`, argparse would have exited and the MES would never have started —
looking like the simulator failing to launch, not like a launch-file bug.

## Prevention

Joined form, `['--low-battery=', LaunchConfiguration('low_battery')]`. The token
is `--low-battery=` and can never be empty, so it cannot be dropped, and
argparse reads the empty value as "unset".

**Rule: for anything passed BETWEEN processes, verify at the receiving end.**
Declaring, substituting and parsing are three separate steps and each can drop a
value. `--show-args` checks the first. The command line in `ps`, or an
explicit log line from the receiver stating what it applied, checks the last.
`sim_node` now logs the battery levels it actually applied for exactly this
reason — a value that was silently dropped and a value that was never set look
identical from inside the program.
