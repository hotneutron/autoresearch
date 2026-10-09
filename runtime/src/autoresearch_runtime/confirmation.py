"""Procedural confirmation: frozen checkout, fixed verifier, durable exposure.

This is a trusted same-account workflow, not filesystem-enforced label secrecy.
Only the proxy's validated aggregate result is released to the research inbox.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import subprocess
import time

from .protocol import atomic_json, sha256
from .review import Conflict, encode, identifier, now


def validate(spec):
    if not isinstance(spec, dict) or spec.get("isolation_mode") != "procedural":
        raise ValueError("Confirmation requires an explicit procedural contract or a qualified access boundary")
    if spec["purpose"] not in {"fresh_confirmation", "protocol_fixture", "historical_replay"}:
        raise ValueError("Unknown confirmation purpose")
    checkout = Path(spec["checkout"]).resolve()
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if head != spec["candidate_commit"]:
        raise Conflict("Confirmation checkout differs from the frozen candidate commit")
    dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=normal"], text=True)
    if dirty.strip():
        raise Conflict("Confirmation checkout must be clean")
    for key in ("candidate", "verifier"):
        item = spec[key]
        path = Path(item["path"]).resolve()
        if not path.is_relative_to(checkout) or sha256(path) != item["sha256"]:
            raise Conflict(f"Frozen confirmation {key} changed or is outside its checkout")
    dataset = spec["dataset"]
    identifier(dataset["id"])
    identifier(dataset["namespace"])
    if not dataset["subjects"] or len(set(dataset["subjects"])) != len(dataset["subjects"]):
        raise ValueError("Confirmation requires unique subject identities")
    if type(dataset["previously_exposed"]) is not bool:
        raise ValueError("Dataset exposure declaration required")
    if spec["purpose"] == "fresh_confirmation" and dataset["previously_exposed"]:
        raise Conflict("Previously exposed data cannot be fresh confirmation")
    if sha256(dataset["path"]) != dataset["sha256"]:
        raise Conflict("Confirmation dataset hash changed")
    if spec["verifier_argv"][1] != str(Path(spec["verifier"]["path"]).resolve()):
        raise ValueError("Verifier command must invoke the bound verifier")
    if not isinstance(spec["released_fields"], dict) or not spec["released_fields"] or "schema_version" not in spec["released_fields"]:
        raise ValueError("Declare the exact aggregate result fields that may be released")
    if len(spec["released_fields"]) > 12 or any(kind not in {"int", "number", "bool"} for kind in spec["released_fields"].values()):
        raise ValueError("Release only declared numeric/boolean aggregate fields")


@contextmanager
def ledger(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
          CREATE TABLE IF NOT EXISTS openings (id TEXT PRIMARY KEY, body TEXT NOT NULL,
            opened TEXT NOT NULL, finished TEXT, status TEXT NOT NULL, result_sha256 TEXT);
          CREATE TABLE IF NOT EXISTS datasets (namespace TEXT, id TEXT, digest TEXT UNIQUE NOT NULL,
            opening TEXT NOT NULL, PRIMARY KEY(namespace,id));
          CREATE TABLE IF NOT EXISTS subjects (namespace TEXT, id TEXT, opening TEXT NOT NULL,
            PRIMARY KEY(namespace,id));
        """)
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def begin(spec):
    """Consume the opening before any evaluator launch, including failed launches."""
    validate(spec)
    dataset = spec["dataset"]
    try:
        with ledger(spec["ledger_path"]) as db:
            db.execute("INSERT INTO openings VALUES (?,?,?,NULL,'opened',NULL)",
                       (spec["request_id"], encode(spec), now()))
            db.execute("INSERT INTO datasets VALUES (?,?,?,?)",
                       (dataset["namespace"], dataset["id"], dataset["sha256"], spec["request_id"]))
            db.executemany("INSERT INTO subjects VALUES (?,?,?)",
                           [(dataset["namespace"], subject, spec["request_id"]) for subject in dataset["subjects"]])
    except sqlite3.IntegrityError as error:
        raise Conflict("Confirmation data or subjects were already opened; failed/interrupted openings also count") from error


def eligibility(spec):
    dataset = spec["dataset"]
    with ledger(spec["ledger_path"]) as db:
        used = db.execute("SELECT 1 FROM datasets WHERE digest=? OR (namespace=? AND id=?)",
                          (dataset["sha256"], dataset["namespace"], dataset["id"])).fetchone()
        overlap = any(db.execute("SELECT 1 FROM subjects WHERE namespace=? AND id=?",
                                 (dataset["namespace"], subject)).fetchone() for subject in dataset["subjects"])
    return {"passed": not (used or overlap), "kind": "confirmation_exposure",
            "reason": "Confirmation data or subjects were already opened" if used or overlap else "No prior opening in the project exposure ledger"}


def require_opening(spec):
    with ledger(spec["ledger_path"]) as db:
        row = db.execute("SELECT body,status FROM openings WHERE id=?", (spec["request_id"],)).fetchone()
        if not row or row["body"] != encode(spec) or row["status"] != "opened":
            raise Conflict("No matching unused opening reservation")
        # A proxy that itself crashes cannot be launched again with this reservation.
        db.execute("UPDATE openings SET status='evaluating' WHERE id=?", (spec["request_id"],))


def run(spec, out):
    out = Path(out)
    validate(spec)
    require_opening(spec)
    result = {"schema_version": 1, "isolation_mode": "procedural", "purpose": spec["purpose"],
              "protocol_valid": False, "request_id": spec["request_id"], "dataset_sha256": spec["dataset"]["sha256"],
              "candidate_commit": spec["candidate_commit"], "raw_labels_released": False}
    started = time.monotonic()
    try:
        dataset = json.loads(Path(spec["dataset"]["path"]).read_text())
        if sorted(dataset["observations"]) != sorted(spec["dataset"]["subjects"]):
            raise ValueError("Dataset subjects differ from the frozen exposure manifest")
        argv = [arg.replace("{dataset}", spec["dataset"]["path"]).replace("{candidate}", spec["candidate"]["path"])
                for arg in spec["verifier_argv"]]
        completed = subprocess.run(argv, cwd=spec["checkout"], capture_output=True, text=True,
                                   timeout=spec["verifier_timeout_seconds"], close_fds=False)
        # Retain failure evidence privately; never copy verifier stdout into the inbox.
        logs = Path(spec["private_log_directory"])
        logs.mkdir(parents=True, exist_ok=True)
        (logs / (spec["request_id"] + ".stdout")).write_text(completed.stdout)
        (logs / (spec["request_id"] + ".stderr")).write_text(completed.stderr)
        if completed.returncode:
            raise ValueError("Fixed verifier failed; opening remains consumed")
        value = json.loads(completed.stdout)
        if not isinstance(value, dict) or set(value) != set(spec["released_fields"]):
            raise ValueError("Verifier output does not match the frozen aggregate-only schema")
        for key, kind in spec["released_fields"].items():
            allowed = {"int": (int,), "number": (int, float), "bool": (bool,)}[kind]
            if type(value[key]) not in allowed:
                raise ValueError("Verifier output has a non-aggregate field type")
        # Reject NaN/Infinity before release.
        encode(value)
        result.update(protocol_valid=True, aggregate=value)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        result["failure_class"] = type(error).__name__
        result["reason"] = "Confirmation did not produce a valid aggregate verdict; this opening cannot be retried"
    result["wall_seconds"] = time.monotonic() - started
    atomic_json(out / "result.json", result)
    with ledger(spec["ledger_path"]) as db:
        db.execute("UPDATE openings SET finished=?,status=?,result_sha256=? WHERE id=?",
                   (now(), "completed" if result["protocol_valid"] else "failed", sha256(out / "result.json"), spec["request_id"]))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(encode(run(json.loads(args.spec.read_text()), args.out)))
