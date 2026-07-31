"""seer_client — READ-ONLY client for the Seer (SRC) TCP API.

Purpose: find out what the robot actually knows, before anything tries to move
it. Chiefly the real station ids from Seer's own map — our names (station_3,
station_9) are invented, and no real AcsAdapter can be written until the true
ids are known.

⚠ THIS MODULE CANNOT MOVE THE ROBOT — BY CONSTRUCTION.

Only status APIs on port 19204 are defined here. The navigation and control
ports (19205/19206) are never opened, and no command API number appears in this
file. `_ALLOWED_PORTS` is enforced at connect time. To command the robot,
someone must deliberately write new code — it cannot happen by a typo here.

Protocol (References/Seer-Driver/seer_api_guide.md §3):

    16-byte big-endian header, then JSON

    byte  0     0x5A            sync, fixed
    byte  1     0x01            version
    bytes 2-3   uint16          sequence, echoed back in the response
    bytes 4-7   uint32          JSON length (0 when there are no parameters)
    bytes 8-9   uint16          API number
    bytes 10-15 0x00 x6         reserved, must be present

    response API number = request + 10000

Usage:

    python3 -m mini_mes.seer_client                 # defaults to 192.168.44.82
    python3 -m mini_mes.seer_client 192.168.44.82
    python3 -m mini_mes.seer_client --json          # machine-readable

The robot is reachable over WiFi only — see docs/network/seer_network_access.md.
"""

import argparse
import json
import socket
import struct
import sys

SYNC = 0x5A
VERSION = 0x01
HEADER = struct.Struct(">BBHIH6s")      # 16 bytes, network order

#: Status port only. Navigation (19206) and control (19205) are deliberately
#: absent — see the warning above.
PORT_STATUS = 19204
_ALLOWED_PORTS = frozenset({PORT_STATUS})

#: Read-only status APIs. Nothing here changes robot state.
API_INFO = 1000     # robot info, versions
API_LOCATION = 1004     # current x, y, angle
API_TASK = 1020     # task status, current site, path
API_ALARM = 1050     # active alarms and errors
API_STATIONS = 1301     # stations on the loaded map  <-- the one we came for

#: The guide recommends >=100-200 ms between requests; the robot drops
#: connections that are polled too hard.
DEFAULT_TIMEOUT = 4.0


class SeerError(RuntimeError):
    pass


class SeerStatusClient:
    """One short-lived TCP connection to Seer's status port."""

    def __init__(self, host, port=PORT_STATUS, timeout=DEFAULT_TIMEOUT):
        if port not in _ALLOWED_PORTS:
            raise SeerError(
                f"port {port} is not a status port. This client is read-only "
                f"and refuses to open control or navigation ports.")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._seq = 0

    def __enter__(self):
        self.sock = socket.create_connection((self.host, self.port),
                                             timeout=self.timeout)
        return self

    def __exit__(self, *exc):
        if self.sock:
            self.sock.close()
            self.sock = None

    # ------------------------------------------------------------ protocol

    def _recv_exactly(self, n):
        """TCP gives no framing — read until n bytes have arrived or the peer
        closes. Short reads are normal and must be looped over."""
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise SeerError(
                    f"connection closed after {len(buf)} of {n} bytes. "
                    f"A malformed header makes the robot hang up silently.")
            buf += chunk
        return buf

    def request(self, api, payload=None):
        """Send one request, return the decoded JSON reply."""
        body = b"" if payload is None else json.dumps(payload).encode()
        self._seq = (self._seq + 1) & 0xFFFF

        header = HEADER.pack(SYNC, VERSION, self._seq, len(body), api, b"\x00" * 6)
        self.sock.sendall(header + body)

        sync, ver, seq, length, rtype, _ = HEADER.unpack(self._recv_exactly(16))

        if sync != SYNC:
            raise SeerError(f"bad sync byte 0x{sync:02X}, expected 0x5A")
        if rtype == 60000:
            raise SeerError(
                f"robot answered 60000 — API {api} was sent to the wrong port. "
                f"{self.port} serves status requests only.")
        if rtype != api + 10000:
            raise SeerError(f"expected reply {api + 10000}, got {rtype}")
        if seq != self._seq:
            raise SeerError(f"sequence mismatch: sent {self._seq}, got {seq}")

        if length == 0:
            return {}
        raw = self._recv_exactly(length)
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise SeerError(f"reply was not valid JSON: {exc}") from exc

    # ------------------------------------------------- read-only convenience

    def stations(self):
        return self.request(API_STATIONS)

    def location(self):
        return self.request(API_LOCATION)

    def task(self):
        return self.request(API_TASK)

    def alarms(self):
        return self.request(API_ALARM)

    def info(self):
        return self.request(API_INFO)


# ------------------------------------------------------------------- report

def _fmt_station(st):
    """Stations come back with vendor field names that vary by version, so try
    the likely spellings rather than assuming one."""
    sid = st.get("id") or st.get("name") or st.get("station_id") or "?"
    x, y = st.get("x"), st.get("y")
    kind = st.get("type") or st.get("station_type") or ""
    pos = f"({x:>8.3f}, {y:>8.3f})" if isinstance(x, (int, float)) \
                                      and isinstance(y, (int, float)) else "(no position)"
    return f"  {str(sid):<24} {pos}  {kind}"


def main():
    ap = argparse.ArgumentParser(
        description="Read-only status report from the Seer controller. "
                    "Cannot move the robot.")
    ap.add_argument("host", nargs="?", default="192.168.44.82",
                    help="Seer IP (default: 192.168.44.82, WiFi only)")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    ap.add_argument("--json", action="store_true",
                    help="dump raw replies instead of a formatted report")
    args = ap.parse_args()

    print(f"connecting to {args.host}:{PORT_STATUS} (status port, read-only)")

    try:
        with SeerStatusClient(args.host, timeout=args.timeout) as c:
            data = {
                "info": c.info(),
                "location": c.location(),
                "stations": c.stations(),
                "task": c.task(),
                "alarms": c.alarms(),
            }
    except socket.timeout:
        print(f"\nTIMED OUT. The robot is reachable over WiFi only.\n"
              f"  ping -c3 {args.host}\n"
              f"  ip route get {args.host}      # must say dev wlan0\n"
              f"See docs/network/seer_network_access.md — putting a 192.168.44.x\n"
              f"address on eth0 breaks WiFi access to the robot.", file=sys.stderr)
        return 2
    except (OSError, SeerError) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    print("\n" + "=" * 66)
    print("STATIONS ON THE LOADED MAP   <-- the real ids, use these")
    print("=" * 66)
    stations = data["stations"].get("stations") or []
    if stations:
        for st in stations:
            print(_fmt_station(st))
        print(f"\n  {len(stations)} stations. Our names (station_3, station_9, "
              f"station_out) are\n  invented placeholders and must be mapped onto these.")
    else:
        print("  none reported — no map loaded, or the map has no stations")

    loc = data["location"]
    print("\n" + "=" * 66)
    print("CURRENT STATE")
    print("=" * 66)
    if loc:
        print(f"  position     x={loc.get('x')}  y={loc.get('y')}  "
              f"angle={loc.get('angle')}")
        print(f"  current map  {loc.get('current_station') or loc.get('map_id') or '-'}")

    task = data["task"]
    if task:
        print(f"  task status  {task.get('task_status', '-')}")
        print(f"  task site    {task.get('target_id') or task.get('task_id') or '-'}")

    alarms = data["alarms"]
    fatals = alarms.get("fatals") or []
    errors = alarms.get("errors") or []
    warnings = alarms.get("warnings") or []
    print(f"\n  alarms       {len(fatals)} fatal · {len(errors)} error · "
          f"{len(warnings)} warning")
    for a in (fatals + errors)[:8]:
        print(f"    {a.get('code', '?')}  {a.get('desc', '')}")

    if fatals or errors:
        print("\n  ⚠ Unresolved alarms present. Per docs/can_relay/test-process.md,\n"
              "    clear them and confirm a clean baseline before any drive test.")

    print("\n" + "=" * 66)
    print("Read-only. Nothing was commanded.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
