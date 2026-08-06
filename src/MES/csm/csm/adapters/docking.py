"""docking — the last few metres, ported from the docking project.

SOURCE: ~/Desktop/docking_gui_dist, written for this robot.
    src/Sim/amr_qd_sim/scripts/dock_approach.py   the controller
    docs/HOW_IT_WORKS.md  §7 crab 2-PD, §8 servo lag / settle-then-drive

WHY THE LANE NETWORK STOPS SHORT. Lanes navigate by MAP POSITION, and a machine's
true position has tolerance the map does not know. So the network only takes the
robot to an approach point a couple of metres out; from there docking closes the
loop on a MARKER fixed to the machine face — a QR/ArUco square the robot watches.
Everything below is expressed relative to that marker, never to the map, which is
what makes the final gap repeatable.

THE TWO IDEAS WORTH KEEPING, both learned the hard way in that project:

1. SETTLE-THEN-DRIVE. The steering servos take ~0.8 s to reach a commanded angle.
   A controller that issues a new angle 30 times a second never lets them arrive:
   the wheels judder, chasing targets that keep moving. So steering is commanded
   FIRST at zero speed, and driving only begins once the joints have actually
   got there. Our simulation has been hiding this by defaulting steer_lag to 0.

2. CRAB 2-PD. Two errors, two proportional gains, pure translation — both wheels
   to the same angle and the same speed, so the body slides without rotating:

       v_along = Kp_dist * (range - target)     close the gap
       v_side  = Kp_lat  * cte                  centre on the marker

   combined, capped, and turned into ONE steering angle and ONE speed.

GENERALISED FOR ANY DOCK ORIENTATION. The original assumes the dock lies along
body +y, because its camera faces the robot's left. Here the approach axis is
given per observation, so a machine on either side of an aisle works with the
same algebra. With axis = +90 deg this reduces exactly to the original.

This module is deliberately free of ROS and of Gazebo: it is arithmetic over an
observation, so it can be tested without a simulator, and the same controller can
later be driven by a real camera instead of simulated ground truth.
"""

import math

# Tuned in the source project; keep the numbers together with what they mean.
D_TARGET = 0.45         # range at which the robot is docked, metres
D_MIN = 0.28            # closer than this is an over-approach fault
KP_DIST = 0.15          # gain on the gap
KP_LAT = 0.5            # gain on the lateral offset
V_MAX = 0.10            # cap on the COMBINED speed, m/s
TOL_D = 0.03            # gap tolerance for "docked"
TOL_LAT = 0.02          # lateral tolerance for "docked"
CONV_N = 3              # consecutive in-tolerance cycles before declaring docked
OBS_STALE = 0.5         # an observation older than this is no observation
TIMEOUT = 60.0          # a dock that takes longer than this has failed
SETTLE_TOL_DEG = 4.0    # steering counts as settled within this
SETTLE_TIMEOUT = 14.0   # ... or after this long, whichever comes first

#: A single range sample that jumps more than this is noise, not motion. Lidar
#: line-fitting at close range has few points and spits out occasional wild
#: values; in the source project those single samples tripped the over-approach
#: guard and stopped docking early. A real approach moves ~0.002 m per sample.
JUMP_REJECT = 0.10
LOWPASS = 0.85          # heavy, for the same reason


class Observation:
    """What the robot sees of the marker, in its own body frame.

    :param range_m: distance to the marker along the approach axis
    :param cte:     lateral offset of the marker from the approach axis;
                    positive means the marker is to the +90 deg side of it
    :param axis:    direction of the approach in the BODY frame, radians.
                    The original project is the axis = pi/2 case.
    :param stamp:   when this was observed, seconds
    """

    def __init__(self, range_m, cte, axis, stamp):
        self.range_m = range_m
        self.cte = cte
        self.axis = axis
        self.stamp = stamp


class Result:
    """Outcome of one controller step."""

    RUNNING = "running"
    DOCKED = "docked"
    FAILED = "failed"


class DockController:
    """Crab 2-PD approach with settle-then-drive and the source project's guards.

    Pure logic: step() takes an observation and the measured steering angles and
    returns what to command. It never talks to ROS.
    """

    def __init__(self, target=D_TARGET, d_min=D_MIN, kp_dist=KP_DIST,
                 kp_lat=KP_LAT, v_max=V_MAX, tol_d=TOL_D, tol_lat=TOL_LAT,
                 conv_n=CONV_N, obs_stale=OBS_STALE, timeout=TIMEOUT):
        self.target = target
        self.d_min = d_min
        self.kp_dist = kp_dist
        self.kp_lat = kp_lat
        self.v_max = v_max
        self.tol_d = tol_d
        self.tol_lat = tol_lat
        self.conv_n = conv_n
        self.obs_stale = obs_stale
        self.timeout = timeout
        self.reset()

    def reset(self, now=0.0):
        self.phase = "settle"
        self.t_start = now
        self.t_phase = now
        self.conv_count = 0
        self.near_count = 0
        self.last_steer = 0.0
        # Reset the filter on every start. Leaving a stale estimate behind made
        # the source project declare "docked" immediately on the next attempt,
        # and the robot simply never moved.
        self.d_filt = None
        self.reason = None

    # ------------------------------------------------------------------ step

    def step(self, obs, steer_actual, now):
        """One control cycle.

        :param obs:          Observation, or None if the marker is not seen
        :param steer_actual: measured steering joint angles, radians
        :param now:          seconds
        :returns: (speed, steer, status) — status is a Result constant
        """
        if now - self.t_start > self.timeout:
            return self._fail("timeout")

        # MARKER LOST. Stop. Never hunt for it by turning — in the source
        # project that only pushed the marker further out of view.
        if obs is None or now - obs.stamp > self.obs_stale:
            return self._fail("marker lost")

        # SETTLE: command the steering, drive nothing, until the wheels arrive.
        if self.phase == "settle":
            steer = self._steer_for(obs.range_m, obs.cte, obs.axis)
            self.last_steer = steer
            err = max(abs(_wrap(a - steer)) for a in steer_actual) \
                if steer_actual else 0.0
            if (math.degrees(err) < SETTLE_TOL_DEG
                    or now - self.t_phase > SETTLE_TIMEOUT):
                self.phase = "run"
            return 0.0, steer, Result.RUNNING

        d = self._filter(obs.range_m)

        # OVER-APPROACH, debounced. A single bad sample must not stop a dock.
        if d < self.d_min:
            self.near_count += 1
            if self.near_count >= 5:
                return self._fail(f"over-approach (range {d:.3f} < {self.d_min})")
        else:
            self.near_count = 0

        e_d = d - self.target
        if abs(e_d) <= self.tol_d and abs(obs.cte) <= self.tol_lat:
            self.conv_count += 1
            if self.conv_count >= self.conv_n:
                self.reason = f"docked at {d:.3f} m, offset {obs.cte:+.3f} m"
                return 0.0, self.last_steer, Result.DOCKED
        else:
            self.conv_count = 0

        speed, steer = self._command(e_d, obs.cte, obs.axis)
        self.last_steer = steer
        return speed, steer, Result.RUNNING

    # ------------------------------------------------------------- internals

    def _command(self, e_d, cte, axis):
        """2-PD -> one steering angle and one speed. Pure translation."""
        v_along = self.kp_dist * e_d
        v_side = self.kp_lat * cte
        # Cap the COMBINED speed. Capping each axis separately lets the diagonal
        # reach sqrt(2) times the limit.
        s = math.hypot(v_along, v_side)
        if s > self.v_max:
            v_along *= self.v_max / s
            v_side *= self.v_max / s
        vx, vy = _to_body(v_along, v_side, axis)
        speed = math.hypot(vx, vy)
        steer = math.atan2(vy, vx) if speed > 1e-6 else self.last_steer
        return speed, steer

    def _steer_for(self, range_m, cte, axis):
        """The steering angle the run phase will want, for settling onto."""
        v_along = self.kp_dist * (range_m - self.target)
        v_side = self.kp_lat * cte
        vx, vy = _to_body(v_along, v_side, axis)
        return math.atan2(vy, vx) if math.hypot(vx, vy) > 1e-6 else axis

    def _filter(self, raw):
        if self.d_filt is None:
            self.d_filt = raw
            return raw
        if abs(raw - self.d_filt) > JUMP_REJECT:
            return self.d_filt                  # single wild sample: ignore it
        self.d_filt = LOWPASS * self.d_filt + (1.0 - LOWPASS) * raw
        return self.d_filt

    def _fail(self, reason):
        self.reason = reason
        return 0.0, self.last_steer, Result.FAILED


def _to_body(v_along, v_side, axis):
    """Rotate (along, side) on the approach axis into body (x, y).

    The side axis is 90 deg CLOCKWISE of the approach axis, not anticlockwise.
    That is what makes axis = pi/2 reduce to the source project exactly:
    along -> body +y, side -> body +x, which is its camera-on-the-left frame.
    """
    ca, sa = math.cos(axis), math.sin(axis)
    return v_along * ca + v_side * sa, v_along * sa - v_side * ca


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


#: Where the docking cameras look, in the body frame. The source project mounts
#: a RealSense on each side (d435_left / d435_right launch files), and the robot
#: crabs sideways into the dock — so the marker is off to one side, never ahead.
#: A machine on the robot's right is seen by the right camera and vice versa.
CAMERA_YAWS = (math.pi / 2, -math.pi / 2)


def observe(robot_pose, marker_pose, max_range=6.0, half_fov=math.radians(55.0),
            camera_yaws=CAMERA_YAWS):
    """Build an Observation from ground truth — the simulator's stand-in camera.

    A real camera sees the marker or it does not, so the same limits apply here:
    beyond max_range, or outside the field of view, the marker is NOT seen and
    this returns None. Docking then stops rather than guessing, which is the
    behaviour the source project insists on.

    :param robot_pose:  (x, y, yaw) in the world
    :param marker_pose: (x, y, yaw) of the marker; yaw is its OUTWARD normal
    """
    rx, ry, ryaw = robot_pose
    mx, my, myaw = marker_pose

    dx, dy = mx - rx, my - ry
    if math.hypot(dx, dy) > max_range:
        return None

    # Marker position in the body frame.
    c, s = math.cos(-ryaw), math.sin(-ryaw)
    bx, by = dx * c - dy * s, dx * s + dy * c

    # The approach axis in the body frame: straight at the marker face, i.e.
    # opposite its outward normal.
    axis = _wrap(myaw + math.pi - ryaw)

    # Range along the axis, lateral offset across it — on the same side axis
    # the controller steers with (90 deg clockwise of the approach).
    ca, sa = math.cos(axis), math.sin(axis)
    range_m = bx * ca + by * sa
    cte = bx * sa - by * ca

    # Facing away, or outside every lens: not seen. Reporting "not seen" rather
    # than a guess is what makes the controller stop instead of hunting.
    if range_m <= 0.0:
        return None
    bearing = math.atan2(by, bx)
    if not any(abs(_wrap(bearing - cam)) <= half_fov for cam in camera_yaws):
        return None
    return Observation(range_m, cte, axis, 0.0)
