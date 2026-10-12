#!/usr/bin/env python3
"""Local asynchronous research-review inbox; Python standard library only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
from urllib.parse import unquote, urlparse
import uuid

REPO = Path.cwd()
DEFAULT_STORE = REPO / "local_artifacts/autoresearch_review"
TEMPLATE = Path(__file__).with_name("inbox.html")
KINDS = {"ack", "comment", "pause", "resume", "approve", "reject"}


class Conflict(ValueError):
    """A stale revision or conflicting idempotency key."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise ValueError("Identifiers must contain 1–100 letters, digits, dots, dashes or underscores")
    return value


def string(value, limit=600):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Expected nonempty text of at most {limit} characters")
    return value


def strings(value, maximum=6):
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"Expected 1–{maximum} short text items")
    return [string(item) for item in value]


class Inbox:
    def __init__(self, directory=DEFAULT_STORE, repo=REPO):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.repo = Path(repo).resolve()
        self.database = self.directory / "inbox.sqlite3"
        with self.connect() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in {0, 1, 2}:
                raise Conflict("Unsupported newer store schema; use a compatible runtime")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS packets (
                    id TEXT PRIMARY KEY, branch TEXT NOT NULL, revision INTEGER NOT NULL,
                    hash TEXT NOT NULL, body TEXT NOT NULL, published TEXT NOT NULL,
                    UNIQUE(branch, revision));
                CREATE TABLE IF NOT EXISTS evidence (hash TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS branches (id TEXT PRIMARY KEY, paused INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS feedback (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    packet_id TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued', reason TEXT, checkpoint TEXT, applied TEXT);
                CREATE TABLE IF NOT EXISTS permits (
                    packet_id TEXT, action_id TEXT, verdict TEXT NOT NULL, feedback_id TEXT NOT NULL,
                    PRIMARY KEY(packet_id, action_id));
                CREATE TABLE IF NOT EXISTS checkpoints (
                    branch TEXT, id TEXT, receipt TEXT NOT NULL, PRIMARY KEY(branch, id));
                CREATE TABLE IF NOT EXISTS jobs (
                    branch TEXT, checkpoint TEXT, action_id TEXT, packet_id TEXT NOT NULL,
                    started TEXT NOT NULL, finished TEXT, returncode INTEGER,
                    PRIMARY KEY(branch, checkpoint));
            """)

    @contextmanager
    def connect(self, write=False):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def validate(self, supplied):
        p = json.loads(encode(supplied))
        if not isinstance(p, dict) or type(p.get("schema_version")) is not int or p["schema_version"] not in {1, 2}:
            raise ValueError("schema_version must be 1 or 2")
        for field in ("id", "branch", "contract_id"):
            identifier(p[field])
        if type(p["revision"]) is not int or p["revision"] < 1:
            raise ValueError("revision must be a positive integer")
        for field in ("title", "question", "takeaway", "why_it_matters", "decision"):
            string(p[field], 320)
        for field in ("changed", "limitations"):
            strings(p[field])
        if p["evidence_status"] not in {"valid", "diagnostic", "invalid"}:
            raise ValueError("evidence_status must be valid, diagnostic or invalid")
        if p["review_mode"] not in {"fyi", "advice", "decision"}:
            raise ValueError("review_mode must be fyi, advice or decision")
        string(p["review_question"], 500)
        string(p["recommendation"], 500)
        string(p["review_by"], 200)
        if type(p.get("historical", False)) is not bool:
            raise ValueError("historical must be boolean")
        if not isinstance(p["metrics"], list) or not (0 if p["schema_version"] == 2 else 1) <= len(p["metrics"]) <= 12:
            raise ValueError("Provide up to 12 metrics with scope and source")
        for metric in p["metrics"]:
            for key in ("name", "baseline", "result", "rule", "scope"):
                string(metric[key], 320)
        if not isinstance(p["actions"], list) or not (0 if p["schema_version"] == 2 else 1) <= len(p["actions"]) <= 10:
            raise ValueError("Provide up to 10 concrete next actions")
        seen = set()
        for a in p["actions"]:
            identifier(a["id"])
            if a["id"] in seen:
                raise ValueError("Duplicate action id")
            seen.add(a["id"])
            for key in ("eligible", "requires_approval"):
                if type(a[key]) is not bool:
                    raise ValueError(f"{key} must be boolean")
            for key in ("label", "reason"):
                string(a[key], 500)
            if a.get("argv") is not None:
                strings(a["argv"], 60)
        if p["review_mode"] == "decision" and not any(a["requires_approval"] for a in p["actions"]):
            raise ValueError("A decision request must identify the actions that require approval")
        sources = p["sources"]
        if not isinstance(sources, list) or not 1 <= len(sources) <= 12:
            raise ValueError("Provide 1–12 explicitly selected, released evidence files")
        snapshots = []
        for source in sources:
            string(source["label"])
            path = (self.repo / source["path"]).resolve()
            if not path.is_relative_to(self.repo) or path.suffix not in {".md", ".json", ".csv", ".txt"}:
                raise ValueError("Evidence must be a text report inside the repository")
            if path.stat().st_size > 2_000_000:
                raise ValueError("Use a compact evidence report (maximum 2 MB per source)")
            raw = path.read_bytes()
            actual = digest(raw)
            if source.get("sha256") and source["sha256"] != actual:
                raise Conflict(f"Evidence changed: {source['path']}")
            source["path"] = path.relative_to(self.repo).as_posix()
            source["sha256"] = actual
            snapshots.append((actual, raw.decode("utf-8")))
        for metric in p["metrics"]:
            if type(metric["source"]) is not int or not 0 <= metric["source"] < len(sources):
                raise ValueError("Every metric must reference an evidence source index")
            if p["schema_version"] == 2:
                from .protocol import pointer
                for key in ("key", "unit", "baseline_id", "comparison_key", "selector"):
                    string(metric[key])
                if type(metric["support"]) is not int or metric["support"] < 0:
                    raise ValueError("Metric support must be a nonnegative count")
                source = sources[metric["source"]]
                raw = next(body for key, body in snapshots if key == source["sha256"])
                actual = pointer(json.loads(raw), metric["selector"])
                if type(actual) is not type(metric["value"]) or actual != metric["value"]:
                    raise Conflict("Metric value does not match its source selector")
        if "project_id" in p:
            identifier(p["project_id"])
        if "workflow" in p:
            from .workflow import validate_workflow
            if p["schema_version"] != 2 or p["actions"] or p["review_mode"] == "decision":
                raise ValueError("Workflow overview is advisory-only and has no executable actions")
            validate_workflow(p["workflow"], len(sources))
            if p.get("project_id", p["workflow"]["project_id"]) != p["workflow"]["project_id"]:
                raise ValueError("Workflow project identity differs")
            p["project_id"] = p["workflow"]["project_id"]
            with self.connect() as db:
                self.validate_workflow_links(db, p)
        if "translations" in p:
            from .localization import validate_translations
            validate_translations(p["translations"], p)
        return p, snapshots

    @staticmethod
    def validate_workflow_links(db, packet):
        """A prose claim is not a permit; links must bind exact same-project records."""
        workflow = packet.get("workflow")
        if not workflow:
            return
        project = workflow["project_id"]
        allowed_branches = {packet["branch"]}
        for effort in workflow["efforts"]:
            target = effort.get("target")
            if not target:
                continue
            row = db.execute("SELECT * FROM packets WHERE id=?", (target["packet_id"],)).fetchone()
            if not row or row["hash"] != target["packet_hash"]:
                raise Conflict("Workflow target packet is missing or changed")
            body = json.loads(row["body"])
            if body.get("project_id") != project or "workflow" in body:
                raise Conflict("Workflow links must target a study in the same declared project")
            allowed_branches.add(row["branch"])
        for disposition in workflow["feedback_dispositions"]:
            row = db.execute("SELECT f.status,p.branch,p.body FROM feedback f JOIN packets p ON p.id=f.packet_id WHERE f.id=?", (disposition["feedback_id"],)).fetchone()
            if not row or row["status"] != "applied" or row["branch"] not in allowed_branches or json.loads(row["body"]).get("project_id") != project:
                raise Conflict("Disposition must refer to applied feedback for this overview or a linked same-project study")

    def publish(self, supplied):
        p, snapshots = self.validate(supplied)
        body = encode(p)
        sha = digest(body.encode())
        with self.connect(write=True) as db:
            existing = db.execute("SELECT * FROM packets WHERE id=?", (p["id"],)).fetchone()
            if existing:
                if existing["hash"] != sha:
                    raise Conflict("Packet ids are immutable; publish a new id and revision")
                return {"id": p["id"], "hash": sha, "published": existing["published"], "duplicate": True}
            latest_row = db.execute("SELECT * FROM packets WHERE branch=? ORDER BY revision DESC LIMIT 1", (p["branch"],)).fetchone()
            if latest_row:
                prior = json.loads(latest_row["body"])
                if prior.get("project_id") != p.get("project_id"):
                    raise Conflict("A branch cannot change its declared project identity")
                if ("workflow" in prior) != ("workflow" in p):
                    raise Conflict("Overview and execution reports must use separate stable branches")
            self.validate_workflow_links(db, p)
            latest = latest_row["revision"] if latest_row else 0
            if p["revision"] != latest + 1:
                raise Conflict("Publish consecutive revisions within each branch")
            for key, snapshot in snapshots:
                db.execute("INSERT OR IGNORE INTO evidence VALUES (?,?)", (key, snapshot))
            published = now()
            db.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)", (p["id"], p["branch"], p["revision"], sha, body, published))
            db.execute("INSERT OR IGNORE INTO branches(id) VALUES (?)", (p["branch"],))
        return {"id": p["id"], "hash": sha, "published": published, "duplicate": False}

    @staticmethod
    def latest(db, branch):
        row = db.execute("SELECT * FROM packets WHERE branch=? ORDER BY revision DESC LIMIT 1", (branch,)).fetchone()
        if not row:
            raise ValueError("Unknown branch")
        return row

    def submit(self, request):
        for key in ("id", "packet_id"):
            identifier(request[key])
        if request["kind"] not in KINDS:
            raise ValueError("Unknown feedback kind")
        if not isinstance(request.get("comment", ""), str) or len(request.get("comment", "")) > 8000:
            raise ValueError("Feedback text must be at most 8000 characters")
        if request["kind"] == "comment":
            string(request.get("comment", ""), 8000)
        value = {key: request.get(key) for key in ("id", "packet_id", "packet_hash", "kind", "action_id", "comment")}
        encoded = encode(value)
        with self.connect(write=True) as db:
            old = db.execute("SELECT * FROM feedback WHERE id=?", (value["id"],)).fetchone()
            if old:
                if old["body"] != encoded:
                    raise Conflict("Feedback id reused with different contents")
                return dict(old)
            row = db.execute("SELECT * FROM packets WHERE id=?", (value["packet_id"],)).fetchone()
            if not row:
                raise ValueError("Unknown packet")
            if row["hash"] != value["packet_hash"] or self.latest(db, row["branch"])["id"] != row["id"]:
                raise Conflict("This report has changed. Refresh and review the current revision.")
            p = json.loads(row["body"])
            if "workflow" in p and value["kind"] not in {"ack", "comment"}:
                raise ValueError("Overview feedback is advisory; open the current study report to approve, pause or resume")
            if value["kind"] in {"approve", "reject"}:
                action = next((a for a in p["actions"] if a["id"] == value["action_id"]), None)
                if not action:
                    raise ValueError("Select a declared action")
                if value["kind"] == "approve" and (not action["eligible"] or not action["requires_approval"]):
                    raise ValueError("Approval cannot override a failed gate or expand an action's scope")
            elif value["action_id"] is not None:
                raise ValueError("Only approve/reject feedback takes an action_id")
            db.execute("INSERT INTO feedback(id,packet_id,body,created) VALUES (?,?,?,?)", (value["id"], value["packet_id"], encoded, now()))
            return dict(db.execute("SELECT * FROM feedback WHERE id=?", (value["id"],)).fetchone())

    def checkpoint(self, branch, checkpoint_id):
        identifier(checkpoint_id)
        with self.connect(write=True) as db:
            previous = db.execute("SELECT receipt FROM checkpoints WHERE branch=? AND id=?", (branch, checkpoint_id)).fetchone()
            if previous:
                return json.loads(previous[0])
            latest = self.latest(db, branch)
            events = db.execute("SELECT f.* FROM feedback f JOIN packets p ON p.id=f.packet_id WHERE p.branch=? AND f.status='queued' ORDER BY f.seq", (branch,)).fetchall()
            receipts = []
            for row in events:
                event = json.loads(row["body"])
                if event["packet_id"] != latest["id"] or event["packet_hash"] != latest["hash"]:
                    status, reason = "stale", "Superseded report: no effect. Resubmit against the current revision."
                else:
                    status, reason = "applied", "Consumed at a safe checkpoint"
                    if event["kind"] in {"pause", "resume"}:
                        db.execute("UPDATE branches SET paused=? WHERE id=?", (int(event["kind"] == "pause"), branch))
                    elif event["kind"] in {"approve", "reject"}:
                        db.execute("INSERT OR REPLACE INTO permits VALUES (?,?,?,?)", (event["packet_id"], event["action_id"], event["kind"], event["id"]))
                    elif event["kind"] == "comment":
                        reason = "Delivered to the meta loop; advisory only, no automatic policy change"
                db.execute("UPDATE feedback SET status=?,reason=?,checkpoint=?,applied=? WHERE id=?", (status, reason, checkpoint_id, now(), event["id"]))
                receipts.append({**event, "status": status, "reason": reason})
            result = {"branch": branch, "checkpoint": checkpoint_id, "packet_id": latest["id"], "feedback": receipts}
            db.execute("INSERT INTO checkpoints VALUES (?,?,?)", (branch, checkpoint_id, encode(result)))
            return result

    @staticmethod
    def action_state(db, row, action):
        paused = db.execute("SELECT paused FROM branches WHERE id=?", (row["branch"],)).fetchone()[0]
        permit = db.execute("SELECT verdict FROM permits WHERE packet_id=? AND action_id=?", (row["id"], action["id"])).fetchone()
        if not action["eligible"]:
            status, reason = "blocked", action["reason"]
        elif paused:
            status, reason = "paused", "Human pause is active for this branch"
        elif permit and permit[0] == "reject":
            status, reason = "rejected", "Human rejected this exact action revision"
        elif action["requires_approval"] and not (permit and permit[0] == "approve"):
            status, reason = "waiting", "Only this action waits for explicit approval; silence is not approval"
        else:
            status, reason = "ready", action["reason"]
        return {**action, "state": status, "runnable": status == "ready", "state_reason": reason}

    def gate(self, branch, action_id):
        with self.connect() as db:
            row = self.latest(db, branch)
            packet = json.loads(row["body"])
            action = next((a for a in packet["actions"] if a["id"] == action_id), None)
            if not action:
                raise ValueError("Unknown action")
            return {"branch": branch, "packet_id": row["id"], "packet_hash": row["hash"], **self.action_state(db, row, action)}

    def run(self, branch, action_id, checkpoint_id):
        receipt = self.checkpoint(branch, checkpoint_id)
        with self.connect(write=True) as db:
            row = self.latest(db, branch)
            if row["id"] != receipt["packet_id"]:
                raise Conflict("New report arrived after this checkpoint; use a new safe checkpoint")
            packet = json.loads(row["body"])
            action = next((a for a in packet["actions"] if a["id"] == action_id), None)
            if not action:
                raise ValueError("Unknown action")
            verdict = self.action_state(db, row, action)
            if not verdict["runnable"]:
                return {"returncode": 2, "gate": verdict, "checkpoint": receipt}
            if not action.get("argv"):
                raise ValueError("No frozen argv for this action; use gate from an existing controller")
            for source in packet["sources"]:
                if digest((self.repo / source["path"]).read_bytes()) != source["sha256"]:
                    raise Conflict("Source changed since publication; publish a new report revision")
            try:
                db.execute("INSERT INTO jobs(branch,checkpoint,action_id,packet_id,started) VALUES (?,?,?,?,?)", (branch, checkpoint_id, action_id, row["id"], now()))
            except sqlite3.IntegrityError as exc:
                raise Conflict("Checkpoint already dispatched a job; inspect it before creating another checkpoint") from exc
        # Review writes remain available while this subprocess runs. Feedback is
        # applied only at a later caller-declared safe checkpoint, never mid-block.
        job_log = self.directory / f"job-{branch}-{checkpoint_id}.log"
        try:
            with job_log.open("w") as log:
                rc = subprocess.run(action["argv"], cwd=self.repo, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
        except OSError as exc:
            job_log.write_text(str(exc))
            rc = 127
        with self.connect(write=True) as db:
            db.execute("UPDATE jobs SET finished=?,returncode=? WHERE branch=? AND checkpoint=?", (now(), rc, branch, checkpoint_id))
        return {"returncode": rc, "packet_id": row["id"], "log": str(job_log), "checkpoint": receipt}

    def snapshot(self):
        with self.connect() as db:
            rows = db.execute("SELECT p.* FROM packets p WHERE revision=(SELECT MAX(revision) FROM packets q WHERE q.branch=p.branch) ORDER BY published DESC,branch").fetchall()
            packets = []
            for row in rows:
                p = json.loads(row["body"])
                p.update(hash=row["hash"], published=row["published"])
                p["actions"] = [self.action_state(db, row, a) for a in p["actions"]]
                p["acknowledged"] = any(json.loads(r[0])["kind"] == "ack" for r in db.execute("SELECT body FROM feedback WHERE packet_id=? AND status!='stale'", (row["id"],)))
                old = db.execute("SELECT body FROM packets WHERE branch=? AND revision<? ORDER BY revision DESC LIMIT 1", (row["branch"], row["revision"])).fetchone()
                p["previous"] = json.loads(old[0]) if old else None
                if "workflow" in p:
                    for effort in p["workflow"]["efforts"]:
                        target = effort.get("target")
                        if target:
                            target_row = db.execute("SELECT branch FROM packets WHERE id=?", (target["packet_id"],)).fetchone()
                            latest_target = self.latest(db, target_row["branch"]) if target_row else None
                            target["is_current"] = bool(latest_target and latest_target["id"] == target["packet_id"] and latest_target["hash"] == target["packet_hash"])
                            target["current_packet_id"] = latest_target["id"] if latest_target else None
                packets.append(p)
            events = [{**dict(r), "body": json.loads(r["body"])} for r in db.execute("SELECT f.*,p.branch FROM feedback f JOIN packets p ON p.id=f.packet_id ORDER BY f.seq DESC LIMIT 200")]
            jobs = [dict(r) for r in db.execute("SELECT * FROM jobs ORDER BY started DESC LIMIT 100")]
        result = {"packets": packets, "feedback": events, "jobs": jobs, "generated": now()}
        # Optional goal-level status is read-only; presentation never instantiates
        # a Controller or grants a campaign permit. Existing stores remain valid.
        contract_path = self.directory / "contract.json"
        if contract_path.exists():
            config = json.loads(contract_path.read_text())
            gate = config.get("contract", {}).get("goal_gate")
            if gate:
                from .goals import GoalLedger
                try:
                    ledger = GoalLedger(gate["ledger"])
                    result["goal_steering"] = ledger.snapshot()
                    result["goal_gate"] = ledger.gate(config["contract"], self.directory)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    result["goal_steering"] = {"state": "goal_review_required", "reason": str(error)}
        return result

    def evidence(self, packet_id, index):
        with self.connect() as db:
            row = db.execute("SELECT body FROM packets WHERE id=?", (packet_id,)).fetchone()
            if not row:
                raise ValueError("Unknown packet")
            sources = json.loads(row[0])["sources"]
            if not 0 <= index < len(sources):
                raise ValueError("Unknown evidence index")
            return db.execute("SELECT body FROM evidence WHERE hash=?", (sources[index]["sha256"],)).fetchone()[0]

    def html(self, offline=False):
        data = self.snapshot() if offline else None
        if data:
            for packet in data["packets"]:
                for i, source in enumerate(packet["sources"]):
                    source["snapshot"] = self.evidence(packet["id"], i)
        translations = json.loads(TEMPLATE.with_name("zh-CN.json").read_text())
        return TEMPLATE.read_text().replace("__INITIAL_DATA__", encode(data).replace("<", "\\u003c")).replace("__OFFLINE__", "true" if offline else "false").replace("__ZH_CN__", encode(translations).replace("<", "\\u003c"))


def server(inbox, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, value, kind="application/json; charset=utf-8"):
            body = (encode(value) if kind.startswith("application/json") else value).encode()
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.valid_host():
                self.send(403, {"error": "Loopback host required"})
                return
            path = urlparse(self.path).path
            try:
                if path == "/":
                    self.send(200, inbox.html(), "text/html; charset=utf-8")
                elif path == "/api/inbox":
                    self.send(200, {**inbox.snapshot(), "token": token})
                elif re.fullmatch(r"/evidence/[A-Za-z0-9_.-]+/[0-9]+", path):
                    _, _, packet_id, index = path.split("/")
                    self.send(200, inbox.evidence(unquote(packet_id), int(index)), "text/plain; charset=utf-8")
                else:
                    self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, IndexError) as exc:
                self.send(400, {"error": str(exc)})

        def do_POST(self):
            if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-Review-Token", ""), token):
                self.send(403, {"error": "Open this inbox locally before submitting feedback"})
                return
            if urlparse(self.path).path != "/api/feedback":
                self.send(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 20_000 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a JSON feedback request of at most 20 KB")
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError("Expected an object")
                self.send(202, inbox.submit(request))
            except Conflict as exc:
                self.send(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                self.send(400, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--repo", type=Path, default=REPO)
    sub = parser.add_subparsers(dest="command", required=True)
    publish = sub.add_parser("publish", help="Publish an immutable report and return immediately")
    publish.add_argument("packet", type=Path)
    overview = sub.add_parser("overview", help="Publish an advisory-only project workflow overview")
    overview.add_argument("document", type=Path)
    sub.add_parser("status")
    checkpoint = sub.add_parser("checkpoint", help="Consume feedback without waiting for a reviewer")
    checkpoint.add_argument("branch")
    checkpoint.add_argument("checkpoint_id")
    gate = sub.add_parser("gate", help="Return action eligibility; exit 2 means this action cannot run")
    gate.add_argument("branch")
    gate.add_argument("action")
    run = sub.add_parser("run", help="Checkpoint, gate and run only the packet's frozen argv")
    run.add_argument("branch")
    run.add_argument("action")
    run.add_argument("checkpoint_id")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    export = sub.add_parser("export")
    export.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        inbox = Inbox(args.store, args.repo)
        rc = 0
        if args.command == "publish":
            result = inbox.publish(json.loads(args.packet.read_text()))
        elif args.command == "overview":
            from .workflow import publish_overview
            result = publish_overview(inbox, json.loads(args.document.read_text()))
        elif args.command == "status":
            result = inbox.snapshot()
        elif args.command == "checkpoint":
            result = inbox.checkpoint(args.branch, args.checkpoint_id)
        elif args.command == "gate":
            result = inbox.gate(args.branch, args.action)
            rc = 0 if result["runnable"] else 2
        elif args.command == "run":
            result = inbox.run(args.branch, args.action, args.checkpoint_id)
            rc = result["returncode"] if result["returncode"] >= 0 else 1
        elif args.command == "export":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(inbox.html(offline=True))
            result = {"output": str(args.output), "mode": "read-only snapshot"}
        else:
            httpd = server(inbox, args.port)
            print(f"Review inbox: http://127.0.0.1:{httpd.server_port}", flush=True)
            print("Feedback is applied only at a caller-declared safe checkpoint.", flush=True)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                httpd.server_close()
            return 0
        print(encode(result))
        return rc
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        print(encode({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
