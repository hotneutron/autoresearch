"""Failure revisitation requires a changed assumption and evidence, not blind repetition."""
from .contracts import hash_text, identifier, seal


def revisit(prior, proposal):
    identifier(prior["id"]); identifier(proposal["id"])
    if not prior.get("reason") or not prior.get("assumption_sha256"): raise ValueError("Prior failure reason/assumption required")
    hash_text(prior["assumption_sha256"]); hash_text(proposal["assumption_sha256"])
    if prior["assumption_sha256"] == proposal["assumption_sha256"]: raise ValueError("Unchanged rejected assumption cannot revive a path")
    if not proposal.get("change_reason") or not proposal.get("evidence_sha256"): raise ValueError("Changed assumption needs released evidence")
    hash_text(proposal["evidence_sha256"])
    return seal({**proposal, "revisits_run": prior["id"], "prior_reason": prior["reason"], "requires_reviewed_round": True})
