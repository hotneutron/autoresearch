"""Single-host transactional distributed authority. Host agents never open this file.

Execution request: execute the plan with trackers in .plan/trackers/ for each milestone.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3
import time
import uuid
from pathlib import Path
from .contracts import add_costs, canonical, costs, digest, hash_text, identifier, integer, seal, verify
from .costs import within

ACTIVE = ("claimed", "authorized", "running", "uncertain")
TERMINAL = ("completed", "crashed", "interrupted", "cancelled", "never_started")


class Conflict(ValueError): pass


class GlobalStore:
    def __init__(self, directory, *, busy_timeout_ms=5000):
        self.busy_timeout_ms = integer(busy_timeout_ms, minimum=1)
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "coordinator.sqlite3"
        with self.transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1): raise Conflict("Unsupported coordinator store schema")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, body TEXT NOT NULL, paused INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS hosts(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rounds(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), body TEXT NOT NULL, state TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS one_open_round ON rounds(project) WHERE state='active';
                CREATE TABLE IF NOT EXISTS units(id TEXT PRIMARY KEY, round TEXT NOT NULL REFERENCES rounds(id), body TEXT NOT NULL, state TEXT NOT NULL, generation INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, unit TEXT NOT NULL REFERENCES units(id), host TEXT NOT NULL REFERENCES hosts(id), generation INTEGER NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS one_unit_owner ON attempts(unit) WHERE state IN ('claimed','authorized','running','uncertain');
                CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, hash TEXT NOT NULL, result TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(attempt TEXT PRIMARY KEY REFERENCES attempts(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS selections(round TEXT PRIMARY KEY REFERENCES rounds(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, round TEXT NOT NULL REFERENCES rounds(id), body TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS historical_charges(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), origin_key TEXT NOT NULL UNIQUE, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS qualifications(unit TEXT PRIMARY KEY REFERENCES units(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, parent TEXT REFERENCES messages(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(seq INTEGER PRIMARY KEY REFERENCES events(seq), acknowledged INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS openings(id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS exposures(population TEXT NOT NULL, subject TEXT NOT NULL, opening TEXT REFERENCES openings(id), PRIMARY KEY(population,subject));
                CREATE TABLE IF NOT EXISTS exposure_data(digest TEXT PRIMARY KEY, opening TEXT NOT NULL REFERENCES openings(id));
                CREATE TABLE IF NOT EXISTS leader(id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL, body TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def transaction(self, *, write=True):
        db = sqlite3.connect(self.database, timeout=self.busy_timeout_ms / 1000)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
                if getattr(self, "active_epoch", None) is not None:
                    current = db.execute("SELECT epoch FROM leader WHERE id=1").fetchone()
                    if current is None or current[0] != self.active_epoch:
                        raise Conflict("Coordinator leadership generation is stale")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally: db.close()

    @staticmethod
    def _row(db, table, key, value):
        # Table/key names are internal constants, never API parameters.
        row = db.execute(f"SELECT * FROM {table} WHERE {key}=?", (value,)).fetchone()
        if row is None: raise Conflict("Unknown " + table + ": " + str(value))
        return row

    @staticmethod
    def _event(db, kind, body):
        event_id = uuid.uuid4().hex
        cursor = db.execute("INSERT INTO events(id,kind,body,created) VALUES (?,?,?,?)", (event_id, kind, canonical(body), time.time()))
        db.execute("INSERT INTO outbox(seq) VALUES (?)", (cursor.lastrowid,))
        return event_id

    @staticmethod
    def _duplicate(db, request_id, body):
        identifier(request_id)
        row = db.execute("SELECT hash,result FROM requests WHERE id=?", (request_id,)).fetchone()
        if row:
            if row["hash"] != digest(body): raise Conflict("Idempotency key reused with different contents")
            return json.loads(row["result"])
        return None

    @staticmethod
    def _remember(db, request_id, body, result):
        db.execute("INSERT INTO requests VALUES (?,?,?)", (request_id, digest(body), canonical(result)))
        return result

    def register_project(self, body):
        identifier(body["id"]); costs(body["budget"])
        hash_text(body["goal_sha256"])
        with self.transaction() as db:
            old = db.execute("SELECT body FROM projects WHERE id=?", (body["id"],)).fetchone()
            if old and json.loads(old[0]) != body: raise Conflict("Project budget/goal immutable; use explicit revision")
            db.execute("INSERT OR IGNORE INTO projects VALUES (?,?,0)", (body["id"], canonical(body)))
        return body

    def register_host(self, body):
        identifier(body["id"]); identifier(body["boot_id"])
        integer(body["capacity"], minimum=1)
        if not isinstance(body.get("profiles"), list) or not body["profiles"]: raise ValueError("Host profiles required")
        for profile in body["profiles"]: identifier(profile)
        value = dict(body, assurance="poc_anonymous")
        with self.transaction() as db:
            old = db.execute("SELECT body FROM hosts WHERE id=?", (body["id"],)).fetchone()
            if old and json.loads(old[0]) != value:
                if db.execute("SELECT 1 FROM attempts WHERE host=? AND state IN ('claimed','authorized','running','uncertain')", (body["id"],)).fetchone():
                    raise Conflict("Host change requires active-attempt reconciliation")
            db.execute("INSERT INTO hosts VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (body["id"], canonical(value)))
        return value

    def _accounting(self, db, project_id):
        charged, reserved = {}, {}
        for imported in db.execute("SELECT body FROM historical_charges WHERE project=?", (project_id,)):
            charged = add_costs(charged or {"wall_ms": 0}, json.loads(imported[0])["costs"])
        for row in db.execute("SELECT id,body,state FROM rounds WHERE project=?", (project_id,)):
            plan = json.loads(row["body"])
            local = {}
            for receipt in db.execute("SELECT r.body FROM receipts r JOIN attempts a ON a.id=r.attempt JOIN units u ON u.id=a.unit WHERE u.round=?", (row["id"],)):
                local = add_costs(local or {"wall_ms": 0}, json.loads(receipt[0])["costs"])
            charged = add_costs(charged or {"wall_ms": 0}, local or {"wall_ms": 0})
            if row["state"] == "active":
                reserved = add_costs(reserved or {"wall_ms": 0}, {k: max(0, v-local.get(k, 0)) for k, v in plan["budget"].items()})
        return {"charged": charged or {"wall_ms": 0}, "reserved": reserved or {"wall_ms": 0}}

    def accounting(self, project_id):
        with self.transaction(write=False) as db:
            self._row(db, "projects", "id", project_id)
            return self._accounting(db, project_id)

    def admit_round(self, plan):
        body = verify(plan)
        for key in ("id", "project_id"): identifier(body[key])
        integer(body["concurrency"], minimum=1); integer(body["top_k"], minimum=1)
        costs(body["budget"])
        units = body.get("units")
        if not isinstance(units, list) or not units or len(units) > 10000: raise ValueError("Finite unit graph required")
        ids = [verify(u)["id"] for u in units]
        if len(set(ids)) != len(ids): raise ValueError("Unit identities must be unique")
        total = {"wall_ms": 0}
        for unit in units:
            u = verify(unit); identifier(u["id"])
            if u["project_id"] != body["project_id"]: raise Conflict("Cross-project unit")
            for dep in u.get("requires", []):
                if dep not in ids or dep == u["id"]: raise ValueError("Invalid task dependency")
            total = add_costs(total, costs(u["costs"]))
        if not within(total, body["budget"]): raise Conflict("Round cannot cover all complete units")
        visited, active = set(), set()
        graph = {verify(u)["id"]: verify(u).get("requires", []) for u in units}
        def visit(unit_id):
            if unit_id in active: raise ValueError("Cyclic task graph")
            if unit_id in visited: return
            active.add(unit_id)
            for dep in graph[unit_id]: visit(dep)
            active.remove(unit_id); visited.add(unit_id)
        for unit_id in graph: visit(unit_id)
        with self.transaction() as db:
            old = db.execute("SELECT body FROM rounds WHERE id=?", (body["id"],)).fetchone()
            if old:
                if json.loads(old[0]) != plan: raise Conflict("Round is immutable")
                return plan
            project = self._row(db, "projects", "id", body["project_id"])
            if project["paused"]: raise Conflict("Project hold blocks new rounds")
            p = json.loads(project["body"])
            if body["goal_sha256"] != p["goal_sha256"]: raise Conflict("Superseded goal")
            parent = body.get("parent_round")
            if parent:
                row = self._row(db, "rounds", "id", parent)
                if row["project"] != body["project_id"] or row["state"] != "closed": raise Conflict("Parent round not sealed")
                review = db.execute("SELECT body FROM reviews WHERE round=? AND state='applied'", (parent,)).fetchall()
                approved = [json.loads(r[0]) for r in review]
                if not any(r["next_round_sha256"] == plan["sha256"] for r in approved):
                    raise Conflict("Exact successor round lacks applied review")
            elif body.get("initial_authorization") is not True: raise Conflict("Initial round authorization required")
            spent = self._accounting(db, body["project_id"])
            if not within(add_costs(spent["charged"], spent["reserved"], body["budget"]), p["budget"]):
                raise Conflict("Global complete-route budget exhausted")
            try:
                db.execute("INSERT INTO rounds VALUES (?,?,?,'active')", (body["id"], body["project_id"], canonical(plan)))
                db.executemany("INSERT INTO units(id,round,body,state) VALUES (?,?,?,'ready')", [(verify(u)["id"], body["id"], canonical(u)) for u in units])
            except sqlite3.IntegrityError as error: raise Conflict("Active round or unit identity already exists") from error
            self._event(db, "round_admitted", {"round": body["id"], "hash": plan["sha256"]})
        return plan

    def claim(self, request):
        for key in ("id", "host_id", "round_id"): identifier(request[key])
        with self.transaction() as db:
            duplicate = self._duplicate(db, request["id"], request)
            if duplicate is not None: return duplicate
            host = json.loads(self._row(db, "hosts", "id", request["host_id"])["body"])
            if request.get("boot_id") != host["boot_id"]: raise Conflict("Host boot binding differs")
            row = self._row(db, "rounds", "id", request["round_id"])
            if row["state"] != "active": raise Conflict("Round is closed")
            plan = verify(json.loads(row["body"]))
            if self._row(db, "projects", "id", row["project"])["paused"]: raise Conflict("Project is paused")
            count = db.execute("SELECT COUNT(*) FROM attempts a JOIN units u ON u.id=a.unit WHERE u.round=? AND a.state IN ('claimed','authorized','running','uncertain')", (row["id"],)).fetchone()[0]
            host_count = db.execute("SELECT COUNT(*) FROM attempts WHERE host=? AND state IN ('claimed','authorized','running','uncertain')", (host["id"],)).fetchone()[0]
            if count >= plan["concurrency"] or host_count >= host["capacity"]:
                return self._remember(db, request["id"], request, {"state": "no_capacity"})
            chosen = None
            for unit in db.execute("SELECT * FROM units WHERE round=? AND state='ready' ORDER BY id", (row["id"],)):
                u = verify(json.loads(unit["body"]))
                if u.get("profile", "local-direct") not in host["profiles"]: continue
                if any(self._row(db, "units", "id", dep)["state"] != "completed" for dep in u.get("requires", [])): continue
                held = set()
                for existing in db.execute("SELECT u.body FROM units u JOIN attempts a ON a.unit=u.id WHERE a.host=? AND a.state IN ('claimed','authorized','running','uncertain')", (host["id"],)):
                    held.update(verify(json.loads(existing[0])).get("resources", []))
                if held.intersection(u.get("resources", [])): continue
                chosen = unit; break
            if chosen is None:
                return self._remember(db, request["id"], request, {"state": "no_work"})
            generation = chosen["generation"] + 1
            grant = {"id": uuid.uuid4().hex, "unit_id": chosen["id"], "host_id": host["id"],
                     "boot_id": host["boot_id"], "generation": generation, "round_id": row["id"],
                     "nonce": uuid.uuid4().hex, "start_before": time.time() + 60,
                     "unit": json.loads(chosen["body"]), "state": "claimed"}
            db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,'claimed')", (grant["id"], chosen["id"], host["id"], generation, canonical(grant)))
            db.execute("UPDATE units SET state='claimed',generation=? WHERE id=?", (generation, chosen["id"]))
            self._event(db, "unit_claimed", grant)
            return self._remember(db, request["id"], request, grant)

    def _attempt(self, db, request):
        row = self._row(db, "attempts", "id", request["attempt_id"])
        grant = json.loads(row["body"])
        for key in ("host_id", "boot_id", "generation", "nonce"):
            if request.get(key) != grant[key]: raise Conflict("Stale or conflicting attempt binding")
        unit = self._row(db, "units", "id", row["unit"])
        if unit["generation"] != row["generation"]: raise Conflict("Attempt generation is stale")
        return row, grant, unit

    def authorize_start(self, request):
        with self.transaction() as db:
            duplicate = self._duplicate(db, request["id"], request)
            if duplicate is not None: return duplicate
            row, grant, unit = self._attempt(db, request)
            if row["state"] != "claimed" or time.time() > grant["start_before"]: raise Conflict("Grant cannot start; reconcile")
            round_row = self._row(db, "rounds", "id", unit["round"])
            if self._row(db, "projects", "id", round_row["project"])["paused"]: raise Conflict("Project hold blocks new launch")
            binding = verify(request["binding"])
            if binding["unit_sha256"] != grant["unit"]["sha256"]: raise Conflict("Local binding differs from frozen unit")
            if not binding.get("argv") or not binding.get("closure") or not binding.get("output_root"):
                raise Conflict("Complete executable host binding required")
            grant.update(binding=request["binding"], deadline=time.time() + verify(grant["unit"])["costs"]["wall_ms"] / 1000)
            db.execute("UPDATE attempts SET body=?,state='authorized' WHERE id=?", (canonical(grant), row["id"]))
            db.execute("UPDATE units SET state='authorized' WHERE id=?", (unit["id"],))
            result = {**grant, "state": "authorized"}
            self._event(db, "launch_authorized", result)
            return self._remember(db, request["id"], request, result)

    def heartbeat(self, request):
        with self.transaction() as db:
            duplicate = self._duplicate(db, request["id"], request)
            if duplicate is not None: return duplicate
            row, grant, unit = self._attempt(db, request)
            if row["state"] not in ("authorized", "running", "uncertain"): raise Conflict("Attempt is not active")
            previous_seq = grant.get("producer_seq", -1)
            integer(request["producer_seq"])
            if request["producer_seq"] <= previous_seq: raise Conflict("Observation sequence is stale")
            grant.update(producer_seq=request["producer_seq"], observed_at=time.time(), supervisor=request["supervisor"])
            db.execute("UPDATE attempts SET body=?,state='running' WHERE id=?", (canonical(grant), row["id"]))
            db.execute("UPDATE units SET state='running' WHERE id=?", (unit["id"],))
            self._event(db, "heartbeat", {"attempt": row["id"], "seq": request["producer_seq"]})
            return self._remember(db, request["id"], request, {"state": "running"})

    def commit_receipt(self, request):
        receipt = deepcopy(request["receipt"])
        costs(receipt["costs"])
        status = receipt["execution_status"]
        if status not in TERMINAL: raise ValueError("Terminal receipt required")
        if status != "completed" and (receipt.get("scientific_pass") is True or receipt.get("evidence_status") == "valid"):
            raise Conflict("Contradictory terminal validity")
        with self.transaction() as db:
            duplicate = self._duplicate(db, request["id"], request)
            if duplicate is not None: return duplicate
            row, grant, unit = self._attempt(db, request)
            old = db.execute("SELECT body FROM receipts WHERE attempt=?", (row["id"],)).fetchone()
            if old:
                if json.loads(old[0]) != receipt: raise Conflict("Receipt is immutable")
                return self._remember(db, request["id"], request, {"state": status, "duplicate": True})
            if row["state"] not in ACTIVE: raise Conflict("Attempt is not active")
            if status != "never_started" and row["state"] == "claimed":
                raise Conflict("Terminal execution requires prior launch authorization")
            if status == "never_started":
                if row["state"] != "claimed" or receipt.get("verified_never_started") is not True:
                    raise Conflict("Never-started evidence required before reassignment")
                if any(receipt["costs"].values()): raise Conflict("Never-started unit cannot charge execution")
            db.execute("INSERT INTO receipts VALUES (?,?)", (row["id"], canonical(receipt)))
            db.execute("UPDATE attempts SET state=? WHERE id=?", (status, row["id"]))
            db.execute("UPDATE units SET state=? WHERE id=?", ("ready" if status == "never_started" else status, unit["id"]))
            if not within(receipt["costs"], verify(grant["unit"])["costs"]):
                project = self._row(db, "rounds", "id", unit["round"])["project"]
                db.execute("UPDATE projects SET paused=1 WHERE id=?", (project,))
            self._event(db, "receipt_committed", {"attempt": row["id"], "receipt": receipt})
            return self._remember(db, request["id"], request, {"state": status, "attempt_id": row["id"]})

    def pause(self, project_id, paused):
        if type(paused) is not bool: raise ValueError("Explicit boolean hold required")
        with self.transaction() as db:
            self._row(db, "projects", "id", project_id)
            db.execute("UPDATE projects SET paused=? WHERE id=?", (int(paused), project_id))
            self._event(db, "project_control", {"project": project_id, "paused": paused})
        return {"paused": paused}

    def mark_uncertain(self, attempt_id):
        with self.transaction() as db:
            row = self._row(db, "attempts", "id", attempt_id)
            if row["state"] in ACTIVE:
                db.execute("UPDATE attempts SET state='uncertain' WHERE id=?", (attempt_id,))
                db.execute("UPDATE units SET state='uncertain' WHERE id=?", (row["unit"],))
        return {"state": "uncertain"}

    def snapshot(self, round_id=None):
        with self.transaction(write=False) as db:
            rounds = [dict(r) for r in db.execute("SELECT * FROM rounds ORDER BY id")]
            if round_id is not None: rounds = [dict(self._row(db, "rounds", "id", round_id))]
            units = [dict(r) for r in db.execute("SELECT * FROM units ORDER BY id") if round_id is None or r["round"] == round_id]
            attempts = [dict(r) for r in db.execute("SELECT * FROM attempts ORDER BY id") if r["unit"] in {u["id"] for u in units}]
            for rows in (rounds, units, attempts):
                for row in rows: row["body"] = json.loads(row["body"])
            return {"schema_version": 1, "rounds": rounds, "units": units, "attempts": attempts, "generated_at": time.time()}

    def events(self, after=0, limit=100):
        integer(after); integer(limit, minimum=1)
        if limit > 1000: raise ValueError("Event page limit exceeded")
        with self.transaction(write=False) as db:
            return [{**dict(r), "body": json.loads(r["body"])} for r in db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?", (after, limit))]

    def reserve_confirmation(self, opening):
        body = verify(opening)
        identifier(body["id"]); identifier(body["population"])
        hash_text(body["dataset_sha256"]); hash_text(body["qualification_sha256"])
        if not body.get("subjects") or len(set(body["subjects"])) != len(body["subjects"]): raise ValueError("Unique subject exposure identities required")
        for subject in body["subjects"]: identifier(subject)
        if body.get("purpose") != "fresh_confirmation": raise ValueError("Declare fresh confirmation purpose")
        for candidate in body["candidate_hashes"]: hash_text(candidate)
        with self.transaction() as db:
            round_row = self._row(db, "rounds", "id", body["round_id"])
            if round_row["project"] != body["project_id"]: raise Conflict("Confirmation project differs")
            old = db.execute("SELECT body FROM openings WHERE id=?", (body["id"],)).fetchone()
            if old:
                if json.loads(old[0]) != opening: raise Conflict("Confirmation opening immutable")
                return {"state": "reserved", "opening_id": body["id"], "duplicate": True}
            try:
                db.execute("INSERT INTO openings VALUES (?,?,'reserved')", (body["id"], canonical(opening)))
                db.execute("INSERT INTO exposure_data VALUES (?,?)", (body["dataset_sha256"], body["id"]))
                db.executemany("INSERT INTO exposures VALUES (?,?,?)", [(body["population"], v, body["id"]) for v in body["subjects"]])
            except sqlite3.IntegrityError as error: raise Conflict("Confirmation data or subjects already exposed") from error
            self._event(db, "confirmation_reserved", opening)
        return {"state": "reserved", "opening_id": body["id"]}

    def begin_confirmation(self, opening_id):
        with self.transaction() as db:
            row = self._row(db, "openings", "id", opening_id)
            if row["state"] != "reserved": raise Conflict("Opening has already been consumed")
            db.execute("UPDATE openings SET state='evaluating' WHERE id=?", (opening_id,))
            self._event(db, "confirmation_opened", {"id": opening_id})
        return json.loads(row["body"])

    def finish_confirmation(self, opening_id, aggregate, *, protocol_valid):
        from .contracts import finite
        if type(protocol_valid) is not bool or not isinstance(aggregate, dict) or not aggregate: raise ValueError("Typed aggregate confirmation required")
        with self.transaction() as db:
            row = self._row(db, "openings", "id", opening_id)
            if row["state"] != "evaluating": raise Conflict("Opening has no active evaluator")
            opening = verify(json.loads(row["body"]))
            fields = opening["released_fields"]
            if set(aggregate) != set(fields): raise ValueError("Release only the exact aggregate fields")
            for key, kind in fields.items():
                value = aggregate[key]
                if kind == "bool" and type(value) is not bool: raise ValueError("Aggregate type differs")
                elif kind == "int" and type(value) is not int: raise ValueError("Aggregate type differs")
                elif kind == "number": finite(value)
                elif kind not in ("bool", "int", "number"): raise ValueError("Invalid release schema")
            result = seal({"id": opening_id + "-result", "purpose": "fresh_confirmation", "protocol_valid": protocol_valid,
                           "qualification_sha256": opening["qualification_sha256"], "candidate_hashes": opening["candidate_hashes"],
                           "aggregate": aggregate, "opening_sha256": json.loads(row["body"])["sha256"]})
            db.execute("UPDATE openings SET state=? WHERE id=?", ("completed" if protocol_valid else "failed", opening_id))
            self._event(db, "confirmation_finished", result)
        return result

    def retry(self, unit_id, correction_sha256):
        hash_text(correction_sha256)
        with self.transaction() as db:
            unit = self._row(db, "units", "id", unit_id)
            round_row = self._row(db, "rounds", "id", unit["round"])
            plan = verify(json.loads(round_row["body"]))
            if round_row["state"] != "active" or unit["state"] not in ("crashed", "interrupted", "cancelled"):
                raise Conflict("Only reconciled procedural failure in an open round can recover")
            policy = plan.get("recovery_policy", {})
            maximum = integer(policy.get("max_attempts", 1), minimum=1)
            attempted = db.execute("SELECT COUNT(*) FROM attempts WHERE unit=?", (unit_id,)).fetchone()[0]
            if attempted >= maximum: raise Conflict("Declared recovery quota exhausted")
            remaining_cost = {"wall_ms": 0}
            for row in db.execute("SELECT body FROM units WHERE round=? AND state IN ('ready','claimed','authorized','running','uncertain')", (unit["round"],)):
                remaining_cost = add_costs(remaining_cost, verify(json.loads(row[0]))["costs"])
            charges = {"wall_ms": 0}
            for row in db.execute("SELECT r.body FROM receipts r JOIN attempts a ON a.id=r.attempt JOIN units u ON u.id=a.unit WHERE u.round=?", (unit["round"],)):
                charges = add_costs(charges, json.loads(row[0])["costs"])
            if not within(add_costs(charges, remaining_cost, verify(json.loads(unit["body"]))["costs"]), plan["budget"]):
                raise Conflict("Complete recovery cannot fit reviewed round budget")
            db.execute("UPDATE units SET state='ready' WHERE id=?", (unit_id,))
            self._event(db, "procedural_retry_authorized", {"unit": unit_id, "correction_sha256": correction_sha256})
        return {"state": "ready", "unit_id": unit_id}

    def acknowledge_events(self, through):
        integer(through)
        with self.transaction() as db:
            maximum = db.execute("SELECT MAX(seq) FROM events").fetchone()[0] or 0
            if through > maximum: raise Conflict("Cannot acknowledge unpublished events")
            db.execute("UPDATE outbox SET acknowledged=1 WHERE seq<=?", (through,))
        return {"through": through}

    def request_cancel(self, request):
        with self.transaction() as db:
            duplicate = self._duplicate(db, request["id"], request)
            if duplicate is not None: return duplicate
            row = self._row(db, "attempts", "id", request["attempt_id"])
            if row["state"] not in ACTIVE: raise Conflict("Cancellation target is not active")
            grant = json.loads(row["body"]); grant["cancel_requested"] = True
            db.execute("UPDATE attempts SET body=? WHERE id=?", (canonical(grant), row["id"]))
            self._event(db, "cancel_requested", {"attempt": row["id"]})
            return self._remember(db, request["id"], request, {"state": "cancel_requested", "attempt_id": row["id"]})

    @contextmanager
    def leadership(self):
        import fcntl
        import os
        with (self.directory / "coordinator.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.transaction() as db:
                prior = db.execute("SELECT epoch FROM leader WHERE id=1").fetchone()
                epoch = prior[0] + 1 if prior else 1
                db.execute("INSERT INTO leader VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET epoch=excluded.epoch,body=excluded.body",
                           (epoch, canonical({"pid": os.getpid(), "started_at": time.time()})))
                self._event(db, "leadership_acquired", {"epoch": epoch})
            self.active_epoch = epoch
            try: yield epoch
            finally:
                self.active_epoch = None
                fcntl.flock(lock, fcntl.LOCK_UN)

    def import_charges(self, record):
        identifier(record["id"]); identifier(record["project_id"])
        identifier(record["origin"]); identifier(record["origin_record_id"])
        hash_text(record["source_sha256"]); costs(record["costs"])
        origin_key = record["project_id"] + ":" + record["origin"] + ":" + record["origin_record_id"]
        with self.transaction() as db:
            project = self._row(db, "projects", "id", record["project_id"])
            old = db.execute("SELECT body FROM historical_charges WHERE origin_key=? OR id=?", (origin_key, record["id"])).fetchone()
            if old:
                prior = json.loads(old[0])
                if {k:v for k,v in prior.items() if k != "id"} != {k:v for k,v in record.items() if k != "id"}:
                    raise Conflict("Historical origin charge changed")
                return {"state": "already_imported", "origin_key": origin_key}
            accounting = self._accounting(db, record["project_id"])
            if not within(add_costs(accounting["charged"], accounting["reserved"], record["costs"]), json.loads(project["body"])["budget"]):
                raise Conflict("Historical charges exceed declared project budget")
            db.execute("INSERT INTO historical_charges VALUES (?,?,?,?)", (record["id"], record["project_id"], origin_key, canonical(record)))
            self._event(db, "historical_charges_imported", record)
        return {"state": "imported", "origin_key": origin_key}
