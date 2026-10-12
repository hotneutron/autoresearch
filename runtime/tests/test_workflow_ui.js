/* Exercise the actual inline inbox renderer with a minimal DOM, no network. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html=fs.readFileSync(process.argv[2], 'utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace('__OFFLINE__','false').replace('__INITIAL_DATA__','null')
  .replace('refresh();if(!OFFLINE)setInterval(refresh,5000);','');
const nodes=new Map();
function node(id){
  if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,showModal(){},close(){}});
  return nodes.get(id);
}
const context=vm.createContext({document:{getElementById:node,querySelectorAll:()=>[],title:''},location:{hash:''},history:{replaceState(){}},setInterval(){},Map,JSON,Date,Number,String,crypto:{randomUUID(){return 'feedback-id';}}});
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
process.stdout.write('Workflow UI rendering checks passed.\n');
