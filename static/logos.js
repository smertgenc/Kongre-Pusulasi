'use strict';
// One visual identity per congress, shared by lists, reports and recommendations.
function logoRecord(id){return typeof state!=='undefined'?state?.logos?.[id]:null;}
function logoContents(id,name){
 const logo=logoRecord(id),hasImage=logo?.status==='ready'&&logo.url;
 const initial=Array.from(String(name||'K'))[0].toLocaleUpperCase('tr-TR');
 const label=logo?.source==='site_icon'?'Web sitesi simgesi':logo?.source==='upload'?'Yüklenen kongre logosu':'Kongre sitesindeki logo';
 return `<span class="logo-fallback" ${hasImage?'hidden':''} aria-hidden="true">${esc(initial)}</span>${hasImage?`<img class="${logo.surface==='dark'?'logo-on-dark':''}" src="${esc(logo.url)}" alt="${esc(name)} · ${label}" title="${label}" loading="lazy" decoding="async">`:''}`;
}
function congressAvatar(id,name,size='normal'){
 return `<span class="congress-icon congress-logo logo-${['normal','small','large'].includes(size)?size:'normal'}" data-logo-id="${esc(id||'')}" data-logo-name="${esc(name||'Kongre')}">${logoContents(id,name)}</span>`;
}
function logoCongressId(metadata,cid){
 if(cid)return cid;
 if(!metadata?.website||typeof state==='undefined')return '';
 // Only an exact official-site match can reuse an existing emblem, never a name guess.
 const website=metadata.website.replace(/\/$/,'');
 return state?.congresses.find(c=>!c.metadata.sample&&c.metadata.website?.replace(/\/$/,'')===website)?.id||'';
}
function applyCongressLogo(id,logo){
 if(!state)return;state.logos??={};state.logos[id]=logo;
 document.querySelectorAll('[data-logo-id]').forEach(node=>{if(node.dataset.logoId===id)node.innerHTML=logoContents(id,node.dataset.logoName);});
}
const logoAttempted=new Set();let logoQueueRunning=false;
async function queueCongressLogos(){
 if(logoQueueRunning||!state)return;logoQueueRunning=true;
 try{
  const records=state.congresses.filter(c=>c.metadata.website&&!c.metadata.sample);
  const queue=records.filter(c=>{const l=logoRecord(c.id),key=c.id+'|'+c.metadata.website;
   if(logoAttempted.has(key)||l?.status==='hidden'||l?.source==='upload')return false;
   return !l||l.website!==c.metadata.website||Date.now()-Date.parse(l.updated_at)>86400000;
  });
  const worker=async()=>{while(queue.length){const c=queue.shift();logoAttempted.add(c.id+'|'+c.metadata.website);
   try{const data=await api('/api/congresses/'+encodeURIComponent(c.id)+'/logo/discover',{});applyCongressLogo(c.id,data.logo);}catch{/* Keep the initial; retrieval must not interrupt AHP work. */}
  }};await Promise.all([worker(),worker()]);
 }finally{logoQueueRunning=false;}
}
function logoField(id,name,prefix){
 return `<div class="field full logo-form-field">${id?`<div class="logo-inline">${congressAvatar(id,name)}<div><b>Kongre logosu</b><p class="hint">Tüm ekranlarda aynı logo kullanılır.</p><button type="button" class="btn small" data-edit-logo="${esc(id)}">Logoyu düzenle</button></div></div>`:`<label for="${prefix}-logo-file">Kongre logosu (isteğe bağlı)</label><input id="${prefix}-logo-file" type="file" accept="image/png,image/jpeg,image/webp,image/x-icon,.ico"><p class="hint">PNG, JPG, WebP veya ICO · En fazla 3 MB. Dosya seçmezseniz kayıtlı web sitesindeki logo aranır.</p>`}</div>`;
}
async function readLogoFile(input){
 const file=input?.files?.[0];if(!file)return null;
 if(file.size>3000000)throw Error('Logo en fazla 3 MB olabilir.');
 if(!/\.(png|jpe?g|webp|ico)$/i.test(file.name))throw Error('PNG, JPG, WebP veya ICO dosyası seçin.');
 return readAiFile(file);
}
async function saveDraftLogo(id,content){
 if(!content)return '';
 try{const data=await api('/api/congresses/'+encodeURIComponent(id)+'/logo/upload',{content});applyCongressLogo(id,data.logo);return '';}
 catch(error){return 'Kongre kaydedildi; logo eklenemedi: '+error.message+' Detay ekranından tekrar yükleyebilirsiniz.';}
}
function editCongressLogo(id){
 const c=state.congresses.find(c=>c.id===id);if(!c)return;
 const dialog=$('#modal');const originalName=c.metadata.name;
 dialog.innerHTML=`<h2>Kongre logosu</h2><div class="logo-manager-preview">${congressAvatar(id,originalName,'large')}<p>${esc(originalName)}</p></div><p>Logo tüm kongre ekranlarında ve kaydedilmiş AI raporunun PDF çıktısında kullanılır. AHP puanları değişmez.</p><label class="logo-upload-label" for="logo-file">Logo dosyası</label><input id="logo-file" type="file" accept="image/png,image/jpeg,image/webp,image/x-icon,.ico"><p class="hint">PNG, JPG, WebP veya ICO · En fazla 3 MB.</p><div class="actions logo-manager-actions"><button type="button" class="btn primary" id="logo-upload">Dosyayı yükle</button><button type="button" class="btn" id="logo-discover" ${c.metadata.website?'':'disabled'}>Web sitesinden bul</button><button type="button" class="btn" id="logo-hide">Logoyu gizle</button><button type="button" class="btn" id="logo-restore">Gizlenen logoyu göster</button></div><p class="hint" id="logo-source"></p><div id="logo-message" role="status" aria-live="polite"></div><div class="actions"><button type="button" class="btn" id="logo-close">Kapat</button></div>`;
 const controls=()=>{const logo=logoRecord(id);$('#logo-hide').hidden=logo?.status!=='ready';$('#logo-restore').hidden=logo?.status!=='hidden';
  $('#logo-source').innerHTML=logo?.source_url?`${logo.source==='site_icon'?'Kongreye ait ayrı logo bulunamadığında sitenin simgesi kullanılır.':'Kaynak: kongrenin kayıtlı web sitesi.'} <a href="${esc(logo.source_url)}" target="_blank" rel="noopener noreferrer">Görsel kaynağı ↗</a>`:logo?.source==='upload'?'Yüklediğiniz dosya bu bilgisayarda saklanır.':'';
 };controls();
 const perform=async action=>{const buttons=$$('button',dialog);buttons.forEach(b=>b.disabled=true);$('#logo-message').textContent='Logo işleniyor…';
  try{const data=await action();applyCongressLogo(id,data.logo);$('#logo-message').textContent=data.message||'Logo güncellendi.';}
  catch(error){$('#logo-message').textContent=error.message;}
  finally{buttons.forEach(b=>b.disabled=false);$('#logo-discover').disabled=!c.metadata.website;controls();}
 };
 $('#logo-upload').onclick=()=>perform(async()=>{const content=await readLogoFile($('#logo-file'));if(!content)throw Error('Önce bir logo dosyası seçin.');return api('/api/congresses/'+encodeURIComponent(id)+'/logo/upload',{content});});
 $('#logo-discover').onclick=()=>perform(()=>api('/api/congresses/'+encodeURIComponent(id)+'/logo/discover',{force:true}));
 $('#logo-hide').onclick=()=>perform(()=>api('/api/congresses/'+encodeURIComponent(id)+'/logo/hide',{}));
 $('#logo-restore').onclick=()=>perform(()=>api('/api/congresses/'+encodeURIComponent(id)+'/logo/restore',{}));
 $('#logo-close').onclick=()=>dialog.close();dialog.showModal();
}
if(typeof document!=='undefined'){
 document.addEventListener('click',event=>{const button=event.target.closest('[data-edit-logo]');if(button){event.preventDefault();editCongressLogo(button.dataset.editLogo);}});
 document.addEventListener('error',event=>{const image=event.target;if(image.tagName==='IMG'&&image.closest('.congress-logo')){image.hidden=true;image.previousElementSibling.hidden=false;}},true);
}
