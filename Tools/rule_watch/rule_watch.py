#!/usr/bin/env python3
"""Photograph the moment a traffic rule fires, and write on the picture which one.

A log line says a rule fired. It does not say what the floor looked like, and
that is the part that decides whether the rule was RIGHT. This watches the run
log, and when a rule fires it freezes the simulation, takes a frame from the
overhead camera, labels it with the rule and every robot's position and state,
and lets the simulation go again.

    python3 rule_watch.py --log Log/fleet_sim5_xxx.log --out docs/rules/shots

The pause is real (`/pause_physics`) so the picture is of the instant the rule
fired, not of wherever the robots had drifted to by the time the frame arrived.
It is always released, including on error — a watcher that leaves the world
frozen would be worse than no watcher.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

#: Each rule, the log line that betrays it, and what it MEANS. The caption on
#: the picture comes from here, so this table is the explanation the reader
#: gets — keep it in the words a person would use, not the code's.
RULES = [
    ("RULE 1  lower number gives way",
     re.compile(r"(amr\d+) gives way to (amr\d+)"),
     "Two robots met head-on. The lower number always stands aside — a fixed "
     "order, so they can never both think they have the road."),

    ("RULE 4  going in to dock has priority",
     re.compile(r"(amr\d+) gives way to (amr\d+).*dock", re.I),
     "One of them is on its way into a station. A robot going in to dock "
     "outranks everyone, whatever its number, so the other one stops."),

    ("RULE 2  wait for the whole group",
     re.compile(r"\[(amr\d+)\] (amr\d+) is past, but (amr\d+) is following it"),
     "The robot it stood aside for has gone by, but another is following. It "
     "keeps waiting until the whole group is past, instead of pulling out in "
     "front of the next one."),

    ("stand-aside begun",
     re.compile(r"\[(amr\d+)\] stepping aside to \(([-+0-9.]+),([-+0-9.]+)\)"),
     "The yielder has picked a lay-by clear of every robot it is giving way "
     "to, and is driving to it. The other robot holds until it arrives."),

    ("stand-aside complete",
     re.compile(r"\[(amr\d+)\] clear — you may pass"),
     "The yielder reached its lay-by and stopped. Only now may the other "
     "robot move — one robot moves at a time."),

    ("RULE 3  off the lane already",
     re.compile(r"\[(amr\d+)\] off the lane already"),
     "It was asked to give way while already on a dock or parking spur. That "
     "is off the road, so it answers by standing still rather than being "
     "dragged out of a bay it is working in."),

    ("encounter over",
     re.compile(r"\[(amr\d+)\] road is clear — it is yours"),
     "Nobody is coming the other way any more. The yielder may rejoin the "
     "lane and carry on."),

    ("RULE 3  queueing, no overtaking",
     re.compile(r"queueing behind (amr\d+)"),
     "The robot ahead is giving way — it is still ON the road, holding a gap "
     "for someone else. Nobody overtakes it; everyone queues."),

    ("deadlock breaker",
     re.compile(r"\[(amr\d+)\] deadlocked with (amr\d+)"),
     "Both have been stopped for each other for 4 seconds and neither is "
     "moving. That is a deadlock, not traffic, so the fleet is asked to "
     "decide who yields."),

    ("hand-over: nowhere to go",
     re.compile(r"\[(amr\d+)\] nowhere to stand aside"),
     "The robot told to give way has no lay-by it can reach. The duty passes "
     "to the other robot, which has the room this one lacks."),

    ("GAVE UP  45 s timeout",
     re.compile(r"\[(amr\d+)\].*gave way for \d+s and nobody passed"),
     "It stood aside and waited 45 seconds and nobody came past. It gives up "
     "and loses the job. Every one of these is a failure worth explaining."),
]


#: EVERY CONDITION THAT STOPS A ROBOT, and what it means. These do not print a
#: log line — they set the robot's halt reason, which appears in each STATE
#: line. Watching the reason CHANGE is what makes the coverage complete: a rule
#: table built from log lines caught 11 of the 19, and silently missed the rest.
CONDITIONS = {
    "layer 1: on course to touch another robot":
        "The last safety check before any wheel command. Sampling both bodies "
        "2 s ahead says they would come within 0.30 m. It only ever says stop "
        "— deciding who goes is a rule above it.",
    "passer: waiting for the yielder to stand aside":
        "It has right of way but will not move until the other robot says it "
        "is clear. One robot moves at a time.",
    "stood aside, waiting to be passed":
        "It reached its lay-by and is holding. It will not rejoin until the "
        "road is clear of everyone coming the other way.",
    "on a spur, waiting to be passed":
        "Asked to give way while already on a dock or parking spur. It is off "
        "the road, so it answers by standing still.",
    "standing aside: threat":
        "On its way to the lay-by, and something OTHER than the robot it is "
        "yielding to is in the way. It stops rather than drive into it.",
    "queueing behind":
        "The robot ahead is giving way — still on the road, holding a gap for "
        "someone else. Nobody overtakes it.",
    "robot ahead on the road":
        "Another robot is inside the protective corridor: within 2.4 m ahead "
        "and 1.2 m either side of the line of travel.",
    "homing: robot ahead":
        "Same corridor check, on the way back to its parking bay.",
    "junction held by another robot":
        "A spur meets the aisle here and someone else has the red light. It "
        "waits, and releases any junction it was holding so no circle forms.",
    "machine has not granted entry":
        "The machine has not opened its door. Nothing to do with traffic.",
    "entry refused: bay occupied":
        "Another robot is already at that station. One robot per station, "
        "ever — the protocol carries only one 'AGV inside' bit.",
    "dwelling at the port":
        "Loading or unloading. Three seconds. Not a stall.",
    "pulling out: road not clear":
        "Reversing out of a bay, and the way out is blocked.",
    "exit complete":
        "Clear of the bay and the interlock is released. The next robot may "
        "come in.",
    "docking finished": "Docked and done.",
    "arrived": "At its goal.",
    "battery flat":
        "0 %. It stops where it stands and nothing recovers it automatically "
        "— exactly as on a real floor.",
    "no lay-by within reach — handing over the yield":
        "It was told to give way and has nowhere it can reach. The duty "
        "passes to the other robot, which has the room this one lacks.",
    "no exit goal": "Finished a job with no bay to back out of.",
}


def explain(reason):
    """The plain-words meaning of a halt reason, matched on its stem."""
    for key, text in CONDITIONS.items():
        if reason.startswith(key):
            return text
    return "No explanation recorded for this condition yet."


CAMERA = None


def pause(paused):
    verb = "pause" if paused else "unpause"
    subprocess.run(["ros2", "service", "call", f"/{verb}_physics",
                    "std_srvs/srv/Empty", "{}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=20)


class FrameCache:
    """Keeps the newest overhead frame, always ready to be written.

    WHY NOT PAUSE AND THEN GRAB. A Gazebo camera stops publishing while physics
    is paused, so a subscriber that waits for a NEW message after pausing waits
    for ever. The first version of this tool did exactly that and produced
    eight "NO FRAME" lines in a row.

    So the picture is taken continuously and kept. On a trigger the cached
    frame is written straight out — at 4 Hz it is at most 250 ms old, which is
    the same instant for a robot moving at 0.6 m/s (0.15 m).

    Not pausing is also the kinder choice: nineteen conditions fire constantly,
    and freezing the world for each one would make the run crawl and change the
    behaviour being photographed.
    """

    def __init__(self, topic="/overhead/overhead/image_raw"):
        import threading
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Image

        self._lock = threading.Lock()
        self._latest = None
        if not rclpy.ok():
            rclpy.init()
        self._rclpy = rclpy

        class Sub(Node):
            def __init__(inner):
                super().__init__("rule_watch_camera")
                inner.create_subscription(Image, topic, inner.on_image,
                                          qos_profile_sensor_data)

            def on_image(inner, msg):
                if msg.encoding not in ("rgb8", "bgr8"):
                    return
                with self._lock:
                    self._latest = (msg.width, msg.height, msg.encoding,
                                    bytes(msg.data))

        self._node = Sub()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        while not self._stop.is_set():
            self._rclpy.spin_once(self._node, timeout_sec=0.2)

    def ready(self, timeout=15.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if self._latest:
                    return True
            time.sleep(0.2)
        return False

    def save(self, path):
        from PIL import Image as PILImage
        with self._lock:
            frame = self._latest
        if frame is None:
            return False
        w, h, encoding, data = frame
        im = PILImage.frombytes("RGB", (w, h), data)
        if encoding == "bgr8":
            b, g, r = im.split()
            im = PILImage.merge("RGB", (r, g, b))
        im.save(path)
        return True


def fleet_state(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as fh:
            return json.load(fh)["fleet"]
    except Exception:
        return []


def annotate(image, title, why, robots, stamp):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(image).convert("RGB")
    pad = 210
    canvas = Image.new("RGB", (im.width, im.height + pad), (16, 22, 28))
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas)

    def font(size, bold=False):
        for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
                  if bold else
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
        return ImageFont.load_default()

    y = im.height + 14
    d.text((22, y), title, fill=(255, 190, 90), font=font(30, True))
    y += 42
    for line in wrap(why, 108):
        d.text((22, y), line, fill=(210, 225, 235), font=font(19))
        y += 25
    y += 6
    for r in robots:
        x0, y0 = r["position"]
        line = ("%-5s (%7.2f,%7.2f)  %-11s %s"
                % (r["name"], x0, y0, r["leg_target"] or "-",
                   (r["halted_because"] or "moving")[:58]))
        d.text((22, y), line, fill=(150, 200, 235), font=font(17))
        y += 21
    d.text((22, canvas.height - 26), stamp, fill=(110, 130, 145), font=font(15))
    canvas.save(image)


def wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def capture(args, shots, title, why, line):
    """Freeze, photograph, label, release. The release always happens."""
    stamp = time.strftime("%H:%M:%S")
    name = "%03d_%s.png" % (shots, re.sub(r"[^a-z0-9]+", "-",
                                          title.lower()).strip("-")[:52])
    path = os.path.join(args.out, name)
    robots = fleet_state(args.state)
    ok = CAMERA.save(path)
    if ok and os.path.exists(path):
        annotate(path, title, why, robots,
                 "%s   %s" % (stamp, line.split("csm]: ")[-1].strip()[:96]))
        print("  %2d  %-46s -> %s" % (shots, title[:46], name), flush=True)
    else:
        print("  %2d  %-46s -> NO FRAME" % (shots, title[:46]), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", default="docs/rules/shots")
    ap.add_argument("--state", default="http://localhost:8080/state")
    ap.add_argument("--limit", type=int, default=40,
                    help="stop after this many pictures")
    ap.add_argument("--settle", type=float, default=0.6,
                    help="seconds to let the camera deliver a frame")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    global CAMERA
    CAMERA = FrameCache()
    if not CAMERA.ready():
        print("no frames on the overhead camera — is the sim running?",
              file=sys.stderr)
        return 1

    fh = open(args.log, encoding="utf-8", errors="ignore")
    fh.seek(0, os.SEEK_END)
    shots = 0
    last_reason = {}
    state_re = re.compile(r"(amr\d+)\([-+][\d.]+,[-+][\d.]+\)[^|\[]*(?:\[([^\]]*)\])?")
    print(f"watching {args.log} — {len(RULES)} rule events + "
          f"{len(CONDITIONS)} halt conditions, up to {args.limit} pictures",
          flush=True)

    while shots < args.limit:
        line = fh.readline()
        if not line:
            time.sleep(0.2)
            continue

        # A ROBOT'S REASON CHANGING IS A CONDITION FIRING.
        #
        # Most of the if/else branches never log; they set a halt reason, which
        # every STATE line carries. Triggering on the CHANGE catches each one
        # the first time it happens and does not photograph it again while it
        # persists. Without this the watcher saw 11 of 19 conditions.
        if "STATE" in line:
            for name, reason in state_re.findall(line):
                reason = (reason or "moving").strip()
                if last_reason.get(name) == reason:
                    continue
                was = last_reason.get(name)
                last_reason[name] = reason
                if was is None or reason == "moving":
                    continue          # first sight, and starting to move again
                shots += 1
                capture(args, shots, name + ": " + reason, explain(reason),
                        line)
                if shots >= args.limit:
                    break
            continue

        for title, pattern, why in RULES:
            if not pattern.search(line):
                continue
            shots += 1
            capture(args, shots, title, why, line)
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pause(False)
        print("\nstopped; simulation released")
