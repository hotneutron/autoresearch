"""Immutable execution bindings and deterministic, explicitly typed verdicts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from .review import Conflict, encode


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temporary.open("w") as handle:
        handle.write(encode(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def pointer(value, key):
    if key == "":
        return value
    if not key.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON pointer")
    for component in key[1:].split("/"):
        component = component.replace("~1", "/").replace("~0", "~")
        value = value[int(component)] if isinstance(value, list) else value[component]
    return value


def verdict(requirement):
    """Read a fixed verifier output. Missing/unknown values always fail closed."""
    path = Path(requirement["path"])
    result = {"path": str(path), "passed": False}
    try:
        actual_hash = sha256(path)
        result["sha256"] = actual_hash
        if requirement.get("sha256") and requirement["sha256"] != actual_hash:
            raise Conflict("Verifier output hash changed")
        value = json.loads(path.read_text())
        checks = requirement["checks"]
        if not checks:
            raise ValueError("A verifier requires explicit checks")
        result["checks"] = {}
        for key, expected in checks.items():
            actual = pointer(value, key)
            result["checks"][key] = type(actual) is type(expected) and actual == expected
        result["passed"] = all(result["checks"].values())
        result["reason"] = "All fixed checks pass" if result["passed"] else "Scientific prerequisite failed"
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        result["reason"] = f"Invalid or unavailable verifier output: {error}"
    return result


def bind_files(paths):
    return {str(Path(p).resolve()): sha256(p) for p in paths}


def verify_binding(task):
    if not task.get("closure"):
        raise ValueError("An explicit source/input/interpreter closure is required")
    executable = str(Path(task["argv"][0]).resolve())
    if executable not in task["closure"]:
        raise ValueError("Executable is not in the frozen closure")
    for path, expected in task["closure"].items():
        if sha256(path) != expected:
            raise Conflict(f"Frozen source/input changed: {path}")
    for key, expected in task.get("required_host_env", {}).items():
        if os.environ.get(key) != expected:
            raise Conflict(f"Host environment changed: {key}")


def runtime_identity():
    root = Path(__file__).parent
    return {"python": str(Path(sys.executable).resolve()),
            "version": sys.version, "sources": bind_files(sorted(root.glob("*.py")))}


def expand(value, output):
    if isinstance(value, str):
        return value.replace("{output}", str(output))
    if isinstance(value, list):
        return [expand(item, output) for item in value]
    if isinstance(value, dict):
        return {key: expand(item, output) for key, item in value.items()}
    return value
