"""One subject promotion writer with expected-old-ref checks and a bounded frontier."""
from __future__ import annotations
import fcntl
import subprocess
from pathlib import Path
from .contracts import identifier, integer


def promote(repository, selected, expected, *, top_k):
    repository = Path(repository).resolve(); integer(top_k, minimum=1)
    if len(selected) > top_k: raise ValueError("Retained frontier exceeds top-k")
    gitdir = Path(subprocess.check_output(["git", "-C", str(repository), "rev-parse", "--absolute-git-dir"], text=True).strip())
    with (gitdir / "autoresearch-promotion.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        commands = ["start"]
        for name, commit in selected.items():
            identifier(name)
            if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit): raise ValueError("Full candidate commit required")
            ref = "refs/heads/research/" + name
            prior = expected.get(name, "0" * 40)
            commands.append("update " + ref + " " + commit + " " + prior)
        commands += ["prepare", "commit"]
        subprocess.run(["git", "-C", str(repository), "update-ref", "--stdin"], input="\n".join(commands) + "\n", text=True, check=True, capture_output=True)
    return {"retained": selected, "validation_required_after_integration": True}
