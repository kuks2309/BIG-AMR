# Gazebo world — where the source material lives

The simulated plant in `src/MES/csm/csm/plant.py` and `src/Sim/trnav_2ws_gazebo/`
is derived from customer material that **cannot be committed here**. This file
records what that material is and where to find it, so the derivation is
traceable without publishing anything.

## Why the files are not in this repository

`kuks2309/BIG-AMR` is **public**. The layout drawings and system decks are Motion
Device / CATL confidential — the covering mail states
"당사의 동의없는 자료의 사용 및 배포를 금합니다" (use and distribution without our
consent is prohibited). `.gitignore` already reserves `meeting_files/` and
`References/local/` for exactly this, per
`docs/claude_guideline/external_reference/handling.md` §5.

They are also large: the five layout drawings total **724 MB**, which git would
carry for ever.

## Working copies (gitignored, on this machine)

`References/local/gazebo-world/`

| path | source | notes |
| --- | --- | --- |
| `cad/BIG& SMALL AGV Layout V1 20260810.dwg` | NAS | 20 MB. **Dated 2026-08-10**, AGV layout specifically — smallest and most focused. Start here. |
| `cad/FM2 Front-end layout V7 20260709_0806.dwg` | NAS | 155 MB. Front-end = the Cell area we model. V7 supersedes the V5 held elsewhere. |
| `decks/system_diagram_V1.3_20260702.pptx` | `meeting_files/` | The `[S7]`/`[S16]`/`[S39]` deck cited throughout `plant.py`. |
| `decks/T-ROBOTICS_260730 ACS Simulation BigAGV AGV Capa_v1.2.pptx` | NAS | Big AGV capacity simulation, v1.2. Not yet read. |
| `extracted/slide*.png` | extracted from the deck | Layout images pulled out of the pptx; 1071x856 native, **text not legible**. |

## Origin — the NAS

Mounted over WebDAV at `~/NAS` (`https://motion-device.synology.me:11111/`).

    ~/NAS/00_Ford_Energy/14.Layout, 동선, 시뮬레이션/
        Layout/BIG& SMALL AGV Layout V1 20260810.dwg      20 MB
        Layout/FM2 Front-end layout V7 20260709_0806.dwg  155 MB
        Layout/Back-end Layout V5 20260615.dwg            203 MB
        Layout/AGV racks update 20260731.dwg               89 MB
        Layout/FM2 PACK ... 20260729.dwg                  256 MB
        시뮬레이션/Big AGV/                                 3 capacity decks
        Layout/Temp/                                       older versions V4, V5, V7

## Reading the DWG — solved 2026-08-11

No DWG reader exists for Ubuntu 22.04 (`libredwg-tools` is not packaged; GDAL's
DWG driver needs proprietary ODA libraries). **LibreDWG 0.14 was built from
source**; `dwg2dxf` works. Only `libtool` was installed system-wide.

    ./configure --prefix=... --disable-shared --enable-static --disable-python --disable-docs
    make -j$(nproc)                       # programs/dwg2dxf
    dwg2dxf -o out.dxf "BIG& SMALL AGV Layout V1 20260810.dwg"

20 MB DWG (AC1032 / AutoCAD 2018) -> 167 MB DXF. Parsed with `ezdxf` 1.4.4
(`pip install --user ezdxf`). The drawing is assembled from blocks: model space
holds only 18 INSERTs, and the relevant one is **`BIG&SMALL-AGV-TR`** at the
origin, unit scale — 324,386 entities when exploded one level.

### Scale — verified three ways

- header `$INSUNITS = 4` (millimetres), `$MEASUREMENT = 1` (metric)
- equipment blocks (`FOIL ASRS_CATHODE...`, `POWDER ASRS_ANODE...`) measure
  2–3 m, which is plausible only in mm
- symbol blocks `zw$CB5A` and `zw$FACA` are both **1.845 m** deep, matching the
  documented **1800 mm roll length** (deck slide 2, "Load Dimensions")

Not verified against an AGV footprint: the AGV symbols carry anonymous ZWCAD
block names and none measures 1300x1900 or 1600x2000 directly.

### What was extracted

`extracted/agv_positions_from_dwg.json` — **51 AGV positions in metres**, with
rotation and scale, from two layers inside `BIG&SMALL-AGV-TR`:

| layer | meaning | count |
| --- | --- | --- |
| `涂布-3.5T大AGV` | Coating / 3.5T Big AGV — amr3's leg | 40 |
| `凹版1.5T大AGV路线` | Gravure / 1.5T Big AGV route — amr1, amr2 | 11 |

Structure visible in the coordinates, e.g. at the coater:

    (145.77, 26.97) rot 0      (149.31, 26.97) rot 0
    (145.77, 31.07) rot 180    (149.31, 31.07) rot 180

Two positions **3.54 m** apart, facing pairs **4.10 m** apart — a machine served
from both sides, which is the LD/ULD pairing `plant.py` already models. Also a
row of five at x=161.95 spaced 3.54 m, and a 3x4 grid at y=243..257.

**3.54 m is the dominant pitch** (7 occurrences in the y-gaps).

### How far our world is from the drawing

| | drawing | `plant.py` |
| --- | --- | --- |
| AGV working area | **~41 m x 246 m** | 43 m x 26 m |
| adjacent AGV positions | **3.54 m** | 2.40 m (2 x PORT_OFFSET) |
| facing-pair separation | **4.10 m** | not modelled |

Width is about right; **length is ~10x too short**. The real line is long and
narrow and we built a compact box, which is very likely why our robots meet each
other constantly — a 246 m line squeezed into 26 m puts every robot in
everyone's way.

### Still open

- The 51 positions are **not named**. Blocks are anonymous (`zw$92FE`), so
  nothing says "Coater 1 ULD". Matching them to stations needs the equipment
  layers (`_COATER CATHODE`, `_COATER OVEN`, `FOIL ASRS_CATHODE`,
  `_MIXING EQ_CATHODE`) — present in the file but **not reachable from
  `BIG&SMALL-AGV-TR` at depth 1 or 2**; they live in other blocks.
- Layers named `...路线` ("route") hold AGV **artwork**, not centrelines:
  `新松AGV3.5t大AGV路线` has 91,732 segments totalling only 656 m, none longer
  than 0.83 m, in a different area (x 235–367 m). The lane centrelines have not
  been located.
- `plant.py` assumptions **A1–A6** therefore remain invented for aisle
  positions and hall extent, though the position data above now constrains them.

## Opening the drawings — solved 2026-08-11

`Tools/cad_view/open_cad.sh` opens the trimmed cell in LibreCAD. Two traps it
works around, both of which look like a broken install and are not:

**LibreCAD cannot read our DWGs.** It opens an AC1032 (AutoCAD 2018) file to an
EMPTY document — no error, no drawing, a blank sheet. The tell is memory: it
settles at ~130 MB with nothing loaded, against ~250 MB when geometry is really
there. Convert with `dwg2dxf` first.

**A terminal inside the VS Code snap kills it.** The snap exports `LOCPATH`,
`GTK_PATH` and friends pointing into `/snap/code/<rev>/`; LibreCAD is a system
binary and picks up snap's glibc, dying with

    symbol lookup error: /snap/core20/.../libpthread.so.0:
    undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE

`env -i` fixes it. The same binary launched from the GNOME app menu is fine.

### The trimmed cell

`Tools/cad_view/trim_dxf.py` flattens the block tree once and keeps only the
entities inside x 100..235 m, y 155..295 m — the area `cad_plant.world` covers:

| | full drawing | trimmed |
| --- | --- | --- |
| size | 167 MB | 57 MB |
| entities | 2,181,327 scanned | 310,113 kept, 19 layers |
| viewer | resolves the whole block tree | flat model space |

Two defects in the first write were invisible until a human opened it, and are
worth remembering for anything else we export:

* **no layer colours** — LibreCAD drew black entities on a black canvas
* **no `$EXTMIN`/`$EXTMAX`** — the viewer opened at the origin, 100 m from the
  nearest line, so the drawing was loaded and off screen

Both are set now. If a drawing still looks empty, try **View -> Auto zoom**
before believing it.

## Opening the WORLD — solved 2026-08-13

`src/Sim/trnav_2ws_gazebo/scripts/view_cad_world.sh` opens `cad_plant.world`. Four
traps, all of which present as "Gazebo is broken":

* **`gzserver` is headless.** It loads the world, publishes state, and draws
  nothing. It reports success the whole time. Use `gazebo` (server + client).
* **The snap environment kills it** — the same `LOCPATH` / `GTK_PATH` trap as
  LibreCAD above, same `env -i` fix.
* **~40 s to load** 274 static models over 305 × 209 m. Look earlier and the
  scene is empty grey, which looks identical to a failure.
* **The window can open on the other monitor.** X reports the primary here as
  `XWAYLAND1` at offset **+1920**, so the window lands near +1990 — the
  right-hand screen. `xrandr --listmonitors` gives the offsets.

### `/gazebo/model_states` truncates — do not use it to verify the world

It reports **127 of 274 models** and stops mid-way through the AGV pads, at the
same boundary on every launch. That is indistinguishable from a world that failed
to finish loading, and it was read as one before being checked.

The world is complete. Gazebo's own API proves it, and it is the tool to use:

    gz model -m m_GRV1 -p              # 184.04 182.315 1.5   = GRAVURE1_BODY centre
    gz model -m asrs_dock_19_post -p   # 151.85 219.43 3.5    = the ASRS dock
    gz model -m grid_y250 -p           # 31.17 250 1.5        = HALL_X[0] + 1

A reproducible truncation at a fixed index is a message limit, not a load
failure — a stall would land somewhere different each time. Worth remembering
for any future world of this size: the count from `model_states` is a floor.

## What IS documented, and what we contradict

From the system deck, slide 2 "1.1 AGV model" — verified by reading the slide
XML directly:

| model | documented size | simulated | gap |
| --- | --- | --- | --- |
| 1.5T-Big AGV A/B (amr1, amr2) | **W1,300 x L1,900 mm** | 900 x 1600 | 400 mm too narrow |
| 3.5T-Big AGV (amr3) | **W1,600 x L2,000 mm** | 900 x 1600 | 700 mm too narrow |

Documented speed is **0.5 m/s** for Big AGVs (slide 15); we run `max_speed 0.6`.

We also model all three robots as identical when the deck specifies two distinct
machines differing in size, weight (1,100 / 1,300 / 1,600 kg), payload and
pass-line height.

A spacing audit against the real bodies found the current world **does** carry
them — LD/ULD pairs clear by 0.80-1.10 m, two robots pass in a 5.0 m aisle with
2.10 m spare — with one exception: the slitter ports at 2.0 m pitch leave
**0.40 m** between docked 3.5T bodies.
