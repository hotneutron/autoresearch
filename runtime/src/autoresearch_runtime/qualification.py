"""Seed-bound paired qualification, distinct from final scientific promotion."""
from __future__ import annotations
import math
import random
import statistics
from .contracts import finite, hash_text, identifier, integer, seal, verify


def qualify(candidate, samples, policy):
    for key in ("candidate_sha256", "benchmark_sha256", "evaluator_sha256", "environment_sha256"):
        hash_text(candidate[key])
    expected = policy["replicates"]
    if not isinstance(expected, list) or not expected: raise ValueError("Freeze replicate identities")
    expected_ids = [identifier(r["id"]) for r in expected]
    if len(set(expected_ids)) != len(expected_ids): raise ValueError("Duplicate replicate identities")
    if len(samples) != len(expected) or {s["replicate_id"] for s in samples} != set(expected_ids):
        raise ValueError("Complete replicate set required")
    if policy["direction"] not in ("lower", "higher"): raise ValueError("Metric direction required")
    margin = finite(policy["minimum_effect"])
    if margin < 0: raise ValueError("Effect margin must be nonnegative")
    deltas, refs = [], []
    for sample in samples:
        for key in ("candidate_sha256", "benchmark_sha256", "evaluator_sha256", "environment_sha256"):
            if sample.get(key) != candidate[key]: raise ValueError("Incomparable replicate " + key)
        replicate = next(r for r in expected if r["id"] == sample["replicate_id"])
        if sample.get("seed") != replicate["seed"]: raise ValueError("Explicit seed identity differs")
        if sample.get("execution_status") != "completed" or sample.get("evidence_valid") is not True or sample.get("guards_passed") is not True:
            raise ValueError("Only completed correct evidence can qualify")
        value, baseline = finite(sample["value"]), finite(sample["baseline"])
        deltas.append(baseline-value if policy["direction"] == "lower" else value-baseline)
        refs.append(hash_text(sample["receipt_sha256"]))
    method = policy["method"]
    if method == "deterministic_margin":
        if policy.get("deterministic") is not True: raise ValueError("Declare deterministic fixture/objective")
        lower = min(deltas); upper = max(deltas)
    elif method == "paired_bootstrap":
        if len(deltas) < 3: raise ValueError("Paired bootstrap requires at least three declared samples")
        confidence = finite(policy["confidence"])
        if not 0 < confidence < 1: raise ValueError("Invalid confidence")
        comparisons = integer(policy["comparisons"], minimum=1)
        if policy.get("correction") != "bonferroni": raise ValueError("Explicit adaptive/multiple-comparison policy required")
        draws = integer(policy.get("draws", 2000), minimum=100)
        if draws > 100000: raise ValueError("Statistical budget exceeded")
        rng = random.Random(integer(policy["analysis_seed"]))
        means = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(draws))
        alpha = (1-confidence) / comparisons
        lower = means[min(draws-1, int(alpha/2 * draws))]
        upper = means[min(draws-1, int((1-alpha/2) * draws))]
    else: raise ValueError("Unregistered qualification method")
    controls = policy.get("matched_controls", [])
    if policy.get("structured_search") is True:
        if not {"random", "classical"} <= set(controls): raise ValueError("Budget-matched random/classical controls required")
        records = policy.get("control_records", {})
        for name in ("random", "classical"):
            record = records.get(name)
            if not record or record.get("budget") != policy.get("comparison_budget") or record.get("benchmark_sha256") != candidate["benchmark_sha256"]:
                raise ValueError("Matched control budget/input evidence required")
            hash_text(record["receipt_sha256"])

    ablations = policy.get("required_ablations", [])
    if any(a not in policy.get("completed_ablations", []) for a in ablations): raise ValueError("Declared ablations incomplete")
    for name in ablations:
        if name not in policy.get("ablation_records", {}): raise ValueError("Ablation receipt evidence required")
        hash_text(policy["ablation_records"][name]["receipt_sha256"])

    return seal({"id": identifier(candidate["id"]), "candidate": candidate, "policy": policy,
                 "receipt_hashes": refs, "samples": samples, "mean_improvement": statistics.mean(deltas),
                 "interval": [lower, upper], "positive": lower > margin, "partition": policy.get("partition", "validation"),
                 "final_promotion": False})


def final_promotion(qualification, confirmation):
    q = verify(qualification); c = verify(confirmation)
    if q.get("positive") is not True or c.get("protocol_valid") is not True or c.get("purpose") != "fresh_confirmation":
        raise ValueError("Positive qualification and fresh final confirmation required")
    if c.get("aggregate", {}).get("accepted") is not True:
        raise ValueError("Final confirmation must release an accepted outcome")
    if qualification["sha256"] != c.get("qualification_sha256") or q["candidate"]["candidate_sha256"] not in c.get("candidate_hashes", []):
        raise ValueError("Confirmation candidate/qualification binding differs")
    return seal({"id": q["id"] + "-final", "qualification_sha256": qualification["sha256"],
                 "confirmation_sha256": confirmation["sha256"], "final_promotion": True})
