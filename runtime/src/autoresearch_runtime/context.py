"""Bounded context reconstructed from canonical state, never conversational memory."""
from __future__ import annotations
import json
from .contracts import integer, seal


def build_context(store, round_id, *, max_events=50, max_bytes=32000):
    integer(max_events, minimum=1); integer(max_bytes, minimum=1000)
    snapshot = store.snapshot(round_id)
    with store.transaction(write=False) as db:
        maximum = db.execute("SELECT MAX(seq) FROM events").fetchone()[0] or 0
    events = store.events(max(0, maximum-max_events), min(1000, max_events))
    result = {"id": round_id + "-context", "rounds": [
                  {"id": r["id"], "project": r["project"], "state": r["state"],
                   "sha256": r["body"]["sha256"], "budget": r["body"]["budget"]}
                  for r in snapshot["rounds"]],
              "units": [{k: u[k] for k in ("id", "state", "generation")} for u in snapshot["units"]],
              "attempts": [{k: a[k] for k in ("id", "unit", "host", "state", "generation")} for a in snapshot["attempts"]],
              "events": events, "omitted_event_count": 0, "authority": "coordinator_records"}
    while len(json.dumps(result).encode()) > max_bytes and result["events"]:
        result["events"].pop(0); result["omitted_event_count"] += 1
    if len(json.dumps(result).encode()) > max_bytes: raise ValueError("Context inventory exceeds budget; request a bounded page")
    return seal(result)
