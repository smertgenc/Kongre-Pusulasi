const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',disabled:false,insertAdjacentHTML(){}});return nodes.get(id)};
  let search={provider_id:'tavily',provider:'Tavily',configured:true,providers:[{id:'jina',name:'Jina AI Search',configured:true},{id:'tavily',name:'Tavily',configured:true}]};
  let ai={provider_id:'gemini',provider:'Gemini',configured:true,model:'model-a',providers:[{id:'gemini',name:'Gemini',configured:true,model:'model-a',default_model:'model-a',help:'test'},{id:'groq',name:'Groq',configured:true,model:'model-b',default_model:'model-b',help:'test'}]};
  const calls=[];let failure=null;
  // Browsers select the option carrying `selected` after replacing the markup.
  Object.defineProperty(node('#ai-provider'),'innerHTML',{set(value){this.html=value;this.value=/value="([^"]+)" selected/.exec(value)?.[1]||''},get(){return this.html||''}});
  const context=vm.createContext({console,window:{addEventListener(){}},$:node,heading:()=>'',esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;'),
    api:async(path,body)=>{
      calls.push({path,body});
      if(path==='/api/search/settings'&&!body)return structuredClone(search);
      if(path==='/api/ai/settings'&&!body)return structuredClone(ai);
      if(path==='/api/search/settings'){
        const p=search.providers.find(p=>p.id===body.provider_id);
        search={...search,provider_id:p.id,provider:p.name};return structuredClone(search);
      }
      if(path==='/api/ai/settings'){
        const p=ai.providers.find(p=>p.id===body.provider_id);p.model=body.model;
        ai={...ai,provider_id:p.id,provider:p.name,model:body.model};return structuredClone(ai);
      }
      if(failure)throw Error(failure);
      if(path==='/api/search/test')return {provider:search.provider,result_count:1,results:[]};
      if(path==='/api/ai/test')return {provider:ai.provider,model:ai.model};
      throw Error('Unexpected route');
    }});
  vm.runInContext(fs.readFileSync('static/ai.js','utf8'),context);
  return {node,calls,run:s=>vm.runInContext(s,context),fail:message=>{failure=message}};
}
test('search initializes saved Tavily, blocks unsaved Jina, then tests only the newly saved service',async()=>{
  const ui=setup();await ui.run('loadResearchSettings()');
  assert.equal(ui.node('#research-provider').value,'tavily');assert.match(ui.node('#research-status').innerHTML,/Tavily/);
  await ui.node('#research-test').onclick();
  assert.equal(ui.calls.at(-1).body.provider_id,'tavily');assert.match(ui.node('#research-message').innerHTML,/Test edilen servis: Tavily/);
  ui.node('#research-provider').value='jina';ui.node('#research-provider').onchange();
  assert.equal(ui.node('#research-test').disabled,true);assert.match(ui.node('#research-test-target').textContent,/henüz kaydedilmedi/);
  assert.match(ui.node('#research-status').innerHTML,/Tavily/);
  const before=ui.calls.length;await ui.node('#research-test').onclick();assert.equal(ui.calls.length,before);
  await ui.node('#research-form').onsubmit({preventDefault(){}});
  assert.equal(ui.node('#research-provider').value,'jina');assert.equal(ui.node('#research-test').disabled,false);
  assert.match(ui.node('#research-status').innerHTML,/Jina AI Search/);
  await ui.node('#research-test').onclick();assert.equal(ui.calls.at(-1).body.provider_id,'jina');
  assert.match(ui.node('#research-message').innerHTML,/Test edilen servis: Jina AI Search/);
});
test('new unsaved search key disables tests and failure names the saved service',async()=>{
  const ui=setup();await ui.run('loadResearchSettings()');
  ui.node('#research-key').value='PRIVATE';ui.node('#research-key').oninput();assert.equal(ui.node('#research-test').disabled,true);
  await ui.node('#research-form').onsubmit({preventDefault(){}});assert.equal(ui.node('#research-key').value,'');
  ui.fail('SSL sertifika doğrulama hatası.');await ui.node('#research-test').onclick();
  assert.match(ui.node('#research-message').innerHTML,/Test edilen servis: Tavily/);
  assert.match(ui.node('#research-message').innerHTML,/SSL sertifika/);assert.doesNotMatch(ui.node('#research-message').innerHTML,/PRIVATE/);
});
test('AI probe uses saved provider and model, blocks edited model until saved, and shows its identity',async()=>{
  const ui=setup();await ui.run('aiSettingsPage()');
  await ui.node('#ai-connection-test').onclick();
  assert.equal(ui.calls.at(-1).body.provider_id,'gemini');assert.equal(ui.calls.at(-1).body.provider_model,'model-a');
  assert.match(ui.node('#ai-settings-message').innerHTML,/Test edilen servis: Gemini · model-a/);
  ui.node('#ai-provider-model').value='model-new';ui.node('#ai-provider-model').oninput();
  assert.equal(ui.node('#ai-connection-test').disabled,true);
  const before=ui.calls.length;await ui.node('#ai-connection-test').onclick();assert.equal(ui.calls.length,before);
  await ui.node('#ai-settings-form').onsubmit({preventDefault(){}});
  assert.equal(ui.node('#ai-connection-test').disabled,false);
  await ui.node('#ai-connection-test').onclick();assert.equal(ui.calls.at(-1).body.provider_model,'model-new');
  ui.node('#ai-provider').value='groq';ui.node('#ai-provider').onchange();
  assert.equal(ui.node('#ai-connection-test').disabled,true);assert.match(ui.node('#ai-test-target').textContent,/Gemini/);
});
