"""Generated peer repositories and bounded CPU contracts for conformance."""
from pathlib import Path
import subprocess
from autoresearch_runtime.contracts import digest, seal
from autoresearch_runtime.experiment_spec import compile_spec
from autoresearch_runtime.protocol import sha256


def git_repo(root, files):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, content in files.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    for argv in (["add", "."], ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Freeze CPU subject"]):
        subprocess.run(["git", "-C", str(root), *argv], check=True)
    return {"repository": "fixture/" + root.name,
            "commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()}


def unit(root, name="candidate-1", value=1):
    root = Path(root).resolve()
    framework = root / "framework"; subject = root / "subject"
    if not framework.exists():
        git_repo(framework, {"runtime.txt": "Pinned fixture framework"})
        git_repo(subject, {"metric.py": "import json,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps({'score':float(sys.argv[2])}))\n", "plan.md": "Finite CPU experiment."})
    ref = lambda p: {"repository": "fixture/" + p.name,
                     "commit": subprocess.check_output(["git", "-C", str(p), "rev-parse", "HEAD"], text=True).strip()}
    return compile_spec({"id": name, "project_id": "subject", "candidate_id": name,
        "phase": "evaluation", "replicate_id": name + "-seed0", "seed": 0,
        "prompt_verbatim": "Evaluate finite CPU hypotheses.", "framework_ref": ref(framework), "subject_ref": ref(subject),
        "argv": ["python:", "subject:metric.py", "output:result.json", str(value)],
        "files": [{"path": "subject:metric.py", "sha256": sha256(subject / "metric.py")}],
        "benchmark_sha256": digest({"benchmark": "cpu", "version": 1}),
        "evaluator_sha256": sha256(subject / "metric.py"), "environment_sha256": digest({"fixture_environment": "cpu-v1"}),
        "metrics": [{"name": "score", "pointer": "/score", "unit": "count", "direction": "lower", "op": "le", "threshold": 10, "meaning": "Fixture only", "minimum_effect": .1}],
        "qualification_policy": {"replicates": [{"id": "r", "seed": 0}], "direction": "lower", "minimum_effect": .1, "method": "deterministic_margin", "deterministic": True},
        "costs": {"wall_ms": 5000}, "timeout_ms": 1000, "profile": "local-direct", "requires": [], "resources": []})


def round_plan(units, name="round-1", concurrency=2, **extra):
    return seal({"id": name, "project_id": "subject", "goal_sha256": digest("finite-goal"),
                 "concurrency": concurrency, "top_k": 2, "budget": {"wall_ms": sum(u["costs"]["wall_ms"] for u in units)},
                 "units": units, "initial_authorization": True, **extra})
