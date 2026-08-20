# Road and traffic rules

Stated by the project owner on 2026-08-20, first in writing and then against a
hand drawing of the layout. This document records **only** what was specified.
Nothing here is inferred, measured or recommended.

Supersedes the earlier version of this file from the same day; what changed is
noted at the end.

---

## 1. The road

The road is a **rectangular closed loop** around the hall.

It is **one road with two lanes**, divided by a line down the middle. One lane
carries traffic one way round; the other carries it back.

There are **no connectors** between the lanes and **no crossings** through the
middle of the hall. The only things attached to the loop are the station spurs.

## 2. Which lane goes which way

- The lane **nearer the centre of the hall** runs in the **CTR1 → CTR4**
  direction.
- The lane **nearer the stations** runs the **opposite** way.

The loop is closed, so that one fact fixes the direction of circulation
everywhere.

## 3. Choosing a lane

An AMR **always takes the shortest path**. Because the two lanes run opposite
ways, that decides the lane: whichever one reaches the destination in fewer
metres.

**The choice is made at the spur, not on the road.** A robot leaving a dock
already knows where it is going next, so it picks its lane before it sets off.
There is no reason to change lane once moving, and no lane changing on the road.

## 4. Stations and spurs

Stations sit **outside the loop, on both long sides**:

- ASRS · GRV1 · GRV2 · GRV3 · GRV4 · WIP_GRV
- SLT · CTR1 · CTR2 · CTR3 · CTR4 · WIP_CTR · WIP_SLT

Every dock keeps its **spur** — a short perpendicular branch from the road to
the station. Each station has two, **LD and ULD**.

**From both lanes an AMR can reach both the LD and the ULD.**

Parking bays and chargers stay exactly as they are today, and are connected to
the road by spurs in the same way the stations are.

## 5. Rotating

**An AMR does not rotate on the road.**

It rotates in two places only:

- **at a corner** of the loop, to follow the road round;
- **at a spur**, when it has come back out of a dock and is deciding where to go
  next.

## 6. Leaving a dock

When docking is finished the AMR comes back out to the **spur** — the point it
left the road at. There it:

1. **stops**;
2. works out its route and decides which way it is going;
3. **rotates** accordingly;
4. takes the **correct lane**;
5. **moves forward** onto the road.

Turning happens at the spur and at the corners. Nowhere else.

## 7. The red light

**Both lanes are blocked** past that point for the whole of this span:

- it **begins** when the AMR starts changing direction at the spur;
- it **ends** only when the AMR **has gone out onto the road**.

The light stays on for the entire time, not just while the AMR is turning. The
turn and the move out onto the road are one protected manoeuvre, and the light
does not clear part way through it.

No other AMR may pass during that time.

It is a red light signal, and it is meant to be that simple.

## 8. Waiting for a busy dock

The docking system itself is unchanged.

If an AMR arrives for a dock another AMR is already holding, it **waits outside,
on the road**, until the docked AMR has finished and moved out. Then it takes
the dock.

It waits **clear of the spur**, so the AMR inside can come out past it. Because
entry to a dock is sideways, the waiting AMR does not have to occupy any
particular point to be able to enter — it moves across when the dock frees.

Robots behind it in the same lane wait. There is no overtaking: the other lane
runs the other way.

## 9. Everywhere is the same

The road is **uniform all the way round** and every spur is the same shape.
There are no wide sections, no narrow sections and no special cases.

This is a deliberate simplification and the reason for it is scope: **CSM is
the product, and the simulation is its test harness.** The harness needs the
right topology — stations, ports, spurs, two directions of travel — not the
right metres. The measured CAD says the real corridors vary between 2.10 m and
2.60 m and that only four are wide enough to run two abreast; none of that
changes a CSM decision, so none of it is modelled.

If the world is ever meant to resemble the plant rather than exercise the CSM,
this section is the first thing that has to go.

## 10. The fleet

**Ten AMRs**, split **2 / 2 / 6** across legs A, B and C — the deck's own figure
[S16], and already what `plant.ROBOT_SEGMENT` carries. The simulator runs three
by default; `robots:=10` runs them all.

Six robots share leg C, in one lane, with no overtaking. §8 therefore matters
more on that leg than anywhere else, and see "Not settled here".

## 11. Guiding principle

**Keep the solution easy.**

---

## What this replaces

Before the first version of this document, the network had lane connectors and
mid-hall crossings, and AMRs rotated while on the road. Sections 1, 3 and 5
remove those.

**Changed from the first version of today, after the drawing:**

- §2 now states which lane runs which way. The first version did not say.
- §4 records that stations sit on both long sides with two spurs each, and that
  parking and chargers join the road the same way.
- §5 adds **corners** as a place rotation is allowed. The first version implied
  the spur was the only one, which cannot work: every GRV→CTR trip crosses a
  short side.
- §8 is new — what a robot does when the dock it wants is occupied.

## Not settled here

- **Where a waiting robot stops**, exactly. §8 says "clear of the spur"; a
  reproducible simulation needs a defined offset rather than wherever the robot
  happened to be, or two robots waiting for one dock will not queue the same way
  twice.
- **Whether waiting off the lane is wanted later.** The measured CAD puts a
  queue position 3.54 m behind each dock (ADR 2026-08-11), which would keep a
  waiting robot out of the lane entirely. That is a throughput question for
  leg C's six robots, not a correctness one, and it is not part of this design.
