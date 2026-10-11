const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('research rendering escapes user attributes and discloses synthetic limitations',()=>{
 const context=vm.createContext({esc:v=>String(v).replaceAll('<','&lt;'),pct:v=>String(v*100),fmt:v=>String(v)});
 vm.runInContext(fs.readFileSync('static/research.js','utf8'),context);
 const html=vm.runInContext(`conjointResultHtml({status:'Teknik test',data_origin:'synthetic',respondents:60,train_n:100,holdout_n:20,iterations:4,holdout_accuracy:.6,holdout_log_loss:.9,attributes:[{id:'fee',label:'<img>'}],coefficients:{fee:{'<script>':0}},importance:{fee:1},limitations:['Araştırma verisi gerekiyor.']})`,context);
 assert.ok(html.includes('&lt;img>'));assert.ok(!html.includes('<script>'));assert.ok(html.includes('Örnek veri'));assert.ok(html.includes('Araştırma verisi gerekiyor.'));
});
