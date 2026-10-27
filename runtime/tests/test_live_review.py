"""Live observations must not mutate scientific/review authority.

Prompt verbatim: looks like the review dashboard is no longer updating
## Revision History
- 2026-10-20: Fresh observations, provider failure isolation, immutable packets and
  unchanged approval state through the generic read-only adapter.
- 2026-10-20: Use a valid metric-bearing packet fixture; protocol validation stays unchanged.
"""
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request

from autoresearch_runtime.live_review import LiveInbox
from autoresearch_runtime.review import Inbox, server


class LiveReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "report.md").write_text("# Frozen report\n\nNo promotion.\n")
        self.inbox = Inbox(self.root / "store", self.root)
        self.packet = {"schema_version": 1, "id": "study-r1", "branch": "study", "revision": 1,
            "contract_id": "frozen", "title": "A study", "question": "Does it work?", "takeaway": "Not yet known.",
            "why_it_matters": "The complete result is pending.", "changed": ["A unit started"], "limitations": ["No outcome"],
            "evidence_status": "diagnostic", "decision": "Wait", "review_mode": "fyi", "review_question": "Read the pending scope.",
            "recommendation": "Do not promote.", "review_by": "At completion", "metrics": [
                {"name": "Qualified models", "baseline": "Required", "result": "0", "rule": "Complete evidence required", "scope": "Study", "source": 0}],
            "sources": [{"label": "Report", "path": "report.md"}],
            "actions": [{"id": "fit", "label": "Fit", "eligible": True, "requires_approval": True, "reason": "Named authority required"}]}
        self.published = self.inbox.publish(self.packet)

    def test_observation_changes_without_new_packet_or_permission(self):
        value = {"summary": "Unit running", "active_campaign": "campaign", "units": [{"id": "fit", "elapsed_seconds": 10}]}
        live = LiveInbox(self.inbox, lambda: value)
        first = live.snapshot()
        value["units"][0]["elapsed_seconds"] = 15
        second = live.snapshot()
        self.assertEqual(first["live_status"]["units"][0]["elapsed_seconds"], 10)
        self.assertEqual(second["live_status"]["units"][0]["elapsed_seconds"], 15)
        self.assertTrue(second["live_status"]["read_only"])
        self.assertEqual(first["packets"][0]["hash"], second["packets"][0]["hash"])
        self.assertFalse(self.inbox.gate("study", "fit")["runnable"])
        self.assertEqual(self.inbox.evidence("study-r1", 0), "# Frozen report\n\nNo promotion.\n")

    def test_failed_callback_is_explicit_and_reports_remain_available(self):
        def fail():
            raise ValueError("Worker identity cannot be verified")
        snapshot = LiveInbox(self.inbox, fail).snapshot()
        self.assertFalse(snapshot["live_status"]["available"])
        self.assertEqual(snapshot["live_status"]["observation_error"], "ValueError")
        self.assertIn("cannot be verified", snapshot["live_status"]["summary"])
        self.assertEqual(snapshot["packets"][0]["id"], "study-r1")

    def test_http_returns_fresh_observation_no_store_and_no_auto_publish(self):
        value = {"summary": "Live", "units": []}
        httpd = server(LiveInbox(self.inbox, lambda: value), 0)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{httpd.server_port}/api/inbox"
        for title in ("Live", "Complete"):
            value["summary"] = title
            with urllib.request.urlopen(url, timeout=2) as response:
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(json.load(response)["live_status"]["summary"], title)
        self.assertEqual(len(self.inbox.snapshot()["packets"]), 1)


if __name__ == "__main__":
    unittest.main()
