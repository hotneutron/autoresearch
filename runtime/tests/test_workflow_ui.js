/* Exercise the actual inline inbox renderer with a minimal DOM, no network. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html=fs.readFileSync(process.argv[2], 'utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace('__OFFLINE__','false').replace('__INITIAL_DATA__','null')
  .replace('__MARKDOWN_JS__',()=>fs.readFileSync(require('node:path').join(require('node:path').dirname(process.argv[2]),'markdown.js'),'utf8'))
  .replace('__ZH_CN__',fs.readFileSync(require('node:path').join(require('node:path').dirname(process.argv[2]),'zh-CN.json'),'utf8'))
  .replace('refresh();if(!OFFLINE)setInterval(refresh,5000);','');
const nodes=new Map();
function node(id){
  if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,setAttribute(){},showModal(){},close(){}});
  return nodes.get(id);
}
const context=vm.createContext({document:{documentElement:{lang:'en'},getElementById:node,querySelectorAll:()=>[],title:''},location:{hash:'',search:'',href:'http://127.0.0.1:8765/'},history:{replaceState(){}},setInterval(){},URL,URLSearchParams,Map,JSON,Date,Number,String,crypto:{randomUUID(){return 'feedback-id';}}});
vm.runInContext(source,context);
const ordinary={id:'study-r2',branch:'study',contract_id:'campaign',title:'Image quality check',revision:2,published:'2026-10-12T12:00:00Z',actions:[],question:'Are smaller files clear?',takeaway:'Quality is unproven.',why_it_matters:'Speed is not enough.',evidence_status:'diagnostic',decision:'Wait',review_mode:'fyi',review_question:'Inspect quality first.',recommendation:'No deployment yet.',review_by:'Next checkpoint',changed:['Compared encoders'],limitations:['No unseen-image test'],metrics:[],sources:[{label:'Image result',path:'result.json',sha256:'a'.repeat(64)}],historical:false,acknowledged:false};
const workflow={kind:'overview',project_id:'images',project_name:'Faster photographs',goal:'Upload pictures faster without losing detail.',background:'New here? Large pictures take time to send.',success_criteria:['Faster uploads and acceptable quality.'],status:'completed',current_question:'Does speed preserve quality?',next_checkpoint:'Independent quality evaluation.',updated_at:'2026-10-12T12:00:00Z',glossary:[{term:'codec',meaning:'An image encoding method.'}],efforts:[{id:'encoder',title:'Smaller images',status:'completed',question:'Can we reduce transfer time?',motivation:'Size is controllable.',approach:'Compare two encoders.',alternatives:[{option:'More bandwidth',reason:'Would confound this comparison.'}],outcome:'Smaller files; quality not proven.',decision:'Defer deployment',rationale:'A useful product needs quality, not only speed.',uncertainty:'Unseen pictures remain untested.',next_step:'Evaluate them.',evidence:[0],target:{packet_id:'study-r1',packet_hash:'b'.repeat(64),is_current:false,current_packet_id:'study-r2'}}],feedback_dispositions:[]};
const overview={...ordinary,id:'images-overview-r1',branch:'images-overview',title:'Faster photographs · Start here',workflow};
context.fixture={packets:[ordinary,overview],feedback:[],generated:'2026-10-12T12:00:00Z'};
node('filter').value='all';
vm.runInContext('data=fixture;render();',context);
let detail=node('detail').innerHTML;
assert.match(detail,/Start here · Faster photographs/);
for(const text of ['Why we tried this:','What we did:','Other options considered','Outcome:','Decision:','Reason:','What remains uncertain:','Next step:','Plain-language glossary','How to steer safely'])assert.ok(detail.includes(text),text);
assert.ok(detail.includes('data-study="study-r2"'));
assert.ok(detail.includes('Linked result is historical'));
assert.ok(detail.includes('no runnable action'));
assert.ok(!detail.includes('<strong>Research can continue</strong>'));
assert.equal(node('kind').innerHTML,'<option value="comment">Suggest a direction / ask a question (advisory)</option>');
assert.ok(node('list').innerHTML.indexOf('Start here')<node('list').innerHTML.indexOf('Image quality check'));
node('filter').value='overview';vm.runInContext('renderList()',context);assert.ok(!node('list').innerHTML.includes('data-packet="study-r2"'));
node('filter').value='all';node('search').value='codec';vm.runInContext('renderList()',context);assert.ok(node('list').innerHTML.includes('images-overview-r1'));
workflow.background='<img src=x onerror=alert(1)>';context.fixture.packets[1].workflow=workflow;node('search').value='';vm.runInContext("detailSignature='';render()",context);
assert.ok(node('detail').innerHTML.includes('&lt;img'));assert.ok(!node('detail').innerHTML.includes('<img src=x'));
vm.runInContext("selected='study-r2';detailSignature='';render()",context);assert.ok(!node('detail').innerHTML.includes('What we tried, why, and what we learned'));
overview.translations={'zh-CN':{title:'更快上传照片 · 从这里开始',workflow:{project_name:'更快上传照片',goal:'更快上传照片，同时保留细节。',efforts:[{id:'encoder',title:'更小的图片',motivation:'文件大小可以控制。',outcome:'文件变小；质量尚未得到证明。'}]}}};
context.fixture.packets[1]=overview;
vm.runInContext("selected='images-overview-r1';setLocale('zh-CN')",context);
assert.equal(context.document.documentElement.lang,'zh-CN');
for(const text of ['从这里开始 · 更快上传照片','为什么尝试：','文件大小可以控制。','如何安全地指导研究','来源证据和反馈保留原始语言'])assert.ok(node('detail').innerHTML.includes(text),text);
assert.ok(node('kind').innerHTML.includes('仅作为建议'));
const localized=vm.runInContext('viewPacket(fixture.packets[1])',context);
assert.equal(localized.id,overview.id);assert.equal(localized.workflow.efforts[0].target.packet_id,'study-r1');assert.deepEqual(Array.from(localized.workflow.efforts[0].evidence),[0]);
assert.equal(overview.workflow.efforts[0].motivation,'Size is controllable.');
node('comment').value='请保留所有失败样本';node('comment').oninput();
vm.runInContext("setLocale('en')",context);assert.equal(node('comment').value,'请保留所有失败样本');assert.ok(node('detail').innerHTML.includes('Start here · Faster photographs'));
context.fixture.goal_steering={state:'candidate_selected',reason:'Outer loop selected a candidate',goal:{goal:'Predict <unseen> workloads'},accounting:{spent_seconds:10,reserved_seconds:0,max_seconds:20},triggers:['reorientation:reorient-1'],reorientation:{id:'reorient-1',unresolved_claim:'Predict unseen workloads',exhausted_path:'Repeated timing diagnostics <failed>',selected_candidate:'new-label-source',no_viable_reason:null,next_checkpoint:'Publish the exact proposal.',candidates:[{id:'new-label-source',status:'viable',decision:'Test independent labels',novelty:'Uses another source',reason:'Direct endpoint evidence',budget:{campaign_seconds:4,downstream_seconds:6}}]}};
vm.runInContext("detailSignature='';render()",context);
assert.ok(node('detail').innerHTML.includes('Goal-level steering'));
assert.ok(node('detail').innerHTML.includes('Predict &lt;unseen&gt; workloads'));
assert.ok(node('detail').innerHTML.includes('10 / 0 / 20'));
assert.ok(node('detail').innerHTML.includes('Outer-loop reorientation'));
assert.ok(node('detail').innerHTML.includes('new-label-source'));
assert.ok(node('detail').innerHTML.includes('Repeated timing diagnostics &lt;failed&gt;'));
assert.ok(node('detail').innerHTML.includes('not private chain-of-thought'));
vm.runInContext("setLocale('zh-CN')",context);
assert.ok(node('detail').innerHTML.includes('目标级纠偏'));
assert.ok(node('detail').innerHTML.includes('外层循环重新定向'));
assert.ok(node('detail').innerHTML.includes('已选择新的候选路径'));
assert.ok(node('detail').innerHTML.includes('不能覆盖科学门槛'));
overview.narrative={schema_version:1,changes:[{id:'size',title:'Compare file size',before:'Original files were large.',after:'Files are smaller.',why_it_matters:'Evaluate quality next.',evidence:[0]}],limitations:[{id:'quality',question:'Is quality preserved?',why_unanswered:'No visual evaluation.',goal_impact:'Speed is not enough.',next_evidence:'Unseen-photo quality test.',evidence:[0]}],insights:[{id:'finding',title:'Size is not quality',comparison:'Same photos, different encoder.',support:'One illustrative panel.',finding:'<img src=x onerror=alert(1)>',interpretation:'Compression may help transfer, quality unknown.',goal_relevance:'Measure quality next.',caveat:'Not tested on unseen photos.',evidence:[0]}]};
overview.translations['zh-CN'].narrative={insights:[{id:'finding',title:'文件大小不等于画面质量',interpretation:'压缩可能改善传输，但画质未知。'}]};
context.fixture.packets[1]=overview;
vm.runInContext("setLocale('en');detailSignature='';render()",context);
let narrativeDetail=node('detail').innerHTML;
for(const text of ['What changed, and why it matters','Before / question:','What remains unanswered, and why','How to interpret it:','Compression may help transfer','Technical detail'])assert.ok(narrativeDetail.includes(text),text);
assert.ok(narrativeDetail.indexOf('Compression may help transfer')<narrativeDetail.indexOf('Technical detail'));
assert.ok(narrativeDetail.includes('&lt;img'));assert.ok(!narrativeDetail.includes('<img src=x'));
assert.ok(narrativeDetail.includes('<details open><summary>3-minute evidence review'));
vm.runInContext("setLocale('zh-CN')",context);
assert.ok(node('detail').innerHTML.includes('三分钟证据解读'));
assert.ok(node('detail').innerHTML.includes('画质未知'));
const translatedNarrative=vm.runInContext('viewPacket(fixture.packets[1]).narrative',context);
assert.equal(translatedNarrative.insights[0].id,'finding');assert.deepEqual(Array.from(translatedNarrative.insights[0].evidence),[0]);
process.stdout.write('Workflow UI, bilingual goal steering and narrative-first evidence rendering checks passed.\n');
