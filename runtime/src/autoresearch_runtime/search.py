"""Finite global barrier and qualified-positive frontier; arrival order never ranks."""
from __future__ import annotations
import json
from .contracts import canonical, identifier, seal, verify
from .global_store import Conflict


class Search:
    def __init__(self, store): self.store = store

    def qualify_unit(self, unit_id, qualification):
        q = verify(qualification)
        with self.store.transaction() as db:
            unit = self.store._row(db, "units", "id", unit_id)
            if unit["state"] != "completed": raise Conflict("Only completed units qualify")
            spec = json.loads(unit["body"])
            if q["candidate"]["candidate_sha256"] != spec["sha256"]: raise Conflict("Qualified candidate identity differs")
            from .qualification import qualify
            frozen = verify(spec)["qualification_policy"]
            if q["policy"] != frozen: raise Conflict("Qualification policy differs from admitted unit")
            calculated = qualify(q["candidate"], q["samples"], frozen)
            if calculated != qualification: raise Conflict("Qualification outcome differs from recomputed evidence")
            for key in ("benchmark_sha256", "evaluator_sha256", "environment_sha256"):
                if q["candidate"][key] != verify(spec)[key]: raise Conflict("Qualification comparison differs: " + key)
            receipt = db.execute("SELECT r.body FROM receipts r JOIN attempts a ON a.id=r.attempt WHERE a.unit=? ORDER BY a.generation DESC LIMIT 1", (unit_id,)).fetchone()
            if receipt is None or json.loads(receipt[0]).get("evidence_status") != "valid": raise Conflict("Qualified unit lacks valid execution evidence")
            from .contracts import digest
            if digest(json.loads(receipt[0])) not in q["receipt_hashes"]: raise Conflict("Qualification lacks this unit receipt")
            old = db.execute("SELECT body FROM qualifications WHERE unit=?", (unit_id,)).fetchone()
            if old and json.loads(old[0]) != qualification: raise Conflict("Qualification is immutable")
            db.execute("INSERT OR IGNORE INTO qualifications VALUES (?,?)", (unit_id, canonical(qualification)))
            self.store._event(db, "unit_qualified", {"unit": unit_id, "hash": qualification["sha256"]})
        return qualification

    def settle_dependencies(self, round_id):
        settled = []
        with self.store.transaction() as db:
            rows = db.execute("SELECT * FROM units WHERE round=?", (round_id,)).fetchall()
            states = {r["id"]: r["state"] for r in rows}
            for row in rows:
                if row["state"] != "ready": continue
                deps = verify(json.loads(row["body"])).get("requires", [])
                if any(states[d] in ("crashed", "interrupted", "cancelled", "invalid") for d in deps):
                    db.execute("UPDATE units SET state='invalid' WHERE id=?", (row["id"],))
                    self.store._event(db, "unit_prerequisite_invalid", {"unit": row["id"], "dependencies": deps})
                    settled.append(row["id"])
        return settled

    def seal_round(self, round_id):
        with self.store.transaction() as db:
            row = self.store._row(db, "rounds", "id", round_id)
            if row["state"] == "closed":
                return json.loads(self.store._row(db, "selections", "round", round_id)["body"])
            plan = verify(json.loads(row["body"]))
            units = db.execute("SELECT * FROM units WHERE round=?", (round_id,)).fetchall()
            unresolved = [u["id"] for u in units if u["state"] in ("ready", "claimed", "authorized", "running", "uncertain")]
            if unresolved: raise Conflict("Round has unresolved units: " + ",".join(unresolved))
            positives, inventory = [], []
            comparison_groups = set()
            for unit in units:
                spec = verify(json.loads(unit["body"]))
                qrow = db.execute("SELECT body FROM qualifications WHERE unit=?", (unit["id"],)).fetchone()
                q = verify(json.loads(qrow[0])) if qrow else None
                if unit["state"] == "completed" and q is None:
                    receipt_row = db.execute("SELECT r.body FROM receipts r JOIN attempts a ON a.id=r.attempt WHERE a.unit=? ORDER BY a.generation DESC LIMIT 1", (unit["id"],)).fetchone()
                    receipt = json.loads(receipt_row[0]) if receipt_row else {}
                    if receipt.get("scientific_pass") is not False:
                        raise Conflict("Required qualification not yet published")
                inventory.append({"unit_id": unit["id"], "state": unit["state"], "qualification_sha256": json.loads(qrow[0])["sha256"] if qrow else None})
                if q and q["positive"] is True:
                    comparison_groups.add(tuple(q["candidate"][key] for key in ("benchmark_sha256", "evaluator_sha256", "environment_sha256")))
                    positives.append({"unit_id": unit["id"], "candidate_id": spec["candidate_id"], "score": q["mean_improvement"],
                                      "qualification_sha256": json.loads(qrow[0])["sha256"], "mechanism": spec.get("mechanism", spec["candidate_id"])})
            if len(comparison_groups) > 1: raise Conflict("Heterogeneous positive cohorts require an explicit comparison protocol")
            positives.sort(key=lambda v: (-v["score"], v["unit_id"]))
            selected, seen = [], set()
            for item in positives:
                if plan.get("mechanism_diversity") and item["mechanism"] in seen: continue
                if item["candidate_id"] in {v["candidate_id"] for v in selected}: continue
                selected.append(item); seen.add(item["mechanism"])
                if len(selected) == plan["top_k"]: break
            record = seal({"id": round_id + "-selection", "round_id": round_id, "project_id": row["project"],
                           "round_sha256": json.loads(row["body"])["sha256"], "inventory": inventory, "selected": selected,
                           "state": "selected" if selected else "reorientation_required"})
            db.execute("INSERT INTO selections VALUES (?,?)", (round_id, canonical(record)))
            db.execute("UPDATE rounds SET state='closed' WHERE id=?", (round_id,))
            self.store._event(db, "round_sealed", record)
            return record
