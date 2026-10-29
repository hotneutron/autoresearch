"""Outbound HTTPS agent with durable grant/receipt outbox and no blind start retries."""
from __future__ import annotations
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from .contracts import canonical, seal, verify, identifier
from .portable_contract import bind_unit
from .protocol import atomic_json
from .metrics import evaluate


class Client:
    def __init__(self, url, *, timeout=15, allow_local_http=False):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme != "https" and not (allow_local_http and parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")):
            raise ValueError("Verified HTTPS endpoint required; local HTTP is only a test fixture")
        self.url, self.timeout = url.rstrip("/"), timeout

    def call(self, operation, body):
        request = Request(self.url + "/integration/v1/" + operation, data=canonical(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=self.timeout) as response: return json.load(response)


class HostAgent:
    def __init__(self, client, supervisor, directory, host, roots, *, python=sys.executable):
        self.client, self.supervisor = client, supervisor
        self.directory = Path(directory).resolve(); self.directory.mkdir(parents=True, exist_ok=True)
        self.host, self.roots, self.python = host, roots, python

    def enroll(self): return self.client.call("hosts/enroll", self.host)

    def claim(self, round_id):
        path = self.directory / "pending-claim.json"
        if path.exists(): request = json.loads(path.read_text())
        else:
            request = {"id": uuid.uuid4().hex, "round_id": round_id, "host_id": self.host["id"], "boot_id": self.host["boot_id"]}
            atomic_json(path, request)
        grant = self.client.call("units/claim", request)
        if grant["state"] == "claimed":
            attempt_root = self.directory / grant["id"]; attempt_root.mkdir(exist_ok=True)
            atomic_json(attempt_root / "grant.json", grant)
        path.unlink()
        return grant

    def start(self, grant):
        root = self.directory / grant["id"]
        out = root / "output"; out.mkdir(exist_ok=True)
        roots = {**self.roots, "output": out}
        path = root / "start-intent.json"
        if path.exists(): request = json.loads(path.read_text())
        else:
            binding = bind_unit(grant["unit"], roots, python=self.python)
            request = {"id": uuid.uuid4().hex, "attempt_id": grant["id"], "binding": binding,
                       **{k: grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}
            atomic_json(path, request)
        authorized = self.client.call("units/start", request)
        atomic_json(root / "authorized.json", authorized)
        body = verify(grant["unit"]); local = verify(request["binding"])
        execution_path = root / "execution-spec.json"
        known = self.supervisor.query(grant["id"])
        if known["state"] not in ("never_registered", "uncertain"):
            return known
        if time.time() >= authorized["deadline"]: raise ValueError("Granted execution deadline expired; reconcile")
        spec = {"argv": local["argv"], "cwd": local["cwd"], "closure": local["closure"], "env": {"PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1"},
                "timeout_ms": min(body["timeout_ms"], int((authorized["deadline"]-time.time())*1000)),
                "grace_ms": min(2000, max(1, body["costs"]["wall_ms"]-body["timeout_ms"])),
                "result_path": str(out / "result.json"), "metrics": body["metrics"],
                "resources": body.get("resources", []), "lease_root": str(self.directory / "leases")}
        if body.get("profile", "local-direct") == "local-container":
            from .executors.container import ContainerExecutor
            from .protocol import sha256
            settings = body["executor"]
            executor = ContainerExecutor(**settings)
            command = executor.command(grant["unit"], roots, grant["id"])
            import shutil
            docker = shutil.which("docker")
            if docker is None: raise ValueError("Container backend unavailable; reconcile grant")
            spec.update(argv=[docker, *command["argv"][1:]], cleanup_argv=[docker, *command["cleanup_argv"][1:]],
                        closure={**local["closure"], docker: sha256(docker)}, profile="local-container")
        elif body.get("profile", "local-direct") != "local-direct":
            raise ValueError("Unqualified executor profile")
        if execution_path.exists():
            spec = json.loads(execution_path.read_text())
        else:
            atomic_json(execution_path, spec)
        return self.supervisor.start(grant["id"], spec)

    def reconcile(self, attempt_id):
        identifier(attempt_id)
        root = self.directory / attempt_id
        grant = json.loads((root / "grant.json").read_text())
        remote = self.client.call("units/query", {"attempt_id": attempt_id})
        status = self.supervisor.query(attempt_id)
        if remote["body"].get("cancel_requested") and status["state"] == "running":
            status = self.supervisor.cancel(attempt_id)
        if status["state"] == "running":
            heartbeat_path = root / "pending-heartbeat.json"
            if heartbeat_path.exists():
                heartbeat = json.loads(heartbeat_path.read_text())
            else:
                seq_path = root / "producer-seq.json"
                seq = json.loads(seq_path.read_text())["value"] + 1 if seq_path.exists() else 0
                atomic_json(seq_path, {"value": seq})
                heartbeat = {"id": uuid.uuid4().hex, "attempt_id": attempt_id, "producer_seq": seq, "supervisor": status,
                             **{k: grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}
                atomic_json(heartbeat_path, heartbeat)
            self.client.call("units/heartbeat", heartbeat)
            heartbeat_path.unlink()
        if status["state"] != "terminal": return status
        path = root / "pending-receipt.json"
        if path.exists(): request = json.loads(path.read_text())
        else:
            receipt = dict(status["receipt"])
            unit = verify(grant["unit"])
            result = root / "output/result.json"
            if result.exists():
                import base64
                raw = result.read_bytes()
                if len(raw) > 2_000_000:
                    receipt.update(scientific_pass=False, evidence_status="invalid", reason="Result exceeds released evidence limit")
                else:
                    artifact = self.client.call("artifacts/blob", {"data": base64.b64encode(raw).decode()})
                    receipt["artifacts"] = [artifact]
                    if receipt["execution_status"] == "completed":
                        try:
                            metrics = evaluate(unit["metrics"], json.loads(raw))
                            receipt.update(scientific_pass=metrics["passed"], evidence_status="valid", metrics=metrics)
                        except (ValueError, TypeError, KeyError) as error:
                            receipt.update(scientific_pass=False, evidence_status="invalid", reason="Malformed result: " + str(error))
            elif receipt["execution_status"] == "completed":
                receipt.update(scientific_pass=False, evidence_status="invalid", reason="Required result missing")
            elapsed = receipt.get("wall_ms", unit["costs"]["wall_ms"])
            receipt["costs"] = {"wall_ms": elapsed}
            if "gpu_ms" in unit["costs"]:
                receipt["costs"]["gpu_ms"] = elapsed * unit["gpu_count"]
            if "microcurrency" in unit["costs"]:
                receipt["costs"]["microcurrency"] = (elapsed * unit["rate_microcurrency_per_second"] + 999) // 1000
            request = {"id": uuid.uuid4().hex, "attempt_id": attempt_id, "receipt": receipt,
                       **{k: grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}
            atomic_json(path, request)
        response = self.client.call("units/receipt", request)
        atomic_json(root / "receipt-ack.json", response)
        return response

    def service(self, round_id, *, once=False):
        self.enroll()
        while True:
            for path in self.directory.glob("*/grant.json"):
                if not (path.parent / "receipt-ack.json").exists():
                    if self.supervisor.query(path.parent.name)["state"] == "never_registered":
                        self.start(json.loads(path.read_text()))
                    self.reconcile(path.parent.name)
            grant = self.claim(round_id)
            if grant["state"] == "claimed": self.start(grant)
            if once: return grant
            time.sleep(1)
