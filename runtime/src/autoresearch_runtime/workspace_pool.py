"""Bounded evaluation slots with live OS leases; uncertain ownership is not expired by time."""
from __future__ import annotations
from pathlib import Path
from .contracts import integer
from .resources import Leases


class WorkspacePool:
    def __init__(self, directory, capacity):
        self.directory = Path(directory).resolve(); self.directory.mkdir(parents=True, exist_ok=True)
        self.capacity = integer(capacity, minimum=1)

    def acquire(self):
        for index in range(self.capacity):
            lease = Leases(self.directory / "leases")
            try: lease.acquire(["slot-" + str(index)])
            except BlockingIOError: continue
            workspace = self.directory / ("slot-" + str(index)); workspace.mkdir(exist_ok=True)
            return {"workspace": workspace, "lease": lease, "slot": index}
        raise BlockingIOError("All evaluation workspaces are leased")
