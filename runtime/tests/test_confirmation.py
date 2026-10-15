"""Procedural confirmation contracts, without claims of OS access isolation."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from autoresearch_runtime.confirmation import begin, ledger, run, validate
from autoresearch_runtime.controller import Controller
from autoresearch_runtime.protocol import atomic_json, bind_files, sha256
from autoresearch_runtime.review import Conflict


VERIFIER = '''import json,sys
data=json.load(open(sys.argv[1]))
model=json.load(open(sys.argv[2]))
errors=[abs(row['y']-model['slope']*row['x']) for row in data['observations'].values()]
print(json.dumps({'schema_version':1,'accepted':max(errors)==0,'mae':sum(errors)/len(errors),'support':len(errors)}))
'''


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.checkout=self.root/'checkout';self.checkout.mkdir()
        self.verifier=self.checkout/'verify.py';self.verifier.write_text(VERIFIER)
        self.candidate=self.checkout/'model.json';atomic_json(self.candidate,{'slope':2})
        for args in (['init','-q'],['add','.'],['-c','user.name=Runtime test','-c','user.email=runtime@example.invalid','commit','-qm','Freeze fixture']):
            subprocess.run(['git','-C',str(self.checkout),*args],check=True,capture_output=True)
        commit=subprocess.check_output(['git','-C',str(self.checkout),'rev-parse','HEAD'],text=True).strip()
        self.data=self.root/'private/labels.json'
        atomic_json(self.data,{'schema_version':1,'observations':{'a':{'x':1,'y':2},'b':{'x':2,'y':4}}})
        self.spec={'isolation_mode':'procedural','purpose':'protocol_fixture','checkout':str(self.checkout),
                   'candidate_commit':commit,'candidate':{'path':str(self.candidate),'sha256':sha256(self.candidate)},
                   'verifier':{'path':str(self.verifier),'sha256':sha256(self.verifier)},
                   'dataset':{'id':'fixture','namespace':'qualification','path':str(self.data),'sha256':sha256(self.data),'subjects':['a','b'],'previously_exposed':False},
                   'ledger_path':str(self.root/'exposure.sqlite3'),'request_id':'first',
                   'private_log_directory':str(self.root/'private/logs'),
                   'verifier_argv':[sys.executable,str(self.verifier),'{dataset}','{candidate}'],
                   'verifier_timeout_seconds':2,
                   'released_fields':{'schema_version':'int','accepted':'bool','mae':'number','support':'int'}}

    def test_single_opening_releases_only_declared_aggregates(self):
        begin(self.spec)
        result=run(self.spec,self.root/'out')
        self.assertTrue(result['protocol_valid'])
        self.assertEqual(result['aggregate']['mae'],0)
        self.assertFalse(result['raw_labels_released'])
        self.assertNotIn('observations',json.dumps(result))
        with self.assertRaises(Conflict):begin(self.spec)

    def test_new_campaign_or_dataset_name_cannot_reopen_same_data(self):
        begin(self.spec)
        changed=copy.deepcopy(self.spec);changed['request_id']='renamed';changed['dataset']['id']='renamed'
        with self.assertRaises(Conflict):begin(changed)

    def test_overlapping_subjects_stay_exposed_after_interrupted_opening(self):
        begin(self.spec)  # Simulate a controller failure before evaluator launch.
        atomic_json(self.data,{'observations':{'a':{'x':3,'y':6},'b':{'x':4,'y':8}}})
        changed=copy.deepcopy(self.spec);changed['request_id']='later';changed['dataset']['id']='later';changed['dataset']['sha256']=sha256(self.data)
        with self.assertRaises(Conflict):begin(changed)

    def test_dirty_checkout_and_exposed_fresh_data_are_rejected(self):
        fresh=copy.deepcopy(self.spec);fresh['purpose']='fresh_confirmation';fresh['dataset']['previously_exposed']=True
        with self.assertRaises(Conflict):validate(fresh)
        self.candidate.write_text('{"slope":3}')
        with self.assertRaises(Conflict):validate(self.spec)

    def test_proxy_itself_cannot_reuse_an_opening(self):
        begin(self.spec);run(self.spec,self.root/'out')
        with self.assertRaises(Conflict):run(self.spec,self.root/'second-out')

    def test_wrong_subject_manifest_consumes_opening_without_releasing_data(self):
        self.spec['dataset']['subjects']=['different']
        begin(self.spec);result=run(self.spec,self.root/'out')
        self.assertFalse(result['protocol_valid'])
        self.assertNotIn('aggregate',result)
        with ledger(self.spec['ledger_path']) as db:
            self.assertEqual(db.execute('SELECT status FROM openings').fetchone()[0],'failed')

    def test_runtime_reserves_opening_and_blocks_repeat_in_another_store(self):
        spec=copy.deepcopy(self.spec);spec.pop('request_id')
        task={'branch':'confirmation','approved':True,
              'argv':[sys.executable,'-m','autoresearch_runtime.confirmation','--spec','{output}/confirmation.json','--out','{output}'],
              'closure':bind_files([sys.executable,self.candidate,self.verifier,self.data]),
              'confirmation':spec,'timeout_seconds':5,
              'verdict':{'path':'{output}/result.json','checks':{'/protocol_valid':True,'/aggregate/accepted':True}}}
        config={'schema_version':1,'id':'confirm-fixture','project_root':str(self.checkout),'prompt_verbatim':'Run a procedural protocol fixture.',
                'budget':{'max_units':1,'max_seconds':5},'tasks':{'evaluate':task}}
        c=Controller(self.root/'runtime',config);c.submit('evaluate');c.run()
        self.assertEqual(c.status()['units'][0]['state'],'completed')
        config['id']='renamed-campaign'
        other=Controller(self.root/'other',config)
        self.assertEqual(other.submit('evaluate')['state'],'blocked')
        other.run()
        self.assertFalse(other.inbox.gate('confirmation','evaluate')['runnable'])

    def test_unexpected_verifier_output_is_retained_privately_not_released(self):
        self.verifier.write_text(VERIFIER.replace("'support':len(errors)","'support':len(errors),'observations':data['observations']"))
        subprocess.run(['git','-C',str(self.checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.checkout),'-c','user.name=Runtime test','-c','user.email=runtime@example.invalid','commit','-qm','Freeze invalid-output fixture'],check=True,capture_output=True)
        self.spec['candidate_commit']=subprocess.check_output(['git','-C',str(self.checkout),'rev-parse','HEAD'],text=True).strip()
        self.spec['verifier']['sha256']=sha256(self.verifier)
        begin(self.spec);result=run(self.spec,self.root/'out')
        self.assertFalse(result['protocol_valid'])
        self.assertNotIn('observations',json.dumps(result))
        self.assertTrue((self.root/'private/logs/first.stdout').exists())


if __name__=='__main__':unittest.main()
