"""Immutable bounded artifact bytes and versioned manifests; hashes are permanent refs."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
import sqlite3
from pathlib import Path
from .contracts import hash_text, identifier, seal, verify
from .protocol import atomic_json


class ArtifactStore:
    def __init__(self, directory, *, max_bytes=64 * 1024 * 1024):
        self.directory = Path(directory).resolve()
        self.blobs = self.directory / "blobs"; self.manifests = self.directory / "manifests"
        self.blobs.mkdir(parents=True, exist_ok=True); self.manifests.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.index = self.directory / "index.sqlite3"
        with sqlite3.connect(self.index) as db:
            db.execute("CREATE TABLE IF NOT EXISTS manifests(id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE)")

    def put(self, data):
        if not isinstance(data, bytes) or len(data) > self.max_bytes: raise ValueError("Artifact exceeds bounded upload contract")
        sha = hashlib.sha256(data).hexdigest(); path = self.blobs / sha
        with tempfile.NamedTemporaryFile(dir=self.blobs, delete=False) as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
        try:
            try: os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != data: raise ValueError("Artifact hash collision or corruption")
        finally: temporary.unlink()
        descriptor = os.open(self.blobs, os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
        return {"sha256": sha, "size": len(data), "key": "blobs/" + sha, "state": "archive_verified"}

    def read(self, sha):
        hash_text(sha); data = (self.blobs / sha).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha: raise ValueError("Archived bytes changed")
        return data

    def commit(self, manifest):
        body = verify(manifest); identifier(body["id"])
        for item in body.get("artifacts", []):
            data = self.read(item["sha256"])
            if len(data) != item["size"]: raise ValueError("Artifact length changed")
        path = self.manifests / (manifest["sha256"] + ".json")
        with sqlite3.connect(self.index, timeout=5) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT sha256 FROM manifests WHERE id=?", (body["id"],)).fetchone()
            if old and old[0] != manifest["sha256"]:
                raise ValueError("Manifest ID is immutable; use a new revision ID")
            atomic_json(path, manifest)
            db.execute("INSERT OR IGNORE INTO manifests VALUES (?,?)", (body["id"], manifest["sha256"]))
        return {"sha256": manifest["sha256"], "state": "archive_verified"}

    def manifest(self, sha):
        hash_text(sha)
        with sqlite3.connect(self.index) as db:
            if not db.execute("SELECT 1 FROM manifests WHERE sha256=?", (sha,)).fetchone():
                raise FileNotFoundError("Manifest is not committed")
        value = json.loads((self.manifests / (sha + ".json")).read_text()); verify(value)
        return value

    def export(self, manifest_hash):
        import base64
        manifest = self.manifest(manifest_hash)
        return seal({"id": manifest["id"], "manifest": manifest,
                     "blobs": {item["sha256"]: base64.b64encode(self.read(item["sha256"])).decode() for item in manifest.get("artifacts", [])}})

    def restore(self, bundle):
        import base64
        body = verify(bundle)
        for sha, encoded in body["blobs"].items():
            ref = self.put(base64.b64decode(encoded, validate=True))
            if ref["sha256"] != sha: raise ValueError("Bundle evidence hash differs")
        return self.commit(body["manifest"])
