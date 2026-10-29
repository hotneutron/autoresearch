"""Detached local execution worker. Durable receipts survive controller exit."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from .protocol import atomic_json, verify_binding, verdict

# ## Revision History
# - 2026-10-28: W01 requires normal completion before scientific acceptance;
#   execution request is preserved in .plan/trackers/m0-contracts-and-correctness.md.


def process_identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        fields = text[text.rfind(")") + 2:].split()
        return {"pid": pid, "start_ticks": fields[19], "host": socket.gethostname(),
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
    except (OSError, IndexError):
        return None


def alive(identity):
    return bool(identity) and process_identity(identity["pid"]) == identity


def execute(spec_path, lease_fds=()):
    spec = json.loads(Path(spec_path).read_text())
    root = Path(spec_path).parent
    atomic_json(root / "worker.json", process_identity(os.getpid()))
    started = time.monotonic()
    result = {"execution_status": "crashed", "returncode": None,
              "evidence_status": "invalid", "scientific_pass": False}
    child = None
    try:
        verify_binding(spec)
        with (root / "stdout.log").open("wb") as log:
            child = subprocess.Popen(spec["argv"], cwd=spec["cwd"], env=spec["env"],
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                     pass_fds=tuple(lease_fds))
            atomic_json(root / "process.json", process_identity(child.pid))
            try:
                rc = child.wait(timeout=spec["timeout_seconds"])
                result["execution_status"] = "completed" if rc == 0 else "crashed"
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                rc = child.returncode
                result["execution_status"] = "interrupted"
                result["reason"] = "Timeout: complete unit is invalid; no automatic retry"
            result["returncode"] = rc
        verify_binding(spec)
        result["verifier"] = verdict(spec["verdict"])
        result["scientific_pass"] = result["execution_status"] == "completed" and rc == 0 and result["verifier"]["passed"]
        result["evidence_status"] = "valid" if result["scientific_pass"] else "invalid"
    except BaseException as error:
        result["reason"] = str(error)
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    result["wall_seconds"] = time.monotonic() - started
    atomic_json(root / "receipt.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(execute(sys.argv[1], [int(value) for value in sys.argv[2:]]))
