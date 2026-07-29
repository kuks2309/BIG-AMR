#!/usr/bin/env bash
# run_gui.sh - launch the teleop control panel with a sanitized environment.
#
# Why the env scrubbing: if this is started from a terminal that lives inside a
# snap (the VS Code snap is the usual case - it exports SNAP, GTK_PATH,
# GDK_PIXBUF_MODULEDIR and friends), those variables point Qt and GTK at the
# snap's bundled core20 libraries. Loading core20's glibc alongside the system
# glibc fails with:
#
#   python3: symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/
#   libpthread.so.0: undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
#
# Unsetting them makes the app resolve the system libraries instead. Harmless
# when launched from a normal terminal - the variables simply are not set.
# Note: no `set -u` here. ROS's setup.bash reads unset variables such as
# AMENT_TRACE_SETUP_FILES and aborts under `set -u`.
set -e

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

if [ ! -f "$WS/install/setup.bash" ]; then
    echo "install/ not found under $WS - build first:"
    echo "  cd $WS && colcon build --packages-select trnav_2ws_description trnav_2ws_gazebo"
    exit 1
fi

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "$WS/install/setup.bash"

exec env \
    -u SNAP -u SNAP_NAME -u SNAP_INSTANCE_NAME -u SNAP_REVISION -u SNAP_ARCH \
    -u SNAP_COMMON -u SNAP_USER_DATA -u SNAP_USER_COMMON -u SNAP_CONTEXT \
    -u GTK_PATH -u GTK_EXE_PREFIX -u LOCPATH \
    -u GDK_PIXBUF_MODULE_FILE -u GDK_PIXBUF_MODULEDIR -u GSETTINGS_SCHEMA_DIR \
    python3 "$WS/install/trnav_2ws_gazebo/lib/trnav_2ws_gazebo/teleop_gui.py" "$@"
