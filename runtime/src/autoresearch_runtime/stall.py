"""Prospective stagnation on complete comparable rounds, distinct from significance."""
from .contracts import finite, integer, seal


def assess_stall(rounds, policy):
    window = integer(policy["window"], minimum=2)
    epsilon = finite(policy["epsilon"])
    if epsilon < 0 or policy["action"] not in ("diagnose", "pivot", "hold", "stop"): raise ValueError("Declare bounded stall policy")
    latest = rounds[-window:]
    if len(latest) < window: return {"state": "insufficient_rounds"}
    if any(r.get("sealed") is not True or r.get("valid") is not True for r in latest): return {"state": "incomplete_evidence"}
    if len({r["benchmark_sha256"] for r in latest}) != 1: return {"state": "incomparable_rounds"}
    values = [finite(r["improvement"]) for r in latest]
    stalled = all(v <= epsilon for v in values)
    return seal({"id": "stall-" + latest[-1]["id"], "state": "stalled" if stalled else "progress",
                 "round_ids": [r["id"] for r in latest], "action": policy["action"] if stalled else None,
                 "diagnostic_budget": policy.get("diagnostic_budget", {}), "requires_reviewed_scope": stalled})
