"""Terminal receipt qualification, including cooperative timeout behavior."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from autoresearch_runtime.protocol import atomic_json, bind_files
from autoresearch_runtime.worker import execute
from autoresearch_runtime.controller import Controller


class WorkerTests(unittest.TestCase):
    def test_restart_rejects_contradictory_terminal_receipt_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            script = root / "experiment.py"
            script.write_text("print('frozen')")
            config = {"schema_version": 1, "id": "receipt-check", "project_root": str(root),
                      "prompt_verbatim": "Check terminal receipt reconciliation.",
                      "budget": {"max_units": 1, "max_seconds": 3},
                      "tasks": {"one": {"branch": "one", "approved": True,
                          "argv": [sys.executable, str(script)], "closure": bind_files([sys.executable, script]),
                          "timeout_seconds": 1, "verdict": {"path": "{output}/result.json", "checks": {"/allowed": True}}}}}
            controller = Controller(root / "store", config)
            controller.submit("one")
            with controller.inbox.connect(write=True) as db:
                db.execute("UPDATE units SET state='launching' WHERE id='one'")
            receipt_path = root / "store/trials/one/receipt.json"
            atomic_json(receipt_path, {"execution_status": "interrupted", "returncode": 0,
                                      "scientific_pass": True, "evidence_status": "valid", "wall_seconds": .2})
            original = receipt_path.read_bytes()
            reopened = Controller(root / "store")
            reopened.reconcile()
            self.assertEqual(reopened.status()["units"][0]["state"], "reconciliation_required")
            self.assertEqual(receipt_path.read_bytes(), original)
            with reopened.inbox.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM packets").fetchone()[0], 1)

    def test_execution_receipt_preserves_terminal_validity(self):
        for mode in ("success", "failed_check", "timeout"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                script = root / "subject.py"
                script.write_text("""import json,signal,sys,time
from pathlib import Path
def finish(*args):
    Path(sys.argv[1]).write_text(json.dumps({'allowed':sys.argv[2]!='failed_check'}))
    sys.exit(0)
signal.signal(signal.SIGTERM,finish)
if sys.argv[2]=='timeout':
    while True: time.sleep(.01)
finish()
""")
                spec = {"argv": [sys.executable, str(script), str(root / "result.json"), mode],
                        "cwd": str(root), "env": {}, "closure": bind_files([sys.executable, script]),
                        "timeout_seconds": .2 if mode == "timeout" else 2,
                        "verdict": {"path": str(root / "result.json"), "checks": {"/allowed": True}}}
                atomic_json(root / "spec.json", spec)
                execute(root / "spec.json")
                receipt = json.loads((root / "receipt.json").read_text())
                self.assertEqual(receipt["returncode"], 0)
                self.assertEqual(receipt["execution_status"], "interrupted" if mode == "timeout" else "completed")
                self.assertEqual(receipt["scientific_pass"], mode == "success")
                self.assertEqual(receipt["evidence_status"], "valid" if mode == "success" else "invalid")
                self.assertGreater(receipt["wall_seconds"], 0)
