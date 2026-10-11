const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',checked:false,disabled:false,dataset:{},innerHTML:'',textContent:'',setAttribute(){},removeAttribute(){}});return nodes.get(id)};
  const settings={provider_id:'gemini',provider:'Gemini',model:'gemini-model',configured:true,
    fallback_providers:[{provider_id:'groq',provider_name:'Groq',provider_model:'groq-model'}]};
  const card={};node('select').value='text';node('.source-content').value='Kongre programı ve bilim kurulu metni.';
  Object.defineProperty(node('#ai-failover'),'innerHTML',{set(value){this.html=value;node('#ai-failover-enabled').checked=value.includes('checked');},get(){return this.html||''}});
  const calls=[];
  const context=vm.createContext({console,window:{addEventListener(){}},$:node,
    $$:selector=>selector==='[data-source]'?[card]:[],state:{models:[{id:'model-1',version:1,name:'Excel modeli'}]},location:{hash:'#ai'},
    heading:()=>'',esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'),toast(){},
    api:async(path,body)=>{calls.push({path,body});if(path==='/api/ai/settings')return structuredClone(settings);
      if(path==='/api/search/settings')return {providers:[]};if(path==='/api/ai/start')return {id:'job-id'};throw Error(path);}});
  vm.runInContext(fs.readFileSync('static/ai.js','utf8'),context);
  vm.runInContext('addAiSource=()=>{};loadAiHistory=async()=>{};',context);
  return {node,calls,run:s=>vm.runInContext(s,context)};
}
test('analysis shows recipients before consent and sends the exact displayed backup model',async()=>{
  const ui=setup();await ui.run('aiPage()');
  assert.equal(ui.node('#ai-failover-enabled').checked,true);
  assert.match(ui.node('#ai-failover-plan').textContent,/Gemini → Groq/);
  assert.match(ui.node('#ai-consent-label').textContent,/Gemini \/ Groq/);
  ui.node('#ai-consent').checked=true;
  await ui.node('#ai-form').onsubmit({preventDefault(){},target:ui.node('#ai-form')});
  const body=ui.calls.find(c=>c.path==='/api/ai/start').body;
  assert.equal(body.provider_id,'gemini');assert.equal(body.transfer_consent,true);
  assert.deepEqual(JSON.parse(JSON.stringify(body.fallback_providers)),[{provider_id:'groq',provider_model:'groq-model'}]);
});
test('turning fallback off clears consent and prevents sending any backup recipient',async()=>{
  const ui=setup();await ui.run('aiPage()');ui.node('#ai-consent').checked=true;
  ui.node('#ai-failover-enabled').checked=false;ui.node('#ai-failover-enabled').onchange();
  assert.equal(ui.node('#ai-consent').checked,false);
  assert.doesNotMatch(ui.node('#ai-consent-label').textContent,/Groq/);
  ui.node('#ai-consent').checked=true;
  await ui.node('#ai-form').onsubmit({preventDefault(){},target:ui.node('#ai-form')});
  assert.equal(ui.calls.find(c=>c.path==='/api/ai/start').body.fallback_providers.length,0);
});
test('report distinguishes planned, contributing, failed and resumed providers and escapes content',()=>{
  const ui=setup();
  const html=ui.run(`aiExecutionSummary({status:'failed',provider_plan:[{provider_name:'Gemini',provider_model:'<img src=x>'},{provider_name:'Groq',provider_model:'model'}],providers_used:[{provider_name:'Gemini',provider_model:'model',batches:2}],provider_failures:[{provider_name:'Groq',code:'RATE_LIMIT',http_status:429}],resumed_batches:1,completed_batches:2})`);
  assert.match(html,/Sonuca katkı verenler/);assert.match(html,/2 parça/);assert.match(html,/Token veya istek kotası doldu/);
  assert.match(html,/1 tamamlanmış parça önceki denemeden korundu/);assert.match(html,/Kısmi sonuçtan AHP puanı üretilmedi/);
  assert.doesNotMatch(html,/<img/);assert.match(html,/&lt;img/);
});
