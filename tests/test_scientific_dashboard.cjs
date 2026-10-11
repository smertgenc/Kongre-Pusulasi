const test=require('node:test'),assert=require('node:assert/strict');
const {dashboardGroups,comparisonSummary}=require('../static/compare.js');
test('dashboard separates date, mode, profile, sample and policy',()=>{
 const a={id:'1',m:{},e:{model_id:'m',metadata:{context:'c'},scale:1,created_at:'2026-10-10',result:{total:80}}};
 for(const change of [{criteria_profile:'other'},{created_at:'2026-10-11'},{mode:'ai_reviewed'},{policy_version:'v3'},{metadata:{context:'c',sample:true}}]){
  const b={...a,id:'2',e:{...a.e,...change}};assert.equal(dashboardGroups([a,b]).length,2);assert.equal(comparisonSummary([a,b]).comparable,false);
 }
 assert.equal(dashboardGroups([a,a]).length,1);
});
