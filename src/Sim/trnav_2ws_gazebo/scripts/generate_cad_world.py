#!/usr/bin/env python3
"""generate_cad_world.py — build cad_plant.world from csm/plant_cad.py.

    ros2 run trnav_2ws_gazebo generate_cad_world.py

This is the CUSTOMER'S plant, not ours. Every number comes from the two layout
drawings via `plant_cad.py`; nothing here is invented, and where the drawing is
silent the world is EMPTY rather than filled in with a guess. An empty patch on
screen is a question to ask the customer, and it should look like one.

WHY A SECOND GENERATOR RATHER THAN A FLAG ON THE FIRST.

`generate_world.py` builds `factory.world` from `plant.py` — the 43 x 26 m world
the fleet has actually been verified in. That world works and must keep working.
This one is ~10x larger in each direction, uses absolute CAD coordinates, and has
no robots in it yet. Sharing a generator between them would mean every change to
one is a risk to the other, for the sake of a `box()` helper.

ABSOLUTE COORDINATES.

The world origin is the CAD origin. A machine at x=113.25 in the drawing is at
x=113.25 in Gazebo, so any point can be read off one and typed into the other.
This costs nothing except that the interesting area is 100-290 m from the origin,
which is why the GUI camera below is parked over the cathode cell rather than at
the origin — at the origin you would be looking at bare ground 200 m from
anything.

WHAT IS DRAWN AND WHAT THAT MEANS

    walls           hall shell, 306 x 209 m               solid
    machines        4 gravure, 4 slitter                  solid
    ASRS            2 racking walls + a crane aisle        walls solid
    coater cells    4, drawn as boundaries                VISUAL ONLY
    lane paint      35 rectangles, flat on the floor      VISUAL ONLY
    junctions       30 crossings, small pale squares      VISUAL ONLY
    AGV positions   45 pads with a nose stripe            VISUAL ONLY
    coater LD/ULD   8 named stations, green / orange      VISUAL ONLY
    GRV1 LD/ULD     2 named stations                      VISUAL ONLY
    WIP access      8 pads on two columns, 4 groups       VISUAL ONLY
    ASRS dock       the ONE position found, flagged       VISUAL ONLY
    charging bay    1 of the 5 the deck says exist        VISUAL ONLY
    grid posts      every 50 m on the hall edge           solid, thin

Lane paint is paint. Making it collidable would put a 2.1 m kerb around every
drivable surface, which is the opposite of what a lane is. The same reasoning the
first generator learned the hard way with docking markers: a printed label is not
an obstacle.

A PAD'S COLOUR SAYS HOW MUCH WE KNOW ABOUT IT. Green is a measured AGV position
with nothing else claimed. Gold is the single ASRS dock, drawn apart because leg A
depends on it and one position cannot serve a 57 m machine. Magenta is the eight
positions at x 185.62 that we CANNOT yet name — the deck says Slitter LD is 4EA
and there are eight of them, so calling them the slitter stations would be a
reading, not a measurement. Purple is WIP rack access.

Making uncertainty a colour rather than a comment is deliberate: this world is
looked at far more often than this file is read, and a guess that looks identical
to a measurement will eventually be treated as one.

NOT DRAWN, BECAUSE WE DO NOT YET KNOW IT — see
`docs/gazebo_world/open-questions.md`:

  * lane DIRECTION. The deck's slide 16 DOES carry direction arrows over the
    cell; they have not yet been read off into a direction per lane.
  * the anode cell (y < 100), which is in the hall but not in our model
  * WIP rack ENVELOPES. The access positions are drawn; the racks themselves,
    and which of the four groups is coater and which slitter, are not known.
  * structural columns
  * 4 of the 5 cathode Big AGV chargers
  * the gravure LD/ULD stations for GRV2-4, and all four slitter LD stations.
    The coaters' and GRV1's are placed; the two do NOT share a pattern (coater
    separates LD/ULD in x, gravure in y), so nothing is extrapolated to the rest.
"""

import math
import os
import sys

from csm import plant_cad as P

#: Machine bodies stand this tall. The drawings are a plan view and carry no
#: heights at all, so this is a DRAWING CONVENTION, not a measurement — enough to
#: read the layout in a 3-D view and to block a robot. Do not treat it as plant
#: data; if heights ever matter, they have to be asked for.
MACHINE_H = 3.0
WALL_H = 4.0
WALL_T = 0.30

#: Paint sits just off the floor so it renders above the ground plane instead of
#: fighting it for the same pixels.
PAINT_Z = 0.01
PAINT_T = 0.02

#: ONE COLOUR FOR EVERY ROAD. Lanes, coater spurs, coater station links, gravure
#: cross-roads and gravure spurs are all road, so they all look like road —
#: asked for on 2026-08-14. Before this there were three appearances: grey for the
#: measured lanes, solid salmon for the spurs and half-opacity salmon for the
#: derived connectors.
#:
#: WHAT THAT COSTS. The half opacity was carrying "derived, not measured" — the
#: coater's eight links and all the gravure roads come from the project lead's
#: description, not the drawing. That distinction is now ONLY in plant_cad
#: (coater_connectors, gravure_cross_roads, gravure_spurs) and no longer visible
#: on screen. If it needs to be visible again, use a marker rather than a colour,
#: because a second road colour reads as a second KIND of road.
ROAD_RGBA = (0.62, 0.66, 0.72, 1)

#: HOW TALL A STATION MARKER STANDS.
#:
#: This world is 305 x 209 m. A 2 x 1.6 m pad on the floor is invisible from any
#: viewpoint that shows more than one machine, and the first version put the
#: stations in the world correctly and left them impossible to find. The marker
#: is a sightline aid, not plant data — nothing in the drawing says a station has
#: a post — so it is deliberately taller than the 3.0 m machines it stands beside.
STATION_POST_H = 7.0
STATION_POST_W = 0.5

COLOURS = {
    "ASRS": (0.95, 0.75, 0.15, 1),      # store
    "GRV":  (0.30, 0.55, 0.90, 1),      # gravure
    "CTR":  (0.85, 0.35, 0.30, 1),      # coater
    "SLT":  (0.45, 0.80, 0.40, 1),      # slitter
}

HDR_TEMPLATE = """<?xml version="1.0"?>
<!--
  cad_plant.world — GENERATED by scripts/generate_cad_world.py from
  csm/plant_cad.py. DO NOT EDIT BY HAND.

  The FM2 cathode cell as the customer's drawings describe it, in ABSOLUTE CAD
  COORDINATES: a position here is the same position in the DWG. Sources and the
  full derivation are in plant_cad.py; what is still unknown is listed in
  docs/gazebo_world/open-questions.md.

  There are no robots in this world. It is the plant on its own, so that the
  geometry can be checked against the drawings before anything drives in it.
-->
<sdf version="1.6">
  <world name="cad_plant">
    <include><uri>model://sun</uri></include>
    <include><uri>model://ground_plane</uri></include>

    <physics type="ode">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
      <ode>
        <solver><type>quick</type><iters>100</iters><sor>1.3</sor></solver>
        <constraints>
          <cfm>0.0</cfm><erp>0.2</erp>
          <contact_max_correcting_vel>100.0</contact_max_correcting_vel>
          <contact_surface_layer>0.001</contact_surface_layer>
        </constraints>
      </ode>
    </physics>

    <scene>
      <ambient>0.6 0.6 0.6 1</ambient>
      <background>0.75 0.80 0.86 1</background>
      <shadows>true</shadows>
    </scene>

    <gui>
      <!-- Over the cathode cell, not the origin. The origin is bare floor 200 m
           from the nearest machine. -->
      <camera name="user_camera">
        <pose>{cam_x:.1f} {cam_y:.1f} {cam_z:.1f} 0 0.95 1.05</pose>
      </camera>
    </gui>

    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
      <ros>
        <namespace>/gazebo</namespace>
      </ros>
      <update_rate>30.0</update_rate>
    </plugin>
"""

FTR = """  </world>
</sdf>
"""


def box(name, x, y, z, sx, sy, sz, rgba, yaw=0.0, solid=True):
    """A static box. solid=False gives a VISUAL ONLY body — no collision."""
    r, g, b, a = rgba
    collision = (f"""
        <collision name="c"><geometry><box><size>{sx:.3f} {sy:.3f} {sz:.3f}</size></box></geometry></collision>"""
                 if solid else "")
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.4f}</pose>
      <link name="link">{collision}
        <visual name="v">
          <geometry><box><size>{sx:.3f} {sy:.3f} {sz:.3f}</size></box></geometry>
          <material>
            <ambient>{r} {g} {b} {a}</ambient>
            <diffuse>{r} {g} {b} {a}</diffuse>
          </material>
        </visual>
      </link>
    </model>"""


def rect(name, x0, y0, x1, y1, z, h, rgba, solid=True):
    """A box given by its extent rather than its centre — the form the CAD data
    is in, so the conversion happens once here instead of at every call site."""
    return box(name, (x0 + x1) / 2, (y0 + y1) / 2, z + h / 2,
               x1 - x0, y1 - y0, h, rgba, solid=solid)


def main():
    parts = []

    # MINIMAL IS THE DEFAULT — the four machine rows and the roads, nothing else.
    #
    # Asked for on 2026-08-13: "remove everything else from the gazebo world except
    # coater asrs gvr slitter roads". At 274 models the world had become hard to
    # read: 135 of them were AGV pads and their nose stripes, and the machines were
    # lost among markers.
    #
    # NOTHING IS DELETED. `--full` restores the survey layer — walls, AGV pads,
    # junction markers, WIP access, charging and grid posts — because every one of
    # those is measured data and dropping it from the code would lose evidence.
    #
    # LD/ULD STATIONS COUNT AS PART OF THEIR MACHINE and stay in both modes. A
    # coater's LD is where the coater is loaded; it is not a survey marker. The
    # gravure's eight were placed one request earlier, so removing them here would
    # undo that.
    full = "--full" in sys.argv
    (wx0, wx1), (wy0, wy1) = P.HALL_X, P.HALL_Y

    # ------------------------------------------------------------- shell
    if full:
        wall = (0.80, 0.80, 0.82, 1)
        parts.append(rect("wall_south", wx0, wy0 - WALL_T, wx1, wy0, 0, WALL_H, wall))
        parts.append(rect("wall_north", wx0, wy1, wx1, wy1 + WALL_T, 0, WALL_H, wall))
        parts.append(rect("wall_west", wx0 - WALL_T, wy0, wx0, wy1, 0, WALL_H, wall))
        parts.append(rect("wall_east", wx1, wy0, wx1 + WALL_T, wy1, 0, WALL_H, wall))

    # ------------------------------------------------------------ machines
    #
    # A COATER IS DRAWN AS AN OUTLINE, NOT A SOLID.
    #
    # COATER_X spans 24.83 m, which Q1 established is the coater CELL INCLUDING
    # ITS AGV APRON — its LD station is at x 125.58 and its ULD at 136.58, both
    # inside that span, and the spur runs in to x 124.56 to serve them. Drawing
    # the cell as a filled 3 m box put the machine on top of its own stations:
    # they were in the world, correctly placed, and completely hidden.
    #
    # It would also be wrong physically. A robot is meant to drive in there, so
    # the cell must not be an obstacle. Where the actual machine stands inside
    # the cell is NOT known — the drawing gives the cell, not the body — so the
    # honest thing is a boundary and empty floor, not a guessed smaller box.
    #
    # The gravure (6.9 m) and slitter (13.05 m) footprints are machine-sized
    # rather than cell-sized and stay solid, but whether they are also cells has
    # NOT been checked. See docs/gazebo_world/open-questions.md.
    for name, x0, y0, x1, y1 in P.machines():
        rgba = COLOURS.get(name[:4] if name == "ASRS" else name[:3],
                           (0.55, 0.55, 0.58, 1))
        if name == "ASRS":
            # A STORE WITH AN AISLE, NOT A SLAB. Two racking walls the full
            # length, a crane aisle between them, at rack height rather than the
            # 3 m machine convention — see plant_cad's ASRS_AISLE_W for what is
            # measured here (the footprint) and what is not (the split, the
            # height). The aisle is PAINT: it belongs to the stacker crane, so it
            # must not be an obstacle, but it is not AGV road either and is
            # coloured apart from the lanes to say so.
            for rname, rx0, ry0, rx1, ry1 in P.asrs_racks():
                parts.append(rect(f"m_{rname}", rx0, ry0, rx1, ry1, 0,
                                  P.ASRS_HEIGHT, rgba))
            ax0, ay0, ax1, ay1 = P.asrs_aisle()
            parts.append(rect("ASRS_crane_aisle", ax0, ay0, ax1, ay1,
                              PAINT_Z, PAINT_T, (0.75, 0.60, 0.20, 1),
                              solid=False))
            continue
        if name.startswith("CTR"):
            # THE COATER CELL BOUNDARY IS NOT DRAWN in minimal mode — asked for on
            # 2026-08-14, "we don't need the red line boundary for each coater".
            #
            # CONSEQUENCE, and it is not small: nothing then marks where a coater
            # IS. Its stations and its spur are drawn, the 24.83 x 7.72 m cell is
            # not, so the coater row reads as stations floating on open floor.
            #
            # We cannot substitute the machine body, because we do not know it.
            # COATER_X is the coater CELL INCLUDING ITS AGV APRON — that is what
            # the drawing gives and what settled the lane-through-coater question
            # (plant_cad COATER_LD_X). Where the machine stands inside the cell has
            # never been established, so drawing a smaller box would be a guess of
            # exactly the kind that put the gravure in the aisle.
            #
            # `--full` still draws the boundary.
            if not full:
                continue
            t = 0.25
            for tag, ex0, ey0, ex1, ey1 in (
                    ("s", x0, y0, x1, y0 + t), ("n", x0, y1 - t, x1, y1),
                    ("w", x0, y0, x0 + t, y1), ("e", x1 - t, y0, x1, y1)):
                parts.append(rect(f"cell_{name}_{tag}", ex0, ey0, ex1, ey1,
                                  0, 0.35, rgba, solid=False))
            # Corner posts, so the cell reads as a bounded area from across the
            # hall without walling it off.
            for cx in (x0, x1):
                for cy in (y0, y1):
                    parts.append(box(f"cell_{name}_p{cx:.0f}_{cy:.0f}", cx, cy,
                                     1.5, 0.3, 0.3, 3.0, rgba, solid=False))
        else:
            parts.append(rect(f"m_{name}", x0, y0, x1, y1, 0, MACHINE_H, rgba))

    # -------------------------------------------------------------- lanes
    #
    # Painted, not built. See the module docstring: a collidable lane is a kerb.
    for i, (x0, y0, x1, y1) in enumerate(P.lanes_drawn(), 1):
        parts.append(rect(f"lane_{i:02d}", x0, y0, x1, y1,
                          PAINT_Z, PAINT_T, ROAD_RGBA, solid=False))

    # ------------------------------------------------- two-lane roads
    #
    # A DASHED CENTRE LINE says "two lanes", and CHEVRONS say which way each runs.
    #
    # The divider is a marking, not a road, so it is not ROAD_RGBA — a second road
    # colour would read as a second kind of road, which is the confusion the single
    # road colour was introduced to remove.
    #
    # THE CHEVRONS ARE AN ASSUMPTION AND ARE COLOURED LIKE ONE. Direction is open
    # question A6; plant_cad.LANE_DIRECTION_RULE applies ordinary keep-right
    # traffic and can be flipped in one line. Nothing routes on them.
    DIVIDER_RGBA = (0.97, 0.97, 0.97, 1)
    ARROW_RGBA = (0.95, 0.75, 0.15, 1)
    DASH, GAP, DIV_W = 3.0, 3.0, 0.16
    ARROW_EVERY, ARM_L, ARM_W = 12.0, 1.8, 0.20

    for road in P.two_lane_roads():
        name, axis, la, lb, div, lo, hi = road
        # --- dashed divider, down the middle of the pair
        n = 0
        s = lo + GAP
        while s + DASH <= hi:
            n += 1
            if axis == "ns":
                parts.append(rect(f"{name}_div{n:02d}", div - DIV_W / 2, s,
                                  div + DIV_W / 2, s + DASH,
                                  PAINT_Z + PAINT_T * 3, PAINT_T,
                                  DIVIDER_RGBA, solid=False))
            else:
                parts.append(rect(f"{name}_div{n:02d}", s, div - DIV_W / 2,
                                  s + DASH, div + DIV_W / 2,
                                  PAINT_Z + PAINT_T * 3, PAINT_T,
                                  DIVIDER_RGBA, solid=False))
            s += DASH + GAP

        # --- chevrons, one set per lane, pointing the way that lane runs.
        # Suppressed entirely when LANE_DIRECTION_RULE is "none" — the ACS meeting
        # says lanes are bidirectional, so the direction may not exist to draw.
        if P.LANE_DIRECTION_RULE == "none":
            continue
        for tag, lane, head in zip("ab", (la, lb), P.two_lane_directions(road)):
            if axis == "ns":
                mid = (lane[0] + lane[2]) / 2.0
                centre = lambda t: (mid, t)          # noqa: E731 - local, clear
            else:
                mid = (lane[1] + lane[3]) / 2.0
                centre = lambda t: (t, mid)          # noqa: E731
            yaw = math.radians(head)
            k = 0
            t = lo + ARROW_EVERY / 2.0
            while t <= hi:
                k += 1
                tx, ty = centre(t)
                for side, arm in ((+1, "l"), (-1, "r")):
                    ang = yaw + math.pi + side * math.radians(38)
                    parts.append(box(
                        f"{name}{tag}_arw{k:02d}{arm}",
                        tx + math.cos(ang) * ARM_L / 2,
                        ty + math.sin(ang) * ARM_L / 2,
                        PAINT_Z + PAINT_T * 3, ARM_L, ARM_W, PAINT_T,
                        ARROW_RGBA, ang, solid=False))
                t += ARROW_EVERY

    # A junction is where two painted rectangles overlap, so it is already
    # covered in lane grey. Marked in a second colour because these are the
    # points a reservation scheme has to arbitrate, and there are thirty of them
    # — a number that is much easier to believe once it is on screen.
    if full:
        for i, (jx, jy) in enumerate(P.JUNCTIONS, 1):
            parts.append(box(f"junction_{i:02d}", jx, jy,
                             PAINT_Z + PAINT_T + 0.005, 1.2, 1.2, 0.01,
                             (0.95, 0.55, 0.15, 1), solid=False))

    # ------------------------------------------------------ AGV positions
    #
    # Drawn from the verbatim measured list, not from the grouped constants, so
    # what appears on screen is what is in the drawing. The nose stripe carries
    # the heading: a pad alone cannot show which way a robot parked there faces,
    # and the rot 0 / rot 180 pairing is the whole evidence for LD/ULD.
    l, w = P.ROBOT_3_5T[1], P.ROBOT_3_5T[0]
    n_asrs = n_unnamed = 0
    for i, (px, py, rot) in enumerate(P.AGV_POSITIONS if full else (), 1):
        yaw = math.radians(rot)
        # Role by position, not by index, so the classification survives any
        # re-ordering of AGV_POSITIONS.
        is_asrs = any(abs(px - ax) < 0.1 and abs(py - ay) < 0.1
                      for ax, ay in P.ASRS_DOCK_FOUND)
        is_unnamed = (abs(px - P.SLITTER_DOCK_X) < 0.1
                      and any(abs(py - sy) < 0.1 for sy in P.SLITTER_DOCK_Y))
        if is_asrs:
            rgba, nose = (0.95, 0.75, 0.15, 1), (0.55, 0.40, 0.05, 1)
            n_asrs += 1
        elif is_unnamed:
            rgba, nose = (0.80, 0.35, 0.75, 1), (0.45, 0.15, 0.42, 1)
            n_unnamed += 1
        else:
            rgba, nose = (0.25, 0.70, 0.35, 1), (0.05, 0.35, 0.10, 1)
        parts.append(box(f"agv_pos_{i:02d}", px, py, PAINT_Z + PAINT_T / 2,
                         l, w, PAINT_T, rgba, yaw, solid=False))
        parts.append(box(f"agv_nose_{i:02d}",
                         px + math.cos(yaw) * (l / 2 - 0.15),
                         py + math.sin(yaw) * (l / 2 - 0.15),
                         PAINT_Z + PAINT_T + 0.005,
                         0.30, w * 0.8, 0.01, nose, yaw, solid=False))
        # A post on the ASRS dock only. It is the one position in this world that
        # a whole leg hangs on (open question A1, BLOCKING), and at ground level
        # it is one pad among forty-five with nothing to distinguish it.
        if is_asrs:
            parts.append(box(f"asrs_dock_{i:02d}_post", px, py,
                             STATION_POST_H / 2, STATION_POST_W, STATION_POST_W,
                             STATION_POST_H, (0.95, 0.75, 0.15, 1), solid=False))

    # --------------------------------------------------- coater spurs
    #
    # Each coater owns one spur, so paint them in the coater's own colour rather
    # than generic lane grey. A spur that belongs to a machine is a different
    # object from a through-lane, and the routing will have to treat it so.
    for i, (sy0, sy1, _side) in enumerate(P.COATER_SPUR, 1):
        parts.append(rect(f"spur_CTR{i}", P.COATER_SPUR_X[0], sy0,
                          P.COATER_SPUR_X[1], sy1,
                          PAINT_Z + PAINT_T, PAINT_T,
                          ROAD_RGBA, solid=False))

    # -------------------------------------------- spur-to-station links
    #
    # One per station, hugging its east edge, running to the spur. ALL EIGHT ARE
    # DERIVED from the project lead's sketch — none is in the drawing — so all
    # eight are drawn at reduced opacity. Nothing here should read as measured.
    for x0, y0, x1, y1, ci, kind in P.coater_connectors():
        parts.append(rect(f"link_CTR{ci}_{kind}", x0, y0, x1, y1,
                          PAINT_Z + PAINT_T, PAINT_T,
                          ROAD_RGBA, solid=False))

    # ------------------------------------------------- coater LD / ULD
    #
    # The first stations in this world that are NAMED rather than merely
    # measured. The deck [S16] says Coater LD 4EA and Coater ULD 4EA; block
    # `zw$4E78` puts LD at x 125.58 and ULD at x 136.58, both at the same y —
    # they differ in x, not y.
    #
    # Drawn as a pad plus a post so they read as stations from across a 300 m
    # hall, where a flat pad is invisible. The post is VISUAL ONLY: a station is
    # a place to stand, not an obstacle.
    LD_RGBA = (0.15, 0.75, 0.30, 1)
    ULD_RGBA = (0.95, 0.55, 0.10, 1)
    for i, sy in enumerate(P.COATER_STATION_Y):
        for kind, sx, rgba in (("ld", P.COATER_LD_X, LD_RGBA),
                               ("uld", P.COATER_ULD_X, ULD_RGBA)):
            # The two symbols of one station, facing each other across it.
            for j, dy in ((0, -P.COATER_STATION_PAIR / 2),
                          (1, +P.COATER_STATION_PAIR / 2)):
                parts.append(box(f"ctr{i+1}_{kind}_{j}", sx, sy + dy,
                                 PAINT_Z + PAINT_T / 2, l, w, PAINT_T,
                                 rgba, 0.0, solid=False))
            parts.append(box(f"ctr{i+1}_{kind}_post", sx, sy,
                             STATION_POST_H / 2, STATION_POST_W, STATION_POST_W,
                             STATION_POST_H, rgba, solid=False))

    # CTR4's ULD is inferred, not measured — drawn hollow-pale so the world does
    # not present a guess with the same confidence as a measurement.
    for i, measured in enumerate(P.COATER_ULD_MEASURED):
        if not measured:
            parts.append(box(f"ctr{i+1}_uld_inferred", P.COATER_ULD_X,
                             P.COATER_STATION_Y[i], 2.8,
                             0.9, 0.9, 0.9, (0.95, 0.55, 0.10, 0.35), solid=False))

    # -------------------------------------------------- gravure stations
    #
    # The four bodies are drawn in the machine loop above, from the same measured
    # extents as every other machine. ALL FOUR now carry LD and ULD — the deck
    # [S16] counts four of each, and each pair sits on its own body's centreline at
    # the two ends, LD south and ULD north. Nothing is copied from GRV1; see
    # plant_cad.gravure_stations() for why this is not the retracted derivation.
    #
    # A label post per machine, because a 6.9 x 17.1 m body 100 m from the camera
    # is a smudge without one.
    for name, gx0, gy0, gx1, gy1 in P.gravure_bodies():
        parts.append(box(f"m_{name}_label", (gx0 + gx1) / 2, (gy0 + gy1) / 2,
                         MACHINE_H + 2.0, 0.6, 0.6, 4.0,
                         (0.20, 0.40, 0.75, 1), solid=False))

    for name, sx, sy, kind in P.gravure_stations():
        rgba = (0.15, 0.75, 0.30, 1) if kind == "LD" else (0.95, 0.55, 0.10, 1)
        tag = f"{name.lower()}_{kind.lower()}"
        parts.append(box(tag, sx, sy, MACHINE_H + 0.05,
                         P.STATION_MARKER, P.STATION_MARKER, 0.10, rgba,
                         solid=False))
        parts.append(box(f"{tag}_post", sx, sy,
                         MACHINE_H + STATION_POST_H / 2,
                         STATION_POST_W, STATION_POST_W, STATION_POST_H,
                         rgba, solid=False))

    # THE GRAVURE ROAD STRUCTURE: a cross-road in each gap joining the two
    # north-south roads, and a short spur off it to each station facing that gap.
    # See plant_cad's gravure_cross_roads() for why it cannot be a road beside the
    # station the way the coater's is — the body fills its corridor.
    #
    # Both derived from the project lead's description, so both at reduced opacity,
    # same as the coater's eight.
    for name, x0, y0, x1, y1, _serves in P.gravure_cross_roads():
        parts.append(rect(f"grv_{name}", x0, y0, x1, y1,
                          PAINT_Z + PAINT_T, PAINT_T,
                          ROAD_RGBA, solid=False))
    for name, x0, y0, x1, y1, kind in P.gravure_spurs():
        parts.append(rect(f"spur_{name}_{kind.lower()}", x0, y0, x1, y1,
                          PAINT_Z + PAINT_T * 2, PAINT_T,
                          ROAD_RGBA, solid=False))

    # ------------------------------------------------------- WIP racks
    #
    # Access points, not slots — see plant_cad.WIP_ACCESS_X. Drawn as pads on
    # the two columns, one per position, in a colour of their own so they are
    # never mistaken for a machine station.
    WIP_RGBA = (0.55, 0.35, 0.75, 1)
    for gi, (ya, yb) in enumerate(P.WIP_GROUP_Y if full else (), 1):
        for ci, wx in enumerate(P.WIP_ACCESS_X, 1):
            for pi, wy in enumerate((ya, yb), 1):
                parts.append(box(f"wip_g{gi}_c{ci}_{pi}", wx, wy,
                                 PAINT_Z + PAINT_T / 2, l, w, PAINT_T,
                                 WIP_RGBA, 0.0, solid=False))
        # One post per group, so four groups read as four racks from a distance.
        parts.append(box(f"wip_g{gi}_post", sum(P.WIP_ACCESS_X) / 2,
                         (ya + yb) / 2, STATION_POST_H / 2 * 0.7,
                         STATION_POST_W * 0.8, STATION_POST_W * 0.8,
                         STATION_POST_H * 0.7, WIP_RGBA, solid=False))

    # ------------------------------------------------------------ charging
    #
    # ONLY the one charging block actually found in the cathode cell. The old
    # four-position set is wrong — two of them sat in the anode cell, drawn as
    # blue pads on empty floor 100 m from anything we model — and is quarantined
    # in plant_cad as CHARGING_UNRECONCILED.
    #
    # The deck says five. We draw the one we can point at, and the gap between
    # one and five stays visible as a question rather than being padded out.
    cw, ch = P.CHARGING_BAY_SIZE
    for i, (bx, by) in enumerate(P.CHARGING_MEASURED if full else (), 1):
        parts.append(box(f"charge_{i}", bx, by, PAINT_Z + PAINT_T / 2,
                         cw, ch, PAINT_T, (0.25, 0.45, 0.85, 1), solid=False))
        parts.append(box(f"charge_{i}_post", bx, by, 2.5, 0.4, 0.4, 5.0,
                         (0.25, 0.45, 0.85, 1), solid=False))

    # ---------------------------------------------------------- grid posts
    #
    # A 306 m hall has no scale on screen — everything is far away and the eye
    # has nothing to measure against. A post every 50 m along the south and west
    # walls gives one, and because the world is in absolute CAD coordinates the
    # post at x=150 IS x=150 in the drawing.
    posts = 0
    gx = int(math.ceil(wx0 / 50.0) * 50) if full else wx1 + 1
    while gx <= wx1:
        parts.append(box(f"grid_x{gx}", gx, wy0 + 1.0, 1.5,
                         0.25, 0.25, 3.0, (0.15, 0.15, 0.18, 1)))
        posts += 1
        gx += 50
    gy = int(math.ceil(wy0 / 50.0) * 50) if full else wy1 + 1
    while gy <= wy1:
        parts.append(box(f"grid_y{gy}", wx0 + 1.0, gy, 1.5,
                         0.25, 0.25, 3.0, (0.15, 0.15, 0.18, 1)))
        posts += 1
        gy += 50

    # The camera looks at the middle of what is actually modelled — the machine
    # bodies — rather than the middle of the hall, half of which is the anode
    # cell we do not model and which is therefore empty floor.
    ms = P.machines()
    cx = sum((m[1] + m[3]) / 2 for m in ms) / len(ms)
    cy = sum((m[2] + m[4]) / 2 for m in ms) / len(ms)
    hdr = HDR_TEMPLATE.format(cam_x=cx - 70, cam_y=cy - 75, cam_z=95)

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "worlds", "cad_plant.world"))
    with open(out, "w") as f:
        f.write(hdr + "".join(parts) + FTR)

    print(f"wrote {out}")
    print(f"  mode      {'FULL' if full else 'MINIMAL'} — "
          f"{'machines, roads and the survey layer' if full else 'machines and roads only; --full adds the survey layer'}")
    print(f"  hall      {wx1 - wx0:.0f} x {wy1 - wy0:.0f} m, absolute CAD coordinates")
    print(f"  machines  {len(ms)} drawn (4 gravure at x "
          f"{P.GRAVURE_X[0]}..{P.GRAVURE_X[1]}, corrected 2026-08-13; "
          f"{len(P.gravure_stations())} gravure stations)")
    print(f"  lanes     {len(P.lanes_drawn())} painted "
          f"({len(P.EXCLUDED_LANES)} excluded), {len(P.JUNCTIONS)} junctions")
    if full:
        print(f"  AGV pads  {len(P.AGV_POSITIONS)} "
              f"({n_asrs} ASRS dock, {n_unnamed} unnamed at x {P.SLITTER_DOCK_X})")
        print(f"  charging  {len(P.CHARGING_MEASURED)} of "
              f"{P.CHARGING_EXPECTED_CATHODE} bays, {posts} grid posts")
    else:
        print("  omitted   walls, 45 AGV pads, 30 junctions, 8 WIP access, "
              "1 charger, grid posts")

    # The plant this world is FOR, and how much of it we can point at. Printed on
    # every build because a shortfall that only lives in a document stops being
    # read, and because the three legs are the reason any of this geometry
    # matters — see plant_cad's `flow` section.
    print("  flow      (deck [S16], cathode)")
    for line in P.flow_summary():
        print(f"              {line}")
    placed = P.stations_placed()
    short = [(k, placed.get(k, 0), v) for k, v in P.STATION_COUNTS_DECK.items()
             if placed.get(k, 0) < v]
    if short:
        print("  stations  " + ", ".join(f"{k} {h}/{w}" for k, h, w in short)
              + "  NOT located")
    print(f"  fleet     " + ", ".join(f"{k} x{v}"
                                      for k, v in P.FLEET_CATHODE.items())
          + f"  = {sum(P.FLEET_CATHODE.values())} cathode Big AGVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
