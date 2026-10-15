"""Rendered source packaging preserves immutable text and offline injection safety.
Revision History: 2026-10-12 — source-report display and template-marker tests.
"""
import json
from pathlib import Path
import tempfile
import unittest

from autoresearch_runtime.review import Inbox
from autoresearch_runtime.workflow import overview_packet
from test_workflow import document


class MarkdownSourceTests(unittest.TestCase):
    def test_exact_source_hash_and_offline_markers_not_interpreted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'report.md'
            raw='# Source\n\n**Evidence**\n\n__MARKDOWN_JS__ __OFFLINE__ __ZH_CN__\n</script><script>alert(1)</script>\n'
            source.write_text(raw);inbox=Inbox(root/'store',root)
            d=document();d['sources']=[dict(label='Markdown report',path='report.md')]
            r=inbox.publish(overview_packet(d));self.assertEqual(inbox.evidence(r['id'],0),raw)
            html=inbox.html(offline=True)
            self.assertEqual(html.count('</script>'),1)
            self.assertIn('"snapshot": "# Source',html)
            self.assertIn('__MARKDOWN_JS__ __OFFLINE__ __ZH_CN__',html)
            self.assertIn('\\u003c/script>',html)
            self.assertIn('function renderMarkdown',html)
            self.assertIn('View raw source',html);self.assertIn('查看原文',html)
            self.assertEqual(inbox.evidence(r['id'],0),raw)

    def test_live_source_modal_has_local_renderer_and_no_network_library(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inbox=Inbox(root/'store',root);html=inbox.html()
            self.assertIn('function markdownLink',html);self.assertNotIn('__MARKDOWN_JS__',html)
            self.assertNotIn('<script src=',html);self.assertNotIn('cdnjs',html)
            self.assertIn('evidence-rendered',html);self.assertIn('aria-labelledby="evidence-title"',html)


if __name__=='__main__':unittest.main()
