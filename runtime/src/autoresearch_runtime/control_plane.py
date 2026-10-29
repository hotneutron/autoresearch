"""Typed coordinator operations; the SQLite transaction domain owns admission."""
from __future__ import annotations
import json
from .audit import Audit
from .review_policy import ReviewPolicy
from .search import Search
from .contracts import integer


class ControlPlane:
    def __init__(self, store, archive):
        self.store, self.archive = store, archive
        self.audit, self.search, self.reviews = Audit(store), Search(store), ReviewPolicy(store)

    def call(self, operation, body):
        operations = {
            "projects/register": self.store.register_project,
            "projects/import-charges": self.store.import_charges,
            "hosts/enroll": self.store.register_host,
            "rounds/admit": self.store.admit_round,
            "units/claim": self.store.claim,
            "units/start": self.store.authorize_start,
            "units/heartbeat": self.store.heartbeat,
            "units/receipt": self.store.commit_receipt,
            "units/cancel": self.store.request_cancel,
            "messages": self.audit.message,
            "review": self.reviews.submit,
            "confirmation/reserve": self.store.reserve_confirmation,
        }
        if operation == "artifacts/blob":
            import base64
            return self.archive.put(base64.b64decode(body["data"], validate=True))
        if operation == "units/receipt":
            for artifact in body["receipt"].get("artifacts", []):
                data = self.archive.read(artifact["sha256"])
                if len(data) != artifact["size"]: raise ValueError("Receipt artifact length differs")
        if operation in operations: return operations[operation](body)
        if operation == "context":
            from .context import build_context
            return build_context(self.store, body["round_id"])
        if operation == "failures/revisit":
            from .failure_index import revisit
            result = revisit(body["prior"], body["proposal"])
            with self.store.transaction() as db: self.store._event(db, "failure_revisit_proposed", result)
            return result
        if operation == "stall":
            from .stall import assess_stall
            result = assess_stall(body["rounds"], body["policy"])
            with self.store.transaction() as db: self.store._event(db, "stall_assessed", result)
            return result
        if operation == "plan-delta":
            from .plan_delta import apply_delta
            result = apply_delta(body["plan"], body["delta"], body["evidence"])
            with self.store.transaction() as db: self.store._event(db, "plan_delta_proposed", result)
            return result
        if operation == "capabilities":
            from .capabilities import probe
            return probe()
        if operation == "review/apply": return self.reviews.apply(body["id"])
        if operation == "rounds/seal": return self.search.seal_round(body["id"])
        if operation == "units/qualify": return self.search.qualify_unit(body["unit_id"], body["qualification"])
        if operation == "units/uncertain": return self.store.mark_uncertain(body["attempt_id"])
        if operation == "units/retry": return self.store.retry(body["unit_id"], body["correction_sha256"])
        if operation == "units/query":
            with self.store.transaction(write=False) as db:
                row = self.store._row(db, "attempts", "id", body["attempt_id"])
                return {**dict(row), "body": json.loads(row["body"])}
        if operation == "control": return self.store.pause(body["project_id"], body["paused"])
        if operation == "confirmation/begin": return self.store.begin_confirmation(body["id"])
        if operation == "confirmation/finish": return self.store.finish_confirmation(body["id"], body["aggregate"], protocol_valid=body["protocol_valid"])
        if operation == "artifacts/manifest": return self.archive.commit(body)
        if operation == "events/ack": return self.store.acknowledge_events(body["through"])
        raise KeyError("Unsupported coordinator operation: " + operation)
