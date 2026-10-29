"""Pre-execution capability profiles; decisions freeze in the contract."""
from __future__ import annotations
import os
import platform
import shutil
from .contracts import seal


def probe():
    return seal({"id": "host-capabilities", "os": platform.system(), "architecture": platform.machine(),
                 "cpu_count": os.cpu_count(), "systemd_available": bool(shutil.which("systemd-run")),
                 "docker_available": bool(shutil.which("docker")), "gpu": "unqualified", "assurance": "poc_local_probe"})


def eligible(profile, required):
    from .contracts import verify
    value = verify(profile)
    return {"allowed": all(value.get(k) == v for k, v in required.items()),
            "profile_sha256": profile["sha256"], "changes_require_new_contract": True}
