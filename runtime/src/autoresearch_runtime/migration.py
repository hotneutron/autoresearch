"""Filtered legacy imports preserve canonical bytes and reveal accounting gaps."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from .contracts import seal, identifier
from .protocol import atomic_json
from .store import backup


def export_legacy(database, origin):
    identifier(origin)
    with sqlite3.connect("file:" + str(Path(database).resolve()) + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        packets = [dict(r) for r in db.execute("SELECT id,branch,revision,hash,body,published FROM packets")]
        for packet in packets:
            if hashlib.sha256(packet["body"].encode()).hexdigest() != packet["hash"]: raise ValueError("Canonical legacy packet hash differs")
        evidence = [dict(r) for r in db.execute("SELECT hash,body FROM evidence")]
        feedback = [dict(r) for r in db.execute("SELECT * FROM feedback")]
        state = {table: [dict(r) for r in db.execute("SELECT * FROM " + table)] for table in ("branches", "permits", "checkpoints", "jobs")}
    return seal({"id": origin + "-legacy", "origin": origin, "packets": packets, "evidence": evidence,
                 "feedback": feedback, "review_state": state, "accounting_imported": False, "exposure_imported": False,
                 "admission_requires_accounting_reconciliation": True})


def recovery_catalog(store, archive, destination):
    destination = Path(destination).resolve(); destination.mkdir(parents=True, exist_ok=True)
    backup(store.database, destination / "coordinator.sqlite3")
    from .audit import Audit
    events = Audit(store).export_events()
    manifest = seal({"id": "coordinator-recovery", "events": events,
                     "database_sha256": hashlib.sha256((destination / "coordinator.sqlite3").read_bytes()).hexdigest(),
                     "archive_root": str(archive.directory), "requires_grant_reconciliation": True})
    atomic_json(destination / "catalog.json", manifest)
    return manifest


def import_legacy(bundle, destination):
    from .contracts import verify
    from .review import Inbox
    body = verify(bundle)
    destination = Path(destination).resolve() / body["origin"]
    if destination.exists(): raise ValueError("Legacy import requires a new origin store")
    inbox = Inbox(destination, destination)
    tables = {"packets": body["packets"], "evidence": body["evidence"], "feedback": body["feedback"], **body["review_state"]}
    with inbox.connect(write=True) as db:
        for table, rows in tables.items():
            columns = [r[1] for r in db.execute("PRAGMA table_info(" + table + ")")]
            for row in rows:
                db.execute("INSERT INTO " + table + "(" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")", [row[c] for c in columns])
        for row in db.execute("SELECT hash,body FROM packets"):
            if hashlib.sha256(row["body"].encode()).hexdigest() != row["hash"]: raise ValueError("Imported legacy bytes changed")
    atomic_json(destination / "origin-manifest.json", bundle)
    return {"origin": body["origin"], "store": str(destination), "packets": len(body["packets"]),
            "admission_requires_accounting_reconciliation": True}
