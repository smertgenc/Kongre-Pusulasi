'use strict';
const aiStatuses={detected:'Kanıt bulundu',not_found:'Bilgi eksik',conflict:'Kaynak çelişkisi',ready:'İncelemeye hazır',failed:'Tamamlanamadı',processing:'Analiz sürüyor'};
const aiFieldNames={name:'Kongre adı',edition:'Edisyon / yıl',start_date:'Başlangıç tarihi',end_date:'Bitiş tarihi',location:'Konum',organizer:'Düzenleyen',format:'Katılım biçimi'};
let aiSourceCounter=0;
let aiRetrySources=null;
let aiRetryPolicy=null;
function modeTabs(active){return `<div class="mode-tabs" aria-label="Analiz yöntemi"><a class="${active==='manual'?'active':''}" href="#new">✎ Manuel değerlendirme</a><a class="${active==='ai'?'active':''}" href="#ai">✦ AI ile analiz</a></div>`;}
function aiMessage(error){return `<div class="banner error" role="alert">${esc(error)}</div>`;}
let aiResearchSettings=null;
let aiHistoryDeleted=false;
function aiFallbackRecipients(settings,enabled=true){
  return enabled?(settings.fallback_providers||[]).map(p=>({provider_id:p.provider_id,provider_model:p.provider_model})):[];
}
function aiPlanNames(settings,enabled=true){
  return [settings.provider,...(enabled?(settings.fallback_providers||[]).map(p=>p.provider_name):[])];
}
const aiFailureNames={RATE_LIMIT:'Token veya istek kotası doldu',QUOTA_EXHAUSTED:'API kredisi yetersiz',REQUEST_TOO_LARGE:'İstek token sınırını aştı',OUTPUT_TOKEN_LIMIT:'Yanıt token sınırına ulaştı',SERVICE_UNAVAILABLE:'Servis geçici olarak kullanılamadı',TIMEOUT:'Bağlantı zaman aşımı',CONNECTION_ERROR:'Bağlantı kurulamadı',DNS_ERROR:'Servis adresi çözümlenemedi',AUTH_ERROR:'API anahtarı kabul edilmedi',ACCESS_DENIED:'API erişimi reddedildi',MODEL_UNAVAILABLE:'Model kullanılamadı',INVALID_REQUEST:'Model isteği kabul etmedi',OUTPUT_SCHEMA_ERROR:'Yanıt biçimi doğrulanamadı'};
function aiExecutionSummary(report){
  if(!report.provider_plan?.length)return '';
  const plan=report.provider_plan.map(p=>p.provider_name+' · '+p.provider_model).join(' → ');
  const used=(report.providers_used||[]).map(p=>p.provider_name+' · '+p.provider_model+' ('+p.batches+' parça)').join(' / ');
  return `<section class="panel section-space ai-execution"><h2>AI çalışma kaydı</h2><p><b>Sağlayıcı sırası:</b> ${esc(plan)}</p>${used?`<p><b>Sonuca katkı verenler:</b> ${esc(used)}</p>`:''}${report.resumed_batches?`<p>${esc(report.resumed_batches)} tamamlanmış parça önceki denemeden korundu.</p>`:''}${(report.provider_failures||[]).map(p=>`<p class="hint">${esc(p.provider_name)}: ${esc(aiFailureNames[p.code]||'İstek tamamlanamadı')}${p.http_status?' · HTTP '+esc(p.http_status):''}</p>`).join('')}${report.status!=='ready'&&report.completed_batches?`<p>${esc(report.completed_batches)} tamamlanmış parça kayıtlı. Kısmi sonuçtan AHP puanı üretilmedi.</p>`:''}</section>`;
}
function readAiFile(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=()=>reject(Error('Dosya okunamadı.'));r.readAsDataURL(file)})}
function updateAiConsent(){
  const label=$('#ai-consent-label');if(!label?.dataset.provider)return;
  const names=[...new Set($$('[data-source]').filter(c=>$('select',c).value==='search').map(c=>$('.search-provider',c)?.selectedOptions[0]?.textContent.split(' · ')[0]).filter(Boolean))];
  label.textContent='Kaynak metinlerinin '+label.dataset.provider+' üzerinden AHP analizi için gönderilmesini'+(names.length?' ve arama sorgularının '+names.join(' / ')+' üzerinden araştırılmasını':'')+' kabul ediyorum. Görsellerin yalnızca bu bilgisayarda okunan metni gönderilir.';
}
function addAiSource(source=null){
  if($$('[data-source]').length>=4){toast('En fazla dört kaynak ekleyebilirsiniz.',true);return}
  const id=++aiSourceCounter;
  $('#ai-sources').insertAdjacentHTML('beforeend',`<fieldset class="source-card" data-source="${id}"><legend>Kaynak ${id}</legend><div class="source-heading"><select aria-label="Kaynak türü"><option value="text">Düz metin</option><option value="url">Web adresi</option><option value="search">Web araması · Jina / Tavily</option><option value="pdf">PDF dosyası</option><option value="image">Görsel · afiş / broşür</option><option value="instagram">Instagram metni</option></select><button type="button" class="btn small remove-source">Kaldır</button></div><div class="source-inputs"></div></fieldset>`);
  const card=$('#ai-sources').lastElementChild,kind=$('select',card);
  const draw=()=>{
    const p=$('.source-inputs',card);card.archive=null;
    if(kind.value==='url')p.innerHTML=`<label>Web adresi<input type="url" class="source-content" required placeholder="https://kongre.org/program"></label><p class="hint">Bu adres ve aynı kongreye ait en fazla dört ilgili sayfa okunur; her alıntının kaynağı raporda gösterilir.</p>`;
    else if(kind.value==='search'){
      const providers=aiResearchSettings?.providers||[{id:'jina',name:'Jina AI Search'},{id:'tavily',name:'Tavily'}];
      p.innerHTML=`<label>Arama servisi<select class="search-provider">${providers.map(x=>`<option value="${x.id}" ${x.id===aiResearchSettings?.provider_id?'selected':''}>${esc(x.name)} · ${x.configured?'Anahtar kayıtlı':'Anahtar gerekli'}</option>`).join('')}</select></label><label>Aranacak kongre<input class="source-content" required minlength="3" maxlength="500" placeholder="Kongre adı, yıl, bilim kurulu ve program"></label><p class="hint">En fazla üç kaynak bulunur ve seçili AI modeli tarafından AHP kriterleriyle incelenir. <a href="#ai-settings">Arama anahtarlarını yönetin →</a></p>`;
      $('.search-provider',card).onchange=()=>{formDirty=true;$('#ai-consent').checked=false;updateAiConsent()};
    }else if(kind.value==='pdf')p.innerHTML=`<label>PDF dosyası<input type="file" class="source-file" accept="application/pdf,.pdf" required></label><p class="hint">En fazla 4 MB, 30 sayfa. Taranmış PDF sayfasını görsel olarak yükleyebilir veya metnini yapıştırabilirsiniz.</p>`;
    else if(kind.value==='image'){
      p.innerHTML=`<label>Kongre görseli<input type="file" class="source-file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" required></label><p class="hint">PNG, JPEG veya WebP · en fazla 4 MB / 20 megapiksel. Afiş ve broşür yazıları bu bilgisayarda okunur; okunan metin AI analizine gönderilir. Fotoğraftaki nesneler yorumlanmaz.</p><div class="image-preview"></div>`;
      $('.source-file',card).onchange=async e=>{const f=e.target.files[0],preview=$('.image-preview',card);card.archive=null;preview.innerHTML='';if(!f)return;if(f.size>4000000){toast('Görsel en fazla 4 MB olabilir.',true);e.target.value='';return}const data=await readAiFile(f);if(e.target.files[0]===f&&['image/png','image/jpeg','image/webp'].includes(f.type))preview.innerHTML=`<img src="data:${f.type};base64,${data}" alt="Yüklenen kongre görselinin önizlemesi">`};
    }else p.innerHTML=`<label>${kind.value==='instagram'?'Gönderi açıklaması':'Kaynak metni'}<textarea rows="7" class="source-content" required minlength="20" maxlength="60000" placeholder="Kongre duyurusu, programı, bilim kurulu veya diğer belgelerden metni yapıştırın."></textarea></label>${kind.value==='instagram'?'<label>Gönderi bağlantısı (isteğe bağlı)<input type="url" class="source-url" placeholder="https://www.instagram.com/p/…"></label><p class="hint">Instagram bağlantısı tek başına okunmaz; gönderi metnini de ekleyin.</p>':''}`;
  };
  kind.onchange=()=>{formDirty=true;$('#ai-consent').checked=false;draw();updateAiConsent()};draw();
  if(source){kind.value=source.kind;draw();if($('.source-content',card))$('.source-content',card).value=source.content;if($('.source-url',card))$('.source-url',card).value=source.url||'';if(source.kind==='image'){card.archive=source;$('.source-file',card).required=false;$('.image-preview',card).textContent='Önceki görsel korunuyor: '+(source.label||'Kongre görseli')}if(source.search_provider)$('.search-provider',card).value=source.search_provider}
  $('.remove-source',card).onclick=()=>{if($$('[data-source]').length>1){card.remove();formDirty=true;$('#ai-consent').checked=false;updateAiConsent()}else toast('En az bir kaynak gereklidir.',true)};
  updateAiConsent();
}
async function aiPage(){
  let connection=null;
  const ahpModel=[...state.models].sort((a,b)=>a.version-b.version)[0],retrySources=aiRetrySources;aiRetrySources=null;
  $('#main').innerHTML=heading('EXCEL MODELİNİZLE ANALİZ','Kongreyi AHP ile analiz et','Kongre kaynaklarını ekleyin. Yapay zekâ 10 kriteri 0/1 değerlendirir; ham puan, AHP puanı ve gerekçeler birlikte gösterilir.',`<a class="btn" href="#ai-settings">AI bağlantısı ⚙</a>`)+modeTabs('ai')+`<form id="ai-form" class="ai-workflow"><section class="panel ai-upload-panel"><div class="panel-head"><div><h2>Kongre kaynakları</h2><p>Metin, web adresi, web araması, PDF veya görsel · en fazla dört kaynak</p></div></div>${retrySources?'<div class="banner">Önceki kaynaklar getirildi. Kontrol edip yeniden analiz edebilirsiniz.</div>':''}<div id="ai-sources"></div><button type="button" class="btn" id="ai-add-source">＋ Kaynak ekle</button><div class="field"><label for="ai-scoring-policy">Puanlama politikası</label><select id="ai-scoring-policy"><option value="legacy">Mevcut proje politikası</option><option value="scientific">Bilimsel kanıt politikası</option></select><p class="hint">Mevcut politika: eksik K1–K9 için 0, K10 için 1 varsayımı. Bilimsel politika: eksik, uygulanamaz veya çelişkili bilgi puansız kalır; AHP aralığı gösterilir. Eski kayıtlar değişmez.</p></div><div class="ahp-method-summary"><span class="eyebrow">UYGULANAN AHP YÖNTEMİ</span><h2>${esc(ahpModel.name)} · v${ahpModel.version}</h2><p>10 kriter · Excel ağırlıkları · 0/1 puanlama</p><p class="hint">Ham puan: 10 kriterin toplamı / 10. AHP puanı: kriter değeri × mevcut global ağırlık × 100. Eksik verinin işlenmesi yukarıdaki politika seçimine bağlıdır. Politika sürümü raporda saklanır; CPCI çelişkileri uzman incelemesi gerektirir.</p><a href="#model" class="method-link" id="ai-method-link">AHP ağırlıklarını görüntüle ↗</a></div><div class="ai-run"><div id="ai-connection"></div><div id="ai-failover"></div><label class="consent"><input id="ai-consent" type="checkbox" required><span id="ai-consent-label">Sağlayıcı bilgisi yükleniyor…</span></label><p class="hint">Kota veya token sınırında, otomatik geçiş açıksa yukarıda gösterilen sağlayıcı sırasıyla devam edilir. Tamamlanmış parçalar yeniden gönderilmez. Her parça ve bağlantı denemesi API kotası veya ücret kullanabilir.</p><button id="ai-submit" class="btn primary" type="submit" disabled>✦ AHP analizini başlat</button><div id="ai-progress" role="status" aria-live="polite"></div><div id="ai-error"></div></div></section></form><section class="panel section-space"><div class="panel-head"><h2>Analiz geçmişi</h2><div class="actions"><button class="btn small" id="ai-history-refresh">Yenile</button><button class="btn small" id="ai-history-trash">Silinen analizler</button><button class="btn small danger" id="ai-history-clear">Geçmişi temizle</button></div></div><div id="ai-history">Yükleniyor…</div></section>`;
  if(aiRetryPolicy){$('#ai-scoring-policy').value=aiRetryPolicy;aiRetryPolicy=null;}
  $('#ai-method-link').onclick=()=>{selectedModel=ahpModel.id};
  aiSourceCounter=0;aiHistoryDeleted=false;
  if(retrySources?.length)retrySources.forEach(addAiSource);else addAiSource();
  $('#ai-add-source').onclick=()=>{addAiSource();formDirty=true};
  $('#ai-form').oninput=()=>formDirty=true;$('#ai-history-refresh').onclick=loadAiHistory;
  $('#ai-history-trash').onclick=()=>{aiHistoryDeleted=!aiHistoryDeleted;$('#ai-history-trash').textContent=aiHistoryDeleted?'Analiz geçmişine dön':'Silinen analizler';$('#ai-history-clear').hidden=aiHistoryDeleted;loadAiHistory()};
  $('#ai-history-clear').onclick=()=>confirmAiDelete();
  $('#ai-form').onsubmit=async e=>{
    e.preventDefault();const form=e.target,button=$('#ai-submit'),error=$('#ai-error'),progress=$('#ai-progress');button.disabled=true;error.innerHTML='';
    try{
      if(!connection?.configured)throw Error('Önce AI bağlantısını kurun.');
      const consent=$('#ai-consent').checked,fallbacks=aiFallbackRecipients(connection,Boolean($('#ai-failover-enabled',form)?.checked));
      $$('input,textarea,select,button',form).forEach(el=>el.disabled=true);
      const sources=[];
      for(const card of $$('[data-source]',form)){
        const kind=$('select',card).value;let content,label='';
        if(kind==='pdf'||kind==='image'){
          const f=$('.source-file',card).files[0];
          if(!f&&card.archive){content=card.archive.content;label=card.archive.label||''}
          else{if(!f||f.size>4000000)throw Error('Dosya en fazla 4 MB olabilir.');label=f.name;content=await readAiFile(f)}
        }else content=$('.source-content',card).value;
        const item={kind,content,label,url:$('.source-url',card)?.value||''};
        if(kind==='search'){item.search_provider=$('.search-provider',card).value;if(!aiResearchSettings?.providers.find(x=>x.id===item.search_provider)?.configured)throw Error('Arama servisi için AI bağlantısı ekranına API anahtarı ekleyin.');}
        sources.push(item);
      }
      const body={scoring_policy:$('#ai-scoring-policy').value,provider_id:connection.provider_id,provider_model:connection.model,fallback_providers:fallbacks,sources,model_id:ahpModel.id,transfer_consent:consent};
      progress.innerHTML='<span class="spinner"></span> Kaynaklar inceleniyor, 10 kriter değerlendiriliyor ve AHP sonucu hesaplanıyor…';form.setAttribute('aria-busy','true');
      const r=await api('/api/ai/start',body);
      if($('#ai-form')===form){formDirty=false;location.hash='#ai-report/'+r.id}else toast('AHP analizi tamamlandı. Analiz geçmişinden açabilirsiniz.');
    }catch(err){error.innerHTML=aiMessage(err.message)}finally{$$('input,textarea,select,button',form).forEach(el=>el.disabled=false);button.disabled=!connection?.configured;if($('#ai-failover-enabled'))$('#ai-failover-enabled').disabled=!(connection?.fallback_providers?.length);progress.textContent='';form.removeAttribute('aria-busy')}
  };
  const activeForm=$('#ai-form');
  try{const [settings,research]=await Promise.all([api('/api/ai/settings'),api('/api/search/settings')]);if($('#ai-form')!==activeForm)return;connection=settings;aiResearchSettings=research;
    $$('.search-provider',activeForm).forEach(select=>{for(const option of select.options){const p=research.providers.find(x=>x.id===option.value);option.textContent=p.name+' · '+(p.configured?'Anahtar kayıtlı':'Anahtar gerekli')}});
    const backups=settings.fallback_providers||[];
    $('#ai-failover').innerHTML=`<label class="consent"><input id="ai-failover-enabled" type="checkbox" ${backups.length?'checked':'disabled'}><span>Kota dolarsa kayıtlı başka bir AI sağlayıcısıyla otomatik devam et</span></label><p id="ai-failover-plan" class="hint"></p>`;
    const showPlan=()=>{
      const enabled=$('#ai-failover-enabled').checked,names=aiPlanNames(settings,enabled);
      $('#ai-failover-plan').textContent=backups.length?'Sağlayıcı sırası: '+names.join(' → '):'Otomatik geçiş için AI bağlantısı ekranında en az bir farklı sağlayıcının anahtarını da kaydedin.';
      $('#ai-consent-label').dataset.provider=names.join(' / ');updateAiConsent();
    };
    $('#ai-failover-enabled').onchange=()=>{$('#ai-consent').checked=false;showPlan()};showPlan();
    $('#ai-connection').innerHTML=settings.configured?`<div class="connection-ready">✦ ${esc(settings.provider)} · ${esc(settings.model)}</div>`:`<div class="banner">${esc(settings.provider)} ile analiz için <a href="#ai-settings"><b>AI bağlantısını kurun →</b></a>.</div>`;
    $('#ai-submit').disabled=!settings.configured;await loadAiHistory();
  }catch(e){if($('#ai-form')===activeForm)$('#ai-connection').innerHTML=aiMessage(e.message)}
}
async function loadAiHistory(){
  const container=$('#ai-history'),deleted=aiHistoryDeleted;if(!container)return;
  try{const rows=await api('/api/ai/analyses?deleted='+deleted);if($('#ai-history')!==container||deleted!==aiHistoryDeleted)return;
    container.innerHTML=(deleted?'<p class="hint">Silinen analizler geri yüklenebilir. Kongreye kaydedilen değerlendirmeler korunur.</p>':'')+(rows.length?rows.map(r=>`<div class="ai-history-row"><a class="logo-inline" href="#ai-report/${r.id}">${congressAvatar(logoCongressId({website:r.website},r.congress_id),r.name)}<span><strong>${esc(r.name)}</strong><small>${dateText(r.created_at)} · ${aiStatuses[r.status]||esc(r.status)}</small></span></a><button class="btn small ${deleted?'':'danger'}" data-history-id="${r.id}" ${r.status==='processing'?'disabled':''}>${deleted?'Geri yükle':'Sil'}</button></div>`).join(''):'<div class="empty">'+(deleted?'Silinen analiz yok.':'Henüz AI analizi yok. İlk analizinizi yukarıdan başlatabilirsiniz.')+'</div>')+(rows.length===100?'<p class="hint">En son 100 analiz gösteriliyor. Geçmişi temizle tüm tamamlanmış analizlere uygulanır.</p>':'');
    $$('[data-history-id]',container).forEach(button=>button.onclick=async()=>{if(!deleted){confirmAiDelete(button.dataset.historyId);return}button.disabled=true;try{await api('/api/ai/analyses/'+button.dataset.historyId+'/restore',{});await loadAiHistory();toast('Analiz geri yüklendi.')}catch(e){button.disabled=false;toast(e.message,true)}});
  }catch(e){if($('#ai-history')===container)container.innerHTML=aiMessage(e.message)}
}
function confirmAiDelete(id=null){
  const modal=$('#modal');modal.innerHTML=`<h2>${id?'Analizi geçmişten kaldır':'Analiz geçmişini temizle'}</h2><p>${id?'Bu analiz':'Tamamlanmış ve başarısız tüm analizler'} silinen analizlere taşınacak. Kongreler ve kaydedilmiş değerlendirmeler korunur. Silinen analizleri geri yükleyebilirsiniz. Çalışan analizler silinmez.</p><div class="actions"><button class="btn" id="history-cancel">Vazgeç</button><button class="btn danger" id="history-confirm">${id?'Analizi sil':'Geçmişi temizle'}</button></div>`;modal.showModal();
  $('#history-cancel').onclick=()=>modal.close();$('#history-confirm').onclick=async e=>{e.target.disabled=true;try{const r=await api(id?'/api/ai/analyses/'+id+'/delete':'/api/ai/analyses/clear',{});modal.close();await loadAiHistory();toast(id?'Analiz silinenlere taşındı.':r.deleted+' analiz silinenlere taşındı.'+(r.processing?' Çalışan analizler korundu.':''))}catch(err){e.target.disabled=false;toast(err.message,true)}};
}
function savedConnectionTestState(saved,selected,key,model){
  const dirty=selected!==saved.provider_id||Boolean(key)||(model!==undefined&&model!==saved.model);
  return {dirty,enabled:saved.configured&&!dirty,
    target:'Test edilecek kayıtlı servis: '+saved.provider+(saved.model?' · '+saved.model:''),
    hint:dirty?'Değişiklikler henüz kaydedilmedi. Testten önce ayarları kaydedin.':!saved.configured?'Test için önce API anahtarını kaydedin.':''};
}
function connectionTestLabel(name,model){return 'Test edilen servis: '+name+(model?' · '+model:'');}
async function aiSettingsPage(){
  $('#main').innerHTML=heading('YAPAY ZEKÂ BAĞLANTISI','AI bağlantısını kurun','AI modeliyle analiz edin; Jina AI Search veya Tavily ile web’den kaynak bulun.',`<a class="btn" href="#ai">Analize dön →</a>`)+`<section class="panel settings-panel"><form id="ai-settings-form"><div id="ai-settings-status" aria-live="polite">Ayarlar yükleniyor…</div><fieldset id="ai-settings-fields" class="settings-fields" disabled><label for="ai-provider">AI sağlayıcısı</label><select id="ai-provider" required></select><p class="hint">Her sağlayıcının anahtarı ve modeli ayrı saklanır. Seçiminiz kaydettiğinizde öncelikli sağlayıcı olur. Diğer kayıtlı anahtarlar, analiz ekranında otomatik geçiş için kullanılabilir.</p><label for="ai-key" id="ai-key-label">API anahtarı</label><input id="ai-key" type="password" autocomplete="new-password" spellcheck="false" maxlength="500"><p class="hint" id="ai-key-status"></p><label for="ai-provider-model">Model</label><input id="ai-provider-model" required maxlength="200" spellcheck="false" autocomplete="off"><p class="hint" id="ai-model-help"></p><button class="btn small" type="button" id="ai-default-model">Önerilen modeli kullan</button><p class="hint">Anahtarınız tarayıcıya geri gönderilmez. Bağlantı testi kayıtlı modele küçük bir örnek istek gönderir ve API kotası kullanabilir. Kongre kayıtlarınız gönderilmez.</p><p class="hint" id="ai-test-target" aria-live="polite"></p><div class="actions"><button class="btn primary" type="submit">Bağlantı ayarlarını kaydet</button><button class="btn" type="button" id="ai-connection-test" disabled>AI bağlantısını test et</button></div></fieldset><div id="ai-settings-message" role="status" aria-live="polite"></div></form></section>`;
  const form=$('#ai-settings-form'),fields=$('#ai-settings-fields'),providerSelect=$('#ai-provider');let settings;
  const current=()=>settings.providers.find(p=>p.id===providerSelect.value);
  const updateTest=()=>{
    if(!settings)return;
    const t=savedConnectionTestState(settings,providerSelect.value,$('#ai-key').value,$('#ai-provider-model').value);
    $('#ai-connection-test').disabled=!t.enabled;$('#ai-test-target').textContent=t.target+(t.hint?' · '+t.hint:'');
  };
  const showProvider=()=>{
    const p=current();$('#ai-key').value='';$('#ai-key').required=!p.configured;
    $('#ai-key-label').textContent=p.name+' API anahtarı';$('#ai-key').placeholder=p.configured?'Yeni anahtar (isteğe bağlı)':p.name+' anahtarınızı yapıştırın';
    $('#ai-key-status').textContent=p.configured?p.name+' anahtarı kayıtlı. Korumak için boş bırakın.':p.name+' için henüz anahtar kaydedilmemiş.';
    $('#ai-provider-model').value=p.model;$('#ai-model-help').textContent=p.help;$('#ai-settings-message').innerHTML='';updateTest();
  };
  const show=s=>{
    if($('#ai-settings-form')!==form)return;settings=s;
    $('#ai-settings-status').innerHTML=`<div class="banner">Kayıtlı AI servisi: <b>${esc(s.provider)}</b> · ${s.configured?'Anahtar kayıtlı':'Anahtar gerekli'}</div>`;
    providerSelect.innerHTML=s.providers.map(p=>`<option value="${p.id}" ${p.id===s.provider_id?'selected':''}>${esc(p.name)}${p.configured?' · Anahtar kayıtlı':''}</option>`).join('');
    showProvider();fields.disabled=false;
  };
  providerSelect.onchange=showProvider;
  $('#ai-key').oninput=$('#ai-provider-model').oninput=()=>{updateTest();$('#ai-settings-message').innerHTML='';};
  $('#ai-default-model').onclick=()=>{$('#ai-provider-model').value=current().default_model;updateTest();$('#ai-settings-message').innerHTML='';};
  form.onsubmit=async e=>{
    e.preventDefault();const body={provider_id:providerSelect.value,api_key:$('#ai-key').value,model:$('#ai-provider-model').value};fields.disabled=true;
    try{const result=await api('/api/ai/settings',body);if($('#ai-settings-form')!==form)return;show(result);$('#ai-settings-message').innerHTML=`<div class="banner">${esc(result.provider)} ayarları kaydedildi. Bağlantıyı test edebilirsiniz.</div>`}
    catch(err){if($('#ai-settings-form')===form)$('#ai-settings-message').innerHTML=aiMessage(err.message)}finally{fields.disabled=false}
  };
  $('#ai-connection-test').onclick=async()=>{
    if(!settings||!savedConnectionTestState(settings,providerSelect.value,$('#ai-key').value,$('#ai-provider-model').value).enabled)return;
    const saved=settings,label=connectionTestLabel(saved.provider,saved.model);fields.disabled=true;
    $('#ai-settings-message').textContent=label+' · API isteği gönderiliyor…';
    try{const result=await api('/api/ai/test',{provider_id:saved.provider_id,provider_model:saved.model});if($('#ai-settings-form')!==form)return;
      $('#ai-settings-message').innerHTML=`<p>${esc(connectionTestLabel(result.provider,result.model))}</p><div class="banner">Bağlantı başarılı</div>`;
    }catch(err){if($('#ai-settings-form')===form)$('#ai-settings-message').innerHTML=`<p>${esc(label)}</p>`+aiMessage(err.message)}finally{fields.disabled=false}
  };
  loadResearchSettings();
  try{show(await api('/api/ai/settings'))}catch(e){if($('#ai-settings-form')===form)$('#ai-settings-message').innerHTML=aiMessage(e.message)}
}

function aiEvidence(f,sources){return f.evidence.map(e=>{const s=sources.find(x=>x.id===e.source_id),segment=s?.segments.find(x=>x.id===e.segment_id);return `<blockquote><p>“${esc(e.quote)}”</p><cite>${esc(segment?.label||s?.label||e.source_id)}${segment?.page?' · Sayfa '+segment.page:''}${s?.retrieved_at?' · Erişim: '+esc(dateText(s.retrieved_at)):''}${(segment?.url||s?.url)?` · <a href="${esc(segment?.url||s.url)}" target="_blank" rel="noopener noreferrer">Kaynağı aç ↗</a>`:''}</cite></blockquote>`}).join('')||'<p class="hint">Bu kriter için kullanılabilir kaynak alıntısı yok.</p>'}
let aiReportTicket=0;
async function aiReport(id){
  const ticket=++aiReportTicket;
  $('#main').innerHTML='<div class="loading">Analiz raporu yükleniyor…</div>';
  let d;try{d=await api('/api/ai/analyses/'+encodeURIComponent(id))}catch(e){if(page==='ai-report')$('#main').innerHTML=aiMessage(e.message);return}
  if(ticket!==aiReportTicket||page!=='ai-report'||!location.hash.endsWith('/'+id))return;
  const a=d.analysis,title=a?.metadata?.name||'Kongre analizi';
  const logoId=logoCongressId({...a?.metadata,website:a?.metadata?.website||d.sources.find(s=>s.kind==='url')?.url},d.review?.saved.id);
  const top=heading('KAYNAKTAN KARARA',`<span class="congress-title">${congressAvatar(logoId,title,'large')}<span>${esc(title)}</span></span>`,`Analiz: ${esc(dateText(d.created_at))} · ${esc(d.provider_name||'OpenAI')} · ${esc(d.provider_model)} · AHP v${d.model.version}`,`<a class="btn" href="#ai">← Analizler</a>${d.status==='ready'?`<a class="btn primary" href="/api/ai/analyses/${encodeURIComponent(id)}/pdf" download>PDF indir ↓</a><button class="btn" id="ai-print">Yazdır</button>`:''}`)+aiExecutionSummary(d);
  if(d.status!=='ready'){
    $('#main').innerHTML=top+`<section class="panel"><h2>${d.latest_retry?.status==='ready'?'Önceki deneme tamamlanamadı':aiStatuses[d.status]}</h2>${d.latest_retry?`<div class="banner">${d.latest_retry.status==='ready'?'Sonraki deneme başarıyla tamamlandı.':'Bu kaynaklarla yeni bir deneme var.'} <a href="#ai-report/${d.latest_retry.id}"><b>${d.latest_retry.status==='ready'?'Sonucu aç →':'Yeni denemeyi aç →'}</b></a></div>`:''}<p class="subtitle" id="ai-live-stage">${esc(d.error||d.stage)}</p>${d.error_details?.http_status?`<p class="provider-diagnostic">${esc(d.error_details.provider||d.provider_name||'AI')} · HTTP ${esc(d.error_details.http_status)}</p>`:''}${d.status==='processing'?'<p class="hint">Sonuç otomatik güncellenecek. Kota dolarsa izin verdiğiniz sıradaki AI sağlayıcısıyla devam edilir; tamamlanan parçalar korunur. Bu sayfadan ayrılsanız da analiz sunucuda sürer. Tüm servisler kullanılamıyorsa ilerleme kaydedilir.</p>':''}<div class="ai-error-actions">${d.status==='processing'?'<button class="btn" id="ai-reload">Durumu yenile</button>':`${d.sources.length&&!d.deleted?'<button class="btn primary" id="ai-retry-stored">Kayıtlı kaynaklarla tekrar dene →</button><button class="btn" id="ai-retry-sources">Kaynakları düzenle</button>':'<a class="btn primary" href="#ai">Kaynak ekle →</a>'}<a class="btn" href="#ai-settings">AI bağlantısını kontrol et</a>`}</div>${d.status==='failed'&&d.provider_id==='groq'&&d.error_details?.code==='REQUEST_TOO_LARGE'&&!d.connection_events?.some(e=>e.phase==='batch')?'<div class="banner">Yeni sürüm, uzun kaynakları otomatik olarak küçük parçalarda işler. Kayıtlı kaynaklarla tekrar deneyebilirsiniz.</div>':''}${d.status==='failed'?'<p class="hint">Kayıtlı kaynaklarla tekrar denemede Jina/Tavily araması ve dosya okuma yenilenmez. Kayıtlı tamamlanmış parçalar korunur; yalnız kalan parçalar işlenir. Önceki kayıt korunur; yeni sonuç ayrıca kaydedilir.</p>':''}</section>`;
    if($('#ai-reload'))$('#ai-reload').onclick=()=>aiReport(id);
    if($('#ai-retry-stored'))$('#ai-retry-stored').onclick=()=>retryStoredAnalysis(d);
    if($('#ai-retry-sources'))$('#ai-retry-sources').onclick=()=>{aiRetryPolicy=d.scoring_policy||'legacy';aiRetrySources=d.sources.map(s=>s.kind==='url'?{kind:'url',content:s.url}:s.kind==='image'?{kind:'image',content:s.image.data,label:s.label}:s.kind==='search'?{kind:'search',content:s.query,search_provider:s.search_provider}:{kind:'text',content:s.segments.map(p=>p.text).join('\n')});location.hash='#ai'};
    if(d.status==='processing')pollAiProgress(id,ticket);
    return;
  }
  const r=d.review?.saved.result||a.result,complete=a.policy_version?a.completeness:d.review?Object.values(d.review.decisions).filter(x=>x.final_value!==null).length/10:a.completeness;
  const missing=a.findings.filter(f=>f.basis==='project_default'||f.value==null),low=a.findings.filter(f=>f.value!==null&&f.confidence<.75);
  const sourceHtml=d.sources.map(s=>`<details class="source-snapshot"><summary>${esc(s.label)} · ${({pdf:'PDF',url:'Web',image:'Görsel / OCR',search:'Web araması'})[s.kind]||'Metin'} · ${esc(dateText(s.retrieved_at))}</summary><p class="hint">SHA-256: ${esc(s.content_hash)}</p>${s.image?`<img class="source-image" src="data:${esc(s.image.mime)};base64,${esc(s.image.data)}" alt="${esc(s.label)}">`:''}${s.warnings.map(w=>`<p class="banner">${esc(w)}</p>`).join('')}${s.segments.map(p=>`<div class="source-text"><b>${p.page?'Sayfa '+p.page:esc(p.label||'Analiz edilen metin')}</b>${p.url?` · <a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">Kaynağı aç ↗</a>`:''}<p>${esc(p.text)}</p></div>`).join('')}</details>`).join('');
  $('#main').innerHTML=top+`${d.retry_of?'<div class="banner">Analiz, önceki denemenin kayıtlı kaynaklarıyla tamamlandı. Varsa tamamlanmış parçalar kullanıldı; arama ve dosya okuma tekrarlanmadı.</div>':''}${d.deleted?'<div class="banner warn">Bu analiz silinenler arasında. Yeni değerlendirme kaydetmek için analiz geçmişinden geri yükleyin.</div>':''}<div class="banner">${d.review?'İncelemeniz kaydedildi. Nihai puan aşağıdadır.':'AHP analizi tamamlandı. Excel ağırlıklarıyla hesaplanan sonuç ve kriter katkıları aşağıda. Kongre kaydına eklemek için bulguları inceleyebilirsiniz.'} Güven değerleri modelin tahminidir; kaynak doğruluğunu garanti etmez.</div><div class="stats ai-stats"><div class="stat"><div class="stat-label">${d.review?'İncelenmiş':'Hesaplanan'} AHP puanı</div><div class="stat-value ai-score">${scoreText(r)}</div>${badge(r.status)}<p class="hint">${r.total==null?'Eksik veriye göre olası aralık':'100 üzerinden'}</p></div><div class="stat"><div class="stat-label">AI güven tahmini</div><div class="stat-value">${a.confidence==null?'—':pct(a.confidence,0)}</div><p class="hint">Bulunan kriterlerin ağırlıklı ortalaması</p></div><div class="stat"><div class="stat-label">${a.policy_version?'Kanıt kapsamı':'Veri tamlığı'}</div><div class="stat-value">${pct(complete,0)}</div><p class="hint">${Math.round(complete*10)} / 10 kriter · ${d.sources.length} kaynak</p></div></div><section class="panel section-space"><h2>Analiz özeti</h2><p class="subtitle">${a.policy_version?esc(a.general_explanation):`AI tespitlerinde ${missing.length} kriterde bilgi eksik veya çelişkili. ${low.length} bulgu düşük güvenle işaretlendi. Puan, kriter değerleri ve AHP ağırlıklarının çarpımlarından hesaplandı.`}</p>${a.conflicts.map(c=>`<div class="banner error">Kaynak çelişkisi · ${esc(aiFieldNames[c.field])}: ${c.values.map(esc).join(' / ')}</div>`).join('')}${a.warnings.map(w=>`<p class="hint">${esc(w)}</p>`).join('')}</section>${a.criteria_profile?scientificSummary(d):''}${a.policy_version?aiPolicyTable(d):''}${aiCalculationTable(d)}<form id="ai-review-form"><section class="panel section-space ai-review-metadata"><h2>Kongre bilgilerini kontrol edin</h2><div class="form-grid ai-meta">${Object.keys(aiFieldNames).map(field=>field==='format'?participationField(d.review?.metadata[field]||a.metadata[field]||'','ai-format'):`<div class="field"><label for="ai-meta-${field}">${esc(aiFieldNames[field])}${['name','edition'].includes(field)?' *':''}</label><input id="ai-meta-${field}" ${['name','edition'].includes(field)?'required':''} type="${field.endsWith('date')?'date':'text'}" maxlength="500" value="${esc(d.review?.metadata[field]||a.metadata[field]||'')}"></div>`).join('')}<div class="field"><label for="ai-reviewer">İnceleyen *</label><input id="ai-reviewer" maxlength="120" required value="${esc(d.review?.evaluator||'')}"></div><div class="field full"><label for="ai-profile">Uygulanan değerlendirme yöntemi</label><textarea id="ai-profile" rows="3" readonly>${esc(d.context)}</textarea></div><div class="field full"><label for="ai-existing">Kongreye kaydet</label><select id="ai-existing"><option value="">Yeni kongre oluştur</option>${state.congresses.map(c=>`<option value="${c.id}">${esc(c.metadata.name)} · ${esc(c.metadata.edition)} — yeni değerlendirme ekle</option>`).join('')}</select></div></div>${d.review?'':logoField(null,title,"ai-review")}${congressResearchFields(d.review?.metadata||a.metadata,"ai-research")}</section><section class="panel section-space ai-findings-panel"><div class="panel-head"><div><h2>Kriterler ve kanıtlar</h2><p>Bulunamayan bilgi, kriterin sağlanmadığı anlamına gelmez.</p></div>${d.review?'':`<button class="btn small" type="button" id="ai-approve-known">${a.policy_version?'Tüm proje puanlarını seç':'Kanıtlı bulguları onayla'}</button>`}</div>${a.findings.map(f=>findingCard(f,d)).join('')}</section><section class="panel section-space ai-source-panel"><h2>Analiz kaynakları</h2><p class="subtitle">Analiz sırasında okunan metinler; kaynak sonradan değişse de bu kopyalar korunur.</p>${sourceHtml}</section><div id="ai-review-error"></div><div class="actions">${d.review?`<a class="btn primary" href="${d.review.saved.deleted?'#trash':'#detail/'+d.review.saved.id+'/'+d.review.saved.evaluation_id}">${d.review.saved.deleted?'Kongre çöp kutusunda · Geri yükle':'Kaydedilen değerlendirmeyi aç ↗'}</a>`:'<button type="submit" class="btn primary" id="ai-review-save">İncelemeyi ve değerlendirmeyi kaydet ↗</button>'}<span class="hint">Bilinmeyen kriterler varsa eksik değerlendirme olarak kaydedilir.</span></div></form>`;
  $('#ai-print').onclick=()=>window.print();
  mountIntelligence('/api/ai/analyses/'+encodeURIComponent(id)+'/insights',$('#main > section.panel.section-space:not(.ai-execution)'));
  $('#ai-review-form').insertAdjacentHTML('beforebegin',`<section class="print-only"><h2>Kongre bilgileri</h2><p>${Object.entries(d.review?.metadata||a.metadata).filter(([key])=>key in aiFieldNames).map(([key,value])=>esc(aiFieldNames[key])+': '+esc(value||'Belirtilmedi')).join(' · ')}</p><h2>Kaynaklar</h2><ul>${d.sources.flatMap(s=>s.segments.map(p=>`<li>${esc(p.label||s.label)}${p.url||s.url?' · '+esc(p.url||s.url):''} · Erişim: ${esc(dateText(s.retrieved_at))}</li>`)).join('')}</ul></section>`);
  if(d.deleted&&!d.review){$$('#ai-review-form input,#ai-review-form textarea,#ai-review-form select,#ai-review-form button').forEach(el=>el.disabled=true);return}
  if(d.review){for(const [code,decision] of Object.entries(d.review.decisions)){const card=$(`[data-criterion="${code}"]`);$('.review-action',card).value=decision.action==='correct'?String(decision.user_value):decision.action;$('.review-note',card).value=decision.note}$$('#ai-review-form input,#ai-review-form textarea,#ai-review-form select').forEach(e=>e.disabled=true);return}
  $('#ai-review-form').oninput=()=>formDirty=true;
  $('#ai-approve-known').onclick=()=>{for(const f of a.findings)if(f.value!==null&&(a.policy_version||f.confidence>=.75))$(`[data-criterion="${f.criterion}"] .review-action`).value='approve';formDirty=true;toast(a.policy_version?'Kanıta ve proje varsayılanlarına dayanan tüm puanlar seçildi. Kaydetmeden önce kontrol edebilirsiniz.':'Güveni en az %75 olan kanıtlı bulgular seçildi. Diğerlerini ayrıca inceleyin.')};
  $('#ai-review-form').onsubmit=async e=>{
    e.preventDefault();const button=$('#ai-review-save');button.disabled=true;
    try{
      const logoContent=await readLogoFile($('#ai-review-logo-file'));
      const metadata={context:d.context,website:d.sources.find(s=>s.kind==='url')?.url||''};
    for(const f of Object.keys(aiFieldNames))metadata[f]=f==='format'?participationValue('ai-format'):$('#ai-meta-'+f).value;
      metadata.research=readCongressResearch('ai-research');
      const decisions={};for(const card of $$('[data-criterion]')){const v=$('.review-action',card).value;decisions[card.dataset.criterion]={action:['true','false'].includes(v)?'correct':v,value:['true','false'].includes(v)?v==='true':null,note:$('.review-note',card).value}}
      const cid=$('#ai-existing').value,existing=state.congresses.find(c=>c.id===cid);
      const reviewed=await api('/api/ai/analyses/'+id+'/review',{metadata,evaluator:$('#ai-reviewer').value,decisions,congress_id:cid||null,previous_id:existing?.evaluations[0]?.id||null});
      formDirty=false;const logoWarning=await saveDraftLogo(reviewed.id||reviewed.saved?.id,logoContent);await refresh();if(page==='ai-report'&&location.hash.endsWith('/'+id))aiReport(id);toast(logoWarning||'İnceleme ve AHP sonucu kaydedildi.',Boolean(logoWarning));
    }catch(err){if($('#ai-review-error'))$('#ai-review-error').innerHTML=aiMessage(err.message);button.disabled=false}
  };
}
function findingCard(f,d){
  const c=state.criteria.find(c=>c.code===f.criterion),v=f.basis==='project_default'?'Proje kuralı · '+Number(f.value):f.value==null?'Bilinmiyor':f.value?'Karşılıyor · 1':'Karşılamıyor · 0';
  return `<article class="ai-finding" data-criterion="${f.criterion}"><div class="finding-head"><div><span class="eyebrow">${f.criterion} · Ağırlık ${pct(d.model.weights[f.criterion],1)}</span><h3>${esc(c.name)}</h3></div><span class="pill">${esc(v)}</span></div><p>${esc(f.explanation)}</p><div class="finding-flags">${f.basis==='project_default'?'Proje varsayılanı · '+esc(aiStatuses[f.status]):esc(aiStatuses[f.status])} · Güven ${f.confidence_label?esc(f.confidence_label):pct(f.confidence,0)}${f.flags.includes('LOW_CONFIDENCE')?' · Manuel kontrol önerilir':''}${f.flags.includes('UNVERIFIED_EVIDENCE')?' · Alıntı kaynakla eşleşmedi':''}</div>${aiEvidence(f,d.sources)}<div class="review-inputs"><label>İnceleme kararı<select class="review-action"><option value="unknown">Bilinmiyor olarak bırak</option><option value="approve" ${f.value==null?'disabled':''}>${f.basis==='project_default'?'Proje varsayılanını kabul et':'AI bulgusunu onayla'}</option><option value="true">Düzelt · karşılıyor (1)</option><option value="false">Düzelt · karşılamıyor (0)</option><option value="reject">Bulguyu reddet</option></select></label><label>Gerekçe / düzeltme notu<textarea class="review-note" rows="2" maxlength="2000" placeholder="Düzeltme ve reddetme için gerekçe gereklidir."></textarea></label></div></article>`;
}

function aiCalculationTable(d){
  const result=d.review?.saved.result||d.analysis.result;
  const rows=state.criteria.map(c=>{
    const value=d.review?d.review.decisions[c.code].final_value:d.analysis.utilities[c.code];
    const contribution=result.contributions[c.code];
    return `<tr><td><b>${c.code}</b> · ${esc(c.name)}</td><td>${pct(d.model.weights[c.code],2)}</td><td>${value==null?'Bilinmiyor':Number(value)}</td><td>${contribution==null?'—':fmt(contribution,2)}</td></tr>`;
  }).join('');
  return `<section class="panel ai-method-table"><div class="panel-head"><div><h2>AHP hesabı ve kriter katkıları</h2><p>${esc(d.model.name)} · v${d.model.version} · Excel ağırlıkları</p></div></div><p class="hint">Her kriterin katkısı = 0/1 değeri × global ağırlık × 100. Toplam, bu katkıların toplamıdır.</p><div class="table-wrap"><table><thead><tr><th>Kriter</th><th>Ağırlık</th><th>Değer</th><th>Puan katkısı</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td colspan="3"><b>${result.total==null?'Olası AHP puanı':'Toplam AHP puanı'}</b></td><td><b>${scoreText(result)}</b></td></tr></tfoot></table></div><p class="hint">${classificationLegend(d.model)}. ${d.analysis.criteria_profile?'Eksik kriterler puansızdır; ağırlıklar yeniden dağıtılmaz.':d.analysis.policy_version?'Varsayılan 0/1 değerleri de AHP hesabına katılır; kanıt kapsamı ayrıca gösterilir.':'Eksik kriterler kesin toplamı belirlemeye yetmez.'}</p></section>`;
}

function aiPolicyTable(d){
  const a=d.analysis,raw=d.review?d.review.saved.raw_score:a.raw_score;
  return `<section class="panel ai-policy-panel section-space"><div class="panel-head"><div><span class="eyebrow">10 KRİTER · 0/1 DEĞERLENDİRME</span><h2>Toplam Ham Puan: ${raw==null?'Eksik':raw} / 10</h2></div><a class="btn small" href="/api/ai/analyses/${encodeURIComponent(d.id)}/result">AI sonucu · JSON indir</a></div><p class="hint">${d.review?'Tablo kaydedilen inceleme kararlarını gösterir. JSON dosyası ilk AI sonucunu içerir.':'Puanlar otomatik hesaplandı. Ayrıntıları açarak gerekçe, kanıt ve kaynağı inceleyin.'} Kanıt bulunmayan varsayılanlar düşük güvenle işaretlenir.</p><div class="table-wrap"><table class="policy-table"><thead><tr><th>Kriter</th><th>Puan</th><th>Güven</th><th>Gerekçe ve kaynak</th></tr></thead><tbody>${a.findings.map(f=>{
    const decision=d.review?.decisions[f.criterion],value=decision?decision.final_value:f.value,c=state.criteria.find(c=>c.code===f.criterion),corrected=decision&&decision.action!=='approve';
    return `<tr><td><b>${f.criterion}</b> · ${esc(c.name)}</td><td><strong>${value==null?'—':Number(value)}</strong></td><td>${corrected?'Kullanıcı kararı':esc(f.confidence_label)}${f.basis==='project_default'&&!corrected?'<small class="default-tag">Proje kuralı</small>':''}</td><td><details><summary>Gerekçe ve kanıtı gör</summary><p>${esc(corrected?(decision.note||'Kullanıcı bilinmiyor olarak kaydetti.'):f.explanation)}</p>${aiEvidence(f,d.sources)}</details></td></tr>`;
  }).join('')}</tbody><tfoot><tr><td colspan="3"><b>Toplam Ham Puan</b></td><td><b>${raw==null?'Eksik':raw} / 10</b></td></tr></tfoot></table></div></section>`;
}

let aiPrintDetails=[];
window.addEventListener('beforeprint',()=>{aiPrintDetails=$$('.policy-table details').map(el=>[el,el.open]);aiPrintDetails.forEach(([el])=>el.open=true)});
window.addEventListener('afterprint',()=>{aiPrintDetails.forEach(([el,open])=>el.open=open);aiPrintDetails=[]});

async function loadResearchSettings(){
  $('#main').insertAdjacentHTML('beforeend',`<section class="panel settings-panel research-panel"><span class="eyebrow">WEB ARAŞTIRMASI</span><h2>Jina AI Search / Tavily</h2><p class="subtitle">Bu servisler kaynak bulur. AHP değerlendirmesini yukarıda seçtiğiniz AI modeli yapar.</p><form id="research-form"><div id="research-status" aria-live="polite"></div><fieldset id="research-fields" class="settings-fields" disabled><label for="research-provider">Arama servisi</label><select id="research-provider"><option value="jina">Jina AI Search</option><option value="tavily">Tavily</option></select><label for="research-key" id="research-key-label">API anahtarı</label><input id="research-key" type="password" autocomplete="new-password" spellcheck="false" maxlength="500"><p id="research-key-hint" class="hint"></p><p class="hint">Anahtar yalnızca bu bilgisayarda saklanır. Bağlantı testi kayıtlı servisle küçük bir örnek arama yapar ve servis kotasını kullanabilir.</p><p id="research-test-target" class="hint" aria-live="polite"></p><div class="actions"><button class="btn primary" type="submit">Arama ayarlarını kaydet</button><button class="btn" type="button" id="research-test">Bağlantıyı test et</button></div></fieldset><div id="research-message" role="status" aria-live="polite"></div></form></section>`);
  const form=$('#research-form'),fields=$('#research-fields'),select=$('#research-provider');let settings;
  const updateTest=()=>{
    if(!settings)return;
    const t=savedConnectionTestState(settings,select.value,$('#research-key').value);
    $('#research-test').disabled=!t.enabled;$('#research-test-target').textContent=t.target+(t.hint?' · '+t.hint:'');
  };
  const showProvider=()=>{const p=settings.providers.find(x=>x.id===select.value);$('#research-key').value='';$('#research-key').required=!p.configured;$('#research-key-label').textContent=p.name+' API anahtarı';$('#research-key-hint').textContent=p.configured?'Anahtar kayıtlı. Korumak için boş bırakın.':'Henüz anahtar kayıtlı değil.';$('#research-message').innerHTML='';updateTest();};
  const show=s=>{if($('#research-form')!==form)return;settings=s;select.value=s.provider_id;$('#research-status').innerHTML=`<div class="banner">Kayıtlı arama servisi: <b>${esc(s.provider)}</b> · ${s.configured?'Anahtar kayıtlı':'Anahtar gerekli'}</div>`;fields.disabled=false;showProvider()};
  select.onchange=showProvider;
  $('#research-key').oninput=()=>{updateTest();$('#research-message').innerHTML='';};
  form.onsubmit=async e=>{e.preventDefault();const body={provider_id:select.value,api_key:$('#research-key').value};fields.disabled=true;try{const r=await api('/api/search/settings',body);if($('#research-form')!==form)return;show(r);$('#research-message').innerHTML='<div class="banner">Arama ayarları kaydedildi. Bağlantıyı test edebilirsiniz.</div>'}catch(err){if($('#research-form')===form)$('#research-message').innerHTML=aiMessage(err.message)}finally{fields.disabled=false}};
  $('#research-test').onclick=async()=>{
    if(!settings||!savedConnectionTestState(settings,select.value,$('#research-key').value).enabled)return;
    const saved=settings,label=connectionTestLabel(saved.provider);fields.disabled=true;
    $('#research-message').textContent=label+' · Örnek arama yapılıyor…';
    try{const r=await api('/api/search/test',{provider_id:saved.provider_id});if($('#research-form')!==form)return;
      $('#research-message').innerHTML=`<p>${esc(connectionTestLabel(r.provider))}</p><div class="banner">Bağlantı başarılı · ${r.result_count} kaynak okundu.</div><ul class="search-test-results">${r.results.map(x=>`<li><a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)} ↗</a></li>`).join('')}</ul>`;
    }catch(err){if($('#research-form')===form)$('#research-message').innerHTML=`<p>${esc(label)}</p>`+aiMessage(err.message)}finally{fields.disabled=false}
  };
  try{show(await api('/api/search/settings'))}catch(err){if($('#research-form')===form)$('#research-message').innerHTML=aiMessage(err.message)}
}

function pollAiProgress(id,ticket,failures=0){
  setTimeout(async()=>{
    if(ticket!==aiReportTicket||page!=='ai-report'||location.hash!=='#ai-report/'+id)return;
    try{
      const result=await api('/api/ai/analyses/'+encodeURIComponent(id)+'/progress');
      if(ticket!==aiReportTicket||page!=='ai-report'||location.hash!=='#ai-report/'+id)return;
      if(result.status!=='processing'){await aiReport(id);return}
      if($('#ai-live-stage'))$('#ai-live-stage').textContent=result.stage;
      pollAiProgress(id,ticket);
    }catch(error){
      if(ticket!==aiReportTicket||page!=='ai-report'||location.hash!=='#ai-report/'+id)return;
      if($('#ai-live-stage'))$('#ai-live-stage').textContent='Durum bağlantısı kesildi; analiz kaydı korunuyor. '+(failures<11?'Bağlantı tekrar kontrol edilecek.':'Durumu yenile düğmesini kullanın.');
      if(failures<11)pollAiProgress(id,ticket,failures+1);
    }
  },failures?5000:2000);
}
async function retryStoredAnalysis(report){
  const button=$('#ai-retry-stored');button.disabled=true;
  try{
    const settings=await api('/api/ai/settings');
    if(page!=='ai-report'||location.hash!=='#ai-report/'+report.id)return;
    if(!settings.configured)throw Error('Önce AI bağlantısından bir sağlayıcı anahtarı kaydedin.');
    const modal=$('#modal');modal.innerHTML=`<h2>Kayıtlı kaynaklarla yeniden analiz</h2><p>Kayıtlı kaynakların kalan parçaları <b>${esc(aiPlanNames(settings).join(" → "))}</b> sırasıyla analiz edilecek. Kota dolduğunda sıradaki servise otomatik geçilir. ${report.completed_batches?esc(report.completed_batches)+" tamamlanmış parça kayıtlı; yöntem sürümü aynıysa yeniden gönderilmez.":""} Jina/Tavily araması ve dosya okuma tekrarlanmaz. Parçalar ve yeniden denemeler API kotası veya ücret kullanabilir. Kaynak metinlerinin bu sağlayıcılara gönderilmesini onaylayarak devam edin.</p><div class="actions"><button class="btn" id="retry-cancel">Vazgeç</button><button class="btn primary" id="retry-confirm">${esc(settings.provider)} ile yeniden dene</button></div><div id="retry-error" role="alert"></div>`;modal.showModal();
    $('#retry-cancel').onclick=()=>modal.close();
    $('#retry-confirm').onclick=async e=>{e.target.disabled=true;try{const result=await api('/api/ai/analyses/'+report.id+'/retry',{provider_id:settings.provider_id,provider_model:settings.model,fallback_providers:aiFallbackRecipients(settings),transfer_consent:true});modal.close();location.hash='#ai-report/'+result.id}catch(error){$('#retry-error').innerHTML=aiMessage(error.message);e.target.disabled=false}};
  }catch(error){toast(error.message,true)}finally{button.disabled=false}
}

function scientificSummary(d){
 const a=d.analysis;
 return `<section class="panel section-space"><h2>Bilimsel değerlendirme kapsamı</h2><p>${esc(a.policy_version)} · ${esc(a.criteria_profile)}</p><p>Kanıtlı kriter oranı: ${pct(a.completeness)} · Ağırlıklı kanıt kapsamı: ${pct(a.evidence_coverage)} · Sayı atanmış ağırlık: ${pct(a.assigned_coverage)}</p><p>AI güveni kalibre edilmiş başarı olasılığı değildir. AHP ağırlıklarının kaynağı ve 70/90 eşikleri deneysel doğrulama gerektirir.</p><p>${a.findings.map(f=>esc(f.criterion+': '+({positive:'Olumlu kanıt',negative:'Olumsuz kanıt',unknown:'Bilinmiyor',not_applicable:'Uygulanamaz',conflict:'Çelişkili'}[f.state]||'Bilinmiyor'))).join(' · ')}</p></section>`;
}
