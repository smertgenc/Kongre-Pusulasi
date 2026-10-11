const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context=vm.createContext({console,location:{hash:'#profile'},window:{addEventListener(){}},fetch:()=>new Promise(()=>{})});
for(const file of ['logos.js','ai.js','compare.js','intelligence.js','database.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../static',file),'utf8'),context);
const run=code=>vm.runInContext(code,context);
test('research form retains every optional persisted field and escapes injected content',()=>{
 context.meta={research:{description:'<img src=x onerror=alert(1)>',keywords:['LLM','AI'],past_years:[2025],committee_members:['Ali']}};
 const html=run('congressResearchFields(meta,"test")');
 assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img'));
 for(const token of ['LLM\nAI','2025','Ali','test-description','test-doi_prefixes'])assert.ok(html.includes(token));
});
test('inactive personal profile does not show a fabricated zero percent',()=>{
 context.fit={score:null,matches:[],message:'Profil ekleyin.'};
 const html=run('personalFitMarkup(fit)');assert.ok(html.includes('#profile'));assert.ok(html.includes('Profil ekleyin.'));
 assert.ok(!html.includes('personal-score'));
});
test('recommendation cards keep AHP, personal fit, organizational score separate and escape names',()=>{
 context.data={message:'3 alternatif',scope:'Yerel kayıtlar',weights:{similarity:.45,ahp:.35,personal_fit:.2},items:[{
 id:'id1',evaluation_id:'e1',name:'<script>alert(1)</script>',edition:'2027',similarity_score:88,ahp_score:75,suitability:'Orta Uygunluk',
 personal_fit:{score:95},ahp_delta:null,fee:'<b>300 EUR</b>',recommendation_score:86,shared_terms:['machine_learning'],reasons:['Konu benzerliği']} ]};
 const html=run('recommendationsMarkup(data)');
 assert.ok(!html.includes('<script>'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<b>300 EUR</b>'));
 for(const token of ['Benzerlik','AHP','Kişisel uyum','Orta Uygunluk','AHP puan farkı karşılaştırılamıyor'])assert.ok(html.includes(token));
});
test('missing organizational matches and unknown fields never claim identity or quality',()=>{
 context.data={fingerprint:{fingerprint_hash:'abc'},organizational_matches:[]};
 const html=run('fingerprintMarkup(data)');assert.ok(html.includes('bulunamadı'));assert.ok(html.includes('Bilinmiyor'));
 assert.ok(html.includes('Aynı kongre olduğu veya kaliteli olduğu sonucunu vermez.'));
});
