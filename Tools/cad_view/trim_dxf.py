#!/usr/bin/env python3
"""Cut the cathode cell out of the 167 MB DXF into a file a viewer can open.

The full drawing is the whole hall plus the anode line plus the east yard, and
it is assembled from nested blocks — a viewer has to resolve the whole tree
before it can draw anything. This flattens the tree once, keeps only the
entities inside the area our Gazebo world covers, and writes them straight into
model space.

Output is in MILLIMETRES, the drawing's own units, so coordinates read in the
viewer are 1000x the metres in plant_cad.py.
"""
import ezdxf
from ezdxf.math import Matrix44

SRC = "BIG_SMALL_AGV_Layout_V1_20260810.dxf"
OUT = "cathode_cell_trimmed.dxf"

# The area cad_plant.world covers, in drawing units (mm), with a margin.
X0, Y0, X1, Y1 = 100_000, 155_000, 235_000, 295_000

print("reading", SRC, "...")
src = ezdxf.readfile(SRC)
out = ezdxf.new(dxfversion="R2010")
msp = out.modelspace()

layers = set()
kept = 0
seen = 0


def inside(x, y):
    return X0 <= x <= X1 and Y0 <= y <= Y1


def points_of(e):
    """Representative points, in the entity's own coordinates."""
    t = e.dxftype()
    try:
        if t == "LINE":
            return [e.dxf.start, e.dxf.end]
        if t == "LWPOLYLINE":
            return [(p[0], p[1], 0) for p in e.get_points()]
        if t == "POLYLINE":
            return [v.dxf.location for v in e.vertices]
        if t in ("CIRCLE", "ARC"):
            return [e.dxf.center]
        if t in ("TEXT", "MTEXT"):
            return [e.dxf.insert]
        if t == "SOLID":
            return [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2]
        if t == "POINT":
            return [e.dxf.location]
        if t == "ELLIPSE":
            return [e.dxf.center]
    except Exception:
        pass
    return []


def emit(e, m):
    """Copy one entity into the output, transformed into world coordinates."""
    global kept
    t = e.dxftype()
    lay = e.dxf.layer if e.dxf.hasattr("layer") else "0"
    try:
        if t == "LINE":
            a, b = m.transform(e.dxf.start), m.transform(e.dxf.end)
            msp.add_line((a.x, a.y), (b.x, b.y), dxfattribs={"layer": lay})
        elif t == "LWPOLYLINE":
            pts = [m.transform((p[0], p[1], 0)) for p in e.get_points()]
            msp.add_lwpolyline([(p.x, p.y) for p in pts],
                               close=bool(e.closed), dxfattribs={"layer": lay})
        elif t == "POLYLINE":
            pts = [m.transform(v.dxf.location) for v in e.vertices]
            if len(pts) >= 2:
                msp.add_lwpolyline([(p.x, p.y) for p in pts],
                                   dxfattribs={"layer": lay})
        elif t in ("CIRCLE", "ARC"):
            c = m.transform(e.dxf.center)
            if t == "CIRCLE":
                msp.add_circle((c.x, c.y), e.dxf.radius, dxfattribs={"layer": lay})
            else:
                msp.add_arc((c.x, c.y), e.dxf.radius, e.dxf.start_angle,
                            e.dxf.end_angle, dxfattribs={"layer": lay})
        elif t in ("TEXT", "MTEXT"):
            p = m.transform(e.dxf.insert)
            txt = e.dxf.text if t == "TEXT" else e.text
            h = e.dxf.height if e.dxf.hasattr("height") else 1000
            msp.add_text(str(txt)[:250], height=h,
                         dxfattribs={"layer": lay}).set_placement((p.x, p.y))
        elif t == "SOLID":
            v = [m.transform(getattr(e.dxf, f"vtx{i}")) for i in range(3)]
            msp.add_lwpolyline([(q.x, q.y) for q in v], close=True,
                               dxfattribs={"layer": lay})
        else:
            return
        layers.add(lay)
        kept += 1
    except Exception:
        pass


def walk(entities, m, depth=0):
    global seen
    for e in entities:
        seen += 1
        if seen % 500_000 == 0:
            print(f"  scanned {seen:,}  kept {kept:,}")
        if e.dxftype() == "INSERT":
            if depth >= 4:
                continue
            try:
                blk = src.blocks[e.dxf.name]
            except Exception:
                continue
            walk(blk, e.matrix44() @ m, depth + 1)
        else:
            pts = points_of(e)
            if not pts:
                continue
            for p in pts:
                q = m.transform((p[0], p[1], 0))
                if inside(q.x, q.y):
                    emit(e, m)
                    break


roots = [e for e in src.modelspace() if e.dxftype() == "INSERT"]
print("root inserts:", len(roots))
for r in roots:
    # Some root INSERTs carry an empty block name — a stale reference in the
    # converted file. Skipping them is safe; they have no geometry to skip.
    try:
        blk = src.blocks[r.dxf.name]
    except Exception:
        print("  skipped INSERT with unresolvable block name", repr(r.dxf.name))
        continue
    walk(blk, r.matrix44())

for lay in sorted(layers):
    if lay not in out.layers:
        try:
            out.layers.add(lay)
        except Exception:
            pass

out.saveas(OUT)
print(f"\nscanned {seen:,} entities, kept {kept:,} in {len(layers)} layers")
print("wrote", OUT)
