'use strict';

function splitResearchTerms(value){return [...new Set(String(value||'').split(/[\n,;]+/).map(s=>s.trim()).filter(Boolean))];}
const researchFieldsConfig=[
 ['description','Kongre açıklaması','text',6000],['call_for_papers','Bildiri çağrısı / CFP','text',12000],
 ['research_fields','Akademik alanlar','list',40],['topics','Konu başlıkları','list',40],['keywords','Anahtar kelimeler','list',40],
 ['country','Ülke','short',200],['city','Şehir','short',200],['fee','Ücret ve para birimi','short',500],
 ['address','Fiziksel adres','short',1000],['committee_members','Komite / bilim kurulu üyeleri','list',100],
 ['speaker_names','Konuşmacılar','list',100],['contact_emails','İletişim e-postaları','list',40],
 ['phones','Telefon numaraları','list',40],['publishers','Yayınevleri','list',40],['proceedings','Bildiri kitabı bilgisi','text',2000],
 ['doi_prefixes','DOI önekleri','list',40],['past_congresses','Geçmiş kongre adları','list',40],
 ['past_years','Geçmiş yıllar','years',40],['social_links','Sosyal medya adresleri','list',40]
];
function congressResearchFields(metadata,prefix){
 const data=metadata?.research||{};
 return `<details class="research-details"><summary>Konu ve organizasyon bilgileri (isteğe bağlı)</summary><p class="hint">Benzer kongre ve kişisel uyum için konu bilgisi ekleyin. Organizasyonel benzerlik için bilinen kurul, yayınevi ve iletişim bilgilerini yazın. Liste alanlarında virgül veya yeni satır kullanın; bilinmeyen alanları boş bırakın.</p><div class="form-grid">${researchFieldsConfig.map(([key,label,type,limit])=>{
 const value=Array.isArray(data[key])?data[key].join('\n'):data[key]||'';
 return `<div class="field ${type==='text'?'full':''}"><label for="${prefix}-${key}">${label}</label>${type==='short'?`<input id="${prefix}-${key}" maxlength="${limit}" value="${esc(value)}">`:`<textarea id="${prefix}-${key}" rows="${type==='text'?3:2}" maxlength="${type==='text'?limit:limit*202}">${esc(value)}</textarea>`}</div>`;
 }).join('')}</div></details>`;
}
function readCongressResearch(prefix){
 return Object.fromEntries(researchFieldsConfig.map(([key,,type])=>{
  const text=$('#'+prefix+'-'+key).value.trim();
  return [key,type==='list'?splitResearchTerms(text):type==='years'?splitResearchTerms(text).map(v=>{
   if(!/^\d{4}$/.test(v))throw Error('Geçmiş yılları dört haneli yazın.');return Number(v);
  }):text];
 }));
}
async function profilePage(){
 const hash=location.hash;$('#main').innerHTML='<div class="loading">Araştırma profiliniz yükleniyor…</div>';
 try{
  const profile=await api('/api/profile/research');if(location.hash!==hash)return;
  const draft={research_fields:[...profile.research_fields],keywords:[...profile.keywords]};
  $('#main').innerHTML=heading('KİŞİSEL AKADEMİK UYUM','Araştırma Profilim','Araştırma alanlarınızı ve anahtar kelimelerinizi ekleyin. Kişisel uyum, AHP puanından ayrı hesaplanır.', '<a class="btn" href="#guide">Profil rehberi</a><a class="btn" href="#congresses">Kongrelere dön →</a>')+
   `<form id="research-profile-form" class="panel profile-panel"><p class="hint">Profil bu bilgisayardaki kişisel çalışma alanınıza aittir. Alanlarınız eşleştirme için yerelde kullanılır.</p>${[['research_fields','Araştırma alanları','Örn. Artificial Intelligence'],['keywords','Anahtar kelimeler','Örn. machine learning, LLM']].map(([key,label,placeholder])=>
    `<fieldset class="profile-group"><legend>${label}</legend><div class="profile-tags" id="profile-${key}-tags"></div><label class="hint" for="profile-${key}-input">${label} ekleyin (en fazla 40)</label><div class="tag-entry"><input id="profile-${key}-input" maxlength="200" placeholder="${placeholder}"><button type="button" class="btn" data-add-profile="${key}" aria-label="${label} ekle">Ekle ＋</button></div></fieldset>`).join('')}
    <label class="profile-enabled"><input id="profile-enabled" type="checkbox" ${profile.enabled||!profile.exists?'checked':''}>Kişiselleştirmeyi etkinleştir</label><p class="hint">Türkçe ve İngilizce için tanımlı alan eşleştirmeleri kullanılır. Bu ilk sürüm metin ve etiketlere dayanır; anlamsal AI tahmini değildir.</p><div id="profile-error" role="alert"></div><div class="actions"><button class="btn primary" type="submit" id="profile-save">Profili kaydet</button>${profile.exists?'<button class="btn danger" type="button" id="profile-delete">Profili sil</button>':''}</div><p id="profile-status" class="hint" role="status">${profile.updated_at?'Son güncelleme: '+esc(dateText(profile.updated_at)):''}</p></form>`;
  function draw(key){$('#profile-'+key+'-tags').innerHTML=draft[key].map((term,i)=>`<span class="profile-tag"><span>${esc(term)}</span><button type="button" data-remove-profile="${key}" data-index="${i}" aria-label="${esc(term)} kaldır">×</button></span>`).join('')||'<span class="hint">Henüz eklenmedi.</span>';
   $$('[data-remove-profile]',$('#profile-'+key+'-tags')).forEach(b=>b.onclick=()=>{draft[key].splice(Number(b.dataset.index),1);formDirty=true;draw(key)});
  }
  function add(key){const input=$('#profile-'+key+'-input'),values=splitResearchTerms(input.value);const known=new Set(draft[key].map(v=>v.toLocaleLowerCase('tr-TR')));
   for(const value of values){if(value.length>200)throw Error('Her terim en fazla 200 karakter olabilir.');if(!known.has(value.toLocaleLowerCase('tr-TR'))){if(draft[key].length>=40)throw Error('En fazla 40 terim ekleyebilirsiniz.');draft[key].push(value);known.add(value.toLocaleLowerCase('tr-TR'));}}
   if(values.length)formDirty=true;input.value='';draw(key);
  }
  for(const key of Object.keys(draft)){draw(key);$('#profile-'+key+'-input').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();try{add(key)}catch(err){$('#profile-error').textContent=err.message}}}}
  $$('[data-add-profile]').forEach(b=>b.onclick=()=>{try{add(b.dataset.addProfile);$('#profile-error').textContent=''}catch(err){$('#profile-error').textContent=err.message}});
  $('#research-profile-form').oninput=()=>formDirty=true;
  $('#research-profile-form').onsubmit=async e=>{e.preventDefault();const b=$('#profile-save');b.disabled=true;try{
    for(const key of Object.keys(draft))add(key);
    await api('/api/profile/research',{...draft,enabled:$('#profile-enabled').checked});formDirty=false;
    if(location.hash===hash){await profilePage();$('#profile-status').textContent='Profil kaydedildi. Kongre ve AI raporlarında güncel uyum hesaplanır.'}toast('Araştırma profili kaydedildi.');
   }catch(err){if($('#profile-error'))$('#profile-error').textContent=err.message;b.disabled=false}
  };
  if($('#profile-delete'))$('#profile-delete').onclick=()=>{const dialog=$('#modal');dialog.setAttribute('aria-labelledby','profile-delete-title');
   dialog.innerHTML='<h2 id="profile-delete-title">Araştırma profili silinsin mi?</h2><p>Araştırma alanlarınız ve anahtar kelimeleriniz silinir. Kongreler ve AHP sonuçları korunur.</p><div class="actions"><button class="btn" id="profile-delete-cancel" autofocus>Vazgeç</button><button class="btn danger" id="profile-delete-confirm">Profili sil</button></div><p id="profile-delete-error" role="alert"></p>';
   $('#profile-delete-cancel').onclick=()=>dialog.close();$('#profile-delete-confirm').onclick=async()=>{const b=$('#profile-delete-confirm');b.disabled=true;try{await api('/api/profile/research/delete',{});formDirty=false;dialog.close();if(location.hash===hash)await profilePage();toast('Araştırma profili silindi.')}catch(err){$('#profile-delete-error').textContent=err.message;b.disabled=false}};dialog.showModal();
  };
 }catch(err){if(location.hash===hash)$('#main').innerHTML=`<div class="panel"><h2>Profil yüklenemedi</h2><p>${esc(err.message)}</p><button class="btn" id="profile-retry">Tekrar dene</button></div>`;if($('#profile-retry'))$('#profile-retry').onclick=profilePage}
}
function personalFitMarkup(fit){
 return `<section class="panel insight-personal"><div class="panel-head"><div><div class="eyebrow">ARAŞTIRMA ALANLARINIZA GÖRE</div><h2>Kişisel uyum</h2></div><a class="btn small" href="#profile">Araştırma profilim →</a></div>${fit.score==null?`<p>${esc(fit.message)}</p>`:`<div class="personal-score">%${fmt(fit.score,1)}</div><p class="hint">${esc(fit.message)}</p><div class="fit-matches">${fit.matches.slice(0,6).map(m=>`<div><span>${esc(m.term)}</span><b>%${fmt(m.score,0)}</b></div>`).join('')}</div>`}<p class="hint">Yerel alan/anahtar kelime eşleşmesi; bir kabul olasılığı veya kalite puanı değildir.</p></section>`;
}
function recommendationsMarkup(data){
 return `<section class="panel section-space"><div class="panel-head"><div><div class="eyebrow">KONUYA GÖRE ALTERNATİFLER</div><h2>Benzer kongreler</h2><p>${esc(data.message)}</p></div></div><p class="hint">${esc(data.scope)} Aynı koşullarda daha yüksek AHP puanı olan alternatifler önce gösterilir.</p>${!data.items.length?`<div class="empty compact-empty">${data.available_count?`${data.available_count} aday bulundu; en az 3 uygun aday olduğunda öneri listesi gösterilir.`:'Konu bilgilerini genişletebilir veya yeni kongreler kaydedebilirsiniz.'}</div>`:`<div class="recommendation-grid">${data.items.map(item=>`<article class="recommendation-card"><h3><a class="logo-inline" href="#detail/${encodeURIComponent(item.id)}/${encodeURIComponent(item.evaluation_id)}">${congressAvatar(item.id,item.name)}<span>${esc(item.name)} ↗</span></a></h3><p class="hint">${esc(item.edition)}</p><div class="recommendation-metrics"><span>Benzerlik <b>%${fmt(item.similarity_score,1)}</b></span><span>AHP <b>${fmt(item.ahp_score,1)} / 100</b></span><span>Kişisel uyum <b>${item.personal_fit.score==null?'Profil / konu bilgisi gerekli':'%'+fmt(item.personal_fit.score,1)}</b></span></div>${badge(item.suitability)}<p>${item.ahp_delta==null?'AHP puan farkı karşılaştırılamıyor.':item.ahp_delta>0?'Mevcut kongreden +'+fmt(item.ahp_delta,1)+' AHP puanı daha yüksek.':'Mevcut kongreye göre AHP farkı: '+fmt(item.ahp_delta,1)}</p><p class="hint">Ülke: ${esc(item.country||'Belirtilmedi')} · Konum: ${esc(item.city||item.location||'Belirtilmedi')}<br>Tarih: ${esc(dateText(item.date))} · Ücret: ${esc(item.fee||'Belirtilmedi')}</p><h4>Neden önerildi?</h4><ul>${item.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul><details><summary>Öneri puanının ayrıntısı</summary><p>Birleşik öneri puanı: ${fmt(item.recommendation_score,1)} / 100</p><p class="hint">Benzerlik ağırlığı %${fmt(data.weights.similarity*100,0)}, AHP %${fmt(data.weights.ahp*100,0)}, kişisel uyum %${fmt(data.weights.personal_fit*100,0)}. Eksik veya karşılaştırılamayan bileşenler çıkarılır; kalan ağırlıklar yeniden oranlanır. AHP puanınız değişmez.</p>${item.shared_terms.length?'<p class="hint">Ortak terimler: '+item.shared_terms.map(esc).join(', ')+'</p>':''}</details></article>`).join('')}</div>`}</section>`;
}
function fingerprintMarkup(data){
 const f=data.fingerprint,fields=[['organizer_normalized','Organizatör'],['website_domain','Web domaini'],['email_domains','E-posta domainleri'],['committee_members_normalized','Komite üyeleri'],['speaker_names_normalized','Konuşmacılar'],['address_normalized','Adres'],['doi_prefixes','DOI önekleri'],['publisher_names','Yayınevleri'],['past_congresses','Geçmiş kongreler']];
 return `<section class="panel insight-fingerprint"><div class="eyebrow">KONGRE PARMAK İZİ</div><h2>Organizasyonel benzerlik</h2><p class="hint">Ortak organizasyon bilgileri benzerliği gösterir. Aynı kongre olduğu veya kaliteli olduğu sonucunu vermez.</p>${data.organizational_matches.length?data.organizational_matches.map(m=>`<article class="organization-match"><div class="panel-head"><a class="logo-inline" href="#detail/${encodeURIComponent(m.id)}">${congressAvatar(m.id,m.name)}<span><b>${esc(m.name)}</b><small>${esc(m.edition)}</small></span></a><strong>%${fmt(m.score,1)}</strong></div><p>${esc(m.level)} · Karşılaştırılabilir veri kapsamı %${fmt(m.coverage,0)}</p>${m.limited_evidence?'<p class="hint">Sınırlı veri: yüksek yüzde tek bir ortak özelliğe dayanabilir.</p>':''}<details><summary>Ortak özellikleri göster</summary><ul>${m.shared_features.map(s=>`<li>${esc(s.label)}: %${fmt(s.similarity,1)}</li>`).join('')}</ul></details></article>`).join(''):'<p>Karşılaştırılabilir organizasyon bilgisi olan başka kongre bulunamadı.</p>'}<details class="fingerprint-data"><summary>Bu kongrenin parmak izi</summary><dl>${fields.map(([key,label])=>{const v=f[key];return `<div><dt>${label}</dt><dd>${esc(Array.isArray(v)?v.join(', ')||'Bilinmiyor':v||'Bilinmiyor')}</dd></div>`}).join('')}</dl><p class="hint">İletişim bilgileri kaynak metninden çıkarılabilir; kayıtlı kaynakları kontrol edin. Boş alanlar benzerlik hesabında sıfır sayılmaz.</p><code class="fingerprint-hash">SHA-256: ${esc(f.fingerprint_hash)}</code></details></section>`;
}
function mountIntelligence(endpoint, before=null){
 const root=document.createElement('div');root.id='intelligence-insights';root.className='section-space';
 if(before)before.before(root);else $('#main').append(root);
 loadIntelligence(endpoint,root);
}
async function loadIntelligence(endpoint,root){
 root.innerHTML='<div class="panel" role="status">Kişisel uyum, benzer kongreler ve organizasyon bilgileri hazırlanıyor…</div>';
 try{const data=await api(endpoint);if(!root.isConnected)return;
  root.innerHTML=`<div class="insight-grid section-space">${personalFitMarkup(data.personal_fit)}${fingerprintMarkup(data)}</div>${recommendationsMarkup(data.recommendations)}`;
 }catch(err){if(!root.isConnected)return;root.innerHTML=`<div class="panel"><h2>Ek değerlendirmeler yüklenemedi</h2><p>${esc(err.message)}</p><button class="btn" id="insights-retry">Tekrar dene</button></div>`;$('#insights-retry',root).onclick=()=>loadIntelligence(endpoint,root)}
}

function researchProfileGuide(){
 return `<section class="panel guide profile-guide section-space" aria-labelledby="profile-guide-title">
  <div class="eyebrow">ARAŞTIRMA PROFİLİ VE KİŞİSEL UYUM</div>
  <h2 id="profile-guide-title">Araştırma Profilim ne işe yarar?</h2>
  <p>Bu bölüm, kongrelerin <strong>sizin çalışma alanınız ve araştırma ilginizle ne kadar örtüştüğünü</strong> görmenizi sağlar. Alanlarınızı ve anahtar kelimelerinizi bir kez kaydedersiniz; uygulama bunları kongrelerin konu bilgileri ve kayıtlı kaynak metinleriyle eşleştirir. Böylece hangi kongreleri daha ayrıntılı inceleyeceğinize karar vermeniz kolaylaşır.</p>
  <div class="guide-profile-note"><strong>AHP puanınız değişmez.</strong> Araştırma profili, mevcut 10 kriterin ağırlıklarını veya kaydedilmiş değerlendirmeleri değiştirmez. Kişisel uyum ayrı bir sonuçtur.</div>
  <h3>1. Profilimi nasıl doldururum?</h3>
  <ol>
   <li><strong>Araştırma alanları</strong> bölümüne çalıştığınız geniş alanları yazın. Örneğin: Yönetim Bilişim Sistemleri, Yapay Zekâ.</li>
   <li><strong>Anahtar kelimeler</strong> bölümüne özellikle ilgilendiğiniz konuları ekleyin. Örneğin: makine öğrenmesi, veri analizi, dijital dönüşüm. Kısa ve belirgin terimler kullanın.</li>
   <li>Her girişten sonra <strong>“Ekle ＋”</strong> düğmesine basın veya <strong>Enter</strong> tuşunu kullanın. Birden çok terimi virgülle ayırabilirsiniz. Eklenen terimler etiket olarak görünür.</li>
   <li><strong>“Kişiselleştirmeyi etkinleştir”</strong> seçeneğini işaretli bırakıp <strong>“Profili kaydet”</strong> düğmesine basın. Yalnızca yazmak veya etiket eklemek, profili kaydetmez.</li>
  </ol>
  <h3>2. Sonucu nerede görürüm?</h3>
  <p>Bir <strong>kongre detayını</strong> veya tamamlanmış bir <strong>AI analiz raporunu</strong> açın. <strong>“Kişisel uyum”</strong> bölümünde profilinizle eşleşme yüzdesini ve terimlere ilişkin eşleşmeleri görebilirsiniz. Profilinizi güncelledikten sonra bu ekranları yeniden açmanız yeterlidir; yeni bir AI analizi başlatmanız gerekmez.</p>
  <div class="table-wrap guide-score-table"><table><caption>Puanları nasıl okumalıyım?</caption><thead><tr><th scope="col">Gösterge</th><th scope="col">Size ne söyler?</th></tr></thead><tbody>
   <tr><th scope="row">AHP puanı</th><td>Kongrenin mevcut 10 kriter ve model ağırlıklarıyla hesaplanan uygunluğunu gösterir. Araştırma profilinizden etkilenmez.</td></tr>
   <tr><th scope="row">Kişisel uyum</th><td>Kongre metninin araştırma alanlarınız ve anahtar kelimelerinizi ne ölçüde kapsadığını gösterir. Profilinize göre değişebilir.</td></tr>
  </tbody></table></div>
  <p><strong>Örnek:</strong> Yapay zekâ ve makine öğrenmesiyle ilgileniyorsanız, programında bu konular bulunan bir kongre kişisel açıdan daha uygun görünebilir. AHP puanı yüksek olan başka bir kongre ise araştırma konunuzla daha az örtüşebilir. Karar verirken iki sonucu ve kongrenin programını birlikte inceleyin.</p>
  <h3>3. Benzer kongre önerilerini nasıl etkiler?</h3>
  <p><strong>“Benzer kongreler”</strong> bölümünde konu benzerliği ve karşılaştırılabilir AHP puanlarının yanında kişisel uyum da önerilerin sıralamasına katılır. Sistem kayıtlı aktif kongreleriniz arasından önerir; profil oluşturmak kendiliğinden internet araması başlatmaz. En az üç uygun aday bulunursa en fazla beş öneri gösterilir. Liste boşsa yeterli benzer kayıt olmayabilir; bu, profilinizin hatalı olduğu anlamına gelmez.</p>
  <h3>4. Yüzdeyi nasıl yorumlamalıyım?</h3>
  <p>Yüksek yüzde, eklediğiniz alan ve terimlerin mevcut kongre metninde daha fazla karşılık bulduğunu gösterir. Düşük yüzde, metinde az eşleşme bulunduğunu gösterir; tek başına kongrenin kötü olduğunu söylemez. Konu bilgisi yetersizse veya profiliniz boş/devre dışıysa yüzde yerine açıklama gösterilir.</p>
  <p>Eşleştirme metin, etiketler ve tanımlı Türkçe–İngilizce terim karşılıklarıyla yapılır. Her eş anlamlı ifadeyi veya konunun bağlamını anlayan bir AI değerlendirmesi değildir. Sonuç bir kabul olasılığı, kalite garantisi veya kesin akademik uygunluk kararı olarak okunmamalıdır.</p>
  <h3>5. Profilimi değiştirebilir veya kapatabilir miyim?</h3>
  <p>Evet. Bir etiketi yanındaki <strong>×</strong> ile kaldırabilir, yeni terimler ekleyebilir ve <strong>“Profili kaydet”</strong> ile güncelleyebilirsiniz. Geçici olarak kullanmak istemiyorsanız <strong>“Kişiselleştirmeyi etkinleştir”</strong> işaretini kaldırıp kaydedin; alanlarınız korunur. <strong>“Profili sil”</strong> ise alan ve anahtar kelimelerinizi kaldırır. Kongreleriniz ve AHP sonuçlarınız her iki durumda da korunur.</p>
  <p>Profil isteğe bağlıdır. Bu bilgisayarda saklanır; kişisel uyum hesabı yerelde yapılır, profil bilgileriniz AI sağlayıcısına gönderilmez ve bu eşleştirme için ek API ücreti oluşmaz.</p>
  <div class="actions"><a class="btn primary" href="#profile">Araştırma profilimi düzenle →</a><a class="btn" href="#congresses">Kongrelerde sonucu incele →</a></div>
 </section>`;
}
