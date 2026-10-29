import tempfile
import unittest
import sqlite3
from unittest.mock import patch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from autoresearch_runtime.global_store import GlobalStore, Conflict
from autoresearch_runtime.contracts import digest, seal
from autoresearch_runtime.portable_contract import bind_unit
import sys
from distributed_fixture import unit, round_plan


class GlobalStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = GlobalStore(self.root / "global")
        self.store.register_project({"id": "subject", "goal_sha256": digest("finite-goal"), "budget": {"wall_ms": 100000}})
        self.store.register_host({"id": "host-a", "boot_id": "boot-a", "capacity": 2, "profiles": ["local-direct"]})
        self.units = [unit(self.root, "candidate-" + str(i)) for i in range(4)]
        self.plan = round_plan(self.units)
        self.store.admit_round(self.plan)

    def claim(self, name):
        return self.store.claim({"id": name, "host_id": "host-a", "boot_id": "boot-a", "round_id": "round-1"})

    def request(self, grant, name):
        return {"id": name, "attempt_id": grant["id"], **{k: grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}

    def test_sqlite_busy_and_transaction_rollback_do_not_acknowledge_changes(self):
        second = GlobalStore(self.root / "global", busy_timeout_ms=20)
        with sqlite3.connect(self.store.database) as lock:
            lock.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                second.pause("subject", True)
            lock.rollback()
        with self.store.transaction(write=False) as db:
            self.assertEqual(db.execute("SELECT paused FROM projects WHERE id='subject'").fetchone()[0], 0)
        with self.assertRaises(RuntimeError):
            with self.store.transaction() as db:
                db.execute("UPDATE projects SET paused=1 WHERE id='subject'")
                raise RuntimeError("Interrupted before commit")
        with self.store.transaction(write=False) as db:
            self.assertEqual(db.execute("SELECT paused FROM projects WHERE id='subject'").fetchone()[0], 0)

    def test_sqlite_disk_limit_rolls_back_failed_project_write(self):
        with sqlite3.connect(self.store.database) as db:
            current = db.execute("PRAGMA page_count").fetchone()[0]
        connect = sqlite3.connect
        def limited_connection(*args, **kwargs):
            db = connect(*args, **kwargs)
            db.execute("PRAGMA max_page_count=" + str(current))
            return db
        with patch("autoresearch_runtime.global_store.sqlite3.connect", side_effect=limited_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.register_project({"id": "too-large", "goal_sha256": digest("other"),
                                             "budget": {"wall_ms": 1}, "metadata": "x" * (1024 * 1024)})
        with self.store.transaction(write=False) as db:
            self.assertIsNone(db.execute("SELECT id FROM projects WHERE id='too-large'").fetchone())

    def test_historical_charges_cannot_be_double_imported_under_another_id(self):
        record = {"id": "import-1", "project_id": "subject", "origin": "legacy",
                  "origin_record_id": "campaign-1", "source_sha256": digest("source"), "costs": {"wall_ms": 50}}
        self.store.import_charges(record)
        self.store.import_charges({**record, "id": "renamed"})
        self.assertEqual(self.store.accounting("subject")["charged"], {"wall_ms": 50})

    def test_racing_claims_and_idempotence(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            grants = list(executor.map(self.claim, ["request-" + str(i) for i in range(6)]))
        self.assertEqual(sum(g["state"] == "claimed" for g in grants), 2)
        self.assertEqual(self.claim("request-0"), grants[0])
        self.store.mark_uncertain(next(g["id"] for g in grants if g["state"] == "claimed"))
        self.assertEqual(self.claim("after-timeout")["state"], "no_capacity")
        self.assertEqual(len(GlobalStore(self.root / "global").snapshot()["attempts"]), 2)

    def test_terminal_receipt_charge_and_stale_binding(self):
        grant = self.claim("claim")
        request = self.request(grant, "start")
        out = self.root / "out"; out.mkdir()
        request["binding"] = bind_unit(grant["unit"], {"framework": self.root/"framework", "subject": self.root/"subject", "output": out}, python=sys.executable)
        self.store.authorize_start(request)
        receipt = self.request(grant, "receipt")
        receipt["receipt"] = {"execution_status": "completed", "scientific_pass": True, "evidence_status": "valid", "costs": {"wall_ms": 20}}
        self.store.commit_receipt(receipt); self.store.commit_receipt(receipt)
        self.assertEqual(self.store.accounting("subject")["charged"], {"wall_ms": 20})
        altered = {**receipt, "id": "stale", "generation": 99}
        with self.assertRaises(Conflict): self.store.commit_receipt(altered)
        invalid = {**receipt, "id": "changed", "receipt": {**receipt["receipt"], "execution_status": "interrupted"}}
        with self.assertRaises(Conflict): self.store.commit_receipt(invalid)

    def test_holds_and_never_started_reassignment(self):
        grant = self.claim("claim")
        self.store.pause("subject", True)
        with self.assertRaises(Conflict): self.claim("paused")
        self.store.pause("subject", False)
        request = self.request(grant, "not-started")
        request["receipt"] = {"execution_status": "never_started", "verified_never_started": True, "costs": {"wall_ms": 0}}
        self.store.commit_receipt(request)
        replacement = self.claim("replacement")
        self.assertEqual(replacement["unit_id"], grant["unit_id"])
        self.assertEqual(replacement["generation"], grant["generation"] + 1)
