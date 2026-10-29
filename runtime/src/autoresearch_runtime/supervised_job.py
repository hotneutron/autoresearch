"""Frozen process-group runner inside an independently bounded systemd service."""
from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from .contracts import verify
from .protocol import atomic_json, verdict, verify_binding
from .resources import Leases


def run(path):
    path = Path(path).resolve()
    spec = verify(json.loads(path.read_text()))
    verify_binding(spec)
    leases = Leases(spec.get("lease_root", path.parent / "leases"))
    leases.acquire(spec.get("resources", []))
    started = time.monotonic()
    result = {"execution_status": "crashed", "scientific_pass": False, "evidence_status": "invalid"}
    child = None
    def interrupted(*args):
        raise InterruptedError("Supervisor termination")
    old = signal.signal(signal.SIGTERM, interrupted)
    try:
        with (path.parent / "stdout.log").open("wb") as output:
            child = subprocess.Popen(spec["argv"], cwd=spec["cwd"], env=spec.get("env", {}),
                                     stdout=output, stderr=subprocess.STDOUT, close_fds=True,
                                     pass_fds=tuple(leases.fds))
            atomic_json(path.parent / "process.json", {"pid": child.pid})
            try:
                code = child.wait(timeout=spec["timeout_ms"] / 1000)
                result["execution_status"] = "completed" if code == 0 else "crashed"
            except (InterruptedError, subprocess.TimeoutExpired):
                result["execution_status"] = "interrupted"
                child.terminate()
                try: code = child.wait(timeout=spec.get("grace_ms", 2000) / 1000)
                except subprocess.TimeoutExpired:
                    child.kill(); code = child.wait()
            result["returncode"] = code
        verify_binding(spec)
        if "verdict" in spec: result["verifier"] = verdict(spec["verdict"])
        result["scientific_pass"] = result["execution_status"] == "completed" and code == 0 and result.get("verifier", {}).get("passed", False)
        result["evidence_status"] = "valid" if result["scientific_pass"] else "invalid"
    except BaseException as error:
        result["reason"] = str(error)
        if child and child.poll() is None: child.kill(); child.wait()
    finally:
        signal.signal(signal.SIGTERM, old)
        leases.close()
    result["wall_ms"] = int((time.monotonic() - started) * 1000)
    atomic_json(path.parent / "receipt.json", result)
    return result


def cleanup(path):
    spec = verify(json.loads(Path(path).read_text()))
    command = spec.get("cleanup_argv")
    if command:
        subprocess.run(command, check=True, capture_output=True, timeout=max(1, spec.get("grace_ms", 2000) / 1000))


if __name__ == "__main__":
    if sys.argv[1] == "--cleanup": cleanup(sys.argv[2])
    else: run(sys.argv[1])
