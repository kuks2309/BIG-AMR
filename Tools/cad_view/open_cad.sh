#!/usr/bin/env bash
# open_cad.sh — open a customer drawing in LibreCAD, from anywhere.
#
#   Tools/cad_view/open_cad.sh                 # the trimmed cathode cell
#   Tools/cad_view/open_cad.sh <file.dxf>      # any DXF
#
# TWO THINGS MAKE THIS NECESSARY, AND BOTH ARE NON-OBVIOUS.
#
# 1. THE ENVIRONMENT HAS TO BE STRIPPED.
#    If your terminal is the one inside the VS Code *snap*, it exports
#    LOCPATH, GTK_PATH and friends pointing into /snap/code/<rev>/. LibreCAD is
#    a system binary; it picks up snap's glibc and dies immediately with
#
#        symbol lookup error: /snap/core20/.../libpthread.so.0:
#        undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
#
#    which reads like a broken install and is not one. `env -i` fixes it. The
#    same LibreCAD launched from the GNOME app menu works fine, because that
#    environment was never inside the snap.
#
# 2. USE THE DXF, NOT THE DWG.
#    LibreCAD 2.1 opens our AC1032 (AutoCAD 2018) DWGs to an EMPTY document —
#    no error, no drawing, just a blank sheet. The tell is memory: it settles at
#    ~130 MB with nothing loaded, against ~270 MB when geometry is really there.
#    Convert with LibreDWG's dwg2dxf first (see docs/gazebo_world/sources.md).
set -euo pipefail

# The ORIGIN-ANCHORED copy by default. The absolute-coordinate file is correct
# for measuring against plant_cad.py, but every viewer we have opens at 0,0 and
# the drawing lives 100 m away, so it comes up as a blank black canvas and looks
# broken. This one lands under the cursor. To read true CAD coordinates off it,
# add (42.22, 166.36) m — or open cathode_cell_trimmed.dxf and use View -> Auto
# zoom.
EXTRACT="$HOME/Desktop/BIG-AMR/References/local/gazebo-world/extracted"
DEFAULT="$EXTRACT/cathode_cell_at_origin.dxf"
FILE="${1:-$DEFAULT}"

if [[ ! -f "$FILE" ]]; then
    echo "no such file: $FILE" >&2
    echo >&2
    echo "The drawings are gitignored — they are customer confidential and this" >&2
    echo "repository is public. See docs/gazebo_world/sources.md for where they" >&2
    echo "live and how the trimmed DXF is produced." >&2
    exit 1
fi

case "$FILE" in
    *.dwg|*.DWG)
        echo "WARNING: $FILE is a DWG." >&2
        echo "LibreCAD opens our DWGs to a blank document. Convert to DXF first." >&2
        ;;
esac

echo "opening $(basename "$FILE") ($(du -h "$FILE" | cut -f1))"
echo "give it ~30 s for a large file; the window is blank until it finishes."
case "$FILE" in
    *at_origin*) echo "coordinates are SHIFTED — add (42.22, 166.36) m for true CAD" ;;
    *trimmed*)   echo "absolute CAD coordinates — press View -> Auto zoom to find the drawing" ;;
esac

exec env -i \
    HOME="$HOME" \
    DISPLAY="${DISPLAY:-:0}" \
    XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
    PATH=/usr/bin:/bin \
    librecad "$FILE"
