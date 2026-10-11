'use strict';
function databaseCounts(counts){
  return `<div class="database-counts">${[['active_congresses','Aktif kongre'],['evaluations','Değerlendirme'],['ai_analyses','AI analizi'],['models','AHP modeli']].map(([key,label])=>`<div><strong>${esc(counts[key]??0)}</strong><span>${label}</span></div>`).join('')}</div>`;
}
async function databasePage(){
  $('#main').innerHTML=heading('KAYITLARINIZI TAŞIYIN','Veritabanı','SQLite dosyanızı seçin, içeriğini kontrol edin ve uygulamaya bağlayın.')+
    `<div class="database-layout"><section class="panel"><div class="eyebrow">MEVCUT BAĞLANTI</div><h2>Bağlı veritabanı</h2><div id="database-status" aria-live="polite">Bağlantı bilgileri yükleniyor…</div></section>
    <section class="panel"><div class="eyebrow">SQLITE DOSYASI</div><h2>Başka bir veritabanı bağla</h2><p class="hint">Kongre Pusulası’ndan alınmış bir <b>.db</b>, <b>.sqlite</b> veya <b>.sqlite3</b> dosyası seçin. Dosya en fazla 100 MB olabilir.</p>
    <p class="hint">Seçtiğiniz dosyanın bu bilgisayardaki çalışma kopyası kullanılır. Yeni kayıtlar bu kopyaya yazılır. Kaynak dosyanız ve önceki veritabanınız korunur; kayıtlar birleştirilmez.</p>
    <form id="database-form"><label for="database-file">SQLite veritabanı dosyası</label><input type="file" id="database-file" accept=".db,.sqlite,.sqlite3,application/vnd.sqlite3" required>
    <p class="hint">Dosya başka bir uygulamada açıksa önce o uygulamadan yedek alın veya uygulamayı kapatın. SQL metni ve diğer uygulamaların farklı tablo yapıları desteklenmez.</p>
    <button class="btn primary" type="submit" id="database-inspect">Dosyayı kontrol et</button></form>
    <div id="database-message" role="status" aria-live="polite"></div><div id="database-preview"></div></section></div>`;
  const form=$('#database-form');let current;
  const message=text=>{if($('#database-form')===form)$('#database-message').textContent=text;};
  $('#database-file').onchange=()=>{$('#database-preview').innerHTML='';message('');};
  try{
    current=await api('/api/database/status');if($('#database-form')!==form)return;
    $('#database-status').innerHTML=`<p class="database-label">${esc(current.label)}</p>${databaseCounts(current.counts)}<p class="hint">Kayıtların tutulduğu çalışma dosyası</p><p class="database-path">${esc(current.path)}</p><p class="hint">Bağlantı uygulama kapatılıp açıldığında korunur. API anahtarları bu dosyaya dahil değildir.</p><a class="btn" href="/api/database/backup">↓ SQLite .db yedeğini indir</a>`;
  }catch(error){if($('#database-form')!==form)return;message(error.message);$('#database-status').textContent='Bağlantı bilgileri alınamadı.';$('#database-inspect').disabled=true;}
  form.onsubmit=async event=>{
    event.preventDefault();if(!current)return;
    const file=$('#database-file').files?.[0];if(!file)return;
    if(!/\.(db|sqlite|sqlite3)$/i.test(file.name)){message('SQLite .db, .sqlite veya .sqlite3 dosyası seçin.');return;}
    if(file.size>current.max_bytes){message('Veritabanı en fazla 100 MB olabilir.');return;}
    const button=$('#database-inspect');button.disabled=true;$('#database-file').disabled=true;$('#database-preview').innerHTML='';message('Dosya bu bilgisayarda kontrol ediliyor…');
    try{
      const response=await fetch('/api/database/inspect',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Database-File-Name':encodeURIComponent(file.name),'X-AHP-Database':current.database_id},body:file});
      const preview=await response.json();if(!response.ok)throw Error(preview.error||preview.detail||'Veritabanı kontrol edilemedi.');
      if($('#database-form')!==form)return;
      message('Dosya uyumlu. Bağlanmadan önce aşağıdaki kayıtları kontrol edin.');
      $('#database-preview').innerHTML=`<section class="database-preview"><h3>${esc(preview.label)}</h3>${databaseCounts(preview.counts)}<p class="hint">Bağlanınca bu dosyanın kayıtları gösterilecek. Önceki bağlantınızın ayrıca yedeği alınacak; önceki çalışma dosyası yerinde kalacak.</p><label class="database-consent"><input type="checkbox" id="database-confirm">Bu veritabanının çalışma kopyasına geçmek istiyorum.</label><button class="btn primary" type="button" id="database-connect" disabled>SQLite veritabanını bağla →</button></section>`;
      $('#database-confirm').onchange=()=>{$('#database-connect').disabled=!$('#database-confirm').checked;};
      $('#database-connect').onclick=async()=>{
        const connect=$('#database-connect');connect.disabled=true;$('#database-confirm').disabled=true;button.disabled=true;$('#database-file').disabled=true;
        message('Önceki kayıtlar yedekleniyor, yeni veritabanına bağlanılıyor…');
        try{
          await api('/api/database/connect',{token:preview.token,database_id:current.database_id,confirmed:true});
          formDirty=false;location.hash='#congresses';location.reload();
        }catch(error){if($('#database-form')!==form)return;message(error.message);connect.disabled=false;$('#database-confirm').disabled=false;button.disabled=false;$('#database-file').disabled=false;}
      };
    }catch(error){message(error.message);}
    finally{if($('#database-form')===form){button.disabled=false;$('#database-file').disabled=false;}}
  };
}
