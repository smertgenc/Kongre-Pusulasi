> Tarihsel geliştirme raporu: burada anılan yerel yedekler, test ekranları ve kaynak ZIP çıktıları GitHub paylaşımına dahil değildir.

# Bilimsel yöntem geliştirmesi — teslim raporu

Tarih: 10 Ekim 2026. Sürüm: **1.11.0**. Kapsam: kullanıcı talimatındaki P0–P4; çalışan uygulama korunarak kontrollü kod uygulaması. Teknik altyapı tamamlandı; gerçek veriyle akademik doğrulama tamamlanmış değildir.

## Güvenli çalışma ve korunan sistem

Önceki oturumun geçici çalışma klasöründeki çalışma kopyası bulunamadı; ana proje hâlâ 1.10.0 idi. Bu nedenle o oturumun sonuçları teslim kanıtı sayılmadı. Güncel kaynak tekrar incelendi, kalıcı `tmp/scientific-v1.11.0/before` kaynak yedeği ve `work` izole kopyası oluşturuldu. `.env` ve operasyonel `data` kopyalanmadı. Bunların 318 dosyalık SHA256 listesi yalnız değişmeme kontrolü için özel çalışma klasöründe tutuldu.

Başlangıç kopyasında Excel seed JSON'u eksik olduğu için ilk test denemesi başarısızdı; eksik test kaynağı kopyalanıp başlangıç tekrar çalıştırıldı: 187 test, 2 isteğe bağlı atlama, kalanlar başarılı. Bu hata uygulamadaki mevcut bir kusur değildi. Geliştirme yalnız izole kopyada, geçici DB'ler ve sahte AI yanıtlarıyla yapıldı; canlı AI/search istekleri gönderilmedi. Son kaynaklar hash kontrollü aktarılır; kalıcı geri alma yedeği `backups/scientific-1.11.0-20261010` içindedir.

`engine.py`, varsayılan hiyerarşi, K1–K10 ağırlıkları, 70/90 eşikleri, operasyonel SQLite şeması 7 ve eski puan kayıtları korunur. Manuel giriş, kaydetme/geçmiş, logosu ve kaynak işleme, AI sağlayıcıları/otomatik geçiş, Tavily/Jina, PDF/CSV, profil, mevcut öneriler, çöp kutusu/geri yükleme ve veritabanı bağlama kaldırılmadı. Yeni araştırma SQLite'ı yalnız kullanıcı açarsa oluşur. Yeni bilimsel puanlama varsayılan değildir.

## Değişen dosyalar ve davranış

|Alan|Dosyalar|Sonuç|
|---|---|---|
|CPCI koruması|`app/congress_policy.py`|Olumlu karar + olumsuz alıntı veya uyuşmayan edisyon artık null/çelişki ve inceleme gerektirir. Yeni legacy politika v3, geçmiş snapshot'lar değişmez.|
|Bilimsel politika|`app/scientific_policy.py`, `app/ai_method.py`, `app/ai_schemas.py`, `app/ai_service.py`, `app/ai_provider.py`|Seçilebilir kanıt politikası; beş durum; sabit ağırlıklarla alt/üst sınır; politika/profil/tarih/nihai insan durum kaydı. Prompt v9, eski parça yanıtları farklı promptla karıştırılmaz. Diğer sağlayıcı adaptör yolları korunur.|
|Rapor ve ekran|`static/ai.js`, `app/pdf_report.py`|Politika seçimi, kanıt/sayı atanmış kapsam ayrımı, puan katkısı, yeni politika JSON'u, kalibrasyon sınırlaması.|
|Dashboard/karşılaştırma|`static/compare.js`, `static/app.js`|Aynı model/context/ölçek/politika/mode/profil/örnek türü/gündeki değerlendirmelerle grup bazlı ortalama ve sıralama; yeni kullanım rehberi açıklaması. Tarih ayrımı muhafazakârdır; farklı günleri birleştirme otomatik yapılmaz.|
|CBC|`app/conjoint.py`|Attribute/level, yasak kombinasyon, seeded seçim setleri, referans kodlama/rank, regularize pooled MNL, yakınsama, fayda/önem, holdout.|
|Araştırma saklama/API|`app/research_store.py`, `app/research_api.py`, `app/main.py`|Varsayılan kapalı ayrı SQLite; izin/onam gereksinimi, takma katılımcı/task bazında yanıtlar, model dondurma.|
|Araştırma UI|`static/research.js`, `static/index.html`, `static/styles.css`|Mevcut panel/tema yapısında ayrı menü, sentetik/demo/gerçek çalışma, seçim, sonuç ve offline deney formu. Araştırma tablo metinleri dar ekranda sarılır; genel breakpointler değiştirilmedi.|
|Hibrit ve deney|`app/research_models.py`, `app/research_metrics.py`, `app/research_experiments.py`|M1–M4 kısıtlı hibrit, metrikler, split/uygunluk kontrolleri, veri seti ve sonuç manifesti.|
|Windows uyumluluğu|`app/research_provenance.py`, `tools/create_research_manifest.py`, `tools/build_windows.py`, `packaging/windows/app.spec`, `desktop/self_test.py`|EXE kaynak `.py` dosyası aramaz; build-time kod manifesti paketlenir. Offline paket testi yeni kaynak/varsayılan kapalı araştırma/CBC tahminini denetler.|
|Geri alma|`tools/restore_scientific.py`|Hash kontrolüyle yalnız değişen kaynak dosyalarını geri alır; kullanıcı verilerine dokunmaz; sonradan düzenlenmiş dosyanın üzerine yazmaz.|
|Belgeler/testler|`docs/CRITERIA_CODEBOOK.md`, `SCIENTIFIC_RESEARCH.md`, `SCIENTIFIC_REPORT_TEMPLATE.md`, yeni `tests/test_scientific*`, `tests/test_conjoint.py`, `tests/test_research*`, README/CHANGELOG/VERSION|Yöntem, kullanım, sınırlar, araştırma planı ve regresyonlar.|

## Önceki denetim sorunlarının durumu

|Kimlik|Durum|Gerekçe ve kalan iş|
|---|---|---|
|AI-001|Çözüldü|Somut ters yönlü CPCI kararı artık olumlu puan alamıyor; doğrulanmış olumsuza da çevrilmiyor. Negatif ifade/yıl testleri var. Genel dil anlama doğruluğu iddiası yok.|
|AHP-001|Kısmen çözüldü|Manuel kişisel koşullar ile kaynak tabanlı AI kriterleri kod kitabında ayrıldı; farklı ölçüm amaçları birleştirilmedi. Ortak bilimsel ölçek için uzman içerik geçerliği gerekiyor.|
|VER-001|Çözüldü|Bilimsel modda K10 dahil eksik veri null; beş durum ve puan aralığı var. Geçmiş legacy varsayımları bilerek korunuyor.|
|DSS-001|Çözüldü|Dashboard ve karşılaştırma aynı uyumluluk imzasını kullanıyor. Karışık yöntem/tarih/örnek kayıtlar ortak sıralanmıyor.|
|CA-001|Araştırma verisi gerekiyor|Gerçek CBC/MNL hesaplaması, seçim kaydı ve teknik doğrulaması var. Gerçek katılımcılardan model eğitilmedi.|
|AHP-002|Araştırma verisi gerekiyor|Ağırlık kaynağı ve 70/90 eşikleri kalibre edilmedi; değiştirilmeden raporlandı. K1+K2 etkisi ve duyarlılık altyapısı görünür.|
|AHP-003|Kısmen çözüldü|Tamamen online için K5 uygulanamaz ayrımı, null ve sabit ağırlıklı sınırlar var. Uygulanamaz kriter için alternatif yeniden ağırlıklandırma politikası bilimsel araştırma gerektiriyor.|
|HIB-001|Kısmen çözüldü|Keyfî karışım yerine AHP kısıtı altında CBC sıralaması gerçekten çalışıyor. Ortak öznitelik etkisi protokolde gerekçelendiriliyor; gerçek veri ile yöntem üstünlüğü kanıtlanmadı.|
|AI-002|Kısmen çözüldü|Alıntı, edisyon, cilt tanımlayıcı, AI çıkarımı ve bağımsız doğrulama ayrıldı. Regex/ad eşleşmesi akademik doğrulama sayılmıyor. Diğer kriterlerin anlamsal doğruluğu ve kaynak kimliğinin bağımsız doğrulaması hâlâ uzman gerektiriyor.|
|REP-001|Kısmen çözüldü|Veri/kod hash, model/prompt/provider/parametre, seed, split, zaman ve sonuç manifesti var. Servisin iç model revizyonu/gerçek token tüketimi her eski AI kaydında mevcut değil; tam canlı LLM tekrarlanabilirliği garanti edilmiyor.|
|REP-002|Kısmen çözüldü|Var olan bağımlılık kilitleri korundu, araştırma motoru standart kütüphane kullanıyor, kaynak ve frozen manifest yolu testli. Native Windows paketi ve farklı platformlarda sayısal tekrar henüz doğrulanmadı.|
|VAL-001|Araştırma verisi gerekiyor|Teknik sentetik/offline test ve metrikler var. Bağımsız uzman/katılımcı verisi, kişi bazlı dış holdout, güç analizi, belirsizlik ve karşılaştırmalı yayın deneyi yok.|

## Test kanıtı

Son genel Python çalıştırması (kaynak geri alma testi dahil): **206 test; 204 başarılı, 2 isteğe bağlı atlama**. Ek AHP çekirdek takımı: **16/16 başarılı**. Toplam **220 başarılı Python testi**, **2 atlanan**; başarısız test yok.

JavaScript: **26/26 başarılı**. Kaynak masaüstü self-test: **28/28 kontrol**, `ok=true`, `version=1.11.0`, `live_ai_verified=false`. Kaynak self-test native Windows EXE doğrulaması değildir.

Atlananlar: macOS Vision native OCR (`RUN_NATIVE_OCR_TEST`) ve opt-in gerçek socket/process desktop entegrasyonu (`RUN_DESKTOP_PROCESS_TEST`). Native Windows WebView2/CLR, OCR EXE ve installer testleri bu Mac ortamında çalıştırılmadı. Gerçek API doğruluğu yerine hata/switch/retry yolları mock ile sınandı.

Öne çıkan yeni doğrulamalar: negatif CPCI kaynak/pozitif AI çelişkisi; eski edisyon/eksik ISBN-DOI; bilinmeyen K10; online K5; bilinen 4/7,2/7,1/7 AHP ağırlıkları/CR=0; hiyerarşi ve hatalı girdi; bilimsel API/PDF/insan incelemesi ve eski snapshot'ın değişmemesi; gruplama; CBC seed/kodlama/rank/yasak kombinasyon/yetersiz veri/çift yanıt; sentetik katsayı geri kazanımı; holdout etiketlerinin eğitim katsayılarını değiştirmemesi; hibrit kısıt/eksik veri/örtüşme; metriklerde bağlar/tanımsızlık/ortak NDCG havuzu; veri sızıntısı/anahtar alanı reddi; ayrı DB/izin/onam; frozen manifest; geri alma.

CBC geliştirme sırasında bir yakınsama eşiği sayısal hassasiyet sorunu görüldü; gradient seçim sayısına normalize edilerek düzeltildi, ilgili takım tekrar geçti. Windows frozen rapor için kaynak dosya erişim sorunu manifestle düzeltildi. Başarısız ara denemeler başarı sayılmadı.

Tarayıcıda ayrı seed DB üzerinde modülü açma, sentetik çalışma oluşturma ve kaydedilmiş MNL sonuçlarını gösterme doğrulandı. Dashboard grup seçimi ve bilimsel politika seçimi de kontrol edildi; tarayıcı JavaScript hata kaydı oluşmadı. 60 sentetik kişi / 1440 seçimle çıkan sonuçlar **örnek teknik çıktı**, saha bulgusu değildir. Ekran görüntüsü `outputs/verification/scientific-conjoint-1.11.0.jpg`.

## Açılış, Windows build ve geri alma

Mac kaynak uygulamasını kapatıp `Baslat.command` ile yeniden açın; eski süreç bellekte eski backend kodunu tutar. Tarayıcıyı yenileyin. Mevcut ana veritabanını silmeyin.

Windows'a yeni `release/AHP-Congress-Analyzer-Windows-Build-Kit-1.11.0.zip` kaynak paketi gönderilir. Windows Python 3.12 x64 build ortamında ZIP açıldıktan sonra `build_windows.bat` çalıştırılır. Mevcut OCR/Inno Setup/WebView2 önkoşulları ve paket smoke/GUI testleri devam eder; ayrıntı `WINDOWS_BUILD.md`. Bu teslim yeni Windows EXE/installer üretildiği anlamına gelmez. 1.10.0 paketleri tarihsel olarak korunur.

Geri alma, kaynak uygulama tamamen kapalıyken proje kökünden:

```text
python3 tools/restore_scientific.py backups/scientific-1.11.0-20261010
python3 tools/restore_scientific.py backups/scientific-1.11.0-20261010 --apply
```

İlk komut yalnız hash kontrolüdür. İkinci komut eski kaynakları döndürür ve bu sürümün kaynaklarını yedekte saklar. `.env`, `data`, kullanıcı kongreleri ve araştırma yan dosyaları değiştirilmez. Sonradan yapılan kaynak düzenlemesi varsa araç durur; elle birleştirme gerekir. Windows kurulu sürüm için önceki doğrulanmış installer ile kaynak geri alma aynı şey değildir; BT dağıtım sürecini uygulayın.

Araştırma SQLite/JSON dosyaları uygulamanın standart DB yedeğine dahil değildir. Yeni araştırma verileri üretildiyse kapanıştan sonra yan dosyaları ayrıca özel konuma yedekleyin. Geri dönülen 1.10.0 kodu bilimsel durum açıklamalarını bilmez; saklı sayısal değerleri yeniden puanlamaz. Araştırma modülünü devre dışı bırakmak için kodu geri almak yerine kendi kapatma düğmesi de kullanılabilir.

## Yayın hazırlığı ve sonraki araştırma

Teknik olarak: AHP doğrulaması, sürümlü belirsizlik politikası, CBC/MNL, bağımsız hibrit hesap, offline deney ve rapor altyapısı hazırdır. **Uygulama bu nedenle otomatik olarak bilimsel açıdan doğrulanmış veya yayına kabul edilebilir sayılmaz.**

Sonraki çalışmalar: uzman grubuyla kriter/attribute içerik geçerliği ve ağırlık gerekçesi; kurum/etik onay ve onam; bilişsel görüşme/pilot CBC; güç ve örneklem/tasarım incelemesi; kongre/kişi bazında bağımsız test verisi; kör uzman etiketi ve uyum; eşiklerin yalnız eğitim/pilot bölümünde kalibrasyonu; heterojenlik/IIA incelemesi, küme bootstrap/güven aralığı; M1–M4 ve eski sezgisel motoru ortak veri protokolünde karşılaştırma; negatif sonuçların raporlanması. Önerilen rapor iskeleti `SCIENTIFIC_REPORT_TEMPLATE.md` içindedir.
