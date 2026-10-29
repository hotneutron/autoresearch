"""Explicit procedural local execution; never claims OS containment."""
from ..contracts import verify


class DirectExecutor:
    def qualification(self):
        return {"available": True, "isolated": False, "assurance": "procedural"}

    def command(self, binding):
        body = verify(binding)
        return {"argv": body["argv"], "cwd": body["cwd"], "closure": body["closure"],
                "profile": "local-direct", "assurance": "procedural"}
