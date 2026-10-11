'use strict';

// Compare saved evaluations as they are. Never recalculate old results with a
// different model merely because another page has that model selected.
function comparisonRecords(congresses, models){
 const byModel=new Map(models.map(m=>[m.id,m]));
 return congresses.map(c=>{
  const e=[...c.evaluations].sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at))||a.id.localeCompare(b.id))[0];
  return {...c,e,m:e?byModel.get(e.model_id):undefined};
 });
}
function evaluationSignature(e){return JSON.stringify([e.model_id,e.metadata.context,e.scale,e.policy_version||'manual-v1',e.mode||'manual',e.criteria_profile||'legacy',Boolean(e.metadata.sample),(e.decision_date||e.created_at||'undated').slice(0,10)]);}
function dashboardGroups(records){
 const grouped=new Map();for(const c of records){const key=evaluationSignature(c.e);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(c);}
 return [...grouped].map(([key,rows])=>({key,rows})).sort((a,b)=>Number(a.rows[0].e.metadata.sample||false)-Number(b.rows[0].e.metadata.sample||false)||b.rows.length-a.rows.length);
}
function comparisonSummary(chosen){
 const evaluated=chosen.filter(c=>c.e);
 const signatures=new Set(evaluated.map(c=>evaluationSignature(c.e)));
 const comparable=chosen.length>=2&&evaluated.length===chosen.length&&signatures.size===1&&chosen.every(c=>c.m);
 const complete=evaluated.every(c=>Number.isFinite(c.e.result.total));
 const best=comparable&&complete?Math.max(...evaluated.map(c=>c.e.result.total)):null;
 return {comparable,complete,winners:best==null?[]:evaluated.filter(c=>Math.abs(c.e.result.total-best)<1e-8)};
}
function comparisonSearch(list,query){
 const q=query.trim().toLocaleLowerCase('tr-TR');
 return list.filter(c=>[c.e?.metadata.name||c.metadata.name,c.e?.metadata.edition||c.metadata.edition,c.e?.metadata.location||c.metadata.location].join(' ').toLocaleLowerCase('tr-TR').includes(q));
}
function comparisonKind(c){return c.e.metadata.sample?'Excel örneği':c.e.mode==='ai_reviewed'?'AI analizi · İncelenmiş':'Manuel değerlendirme';}

function compare(){
 const list=comparisonRecords(state.congresses,state.models);
 const validIds=new Set(list.filter(c=>c.e).map(c=>c.id));
 for(const id of selected)if(!validIds.has(id))selected.delete(id);
 $('#main').innerHTML=heading('YAN YANA DEĞERLENDİRİN','Kongre karşılaştırma',
  'Tüm kongreleriniz arasından seçin; puanları, katılım biçimlerini ve kriter katkılarını yan yana inceleyin.',
  '<a class="btn" href="#congresses">Kongreler →</a>')+
  `<section class="panel compare-picker"><div class="panel-head"><div><h2>Karşılaştırılacak kongreler</h2><p>Her kongrenin en son kaydedilmiş değerlendirmesi gösterilir.</p></div><span class="pill">${list.length} kongre</span></div>
   <div class="compare-tools"><div class="field"><label for="compare-search">Kongre ara</label><input type="search" id="compare-search" placeholder="Ad, edisyon veya konum…"></div>
   <div class="actions"><button type="button" class="btn small" id="compare-all">Tümünü seç</button><button type="button" class="btn small" id="compare-clear">Seçimi temizle</button><button type="button" class="btn primary small" id="compare-show">Karşılaştırmayı göster</button></div></div>
   <p class="hint" id="compare-count" role="status" aria-live="polite"></p><div id="compare-selection"></div></section><div id="comparison" class="section-space" tabindex="-1"></div>`;
 const drawResult=()=>{
  const chosen=list.filter(c=>selected.has(c.id)&&c.e),summary=comparisonSummary(chosen);
  if(chosen.length<2){
   $('#comparison').innerHTML='<section class="panel empty"><h2>İki veya daha fazla kongre seçin</h2><p>Yukarıdaki listeden seçim yapın veya “Tümünü seç” düğmesini kullanın.</p></section>';return;
  }
  const banner=!summary.comparable?
   '<div class="banner warn">Seçilen kongrelerin modeli, değerlendirme koşulları, ölçeği veya kayıt türü farklı. Puanlar kendi kayıtlı değerlendirmeleriyle gösterilir; farklı koşullar nedeniyle ortak sıralama yapılmaz.</div>':
   !summary.complete?'<div class="banner warn">Eksik verili kongrelerde olası puan aralığı gösterilir. Kesin sıralama için eksik kriterleri tamamlayın.</div>':
   `<div class="banner">${summary.winners.length>1?'En yüksek puanı paylaşanlar':'En yüksek puan'}: <b>${summary.winners.map(c=>esc(c.e.metadata.name)).join(' · ')}</b> · ${scoreText(summary.winners[0].e.result)}</div>`;
  const row=(label,values)=>`<tr><th scope="row">${label}</th>${values.map(v=>`<td>${v}</td>`).join('')}</tr>`;
  $('#comparison').innerHTML=banner+`<section class="panel table-panel compare-results"><div class="panel-head"><div><h2>Seçilen kongrelerin karşılaştırması</h2><p>${chosen.length} kongre · Geniş tabloyu yatay kaydırabilirsiniz.</p></div></div>
   <div class="table-wrap" tabindex="0" role="region" aria-label="Kongre karşılaştırma tablosu"><table class="compare-table"><caption class="compare-caption">Kayıtlı sonuçlar · Kriter değerleri 0–1 aralığına dönüştürülmüştür.</caption><thead><tr><th scope="col">KONGRE / KRİTER</th>${chosen.map(c=>`<th scope="col"><a href="#detail/${encodeURIComponent(c.id)}/${encodeURIComponent(c.e.id)}" class="logo-inline">${congressAvatar(c.id,c.e.metadata.name)}<span>${esc(c.e.metadata.name)} ↗</span></a><small>${esc(c.e.metadata.edition)}</small></th>`).join('')}</tr></thead><tbody>
   ${row('Toplam AHP puanı',chosen.map(c=>`<h2>${scoreText(c.e.result)} <small>/ 100</small></h2><div class="compare-badge">${badge(c.e.result.status)}</div>`))}
   ${row('AHP modeli',chosen.map(c=>c.m?`${esc(c.m.name)} · v${c.m.version}`:'Model bilgisi bulunamadı'))}
   ${row('Değerlendirme koşulları',chosen.map(c=>esc(c.e.metadata.context||'Belirtilmedi')))}
   ${row('Kayıt türü / ölçek',chosen.map(c=>`${comparisonKind(c)}<p class="hint">0–${c.e.scale}</p>`))}
   ${row('Katılım biçimi',chosen.map(c=>esc(c.e.metadata.format||'Belirtilmedi')))}
   ${row('Konum',chosen.map(c=>esc(c.e.metadata.location||'Belirtilmedi')))}
   ${row('Değerlendirme tarihi',chosen.map(c=>esc(dateText(c.e.created_at))))}
   ${state.criteria.map(k=>row(`${k.code} · ${esc(k.name)}`,chosen.map(c=>{
    const u=c.e.utilities[k.code],weight=c.m?.weights[k.code];
    return `<span class="heat" style="background:${u==null?'#eef0f4':`rgba(45,91,214,${.08+u*.23})`}">${u==null?'Eksik':fmt(u,2)}</span><p class="hint">${weight==null?'Ağırlık bilinmiyor':pct(weight,1)+' ağırlık'}<br>${fmt(c.e.result.contributions[k.code])} puan katkı</p>`;
   }))).join('')}
   </tbody></table></div></section>`;
 };
 const updateCount=()=>{
  const visible=comparisonSearch(list,$('#compare-search').value),hidden=list.filter(c=>selected.has(c.id)&&!visible.some(v=>v.id===c.id)).length;
  $('#compare-count').textContent=`${visible.length} / ${list.length} kongre gösteriliyor · ${selected.size} seçili${hidden?' · '+hidden+' seçim arama dışında':''}`;
  $('#compare-clear').disabled=selected.size===0;
  $('#compare-show').disabled=selected.size<2;
  $('#compare-all').disabled=!visible.some(c=>c.e&&!selected.has(c.id));
  $('#compare-all').textContent=$('#compare-search').value.trim()?'Görünenleri seç':'Tümünü seç';
 };
 const drawSelection=()=>{
  const visible=comparisonSearch(list,$('#compare-search').value);
  $('#compare-selection').innerHTML=visible.length?`<div class="selection-grid">${visible.map(c=>{
   const meta=c.e?.metadata||c.metadata;
   return `<label class="compare-card ${selected.has(c.id)?'is-selected':''}"><input type="checkbox" data-compare="${esc(c.id)}" ${selected.has(c.id)?'checked':''} ${c.e?'':'disabled'}>${congressAvatar(c.id,meta.name)}<span><strong>${esc(meta.name)}</strong><small>${esc(meta.edition||'Edisyon belirtilmedi')}</small>${c.e?`<small class="compare-score">${scoreText(c.e.result)} puan · ${esc(c.e.result.status)}</small><small>${c.m?'Model v'+c.m.version:'Model bulunamadı'} · ${comparisonKind(c)} · 0–${c.e.scale}</small><small class="compare-context">${esc(meta.context||'Koşul belirtilmedi')}</small>`:'<small>Henüz değerlendirme yok</small>'}</span></label>`;
  }).join('')}</div>`:`<div class="empty"><p>${list.length?'Aramanızla eşleşen kongre yok.':'Henüz kongre eklenmemiş.'}</p></div>`;
  $$('[data-compare]').forEach(el=>el.onchange=()=>{
   el.checked?selected.add(el.dataset.compare):selected.delete(el.dataset.compare);
   el.closest('.compare-card').classList.toggle('is-selected',el.checked);updateCount();drawResult();
  });
  updateCount();drawResult();
 };
 $('#compare-search').oninput=drawSelection;
 $('#compare-all').onclick=()=>{comparisonSearch(list,$('#compare-search').value).filter(c=>c.e).forEach(c=>selected.add(c.id));drawSelection();};
 $('#compare-clear').onclick=()=>{selected.clear();drawSelection();};
 $('#compare-show').onclick=()=>{$('#comparison').scrollIntoView({behavior:'smooth',block:'start'});$('#comparison').focus({preventScroll:true});};
 drawSelection();
}

if(typeof module!=='undefined')module.exports={comparisonRecords,comparisonSummary,comparisonSearch,evaluationSignature,dashboardGroups};
