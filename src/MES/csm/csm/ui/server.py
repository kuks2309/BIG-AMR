"""A live view of the running CSM, in a browser.

The handbook records that "CSM has no UI in the specification and needs one",
and that it is unscoped. This is the operator's view of the simulation: what
every robot, job, machine, rack and material is doing, right now.

WHY A BROWSER AND NOT A TERMINAL. The floor is two-dimensional and the most
useful single thing is a map with the robots on it. A terminal cannot draw one.

WHY NO WEB FRAMEWORK. This runs inside a ROS node on a plant PC. Adding Flask
or FastAPI to that would be a dependency, a version conflict and an install
step, in exchange for nothing this needs — the whole surface is two GETs.
Python's own http.server does it.

WHY POLLING AND NOT WEBSOCKETS. A factory floor changes at walking pace. Two
samples a second is more than enough, and a poll survives the page being left
open overnight, the node restarting underneath it, and a laptop lid closing —
none of which a socket does without reconnect logic nobody will maintain.

READ-ONLY. There is no route that changes anything. An operator screen that can
accidentally dispatch a robot is worse than no screen.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .page import page as live_page
from . import dashboard, tables
from .state import collect


def _store(node):
    """The job store, or None. Never the thing that breaks a page."""
    try:
        return node.app.store
    except Exception:
        return None


def _clock(node):
    """The node's own clock, or None if it cannot be read.

    None is honest: the ageing checks need a clock, and without one they say
    so rather than reporting everything as fine.
    """
    try:
        return node.get_clock().now().nanoseconds * 1e-9
    except Exception:
        return None


class _Handler(BaseHTTPRequestHandler):
    node = None

    def do_GET(self):
        if self.path.startswith("/state"):
            return self._json(collect(self.node))
        if self.path.startswith("/health"):
            # The management view's data. A separate snapshot rather than a
            # field on /state, because the two pages ask different questions
            # and neither should slow the other down.
            return self._json(dashboard.report(collect(self.node),
                                               now=_clock(self.node)))
        if self.path.startswith("/tables.json"):
            return self._json(tables.collect(_store(self.node)))
        if self.path.rstrip("/") in ("/dashboard", "/status"):
            return self._html(dashboard.page())
        if self.path.rstrip("/") in ("/tables", "/records"):
            return self._html(tables.page())
        if self.path in ("/", "/index.html"):
            return self._html(live_page())
        self.send_error(404)

    def _json(self, payload):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # The page polls; nothing here may be cached.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # NO-STORE ON THE PAGE TOO, not only on the data.
        #
        # It was set on /state and forgotten here, so a browser could keep
        # serving a page from an earlier run while the data underneath it had
        # moved on. The symptom is the worst kind: a view that looks alive and
        # is showing something else.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        """Silence. One line per poll would drown the node's own log."""


class UiServer:
    """Serves the view on a background thread.

    Failure to start is NOT fatal. A view is a convenience; a port already in
    use must never stop a simulation from running.
    """

    def __init__(self, node, port=8080, logger=print):
        self.node = node
        self.port = port
        self.logger = logger
        self._httpd = None
        self._thread = None

    def start(self):
        handler = type("_BoundHandler", (_Handler,), {"node": self.node})
        try:
            self._httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        except OSError as exc:
            self.logger(f"UI not started on port {self.port}: {exc}")
            return False
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        daemon=True)
        self._thread.start()
        self.logger(f"UI on http://localhost:{self.port}")
        return True

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
