import tempfile
import unittest
import sys
from pathlib import Path
from autoresearch_runtime.contracts import digest,seal
from autoresearch_runtime.failure_index import revisit
from autoresearch_runtime.plan_delta import apply_delta,condition_state
from autoresearch_runtime.plan_delta import materialize_subject_plan
from distributed_fixture import git_repo
from autoresearch_runtime.stall import assess_stall
from autoresearch_runtime.hooks import run_hook
from autoresearch_runtime.protocol import bind_files
from autoresearch_runtime.capabilities import probe,eligible


class LearningTests(unittest.TestCase):
    def test_revisit_requires_changed_evidence(self):
        prior={'id':'failed','reason':'Resource contention','assumption_sha256':digest('old')}
        with self.assertRaises(ValueError):revisit(prior,{'id':'retry','assumption_sha256':digest('old')})
        result=revisit(prior,{'id':'retry','assumption_sha256':digest('new'),'evidence_sha256':digest('evidence'),'change_reason':'Cache removed contention'})
        self.assertTrue(result['requires_reviewed_round'])
    def test_delta_inherits_conditions_and_invalidates_approval(self):
        plan={'budget':10,'required_conditions':['correctness'],'prompt_verbatim':'Evaluate the bounded CPU fixture.'}
        delta=seal({'id':'delta','prior_plan_sha256':digest(plan),'changes':[{'pointer':'/budget','before':10,'after':12,'evidence_ids':['e1']}]})
        result=apply_delta(plan,delta,{'e1':digest('evidence')})
        self.assertEqual(result['plan']['budget'],12);self.assertEqual(plan['budget'],10)
        condition=condition_state('correctness',plan)
        self.assertEqual(condition_state('correctness',{'changed':True},{**condition,'state':'passed'})['state'],'pending')
        bad=seal({'id':'bad','prior_plan_sha256':digest(plan),'changes':[{'pointer':'/required_conditions','before':['correctness'],'after':[],'evidence_ids':['e1']}]})
        with self.assertRaises(ValueError):apply_delta(plan,bad,{'e1':digest('evidence')})
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "subject"
            ref = git_repo(repository, {"baseline.txt": "frozen"})
            committed = materialize_subject_plan(repository, ".plan/next.md", result,
                expected_head=ref["commit"], approved_delta_sha256=delta["sha256"])
            self.assertTrue(committed["requires_successor_round_review"])
            self.assertNotEqual(committed["subject_commit"], ref["commit"])
            self.assertIn("## Revision History", (repository / ".plan/next.md").read_text())
    def test_stall_and_advisory_bounded_hook(self):
        rounds=[{'id':'r'+str(i),'sealed':True,'valid':True,'benchmark_sha256':digest('benchmark'),'improvement':0} for i in range(2)]
        self.assertEqual(assess_stall(rounds,{'window':2,'epsilon':.1,'action':'hold'})['state'],'stalled')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=root/'hook.py';script.write_text("print('advisory only')")
            spec={'id':'hook','argv':[sys.executable,str(script)],'cwd':str(root),'closure':bind_files([sys.executable,script]),'timeout_ms':1000,'max_output_bytes':8}
            result=run_hook(spec)
            self.assertEqual(result['stdout'],'advisory');self.assertTrue(result['truncated']);self.assertFalse(result['grants_approval'])
        profile=probe();self.assertTrue(eligible(profile,{'os':profile['os']})['allowed'])
