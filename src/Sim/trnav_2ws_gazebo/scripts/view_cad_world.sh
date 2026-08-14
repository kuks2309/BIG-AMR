#!/usr/bin/env bash
# view_cad_world.sh — open cad_plant.world in Gazebo so a human can look at it.
#
#   scripts/view_cad_world.sh              # open the world
#   scripts/view_cad_world.sh --headless   # server only, no GUI (for audits/CI)
#   scripts/view_cad_world.sh --stop       # kill whatever this started
#
# This exists because opening this world by hand goes wrong in four ways that all
# look like "Gazebo is broken" and none of which are. Every one of them cost time
# on 2026-08-13.
#
# 1. `gzserver` IS HEADLESS. It loads the world, publishes state, and draws
#    nothing — there is no window and there never will be. You want `gazebo`
#    (server + client) or a `gzclient` alongside the server. Reaching for
#    gzserver and then wondering why the screen is empty is the single easiest
#    mistake here, because the world loads perfectly and reports success.
#
# 2. THE ENVIRONMENT HAS TO BE STRIPPED. A terminal inside the VS Code *snap*
#    exports LOCPATH, GTK_PATH and GIO_MODULE_DIR pointing into /snap/code/<rev>/.
#    Gazebo is a system binary; it picks up snap's glibc and dies with
#
#        symbol lookup error: /snap/core20/.../libpthread.so.0:
#        undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
#
#    `env -i` fixes it. Same trap, same fix as Tools/cad_view/open_cad.sh — see
#    docs/gazebo_world/sources.md, "Opening the drawings".
#
# 3. IT TAKES TIME TO LOAD. Static models spread over 305 x 209 m — ~40 s for the
#    274-model --full world, less for the default minimal one. Look too early and
#    you get an empty grey scene that is indistinguishable from a failure.
#
# 4. THE WINDOW MAY OPEN ON YOUR OTHER MONITOR. On this machine X reports the
#    primary as XWAYLAND1 at offset +1920, so Gazebo comes up at roughly +1990 —
#    on the right-hand screen, which is not the one VS Code is on. `xrandr
#    --listmonitors` tells you the offsets; the window title is "Gazebo".
#
# NOTE ON CHECKING THE WORLD FROM ROS: /gazebo/model_states TRUNCATES. On the full
# world it reported 127 of 274 models and stopped mid-way through the AGV pads,
# identically on every launch, so it looked exactly like a world that failed to
# finish loading. It was not. Verify a specific model with Gazebo's own API:
#
#     gz model -m m_GRV1 -p        # -> 176.63 182.9 1.5 0 -0 0
#
# `gz model` EXITS 0 EVEN WHEN NOTHING IS RUNNING. It prints
#
#     An instance of Gazebo is not running.
#
# and still returns success, so `until gz model ... ; do sleep; done` never waits
# and `if gz model ...` never fails. Test the OUTPUT, not the exit code:
#
#     gz model -m m_GRV1 -p | grep -qE '^[0-9-]'
#
# Getting this wrong made a dead server look like six missing models.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD="$(cd "$HERE/.." && pwd)/worlds/cad_plant.world"
ROS_SETUP="$(ls -d /opt/ros/*/setup.bash 2>/dev/null | head -1)"

# WAIT FOR THE OLD ONE TO ACTUALLY GO. Stopping and restarting inside a couple of
# seconds makes gzserver abort on startup with
#
#     gzserver: boost/smart_ptr/shared_ptr.hpp:728: Assertion `px != 0' failed.
#     [Err] [TransportIface.cc:385] Unable to read from master
#
# which looks like a corrupt world and is not: the previous master still holds port
# 11345 and the new server races it. `sleep 2` was not enough — wait for the
# processes to be gone AND the port to be free.
wait_for_stop() {
    for _ in $(seq 1 40); do
        if ! pgrep -x gzserver >/dev/null 2>&1 \
           && ! pgrep -x gzclient >/dev/null 2>&1 \
           && ! (ss -ltn 2>/dev/null | grep -q ':11345'); then
            return 0
        fi
        sleep 0.5
    done
    echo "warning: gazebo still holding port 11345 after 20 s" >&2
}

if [[ "${1:-}" == "--stop" ]]; then
    # -x, not -f: `pkill -f gzserver` also matches the shell running this script,
    # which kills the caller. That happened.
    pkill -x gzclient 2>/dev/null || true
    pkill -x gzserver 2>/dev/null || true
    wait_for_stop
    echo "stopped"
    exit 0
fi

if [[ ! -f "$WORLD" ]]; then
    echo "no world at $WORLD" >&2
    echo "generate it first:  ros2 run trnav_2ws_gazebo generate_cad_world.py" >&2
    exit 1
fi
if [[ -z "$ROS_SETUP" ]]; then
    echo "no ROS install found under /opt/ros — the world's state plugin needs it" >&2
    exit 1
fi

BIN=gazebo
[[ "${1:-}" == "--headless" ]] && BIN=gzserver

if pgrep -x gzserver >/dev/null 2>&1; then
    echo "a gzserver is already running — stop it first:  $0 --stop" >&2
    exit 1
fi

echo "opening $(basename "$WORLD") with $BIN"
N=$(grep -c '<model name=' "$WORLD" || true)
[[ "$BIN" == gazebo ]] && echo "  loading $N models; check the OTHER monitor if nothing appears"

# setsid so it survives this shell; env -i for trap 2. DISPLAY/XAUTHORITY are
# passed through explicitly because env -i drops them and the GUI needs them.
setsid env -i \
    HOME="$HOME" USER="$USER" \
    DISPLAY="${DISPLAY:-:0}" \
    XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
    PATH=/usr/local/bin:/usr/bin:/bin \
    bash -lc "source '$ROS_SETUP'; exec $BIN --verbose '$WORLD'" \
    >/tmp/cad_world_gazebo.log 2>&1 </dev/null &
disown

echo "  log: /tmp/cad_world_gazebo.log"
echo "  stop with: $0 --stop"
