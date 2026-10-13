"""Display-only locale data cannot alter scientific evidence or approvals."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from autoresearch_runtime.review import Inbox, Conflict
from autoresearch_runtime.workflow import overview_packet
from test_workflow import document


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'evidence.json').write_text('{"value":7}')
        self.inbox=Inbox(self.root/'store',self.root)
        self.packet=overview_packet(document())
        self.packet['translations']={'zh-CN':{'title':'图片上传研究 · 从这里开始','takeaway':'这是示例，不是实验结论。',
            'workflow':{'project_name':'图片上传研究','goal':'更快上传图片并保持质量。','efforts':[{'id':'small-files','motivation':'文件大小可控。','outcome':'质量评估尚未完成。'}]}}}

    def test_translation_is_hash_bound_display_text_and_evidence_unchanged(self):
        before=copy.deepcopy(self.packet);r=self.inbox.publish(self.packet)
        self.assertEqual(before,self.packet)
        actual=self.inbox.snapshot()['packets'][0];self.assertEqual(actual['translations']['zh-CN']['title'],'图片上传研究 · 从这里开始')
        self.assertEqual(actual['actions'],[]);self.assertEqual(self.inbox.evidence(r['id'],0),'{"value":7}')
        changed=copy.deepcopy(self.packet);changed['translations']['zh-CN']['title']='不同翻译'
        with self.assertRaises(Conflict):self.inbox.publish(changed)
        changed.update(revision=2,id='image-compression-overview-r2');r2=self.inbox.publish(changed);self.assertNotEqual(r['hash'],r2['hash'])

    def test_translation_rejects_authority_identity_and_numeric_changes(self):
        for key,value in [('actions',[{'eligible':True}]),('sources',[{'path':'private.json'}]),('metrics',[{'value':999}]),('project_id','other'),('revision',3),('workflow',{'status':'running'})]:
            p=copy.deepcopy(self.packet);p['translations']['zh-CN']={key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):self.inbox.publish(p)
        p=copy.deepcopy(self.packet);p['translations']['zh-CN']['workflow']['efforts'][0]['id']='other-effort'
        with self.assertRaises(ValueError):self.inbox.publish(p)
        p=copy.deepcopy(self.packet);p['translations']['zh-CN']['workflow']['efforts'][0]['evidence']=[0]
        with self.assertRaises(ValueError):self.inbox.publish(p)

    def test_alignment_locale_and_text_shape_rejected(self):
        for change in ({'workflow':{'efforts':[]}},{'changed':['extra','items','wrong-length']},{'title':3}):
            p=copy.deepcopy(self.packet);p['translations']['zh-CN']=change
            with self.assertRaises(ValueError):self.inbox.publish(p)
        p=copy.deepcopy(self.packet);p['translations']={'zh-TW':{'title':'not supported'}}
        with self.assertRaises(ValueError):self.inbox.publish(p)

    def test_overview_builder_passes_only_validated_display_translations(self):
        d=document();d['translations']=self.packet['translations'];p=overview_packet(d);self.inbox.publish(p)
        self.assertEqual(p['workflow']['project_id'],'image-compression')
        self.assertEqual(self.inbox.snapshot()['jobs'],[])
        template=self.inbox.html(offline=True)
        self.assertIn('简体中文',template);self.assertNotIn('__ZH_CN__',template)
        self.assertIn('来源证据和反馈保留原始语言',template)


if __name__=='__main__':unittest.main()
