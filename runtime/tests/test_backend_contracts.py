import tempfile
import unittest
from pathlib import Path
from autoresearch_runtime.supervisor import SystemdSupervisor,UnqualifiedBackend
from autoresearch_runtime.executors.container import ContainerExecutor
from autoresearch_runtime.contracts import seal
from autoresearch_runtime.audit import Audit
from autoresearch_runtime.global_store import GlobalStore
from autoresearch_runtime.migration import recovery_catalog
from autoresearch_runtime.artifacts import ArtifactStore
from autoresearch_runtime.contracts import digest
from autoresearch_runtime.context import build_context
from distributed_fixture import unit,round_plan
from autoresearch_runtime.controller import Controller
from autoresearch_runtime.protocol import bind_files
from autoresearch_runtime.migration import export_legacy, import_legacy
import sys
import sqlite3


class BackendContracts(unittest.TestCase):
    def test_legacy_origin_import_preserves_packets_and_pause_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            script = root / "subject.py"
            script.write_text("print('frozen')")
            config = {"schema_version": 1, "id": "legacy", "project_root": str(root),
                      "prompt_verbatim": "Check legacy persistence.", "budget": {"max_units": 1, "max_seconds": 2},
                      "tasks": {"one": {"branch": "one", "approved": True, "timeout_seconds": 1,
                          "argv": [sys.executable, str(script)], "closure": bind_files([sys.executable, script]),
                          "verdict": {"path": "{output}/result.json", "checks": {"/allowed": True}}}}}
            controller = Controller(root / "legacy", config)
            controller.submit("one")
            packet = controller.inbox.snapshot()["packets"][0]
            controller.inbox.submit({"id": "pause", "packet_id": packet["id"], "packet_hash": packet["hash"], "kind": "pause", "comment": "Pause"})
            controller.inbox.checkpoint("one", "boundary")
            bundle = export_legacy(controller.inbox.database, "source-a")
            imported = import_legacy(bundle, root / "imports")
            with sqlite3.connect(Path(imported["store"]) / "inbox.sqlite3") as db:
                self.assertEqual(db.execute("SELECT hash FROM packets").fetchone()[0], packet["hash"])
                self.assertEqual(db.execute("SELECT paused FROM branches WHERE id='one'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0], 1)
            self.assertTrue(imported["admission_requires_accounting_reconciliation"])

    def test_unqualified_supervisor_reports_missing_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor=SystemdSupervisor(directory)
            status=supervisor.qualification()
            self.assertFalse(status['qualified'])
            if not status['available']:
                with self.assertRaises(UnqualifiedBackend):supervisor.start('attempt',{'argv':['/bin/true'],'timeout_ms':100})
    def test_container_plan_has_read_only_sources_and_exact_cleanup(self):
        executor=ContainerExecutor('python@sha256:'+'a'*64,uid=1000,gid=1000,memory_bytes=1024**3,cpu_millis=1000)
        with tempfile.TemporaryDirectory() as directory:
            spec=unit(Path(directory));roots={'subject':Path(directory)/'subject','output':Path(directory)/'out'}
            command=executor.command(spec,roots,'attempt')
            self.assertIn('--network=none',command['argv']);self.assertIn('--read-only',command['argv'])
            self.assertEqual(command['cleanup_argv'],['docker','rm','--force','ar-attempt'])
            source=next(arg for arg in command['argv'] if 'dst=/subject' in arg)
            self.assertTrue(source.endswith('readonly'))
    def test_audit_reply_integrity_and_online_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=GlobalStore(root/'global');archive=ArtifactStore(root/'archive');audit=Audit(store)
            store.register_project({'id':'subject','goal_sha256':digest('finite-goal'),'budget':{'wall_ms':100000}})
            store.admit_round(round_plan([unit(root)]))
            message=audit.message({'id':'question','project_id':'subject','text':'What changed?'})
            reply=audit.message({'id':'reply','project_id':'subject','text':'Measured result','in_reply_to':'question'})
            self.assertEqual(reply['in_reply_to'],'question')
            segment=audit.export_events();self.assertEqual(audit.verify_segment(segment)['anchor'],segment['anchor'])
            context=build_context(store,'round-1');self.assertEqual(context['authority'],'coordinator_records')
            catalog=recovery_catalog(store,archive,root/'backup');self.assertTrue(catalog['requires_grant_reconciliation'])
            self.assertTrue((root/'backup/coordinator.sqlite3').exists())
