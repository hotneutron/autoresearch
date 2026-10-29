// Actual-template POC fleet rendering, localization, and draft retention.
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const template=fs.readFileSync(process.argv[2],'utf8');
const script=template.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements=new Map();
function element(){return {textContent:'',value:'',children:[],append(...nodes){this.children.push(...nodes)},replaceChildren(...nodes){this.children=nodes}}}
function node(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)}
const fixture={rounds:[{id:'round-1',project:'subject',state:'closed'}],units:[{id:'candidate-1',round:'round-1',state:'completed',generation:1,body:{costs:{wall_ms:10}}}],attempts:[]};
const context=vm.createContext({document:{documentElement:{},getElementById:node,createElement:element},crypto:{randomUUID:()=> 'request-id'},setInterval(){},Date,console,fetch:async path=>({ok:true,json:async()=>path==='/api/messages'?{items:[{id:'reply',text:'<img src=x onerror=alert(1)>',in_reply_to:'question'}]}:fixture})});
vm.runInContext(script,context);
(async()=>{
 await vm.runInContext('refresh()',context);
 assert.equal(node('units').children[0].children[0].textContent,'candidate-1');
 assert.equal(node('messages').children[0].children[1].textContent,'<img src=x onerror=alert(1)>');
 node('reply').value='Keep this draft';node('reply').oninput();
 node('review-json').value='Review draft';node('review-json').oninput();
 node('language').value='zh-CN';node('language').onchange();
 assert.equal(node('title').textContent,'研究审阅');
 assert.equal(node('reply').value,'Keep this draft');
 assert.equal(node('review-json').value,'Review draft');
 assert.ok(node('assurance').textContent.includes('自行声明'));
 assert.equal(vm.runInContext('selected',context),'round-1');
 console.log('Fleet actual-template rendering, bilingual assurance, safe text and draft retention passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
