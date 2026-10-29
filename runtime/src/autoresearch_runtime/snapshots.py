"""Recoverable subject Git objects; candidate identity does not require public branches."""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from .contracts import identifier, seal, verify


class Snapshots:
    def __init__(self, archive): self.archive = archive

    def capture(self, repository, commit, snapshot_id):
        identifier(snapshot_id)
        repository = Path(repository).resolve()
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit): raise ValueError("Full subject commit required")
        actual = subprocess.check_output(["git", "-C", str(repository), "rev-parse", commit + "^{commit}"], text=True).strip()
        if actual != commit: raise ValueError("Candidate commit differs")
        ref = "refs/autoresearch/archive/" + snapshot_id
        subprocess.run(["git", "-C", str(repository), "update-ref", ref, commit, "0" * 40], check=True)
        archived = False
        try:
            with tempfile.TemporaryDirectory() as directory:
                bundle = Path(directory) / "subject.bundle"
                subprocess.run(["git", "-C", str(repository), "bundle", "create", str(bundle), ref], check=True, capture_output=True)
                blob = self.archive.put(bundle.read_bytes())
            manifest = seal({"id": snapshot_id, "repository": str(repository), "commit": commit, "artifacts": [blob], "kind": "subject_git_bundle"})
            self.archive.commit(manifest)
            archived = True
            return manifest
        finally:
            # Objects remain in the Git database; the verified archive owns persistence.
            if archived:
                subprocess.run(["git", "-C", str(repository), "update-ref", "-d", ref, commit], check=True)

    def restore(self, manifest, destination):
        body = verify(manifest)
        if body["kind"] != "subject_git_bundle": raise ValueError("Subject snapshot required")
        destination = Path(destination).resolve()
        if destination.exists(): raise ValueError("Restore needs a new workspace")
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "subject.bundle"; bundle.write_bytes(self.archive.read(body["artifacts"][0]["sha256"]))
            destination.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(destination)], check=True)
            subprocess.run(["git", "-C", str(destination), "fetch", "-q", str(bundle),
                            "refs/autoresearch/archive/" + body["id"]], check=True)
        subprocess.run(["git", "-C", str(destination), "checkout", "--detach", "-q", body["commit"]], check=True)
        actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
        if actual != body["commit"]: raise ValueError("Restored candidate differs")
        return destination
