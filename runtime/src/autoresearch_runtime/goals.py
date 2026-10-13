"""Goal-level steering above immutable campaigns, with durable aggregate admission.

The project agent supplies scientific meaning. This ledger enforces bindings,
scope, prospective review checkpoints and accounting, not scientific relevance.
Revision History: 2026-10-12 — initial goal/proposal/assessment/admission ledger.
2026-10-13 — require outer-loop reorientation after a terminal campaign checkpoint.
2026-10-13 — require context-changing rebrainstorm after a no-viable inventory.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import json
import math
from pathlib import Path
import sqlite3

from .protocol import sha256
from .review import Conflict, digest, encode, identifier, now, string

ACTIONS = {"CONTINUE", "PIVOT", "DEFER", "STOP", "ASK_HUMAN"}
OUTCOMES = {"supported", "unsupported", "inconclusive", "invalid"}
TERMINAL = {"completed", "crashed", "interrupted", "blocked"}
CANDIDATE_STATES = {"viable", "rejected", "blocked"}


def fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) != set(required) | (set(value) & set(optional)):
        raise ValueError("Goal record has missing or unknown fields")


def number(value, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("Expected a finite nonnegative allowance")
    return value


def hashed(value):
    return digest(encode(value).encode())


def hash_text(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError("Expected a SHA-256 binding")


def evidence(items, *, empty=False):
    if not isinstance(items, list) or len(items) > 30 or (not items and not empty):
        raise ValueError("Select explicit released evidence")
    for item in items:
        fields(item, {"path", "sha256"})
        hash_text(item["sha256"])
        path = Path(item["path"])
        if not path.is_absolute() or sha256(path) != item["sha256"]:
            raise Conflict("Released goal evidence is missing or changed")


def texts(items, *, empty=False):
    if not isinstance(items, list) or len(items) > 30 or (not items and not empty):
        raise ValueError("Expected explicit text items")
    for item in items:
        string(item, 2000)


def base(record, required):
    fields(record, {"schema_version", "id", "prompt_verbatim"} | set(required))
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("Unsupported goal record schema")
    identifier(record["id"])
    string(record["prompt_verbatim"], 50000)


def contract_hash(contract):
    """Exclude only the references that would otherwise form a circular hash."""
    value = copy.deepcopy(contract)
    value.pop("goal_gate", None)
    return hashed(value)


def validate_gate(gate):
    fields(gate, {"ledger", "goal_hash", "proposal_id", "proposal_hash", "assessment_id", "assessment_hash"})
    if not Path(gate["ledger"]).is_absolute():
        raise ValueError("Goal ledger path must be absolute")
    for key in ("goal_hash", "proposal_hash", "assessment_hash"):
        hash_text(gate[key])
    for key in ("proposal_id", "assessment_id"):
        identifier(gate[key])


class GoalLedger:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "goals.sqlite3"
        with self.connect(write=True) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise Conflict("Unsupported goal ledger schema")
            db.executescript("""
              CREATE TABLE IF NOT EXISTS records (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                id TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL,
                UNIQUE(kind,id));
              CREATE TABLE IF NOT EXISTS admissions (
                campaign TEXT PRIMARY KEY, directory TEXT UNIQUE NOT NULL,
                proposal TEXT NOT NULL, assessment TEXT NOT NULL, goal TEXT NOT NULL,
                contract_hash TEXT NOT NULL, reserved REAL NOT NULL, charged REAL NOT NULL DEFAULT 0,
                state TEXT NOT NULL, checkpoint TEXT, created TEXT NOT NULL);
            """)
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self, write=False):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
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

    @staticmethod
    def put(db, kind, record):
        body, key = encode(record), hashed(record)
        old = db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, record["id"])).fetchone()
        if old:
            if old["hash"] != key:
                raise Conflict("Goal records are immutable; use a new ID/revision")
            return {"id": old["id"], "hash": old["hash"], "duplicate": True}
        db.execute("INSERT INTO records(kind,id,hash,body,created) VALUES (?,?,?,?,?)",
                   (kind, record["id"], key, body, now()))
        return {"id": record["id"], "hash": key, "duplicate": False}

    @staticmethod
    def record(db, kind, record_id):
        row = db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, record_id)).fetchone()
        if not row:
            raise Conflict(f"Missing {kind} record")
        if hashed(json.loads(row["body"])) != row["hash"]:
            raise Conflict("Goal ledger record changed")
        return row, json.loads(row["body"])

    @staticmethod
    def latest_goal(db):
        row = db.execute("SELECT id FROM records WHERE kind='goal' ORDER BY seq DESC LIMIT 1").fetchone()
        if not row:
            raise Conflict("Publish the original project goal first")
        return GoalLedger.record(db, "goal", row["id"])

    @staticmethod
    def path_state(db):
        """Return the current terminal-checkpoint/reorientation relationship.

        A later goal revision is itself a material reorientation and supersedes an
        older candidate inventory. Proposal/assessment records deliberately do not
        affect this state because they are not goal-context events.
        """
        checkpoint = db.execute(
            "SELECT seq,id,hash,body FROM records WHERE kind='checkpoint' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        reorientation = db.execute(
            "SELECT seq,kind,id,hash,body FROM records WHERE kind IN ('reorientation','rebrainstorm') ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        goal = db.execute(
            "SELECT seq,id FROM records WHERE kind='goal' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if not checkpoint or (goal and goal["seq"] > checkpoint["seq"]):
            return {"checkpoint": None, "reorientation": None, "pending": False}
        cp = {**dict(checkpoint), "body": json.loads(checkpoint["body"])}
        if not reorientation or reorientation["seq"] < checkpoint["seq"]:
            return {"checkpoint": cp, "reorientation": None, "pending": True}
        record = {**dict(reorientation), "body": json.loads(reorientation["body"])}
        return {"checkpoint": cp, "reorientation": record, "pending": False}

    def anchor(self, record):
        base(record, {"revision", "project_id", "goal", "claims", "non_goals", "allowed_scopes", "budget", "drift_policy"})
        identifier(record["project_id"])
        string(record["goal"], 2000)
        if type(record["revision"]) is not int or record["revision"] < 1:
            raise ValueError("Goal revision must be a positive integer")
        texts(record["non_goals"])
        texts(record["allowed_scopes"])
        if not isinstance(record["claims"], list) or not 1 <= len(record["claims"]) <= 30:
            raise ValueError("Explicit parent claims required")
        seen = set()
        for claim in record["claims"]:
            fields(claim, {"id", "question", "success_evidence"})
            identifier(claim["id"]); string(claim["question"], 2000); string(claim["success_evidence"], 2000)
            if claim["id"] in seen:
                raise ValueError("Duplicate parent claim")
            seen.add(claim["id"])
        budget = record["budget"]
        fields(budget, {"max_seconds", "imported_seconds", "import_evidence"})
        number(budget["max_seconds"], positive=True); number(budget["imported_seconds"])
        evidence(budget["import_evidence"], empty=budget["imported_seconds"] == 0)
        if budget["imported_seconds"] > budget["max_seconds"]:
            raise ValueError("Imported charges exceed aggregate cap")
        policy = record["drift_policy"]
        fields(policy, {"max_diagnostic_campaigns", "max_diagnostic_seconds", "max_unchanged_checkpoints"})
        for key in ("max_diagnostic_campaigns", "max_unchanged_checkpoints"):
            if type(policy[key]) is not int or policy[key] < 1:
                raise ValueError("Prospective checkpoint count must be positive")
        number(policy["max_diagnostic_seconds"], positive=True)
        with self.connect(write=True) as db:
            old = db.execute("SELECT hash FROM records WHERE kind='goal' AND id=?", (record["id"],)).fetchone()
            if old:
                return self.put(db, "goal", record)
            prior = db.execute("SELECT id FROM records WHERE kind='goal' ORDER BY seq DESC LIMIT 1").fetchone()
            if prior:
                _, goal = self.record(db, "goal", prior["id"])
                if record["project_id"] != goal["project_id"] or record["revision"] != goal["revision"] + 1:
                    raise Conflict("Goal project is fixed and revisions must be consecutive")
                for key in ("imported_seconds", "import_evidence"):
                    if budget[key] != goal["budget"][key]:
                        raise Conflict("Historical charges cannot be reset or reimported")
                accounts = self.context(db)["accounting"]
                if budget["max_seconds"] < accounts["spent_seconds"] + accounts["reserved_seconds"]:
                    raise Conflict("New cap cannot erase committed charges/reservations")
            elif record["revision"] != 1:
                raise Conflict("Initial goal must have revision1")
            return self.put(db, "goal", record)

    def context(self, db):
        goal_row, goal = self.latest_goal(db)
        admissions = [dict(r) for r in db.execute("SELECT * FROM admissions ORDER BY created,campaign")]
        rows = [dict(r) for r in db.execute("SELECT seq,kind,id,hash FROM records ORDER BY seq")]
        # Assessment/proposal authoring does not itself change research context.
        events = [r for r in rows if r["kind"] in {"goal", "control", "checkpoint", "reorientation", "rebrainstorm"}]
        spent = goal["budget"]["imported_seconds"] + sum(a["charged"] for a in admissions)
        reserved = sum(a["reserved"] for a in admissions if a["state"] == "active")
        checkpoints = []
        for row in db.execute("SELECT id FROM records WHERE kind='checkpoint' ORDER BY seq"):
            _, cp = self.record(db, "checkpoint", row["id"])
            checkpoints.append(cp)
        diagnostics = [cp for cp in checkpoints if cp["proposal_kind"] == "diagnostic"]
        unchanged = 0
        for cp in reversed(checkpoints):
            if cp["decision_changed"] or cp["blocker_changed"]:
                break
            unchanged += 1
        controls = [json.loads(r[0]) for r in db.execute("SELECT body FROM records WHERE kind='control' ORDER BY seq")]
        stopped = False
        explicit = []
        for item in controls:
            if item["action"] == "STOP":
                stopped = True
            elif item["action"] == "RESUME":
                stopped = False
            if item["action"] in {"REVIEW", "STOP", "RESUME"}:
                explicit.append("control:" + item["id"])
        # Controls stay visible in every fresh assessment; STOP is persistent
        # until an explicit RESUME. Reassessment never erases old charges.
        policy = goal["drift_policy"]
        triggers = list(explicit)
        if len(diagnostics) >= policy["max_diagnostic_campaigns"]:
            triggers.append("diagnostic_campaign_limit")
        if sum(cp["charged_seconds"] for cp in diagnostics) >= policy["max_diagnostic_seconds"]:
            triggers.append("diagnostic_runtime_limit")
        if unchanged >= policy["max_unchanged_checkpoints"]:
            triggers.append("unchanged_blocker_limit")
        path = self.path_state(db)
        if path["pending"]:
            triggers.append("outer_loop_reorientation_required")
        elif path["reorientation"]:
            record = path["reorientation"]["body"]
            if record["selected_candidate"] is not None:
                prefix = "reorientation:"
            elif path["reorientation"]["kind"] == "reorientation":
                prefix = "rebrainstorm_required:"
            else:
                prefix = "awaiting_context_change:"
            triggers.append(prefix + record["id"])
        result = {"goal_hash": goal_row["hash"], "goal": goal, "events": events,
                  "accounting": {"spent_seconds": spent, "reserved_seconds": reserved,
                    "max_seconds": goal["budget"]["max_seconds"],
                    "remaining_seconds": goal["budget"]["max_seconds"] - spent - reserved},
                  "active_campaigns": [a["campaign"] for a in admissions if a["state"] == "active"],
                  "triggers": sorted(set(triggers)), "stopped": stopped,
                  "diagnostic_campaigns": len(diagnostics), "unchanged_checkpoints": unchanged,
                  "admissions": admissions}
        result["reorientation"] = path["reorientation"]["body"] if path["reorientation"] else None
        result["reorientation_checkpoint"] = (
            {key: path["checkpoint"][key] for key in ("id", "hash")} if path["checkpoint"] else None
        )
        result["context_hash"] = hashed(result)
        return result

    def reorient(self, record):
        """Record the public outer-loop candidate inventory after a checkpoint.

        The project agent authors scientific candidates and concise rationales.
        This ledger validates bindings, scope and complete budgets; it does not
        generate ideas, infer private reasoning or claim independent review.
        """
        base(record, {"goal_hash", "context_hash", "checkpoint_id", "checkpoint_hash",
                      "unresolved_claim", "exhausted_path", "candidates",
                      "selected_candidate", "no_viable_reason", "next_checkpoint"})
        for key in ("goal_hash", "context_hash", "checkpoint_hash"):
            hash_text(record[key])
        identifier(record["checkpoint_id"])
        for key in ("unresolved_claim", "exhausted_path", "next_checkpoint"):
            string(record[key], 5000 if key == "exhausted_path" else 2000)
        if not isinstance(record["candidates"], list) or not 1 <= len(record["candidates"]) <= 10:
            raise ValueError("Reorientation requires 1–10 explicit candidates")
        seen = set(); viable = {}
        for candidate in record["candidates"]:
            fields(candidate, {"id", "proposal_id", "parent_claim", "scope", "kind",
                               "decision", "endpoint_relevance", "novelty", "status",
                               "reason", "budget", "evidence"})
            identifier(candidate["id"]); identifier(candidate["proposal_id"]); identifier(candidate["parent_claim"])
            if candidate["id"] in seen:
                raise ValueError("Duplicate reorientation candidate")
            seen.add(candidate["id"])
            if candidate["kind"] not in {"diagnostic", "modeling", "evidence"}:
                raise ValueError("Unknown candidate proposal kind")
            if candidate["status"] not in CANDIDATE_STATES:
                raise ValueError("Unknown reorientation candidate status")
            for key in ("scope", "decision", "endpoint_relevance", "novelty", "reason"):
                string(candidate[key], 2000)
            fields(candidate["budget"], {"campaign_seconds", "downstream_seconds"})
            number(candidate["budget"]["campaign_seconds"], positive=True)
            number(candidate["budget"]["downstream_seconds"])
            evidence(candidate["evidence"])
            if candidate["status"] == "viable":
                viable[candidate["id"]] = candidate
        selected = record["selected_candidate"]
        if viable:
            if selected not in viable:
                raise ValueError("Select exactly one viable reorientation candidate")
            if record["no_viable_reason"] is not None:
                raise ValueError("A selected viable candidate cannot claim no viable path")
        else:
            if selected is not None:
                raise ValueError("Cannot select a rejected or blocked candidate")
            string(record["no_viable_reason"], 5000)
        with self.connect(write=True) as db:
            old = db.execute(
                "SELECT 1 FROM records WHERE kind='reorientation' AND id=?", (record["id"],)
            ).fetchone()
            if old:
                return self.put(db, "reorientation", record)
            context = self.context(db)
            path = self.path_state(db)
            if context["goal_hash"] != record["goal_hash"] or context["context_hash"] != record["context_hash"]:
                raise Conflict("Reorientation context is stale")
            if context["active_campaigns"]:
                raise Conflict("Finish the active campaign before outer-loop reorientation")
            if not path["pending"] or not path["checkpoint"]:
                raise Conflict("No unreoriented terminal campaign checkpoint")
            if (path["checkpoint"]["id"] != record["checkpoint_id"]
                    or path["checkpoint"]["hash"] != record["checkpoint_hash"]):
                raise Conflict("Reorientation does not bind the latest checkpoint")
            goal = context["goal"]
            claims = {item["id"] for item in goal["claims"]}
            for candidate in viable.values():
                if candidate["parent_claim"] not in claims or candidate["scope"] not in goal["allowed_scopes"]:
                    raise Conflict("Viable candidate exceeds current goal claim/scope")
                if sum(candidate["budget"].values()) > context["accounting"]["remaining_seconds"]:
                    raise Conflict("Viable candidate complete route exceeds aggregate remainder")
            return self.put(db, "reorientation", record)

    def rebrainstorm(self, record):
        """Re-open candidate generation only after an explicit context change.

        This prevents an immediate loop over the same rejected slate. A selected
        candidate binds the next proposal exactly like a first reorientation. If
        none is viable, explicit unblock conditions become durable state.
        """
        base(record, {"goal_hash", "context_hash", "parent_id", "parent_hash", "round",
                      "unresolved_claim", "novelty_basis", "candidates",
                      "selected_candidate", "no_viable_reason", "awaiting_context_change",
                      "next_checkpoint"})
        for key in ("goal_hash", "context_hash", "parent_hash"):
            hash_text(record[key])
        identifier(record["parent_id"])
        if type(record["round"]) is not int or record["round"] < 1:
            raise ValueError("Rebrainstorm round must be positive")
        string(record["unresolved_claim"], 2000); string(record["next_checkpoint"], 2000)
        novelty = record["novelty_basis"]
        if not isinstance(novelty, list) or not 1 <= len(novelty) <= 10:
            raise ValueError("Rebrainstorm requires an explicit context change")
        for item in novelty:
            fields(item, {"kind", "description", "evidence"})
            if item["kind"] not in {"new_evidence", "authority_change", "infrastructure_change",
                                    "objective_change", "budget_change", "external_coordination"}:
                raise ValueError("Unknown rebrainstorm context-change kind")
            string(item["description"], 2000); evidence(item["evidence"])
        if not isinstance(record["candidates"], list) or not 1 <= len(record["candidates"]) <= 10:
            raise ValueError("Rebrainstorm requires 1–10 explicit candidates")
        seen=set();viable={}
        for candidate in record["candidates"]:
            fields(candidate, {"id", "proposal_id", "parent_claim", "scope", "kind",
                               "decision", "endpoint_relevance", "novelty", "status",
                               "reason", "budget", "evidence"})
            identifier(candidate["id"]);identifier(candidate["proposal_id"]);identifier(candidate["parent_claim"])
            if candidate["id"] in seen:raise ValueError("Duplicate rebrainstorm candidate")
            seen.add(candidate["id"])
            if candidate["kind"] not in {"diagnostic", "modeling", "evidence"}:raise ValueError("Unknown candidate proposal kind")
            if candidate["status"] not in CANDIDATE_STATES:raise ValueError("Unknown rebrainstorm candidate status")
            for key in ("scope", "decision", "endpoint_relevance", "novelty", "reason"):string(candidate[key],2000)
            fields(candidate["budget"], {"campaign_seconds", "downstream_seconds"});number(candidate["budget"]["campaign_seconds"],positive=True);number(candidate["budget"]["downstream_seconds"]);evidence(candidate["evidence"])
            if candidate["status"]=="viable":viable[candidate["id"]]=candidate
        selected=record["selected_candidate"]
        if viable:
            if selected not in viable:raise ValueError("Select exactly one viable rebrainstorm candidate")
            if record["no_viable_reason"] is not None or record["awaiting_context_change"]:
                raise ValueError("Selected candidate cannot await another context change")
        else:
            if selected is not None:raise ValueError("Cannot select a rejected or blocked candidate")
            string(record["no_viable_reason"],5000)
            waiting=record["awaiting_context_change"]
            if not isinstance(waiting,list) or not 1<=len(waiting)<=10:raise ValueError("No-viable rebrainstorm needs explicit unblock conditions")
            for condition in waiting:string(condition,1000)
        with self.connect(write=True) as db:
            old=db.execute("SELECT 1 FROM records WHERE kind='rebrainstorm' AND id=?",(record["id"],)).fetchone()
            if old:return self.put(db,"rebrainstorm",record)
            context=self.context(db);path=self.path_state(db)
            if context["goal_hash"]!=record["goal_hash"] or context["context_hash"]!=record["context_hash"]:raise Conflict("Rebrainstorm context is stale")
            if context["active_campaigns"]:raise Conflict("Finish the active campaign before rebrainstorm")
            parent=path["reorientation"]
            if not parent or parent["body"]["selected_candidate"] is not None:raise Conflict("Rebrainstorm requires a no-viable parent inventory")
            if parent["id"]!=record["parent_id"] or parent["hash"]!=record["parent_hash"]:raise Conflict("Rebrainstorm does not bind current no-viable inventory")
            if parent["kind"]=="rebrainstorm" and record["round"]!=parent["body"]["round"]+1:raise Conflict("Rebrainstorm rounds must be consecutive")
            if parent["kind"]=="reorientation" and record["round"]!=1:raise Conflict("Initial rebrainstorm round must be1")
            goal=context["goal"];claims={item["id"] for item in goal["claims"]}
            for candidate in viable.values():
                if candidate["parent_claim"] not in claims or candidate["scope"] not in goal["allowed_scopes"]:raise Conflict("Viable candidate exceeds current goal claim/scope")
                if sum(candidate["budget"].values())>context["accounting"]["remaining_seconds"]:raise Conflict("Viable candidate complete route exceeds aggregate remainder")
            return self.put(db,"rebrainstorm",record)

    def proposal(self, record):
        base(record, {"goal_hash", "campaign_id", "contract_sha256", "parent_claim", "scope", "kind", "decision", "blocker", "endpoint_relevance", "outcomes", "alternatives", "budget"})
        hash_text(record["goal_hash"]); hash_text(record["contract_sha256"])
        identifier(record["campaign_id"]); identifier(record["parent_claim"])
        for key in ("decision", "endpoint_relevance", "scope"):
            string(record[key], 2000)
        if record["kind"] not in {"diagnostic", "modeling", "evidence"}:
            raise ValueError("Unknown proposal kind")
        fields(record["blocker"], {"description", "evidence"})
        string(record["blocker"]["description"], 2000); evidence(record["blocker"]["evidence"])
        fields(record["outcomes"], OUTCOMES)
        for outcome in record["outcomes"].values():
            fields(outcome, {"observation", "decision", "action"})
            for text in outcome.values():
                string(text, 2000)
        if not isinstance(record["alternatives"], list) or not 1 <= len(record["alternatives"]) <= 10:
            raise ValueError("Compare alternatives including no new acquisition")
        for option in record["alternatives"]:
            fields(option, {"option", "reason"})
            string(option["option"], 2000); string(option["reason"], 2000)
        fields(record["budget"], {"campaign_seconds", "downstream_seconds"})
        number(record["budget"]["campaign_seconds"], positive=True); number(record["budget"]["downstream_seconds"])
        with self.connect(write=True) as db:
            old = db.execute("SELECT 1 FROM records WHERE kind='proposal' AND id=?", (record["id"],)).fetchone()
            if not old:
                row, goal = self.latest_goal(db)
                if row["hash"] != record["goal_hash"]:
                    raise Conflict("Proposal refers to a superseded goal")
                if record["parent_claim"] not in {c["id"] for c in goal["claims"]} or record["scope"] not in goal["allowed_scopes"]:
                    raise Conflict("Proposal exceeds goal claim/scope authorization")
                path = self.path_state(db)
                if path["pending"]:
                    raise Conflict("Publish outer-loop reorientation before a successor proposal")
                if path["reorientation"]:
                    reorientation = path["reorientation"]["body"]
                    selected_id = reorientation["selected_candidate"]
                    if selected_id is None:
                        raise Conflict("Reorientation found no viable successor proposal")
                    selected = next(item for item in reorientation["candidates"] if item["id"] == selected_id)
                    bindings = {
                        "id": "proposal_id", "parent_claim": "parent_claim", "scope": "scope",
                        "kind": "kind", "decision": "decision", "endpoint_relevance": "endpoint_relevance",
                    }
                    for proposal_key, candidate_key in bindings.items():
                        if record[proposal_key] != selected[candidate_key]:
                            raise Conflict("Proposal differs from selected reorientation candidate")
                    if record["budget"] != selected["budget"]:
                        raise Conflict("Proposal budget differs from selected reorientation candidate")
            return self.put(db, "proposal", record)

    def control(self, record):
        base(record, {"action", "reason"})
        if record["action"] not in {"REVIEW", "STOP", "RESUME"}:
            raise ValueError("Goal control must be REVIEW, STOP or explicit RESUME")
        string(record["reason"], 2000)
        with self.connect(write=True) as db:
            self.latest_goal(db)
            return self.put(db, "control", record)

    def assess(self, record):
        base(record, {"proposal_id", "proposal_hash", "goal_hash", "context_hash", "action", "reason", "trigger_dispositions", "evidence", "next_checkpoint"})
        identifier(record["proposal_id"])
        for key in ("proposal_hash", "goal_hash", "context_hash"):
            hash_text(record[key])
        if record["action"] not in ACTIONS:
            raise ValueError("Unknown goal steering action")
        string(record["reason"], 5000); string(record["next_checkpoint"], 2000)
        evidence(record["evidence"])
        if not isinstance(record["trigger_dispositions"], list):
            raise ValueError("Address prospective review triggers")
        addressed = set()
        for item in record["trigger_dispositions"]:
            fields(item, {"trigger", "reason"})
            string(item["trigger"]); string(item["reason"], 2000)
            if item["trigger"] in addressed:
                raise ValueError("Duplicate trigger disposition")
            addressed.add(item["trigger"])
        with self.connect(write=True) as db:
            old = db.execute("SELECT 1 FROM records WHERE kind='assessment' AND id=?", (record["id"],)).fetchone()
            if old:
                return self.put(db, "assessment", record)
            context = self.context(db)
            row, proposal = self.record(db, "proposal", record["proposal_id"])
            if row["hash"] != record["proposal_hash"] or record["goal_hash"] != proposal["goal_hash"]:
                raise Conflict("Assessment does not bind its exact goal/proposal")
            if record["goal_hash"] != context["goal_hash"] or record["context_hash"] != context["context_hash"]:
                raise Conflict("Goal assessment context is stale")
            if record["action"] in {"CONTINUE", "PIVOT"}:
                if context["stopped"] or context["active_campaigns"]:
                    raise Conflict("Explicit stop or unresolved campaign blocks continuation")
                if set(context["triggers"]) - addressed:
                    raise Conflict("Unaddressed goal drift/intervention trigger")
                if sum(proposal["budget"].values()) > context["accounting"]["remaining_seconds"]:
                    raise Conflict("Complete route to deliverable exceeds aggregate remainder")
            return self.put(db, "assessment", record)

    def _gate(self, db, contract, directory):
        gate = contract["goal_gate"]
        validate_gate(gate)
        if Path(gate["ledger"]).resolve() != self.directory:
            raise Conflict("Goal gate points at a different ledger")
        key = contract_hash(contract)
        admitted = db.execute("SELECT * FROM admissions WHERE campaign=?", (contract["id"],)).fetchone()
        if admitted:
            if admitted["directory"] != str(Path(directory).resolve()) or admitted["contract_hash"] != key or admitted["proposal"] != gate["proposal_hash"] or admitted["assessment"] != gate["assessment_hash"] or admitted["goal"] != gate["goal_hash"]:
                raise Conflict("Campaign admission identity changed; no replacement/retry")
            if admitted["state"] != "active":
                raise Conflict("Campaign checkpoint is closed; no re-admission")
            return dict(admitted), None
        context = self.context(db)
        row, proposal = self.record(db, "proposal", gate["proposal_id"])
        review_row, assessment = self.record(db, "assessment", gate["assessment_id"])
        if row["hash"] != gate["proposal_hash"] or review_row["hash"] != gate["assessment_hash"]:
            raise Conflict("Goal gate references changed proposal/assessment")
        if gate["goal_hash"] != proposal["goal_hash"] or gate["goal_hash"] != assessment["goal_hash"] or gate["goal_hash"] != context["goal_hash"]:
            raise Conflict("Goal gate is superseded")
        if assessment["proposal_hash"] != row["hash"] or assessment["proposal_id"] != proposal["id"] or assessment["context_hash"] != context["context_hash"]:
            raise Conflict("Goal admission assessment is stale")
        if assessment["action"] not in {"CONTINUE", "PIVOT"} or context["stopped"] or context["active_campaigns"]:
            raise Conflict("Goal review required before another campaign")
        evidence(proposal["blocker"]["evidence"]); evidence(assessment["evidence"])
        if proposal["campaign_id"] != contract["id"] or proposal["contract_sha256"] != key or contract.get("project_id") != context["goal"]["project_id"]:
            raise Conflict("Proposal is not bound to this project/campaign contract")
        if contract["budget"]["max_seconds"] != proposal["budget"]["campaign_seconds"]:
            raise Conflict("Campaign allowance differs from the reviewed complete proposal")
        if sum(t["timeout_seconds"] for t in contract["tasks"].values()) > proposal["budget"]["campaign_seconds"]:
            raise Conflict("Goal allowance cannot cover all declared complete units")
        if sum(proposal["budget"].values()) > context["accounting"]["remaining_seconds"]:
            raise Conflict("Complete goal route does not fit aggregate budget")
        return None, proposal

    def gate(self, contract, directory):
        with self.connect() as db:
            try:
                admitted, _ = self._gate(db, contract, directory)
                return {"allowed": True, "state": "admitted" if admitted else "ready", "reason": "Complete design admitted" if admitted else "Exact goal assessment permits new admission"}
            except (OSError, ValueError, KeyError, TypeError) as error:
                return {"allowed": False, "state": "goal_review_required", "reason": str(error)}

    def admit(self, contract, directory):
        """Reserve once before first launch. A later intervention affects successors."""
        with self.connect(write=True) as db:
            admitted, proposal = self._gate(db, contract, directory)
            if admitted:
                return admitted
            gate = contract["goal_gate"]
            db.execute("INSERT INTO admissions(campaign,directory,proposal,assessment,goal,contract_hash,reserved,state,created) VALUES (?,?,?,?,?,?,?,?,?)",
                (contract["id"], str(Path(directory).resolve()), gate["proposal_hash"], gate["assessment_hash"], gate["goal_hash"], contract_hash(contract), proposal["budget"]["campaign_seconds"], "active", now()))
            return dict(db.execute("SELECT * FROM admissions WHERE campaign=?", (contract["id"],)).fetchone())

    def checkpoint(self, record):
        base(record, {"campaign_id", "outcome", "decision_changed", "blocker_changed", "explanation", "evidence"})
        identifier(record["campaign_id"])
        if record["outcome"] not in OUTCOMES or type(record["decision_changed"]) is not bool or type(record["blocker_changed"]) is not bool:
            raise ValueError("Checkpoint requires an explicit outcome and progress report")
        string(record["explanation"], 5000); evidence(record["evidence"])
        with self.connect(write=True) as db:
            admission = db.execute("SELECT * FROM admissions WHERE campaign=?", (record["campaign_id"],)).fetchone()
            if not admission:
                raise Conflict("No campaign admission to settle")
            if admission["checkpoint"]:
                _, old = self.record(db, "checkpoint", admission["checkpoint"])
                supplied = {k: old[k] for k in record}
                if supplied != record:
                    raise Conflict("Campaign checkpoint immutable; no replacement attempt")
                row, _ = self.record(db, "checkpoint", admission["checkpoint"])
                return {"id": row["id"], "hash": row["hash"], "duplicate": True}
            directory = Path(admission["directory"])
            database = directory / "inbox.sqlite3"
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as runtime:
                runtime.row_factory = sqlite3.Row
                config = json.loads(runtime.execute("SELECT body FROM runtime_config WHERE id=1").fetchone()[0])
                units = [dict(r) for r in runtime.execute("SELECT * FROM units")]
            from .protocol import runtime_identity
            if config["runtime"] != runtime_identity() or contract_hash(config["contract"]) != admission["contract_hash"]:
                raise Conflict("Settle with the exact pinned campaign runtime/contract")
            tasks = config["contract"]["tasks"]
            if not units or any(u["state"] not in TERMINAL for u in units):
                raise Conflict("Complete campaign boundary not reached; active/queued/unresolved work")
            receipts, charged, failed = [], 0, False
            from .worker import alive
            for unit in units:
                if unit["task_id"] not in tasks:
                    raise Conflict("Unknown campaign unit")
                root = directory / "trials" / unit["id"]
                for identity in ("worker.json", "process.json"):
                    path = root / identity
                    if path.exists() and alive(json.loads(path.read_text())):
                        raise Conflict("Live campaign process prevents settlement")
                if unit["state"] == "blocked":
                    failed = True
                    if not unit["result"] or json.loads(unit["result"]).get("scientific_pass") is not False:
                        raise Conflict("Blocked unit lacks fixed failure result")
                    continue
                path = root / "receipt.json"
                receipt = json.loads(path.read_text())
                if receipt != json.loads(unit["result"]) or receipt["execution_status"] != unit["state"]:
                    raise Conflict("Runtime receipt differs from reconciled unit")
                number(receipt["wall_seconds"])
                charged += receipt["wall_seconds"]
                failed |= receipt.get("scientific_pass") is not True
                receipts.append({"path": str(path), "sha256": sha256(path)})
            if set(tasks) != {u["task_id"] for u in units} and not failed:
                raise Conflict("All declared units must finish; no selective early checkpoint")
            if failed and record["outcome"] != "invalid":
                raise Conflict("Failed complete unit cannot count as valid scientific progress")
            proposal_row = db.execute("SELECT id FROM records WHERE kind='proposal' AND hash=?", (admission["proposal"],)).fetchone()
            _, proposal = self.record(db, "proposal", proposal_row["id"])
            full = {**record, "charged_seconds": charged, "receipts": receipts, "proposal_kind": proposal["kind"], "proposal_hash": admission["proposal"], "goal_hash": admission["goal"]}
            result = self.put(db, "checkpoint", full)
            db.execute("UPDATE admissions SET charged=?,reserved=0,state='closed',checkpoint=? WHERE campaign=?", (charged, record["id"], record["campaign_id"]))
            return {**result, "charged_seconds": charged}

    def snapshot(self):
        with self.connect() as db:
            context = self.context(db)
            recent = [dict(r) for r in db.execute("SELECT kind,id,hash,body,created FROM records ORDER BY seq DESC LIMIT 20")]
        context["records"] = [{**r, "body": json.loads(r["body"])} for r in recent]
        ready = next((r for r in context["records"] if r["kind"] == "assessment"
                      and r["body"]["context_hash"] == context["context_hash"]
                      and r["body"]["goal_hash"] == context["goal_hash"]
                      and r["body"]["action"] in {"CONTINUE", "PIVOT"}), None)
        path = context["reorientation"]
        pending = "outer_loop_reorientation_required" in context["triggers"]
        context["state"] = (
            "stopped" if context["stopped"] else
            "active_campaign" if context["active_campaigns"] else
            "ready_for_admission" if ready else
            "reorientation_required" if pending else
            "rebrainstorm_required" if path and path["selected_candidate"] is None and any(t.startswith("rebrainstorm_required:") for t in context["triggers"]) else
            "awaiting_context_change" if path and path["selected_candidate"] is None else
            "candidate_selected" if path else
            "goal_review_required"
        )
        context["reason"] = (
            "Explicit stop; requires resume and fresh assessment" if context["stopped"] else
            "Admitted design may finish; next campaign requires fresh assessment" if context["active_campaigns"] else
            "Exact proposal has a fresh goal assessment; dispatch still checks all bindings and gates" if ready else
            "Terminal campaign checkpoint requires an evidence-backed outer-loop candidate inventory" if pending else
            "No viable candidate in the current slate; publish a context-changing rebrainstorm" if path and path["selected_candidate"] is None and any(t.startswith("rebrainstorm_required:") for t in context["triggers"]) else
            path["no_viable_reason"] if path and path["selected_candidate"] is None else
            "Outer loop selected a viable candidate; publish its exact bound proposal and fresh assessment" if path else
            "Bind the next proposal to a fresh goal assessment before admission"
        )
        context["generated"] = now()
        return context
