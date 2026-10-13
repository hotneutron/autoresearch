"""Behavioral qualification for durable execution and the human review boundary."""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
import uuid

from autoresearch_runtime.controller import Controller
from autoresearch_runtime.protocol import atomic_json, bind_files, sha256
from autoresearch_runtime.review import Conflict, Inbox
from autoresearch_runtime.store import migrate


SCRIPT = '''import json, pathlib, sys, time
out=pathlib.Path(sys.argv[1])
time.sleep(float(sys.argv[2]))
(out/'executed').write_text('once')
(out/'result.json').write_text(json.dumps({'schema_version':1,'allowed':sys.argv[3]=='yes','value':7}))
'''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script = self.root / "experiment.py"
        self.script.write_text(SCRIPT)
        self.pre = self.root / "prerequisite.json"
        atomic_json(self.pre, {"modeling_allowed": True})
        self.config = {"schema_version": 1, "id": "qualification", "project_root": str(self.root),
                       "prompt_verbatim": "Run bounded integration checks.",
                       "budget": {"max_units": 4, "max_seconds": 20},
                       "lease_root": str(self.root / "leases"), "tasks": {}}
        for name in ("one", "two"):
            self.config["tasks"][name] = {"branch": name, "title": name, "approved": True,
                "argv": [sys.executable, str(self.script), "{output}", "0", "yes"],
                "closure": bind_files([sys.executable, self.script]), "timeout_seconds": 3,
                "requires": [{"path": str(self.pre), "checks": {"/modeling_allowed": True}}],
                "verdict": {"path": "{output}/result.json", "checks": {"/schema_version": 1, "/allowed": True}},
                "report_metrics": [{"name": "Value", "key": "value", "pointer": "/value", "unit": "count",
                    "support": 1, "baseline": "7", "baseline_id": "fixed", "comparison_key": "fixture-v1",
                    "rule": "Fixture value", "scope": "Fixture",}]}
        self.store = self.root / "store"

    def controller(self):
        return Controller(self.store, self.config)

    def feedback(self, c, branch, kind, action=None):
        p = next(p for p in c.inbox.snapshot()["packets"] if p["branch"] == branch)
        return c.inbox.submit({"id": uuid.uuid4().hex, "packet_id": p["id"], "packet_hash": p["hash"],
                               "kind": kind, "action_id": action, "comment": "Preserved feedback"})

    def test_project_id_is_carried_into_study_packets(self):
        self.config['project_id'] = 'portable-project'
        c = self.controller(); c.submit('one'); c.run()
        p = c.inbox.snapshot()['packets'][0]
        self.assertEqual(p['project_id'], 'portable-project')
        self.assertEqual(p['contract_id'], 'qualification')
        self.assertEqual(c.status()['units'][0]['state'], 'completed')

    def test_A03_A08_completed_process_can_fail_scientific_gate(self):
        self.config["tasks"]["one"]["argv"][-1] = "no"
        c = self.controller()
        c.submit("one")
        c.run()
        result = json.loads(c.status()["units"][0]["result"])
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["scientific_pass"])
        self.assertEqual(c.inbox.snapshot()["packets"][0]["evidence_status"], "invalid")

    def test_A07_prerequisite_blocks_fit_and_cannot_be_approved(self):
        atomic_json(self.pre, {"modeling_allowed": False})
        self.config["tasks"]["one"]["approved"] = False
        c = self.controller()
        self.assertEqual(c.submit("one")["state"], "blocked")
        with self.assertRaises(ValueError):
            self.feedback(c, "one", "approve", "one")
        c.run()
        self.assertFalse((self.store / "trials/one/executed").exists())

    def test_A04_A19_idle_approval_allows_only_its_action(self):
        self.config["tasks"]["one"]["approved"] = False
        c = self.controller()
        c.submit("one")
        c.submit("two")
        self.feedback(c, "one", "comment")
        self.feedback(c, "one", "ack")
        c.run()
        self.assertTrue((self.store / "trials/two/executed").exists())
        self.assertFalse((self.store / "trials/one/executed").exists())
        self.feedback(c, "one", "approve", "one")
        Controller(self.store).run()
        self.assertTrue((self.store / "trials/one/executed").exists())

    def test_A19_idle_resume_is_consumed_without_dispatch_first(self):
        c = self.controller()
        c.submit("one")
        self.feedback(c, "one", "pause")
        self.assertEqual(c.step()["state"], "idle")
        self.feedback(c, "one", "resume")
        c.run()
        self.assertTrue((self.store / "trials/one/executed").exists())

    def test_A09_controller_restart_reconciles_detached_worker(self):
        self.config["tasks"]["one"]["argv"][-2] = "0.3"
        c = self.controller()
        c.submit("one")
        self.assertEqual(c.step()["state"], "running")
        other = Controller(self.store)
        other.run()
        self.assertEqual(other.status()["units"][0]["state"], "completed")
        self.assertEqual(len(other.inbox.snapshot()["packets"]), 1)

    def test_A09_unknown_launch_is_never_automatically_retried(self):
        c = self.controller()
        c.submit("one")
        with c.inbox.connect(write=True) as db:
            db.execute("UPDATE units SET state='launching' WHERE id='one'")
        self.assertEqual(Controller(self.store).step()["state"], "reconciliation_required")
        self.assertFalse((self.store / "trials/one/executed").exists())

    def test_A09_durable_outbox_survives_publication_failure(self):
        c = self.controller()
        original = c.inbox.publish
        def fail(_):
            raise OSError("simulated reporting outage")
        c.inbox.publish = fail
        with self.assertRaises(OSError):
            c.submit("one")
        self.assertEqual(c.status()["pending_publications"], 1)
        other = Controller(self.store)
        other.run()
        self.assertEqual(other.status()["pending_publications"], 0)
        self.assertEqual(other.status()["units"][0]["state"], "completed")

    def test_A10_logical_unit_cannot_be_reissued_with_new_name(self):
        c = self.controller()
        c.submit("one")
        c.run()
        with self.assertRaises(Conflict):
            c.submit("one", "new-checkpoint")
        self.assertEqual(c.submit("one")["state"], "completed")
        c.run()
        with c.inbox.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM journal WHERE kind='launch_reserved'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_A11_executable_source_drift_prevents_dispatch(self):
        c = self.controller()
        c.submit("one")
        self.script.write_text(SCRIPT + "\n# drift\n")
        self.assertIn("changed", c.step()["reasons"]["one"])
        self.assertFalse((self.store / "trials/one/executed").exists())

    def test_A11_environment_binding_is_enforced(self):
        key = "AUTORESEARCH_TEST_BINDING"
        self.config["tasks"]["one"]["required_host_env"] = {key: os.environ.get(key)}
        c = self.controller()
        c.submit("one")
        old = os.environ.get(key)
        os.environ[key] = "changed"
        try:
            self.assertIn("environment changed", c.step()["reasons"]["one"])
        finally:
            if old is None:
                os.environ.pop(key)
            else:
                os.environ[key] = old

    def test_A12_timeout_invalidates_whole_unit(self):
        self.config["tasks"]["one"]["argv"][-2] = "10"
        self.config["tasks"]["one"]["timeout_seconds"] = 0.15
        c = self.controller()
        c.submit("one")
        c.run()
        row = c.status()["units"][0]
        self.assertEqual(row["state"], "interrupted")
        self.assertFalse(json.loads(row["result"])["scientific_pass"])
        self.assertFalse((self.store / "trials/one/executed").exists())

    def test_A13_budget_prevents_another_complete_unit(self):
        self.config["budget"]["max_units"] = 1
        c = self.controller()
        c.submit("one")
        c.submit("two")
        result = c.run()
        self.assertIn("Budget", result["reasons"]["two"])
        self.assertFalse((self.store / "trials/two/executed").exists())

    def test_A13_resource_lease_excludes_another_campaign(self):
        self.config["tasks"]["one"]["resources"] = ["gpu:fixture-uuid"]
        c = self.controller()
        c.submit("one")
        handles = c.acquire_resources(self.config["tasks"]["one"])
        try:
            self.assertEqual(c.step()["state"], "idle")
            self.assertFalse((self.store / "trials/one/executed").exists())
        finally:
            for fd in handles:
                os.close(fd)
        c.run()
        self.assertTrue((self.store / "trials/one/executed").exists())

    def test_A06_revised_packet_cannot_authorize_old_job(self):
        self.config["tasks"]["one"]["approved"] = False
        c = self.controller()
        c.submit("one")
        self.feedback(c, "one", "approve", "one")
        c.feedback()
        p = copy.deepcopy(c.inbox.snapshot()["packets"][0])
        for key in ("hash", "published", "acknowledged", "previous"):
            p.pop(key, None)
        p.update(id="one-r2", revision=2)
        c.inbox.publish(p)
        c.run()
        self.assertFalse((self.store / "trials/one/executed").exists())

    def test_A17_typed_metric_must_match_source(self):
        c = self.controller()
        c.submit("one")
        c.run()
        p = copy.deepcopy(c.inbox.snapshot()["packets"][0])
        p.update(id="one-r3", revision=3)
        p["metrics"][0]["value"] = 8
        with self.assertRaises(Conflict):
            c.inbox.publish(p)

    def test_A02_lossless_migration_keeps_hashes_and_pauses(self):
        c = self.controller()
        c.submit("one")
        self.feedback(c, "one", "pause")
        c.feedback()
        source = c.inbox.database
        source_hash = sha256(source)
        dest = self.root / "migrated"
        result = migrate(source, dest, self.store)
        migrated = Inbox(dest, self.store)
        self.assertEqual(migrated.snapshot()["packets"][0]["hash"], c.inbox.snapshot()["packets"][0]["hash"])
        self.assertEqual(migrated.gate("one", "one")["state"], "paused")
        self.assertEqual(result["counts"]["feedback"], 1)
        self.assertEqual(sha256(source), source_hash)

    def test_A15_steering_preserves_prompt_and_limits_next_tasks(self):
        c = self.controller()
        record = {"id": "pivot", "action": "PIVOT", "trigger": "diagnostic evidence", "evidence": [str(self.pre)],
                  "alternatives": ["continue", "diagnose"], "reason": "Discriminate an explanation", "next_tasks": ["two"],
                  "budget": {"units": 1}, "invalidation": ["candidate features"], "next_checkpoint": "complete-unit",
                  "prompt_verbatim": "Inspect the mechanism.\nKeep the original gate."}
        self.assertEqual(c.steer(record), record)
        record["next_tasks"] = ["unapproved-new-tool"]
        with self.assertRaises(ValueError):
            c.steer(record)

    def test_contextual_narrative_from_fixed_result_and_bad_pointer_fails_report(self):
        from test_narrative import narrative
        n=narrative()
        self.config['tasks']['one']['review_narrative']={'pending':n}
        self.config['tasks']['one']['review_changed']={'pending':['Prepared a complete size/quality comparison.']}
        self.config['tasks']['one']['report_narrative_pointer']='/narrative'
        self.script.write_text(SCRIPT+"\n(out/'result.json').write_text(json.dumps({'schema_version':1,'allowed':True,'value':7,'narrative':"+repr(n)+"}))\n")
        for task in self.config['tasks'].values():task['closure']=bind_files([sys.executable,self.script])
        c=self.controller();c.submit('one')
        self.assertEqual(c.inbox.snapshot()['packets'][0]['narrative'],n)
        c.run();self.assertEqual(c.inbox.snapshot()['packets'][0]['narrative'],n)
        self.assertTrue(json.loads(c.status()['units'][0]['result'])['scientific_pass'])

    def test_missing_completed_narrative_is_not_fabricated(self):
        self.config['tasks']['one']['report_narrative_pointer']='/missing'
        c=self.controller();c.submit('one');c.run()
        result=json.loads(c.status()['units'][0]['result'])
        self.assertTrue(result['scientific_pass'])
        self.assertEqual(result,json.loads((self.store/'trials/one/receipt.json').read_text()))
        p=c.inbox.snapshot()['packets'][0]
        self.assertEqual(p['evidence_status'],'invalid');self.assertIn('Report schema failure',p['takeaway'])
        self.assertNotIn('narrative',p)

    def test_A16_unqualified_confirmation_backend_fails_closed(self):
        self.config["tasks"]["one"]["confirmation"] = True
        with self.assertRaisesRegex(ValueError, "access boundary"):
            self.controller()

    def test_A18_newer_database_schema_is_rejected(self):
        c = self.controller()
        with c.inbox.connect(write=True) as db:
            db.execute("PRAGMA user_version=999")
        with self.assertRaisesRegex(Conflict, "newer store schema"):
            Controller(self.store)

    def test_A02_migrated_review_cli_needs_no_campaign_contract(self):
        import subprocess
        c = self.controller()
        c.submit("one")
        with c.inbox.connect() as db:
            packet = json.loads(db.execute("SELECT body FROM packets").fetchone()[0])
        legacy = Inbox(self.root / "legacy", self.store)
        legacy.publish(packet)
        output = subprocess.check_output([sys.executable, "-m", "autoresearch_runtime.cli", "--store",
                                          str(legacy.directory), "review", "status"], text=True)
        self.assertEqual(json.loads(output)["packets"][0]["id"], packet["id"])

    def test_A13_child_retains_lease_if_worker_is_killed(self):
        import signal
        from autoresearch_runtime.worker import alive
        self.config["tasks"]["one"]["argv"][-2] = "2"
        self.config["tasks"]["one"]["resources"] = ["gpu:orphan-child"]
        c = self.controller()
        c.submit("one")
        dispatched = c.step()
        process_file = self.store / "trials/one/process.json"
        deadline = time.monotonic() + 3
        while not process_file.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(process_file.exists())
        child = json.loads(process_file.read_text())
        try:
            os.kill(dispatched["worker_pid"], signal.SIGKILL)
            time.sleep(.05)
            self.assertTrue(alive(child))
            with self.assertRaises(BlockingIOError):
                c.acquire_resources(self.config["tasks"]["one"])
            self.assertEqual(c.step()["state"], "reconciliation_required")
        finally:
            if alive(child):
                os.killpg(child["pid"], signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
