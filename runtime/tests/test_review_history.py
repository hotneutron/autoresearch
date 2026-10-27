"""Immutable paginated report history and historical permission safety.

Exact user prompt is preserved in review_history.py.
## Revision History
- 2026-10-21T01:31:00Z: >131 revisions, immutable hashes/evidence, paging,
  exact retrieval, read-only historical actions, HTTP endpoints and bad input.
"""
import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from autoresearch_runtime.review import Inbox,Conflict,server
from autoresearch_runtime.live_review import LiveInbox

class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.inbox=Inbox(self.root,self.root);(self.root/'evidence.md').write_text('# Exact historical evidence\n')
  self.base={'schema_version':2,'id':'report-r1','branch':'report','revision':1,'contract_id':'c','title':'First result','question':'Did it qualify?','takeaway':'Valid failure','why_it_matters':'Every gate','changed':['New evidence'],'limitations':['No promotion'],'evidence_status':'diagnostic','decision':'Reorient','review_mode':'fyi','review_question':'Inspect next experiment','recommendation':'Continue','review_by':'Next checkpoint','metrics':[],'sources':[{'label':'Evidence','path':'evidence.md'}],'actions':[{'id':'next','label':'Next experiment','reason':'Independent','eligible':True,'requires_approval':False}]}
  for i in range(1,133):self.inbox.publish({**self.base,'id':f'report-r{i}','revision':i,'title':f'Result {i}'})
 def test_all_revisions_paged_and_first_last(self):
  p=self.inbox.history('report',0,50);self.assertEqual(p['total'],132);self.assertEqual(p['items'][0]['revision'],132);self.assertEqual(p['series'][0]['first_packet_id'],'report-r1');self.assertEqual(p['series'][0]['latest_packet_id'],'report-r132');ids=[]
  while True:
   ids += [r['id'] for r in p['items']]
   if p['next_offset'] is None:break
   p=self.inbox.history('report',p['next_offset'],50)
  self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(ids),132);self.assertEqual(ids[-1],'report-r1')
 def test_exact_historical_packet_is_read_only_and_evidence_unchanged(self):
  with self.inbox.connect() as db:before=db.execute('select hash,body from packets where id=?',('report-r1',)).fetchone()
  p=self.inbox.report('report-r1')['packet'];self.assertTrue(p['archive_read_only']);self.assertFalse(p['actions'][0]['runnable']);self.assertFalse(p['actions'][0]['eligible']);self.assertEqual(p['hash'],before['hash']);self.assertEqual(p['revision_navigation']['newer'],'report-r2');self.assertEqual(p['revision_navigation']['latest'],'report-r132');self.assertEqual(self.inbox.evidence(p['id'],0),'# Exact historical evidence\n');self.assertFalse(self.inbox.report('report-r132')['packet']['archive_read_only'])
  with self.assertRaises(Conflict):self.inbox.submit({'id':'old-comment','packet_id':p['id'],'packet_hash':p['hash'],'kind':'comment','action_id':None,'comment':'Old'})
  with self.inbox.connect() as db:after=db.execute('select hash,body from packets where id=?',('report-r1',)).fetchone()
  self.assertEqual(tuple(before),tuple(after))
 def test_bad_history_inputs(self):
  for args in [('report',-1,50),('report',0,101),('../report',0,50)]:
   with self.assertRaises(ValueError):self.inbox.history(*args)
  with self.assertRaises(ValueError):self.inbox.report('missing')
 def test_http_history_and_packet(self):
  h=server(LiveInbox(self.inbox,lambda:{'summary':'Live separate'}),0);thread=threading.Thread(target=h.serve_forever,daemon=True);thread.start();self.addCleanup(h.server_close);self.addCleanup(h.shutdown)
  base=f'http://127.0.0.1:{h.server_port}'
  with urllib.request.urlopen(base+'/api/history?branch=report&limit=50') as r:p=json.load(r)
  self.assertEqual(p['total'],132)
  with urllib.request.urlopen(base+'/api/report/report-r1') as r:p=json.load(r)
  self.assertTrue(p['packet']['archive_read_only'])
  with urllib.request.urlopen(base+'/api/experiments') as r:p=json.load(r)
  self.assertFalse(p['available'])
  with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/api/history?offset=-1')

if __name__=='__main__':unittest.main()
