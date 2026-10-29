"""Anonymous POC HTTP API behind HTTPS or native TLS, with bounded CORS routes.

Execution request: execute the plan with trackers in .plan/trackers/ for each milestone.
"""
from __future__ import annotations
import base64
import json
import sqlite3
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .contracts import canonical, hash_text
from .control_plane import ControlPlane
from .global_store import Conflict


def server(store, archive, *, host="127.0.0.1", port=8766, tls_cert=None, tls_key=None, access_mode="anonymous_poc", authority=None):
    if access_mode != "anonymous_poc": raise ValueError("Authenticated identity provider is not configured; no silent fallback")
    api = ControlPlane(store, archive)
    from .review import Inbox
    review_root = store.directory / "review"
    inbox = Inbox(review_root, review_root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def send(self, status, value, kind="application/json; charset=utf-8"):
            data = (canonical(value) if kind.startswith("application/json") else value).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(data)

        def valid_host(self):
            return authority is None or self.headers.get("Host") == authority

        def do_OPTIONS(self): self.send(200, {"access_mode": "anonymous_poc"})

        def do_GET(self):
            if not self.valid_host(): self.send(400, {"error": "Unexpected authority"}); return
            parsed = urlparse(self.path); path = parsed.path
            try:
                if path == "/":
                    from pathlib import Path
                    self.send(200, Path(__file__).with_name("fleet.html").read_text(), "text/html; charset=utf-8")
                elif path == "/reports":
                    self.send(200, inbox.html(), "text/html; charset=utf-8")
                elif path == "/api/inbox":
                    self.send(200, {**inbox.snapshot(), "access_mode": "anonymous_poc"})
                elif path == "/api/history":
                    query = parse_qs(parsed.query)
                    self.send(200, inbox.history(query.get("branch", [None])[0], int(query.get("offset", [0])[0]), int(query.get("limit", [50])[0])))
                elif path.startswith("/api/report/"):
                    self.send(200, inbox.report(path.rsplit("/", 1)[1]))
                elif path in ("/health", "/api/status", "/api/rounds"):
                    result = store.snapshot(); result.update(access_mode="anonymous_poc", actor_assurance="poc_anonymous")
                    self.send(200, result)
                elif path.startswith("/api/rounds/"): self.send(200, store.snapshot(path.rsplit("/", 1)[1]))
                elif path == "/api/messages": self.send(200, {"items": api.audit.messages()})
                elif path == "/api/events":
                    query = parse_qs(parsed.query); self.send(200, api.audit.export_events(int(query.get("after", [0])[0])))
                elif path.startswith("/evidence/"):
                    pieces = path.split("/")
                    if len(pieces) == 4:
                        self.send(200, inbox.evidence(pieces[2], int(pieces[3])), "text/plain; charset=utf-8")
                    else:
                        data = archive.read(path.rsplit("/", 1)[1]); self.send(200, data.decode("utf-8"), "text/plain; charset=utf-8")
                elif path.startswith("/api/artifacts/"):
                    data = archive.read(path.rsplit("/", 1)[1]); self.send(200, {"data": base64.b64encode(data).decode()})
                elif path.startswith("/api/bundles/"): self.send(200, archive.export(path.rsplit("/", 1)[1]))
                else: self.send(404, {"error": "Not found"})
            except FileNotFoundError: self.send(404, {"error": "Artifact not found"})
            except (ValueError, KeyError, UnicodeError) as error: self.send(400, {"error": str(error)})
            except sqlite3.Error as error: self.send(503, {"error": str(error)})

        def do_POST(self):
            if not self.valid_host(): self.send(400, {"error": "Unexpected authority"}); return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 4 * 1024 * 1024 or self.headers.get_content_type() != "application/json":
                    raise ValueError("Expected bounded JSON request")
                self.connection.settimeout(15)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict): raise ValueError("Expected object")
                path = urlparse(self.path).path
                if path == "/api/feedback":
                    result = inbox.submit(body)
                elif path == "/api/reports/publish":
                    from .contracts import relative
                    from .protocol import atomic_json
                    from pathlib import Path
                    for evidence in body["evidence"]:
                        logical = relative(evidence["path"])
                        target = (review_root / logical).resolve()
                        if not target.is_relative_to(review_root): raise ValueError("Released source escapes review root")
                        data = base64.b64decode(evidence["data"], validate=True)
                        if len(data) > 2_000_000: raise ValueError("Released text evidence limit exceeded")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                    result = inbox.publish(body["packet"])
                elif path == "/api/artifacts":
                    result = archive.put(base64.b64decode(body["data"], validate=True))
                else:
                    prefix = "/integration/v1/" if path.startswith("/integration/v1/") else "/api/"
                    if not path.startswith(prefix): self.send(404, {"error": "Not found"}); return
                    result = api.call(path[len(prefix):], body)
                self.send(200, result)
            except Conflict as error: self.send(409, {"error": str(error)})
            except (ValueError, TypeError, KeyError) as error: self.send(400, {"error": str(error)})
            except sqlite3.Error as error: self.send(503, {"error": str(error)})
            except OSError as error: self.send(503, {"error": str(error)})
    class BoundedServer(ThreadingHTTPServer):
        def __init__(self, *args):
            self.slots = threading.BoundedSemaphore(64)
            super().__init__(*args)

        def process_request(self, request, address):
            request.settimeout(15)
            if not self.slots.acquire(blocking=False):
                try: request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                finally: self.shutdown_request(request)
                return
            try: super().process_request(request, address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, address):
            try: super().process_request_thread(request, address)
            finally: self.slots.release()

    httpd = BoundedServer((host, port), Handler)
    httpd.daemon_threads = True
    if tls_cert or tls_key:
        if not tls_cert or not tls_key: httpd.server_close(); raise ValueError("TLS certificate and key must be configured together")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(tls_cert, tls_key); httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    return httpd
