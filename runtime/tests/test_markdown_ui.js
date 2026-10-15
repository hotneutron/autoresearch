/* Safe Markdown subset and actual source modal, no browser/network dependency.
 * Revision History: 2026-10-12 — source rendering, raw toggle and injection tests.
 */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.dirname(process.argv[2]);
const renderer=fs.readFileSync(path.join(root,'markdown.js'),'utf8');
const context=vm.createContext({URL,String,Math});vm.runInContext(renderer,context);
const render=text=>{context.input=text;return vm.runInContext('renderMarkdown(input)',context);};
let result=render('# Report\n\n## Finding\n\n**Bold** and *emphasis* with `a < b`.\n\n- one\n- two\n\n1. first\n2. second\n\n> Quoted evidence\n\n```python\nx = "<script>"\n```\n\n| Arm | Result |\n| --- | ---: |\n| baseline | 5% |\n');
for(const tag of ['<h1>Report</h1>','<h2>Finding</h2>','<strong>Bold</strong>','<em>emphasis</em>','<code>a &lt; b</code>','<ul>','<ol>','<blockquote>','<table>','&lt;script&gt;'])assert.ok(result.includes(tag),tag);
result=render('Title\n=====\n\nSubtitle\n-----\n\n- parent\n  - child\n\n- [x] complete\n\n| a | b |\n| --- | --- |\n| `x|y` | a\\|b |');
assert.ok(result.includes('<h1>Title</h1>'));assert.ok(result.includes('<h2>Subtitle</h2>'));
assert.ok(result.includes('<li>parent<ul><li>child</li>'));
assert.ok(result.includes('☑ complete'));assert.ok(result.includes('<code>x|y</code>'));assert.ok(result.includes('a|b'));
for(const attack of ['<script>alert(1)</script>','<img src=x onerror=alert(1)>','<svg/onload=alert(1)>','<iframe src="https://evil">','[run](javascript:alert(1))','[run](JaVaScRiPt:alert(1))','[run](data:text/html,x)','[run](vbscript:x)','[run](file:///etc/passwd)','[run](//evil.test/x)','![pixel](https://evil.test/pixel)','[run](java&#x73;cript:alert(1))','[run](https://good.test/\"onmouseover=\"x)']){
 const html=render(attack);assert.ok(!/<script|<img|<svg|<iframe|href="(?:javascript|data|vbscript|file):|onerror=|onmouseover="/i.test(html.replace(/&lt;[^<]*/g,'')),attack);
 assert.ok(!html.includes('<img'),attack);
}
result=render('[safe](https://example.org/report?q=1&x=2) [relative](../REPORT.md) ![diagram](diagram.svg)');
assert.ok(result.includes('href="https://example.org/report?q=1&amp;x=2"'));assert.ok(result.includes('noopener noreferrer'));
assert.ok(!result.includes('href="../'));assert.ok(!result.includes('<img'));
assert.equal(render('~~~\n<script>\n'),'<pre><code>&lt;script&gt;\n</code></pre>');

// Exercise the actual modal live, raw toggle, Chinese, JSON and stale fetch races.
const html=fs.readFileSync(process.argv[2],'utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1].replace('__OFFLINE__','false').replace('__INITIAL_DATA__','null').replace('__ZH_CN__',fs.readFileSync(path.join(root,'zh-CN.json'),'utf8')).replace('__MARKDOWN_JS__',()=>renderer).replace('refresh();if(!OFFLINE)setInterval(refresh,5000);','');
const nodes=new Map();function node(id){if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,setAttribute(){},showModal(){},close(){}});return nodes.get(id);}
let replies=[];
const modal=vm.createContext({document:{documentElement:{lang:'en'},getElementById:node,querySelectorAll:()=>[],title:''},location:{hash:'',search:'',href:'http://127.0.0.1:8765/'},history:{replaceState(){}},setInterval(){},URL,URLSearchParams,Map,JSON,Date,Number,String,crypto:{randomUUID(){return 'id';}},fetch(){return new Promise(resolve=>replies.push(resolve));}});
vm.runInContext(source,modal);
modal.packet={id:'study-r1',sources:[{label:'Readable report',path:'REPORT.md',sha256:'a'.repeat(64)},{label:'Exact result',path:'result.json',sha256:'b'.repeat(64)}]};
(async()=>{
 const pending=vm.runInContext('showEvidence(packet,0)',modal);replies.shift()({ok:true,text:async()=> '# Finding\n\n**Detailed** evidence.'});await pending;
 assert.ok(node('evidence-rendered').innerHTML.includes('<h1>Finding</h1>'));assert.equal(node('evidence-rendered').hidden,false);assert.equal(node('evidence-body').hidden,true);
 node('evidence-toggle').onclick();assert.equal(node('evidence-body').textContent,'# Finding\n\n**Detailed** evidence.');assert.equal(node('evidence-body').hidden,false);
 vm.runInContext("locale='zh-CN';renderEvidence()",modal);assert.ok(node('evidence-toggle').textContent.includes('查看渲染'));
 const old=vm.runInContext('showEvidence(packet,0)',modal),oldReply=replies.shift();
 const next=vm.runInContext('showEvidence(packet,1)',modal),newReply=replies.shift();newReply({ok:true,text:async()=>'{"exact":7}'});await next;oldReply({ok:true,text:async()=> '# Stale'});await old;
 assert.equal(node('evidence-body').textContent,'{"exact":7}');assert.equal(node('evidence-rendered').hidden,true);assert.equal(node('evidence-toggle').hidden,true);
 const closing=vm.runInContext('showEvidence(packet,0)',modal),closedReply=replies.shift();node('close-evidence').onclick();closedReply({ok:true,text:async()=> '# After close'});await closing;
 assert.equal(vm.runInContext('evidenceState',modal),null);
 // Offline path is embedded text, requiring no fetch.
 const offlineSource=source.replace('const OFFLINE = false;','const OFFLINE = true;');
 const offline=vm.createContext({...modal,fetch(){throw new Error('Offline source must not fetch');}});vm.runInContext(offlineSource,offline);offline.packet={id:'off',sources:[{label:'Snapshot',path:'report.md',sha256:'c'.repeat(64),snapshot:'# Offline\n\nEvidence'}]};
 await vm.runInContext('showEvidence(packet,0)',offline);assert.ok(node('evidence-rendered').innerHTML.includes('<h1>Offline</h1>'));
 process.stdout.write('Safe Markdown, live/raw/Chinese/offline modal and stale-fetch checks passed.\n');
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
