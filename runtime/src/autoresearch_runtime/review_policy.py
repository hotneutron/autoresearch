"""Exact successor review binding; anonymous POC assurance is always explicit."""
from __future__ import annotations
import json
from .contracts import canonical, hash_text, identifier, seal, verify
from .global_store import Conflict


class ReviewPolicy:
    def __init__(self, store): self.store = store

    def submit(self, record):
        body = verify(record)
        identifier(body["id"]); identifier(body["round_id"])
        if body["decision"] not in ("approve", "reject", "changes_requested"): raise ValueError("Typed review decision required")
        hash_text(body["selection_sha256"]); hash_text(body["next_round_sha256"])
        value = seal({**body, "actor_assurance": "poc_anonymous", "independence_verified": False})
        with self.store.transaction() as db:
            row = self.store._row(db, "rounds", "id", body["round_id"])
            if row["project"] != body["project_id"]: raise Conflict("Review project differs")
            selection = self.store._row(db, "selections", "round", body["round_id"])
            if json.loads(selection["body"])["sha256"] != body["selection_sha256"]: raise Conflict("Review selection is stale")
            old = db.execute("SELECT body FROM reviews WHERE id=?", (body["id"],)).fetchone()
            if old:
                if json.loads(old[0]) != value: raise Conflict("Review is immutable")
                return value
            db.execute("INSERT INTO reviews VALUES (?,?,?,'queued')", (body["id"], body["round_id"], canonical(value)))
            self.store._event(db, "review_queued", value)
        return value

    def apply(self, review_id):
        with self.store.transaction() as db:
            row = self.store._row(db, "reviews", "id", review_id)
            body = verify(json.loads(row["body"]))
            if row["state"] == "applied": return {"state": "applied", "review_id": review_id}
            round_row = self.store._row(db, "rounds", "id", row["round"])
            if round_row["state"] != "closed": raise Conflict("Round boundary not complete")
            if self.store._row(db, "projects", "id", round_row["project"])["paused"]: raise Conflict("Project stop/hold prevents review application")
            selection = json.loads(self.store._row(db, "selections", "round", row["round"])["body"])
            if selection["sha256"] != body["selection_sha256"]: raise Conflict("Review selection changed")
            if body["decision"] != "approve": return {"state": body["decision"], "review_id": review_id}
            db.execute("UPDATE reviews SET state='applied' WHERE id=?", (review_id,))
            self.store._event(db, "review_applied", {"id": review_id, "round_id": row["round"], "next_round_sha256": body["next_round_sha256"]})
            return {"state": "applied", "review_id": review_id, "actor_assurance": "poc_anonymous"}
