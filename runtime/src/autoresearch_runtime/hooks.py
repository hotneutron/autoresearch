"""Bounded declared hooks are advisory context and cannot grant successor approval."""
from __future__ import annotations
import subprocess
import time
import os
import signal
import tempfile
from .contracts import integer, seal
from .protocol import verify_binding


def run_hook(spec):
    verify_binding(spec)
    timeout = integer(spec["timeout_ms"], minimum=1)
    limit = integer(spec.get("max_output_bytes", 8192), minimum=1)
    if timeout > 30000 or limit > 65536: raise ValueError("Hook budget exceeds profile")
    started = time.monotonic()
    import selectors
    process = subprocess.Popen(spec["argv"], cwd=spec["cwd"], env=spec.get("env", {}),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
    output = bytearray()
    timed_out, exceeded = False, False
    deadline = started + timeout / 1000
    def kill_group():
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True; kill_group(); break
                ready = selector.select(remaining)
                if not ready: continue
                data = os.read(process.stdout.fileno(), min(4096, limit + 1 - len(output)))
                if not data:
                    selector.unregister(process.stdout); break
                output.extend(data)
                if len(output) > limit:
                    exceeded = True; kill_group(); break
        try: code = process.wait(timeout=max(.001, deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True; kill_group(); code = process.wait()
    finally:
        if process.poll() is None: kill_group(); process.wait()
        process.stdout.close()
    record = {"returncode": code, "stdout": bytes(output[:limit]).decode("utf-8", errors="replace"),
              "truncated": exceeded, "timed_out": timed_out, "output_limit_exceeded": exceeded}
    verify_binding(spec)
    return seal({"id": spec["id"], **record, "wall_ms": int((time.monotonic()-started)*1000), "advisory": True, "grants_approval": False})
