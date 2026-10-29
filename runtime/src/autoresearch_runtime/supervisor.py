"""Persistent systemd deadline authority, opt-in for new distributed runs.

Execution request: execute the plan with trackers in .plan/trackers/ for each milestone.
Backend qualification requires actual Linux/systemd conformance; mocks are insufficient.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from contextlib import contextmanager
from .contracts import canonical, identifier, integer, seal
from .protocol import atomic_json


class UnqualifiedBackend(RuntimeError): pass


class SystemdSupervisor:
    def __init__(self, directory, *, user=True):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.user = user

    def qualification(self):
        reasons = []
        if sys.platform != "linux": reasons.append("systemd supervision requires Linux")
        if not shutil.which("systemd-run") or not shutil.which("systemctl"):
            reasons.append("systemd tools unavailable")
        if not reasons:
            probe = subprocess.run(self._ctl("show", "--property=Version"), capture_output=True, timeout=5)
            if probe.returncode: reasons.append("service manager unavailable to execution account")
        return {"available": not reasons, "qualified": False, "reasons": reasons,
                "requirement": "actual lifecycle/deadline/lease conformance"}

    def _ctl(self, *args):
        return ["systemctl", *(["--user"] if self.user else []), *args]

    @contextmanager
    def _lock(self):
        with (self.directory / "supervisor.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def start(self, attempt_id, spec):
        identifier(attempt_id)
        integer(spec["timeout_ms"], minimum=1)
        grace_ms = integer(spec.get("grace_ms", 2000), minimum=1)
        if not isinstance(spec.get("argv"), list) or not spec["argv"]:
            raise ValueError("Frozen argv required")
        body = seal(spec)
        path = self.directory / (attempt_id + ".json")
        with self._lock():
            if path.exists():
                previous = json.loads(path.read_text())
                if previous["spec_sha256"] != body["sha256"]: raise ValueError("Attempt spec is immutable")
                return previous
            check = self.qualification()
            if not check["available"]: raise UnqualifiedBackend("; ".join(check["reasons"]))
            unit = "autoresearch-" + hashlib.sha256(attempt_id.encode()).hexdigest()[:24]
            record = {"id": attempt_id, "unit": unit, "spec_sha256": body["sha256"],
                      "state": "launch_intent", "spec": body}
            atomic_json(path, record)
            out = self.directory / attempt_id
            out.mkdir(exist_ok=False)
            atomic_json(out / "job.json", body)
            command = ["systemd-run", *(["--user"] if self.user else []), "--quiet", "--no-block",
                       "--unit=" + unit, "--property=KillMode=control-group",
                       "--property=RuntimeMaxSec=" + str(spec["timeout_ms"] / 1000),
                       "--property=TimeoutStopSec=" + str(grace_ms / 1000),
                       "--property=SendSIGKILL=yes", "--property=Restart=no",
                       "--property=WorkingDirectory=" + str(out),
                       sys.executable, "-m", "autoresearch_runtime.supervised_job", str(out / "job.json")]
            if spec.get("cleanup_argv"):
                cleanup = spec["cleanup_argv"]
                if len(cleanup) != 4 or cleanup[1:3] != ["rm", "--force"] or cleanup[3] != "ar-" + attempt_id:
                    raise ValueError("Only the frozen owned container can be cleaned up")
                # systemd executes this independently even after killing the Python runner.
                import shlex
                command.insert(-4, "--property=ExecStopPost=" + shlex.join([sys.executable, "-m", "autoresearch_runtime.supervised_job", "--cleanup", str(out / "job.json")]))
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                record["state"] = "submitted" if result.returncode == 0 else "uncertain"
                record["diagnostic"] = result.stderr[-2000:]
            except (OSError, subprocess.TimeoutExpired) as error:
                record["state"] = "uncertain"
                record["diagnostic"] = str(error)
            atomic_json(path, record)
            return record

    def query(self, attempt_id):
        identifier(attempt_id)
        path = self.directory / (attempt_id + ".json")
        if not path.exists(): return {"state": "never_registered", "id": attempt_id}
        record = json.loads(path.read_text())
        if not self.qualification()["available"]: return {"id": attempt_id, "state": "uncertain"}
        result = subprocess.run(self._ctl("show", record["unit"], "--property=ActiveState,SubState,Result,ExecMainStatus"),
                                capture_output=True, text=True, timeout=5)
        if result.returncode: return {"id": attempt_id, "state": "uncertain", "diagnostic": result.stderr}
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        active = fields.get("ActiveState") in ("active", "activating", "deactivating")
        receipt = self.directory / attempt_id / "receipt.json"
        if active: return {"id": attempt_id, "state": "running", "process": fields}
        if receipt.exists(): return {"id": attempt_id, "state": "terminal", "receipt": json.loads(receipt.read_text()), "process": fields}
        # A service timeout has verifiable terminal state even without a child receipt.
        if fields.get("Result") in ("timeout", "signal", "exit-code"):
            result = {"execution_status": "interrupted" if fields["Result"] == "timeout" else "crashed",
                      "scientific_pass": False, "evidence_status": "invalid", "result": fields}
            return {"id": attempt_id, "state": "terminal", "receipt": result}
        return {"id": attempt_id, "state": "uncertain", "process": fields}

    def cancel(self, attempt_id):
        identifier(attempt_id)
        record = json.loads((self.directory / (attempt_id + ".json")).read_text())
        if not self.qualification()["available"]: raise UnqualifiedBackend("service manager unavailable")
        subprocess.run(self._ctl("stop", record["unit"]), check=True, capture_output=True, timeout=10)
        return self.query(attempt_id)
