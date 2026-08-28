#!/usr/bin/env bash
# Run the two-lane fleet sim. Kills any previous run of MINE first.
#   ./run_sim.sh            5 robots, no road overlay
#   ./run_sim.sh 3          3 robots
#   ./run_sim.sh 5 roads    paint the road graph into the world
#
# THE ROAD OVERLAY IS OFF BY DEFAULT. It is 119 nodes and 304 edges of extra
# visual geometry for gzclient to draw every frame, and the dashboard at
# :8080 now draws the same graph for free. Keep the flag: painting it into
# the world is still the only way to see the lanes against the real bodies.
# NOT `set -u`: /opt/ros/humble/setup.bash reads unbound variables
# (AMENT_TRACE_SETUP_FILES) and dies under it.
set -e
set +e
cd "$(dirname "$0")"
ROBOTS="${1:-5}"
ROADS="${2:-noroads}"

# --- 1. kill the previous run BY PROCESS GROUP, never by name -------------
# (other people run their own sims on this box; pkill would take theirs too)
PG=$(ps -eo pgid,args --no-headers | grep "[f]leet\.launch" | awk '{print $1}' | head -1)
if [ -n "$PG" ]; then echo "killing previous launch, pgid=$PG"; kill -TERM -"$PG"; fi
for q in $(ps -eo pid,args --no-headers | grep "[c]ontact_meter" | awk '{print $1}'); do kill -TERM "$q" 2>/dev/null; done
python3 -c "import time; time.sleep(6)"
REM=$(ps -eo pid,args --no-headers | grep -E "[f]leet\.launch|[g]zserver|[g]zclient|[c]ontact_meter" | awk '{print $1}')
[ -n "$REM" ] && kill -KILL $REM 2>/dev/null
python3 -c "import time; time.sleep(2)"

source /opt/ros/humble/setup.bash
source install/setup.bash

# --- 2. regenerate the world from plant.py (it is GENERATED, not edited) ---
if [ "$ROADS" = "roads" ]; then
  python3 src/Sim/trnav_2ws_gazebo/scripts/generate_world.py --roads
else
  python3 src/Sim/trnav_2ws_gazebo/scripts/generate_world.py
fi

# --- 3. build (symlink-install: python is live, but the world must copy) ---
colcon build --symlink-install --packages-select csm trnav_2ws_gazebo | tail -2
source install/setup.bash

# --- 4. launch detached, so it survives this shell -------------------------
LOG="Log/fleet_$(date +%Y-%m-%d_%H%M%S).log"
setsid nohup ros2 launch trnav_2ws_gazebo fleet.launch.py robots:="$ROBOTS" \
  > "$LOG" 2>&1 < /dev/null &
disown
echo "launched  -> $LOG"
echo "dashboard -> http://localhost:8080"

# --- 5. wait for spawn, then start the independent contact meter ----------
python3 -c "import time; time.sleep(115)"
echo "--- process census (want 1 launch / 1 gzserver / 1 gzclient / 1 sim_node) ---"
ps -eo pid,pgid,args --no-headers \
  | grep -E "[f]leet\.launch|[g]zserver|[g]zclient|[s]im_node" | cut -c1-80

CL="Log/contact_$(date +%Y-%m-%d_%H%M%S).log"
setsid nohup python3 -u Tools/contact_meter/contact_meter.py \
  --interval 0.2 --report 300 --out "$CL" > /dev/null 2>&1 < /dev/null &
disown
echo "contact meter -> $CL   (this is the arbiter, not the CSM's own view)"
