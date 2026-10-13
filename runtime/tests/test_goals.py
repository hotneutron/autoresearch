"""Goal-linked admission, drift steering, aggregate accounting and safety.
Revision History: 2026-10-12 — initial portable-project behavioral tests.
2026-10-13 — outer-loop reorientation and selected-candidate binding.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from autoresearch_runtime.controller import Controller
from autoresearch_runtime.goals import GoalLedger, contract_hash
from autoresearch_runtime.protocol import atomic_json, bind_files, sha256
from autoresearch_runtime.review import Conflict

PROMPT = 'Implement goal steering. Preserve the parent goal and charged budget.'
SCRIPT = """import json,pathlib,sys
out=pathlib.Path(sys.argv[1]);(out/'executed').write_text('once')
(out/'result.json').write_text(json.dumps({'ok':True}))
"""


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = self.root / 'released.json'; atomic_json(self.report, {'old_seconds':10})
        self.script = self.root / 'experiment.py'; self.script.write_text(SCRIPT)
        self.ledger = GoalLedger(self.root / 'goal')
        self.goal = dict(schema_version=1,id='goal-r1',revision=1,project_id='image-upload',
            prompt_verbatim=PROMPT,goal='Reduce upload time without image-quality loss.',
            claims=[dict(id='quality-speed',question='Does compression improve upload time at fixed quality?',success_evidence='Matched quality and upload evaluation.')],
            non_goals=['Minimizing CPU variance as an end in itself.'],allowed_scopes=['released-evidence'],
            budget=dict(max_seconds=100,imported_seconds=10,import_evidence=self.evidence()),
            drift_policy=dict(max_diagnostic_campaigns=1,max_diagnostic_seconds=10,max_unchanged_checkpoints=1))
        self.goal_receipt = self.ledger.anchor(self.goal)

    def evidence(self):
        return [dict(path=str(self.report),sha256=sha256(self.report))]

    def config(self, name='campaign'):
        return dict(schema_version=1,id=name,project_id='image-upload',project_root=str(self.root),
            prompt_verbatim=PROMPT,budget=dict(max_units=2,max_seconds=8),tasks={
            n:dict(branch=n,approved=True,argv=[sys.executable,str(self.script),'{output}'],
                closure=bind_files([sys.executable,self.script]),timeout_seconds=3,
                verdict=dict(path='{output}/result.json',checks={'/ok':True})) for n in ('one','two')})

    def proposal(self, config, *, kind='diagnostic', name='proposal', downstream=0):
        return dict(schema_version=1,id=name,prompt_verbatim=PROMPT,goal_hash=self.ledger.snapshot()['goal_hash'],
            campaign_id=config['id'],contract_sha256=contract_hash(config),parent_claim='quality-speed',
            scope='released-evidence',kind=kind,decision='Choose compression candidate.',
            blocker=dict(description='Unknown size/quality tradeoff.',evidence=self.evidence()),
            endpoint_relevance='Measure size at fixed quality, not a timing surrogate.',
            outcomes={k:dict(observation=k,decision='Retain or reject candidate.',action='Review next goal decision.') for k in ('supported','unsupported','inconclusive','invalid')},
            alternatives=[dict(option='No new acquisition',reason='Inspect released paired quality/size evidence first.')],
            budget=dict(campaign_seconds=config['budget']['max_seconds'],downstream_seconds=downstream))

    def assessment(self, proposal, receipt, *, name='review', action='PIVOT', address=True):
        s=self.ledger.snapshot()
        return dict(schema_version=1,id=name,prompt_verbatim=PROMPT,proposal_id=proposal['id'],
            proposal_hash=receipt['hash'],goal_hash=s['goal_hash'],context_hash=s['context_hash'],
            action=action,reason='The outcome will decide a candidate rather than only another variance trial.',
            trigger_dispositions=[dict(trigger=t,reason='Use a goal-linked evidence pivot, preserving old gates.') for t in s['triggers']] if address else [],
            evidence=self.evidence(),next_checkpoint='Full campaign result and goal reassessment.')

    def bind(self, config, *, kind='diagnostic', name='proposal'):
        p=self.proposal(config,kind=kind,name=name); pr=self.ledger.proposal(p)
        a=self.assessment(p,pr,name=name+'-review'); ar=self.ledger.assess(a)
        config['goal_gate']=dict(ledger=str(self.ledger.directory),goal_hash=p['goal_hash'],
            proposal_id=p['id'],proposal_hash=pr['hash'],assessment_id=a['id'],assessment_hash=ar['hash'])
        return p,pr,a,ar

    def cp(self, campaign='campaign', name='complete', outcome='inconclusive', progress=False):
        return dict(schema_version=1,id=name,prompt_verbatim=PROMPT,campaign_id=campaign,outcome=outcome,
            decision_changed=progress,blocker_changed=False,explanation='Full result retained; review parent modeling claim.',evidence=self.evidence())

    def reorientation(self, proposal, *, name='reorient', status='viable', selected=True):
        snapshot=self.ledger.snapshot();checkpoint=snapshot['reorientation_checkpoint']
        candidate=dict(id='compression-pivot',proposal_id=proposal['id'],parent_claim=proposal['parent_claim'],
            scope=proposal['scope'],kind=proposal['kind'],decision=proposal['decision'],
            endpoint_relevance=proposal['endpoint_relevance'],
            novelty='Changes the label/objective path instead of repeating the exhausted variance study.',
            status=status,reason='Directly changes the unresolved quality-speed decision.',
            budget=proposal['budget'],evidence=self.evidence())
        return dict(schema_version=1,id=name,prompt_verbatim='Brainstorm orthogonal next paths.',
            goal_hash=snapshot['goal_hash'],context_hash=snapshot['context_hash'],
            checkpoint_id=checkpoint['id'],checkpoint_hash=checkpoint['hash'],
            unresolved_claim='Does compression improve upload time at fixed quality?',
            exhausted_path='The completed variance-oriented campaign cannot answer the quality endpoint.',
            candidates=[candidate],selected_candidate=candidate['id'] if selected else None,
            no_viable_reason=None if selected else 'No candidate has a qualified complete route.',
            next_checkpoint='Publish the selected exact proposal or report no viable candidate.')

    def test_anchor_immutable_revision_and_historical_accounting(self):
        self.assertTrue(self.ledger.anchor(self.goal)['duplicate'])
        g=copy.deepcopy(self.goal);g['goal']='Different text'
        with self.assertRaises(Conflict):self.ledger.anchor(g)
        g=copy.deepcopy(self.goal);g.update(id='goal-r2',revision=2);g['budget']['imported_seconds']=0
        with self.assertRaisesRegex(Conflict,'reset'):self.ledger.anchor(g)
        g=copy.deepcopy(self.goal);g.update(id='goal-r2',revision=2);g['budget']['max_seconds']=120
        self.ledger.anchor(g)
        self.assertEqual(self.ledger.snapshot()['accounting']['spent_seconds'],10)

    def test_proposal_schema_scope_complete_outcomes_and_finite_cost(self):
        p=self.proposal(self.config())
        for mutate in (lambda p:p.update(scope='private-labels'),lambda p:p['outcomes'].pop('invalid'),
                       lambda p:p['budget'].update(campaign_seconds=float('nan')),
                       lambda p:p.update(parent_claim='other')):
            bad=copy.deepcopy(p);mutate(bad)
            with self.assertRaises(ValueError):self.ledger.proposal(bad)
        self.ledger.proposal(p)
        bad=copy.deepcopy(p);bad['decision']='Changed'
        with self.assertRaises(Conflict):self.ledger.proposal(bad)

    def test_missing_assessment_prevents_actual_dispatch(self):
        c=self.config();p=self.proposal(c);pr=self.ledger.proposal(p)
        c['goal_gate']=dict(ledger=str(self.ledger.directory),goal_hash=p['goal_hash'],proposal_id=p['id'],proposal_hash=pr['hash'],assessment_id='missing',assessment_hash='0'*64)
        controller=Controller(self.root/'campaign',c);controller.submit('one')
        self.assertIn('Goal review required',controller.step()['reasons']['one'])
        self.assertFalse((controller.directory/'trials/one/executed').exists())
        self.assertEqual(self.ledger.snapshot()['accounting']['reserved_seconds'],0)

    def test_intervention_stales_prelaunch_assessment_and_needs_disposition(self):
        c=self.config();p,pr,_,_=self.bind(c)
        self.ledger.control(dict(schema_version=1,id='user-review',prompt_verbatim='Review the original goal.',action='REVIEW',reason='Drifted too far.'))
        self.assertFalse(self.ledger.gate(c,self.root/'campaign')['allowed'])
        a=self.assessment(p,pr,name='fresh',address=False)
        with self.assertRaisesRegex(Conflict,'Unaddressed'):self.ledger.assess(a)
        a=self.assessment(p,pr,name='fresh');ar=self.ledger.assess(a)
        c['goal_gate'].update(assessment_id=a['id'],assessment_hash=ar['hash'])
        self.assertTrue(self.ledger.gate(c,self.root/'campaign')['allowed'])

    def test_explicit_stop_cannot_be_overridden_by_agent_assessment(self):
        c=self.config();p,pr,_,_=self.bind(c)
        self.ledger.control(dict(schema_version=1,id='stop',prompt_verbatim='stop',action='STOP',reason='User stop.'))
        with self.assertRaisesRegex(Conflict,'stop'):self.ledger.assess(self.assessment(p,pr,name='agent-resume'))
        self.ledger.control(dict(schema_version=1,id='resume',prompt_verbatim='resume',action='RESUME',reason='Explicit user resume.'))
        self.ledger.assess(self.assessment(p,pr,name='after-resume'))

    def test_route_budget_not_just_unit_budget(self):
        c=self.config();p=self.proposal(c,downstream=90);pr=self.ledger.proposal(p)
        with self.assertRaisesRegex(Conflict,'route'):self.ledger.assess(self.assessment(p,pr))
        self.ledger.assess(self.assessment(p,pr,action='ASK_HUMAN'))
        self.assertEqual(self.ledger.snapshot()['accounting']['spent_seconds'],10)

    def test_contract_and_evidence_drift_fail_admission(self):
        c=self.config();self.bind(c)
        changed=copy.deepcopy(c);changed['tasks']['one']['approved']=False
        self.assertFalse(self.ledger.gate(changed,self.root/'campaign')['allowed'])
        self.report.write_text('{"changed":true}')
        self.assertFalse(self.ledger.gate(c,self.root/'campaign')['allowed'])

    def test_full_design_finishes_after_goal_intervention_and_settles_once(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two')
        controller.step()
        self.ledger.control(dict(schema_version=1,id='review-running',prompt_verbatim='Review goal.',action='REVIEW',reason='Hold successor, preserve current complete design.'))
        with self.assertRaisesRegex(Conflict,'boundary'):self.ledger.checkpoint(self.cp())
        Controller(controller.directory).run()
        self.assertTrue((controller.directory/'trials/two/executed').exists())
        cp=self.ledger.checkpoint(self.cp())
        self.assertTrue(self.ledger.checkpoint(self.cp())['duplicate'])
        s=self.ledger.snapshot()
        self.assertAlmostEqual(s['accounting']['spent_seconds'],10+cp['charged_seconds'])
        self.assertEqual(s['accounting']['reserved_seconds'],0)
        self.assertIn('diagnostic_campaign_limit',s['triggers']);self.assertIn('unchanged_blocker_limit',s['triggers'])
        self.assertFalse(self.ledger.gate(c,controller.directory)['allowed'])
        c2=self.config('new-campaign');p=self.proposal(c2,name='next')
        with self.assertRaisesRegex(Conflict,'reorientation'):self.ledger.proposal(p)
        self.ledger.reorient(self.reorientation(p));pr=self.ledger.proposal(p)
        with self.assertRaisesRegex(Conflict,'Unaddressed'):self.ledger.assess(self.assessment(p,pr,name='next-review',address=False))
        self.ledger.assess(self.assessment(p,pr,name='next-review'))

    def test_terminal_checkpoint_requires_reorientation_and_binds_selected_candidate(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two');controller.run();self.ledger.checkpoint(self.cp())
        snapshot=self.ledger.snapshot()
        self.assertEqual(snapshot['state'],'reorientation_required')
        self.assertIn('outer_loop_reorientation_required',snapshot['triggers'])
        c2=self.config('orthogonal');p=self.proposal(c2,name='orthogonal-proposal',kind='evidence')
        record=self.reorientation(p);document=self.root/'reorientation.json';atomic_json(document,record)
        receipt=json.loads(subprocess.check_output([sys.executable,'-m','autoresearch_runtime.cli','--store',str(self.ledger.directory),'goal','reorient',str(document)],text=True))
        self.assertFalse(receipt['duplicate'])
        selected=self.ledger.snapshot()
        self.assertEqual(selected['state'],'candidate_selected')
        self.assertEqual(selected['reorientation']['selected_candidate'],'compression-pivot')
        bad=copy.deepcopy(p);bad.update(id='different-proposal')
        with self.assertRaisesRegex(Conflict,'selected reorientation'):self.ledger.proposal(bad)
        pr=self.ledger.proposal(p);a=self.assessment(p,pr,name='orthogonal-review')
        self.assertIn('reorientation:'+record['id'],{item['trigger'] for item in a['trigger_dispositions']})
        self.ledger.assess(a)

    def test_explicit_no_viable_candidate_is_visible_and_blocks_successor(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two');controller.run();self.ledger.checkpoint(self.cp())
        p=self.proposal(self.config('blocked-next'),name='blocked-proposal')
        record=self.reorientation(p,name='no-route',status='blocked',selected=False)
        self.ledger.reorient(record)
        snapshot=self.ledger.snapshot()
        self.assertEqual(snapshot['state'],'rebrainstorm_required')
        with self.assertRaisesRegex(Conflict,'no viable'):self.ledger.proposal(p)
        fresh=self.proposal(self.config('fresh-context'),name='fresh-context-proposal',kind='evidence')
        candidate=dict(id='fresh-source',proposal_id=fresh['id'],parent_claim=fresh['parent_claim'],scope=fresh['scope'],kind=fresh['kind'],decision=fresh['decision'],endpoint_relevance=fresh['endpoint_relevance'],novelty='New authority and infrastructure make this distinct.',status='viable',reason='The prior blocker changed.',budget=fresh['budget'],evidence=self.evidence())
        current=self.ledger.snapshot();parent=current['reorientation']
        record=dict(schema_version=1,id='rebrainstorm-1',prompt_verbatim='Fix the issue then continue.',goal_hash=current['goal_hash'],context_hash=current['context_hash'],parent_id=parent['id'],parent_hash=next(r['hash'] for r in current['records'] if r['kind']=='reorientation' and r['id']==parent['id']),round=1,unresolved_claim='Does compression preserve quality?',novelty_basis=[dict(kind='authority_change',description='User authorized the corrected fresh campaign.',evidence=self.evidence())],candidates=[candidate],selected_candidate='fresh-source',no_viable_reason=None,awaiting_context_change=[],next_checkpoint='Publish selected proposal.')
        self.ledger.rebrainstorm(record)
        self.assertEqual(self.ledger.snapshot()['state'],'candidate_selected')
        self.ledger.proposal(fresh)

    def test_rebrainstorm_without_viable_candidate_waits_for_context_change(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two');controller.run();self.ledger.checkpoint(self.cp())
        p=self.proposal(self.config('blocked-next'),name='blocked-proposal');self.ledger.reorient(self.reorientation(p,name='no-route',status='blocked',selected=False))
        current=self.ledger.snapshot();parent=current['reorientation'];parent_hash=next(r['hash'] for r in current['records'] if r['kind']=='reorientation' and r['id']==parent['id'])
        blocked=dict(id='still-blocked',proposal_id='still-blocked-proposal',parent_claim='quality-speed',scope='released-evidence',kind='diagnostic',decision='Wait for external labels.',endpoint_relevance='No independent labels exist.',novelty='External coordination was checked.',status='blocked',reason='Labels remain unavailable.',budget=dict(campaign_seconds=1,downstream_seconds=0),evidence=self.evidence())
        record=dict(schema_version=1,id='rebrainstorm-wait',prompt_verbatim='Rebrainstorm.',goal_hash=current['goal_hash'],context_hash=current['context_hash'],parent_id=parent['id'],parent_hash=parent_hash,round=1,unresolved_claim='Does compression preserve quality?',novelty_basis=[dict(kind='external_coordination',description='Checked whether an external panel is available.',evidence=self.evidence())],candidates=[blocked],selected_candidate=None,no_viable_reason='External labels remain unavailable.',awaiting_context_change=['An independent label panel becomes available.'],next_checkpoint='Wait for external panel availability.')
        self.ledger.rebrainstorm(record);snapshot=self.ledger.snapshot();self.assertEqual(snapshot['state'],'awaiting_context_change');self.assertEqual(snapshot['reason'],'External labels remain unavailable.')

    def test_reorientation_rejects_stale_context_and_overbudget_viable_candidate(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two');controller.run();self.ledger.checkpoint(self.cp())
        expensive=self.proposal(self.config('expensive'),name='expensive-proposal',downstream=90)
        with self.assertRaisesRegex(Conflict,'aggregate remainder'):
            self.ledger.reorient(self.reorientation(expensive,name='too-expensive'))
        candidate=self.proposal(self.config('fresh'),name='fresh-proposal')
        stale=self.reorientation(candidate,name='stale-reorientation')
        self.ledger.control(dict(schema_version=1,id='review-after-checkpoint',prompt_verbatim='Review again.',action='REVIEW',reason='New evidence arrived.'))
        with self.assertRaisesRegex(Conflict,'stale'):self.ledger.reorient(stale)

    def test_later_goal_revision_is_itself_material_reorientation(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.submit('two');controller.run();self.ledger.checkpoint(self.cp())
        self.assertEqual(self.ledger.snapshot()['state'],'reorientation_required')
        goal=copy.deepcopy(self.goal);goal.update(id='goal-r2',revision=2,goal='Use an independent quality label source.')
        self.ledger.anchor(goal)
        proposal=self.proposal(self.config('new-goal-campaign'),name='new-goal-proposal')
        self.ledger.proposal(proposal)
        self.assertNotIn('outer_loop_reorientation_required',self.ledger.snapshot()['triggers'])

    def test_no_partial_success_checkpoint_or_overlapping_campaign(self):
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.run()
        with self.assertRaisesRegex(Conflict,'All declared'):self.ledger.checkpoint(self.cp())
        other=copy.deepcopy(c)
        with self.assertRaises(Conflict):self.ledger.admit(other,self.root/'replacement')
        p=self.proposal(self.config('second'),name='second');pr=self.ledger.proposal(p)
        with self.assertRaisesRegex(Conflict,'unresolved'):self.ledger.assess(self.assessment(p,pr,name='second-review'))

    def test_scientific_and_approval_gates_remain_independent(self):
        c=self.config();c['tasks']['one']['approved']=False;self.bind(c)
        controller=Controller(self.root/'campaign',c);controller.submit('one')
        self.assertEqual(controller.step()['state'],'idle')
        self.assertEqual(self.ledger.snapshot()['accounting']['reserved_seconds'],0)
        c2=self.config('failed');pre=self.root/'failed-pre.json';atomic_json(pre,{'allowed':False})
        c2['tasks']['one']['requires']=[dict(path=str(pre),checks={'/allowed':True})]
        self.bind(c2,name='failed-proposal')
        controller2=Controller(self.root/'failed',c2)
        self.assertEqual(controller2.submit('one')['state'],'blocked')
        self.assertEqual(controller2.step()['state'],'idle')
        self.assertFalse((controller2.directory/'trials/one/executed').exists())

    def test_changed_goal_revision_invalidates_only_new_admission(self):
        c=self.config();self.bind(c)
        g=copy.deepcopy(self.goal);g.update(id='goal-r2',revision=2,goal='Revisit upload quality first.')
        self.ledger.anchor(g)
        self.assertFalse(self.ledger.gate(c,self.root/'campaign')['allowed'])

    def test_concurrent_admission_reserves_only_one_complete_campaign(self):
        import concurrent.futures
        configs=[]
        for i in range(2):
            c=self.config('parallel-'+str(i));self.bind(c,name='parallel-proposal-'+str(i));configs.append(c)
        def reserve(i):
            try:
                GoalLedger(self.ledger.directory).admit(configs[i],self.root/('parallel-'+str(i)))
                return True
            except Conflict:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(reserve,range(2))),1)
        self.assertEqual(self.ledger.snapshot()['accounting']['reserved_seconds'],8)

    def test_failed_unit_charged_no_valid_checkpoint_or_replacement(self):
        self.script.write_text("import sys;sys.exit(2)\n")
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c)
        controller.submit('one');controller.run()
        with self.assertRaisesRegex(Conflict,'Failed complete unit'):self.ledger.checkpoint(self.cp())
        cp=self.ledger.checkpoint(self.cp(outcome='invalid'))
        self.assertGreater(cp['charged_seconds'],0)
        self.assertAlmostEqual(self.ledger.snapshot()['accounting']['spent_seconds'],10+cp['charged_seconds'])
        with self.assertRaises(Conflict):self.ledger.admit(c,self.root/'replacement')

    def test_active_reservation_survives_restart_and_cap_cannot_shrink(self):
        c=self.config();self.bind(c);self.ledger.admit(c,self.root/'campaign')
        other=GoalLedger(self.ledger.directory)
        self.assertEqual(other.snapshot()['accounting']['reserved_seconds'],8)
        self.assertEqual(other.admit(c,self.root/'campaign')['reserved'],8)
        g=copy.deepcopy(self.goal);g.update(id='goal-r2',revision=2);g['budget']['max_seconds']=15
        with self.assertRaisesRegex(Conflict,'reservations'):other.anchor(g)

    def test_inconclusive_is_not_automatic_rejection_and_held_assessment_cannot_launch(self):
        c=self.config();p=self.proposal(c);pr=self.ledger.proposal(p)
        a=self.assessment(p,pr,action='DEFER');ar=self.ledger.assess(a)
        c['goal_gate']=dict(ledger=str(self.ledger.directory),goal_hash=p['goal_hash'],proposal_id=p['id'],proposal_hash=pr['hash'],assessment_id=a['id'],assessment_hash=ar['hash'])
        self.assertFalse(self.ledger.gate(c,self.root/'campaign')['allowed'])
        a=self.assessment(p,pr,name='reorient',action='PIVOT');ar=self.ledger.assess(a)
        c['goal_gate'].update(assessment_id=a['id'],assessment_hash=ar['hash'])
        self.assertTrue(self.ledger.gate(c,self.root/'campaign')['allowed'])
        self.assertEqual(self.ledger.snapshot()['state'],'ready_for_admission')

    def test_cli_and_live_read_only_review_status(self):
        output=subprocess.check_output([sys.executable,'-m','autoresearch_runtime.cli','--store',str(self.ledger.directory),'goal','status'],text=True)
        self.assertEqual(json.loads(output)['goal']['project_id'],'image-upload')
        c=self.config();self.bind(c);controller=Controller(self.root/'campaign',c);controller.submit('one')
        snapshot=controller.inbox.snapshot()
        self.assertIn('goal_steering',snapshot);self.assertEqual(snapshot['jobs'],[])
        html=controller.inbox.html(offline=True)
        self.assertIn('Goal-level steering',html);self.assertIn('目标级纠偏',html)
        self.assertEqual(self.ledger.snapshot()['accounting']['reserved_seconds'],0)


if __name__=='__main__':unittest.main()
