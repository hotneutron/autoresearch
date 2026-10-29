"""Host-local exclusive resource leases. Global capacity belongs to the coordinator."""
from __future__ import annotations
import fcntl
import hashlib
import os
from pathlib import Path
from .contracts import identifier


class Leases:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.fds = []

    def acquire(self, resources):
        if self.fds: raise ValueError("Lease set already acquired")
        try:
            for resource in sorted(set(resources)):
                identifier(resource)
                path = self.directory / hashlib.sha256(resource.encode()).hexdigest()
                fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
                self.fds.append(fd)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.close()
            raise
        return self

    def close(self):
        for fd in self.fds: os.close(fd)
        self.fds.clear()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
