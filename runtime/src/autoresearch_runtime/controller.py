"""Bounded research queue with durable jobs, review, budgets, and local leases.

Contracts come from the project adapter. Agent submissions select declared units;
they cannot supply eligibility, commands, verifier rules, or approval policy.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

from .protocol import atomic_json, expand, pointer, runtime_identity, sha256, verdict, verify_binding
from .review import Inbox, Conflict, encode, identifier, now
from .worker import alive

STEERING = {"CONTINUE", "DIAGNOSE", "PIVOT", "ADVANCE", "DEFER", "STOP", "ASK_HUMAN"}


class Controller:
    def __init__(self, directory, config=None):
        self.directory = Path(directory).resolve()
        self.inbox = Inbox(self.directory, self.directory)
        with self.inbox.connect(write=True) as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS runtime_config (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS units (id TEXT PRIMARY KEY, task_id TEXT UNIQUE NOT NULL,
                branch TEXT NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL,
                packet_id TEXT, worker TEXT, result TEXT, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, body TEXT NOT NULL, delivered INTEGER DEFAULT 0);
              CREATE TABLE IF NOT EXISTS steering (id TEXT PRIMARY KEY, body TEXT NOT NULL, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, body TEXT, created TEXT);
            """)
            previous = db.execute("SELECT body FROM runtime_config WHERE id=1").fetchone()
            if previous:
                self.config = json.loads(previous[0])
                if config is not None and config != self.config["contract"]:
                    raise Conflict("Campaign contract is immutable; create a new campaign/epoch")
            else:
                if config is None:
                    raise ValueError("Initialize the runtime with a frozen campaign contract")
                self.validate_config(config)
                self.config = {"contract": config, "runtime": runtime_identity()}
                db.execute("INSERT INTO runtime_config VALUES (1,?)", (encode(self.config),))
            db.execute("PRAGMA user_version=2")
        if self.config["runtime"] != runtime_identity():
            raise Conflict("Runtime changed; use the pinned runtime or migrate after job reconciliation")
        self.contract = self.config["contract"]
        atomic_json(self.directory / "contract.json", self.config)

    @staticmethod
    def validate_config(config):
        if config.get("schema_version") != 1:
            raise ValueError("Unsupported campaign schema")
        identifier(config["id"])
        if "project_id" in config:
            identifier(config["project_id"])
        if not config.get("prompt_verbatim"):
            raise ValueError("Original instruction required")
        if not Path(config["project_root"]).is_dir():
            raise ValueError("Project root unavailable")
        budget = config["budget"]
        if type(budget["max_units"]) is not int or budget["max_units"] < 1 or budget["max_seconds"] <= 0:
            raise ValueError("Finite positive budget required")
        for task_id, task in config["tasks"].items():
            identifier(task_id)
            identifier(task["branch"])
            if task.get("approved") not in (True, False) or type(task["approved"]) is not bool:
                raise ValueError("Authorization must be explicit")
            if task["timeout_seconds"] <= 0 or task["timeout_seconds"] > budget["max_seconds"]:
                raise ValueError("Whole unit must fit within the frozen budget")
            if not isinstance(task["argv"], list) or not all(isinstance(x, str) for x in task["argv"]):
                raise ValueError("argv must be a string list")
            verify_binding(task)
            if not task["verdict"]["checks"]:
                raise ValueError("Fixed verifier checks required")
            if task.get("backend", "local") != "local":
                raise ValueError("Remote execution requires a registered, qualified job adapter")
            if task.get("confirmation"):
                from .confirmation import validate
                validate(task["confirmation"])
                expected = [sys.executable, "-m", "autoresearch_runtime.confirmation", "--spec", "{output}/confirmation.json", "--out", "{output}"]
                if task["argv"] != expected:
                    raise ValueError("Confirmation must use the fixed runtime proxy")

    @contextmanager
    def exclusive(self):
        with (self.directory / "controller.lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Conflict("Another controller operation owns this campaign") from error
            yield

    def event(self, db, kind, value):
        db.execute("INSERT INTO journal(kind,body,created) VALUES (?,?,?)", (kind, encode(value), now()))

    def feedback(self):
        with self.inbox.connect() as db:
            active = {r[0] for r in db.execute("SELECT branch FROM units WHERE state IN ('launching','running','reconciliation_required')")}
        receipts = []
        for packet in self.inbox.snapshot()["packets"]:
            if packet["branch"] not in active:
                with self.inbox.connect() as db:
                    queued = db.execute("SELECT 1 FROM feedback f JOIN packets p ON p.id=f.packet_id WHERE p.branch=? AND f.status='queued'", (packet["branch"],)).fetchone()
                if not queued:
                    continue
                receipt = self.inbox.checkpoint(packet["branch"], "boundary-" + uuid.uuid4().hex)
                if receipt["feedback"]:
                    receipts.append(receipt)
                    with self.inbox.connect(write=True) as db:
                        self.event(db, "feedback", receipt)
        return receipts

    def submit(self, task_id, unit_id=None):
        """One stable logical unit per task in this frozen campaign."""
        task = copy.deepcopy(self.contract["tasks"][task_id])
        unit_id = unit_id or task_id
        identifier(unit_id)
        if unit_id != task.get("unit_id", task_id):
            raise Conflict("Unit identity is fixed by the task contract")
        with self.exclusive():
            self.flush()
            self.feedback()
            with self.inbox.connect() as db:
                existing = db.execute("SELECT * FROM units WHERE id=? OR task_id=?", (unit_id, task_id)).fetchone()
                if existing:
                    return dict(existing)
                if db.execute("SELECT 1 FROM units WHERE branch=? AND state IN ('queued','launching','running','reconciliation_required')", (task["branch"],)).fetchone():
                    raise Conflict("Finish or resolve the existing unit on this branch first")
            output = self.directory / "trials" / unit_id
            output.mkdir(parents=True, exist_ok=False)
            task = expand(task, output)
            task["cwd"] = task.get("cwd", self.contract["project_root"])
            task["env"] = task.get("env", {"PATH": os.defpath, "PYTHONNOUSERSITE": "1"})
            if task.get("confirmation"):
                task["confirmation"]["request_id"] = self.contract["id"] + "." + unit_id
                manifest = output / "confirmation.json"
                atomic_json(manifest, task["confirmation"])
                task["closure"][str(manifest)] = sha256(manifest)
            prerequisites = [verdict(r) for r in task.get("requires", [])]
            if task.get("confirmation"):
                from .confirmation import eligibility
                prerequisites.append(eligibility(task["confirmation"]))
            eligible = all(r["passed"] for r in prerequisites)
            info = {"execution_status": "not_started", "scientific_pass": eligible,
                    "evidence_status": "diagnostic", "prerequisites": prerequisites,
                    "reason": "Frozen prerequisites pass" if eligible else "Scientific prerequisite failed"}
            state = "queued" if eligible else "blocked"
            atomic_json(output / "spec.json", task)
            packet = self.packet(unit_id, task, info, pending=True)
            with self.inbox.connect(write=True) as db:
                db.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?)",
                           (unit_id, task_id, task["branch"], encode(task), state, packet["id"], None,
                            None if eligible else encode(info), now()))
                db.execute("INSERT INTO outbox(id,body) VALUES (?,?)", (packet["id"], encode(packet)))
                self.event(db, "submitted", {"unit": unit_id, "state": state})
            self.flush()
            return {"unit": unit_id, "state": state, "packet_id": packet["id"]}

    def packet(self, unit_id, task, info, pending=False):
        branch = task["branch"]
        with self.inbox.connect() as db:
            revision = (db.execute("SELECT MAX(revision) FROM packets WHERE branch=?", (branch,)).fetchone()[0] or 0) + 1
        packet_id = f"{branch}-r{revision}"
        evidence = self.directory / "evidence" / f"{packet_id}.json"
        released = {"unit": unit_id, "result": info, "values": {}}
        metrics = []
        if not pending and task.get("report_metrics") and info.get("execution_status") == "completed":
            raw = json.loads(Path(task["verdict"]["path"]).read_text())
            for index, metric in enumerate(task["report_metrics"]):
                value = pointer(raw, metric["pointer"])
                released["values"][str(index)] = value
                metrics.append({"name": metric["name"], "baseline": metric["baseline"],
                                "result": str(value), "rule": metric["rule"], "scope": metric["scope"],
                                "source": 0, "key": metric["key"], "unit": metric["unit"],
                                "support": metric["support"], "selector": f"/values/{index}",
                                "value": value, "baseline_id": metric["baseline_id"],
                                "comparison_key": metric["comparison_key"]})
        atomic_json(evidence, released)
        passed = info.get("scientific_pass", False)
        review = "decision" if pending and not task["approved"] else "fyi"
        return {"schema_version": 2, "id": packet_id, "branch": branch, "revision": revision,
                **({"project_id": self.contract["project_id"]} if "project_id" in self.contract else {}),
                "contract_id": self.contract["id"], "title": task.get("title", task["branch"]),
                "question": task.get("question", "Does this complete unit satisfy its fixed verifier?"),
                "takeaway": info.get("reason", "Scientific checks pass" if passed else "Scientific checks fail"),
                "why_it_matters": task.get("why_it_matters", "Only verified evidence can support dependent research actions."),
                "changed": ["Unit prepared under a frozen contract" if pending else "Complete unit execution and verification recorded"],
                "limitations": task.get("limitations", ["Execution success alone is not scientific qualification."]),
                "evidence_status": "diagnostic" if pending else ("valid" if passed else "invalid"),
                "decision": "Await scoped decision" if review == "decision" else ("Ready" if pending and passed else "Recorded; no automatic promotion"),
                "review_mode": review, "review_question": "Review at your pace; only named unapproved actions wait.",
                "recommendation": task.get("recommendation", "Inspect the fixed checks and the recorded evidence."),
                "review_by": "Next safe checkpoint; no deadline grants approval", "metrics": metrics,
                "actions": [{"id": unit_id, "label": task.get("title", unit_id), "eligible": passed,
                             "requires_approval": not task["approved"], "reason": info.get("reason", "Fixed checks evaluated")}] if pending else [],
                "sources": [{"label": "Released unit evidence", "path": str(evidence.relative_to(self.directory)), "sha256": sha256(evidence)}],
                "prompt_verbatim": self.contract["prompt_verbatim"], "historical": self.contract.get("historical", False)}

    def flush(self):
        with self.inbox.connect() as db:
            pending = [dict(r) for r in db.execute("SELECT * FROM outbox WHERE delivered=0 ORDER BY rowid")]
        for row in pending:
            self.inbox.publish(json.loads(row["body"]))
            with self.inbox.connect(write=True) as db:
                db.execute("UPDATE outbox SET delivered=1 WHERE id=?", (row["id"],))

    def reconcile(self):
        with self.inbox.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM units WHERE state IN ('launching','running','reconciliation_required')")]
        for row in rows:
            root = self.directory / "trials" / row["id"]
            receipt = root / "receipt.json"
            if receipt.exists():
                process = root / "process.json"
                if process.exists() and alive(json.loads(process.read_text())):
                    continue
                result = json.loads(receipt.read_text())
                # Consume responses to the current packet before superseding it.
                self.inbox.checkpoint(row["branch"], "completed-" + row["id"])
                task = json.loads(row["spec"])
                try:
                    packet = self.packet(row["id"], task, result)
                except (ValueError, KeyError, OSError, TypeError) as error:
                    result.update(scientific_pass=False, evidence_status="invalid", reason=f"Report schema failure: {error}")
                    task.pop("report_metrics", None)
                    packet = self.packet(row["id"], task, result)
                with self.inbox.connect(write=True) as db:
                    db.execute("UPDATE units SET state=?,result=? WHERE id=?",
                               (result["execution_status"], encode(result), row["id"]))
                    db.execute("INSERT OR IGNORE INTO outbox(id,body) VALUES (?,?)", (packet["id"], encode(packet)))
                    self.event(db, "completed", {"unit": row["id"], "result": result})
            else:
                identity_file = root / "worker.json"
                identity = json.loads(identity_file.read_text()) if identity_file.exists() else json.loads(row["worker"] or "null")
                if not alive(identity):
                    with self.inbox.connect(write=True) as db:
                        db.execute("UPDATE units SET state='reconciliation_required' WHERE id=?", (row["id"],))
        self.flush()

    def acquire_resources(self, task):
        root = Path(self.contract.get("lease_root", Path.home() / ".local/state/autoresearch/leases"))
        root.mkdir(parents=True, exist_ok=True)
        descriptors = []
        try:
            for resource in sorted(set(task.get("resources", []))):
                path = root / hashlib.sha256(resource.encode()).hexdigest()
                fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
                descriptors.append(fd)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return descriptors
        except BaseException:
            for fd in descriptors:
                os.close(fd)
            raise

    def step(self):
        with self.exclusive():
            self.reconcile()
            self.feedback()
            with self.inbox.connect() as db:
                rows = [dict(r) for r in db.execute("SELECT * FROM units ORDER BY created,id")]
            active = [r for r in rows if r["state"] in {"running", "launching", "reconciliation_required"}]
            if active:
                return {"state": active[0]["state"], "unit": active[0]["id"]}
            spent = sum(json.loads(r["result"] or "{}").get("wall_seconds", 0) for r in rows)
            attempted = sum(r["state"] in {"completed", "crashed", "interrupted"} for r in rows)
            reasons = {}
            for row in rows:
                if row["state"] != "queued":
                    continue
                task = json.loads(row["spec"])
                gate = self.inbox.gate(row["branch"], row["id"])
                if gate["packet_id"] != row["packet_id"] or not gate["runnable"]:
                    reasons[row["id"]] = "Review gate or report revision changed"
                    continue
                if attempted >= self.contract["budget"]["max_units"] or spent + task["timeout_seconds"] > self.contract["budget"]["max_seconds"]:
                    reasons[row["id"]] = "Budget cannot cover another complete unit"
                    continue
                try:
                    verify_binding(task)
                    prerequisites = [verdict(r) for r in task.get("requires", [])]
                    if not all(v["passed"] for v in prerequisites):
                        raise Conflict("Scientific prerequisite failed at dispatch")
                    descriptors = self.acquire_resources(task)
                except (OSError, ValueError) as error:
                    reasons[row["id"]] = str(error)
                    continue
                try:
                    if task.get("confirmation"):
                        from .confirmation import begin
                        try:
                            begin(task["confirmation"])
                        except (OSError, ValueError) as error:
                            reasons[row["id"]] = str(error)
                            info = {"execution_status": "not_started", "scientific_pass": False,
                                    "evidence_status": "invalid", "reason": str(error)}
                            packet = self.packet(row["id"], task, info, pending=True)
                            with self.inbox.connect(write=True) as db:
                                db.execute("UPDATE units SET state='blocked',result=?,packet_id=? WHERE id=?",
                                           (encode(info), packet["id"], row["id"]))
                                db.execute("INSERT INTO outbox(id,body) VALUES (?,?)", (packet["id"], encode(packet)))
                            self.flush()
                            continue
                    with self.inbox.connect(write=True) as db:
                        current = self.inbox.latest(db, row["branch"])
                        action = next(a for a in json.loads(current["body"])["actions"] if a["id"] == row["id"])
                        if current["id"] != row["packet_id"] or not self.inbox.action_state(db, current, action)["runnable"]:
                            raise Conflict("Gate changed before reservation")
                        db.execute("UPDATE units SET state='launching' WHERE id=? AND state='queued'", (row["id"],))
                        self.event(db, "launch_reserved", {"unit": row["id"], "timeout_seconds": task["timeout_seconds"]})
                    path = self.directory / "trials" / row["id"]
                    with (path / "supervisor.log").open("wb") as log:
                        worker = subprocess.Popen([sys.executable, "-m", "autoresearch_runtime.worker", str(path / "spec.json"), *map(str, descriptors)],
                                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                                  pass_fds=tuple(descriptors))
                    from .worker import process_identity
                    with self.inbox.connect(write=True) as db:
                        db.execute("UPDATE units SET state='running',worker=? WHERE id=?", (encode(process_identity(worker.pid)), row["id"]))
                    # Reap detached workers when this controller remains alive.
                    import threading
                    threading.Thread(target=worker.wait, daemon=True).start()
                    return {"state": "running", "unit": row["id"], "worker_pid": worker.pid}
                finally:
                    for fd in descriptors:
                        os.close(fd)
            return {"state": "idle", "reasons": reasons,
                    "spent_seconds": spent, "attempted_units": attempted}

    def run(self, *, idle_timeout=0, poll_seconds=0.2):
        deadline = time.monotonic() + idle_timeout
        while True:
            result = self.step()
            if result["state"] == "reconciliation_required":
                return result
            if result["state"] == "idle":
                if not result["reasons"] or time.monotonic() >= deadline:
                    return result
            else:
                deadline = time.monotonic() + idle_timeout
            time.sleep(poll_seconds)

    def steer(self, record):
        required = {"id", "action", "trigger", "evidence", "alternatives", "reason", "next_tasks", "budget", "invalidation", "next_checkpoint", "prompt_verbatim"}
        if not required <= record.keys() or record["action"] not in STEERING:
            raise ValueError("Incomplete steering decision")
        for task in record["next_tasks"]:
            if task not in self.contract["tasks"]:
                raise ValueError("New task requires a new frozen contract")
        if record["action"] in {"ADVANCE", "PIVOT"}:
            if any(not self.contract["tasks"][t]["approved"] for t in record["next_tasks"]):
                raise Conflict("Pivot exceeds current authorization; publish a scoped decision")
        with self.inbox.connect(write=True) as db:
            old = db.execute("SELECT body FROM steering WHERE id=?", (record["id"],)).fetchone()
            if old and old[0] != encode(record):
                raise Conflict("Steering records are immutable")
            db.execute("INSERT OR IGNORE INTO steering VALUES (?,?,?)", (record["id"], encode(record), now()))
        return record

    def status(self):
        with self.inbox.connect() as db:
            units = [dict(r) for r in db.execute("SELECT id,task_id,branch,state,result FROM units ORDER BY created")]
            pending = db.execute("SELECT COUNT(*) FROM outbox WHERE delivered=0").fetchone()[0]
        return {"campaign": self.contract["id"], "units": units, "pending_publications": pending,
                "inbox": self.inbox.snapshot()}
