import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from autoresearch_runtime.artifacts import ArtifactStore
from autoresearch_runtime.global_store import GlobalStore
from autoresearch_runtime.hosting import server
from autoresearch_runtime.host_agent import Client, HostAgent
from autoresearch_runtime.contracts import digest, seal
from autoresearch_runtime.protocol import atomic_json
from autoresearch_runtime.supervised_job import run
from distributed_fixture import unit, round_plan


class FixtureSupervisor:
    """Synchronous CPU fixture, explicitly not qualified independent supervision."""
    def __init__(self, root): self.root=Path(root);self.results={}
    def query(self, attempt): return {"state":"terminal","receipt":self.results[attempt]} if attempt in self.results else {"state":"never_registered"}
    def start(self, attempt, spec):
        path=self.root/attempt;path.mkdir(exist_ok=True)
        atomic_json(path/'job.json',seal(spec));self.results[attempt]=run(path/'job.json')
        return self.query(attempt)


class HostingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.store=GlobalStore(self.root/'global');self.archive=ArtifactStore(self.root/'archive')
        self.http=server(self.store,self.archive,port=0)
        threading.Thread(target=self.http.serve_forever,daemon=True).start()
        self.addCleanup(self.http.server_close);self.addCleanup(self.http.shutdown)
        self.url='http://127.0.0.1:'+str(self.http.server_port)
    def post(self,path,body):
        request=Request(self.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':'https://another.example'},method='POST')
        with urlopen(request,timeout=5) as response:
            self.assertEqual(response.headers['Access-Control-Allow-Origin'],'*')
            return json.load(response)
    def test_anonymous_reads_writes_and_hash_boundary(self):
        self.post('/integration/v1/projects/register',{'id':'subject','goal_sha256':digest('finite-goal'),'budget':{'wall_ms':100000}})
        blob=self.post('/api/artifacts',{'data':base64.b64encode(b'released evidence').decode()})
        with urlopen(self.url+'/evidence/'+blob['sha256']) as response:self.assertEqual(response.read(),b'released evidence')
        with urlopen(Request(self.url+'/api/artifacts',method='OPTIONS')) as response:self.assertEqual(response.status,200)
        with self.assertRaises(HTTPError):urlopen(self.url+'/evidence/../private')
        self.post('/api/messages',{'id':'message','project_id':'subject','text':'Reviewer question'})
        with urlopen(self.url+'/api/messages') as response:self.assertEqual(json.load(response)['items'][0]['actor_assurance'],'poc_anonymous')
    def test_host_fixture_round_trip_has_no_authentication(self):
        self.store.register_project({'id':'subject','goal_sha256':digest('finite-goal'),'budget':{'wall_ms':100000}})
        plan=round_plan([unit(self.root)]);self.store.admit_round(plan)
        supervisor=FixtureSupervisor(self.root/'supervisor');supervisor.root.mkdir()
        client=Client(self.url,allow_local_http=True)
        agent=HostAgent(client,supervisor,self.root/'agent',{'id':'host','boot_id':'boot','capacity':1,'profiles':['local-direct']},{'framework':self.root/'framework','subject':self.root/'subject'})
        agent.enroll();grant=agent.claim('round-1');agent.start(grant);receipt=agent.reconcile(grant['id'])
        self.assertEqual(receipt['state'],'completed')
        self.assertEqual(self.store.snapshot()['units'][0]['state'],'completed')
        self.assertEqual(agent.reconcile(grant['id']),receipt)
        self.assertEqual(len(self.store.events()),4)
