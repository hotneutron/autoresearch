"""Immutable peer-root resolution; absolute paths never define global identity."""
from __future__ import annotations
from pathlib import Path
import subprocess
from .contracts import identifier, hash_text, relative, seal, verify
from .protocol import sha256


def repo_ref(value):
    if not isinstance(value, dict) or not isinstance(value.get("repository"), str) or not value["repository"]:
        raise ValueError("Declare repository identity")
    commit = value.get("commit")
    if not isinstance(commit, str) or len(commit) not in (40, 64) or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Repository ref must pin a full commit")
    return value


def resolve(value, roots):
    if not isinstance(value, str) or ":" not in value:
        raise ValueError("Declare root:relative-path")
    name, path = value.split(":", 1)
    identifier(name); relative(path)
    if name not in roots:
        raise ValueError("Logical root unavailable: " + name)
    base = Path(roots[name]).resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("Resolved path escapes declared root")
    return target


def bind_unit(unit, roots, *, python):
    body = verify(unit)
    for name in ("framework", "subject"):
        ref = repo_ref(body[name + "_ref"])
        root = Path(roots[name]).resolve()
        actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if actual != ref["commit"]:
            raise ValueError(name + " checkout differs from pinned commit")
    closure = {}
    for item in body["files"]:
        path = resolve(item["path"], roots)
        if sha256(path) != hash_text(item["sha256"]):
            raise ValueError("Frozen input changed: " + item["path"])
        closure[str(path)] = item["sha256"]
    def expand(arg):
        if arg == "python:": return str(Path(python).resolve())
        if isinstance(arg, str) and arg.split(":", 1)[0] in roots:
            return str(resolve(arg, roots))
        return arg
    argv = [expand(arg) for arg in body["argv"]]
    executable = Path(argv[0]).resolve()
    closure[str(executable)] = sha256(executable)
    if "interpreter_sha256" in body and closure[str(executable)] != body["interpreter_sha256"]:
        raise ValueError("Interpreter differs from frozen environment")
    return seal({"unit_sha256": unit["sha256"], "argv": argv,
                 "cwd": str(Path(roots["subject"]).resolve()), "closure": closure,
                 "output_root": str(Path(roots["output"]).resolve()),
                 "host_id": identifier(body.get("host_id", "portable"))})
