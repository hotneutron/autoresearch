"""Finite frozen units compiled from subject-authored plans. Request: see M0 tracker."""
from __future__ import annotations
from copy import deepcopy
from .contracts import costs, hash_text, identifier, integer, relative, seal
from .portable_contract import repo_ref
from .metrics import validate_metrics


def compile_spec(value):
    body = deepcopy(value)
    for field in ("id", "project_id", "candidate_id", "phase", "replicate_id"):
        identifier(body[field])
    if body["phase"] not in ("baseline", "evaluation", "qualification", "confirmation", "ablation"):
        raise ValueError("Unregistered execution phase")
    if not isinstance(body.get("prompt_verbatim"), str) or not body["prompt_verbatim"].strip():
        raise ValueError("Original instruction required")
    repo_ref(body["framework_ref"]); repo_ref(body["subject_ref"])
    integer(body["timeout_ms"], minimum=1)
    costs(body["costs"])
    if "gpu_ms" in body["costs"]: integer(body["gpu_count"])
    if "microcurrency" in body["costs"]: integer(body["rate_microcurrency_per_second"])
    if body["costs"].get("wall_ms", 0) < body["timeout_ms"]:
        raise ValueError("Complete reservation must cover execution timeout")
    argv = body.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v for v in argv):
        raise ValueError("Declare an exact argv list")
    if not body.get("files"): raise ValueError("Declare source/input/evaluator closure")
    for item in body["files"]:
        name, path = item["path"].split(":", 1)
        if name not in ("subject", "framework", "input", "evaluator"): raise ValueError("Invalid input root")
        relative(path); hash_text(item["sha256"])
        if body["phase"] != "confirmation" and item.get("partition") == "final":
            raise ValueError("Final partition is unavailable to iterative contracts")
    if body.get("partition") == "final" and body["phase"] != "confirmation":
        raise ValueError("Final partition requires confirmation")
    validate_metrics(body["metrics"])
    if not isinstance(body.get("qualification_policy"), dict) or not body["qualification_policy"].get("replicates"):
        raise ValueError("Freeze the qualification policy before admission")
    if not body.get("benchmark_sha256"): raise ValueError("Freeze benchmark identity")
    hash_text(body["benchmark_sha256"])
    hash_text(body["evaluator_sha256"])
    hash_text(body["environment_sha256"])
    if body.get("seed") is not None: integer(body["seed"])
    for name in body.get("requires", []): identifier(name)
    body.setdefault("resources", [])
    for name in body["resources"]: identifier(name)
    return seal(body)
