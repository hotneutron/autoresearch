"""Generic workflow publication, newcomer context, evidence and steering safety."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import unittest

from autoresearch_runtime.review import Conflict, Inbox, server
from autoresearch_runtime.workflow import overview_packet, publish_overview


def document():
    return dict(schema_version=1, revision=1, summary="A smaller image improves speed, but quality is not yet proven.",
                prompt_verbatim="Explain what was tried and why; make it useful to a newcomer.", sources=[dict(label="Released image-compression report", path="evidence.json")],
                workflow=dict(kind="overview", project_id="image-compression", project_name="Faster image uploads",
                              goal="Send photographs faster without visible loss of detail.",
                              background="Large photographs take time to upload. We are comparing smaller files before changing the product.",
                              success_criteria=["Uploads become faster while independent image-quality checks still pass."],
                              status="completed", current_question="Does a faster codec preserve quality?", next_checkpoint="Complete the independent quality evaluation.",
                              updated_at="2026-10-12T12:00:00+00:00", glossary=[dict(term="codec", meaning="A method for encoding or compressing an image.")],
                              efforts=[dict(id="small-files", title="Try a faster image encoder", status="completed", question="Can we reduce upload time?",
                                            motivation="File size is a controllable cause of transfer time.", approach="Compare two encoders on the same public images.",
                                            alternatives=[dict(option="Increase network bandwidth", reason="Changes infrastructure and does not isolate the encoding effect.")],
                                            outcome="Files are smaller, but quality evaluation is incomplete.", decision="Do not deploy yet.", rationale="Speed alone does not establish acceptable image quality.",
                                            uncertainty="Quality of unseen images is untested.", next_step="Run a complete independent quality check.", evidence=[0])],
                              feedback_dispositions=[]))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name);(self.repo/"evidence.json").write_text(json.dumps(dict(speedup=1.2)))
        self.inbox=Inbox(self.repo/"store",self.repo)

    def publish(self, doc=None):
        return publish_overview(self.inbox, doc or document())

    def feedback(self, packet, kind="comment", key="comment-1", text="Evaluate unseen images first."):
        return dict(id=key,packet_id=packet['id'],packet_hash=packet['hash'],kind=kind,comment=text,action_id=None)

    def study(self, project="image-compression", revision=1):
        p=overview_packet(document());p.pop('workflow')
        for section in ('changes','limitations'):
            for item in p['narrative'][section]:item.pop('efforts',None)
        p.update(id=f'quality-study-r{revision}',branch='quality-study',revision=revision,project_id=project)
        p['actions']=[dict(id='quality-check',label='Run quality check',eligible=True,requires_approval=True,reason='Needs separate data authorization.')]
        p['review_mode']='decision';return p

    def test_generic_overview_and_immutable_revision(self):
        receipt=self.publish();self.assertTrue(self.publish()['duplicate'])
        p=self.inbox.snapshot()['packets'][0];self.assertEqual(p['project_id'],'image-compression');self.assertEqual(p['actions'],[])
        self.assertIn('motivation',p['workflow']['efforts'][0]);self.assertIn('codec',p['workflow']['glossary'][0]['term'])
        self.assertEqual(p['narrative']['changes'][0]['efforts'],['small-files'])
        self.assertEqual(p['narrative']['limitations'][0]['efforts'],['small-files'])
        changed=document();changed['summary']='A different conclusion.'
        with self.assertRaises(Conflict):self.publish(changed)
        changed['revision']=2;self.publish(changed);self.assertEqual(self.inbox.snapshot()['packets'][0]['previous']['id'],receipt['id'])
        (self.repo/'evidence.json').unlink();self.assertIn('speedup',self.inbox.evidence(receipt['id'],0))

    def test_overview_cannot_approve_pause_or_dispatch(self):
        self.inbox.publish(self.study());self.publish();packets=self.inbox.snapshot()['packets'];p=next(x for x in packets if 'workflow' in x)
        for kind in ('pause','resume','approve','reject'):
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'advisory'):
                self.inbox.submit(self.feedback(p,kind,key=kind))
        with self.assertRaises(ValueError):self.inbox.run(p['branch'],'quality-check','wrong-branch')
        self.inbox.submit(self.feedback(p));self.inbox.checkpoint(p['branch'],'read-comment')
        self.assertFalse(self.inbox.gate('quality-study','quality-check')['runnable'])
        forged=overview_packet(document());forged['actions']=self.study()['actions']
        with self.assertRaisesRegex(ValueError,'advisory-only'):self.inbox.publish(forged)

    def test_links_require_hash_and_same_project_and_mark_stale(self):
        receipt=self.inbox.publish(self.study());doc=document();doc['workflow']['efforts'][0]['target']=dict(packet_id=receipt['id'],packet_hash=receipt['hash']);self.publish(doc)
        p=next(x for x in self.inbox.snapshot()['packets'] if 'workflow' in x)
        self.assertTrue(p['workflow']['efforts'][0]['target']['is_current'])
        self.inbox.publish(self.study(revision=2));p=next(x for x in self.inbox.snapshot()['packets'] if 'workflow' in x)
        self.assertFalse(p['workflow']['efforts'][0]['target']['is_current']);self.assertEqual(p['workflow']['efforts'][0]['target']['current_packet_id'],'quality-study-r2')
        bad=copy.deepcopy(doc);bad['revision']=2;bad['workflow']['efforts'][0]['target']['packet_hash']='0'*64
        with self.assertRaises(Conflict):self.publish(bad)
        other=self.study('other-project');other.update(id='other-r1',branch='other');r=self.inbox.publish(other)
        bad['workflow']['efforts'][0]['target']=dict(packet_id=r['id'],packet_hash=r['hash'])
        with self.assertRaisesRegex(Conflict,'same declared project'):self.publish(bad)

    def test_feedback_disposition_requires_applied_actual_receipt(self):
        self.publish();p=self.inbox.snapshot()['packets'][0];self.inbox.submit(self.feedback(p))
        doc=document();doc['revision']=2;doc['workflow']['feedback_dispositions']=[dict(feedback_id='comment-1',disposition='adopted',reason='Quality evidence is required before deployment.',evidence=[0])]
        with self.assertRaisesRegex(Conflict,'applied feedback'):self.publish(doc)
        self.inbox.checkpoint(p['branch'],'feedback-boundary');self.publish(doc)
        p=self.inbox.snapshot()['packets'][0];self.assertEqual(p['workflow']['feedback_dispositions'][0]['disposition'],'adopted')
        bad=copy.deepcopy(doc);bad['revision']=3;bad['workflow']['feedback_dispositions'][0]['feedback_id']='unknown'
        with self.assertRaises(Conflict):self.publish(bad)

    def test_project_identity_and_branch_kind_cannot_change(self):
        self.publish();p=overview_packet(document());p.pop('workflow')
        for section in ('changes','limitations'):
            for item in p['narrative'][section]:item.pop('efforts',None)
        p['revision']=2;p['id']='image-compression-overview-r2';p['project_id']='image-compression'
        with self.assertRaises(Conflict):self.inbox.publish(p)
        self.inbox.publish(self.study());p=self.study('other-project',2)
        with self.assertRaisesRegex(Conflict,'project identity'):self.inbox.publish(p)

    def test_required_plain_language_and_evidence_validation(self):
        for mutate in (lambda d:d['workflow'].update(background=''),lambda d:d['workflow'].update(updated_at='2026-10-12T12:00:00'),
                       lambda d:d['workflow']['efforts'][0].update(evidence=[True]),lambda d:d['workflow']['efforts'][0].update(evidence=[1]),
                       lambda d:d['workflow']['efforts'][0].update(rationale=''),lambda d:d['workflow'].update(secret_trace='not allowed')):
            bad=document();mutate(bad)
            with self.subTest(value=bad),self.assertRaises((ValueError,TypeError)):self.publish(bad)
        bad=document();bad['workflow']['glossary']*=2
        with self.assertRaises(ValueError):self.publish(bad)
        bad=document();bad['sources'][0]['path']='../outside.json'
        with self.assertRaises(ValueError):self.publish(bad)

    def test_main_cli_publishes_overview_without_campaign_and_no_jobs(self):
        path=self.repo/'overview.json';path.write_text(json.dumps(document()))
        r=subprocess.run([sys.executable,'-m','autoresearch_runtime.cli','--store',str(self.inbox.directory),'review','overview',str(path),'--repo',str(self.repo)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['id'],'image-compression-overview-r1')
        self.assertEqual(self.inbox.snapshot()['jobs'],[])
        r=subprocess.run([sys.executable,'-m','autoresearch_runtime.review','--store',str(self.inbox.directory),'--repo',str(self.repo),'overview',str(path)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['duplicate'])

    def test_http_overview_feedback_and_current_revision_boundary(self):
        self.publish();httpd=server(self.inbox,0);threading.Thread(target=httpd.serve_forever,daemon=True).start()
        self.addCleanup(httpd.server_close);self.addCleanup(httpd.shutdown)
        base=f'http://127.0.0.1:{httpd.server_port}'
        with urllib.request.urlopen(base+'/api/inbox',timeout=2) as response:snapshot=json.load(response)
        packet=snapshot['packets'][0];token=snapshot['token']
        def post(request):
            return urllib.request.urlopen(urllib.request.Request(base+'/api/feedback',data=json.dumps(request).encode(),headers={'Content-Type':'application/json','X-Review-Token':token}),timeout=2)
        with post(self.feedback(packet)) as response:self.assertEqual(response.status,202)
        with self.assertRaises(urllib.error.HTTPError) as error:post(self.feedback(packet,'pause',key='pause'))
        self.assertEqual(error.exception.code,400);error.exception.close()
        self.inbox.checkpoint(packet['branch'],'feedback-checkpoint')
        d=document();d['revision']=2;self.publish(d)
        with self.assertRaises(urllib.error.HTTPError) as error:post(self.feedback(packet,key='stale'))
        self.assertEqual(error.exception.code,409);error.exception.close()
        with urllib.request.urlopen(base+f'/evidence/{packet["id"]}/0',timeout=2) as response:self.assertIn('speedup',response.read().decode())

    def test_offline_export_has_escaped_context_and_no_writing(self):
        d=document();d['workflow']['background']="</script><script>alert('x')</script>";self.publish(d)
        html=self.inbox.html(offline=True);self.assertEqual(html.count('</script>'),1);self.assertIn('\\u003c/script>',html)
        self.assertIn('Why we tried this:',html);self.assertIn('Start here',html);self.assertIn('advisory',html)


if __name__=='__main__':unittest.main()
