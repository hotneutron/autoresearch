"""Read-only live presentation alongside immutable authored review packets.

Prompt verbatim: looks like the review dashboard is no longer updating
## Revision History
- 2026-10-20: Add a project-neutral observation callback; it never dispatches work,
  amends packets, consumes feedback or changes admission/approval state.
- 2026-10-21T01:31:00Z: Delegate immutable report history and optional trusted
  experiment history read-only, no permission or scientific-state changes.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Callable

from .review import now


def live_snapshot(value: dict) -> dict:
    """Normalize an observation, separate from scientific packet validation."""
    if not isinstance(value, dict):
        raise ValueError("Live observation must be an object")
    result = deepcopy(value)
    result["schema_version"] = 1
    result["read_only"] = True
    result["observed_at"] = result.get("observed_at") or now()
    if not isinstance(result["observed_at"], str):
        raise ValueError("Live observation needs a timestamp")
    for key in ("summary", "progress_note"):
        if key in result and not isinstance(result[key], str):
            raise ValueError(f"Live {key} must be text")
    for key in ("units", "checkpoints"):
        values = result.setdefault(key, [])
        if not isinstance(values, list) or len(values) > 200 or any(not isinstance(v, dict) for v in values):
            raise ValueError(f"Live {key} must contain at most 200 observation objects")
    return result


class LiveInbox:
    """Wrap an inbox with a fresh read-only observation on each HTTP snapshot.

    The trusted host supplies the callback and retains responsibility for path,
    process and scientific-outcome provenance. Observations are never published
    as evidence or used for feedback/action gates. Callback failure keeps the
    immutable inbox usable and makes missing liveness explicit, not 'running'.
    """

    def __init__(self, inbox, observe: Callable[[], dict]):
        self.inbox = inbox
        self.observe = observe

    def snapshot(self):
        snapshot = self.inbox.snapshot()
        try:
            observation = live_snapshot(self.observe())
        except Exception as error:
            observation = live_snapshot({"available": False, "summary": str(error), "observation_error": type(error).__name__})
        snapshot["live_status"] = observation
        return snapshot

    def html(self, *args, **kwargs):
        return self.inbox.html(*args, **kwargs)

    def evidence(self, *args, **kwargs):
        return self.inbox.evidence(*args, **kwargs)

    def history(self, *args, **kwargs):
        return self.inbox.history(*args, **kwargs)

    def report(self, *args, **kwargs):
        return self.inbox.report(*args, **kwargs)

    def experiments(self, *args, **kwargs):
        if hasattr(self.inbox, 'experiments'):
            return self.inbox.experiments(*args, **kwargs)
        return {'available':False,'items':[],'total':0,'reason':'No experiment history provider is attached'}

    def experiment(self, *args, **kwargs):
        return self.inbox.experiment(*args, **kwargs)

    def experiment_evidence(self, *args, **kwargs):
        return self.inbox.experiment_evidence(*args, **kwargs)

    def submit(self, *args, **kwargs):
        return self.inbox.submit(*args, **kwargs)
