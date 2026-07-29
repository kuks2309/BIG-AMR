#!/usr/bin/env bash
# start_sim.sh - bring up the whole Foil_A082 simulation with one command.
#
# Opens a separate labelled terminal window for each piece and starts them in
# dependency order, each waiting for the one before it. Nothing needs manual
# sequencing.
#
#   1. Gazebo        gzserver + gzclient, robot spawned, controllers active
#   2. Control panel PyQt5 teleop GUI (waits for /joint_states)
#
# usage:
#   ./start_sim.sh                 normal
#   ./start_sim.sh --lag 0.8       simulate a slow steering servo (tau seconds)
#   ./start_sim.sh --no-gui        skip the control panel
#   ./start_sim.sh --headless      no Gazebo window either (CI / remote)
#   ./start_sim.sh --help
#
# Stop everything with:  ./stop_sim.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

LAG="0.0"; WANT_GUI=1; GZ_GUI="true"

while [ $# -gt 0 ]; do
    case "$1" in
        --lag)      LAG="${2:-0.8}"; shift 2 ;;
        --no-gui)   WANT_GUI=0; shift ;;
        --headless) GZ_GUI="false"; shift ;;
        -h|--help)  sed -n '2,/^set -u/{/^set -u/d;p}' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "unknown option: $1   (see --help)"; exit 2 ;;
    esac
done

# ---- preflight ----
command -v gnome-terminal >/dev/null || {
    echo "gnome-terminal not found — this launcher needs GNOME Terminal."; exit 1; }

if [ ! -f "$WS/install/setup.bash" ]; then
    echo "install/ not found under $WS"
    echo "build first:"
    echo "  cd $WS && colcon build --packages-select trnav_2ws_description trnav_2ws_gazebo"
    exit 1
fi

# A stale gzserver holds port 11345 and the next launch dies with
# "bind: Address already in use", so clear any leftovers first.
if pgrep -f 'gzserver|gzclient' >/dev/null 2>&1; then
    echo "[start_sim] clearing leftover Gazebo processes..."
    bash "$SCRIPT_DIR/stop_sim.sh" >/dev/null 2>&1
fi

# Track the shell PID of every window we open so stop_sim.sh closes exactly
# these and not the user's own terminals.
PIDFILE="/tmp/trnav_2ws_sim_windows.pids"
: > "$PIDFILE"

SRC="source /opt/ros/humble/setup.bash; source '$WS/install/setup.bash'"

# Strip snap variables before spawning anything graphical. If this script is run
# from a terminal inside a snap (the VS Code snap is the usual case) those
# variables point GTK at snap's bundled core20 libraries, and gnome-terminal dies
# with "undefined symbol: __libc_pthread_init". Harmless from a normal terminal —
# the variables simply are not set.
CLEAN_ENV=(env
    -u SNAP -u SNAP_NAME -u SNAP_INSTANCE_NAME -u SNAP_REVISION -u SNAP_ARCH
    -u SNAP_COMMON -u SNAP_USER_DATA -u SNAP_USER_COMMON -u SNAP_CONTEXT
    -u GTK_PATH -u GTK_EXE_PREFIX -u LOCPATH
    -u GDK_PIXBUF_MODULE_FILE -u GDK_PIXBUF_MODULEDIR -u GSETTINGS_SCHEMA_DIR)

# Open a labelled window. The window records its own shell PID first, and keeps
# the shell alive after the command exits so a crash message stays readable.
win() {
    local title="$1" cmd="$2"
    "${CLEAN_ENV[@]}" gnome-terminal --title="$title" -- bash -c \
        "echo \$\$ >> '$PIDFILE'; printf '\033]0;%s\007' '$title'; $cmd; \
         echo; echo '[$title exited — window kept open; ./stop_sim.sh closes it]'; \
         exec bash"
}

echo "[start_sim] workspace : $WS"
echo "[start_sim] steer lag : ${LAG}s   gazebo gui: $GZ_GUI   panel: $WANT_GUI"

# ---- 1. Gazebo ----
win "Gazebo — Foil_A082" \
    "$SRC; ros2 launch trnav_2ws_gazebo sim.launch.py gui:=$GZ_GUI steer_lag:=$LAG"

# ---- 2. Control panel ----
# Waits for /joint_states, which only appears once the robot has spawned and
# joint_state_broadcaster is active — so the panel never starts against a
# half-built system.
if [ "$WANT_GUI" -eq 1 ]; then
    win "Control panel" \
        "$SRC; echo 'waiting for the robot to spawn...'; \
         until ros2 topic list 2>/dev/null | grep -q '/joint_states'; do sleep 1; done; \
         echo 'robot is up — starting control panel'; \
         bash '$SCRIPT_DIR/run_gui.sh'"
fi

echo "[start_sim] windows opened. Stop everything with:"
echo "    bash $SCRIPT_DIR/stop_sim.sh"
