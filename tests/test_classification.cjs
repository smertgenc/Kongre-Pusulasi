const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context=vm.createContext({console,location:{hash:'#dashboard'},window:{addEventListener(){}},fetch:()=>new Promise(()=>{})});
for(const file of ['logos.js','ai.js','compare.js','intelligence.js','database.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../static',file),'utf8'),context);
const run=code=>vm.runInContext(code,context);
test('live preview respects exact boundaries and custom model thresholds',()=>{
 for(const [medium,high] of [[70,90],[40,75],[0,100]]){
  for(const [value,expected] of [[medium-1e-8,'Düşük Uygunluk'],[medium,'Orta Uygunluk'],[high-1e-8,'Orta Uygunluk'],[high,'Yüksek Uygunluk']]){
   if(value<0)continue;
   const status=run(`clientScore(Object.fromEntries(codes.map(c=>[c,${value/100}])), {weights:Object.fromEntries(codes.map(c=>[c,c==='K1'?1:0])), thresholds:{average:${medium},valid:${high}}}).status`);
   assert.equal(status,expected);
  }
 }
});
test('an unknown zero-weight criterion stays incomplete like the backend',()=>{
 const status=run(`clientScore(Object.fromEntries(codes.map(c=>[c,c==='K10'?null:1])), {weights:Object.fromEntries(codes.map(c=>[c,c==='K1'?1:0])),thresholds:{average:70,valid:90}}).status`);
 assert.equal(status,'Eksik veri');
});
test('all 1024 binary previews agree with backend classification',()=>{
 const {execFileSync}=require('node:child_process');
 const root=path.resolve(__dirname,'..');
 const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 const python=process.env.PYTHON||(fs.existsSync(localPython)?localPython:(process.platform==='win32'?'python':'python3'));
 const data=JSON.parse(execFileSync(python,['-c',
  'import json,itertools;from engine import *;m=calculate_model(DEFAULT_MATRICES);print(json.dumps({"model":m,"results":[score(m["weights"],dict(zip([c[0] for c in CRITERIA],v)),m["thresholds"])["status"] for v in itertools.product([0,1],repeat=10)]}))'],{encoding:'utf8',cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
 context.testModel=data.model;
 for(let i=0;i<1024;i++){
  context.testUtilities=Object.fromEntries(Array.from({length:10},(_,j)=>['K'+(j+1),(i>>(9-j))&1]));
  assert.equal(run('clientScore(testUtilities,testModel).status'),data.results[i]);
 }
});
test('badges and threshold explanations use suitability labels; consistency stays separate',()=>{
 for(const [label,css] of [['Düşük Uygunluk','bad'],['Orta Uygunluk','mid'],['Yüksek Uygunluk','good'],['Eksik veri','missing'],['Tutarlı','good'],['Tutarsız','bad']]){
  const html=run(`badge(${JSON.stringify(label)})`);assert.ok(html.includes(`badge ${css}`));assert.ok(html.includes(label));
 }
 const html=run('classificationLegend({thresholds:{average:40,valid:75}})');
 for(const text of ['40','75','Düşük Uygunluk','Orta Uygunluk','Yüksek Uygunluk'])assert.ok(html.includes(text));
});
