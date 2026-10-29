"""Exact complete-route costs; runtime status uses integer resource dimensions."""
from __future__ import annotations
from .contracts import costs, integer


def reservation(*, prepare_ms, execution_ms, evaluation_ms, grace_ms, gpu_count=0, rate_microcurrency_per_second=0):
    values = [integer(v) for v in (prepare_ms, execution_ms, evaluation_ms, grace_ms, gpu_count, rate_microcurrency_per_second)]
    total = sum(values[:4])
    if not total: raise ValueError("Reserve a complete bounded route")
    return {"wall_ms": total, "gpu_ms": total * gpu_count,
            "microcurrency": (total * rate_microcurrency_per_second + 999) // 1000}


def within(actual, budget):
    actual, budget = costs(actual), costs(budget)
    return set(actual) <= set(budget) and all(v <= budget[k] for k, v in actual.items())
