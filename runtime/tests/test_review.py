"""Integration checks for the human/runner boundary, without GPU experiments."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoresearch_runtime.review import Conflict, Inbox, server


class ReviewWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "evidence.md").write_text("Frozen experiment result: labels invalid.\n")
        self.inbox = Inbox(self.repo / "store", self.repo)

    def packet(self, branch="study", revision=1):
        return {"schema_version": 1, "id": f"{branch}-r{revision}", "branch": branch,
            "revision": revision, "contract_id": "contract-v1", "title": "A result",
            "question": "Does it generalize?", "takeaway": "Measurements failed; the model remains untested.",
            "why_it_matters": "Diagnose measurement before fitting.", "changed": ["New data collected"],
            "limitations": ["No valid labels"], "evidence_status": "invalid", "decision": "No fitting",
            "review_mode": "decision", "review_question": "Authorize a new diagnostic?",
            "recommendation": "Inspect existing evidence first", "review_by": "Next available review",
            "metrics": [{"name": "Labels", "baseline": "Qualified labels", "result": "0", "rule": "Valid labels required", "scope": "Corpus", "source": 0}],
            "sources": [{"label": "Report", "path": "evidence.md"}],
            "actions": [
                {"id": "summarize", "label": "Summarize released evidence", "eligible": True, "requires_approval": False,
                 "reason": "Authorized existing-data task", "argv": [sys.executable, "-c", "from pathlib import Path; Path('completed').write_text('yes')"]},
                {"id": "diagnose", "label": "New diagnostic", "eligible": True, "requires_approval": True, "reason": "New scope needs explicit approval"},
                {"id": "fit", "label": "Fit model", "eligible": False, "requires_approval": True, "reason": "Labels invalid"}]}

    def publish(self, packet=None):
        self.p = packet or self.packet()
        self.published = self.inbox.publish(self.p)
        return self.published

    def feedback(self, kind, action=None, text="", *, packet=None, key=None):
        p = packet or self.p
        return {"id": key or str(uuid.uuid4()), "packet_id": p["id"],
            "packet_hash": self.inbox.publish(p)["hash"], "kind": kind,
            "action_id": action, "comment": text}

    def http(self):
        httpd = server(self.inbox, 0)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        base = f"http://127.0.0.1:{httpd.server_port}"
        with urllib.request.urlopen(base + "/api/inbox", timeout=2) as response:
            token = json.load(response)["token"]
        return base, token

    def post(self, base, token, body):
        request = urllib.request.Request(base + "/api/feedback", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Review-Token": token})
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 202)
            return json.load(response)

    def test_pending_review_does_not_block_another_action_or_branch(self):
        self.publish()
        self.inbox.publish(self.packet("other"))
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])
        self.assertFalse(self.inbox.gate("study", "fit")["runnable"])
        self.assertTrue(self.inbox.gate("study", "summarize")["runnable"])
        result = self.inbox.run("other", "summarize", "batch-1")
        self.assertEqual(result["returncode"], 0)
        self.assertEqual((self.repo / "completed").read_text(), "yes")
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])

    def test_comment_and_read_receipt_are_not_approval(self):
        self.publish()
        text = "Keep all failed samples.\nDo not change the frozen gate."
        self.inbox.submit(self.feedback("comment", text=text))
        self.inbox.submit(self.feedback("ack"))
        receipt = self.inbox.checkpoint("study", "review-1")
        self.assertEqual(receipt["feedback"][0]["comment"], text)
        self.assertIn("advisory", receipt["feedback"][0]["reason"])
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])
        self.assertTrue(self.inbox.gate("study", "summarize")["runnable"])

    def test_web_feedback_during_execution_applies_at_next_checkpoint(self):
        p = self.packet()
        p["actions"][0]["argv"] = [sys.executable, "-c", "from pathlib import Path; import time; Path('started').write_text('yes'); time.sleep(1.2); Path('completed').write_text('yes')"]
        self.publish(p)
        base, token = self.http()
        with ThreadPoolExecutor() as pool:
            job = pool.submit(self.inbox.run, "study", "summarize", "batch-1")
            deadline = time.monotonic() + 4
            while not (self.repo / "started").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((self.repo / "started").exists())
            result = self.post(base, token, self.feedback("pause", text="Pause after the complete pair."))
            self.assertEqual(result["status"], "queued")
            self.assertFalse(job.done(), "HTTP review must remain available while execution is active")
            self.assertTrue(self.inbox.gate("study", "summarize")["runnable"])
            self.assertEqual(job.result(timeout=4)["returncode"], 0)
        # Replaying a checkpoint does not consume events that arrived later.
        self.assertEqual(self.inbox.checkpoint("study", "batch-1")["feedback"], [])
        self.inbox.checkpoint("study", "batch-2")
        self.assertEqual(self.inbox.gate("study", "summarize")["state"], "paused")

    def test_approval_never_overrides_a_hard_gate_and_is_revision_bound(self):
        self.publish()
        with self.assertRaises(ValueError):
            self.inbox.submit(self.feedback("approve", "fit"))
        self.inbox.submit(self.feedback("approve", "diagnose"))
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])
        self.inbox.checkpoint("study", "one")
        self.assertTrue(self.inbox.gate("study", "diagnose")["runnable"])
        self.inbox.publish(self.packet(revision=2))
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])
        self.assertFalse(self.inbox.gate("study", "fit")["runnable"])

    def test_stale_queued_feedback_has_no_effect_and_old_submission_is_rejected(self):
        self.publish()
        request = self.feedback("approve", "diagnose")
        self.inbox.submit(request)
        self.inbox.publish(self.packet(revision=2))
        receipt = self.inbox.checkpoint("study", "next")
        self.assertEqual(receipt["feedback"][0]["status"], "stale")
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])
        request["id"] = str(uuid.uuid4())
        base, token = self.http()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post(base, token, request)
        self.assertEqual(error.exception.code, 409)
        error.exception.close()

    def test_feedback_retries_are_idempotent_and_conflicts_rejected(self):
        self.publish()
        request = self.feedback("comment", text="A single comment.")
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda _: self.inbox.submit(request), range(4)))
        self.assertEqual(len({r["seq"] for r in responses}), 1)
        self.assertEqual(len(self.inbox.checkpoint("study", "once")["feedback"]), 1)
        changed = {**request, "comment": "Different feedback under the same id"}
        with self.assertRaises(Conflict):
            self.inbox.submit(changed)

    def test_resume_preserves_unanswered_approvals_and_other_branches(self):
        self.publish()
        self.inbox.publish(self.packet("other"))
        self.inbox.submit(self.feedback("pause"))
        self.inbox.checkpoint("study", "pause")
        self.assertTrue(self.inbox.gate("other", "summarize")["runnable"])
        self.p = self.packet(revision=2)
        self.inbox.publish(self.p)
        self.assertFalse(self.inbox.gate("study", "summarize")["runnable"])
        self.inbox.submit(self.feedback("resume"))
        self.inbox.checkpoint("study", "resume")
        self.assertTrue(self.inbox.gate("study", "summarize")["runnable"])
        self.assertFalse(self.inbox.gate("study", "diagnose")["runnable"])

    def test_frozen_source_and_dispatch_cannot_be_silently_reused(self):
        self.publish()
        self.assertEqual(self.inbox.run("study", "summarize", "first")["returncode"], 0)
        with self.assertRaises(Conflict):
            self.inbox.run("study", "summarize", "first")
        (self.repo / "evidence.md").write_text("Changed after publication")
        with self.assertRaises(Conflict):
            self.inbox.run("study", "summarize", "second")
        self.assertIn("labels invalid", self.inbox.evidence(self.p["id"], 0))

    def test_html_snapshot_embeds_sources_as_text_and_web_requires_local_token(self):
        (self.repo / "evidence.md").write_text("</script><script>throw new Error('unsafe')</script>")
        p = self.packet()
        p["title"] = "<img src=x onerror=alert(1)>"
        self.publish(p)
        html = self.inbox.html(offline=True)
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn("\\u003c/script>", html)
        base, _ = self.http()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post(base, "wrong-token", self.feedback("ack"))
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + "/evidence/../../evidence.md", timeout=2)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_publication_is_immutable_and_revisions_are_consecutive(self):
        published = self.publish()
        self.assertTrue(self.inbox.publish(self.p)["duplicate"])
        self.assertEqual(self.inbox.publish(self.p)["hash"], published["hash"])
        changed = {**self.p, "takeaway": "A different conclusion"}
        with self.assertRaises(Conflict):
            self.inbox.publish(changed)
        with self.assertRaises(Conflict):
            self.inbox.publish(self.packet(revision=3))
        self.inbox.publish(self.packet(revision=2))
        self.assertEqual(self.inbox.snapshot()["packets"][0]["previous"]["id"], "study-r1")


if __name__ == "__main__":
    unittest.main()
