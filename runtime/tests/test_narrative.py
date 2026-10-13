"""Generic source-backed review explanations, not inferred science or permits.
Revision History: 2026-10-12 — initial narrative schema/builder/locale tests.
2026-10-13 — workflow-effort cross-reference validation.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from autoresearch_runtime.narrative import validate
from autoresearch_runtime.review import Inbox, Conflict
from autoresearch_runtime.workflow import overview_packet
from test_workflow import document


def narrative():
    return dict(schema_version=1,
        changes=[dict(id='size-change',title='Smaller photos, quality still unknown',before='Large original photos took longer to upload.',after='The new encoder produced20% smaller files on the same images.',why_it_matters='Transfer size improved, so quality—not further compression—is the next decision.',evidence=[0])],
        limitations=[dict(id='quality-gap',question='Will unseen photos retain detail?',why_unanswered='Only file size has been measured; no visual-quality study has run.',goal_impact='Speed alone does not meet the product goal of preserving photo detail.',next_evidence='An independent quality comparison on unseen images.',evidence=[0])],
        insights=[dict(id='size-evidence',title='Reduced bytes do not yet mean better photos',comparison='Two encoders on the same images and fixed upload settings.',support='Illustrative fixture only; no experimental population is claimed.',finding='File bytes decreased20%; visual quality remains unmeasured.',interpretation='Smaller files could reduce transfer time, but this does not test quality.',goal_relevance='The next useful test is quality rather than more size reduction.',caveat='No unseen images or production traffic were evaluated.',evidence=[0])])


class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'evidence.json').write_text('{"speedup":1.2}')
        self.inbox=Inbox(self.root/'store',self.root)

    def test_builder_context_overrides_and_derived_defaults(self):
        d=document();d.update(narrative=narrative(),changed=['Smaller files replace original files in this comparison.'],limitations=['Quality of unseen images is still unmeasured.'])
        p=overview_packet(d);self.inbox.publish(p)
        self.assertEqual(p['changed'],d['changed']);self.assertEqual(p['limitations'],d['limitations'])
        self.assertEqual(p['narrative'],d['narrative']);self.assertEqual(p['actions'],[])
        default=overview_packet(document())
        self.assertIn('quality',default['changed'][0]);self.assertIn('independent quality',default['limitations'][0])
        self.assertNotIn('private internal', ' '.join(default['limitations']))
        self.assertEqual(default['narrative']['insights'][0]['interpretation'],document()['workflow']['efforts'][0]['rationale'])
        self.assertEqual(default['narrative']['changes'][0]['efforts'],['small-files'])
        self.assertEqual(default['narrative']['limitations'][0]['efforts'],['small-files'])

    def test_related_efforts_are_canonical_and_must_exist_in_workflow(self):
        n=narrative();n['changes'][0]['efforts']=['small-files'];n['limitations'][0]['efforts']=['small-files']
        validate(n,1,{'small-files'})
        d=document();d['narrative']=n;self.inbox.publish(overview_packet(d))
        bad=copy.deepcopy(n);bad['changes'][0]['efforts']=['unknown-effort']
        with self.assertRaisesRegex(ValueError,'unknown workflow effort'):validate(bad,1,{'small-files'})
        with self.assertRaisesRegex(ValueError,'require a workflow'):validate(n,1)

    def test_schema_rejects_missing_context_bad_refs_and_duplicate_ids(self):
        for section,key in [('changes','before'),('limitations','goal_impact'),('insights','interpretation')]:
            n=narrative();n[section][0].pop(key)
            with self.subTest(section=section),self.assertRaises(ValueError):validate(n,1)
        for bad in ([],[True],[1],[0,0]):
            n=narrative();n['insights'][0]['evidence']=bad
            with self.subTest(refs=bad),self.assertRaises(ValueError):validate(n,1)
        n=narrative();n['insights']*=2
        with self.assertRaises(ValueError):validate(n,1)

    def test_narrative_requires_schema2_and_is_immutable(self):
        p=overview_packet(document());p['narrative']=narrative();self.inbox.publish(p)
        changed=copy.deepcopy(p);changed['narrative']['insights'][0]['interpretation']='A different explanation.'
        with self.assertRaises(Conflict):self.inbox.publish(changed)
        changed.update(id='image-compression-overview-r2',revision=2);self.inbox.publish(changed)
        old=copy.deepcopy(p);old.update(schema_version=1,id='legacy-r1',branch='legacy');old.pop('workflow')
        with self.assertRaises(ValueError):self.inbox.publish(old)

    def test_locale_can_only_overlay_matching_text(self):
        p=overview_packet(document());p['narrative']=narrative()
        p['translations']={'zh-CN':{'narrative':{'insights':[dict(id='size-evidence',title='文件更小，但质量仍未知',interpretation='尚未检验画面质量。')]}}}
        self.inbox.publish(p)
        for mutation in ('id','evidence','authority'):
            x=copy.deepcopy(p);x.update(id='image-compression-overview-r2',revision=2)
            item=x['translations']['zh-CN']['narrative']['insights'][0]
            if mutation=='id':item['id']='different'
            elif mutation=='evidence':item['evidence']=[0]
            else:item['eligible']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.inbox.publish(x)

    def test_empty_workflow_no_fabricated_observations_and_escaped_export(self):
        d=document();d['workflow']['efforts']=[]
        p=overview_packet(d);self.assertIn('No completed study',p['narrative']['insights'][0]['support'])
        self.inbox.publish(p)
        p=overview_packet(document());p.update(revision=2,id='image-compression-overview-r2');p['narrative']=narrative()
        p['narrative']['insights'][0]['finding']='</script><script>not executable</script>'
        self.inbox.publish(p);html=self.inbox.html(offline=True)
        self.assertEqual(html.count('</script>'),1);self.assertIn('\\u003c/script>',html)
        self.assertIn('what the findings mean',html);self.assertIn('Technical detail',html)
        self.assertEqual(self.inbox.snapshot()['jobs'],[])


if __name__=='__main__':unittest.main()
