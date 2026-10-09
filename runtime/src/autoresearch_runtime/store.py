"""Consistent SQLite backups and lossless migration of prototype inbox stores."""
import json
from pathlib import Path
import sqlite3

from .protocol import atomic_json
from .review import Inbox, Conflict


def backup(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise Conflict("SQLite backup failed integrity check")
    return destination


def migrate(source, destination, project):
    """Import into a new store; original DB/WAL and immutable packet bytes stay intact."""
    destination = Path(destination)
    database = backup(source, destination / "inbox.sqlite3")
    inbox = Inbox(destination, project)
    with inbox.connect(write=True) as db:
        counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in ("packets", "evidence", "feedback", "permits", "checkpoints", "jobs")}
        for row in db.execute("SELECT hash,body FROM packets"):
            import hashlib
            if hashlib.sha256(row["body"].encode()).hexdigest() != row["hash"]:
                raise Conflict("Migration packet hash mismatch")
        db.execute("PRAGMA user_version=2")
    result = {"source": str(Path(source).resolve()), "destination": str(database.resolve()),
              "status": "pass", "counts": counts, "schema_version": 2}
    atomic_json(destination / "migration.json", result)
    return result
