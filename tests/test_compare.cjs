const test=require('node:test');
const assert=require('node:assert/strict');
const {comparisonRecords,comparisonSummary,comparisonSearch}=require('../static/compare.js');
const models=[{id:'m1',version:1,weights:{K1:.2}},{id:'m2',version:2,weights:{K1:.4}}];
function congress(id,profile='Profil A',options={}){
 const e={id:'e-'+id,created_at:'2026-10-03T10:00:00Z',model_id:'m1',scale:1,
 metadata:{name:'Kongre '+id,edition:'2027',context:profile},result:{total:80,lower:80,upper:80},...options};
 return {id,metadata:e.metadata,evaluations:[e]};
}
test('all profiles and models remain visible; a congress without evaluation remains visible',()=>{
 const input=[congress('A'),congress('B','Profil B',{model_id:'m2'}),{id:'C',metadata:{name:'Boş'},evaluations:[]}];
 const before=JSON.stringify(input);const rows=comparisonRecords(input,models);
 assert.equal(rows.length,3);assert.equal(rows[1].m.id,'m2');assert.equal(rows[2].e,undefined);
 assert.equal(JSON.stringify(input),before);
});
test('latest saved evaluation wins even when it belongs to another model',()=>{
 const c=congress('A');c.evaluations.push({...c.evaluations[0],id:'new',created_at:'2026-10-04T10:00:00Z',model_id:'m2'});
 const [row]=comparisonRecords([c],models);assert.equal(row.e.id,'new');assert.equal(row.m.weights.K1,.4);
});
test('Turkish search finds names, editions and locations',()=>{
 const a=congress('A');a.metadata.name='İSTANBUL KONGRESİ';a.metadata.location='Bursa';
 const rows=comparisonRecords([a,congress('B')],models);
 assert.equal(comparisonSearch(rows,'istanbul').length,1);assert.equal(comparisonSearch(rows,'BURSA').length,1);
 assert.equal(comparisonSearch(rows,'2027').length,2);assert.equal(comparisonSearch(rows,' ').length,2);
});
test('mixed context/model/scale/policy/sample groups never declare a winner',()=>{
 const variants=[{model_id:'m2'},{scale:5},{policy_version:'new-policy'},
 {metadata:{name:'B',context:'Different'}},{metadata:{name:'B',context:'Profil A',sample:true}}];
 for(const change of variants){
  const summary=comparisonSummary(comparisonRecords([congress('A'),congress('B','Profil A',change)],models));
  assert.equal(summary.comparable,false);assert.deepEqual(summary.winners,[]);
 }
});
test('same conditions show all ties; incomplete totals never become zero',()=>{
 let rows=comparisonRecords([congress('A'),congress('B')],models);
 assert.equal(comparisonSummary(rows).winners.length,2);
 rows[1].e.result={total:null,lower:15,upper:95};const summary=comparisonSummary(rows);
 assert.equal(summary.comparable,true);assert.equal(summary.complete,false);assert.deepEqual(summary.winners,[]);
 assert.equal(rows[1].e.result.total,null);
});
test('unknown models and unevaluated rows cannot produce a winner',()=>{
 const rows=comparisonRecords([congress('A'),congress('B','Profil A',{model_id:'gone'})],models);
 assert.equal(comparisonSummary(rows).comparable,false);
 rows.push({id:'empty'});assert.deepEqual(comparisonSummary(rows).winners,[]);
});
test('browser entrypoint still resolves every navigation handler after loading comparison',()=>{
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
 const context=vm.createContext({console,location:{hash:'#compare'},window:{addEventListener(){}},fetch:()=>new Promise(()=>{})});
 for(const file of ['logos.js','ai.js','compare.js','intelligence.js','database.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../static',file),'utf8'),context);
 for(const name of ['dashboard','congresses','compare','scenario','modelPage','guide','editor','detail','aiPage','aiReport','aiSettingsPage','trashPage','profilePage']){
  assert.equal(vm.runInContext(`typeof ${name}`,context),'function',name+' must remain available to render()');
 }
});
