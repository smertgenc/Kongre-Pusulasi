const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const context=vm.createContext({console,location:{hash:'#congresses'},window:{addEventListener(){}},fetch:()=>new Promise(()=>{})});
for(const f of ['logos.js','ai.js','compare.js','intelligence.js','database.js','app.js'])vm.runInContext(fs.readFileSync('static/'+f,'utf8'),context);
const run=s=>vm.runInContext(s,context);
test('registered logos use local assets with readable alt text; unknown and hidden logos keep fallback',()=>{
 run(`state={logos:{a:{status:'ready',source:'website',url:'/api/congresses/a/logo?v=123'},b:{status:'hidden'}}}`);
 const html=run(`congressAvatar('a','Kongre "A"')`);
 assert.ok(html.includes('src="/api/congresses/a/logo?v=123"'));assert.ok(html.includes('Kongre &quot;A&quot;'));assert.ok(!html.includes('onerror='));
 for(const id of ['b','unknown']){const result=run(`congressAvatar('${id}','Kongre')`);assert.ok(!result.includes('<img'));assert.ok(result.includes('logo-fallback'));}
});
test('malicious congress names and ids cannot introduce HTML through any logo surface',()=>{
 const html=run(`congressAvatar('x" onclick="evil()','<script>alert(1)</script>')`);
 assert.ok(!html.includes('<script>'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(html.includes('&quot; onclick=&quot;'));
});
test('site icons are identified honestly and report association uses exact website identity',()=>{
 run(`state={logos:{a:{status:'ready',source:'site_icon',url:'/api/congresses/a/logo'}},congresses:[{id:'a',metadata:{website:'https://university.example/event-one'}}]}`);
 assert.ok(run(`congressAvatar('a','Congress')`).includes('Web sitesi simgesi'));
 assert.equal(run(`logoCongressId({website:'https://university.example/event-one/'})`),'a');
 assert.equal(run(`logoCongressId({website:'https://university.example/event-two'})`),'');
 assert.equal(run(`logoCongressId({},'saved-id')`),'saved-id');
});
