# Big-AMR — the whole project, explained simply

**Start here if you are new.** This document assumes you know nothing about the project.
It uses short sentences and plain words. Every technical term is explained the first
time it appears.

Read this first. Then read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the plant design,
[`ARCHITECTURE-ROBOT.md`](ARCHITECTURE-ROBOT.md) for what runs on the robot, and
[`GLOSSARY.md`](GLOSSARY.md) when you meet a word you do not know.

> ⚠ **This repository is public.** Customer protocol documents, PLC signal maps and
> network plans are **not** stored here. They live outside the repository. This document
> describes the shape of the system, never the customer's confidential details.

---

## Contents

1. [The project in one page](#1-the-project-in-one-page)
2. [The problem we were given](#2-the-problem-we-were-given)
3. [The trick that makes it possible](#3-the-trick-that-makes-it-possible)
4. [The robot itself](#4-the-robot-itself)
5. [The factory around the robot](#5-the-factory-around-the-robot)
6. [One job, from beginning to end](#6-one-job-from-beginning-to-end)
7. [The software, layer by layer](#7-the-software-layer-by-layer)
8. [How the robot knows where it is](#8-how-the-robot-knows-where-it-is)
9. [What is built and what is not](#9-what-is-built-and-what-is-not)
10. [The questions still open](#10-the-questions-still-open)
11. [Where to find things](#11-where-to-find-things)
12. [If you remember only ten things](#12-if-you-remember-only-ten-things)

---

## 1. The project in one page

A battery factory has robots that carry material between machines. These robots are
called **AMRs** — Autonomous Mobile Robots. They drive themselves around the floor.

One of these robots is called **Foil_A082**. It already works. It was bought from a
vendor, and the vendor's computer inside it drives it around.

We want the robot to do things the vendor's computer cannot do. Mainly, we want it to
park against a machine with millimetre accuracy so material can be handed over safely.

We are not allowed to change the vendor's computer. We cannot reprogram it, rewire it,
or replace it. It is production equipment.

**So we add a second brain instead.**

We put our own computer on the robot, and we put a small electronic board in the middle
of the cable between the vendor's computer and the motors. Most of the time that board
does nothing — it just passes messages through. But when we want control, the board
blocks the vendor's messages and lets our computer drive instead.

While that happens, the board also **lies to the vendor's computer**. It keeps replying
as if nothing changed, so the vendor's computer believes the robot is parked and quiet.
It never raises an alarm.

That is the heart of the project. Everything else is built around it.

---

## 2. The problem we were given

### The robot works, but we cannot open it

The robot's command chain looks like this:

```
fleet controller  →  PLC  →  vendor controller  →  CAN cable  →  wheel motors
```

Every one of those boxes is production equipment. It works. It is certified. Nobody
wants us touching it.

A **PLC** is a rugged industrial computer that runs a machine. A **CAN cable** is the
wire inside the robot that carries commands to the motors.

The vendor controller is called **Seer**. Remember that name — you will hear it every
day.

### Why a second brain is needed at all

Seer is good at driving across a big open floor. It is not good enough at the last two
metres, where the robot has to slide into a machine and line up precisely.

That last part needs different sensors, different maths, and different control. That is
what we are adding.

### The constraint that shapes everything

> **We may not modify Seer, and Seer must never notice anything unusual.**

If Seer notices, it raises an alarm and stops the robot. So our system is designed
around staying invisible to it.

---

## 3. The trick that makes it possible

### The board in the middle

We splice a small board into the CAN cable between Seer and the motors. The board is
called the **Black Panda**, and the software on it is called **the gate**.

Think of it like a person sitting between two people passing notes. Normally they hand
every note straight along. But they *could* stop a note, write their own, and hand that
along instead — and the person receiving it would never know.

### What the gate does when we take control

Three things happen at the same time.

**1. It blocks Seer's commands.** Seer keeps sending orders to the motors. The gate stops
them. The motors never hear them.

**2. It sends fake replies.** When a motor receives a command it normally confirms it.
Since the motors never got Seer's commands, they cannot confirm. So the gate makes up
the confirmations itself. Seer thinks its orders arrived and worked.

**3. It freezes the report.** This is the clever part. Seer constantly asks the motors
"where are you now?". The gate takes a snapshot of the answer at the moment we take
control, and keeps replaying that same snapshot. So while our computer is actually
driving the robot around, Seer sees "not moving, everything normal".

### Why the freeze is necessary

Without it, Seer would see the wheels turning when it did not command them. It would
report a **following error** — the gap between what it asked for and what happened — and
raise an alarm.

### The 300 millisecond gap

The board contains a physical relay, a switch that takes about 150 to 220 milliseconds
to flip. During that time the motors cannot be reached at all.

If Seer got silence for that long it would raise a motor timeout alarm. So the gate
answers Seer from memory for the whole switch-over, covering the gap.

### When we are done

The gate goes back to passing messages through. Seer carries on as normal. It never knew.

---

## 4. The robot itself

### How it is built

Foil_A082 has **two wheels**, one at the front and one at the rear, both on the centre
line. Both wheels are driven, and both can swivel.

That is unusual. Most robots either have fixed wheels like a tank, or steer only at the
front like a car.

Because both wheels swivel, this robot can:

- **drive forward and backward** — both wheels straight
- **rotate on the spot** — wheels turned opposite ways
- **crab** — both wheels turned the same way, so the robot slides sideways without the
  body turning at all

**Crab motion is the important one.** It lets the robot slot straight into a narrow bay
it could never have turned into.

### The numbers

| | |
|---|---|
| Wheelbase (distance between wheels) | 1.200 m |
| Wheel radius | 0.125 m |
| Steering range | ±90° |

### What it can sense

| Sensor | What it gives us |
|---|---|
| **2 safety laser scanners** | distances to everything around it, in one flat horizontal slice |
| **1 IMU** | how fast it is turning and which way it is tilted |
| **6 depth cameras** | a 3D picture of the space close to the robot |
| **Cameras** | ordinary colour video, for recognising objects |

**The laser scanners are special.** They are *safety-rated*. They can stop the robot by
themselves, through a direct electrical connection, with no software involved. If every
program on the robot crashed, the scanners would still stop it before it hit somebody.

**The depth cameras exist for a specific reason.** A flat laser scan only sees one
height. It cannot see a forklift arm sticking out at chest height, a pallet hanging over
its own base, or a low step. The robot would drive straight into any of them. The depth
cameras give the robot a world with a *height*.

### The computers on board

| Computer | Job |
|---|---|
| **Seer** | the vendor's. Drives the robot across the floor |
| **Jetson** | ours. Handles the precise final approach |
| **Black Panda** | the small board. Decides which of the two reaches the motors |

---

## 5. The factory around the robot

### The layers above

A factory's software is arranged in layers. Each layer only talks to its neighbours.

```
  business systems      what to make, how many, for whom
        │
  work management       which machine does what, and when      ← we are building here
        │
  fleet control         which robot goes where
        │
  the robot             drives, docks, carries
```

Different companies use different names for these layers. In this project:

| Name | What it does |
|---|---|
| **ACS** | the fleet controller. Picks a robot, plans its route, stops two robots deadlocking, sends robots to charge |
| **CSM** | *Central System Management*. Watches the machines, decides that material must move, creates jobs, and hands them down to the ACS |

**CSM is the part we are building.** Earlier documents in this repository call it the
"Mini MES" — that was our working name before the official one existed.

### Why CSM has to exist

The ACS knows about **robots**. It does not know *why* anything is being moved.

Somebody has to know that a machine has finished a batch, that the material must reach a
different machine before the next step, and that this counts as one unit of work to be
tracked from start to finish.

That knowledge is not the fleet controller's job. That is what CSM is for.

### What talks to what

The machines on the line are controlled by PLCs. CSM talks to those PLCs directly to
find out what each machine is doing.

The exact protocol and signal list came from the customer. It is documented outside this
repository. What matters architecturally is that our code never learns those details
directly — see [§7](#7-the-software-layer-by-layer).

---

## 6. One job, from beginning to end

Here is a single piece of work travelling through the whole system.

### Step 1 — a machine finishes

A machine finishes processing a batch of material. It signals that it needs an AMR.

### Step 2 — CSM notices and creates a job

CSM is watching the machines. It sees the signal and creates a **job**:

> move material from machine A to machine B

The job is given an identity and starts in a state called `IDLE`.

### Step 3 — CSM asks the ACS for a robot

CSM does not choose a robot. It asks the ACS.

The ACS can answer three ways:

| Answer | Meaning |
|---|---|
| **accepted** | a robot is on its way |
| **busy** | valid job, but no robot free right now |
| **rejected** | this job is wrong and never will work |

**"Busy" is not "rejected".** This distinction caused a real bug. When the two were
treated the same, every job created while another was in progress was thrown away — the
factory produced work and our software deleted it. A busy fleet means *wait*, not *give
up*.

### Step 4 — Seer drives the robot there

The ACS tells Seer where to go. Seer navigates across the floor, avoiding obstacles.

During this whole part, the gate is transparent. Seer is genuinely driving. Nothing
knows the gate is even there.

### Step 5 — arrival, and the handover

The robot stops at an **approach point** just in front of the machine, not at the
machine's own position. Driving to the machine's position would mean driving *into* it.

Now the handover happens:

1. The gate engages
2. Seer's commands stop reaching the motors
3. Seer starts receiving frozen, comfortable-looking replies
4. Our Jetson drives the last stretch, using its own sensors

### Step 6 — the docking handshake

The robot and the machine now exchange signals in a fixed order before anything moves.

The customer's specification defines this precisely. The shape of it is:

1. The machine reports it is **ready** — its doors open, its clamps released, no alarms
2. The machine gives **permission to enter**
3. The robot signals it is **entering**
4. **The machine is now forbidden to move** until the robot has left
5. Material is transferred
6. The robot signals it has **left**
7. The machine is free again

**Two details are worth understanding properly.**

**It is a mutual watchdog.** Both sides send a heartbeat. The machine only allows entry
if it has been hearing the robot continuously. The robot only enters if it has been
hearing the machine continuously. And critically — the machine only decides the robot has
*left* after it has heard nothing for longer than a set time. Silence never means "safe".
Silence means "assume the robot is still inside".

**The order is not negotiable.** Every signal has a precondition. This is not a suggestion
about good practice; it is what stops a machine closing on a robot.

### Step 7 — the second journey

A transport job is **two journeys, not one**:

1. drive to the source and collect
2. drive to the destination and deliver

Going straight to the destination would report material delivered that was never picked
up.

### Step 8 — closing the job

When delivery is done, CSM does two things that are easy to get wrong:

- it tells the **destination** that material arrived
- it tells the **source** that material was collected

**The second one matters more than it looks.** If the source is never told, it stays
marked "finished" forever. It never asks for another robot. The line runs two or three
jobs and then quietly stops, while machines keep finishing batches. This was a real bug
and it took a while to find, because nothing appeared broken.

---

## 7. The software, layer by layer

### The core idea: state machines

A **finite state machine** (FSM) means: the system is in exactly one situation at a time,
and there are defined doors between situations.

A job is always in exactly one of these:

```
IDLE  →  ASSIGNED  →  RUNNING  →  DONE
                          │
                          └────→  FAILED
```

You cannot jump from `IDLE` to `DONE`. There is no door. Not "we check for that" — the
machine literally has no way to express it.

### The three exits that matter

`RUNNING` has **three** ways out: success, failure, and **timeout**.

The timeout is not a nicety. Remember that while the gate is engaged, everything above
is blind *by design* — Seer is being fed a frozen snapshot and reports "parked, normal".

So if our Jetson crashes in the middle of docking, **nobody upstream sees a problem**.
Seer says everything is fine. The ACS repeats it. CSM believes it.

The timeout is the only thing that can end that job.

> **The rule:** any state that waits for something outside itself needs three exits —
> success, failure, and timeout. A waiting state with only a success arrow is a place the
> system can hang forever.

### The runtime shape

CSM is not one big loop. It is a **supervisor** holding several independent state
machines, each running at its own speed.

| Machine | Job | How often |
|---|---|---|
| **equipment monitor** | notices machines that have finished | about once a second |
| **dispatcher** | decides which waiting job gets to ask for a robot next | twice a second |
| **job tracker** | moves every job forward one step | four times a second |

The supervisor itself contains **no logic**. It starts the machines, watches for a stop
signal, and shuts them down. All decisions live inside the machines.

**Why split it up.** With one loop, an error anywhere stops everything, and every part is
forced to run at the same speed. Split apart, one machine crashing does not silence the
others — the supervisor records the failure and its siblings keep going. This is tested.

### The adapter idea

The most important design decision in the whole codebase.

Our state machines **never** talk to a protocol directly. They talk to a plain interface:

```
    get_station_status(machine_id)
    send_station_command(machine_id, command)
```

Behind that interface sits either a real implementation or a fake one for testing.

**Why this mattered so much.** For months the customer's protocol was unknown. If the
protocol details had been allowed into our state machines, the whole project would have
sat waiting for an answer. Behind an interface, everything was written and tested against
a fake factory instead. When the real specification arrived, only one new class needs
writing.

The same reasoning applies to the ACS, whose interface is still undecided today.

This is not theory. It is why there is working, tested software right now instead of a
folder of notes.

---

## 8. How the robot knows where it is

Two questions get confused constantly. They are different.

| Question | Called | How it fails |
|---|---|---|
| How far have I moved since a moment ago? | **odometry** | drifts — small errors pile up forever |
| Where am I on the map? | **localisation** | can be wrong, but does not drift |

### Why drift matters

The IMU cannot tell you an angle. It can only tell you how fast you are turning. To get
an angle, the software adds those up continuously.

Suppose it reports 10.1 degrees per second when the truth is 10.0. A tiny error.

| After | Error |
|---|---|
| 1 second | 0.1° — invisible |
| 1 minute | 6° |
| 10 minutes | 60° |
| 1 hour | a full circle wrong |

Nothing corrects it. Every old mistake is still in there.

A laser scanner does not add anything up. It measures real walls, fresh, every time. If
it is 2 cm out, it is still 2 cm out an hour later. **Noisy, but never drifting.**

Think of the IMU as your wristwatch and the laser as the station clock. The watch is
always with you but gains time. The clock is only occasionally visible but is never
badly wrong. You use the watch all day and reset it whenever you pass the station.

### What we run

**Scan matching for odometry.** Compare the laser scan from a moment ago with the one
from now. Find the shift that makes them line up. That shift is the movement.

This replaces counting wheel rotations, which lies exactly when it matters most — a wheel
spinning on a wet patch reports metres of travel while the robot sits still.

**A particle filter for localisation.** Scatter ten thousand guesses of where the robot
might be. Every cycle: move them all by the odometry, score each by how well the laser
matches the map from there, discard the bad, duplicate the good. The cloud collapses onto
the truth.

The robot never calculates its position directly. It keeps a crowd of guesses and lets
the wrong ones die. That is why it can recover after being confused.

**One thing worth knowing.** Our particle filter is a re-creation of the vendor's own,
rebuilt by studying their compiled software. It was verified to produce bit-for-bit
identical results. The consequence is strategic: the robot can now locate itself
**without Seer**.

---

## 9. What is built and what is not

Honesty here is more useful than optimism.

### Working

| Part | Note |
|---|---|
| **The gate** | tested on the real robot, 76-cycle endurance run passed |
| **Sensor drivers** | lasers, IMU, depth cameras, ordinary cameras |
| **Localisation** | verified bit-identical to the vendor's |
| **Motion maths** | nine kinds of movement, verified correct |
| **Simulation** | the full robot in a simulated warehouse, with a control panel |
| **CSM** | three state machines, 76 automated tests, runs the simulation end to end |

### Not working yet

| Gap | Why it matters |
|---|---|
| **The mux is missing** | This is the big one. Our motion software calculates wheel commands and publishes them — and **nothing receives them**. The component that would route them into the motor driver does not exist. Motion and driving are not joined on the real robot |
| **Wrong robot's measurements** | Nine configuration files still hold the dimensions of a *different* robot — wheels in the wrong place, wheel radius 36% too small |
| **Never connected to the real robot** | All CSM testing has been in simulation. Our development machine is not on the robot's network |
| **No failure testing on the real system** | In simulation every job succeeded, so the failure and timeout paths were only exercised in automated tests |

### Honest summary

The dangerous, clever part — the gate — is proven on real hardware.

The ordinary part — connecting our motion software to the wheels — is not done.

That is an unusual shape for a project, and it is worth saying out loud rather than
discovering later.

---

## 10. The questions still open

These are not criticisms. They are the things that genuinely have not been decided.

| Question | Why it matters |
|---|---|
| **Which state machines, exactly, and what does each own?** | This decides the structure of everything below it. Three are built; the names on the whiteboard were never confirmed |
| **How does CSM hand a job to the ACS?** | Depends on whether the ACS can be modified. Seer cannot be — but nobody has said whether the ACS can |
| **Who commands the gate?** | Our documents assume CSM does. The original sketch did not show that link. This is safety-relevant — whoever commands the gate decides when a robot stops obeying its certified controller |
| **Two systems, one machine** | The customer's own MES and our CSM both connect to the same equipment. Whether both can command it, or only one, needs settling in writing |
| **What language should CSM be?** | It is Python now. Cheap to change today, expensive later |

### One technical risk worth flagging early

The customer's specification says a machine requests a robot by **changing a value**, and
the request is the moment of change — not the value itself.

Our equipment monitor currently **samples** the machines about once a second. If a value
changes and changes back between two samples, we would miss the request entirely, and the
machine would believe it had been heard.

This needs a design decision, not a small fix. The protocol does support being *notified*
of changes rather than asking repeatedly, which is the proper answer.

---

## 11. Where to find things

### Documents

| File | What it is |
|---|---|
| [`PROJECT-SUMMARY.md`](PROJECT-SUMMARY.md) | this document |
| [`README.md`](README.md) | short overview, build and run instructions |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | the plant design — CSM, ACS, how orders flow |
| [`ARCHITECTURE-ROBOT.md`](ARCHITECTURE-ROBOT.md) | what runs on the robot. §10 explains every component one by one |
| [`WORKFLOW.md`](WORKFLOW.md) | one order followed end to end, including the reporting path back |
| [`GLOSSARY.md`](GLOSSARY.md) | every term you will hear, including how to pronounce them |

### Code

```
src/
  MES/mini_mes/        CSM — the job layer we are building
  Navigation/          localisation and odometry
  Control/             the motion maths — nine kinds of movement
  Sensors/             lasers, IMU, depth cameras, ordinary cameras
  Comm/CAN/            talking to the motors through the gate
  Actuators/           talking to the motors directly
  Sim/                 the simulated robot and warehouse
Tools/                 the gate firmware, benches, field kits, standalone tools
docs/                  decisions, audits, debt, verification records
```

### Running it yourself

```bash
# the job layer against a fake factory — instant, no hardware
python3 -m mini_mes.demo --jobs 5

# the same, under the real supervisor, on real timers
python3 -m mini_mes.supervised_demo --seconds 20

# the simulated robot in a warehouse
bash src/Sim/trnav_2ws_gazebo/scripts/start_sim.sh
ros2 run mini_mes sim_node

# all the tests
cd src/MES/mini_mes && python3 -m pytest test/ -q
```

---

## 12. If you remember only ten things

1. **The robot already works.** We are adding a second brain, not building a robot.

2. **Seer is untouchable.** We may not modify it, and it must never notice us.

3. **The gate is the trick.** It blocks the vendor's commands, fakes the replies, and
   freezes the report so the vendor believes the robot is parked.

4. **Crab motion** — both wheels turn the same way and the robot slides sideways without
   rotating. It is why the robot can enter bays it could not turn into.

5. **The safety scanners are independent.** They stop the robot through hardware. No
   software can override them.

6. **Odometry drifts. Localisation does not.** Two different questions with opposite
   failure modes. You need both.

7. **Busy is not rejected.** A busy fleet means wait. Treating them the same throws away
   real work.

8. **Completing a job must free the source, not just the destination.** Otherwise the
   line quietly stops after a few jobs.

9. **Every waiting state needs three exits** — success, failure, and timeout. While the
   gate is engaged, everything above is blind, and the timeout is the only thing that can
   end a stuck job.

10. **Adapters are why this project has working software.** The customer's protocol was
    unknown for months. Because it was kept behind an interface, everything else was
    built and tested anyway.

---

## A note on confidentiality

This repository is **public**.

The customer's protocol specifications, the PLC signal maps, the network plans and the
meeting recordings are **not** in it and must not be added. They belong in a private
location.

This document describes the *shape* of the system — what the parts are and why. That is
ours to explain. The customer's specific signal names, addresses and network layouts are
theirs.

If in doubt, ask before committing.
