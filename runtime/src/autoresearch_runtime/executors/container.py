"""Frozen read-only container profile; qualification requires actual backend evidence."""
from __future__ import annotations
import re
import shutil
from pathlib import Path
from ..contracts import integer, identifier, verify


class ContainerExecutor:
    def __init__(self, image, *, uid, gid, memory_bytes, cpu_millis, pids=128):
        if not isinstance(image, str) or not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}", image):
            raise ValueError("Pin container image digest")
        self.image = image
        self.uid, self.gid = integer(uid, minimum=1), integer(gid)
        self.memory, self.cpu, self.pids = integer(memory_bytes, minimum=1), integer(cpu_millis, minimum=1), integer(pids, minimum=1)

    def qualification(self):
        return {"available": bool(shutil.which("docker")), "qualified": False,
                "requirement": "real mounts/network/resource/deadline conformance"}

    def command(self, unit, roots, attempt_id):
        body = verify(unit); identifier(attempt_id)
        argv = ["docker", "run", "--name", "ar-" + attempt_id, "--network=none", "--read-only",
                "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user", f"{self.uid}:{self.gid}",
                "--memory", str(self.memory), "--cpus", str(self.cpu / 1000), "--pids-limit", str(self.pids),
                "--tmpfs", "/tmp:rw,nosuid,noexec,size=268435456", "--workdir", "/subject"]
        for name in ("subject", "input", "framework", "evaluator", "output"):
            if name in roots:
                source = str(Path(roots[name]).resolve())
                if ":" in source or "," in source: raise ValueError("Unsafe mount source")
                argv += ["--mount", f"type=bind,src={source},dst=/{name}," + ("rw" if name == "output" else "readonly")]
        gpu = body.get("gpu_uuid")
        if gpu:
            if not re.fullmatch(r"GPU-[A-Za-z0-9-]+", gpu): raise ValueError("Declare exact GPU UUID")
            argv += ["--gpus", "device=" + gpu]
        def convert(value):
            if value == "python:": return "python3"
            if ":" in value and value.split(":", 1)[0] in roots:
                from ..contracts import relative
                name, path = value.split(":", 1); relative(path)
                return "/" + name + "/" + path
            return value
        argv += [self.image, *[convert(v) for v in body["argv"]]]
        return {"argv": argv, "container_id": "ar-" + attempt_id, "profile": "local-container",
                "image": self.image, "cleanup_argv": ["docker", "rm", "--force", "ar-" + attempt_id]}
