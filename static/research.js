'use strict';
let researchStudy = null;
let researchPageTicket = 0;
let researchStudyTicket = 0;
const researchKinds = {
 synthetic: {label:'Örnek veri', title:'Örnek sonuçları gör', description:'Bilgisayar örnek seçimler üretir. Veri girmeden sonuç ekranını tanıyın.', action:'Örnek analizi başlat', name:'Örnek tercih analizi'},
 demo: {label:'Deneme', title:'Seçim yaparak dene', description:'Örnek kongreler arasından kendiniz seçim yapın; anketin nasıl çalıştığını öğrenin.', action:'Seçim ekranını hazırla', name:'Tercih denemem'},
 research: {label:'Katılımcı araştırması', title:'Katılımcılarla araştır', description:'İzin ve onam bilgilerini hazırlayıp gerçek katılımcıların seçimlerini kaydedin.', action:'Araştırmayı oluştur', name:'Kongre tercih araştırması'}
};
const researchKind = kind => researchKinds[kind]?.label || 'Veri türü belirtilmedi';
function researchFocus(element) {
 if (!element) return;
 element.focus({preventScroll:true});
 element.scrollIntoView({block:'start',behavior:'auto'});
}
function researchHelpHtml() {
 return `<details class="cbc-help"><summary>Bu bölüm ne işe yarar?</summary><div>
 <p>Örneğin, katılımcılar düşük ücretli çevrim içi bir kongreyi mi, daha pahalı yüz yüze bir kongreyi mi seçiyor? Bu bölüm, sunulan seçenekler arasındaki tercihlerden özelliklerin etkisini hesaplar. Yöntemin adı <b>Conjoint tercih analizi</b>dir.</p>
 <p>AHP, kongrelerin belirlenen kriterlere uygunluğunu değerlendirir. Tercih analizi ise seçim davranışını inceler. Buradaki sonuçlar kayıtlı AHP puanlarınızı değiştirmez.</p>
 <p>Varsayılan seçenekler kayıt ücreti, katılım biçimi, araştırma ilgisi ve akademik etkileşimdir. İleri ayarlarda bu özellikleri değiştirebilirsiniz.</p>
 <p>İşlem bu bilgisayarda yapılır; API anahtarı veya token gerekmez. Örnek ve deneme verileri bilimsel araştırma bulgusu sayılmaz.</p>
 <p>Araştırma kayıtları ayrı dosyada saklanır ve standart kongre veritabanı yedeğine dahil değildir. Bu bölümü kapatmak çalışmaları silmez.</p></div></details>`;
}
function researchCreateHtml() {
 return `<form id="cbc-create">
 <fieldset class="cbc-mode-fieldset"><legend>Nasıl başlamak istersiniz?</legend><div class="cbc-mode-grid">
 ${Object.entries(researchKinds).map(([kind,k],i)=>`<label class="cbc-mode-card"><input type="radio" name="cbc-kind" value="${kind}" ${i===0?'checked':''}><span><span class="cbc-mode-title">${k.title}</span>${i===0?'<small class="cbc-recommended">İlk kullanım için</small>':''}<span class="cbc-mode-description">${k.description}</span></span></label>`).join('')}
 </div></fieldset>
 <div class="field"><label for="cbc-title">Çalışmanıza bir ad verin</label><input id="cbc-title" required maxlength="200" value="Örnek tercih analizi" aria-describedby="cbc-title-help"><p class="hint" id="cbc-title-help">Daha sonra bu adla kayıtlı çalışmalarınızdan açabilirsiniz.</p></div>
 <details class="cbc-details" id="cbc-advanced"><summary>İleri ayarlar <span>· İsteğe bağlı</span></summary><div class="cbc-details-content">
 <p>İlk deneme için bu ayarları değiştirmeniz gerekmez. Her soruda üç kongre seçeneği gösterilir.</p>
 <div class="form-grid"><div class="field"><label for="cbc-tasks">Kişi başına soru sayısı</label><input id="cbc-tasks" type="number" value="24" min="12" max="80" step="1" required><p class="hint">12–80 soru. Bazı sorular sonucun kontrolü için ayrı tutulur.</p></div>
 <div class="field"><label for="cbc-seed">Aynı soru setini üretme kodu</label><input id="cbc-seed" type="number" value="42" step="1" required><p class="hint">Aynı ayarlar ve kod aynı seçenekleri üretir. Teknik adı: rastgelelik tohumu.</p></div></div>
 <details class="cbc-details"><summary>Özellikleri özelleştir <span>· Teknik düzenleme</span></summary><div class="cbc-details-content">
 <p>Varsayılan özellikler: ücret, katılım biçimi, alan ilgisi ve etkileşim. Yayın, konum veya geçmiş gibi özellikleri eklerken uzman değerlendirmesiyle aynı etkiyi iki kez ölçmediğinizden emin olun. Soru tasarımı rastgeledir; optimal tasarım iddiası yoktur.</p>
 <div class="field"><label for="cbc-attributes">Özellikler ve seçenekleri · JSON</label><textarea id="cbc-attributes" rows="5" spellcheck="false" placeholder='[{"id":"fee","label":"Ücret","levels":["Düşük","Yüksek"]}, ...]'></textarea><p class="hint">Boş bırakırsanız hazır özellikler kullanılır. 2–6 özellik; her biri için 2–4 seçenek gerekir.</p></div>
 <div class="field"><label for="cbc-forbidden">Birlikte gösterilmeyecek seçenekler · JSON</label><textarea id="cbc-forbidden" rows="2" spellcheck="false">[]</textarea><p class="hint">Kısıtlama yoksa [] olarak bırakın.</p></div></div></details>
 </div></details>
 <fieldset class="cbc-ethics" id="cbc-ethics" hidden disabled><legend>Katılımcı araştırmasına başlamadan önce</legend>
 <p>Gerekli kurum/etik izinleri, katılımcı onamı ve veri yönetimi planınız hazır olmalı. Katılımcı adı yerine bir kod kullanın.</p>
 <div class="form-grid"><div class="field"><label for="cbc-approval">İzin / onay referansı *</label><input id="cbc-approval" maxlength="300" required placeholder="Kurul adı ve onay numarası"></div>
 <div class="field"><label for="cbc-consent-version">Onam metninin sürümü *</label><input id="cbc-consent-version" maxlength="80" required placeholder="Örn. v1 · 10.10.2026"></div></div>
 <div class="field"><label for="cbc-consent-text">Katılımcıya gösterilecek onam metni *</label><textarea id="cbc-consent-text" maxlength="5000" required rows="5"></textarea></div>
 <div class="field"><label for="cbc-management">Veri yönetimi planı referansı *</label><input id="cbc-management" maxlength="300" required placeholder="Plan adı veya kurum içi referansı"></div>
 <label class="consent"><input id="cbc-authorized" type="checkbox" required> Gerekli araştırma izinleri alındı.</label></fieldset>
 <div class="cbc-start-action"><button class="btn primary" type="submit" id="cbc-create-button">Örnek analizi başlat <span aria-hidden="true">→</span></button><p class="hint" id="cbc-action-help">Örnek çalışma ve sonuçlar otomatik hazırlanır. Gerçek katılımcı gerekmez.</p></div>
 <p id="cbc-create-error" class="cbc-message" role="alert"></p></form>`;
}
async function researchPage() {
 const ticket=++researchPageTicket;
 $('#main').innerHTML=heading('KONGRE TERCİHLERİNİ ANLAYIN','Tercih analizi','Bir kongreyi seçerken hangi özellikler daha çok etkili? Seçimleri inceleyin, tercihleri görün.')+
  '<div class="cbc-page" id="cbc-page"><section class="panel" id="cbc-body" role="status">Tercih çalışmaları yükleniyor…</section></div>';
 const body=$('#cbc-body'),root=$('#cbc-page');
 const current=()=>page==='research'&&ticket===researchPageTicket&&root.isConnected;
 try {
  const r=await api('/api/research/status');if(!current())return;
  if(!r.studies.some(s=>s.id===researchStudy))researchStudy=null;
  body.removeAttribute('role');body.className='panel cbc-intro';
  body.innerHTML=`<div class="cbc-intro-heading"><div><span class="cbc-kicker">CONJOINT YÖNTEMİ</span><h2>Kongre seçimlerini anlamanın bir yolu</h2></div><span class="cbc-state">${r.enabled?'Kullanıma açık':'İsteğe bağlı bölüm'}</span></div>
   <p>Katılımcıya farklı özelliklerde kongre seçenekleri sunulur. Seçimlerinden, ücretin veya katılım biçiminin tercihte ne kadar etkili olduğu hesaplanır.</p>
   <ol class="cbc-steps" aria-label="Tercih analizinin adımları"><li><span>1</span><div><b>Bir çalışma seçin</b><small>Hazır örnekle başlayabilirsiniz.</small></div></li><li><span>2</span><div><b>Seçimleri hazırlayın</b><small>Örnek veya katılımcı seçimleri.</small></div></li><li><span>3</span><div><b>Etkileri görün</b><small>Hangi özellik öne çıkıyor?</small></div></li></ol>
   ${researchHelpHtml()}${!r.enabled?'<div class="cbc-start-action"><button class="btn primary" id="cbc-toggle">Tercih analizini aç →</button><p class="hint">Başlamak için bu bölümü bir kez açın.</p></div>':''}`;
  if(!r.enabled){
   $('#cbc-toggle').onclick=async e=>{const b=e.currentTarget;b.disabled=true;b.textContent='Açılıyor…';try{await api('/api/research/settings',{enabled:true});if(current()){researchStudy=null;await researchPage();}}catch(error){if(current()){toast(error.message,true);b.disabled=false;b.textContent='Tercih analizini aç →';}}};return;
  }
  root.insertAdjacentHTML('beforeend',`<details class="panel cbc-new" id="cbc-new" ${!researchStudy?'open':''}><summary><span>Yeni bir çalışma başlat</span><small>Örnek, deneme veya katılımcı araştırması</small></summary>${researchCreateHtml()}</details>
   <section class="panel cbc-saved" aria-labelledby="cbc-saved-title"><div class="cbc-section-head"><h2 id="cbc-saved-title">Kayıtlı çalışmalarınız</h2><span class="cbc-state">${r.studies.length} çalışma</span></div>
   <div class="cbc-study-list">${r.studies.map(s=>`<button class="cbc-study-card" data-study="${esc(s.id)}" aria-pressed="${s.id===researchStudy}"><span><b>${esc(s.title)}</b><small>${researchKind(s.kind)}</small></span><span class="cbc-study-state">${s.estimated?'Sonuçları gör':'Çalışmaya devam et'} <span aria-hidden="true">→</span></span></button>`).join('')||'<p class="cbc-empty">Henüz bir çalışmanız yok. Yukarıdan “Örnek sonuçları gör” ile başlayabilirsiniz.</p>'}</div></section>
   <section class="panel" id="cbc-study" tabindex="-1" hidden></section><section class="panel" id="research-experiments"></section>
   <div class="cbc-module-footer"><p>Çalışmalarınız bu bilgisayarda saklanır. Bu bölümü kapattığınızda kayıtlar korunur.</p><button class="btn small" id="cbc-disable">Bu bölümü kapat</button></div>`);
  let autoTitle=researchKinds.synthetic.name;
  $$('input[name="cbc-kind"]',root).forEach(input=>input.onchange=()=>{
   const k=researchKinds[input.value],isResearch=input.value==='research';
   if($('#cbc-title').value===autoTitle)$('#cbc-title').value=k.name;autoTitle=k.name;
   const ethics=$('#cbc-ethics');ethics.hidden=!isResearch;ethics.disabled=!isResearch;
   $('#cbc-create-button').textContent=k.action+' →';
   $('#cbc-action-help').textContent=input.value==='synthetic'?'Örnek çalışma ve sonuçlar otomatik hazırlanır. Gerçek katılımcı gerekmez.':input.value==='demo'?'Önce seçenekler hazırlanır. Sonuç hesaplamak için yeterli sayıda seçim kaydetmeniz gerekir.':'Her katılımcı için ayrı bir kod kullanın. Seçimler onam alındıktan sonra kaydedilir.';
  });
  $('#cbc-create').onsubmit=async e=>{
   e.preventDefault();const form=e.currentTarget,b=$('#cbc-create-button'),errorBox=$('#cbc-create-error');
   const kind=$('input[name="cbc-kind"]:checked',form).value;errorBox.textContent='';
   let attributes,forbidden;
   try{attributes=$('#cbc-attributes').value.trim()?JSON.parse($('#cbc-attributes').value):null;}catch{errorBox.textContent='Özellikler alanındaki JSON biçimini kontrol edin. Hazır seçenekler için bu alanı boş bırakabilirsiniz.';$('#cbc-advanced').open=true;return;}
   try{forbidden=JSON.parse($('#cbc-forbidden').value);}catch{errorBox.textContent='Birlikte gösterilmeyecek seçenekler alanındaki JSON biçimini kontrol edin. Kısıtlama yoksa [] yazın.';$('#cbc-advanced').open=true;return;}
   const payload={title:$('#cbc-title').value.trim(),kind,seed:Number($('#cbc-seed').value),tasks:Number($('#cbc-tasks').value),attributes,forbidden,
    collection_authorized:kind==='research'&&$('#cbc-authorized').checked,approval_reference:kind==='research'?$('#cbc-approval').value:'',consent_version:kind==='research'?$('#cbc-consent-version').value:'',consent_text:kind==='research'?$('#cbc-consent-text').value:'',data_management_reference:kind==='research'?$('#cbc-management').value:''};
   if(!payload.title){errorBox.textContent='Çalışmanızı daha sonra bulabilmek için bir ad yazın.';return;}
   b.disabled=true;b.textContent=kind==='synthetic'?'Örnek sonuçlar hazırlanıyor…':'Çalışma hazırlanıyor…';
   let created=null;
   try {
    created=await api('/api/research/studies',payload);
    if(kind==='synthetic')await api('/api/research/studies/'+created.id+'/estimate',{});
    if(current()){researchStudy=created.id;await researchPage();researchFocus($('#cbc-study'));}
   } catch(error) {
    if(current()){
     if(created){researchStudy=created.id;await researchPage();const msg=$('#cbc-status');if(msg)msg.textContent='Çalışma kaydedildi, sonuç henüz hesaplanamadı. Yeniden deneyebilirsiniz. '+error.message;researchFocus($('#cbc-study'));}
     else errorBox.textContent=error.message;
    }
   } finally {if(b.isConnected){b.disabled=false;b.textContent=researchKinds[kind].action+' →';}}
  };
  // Reveal invalid advanced fields before the browser tries to focus them.
  $('#cbc-create').addEventListener('invalid',e=>{let p=e.target.parentElement;while(p&&p!==e.currentTarget){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}},true);
  $$('[data-study]',root).forEach(b=>b.onclick=async()=>{researchStudy=b.dataset.study;$('#cbc-new').open=false;await showConjointStudy(researchStudy);if(current())researchFocus($('#cbc-study'));});
  $('#cbc-disable').onclick=async e=>{const b=e.currentTarget;b.disabled=true;try{await api('/api/research/settings',{enabled:false});if(current()){researchStudy=null;await researchPage();}}catch(error){if(current()){toast(error.message,true);b.disabled=false;}}};
  researchExperimentForm(r.studies);
  if(researchStudy)await showConjointStudy(researchStudy);
 } catch(error) {if(current())body.textContent=error.message;}
}
function conjointResultHtml(m) {
 const ranked=m.attributes.map(a=>({...a,share:m.importance[a.id]})).sort((a,b)=>(b.share??-1)-(a.share??-1));
 const best=ranked.filter(a=>Number.isFinite(a.share)&&a.share>0&&Math.abs(a.share-ranked[0].share)<1e-9);
 const summary=best.length?'Bu çalışmadaki seçenekler arasında en çok fark yaratan '+(best.length===1?'özellik: ':'özellikler: ')+best.map(a=>a.label).join(', ')+'.':'Bu seçimlerle özellikler arasında belirgin bir fark hesaplanamadı.';
 const isResearch=m.data_origin==='research';
 return `<div class="cbc-result-note"><span class="cbc-state">${researchKind(m.data_origin)}</span><p>${isResearch?'Bu sonuçlar kaydedilen katılımcı seçimlerine dayanır. Bağımsız bilimsel doğrulama ayrıca gerekir.':'Bu sonuçlar öğrenme ve deneme amaçlıdır. Gerçek katılımcı tercihleri olarak yorumlamayın.'}</p></div>
 <h3>Seçimlerde hangi özellik öne çıkıyor?</h3><p class="cbc-result-summary">${esc(summary)}</p>
 <div class="cbc-importance" role="list" aria-label="Özelliklerin tercihe etkisi">${ranked.map(a=>{
  const levels=Object.entries(m.coefficients[a.id]);const max=Math.max(...levels.map(([,v])=>v));const preferred=levels.filter(([,v])=>Math.abs(v-max)<1e-9).map(([name])=>name);
  const share=Number.isFinite(a.share)?Math.max(0,Math.min(1,a.share)):null;
  return `<div class="cbc-importance-row" role="listitem"><div class="cbc-importance-label"><b>${esc(a.label)}</b><strong>${share==null?'Hesaplanamadı':pct(share)}</strong></div><div class="cbc-importance-track" aria-hidden="true"><span style="width:${share==null?0:share*100}%"></span></div><p>${preferred.length===levels.length?'Bu özelliğin seçenekleri arasında fark yok.':'Öne çıkan seçenek'+(preferred.length>1?'ler':'')+': '+preferred.map(esc).join(' / ')}</p></div>`;
 }).join('')}</div><p class="cbc-caption">Yüzdeler, bu çalışmada sunulan özellik ve seçeneklerin göreli etkisini gösterir. Bunlar kongrelerin AHP uygunluk puanı değildir.</p>
 <div class="cbc-result-stats"><div><span>${m.data_origin==='synthetic'?'Örnek katılımcı':'Katılımcı kodu'}</span><strong>${fmt(m.respondents,0)}</strong></div><div><span>Toplam seçim</span><strong>${fmt(m.train_n+m.holdout_n,0)}</strong></div><div><span>Kontrol sorularında doğru tahmin</span><strong>${m.holdout_accuracy==null?'—':pct(m.holdout_accuracy)}</strong></div></div>
 <p class="cbc-caption">Model ${fmt(m.train_n,0)} seçimden öğrenip ayrı tutulan ${fmt(m.holdout_n,0)} seçimle kontrol edildi. Bu oran, yeni katılımcılarda aynı başarıyı garanti etmez.</p>
 <details class="cbc-details"><summary>Hesaplama ayrıntıları ve sınırlamalar</summary><div class="cbc-details-content">
 <p>Seçim verileri MNL (çok seçenekli logit) modeliyle hesaplanır. <b>Fayda katsayısı</b>, aynı özelliğin seçeneklerini karşılaştırır: daha yüksek değer daha güçlü tercih etkisini gösterir. Her özelliğin ilk seçeneği referanstır ve 0 kabul edilir.</p>
 <div class="table-wrap"><table><caption>Seçeneklerin modeldeki fayda katsayıları</caption><thead><tr><th scope="col">Özellik</th><th scope="col">Seçenek ve katsayı</th><th scope="col">Göreli etki</th></tr></thead><tbody>${m.attributes.map(a=>`<tr><th scope="row">${esc(a.label)}</th><td>${Object.entries(m.coefficients[a.id]).map(([level,v])=>esc(level)+': '+fmt(v,3)).join(' · ')}</td><td>${m.importance[a.id]==null?'Tanımsız':pct(m.importance[a.id])}</td></tr>`).join('')}</tbody></table></div>
 <p>Model ${m.iterations} hesaplama adımında tamamlandı. Tahmin hatası (log-loss): ${fmt(m.holdout_log_loss,3)}. Bu değer küçüldükçe olasılık tahmini iyileşir; yalnız aynı kontrol verisi üzerinde karşılaştırın.</p><p>${esc(m.status)}</p><ul>${m.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></details>`;
}
async function showConjointStudy(id) {
 const ticket=++researchStudyTicket;const box=$('#cbc-study');if(!box)return;
 const current=()=>page==='research'&&researchStudy===id&&ticket===researchStudyTicket&&box.isConnected;
 box.hidden=false;box.innerHTML='<p role="status">Çalışma yükleniyor…</p>';
 $$('[data-study]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.study===id)));
 try {
  const s=await api('/api/research/studies/'+encodeURIComponent(id));if(!current())return;
  box.innerHTML=`<div class="cbc-section-head"><div><span class="cbc-kicker">${s.model?'SONUÇLARINIZ':'SEÇİM EKRANI'}</span><h2>${esc(s.title)}</h2></div><span class="cbc-state">${researchKind(s.kind)}</span></div>
   ${s.model?conjointResultHtml(s.model):s.kind==='synthetic'?'<p>Örnek seçimleri bilgisayar hazırlar. Sonucu görmek için aşağıdaki düğmeye basın.</p>':`
   <p>Her soruda sunulan kongre seçeneklerinden birini seçin. Seçimler bu çalışmaya kaydedilir.</p>
   <div class="form-grid"><div class="field"><label for="cbc-person">Katılımcı kodu</label><input id="cbc-person" pattern="[a-zA-Z0-9_-]+" maxlength="80" required placeholder="Örn. katilimci_001" aria-describedby="cbc-person-help"><p class="hint" id="cbc-person-help">Her kişi için farklı kod. Yalnız harf, rakam, _ ve - kullanın; ad veya e-posta yazmayın.</p></div>
   <div class="field"><label for="cbc-task">Yanıtlanacak soru</label><select id="cbc-task">${s.design.tasks.map((t,i)=>`<option value="${t.id}">Soru ${i+1} / ${s.design.tasks.length}</option>`).join('')}</select><p class="hint">Seçimden sonra sonraki soruya geçilir.</p></div></div>
   ${s.kind==='research'?`<details class="cbc-details" open><summary>Katılımcı bilgilendirmesi ve onam</summary><div class="cbc-details-content cbc-consent-copy">${esc(s.consent_text)}</div></details><label class="consent"><input id="cbc-person-consent" type="checkbox" required> Onam metnini okudum ve kabul ediyorum (${esc(s.consent_version)}).</label>`:''}
   <div class="cbc-question-head"><h3>Hangi kongreyi seçerdiniz?</h3><span id="cbc-progress"></span></div><div class="cbc-alternatives" id="cbc-alternatives"></div>
   <div class="cbc-response-footer"><p id="cbc-response-count">Bu çalışmada ${s.response_count||0} seçim kaydedildi.</p><button class="btn small" id="cbc-next-person" type="button">Yeni katılımcıya geç</button></div>`}
   <p id="cbc-status" class="cbc-message" role="status"></p>
   ${s.model?'<p class="cbc-caption">Sonuçlar kaydedildi. Bu çalışma yeni yanıtlara kapalıdır; yeni seçimler için ayrı çalışma oluşturabilirsiniz.</p>':`<div class="cbc-estimate-area"><h3>${s.kind==='synthetic'?'Örnek sonucu hazırlayın':'Seçimler hazır mı?'}</h3><p>${s.kind==='synthetic'?'Gerçek katılımcı verisi veya API bağlantısı gerekmez.':'Yeterli seçim kaydedildikten sonra özelliklerin tercih üzerindeki etkisini hesaplayın. Sonuç oluşturulduğunda bu çalışmaya yeni yanıt eklenemez.'}</p><button class="btn primary" id="cbc-estimate">${s.kind==='synthetic'?'Örnek sonuçları hesapla':'Seçimlerden sonuç hesapla'}</button></div>`}`;
  if(s.model){
   if(!$('#research-study option[value="'+id+'"]'))$('#research-study')?.insertAdjacentHTML('beforeend',`<option value="${esc(id)}">${esc(s.title)} · ${researchKind(s.kind)}</option>`);
   const card=$('[data-study="'+id+'"] .cbc-study-state');if(card)card.textContent='Sonuçları gör →';
  }
  if(!s.model&&s.kind!=='synthetic'){
   const person=$('#cbc-person'),taskSelect=$('#cbc-task'),status=$('#cbc-status'),alternatives=$('#cbc-alternatives');let responseCount=s.response_count||0;
   const draw=()=>{
    const t=s.design.tasks.find(t=>t.id===taskSelect.value);$('#cbc-progress').textContent=`Soru ${taskSelect.selectedIndex+1} / ${s.design.tasks.length}`;
    alternatives.innerHTML=t.alternatives.map((p,i)=>`<button type="button" class="cbc-option" data-choice="${i}"><span class="cbc-option-title">Seçenek ${String.fromCharCode(65+i)}</span><span class="cbc-option-properties">${s.design.attributes.map(a=>`<span><small>${esc(a.label)}</small><b>${esc(p[a.id])}</b></span>`).join('')}</span><span class="cbc-option-action">Bu kongreyi seç <span aria-hidden="true">→</span></span></button>`).join('');
    $$('[data-choice]',box).forEach(b=>b.onclick=async()=>{
     if(!person.reportValidity())return;const consent=$('#cbc-person-consent');if(consent&&!consent.reportValidity())return;
     const task=taskSelect.value;const selectedButton=b;$$('[data-choice]',box).forEach(el=>el.disabled=true);taskSelect.disabled=true;person.disabled=true;$('#cbc-next-person').disabled=true;$('#cbc-estimate').disabled=true;if(consent)consent.disabled=true;
     status.textContent='Seçiminiz kaydediliyor…';
     try{
      await api('/api/research/studies/'+id+'/responses',{respondent:person.value,task,choice:Number(selectedButton.dataset.choice),consent:Boolean(consent?.checked),consent_version:s.consent_version});
      if(!current())return;responseCount++;$('#cbc-response-count').textContent=`Bu çalışmada ${responseCount} seçim kaydedildi.`;
      if(taskSelect.selectedIndex<s.design.tasks.length-1){taskSelect.selectedIndex++;draw();status.textContent=`Seçiminiz kaydedildi. Soru ${taskSelect.selectedIndex+1} için devam edin.`;}
      else{status.textContent='Son sorunun seçimi kaydedildi. Atladığınız sorular varsa üstten seçebilir veya yeni katılımcıya geçebilirsiniz.';}
     }catch(error){if(current()){status.textContent=error.message;$$('[data-choice]',box).forEach(el=>el.disabled=false);}}
     finally{if(current()){taskSelect.disabled=false;person.disabled=false;$('#cbc-next-person').disabled=false;$('#cbc-estimate').disabled=false;if(consent)consent.disabled=false;}}
    });
   };
   taskSelect.onchange=draw;
   $('#cbc-next-person').onclick=()=>{person.value='';taskSelect.selectedIndex=0;const consent=$('#cbc-person-consent');if(consent)consent.checked=false;status.textContent='Yeni katılımcı için farklı bir kod girin.';draw();person.focus();};
   draw();
  }
  if(!s.model)$('#cbc-estimate').onclick=async e=>{
   const b=e.currentTarget;b.disabled=true;const status=$('#cbc-status');status.textContent='Seçimler inceleniyor, sonuçlar hazırlanıyor…';
   // Prevent a response from being added while the model is being finalized.
   $$('input,select,button',box).forEach(el=>el.disabled=true);
   try{await api('/api/research/studies/'+id+'/estimate',{});if(current()){await showConjointStudy(id);researchFocus(box);}}
   catch(error){if(current()){status.textContent=error.message.startsWith('Yetersiz veri:')?'Sonuç hesaplamak için henüz yeterli seçim yok. Daha fazla katılımcının soruları tamamlamasını sağlayıp tekrar deneyin.':error.message;b.disabled=false;$$('input,select,button',box).forEach(el=>el.disabled=false);}}
  };
 }catch(error){if(current())box.innerHTML=`<p role="alert">${esc(error.message)}</p>`;}
}

function researchExperimentForm(studies) {
 $('#research-experiments').innerHTML=`<details class="cbc-experiment-details"><summary><span>Araştırmacılar için: yöntemleri karşılaştır</span><small>İleri kullanım · Hazırlanmış veri seti gerekir</small></summary><div class="cbc-details-content">
 <p>Aynı kongreleri AHP, tercih modeli ve bu iki yöntemin birlikte kullanımıyla inceleyin. Bu alan, araştırma protokolü ve veri seti hazır olan çalışmalar içindir.</p>
 <dl class="cbc-model-key"><div><dt>M1 · AHP</dt><dd>Uzman kriterlerinden uygunluk puanı.</dd></div><div><dt>M2 · Tercih modeli</dt><dd>Kaydedilmiş seçimlerden tercih sıralaması.</dd></div><div><dt>M3 · AHP + tercih</dt><dd>AHP eşiğini geçen kongreler arasında tercih sıralaması.</dd></div><div><dt>M4 · AI + AHP + tercih</dt><dd>Aynı yöntem; uzman yerine kayıtlı AI kriterleriyle.</dd></div></dl>
 <p class="hint">AHP uygunluk sınırını belirler; tercih modeli bu sınırı geçenleri sıralar. Puanlar keyfî bir oranla toplanmaz. Eksik AHP puanı olanlar M3/M4'e alınmaz. Bu deney kayıtlı kongre sıralamanızı değiştirmez.</p>
 <form id="research-run"><div class="field"><label for="research-dataset">Hazırladığınız araştırma verisi · JSON</label><textarea id="research-dataset" rows="6" required placeholder="Şemaya uygun araştırma kayıtlarını buraya yapıştırın."></textarea><a class="cbc-text-link" href="/api/research/dataset-schema" target="_blank" rel="noopener">Veri dosyasının yapısını görüntüle ↗</a><p class="hint">Anahtar, token, ad veya iletişim bilgisi girmeyin. Aynı kongre serisini hem eğitim hem test için kullanmayın. Gerçek ve örnek verileri ayrı tutun. En fazla 100 kayıt; 200 KB istek sınırı.</p></div>
 <div class="form-grid"><div class="field"><label for="research-study">Kullanılacak tercih sonucu</label><select id="research-study"><option value="">Tercih modeli olmadan · yalnız AHP</option>${studies.filter(s=>s.estimated).map(s=>`<option value="${esc(s.id)}">${esc(s.title)} · ${researchKind(s.kind)}</option>`).join('')}</select></div>
 <div class="field"><label for="research-threshold">En düşük kabul edilen AHP puanı</label><input id="research-threshold" type="number" min="0" max="100" step="any" required placeholder="0–100"><p class="hint">Araştırma protokolünüzde belirlediğiniz eşiği girin.</p></div></div>
 <div class="field"><label for="research-rationale">Bu eşiği ve özellikleri neden seçtiniz?</label><textarea id="research-rationale" required minlength="20" maxlength="2000" placeholder="Eşik seçiminizi, ortak özelliklerin rolünü ve uzman etiketlerinin kaynağını açıklayın."></textarea></div>
 <label class="consent"><input id="research-overlap" type="checkbox" required> Ortak özelliklerin etkisini ve eşik gerekçesini araştırma protokolünde tanımladım.</label><button class="btn primary" type="submit">Yöntemleri karşılaştır</button></form><div id="research-run-result" class="cbc-message" role="status"></div></div></details>`;
 $('#research-run').onsubmit=async e=>{
  e.preventDefault();const form=e.currentTarget,button=$('button',form),out=$('#research-run-result');let dataset;
  try{dataset=JSON.parse($('#research-dataset').value);}catch{out.textContent='Araştırma verisi okunamadı. JSON biçimini kontrol edip tekrar deneyin.';return;}
  button.disabled=true;out.textContent='Yöntemler aynı veri setinde karşılaştırılıyor…';
  try{
   const r=await api('/api/research/experiments',{dataset,study_id:$('#research-study').value||null,minimum_ahp:Number($('#research-threshold').value),overlap_acknowledged:$('#research-overlap').checked,protocol_rationale:$('#research-rationale').value});
   if(!out.isConnected||page!=='research')return;
   out.innerHTML=`<h3>Karşılaştırma sonucu · ${researchKind(r.manifest.origin)}</h3><p>Bu deney bilgisayarınızda hesaplandı; API kotası kullanılmadı.</p><div class="table-wrap"><table><thead><tr><th>Yöntem</th><th>Kongre sırası</th><th>Sıralama uyumu (NDCG)</th></tr></thead><tbody>${Object.entries(r.results.models).map(([name,m])=>`<tr><td>${esc(name)}</td><td>${m.ranking.map(esc).join(' → ')||'Uygun aday yok'}</td><td>${fmt(r.metrics.ndcg[name],3)}</td></tr>`).join('')}</tbody></table></div><p>NDCG, sıralamanın referans uygunluk sırasına uyumunu 0–1 arasında gösterir; 1 daha yüksek uyumdur.</p><p>AI kriterleri için F1: ${fmt(r.metrics.ai_criteria.f1_positive,3)} · Yanıtlanan kriter oranı: ${r.metrics.ai_criteria.prediction_coverage==null?'—':pct(r.metrics.ai_criteria.prediction_coverage)}</p><p class="hint">F1, olumlu kriterleri bulmadaki kesinlik ve duyarlılığı birlikte özetler. Tek başına bilimsel geçerlik ölçüsü değildir.</p><details class="cbc-details"><summary>Deney ayrıntıları ve sınırlamalar</summary><div class="cbc-details-content"><p>Çalıştırma kodu: ${esc(r.run_id)}</p>${r.limitations.map(x=>`<p>${esc(x)}</p>`).join('')}</div></details><button class="btn" id="research-download">Deney raporunu ve verilerini indir · JSON</button>`;
   $('#research-download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='ahp-research-'+r.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  }catch(error){if(out.isConnected)out.textContent=error.message;}finally{if(button.isConnected)button.disabled=false;}
 };
}
if(typeof module!=='undefined')module.exports={conjointResultHtml,researchKind};
