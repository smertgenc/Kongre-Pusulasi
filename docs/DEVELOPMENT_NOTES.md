# Geliştirme notları ve sürüm geçmişi

Bu belge önceki geliştirme ve doğrulama kayıtlarını içerir. Bahsedilen kişisel yedekler, geçici çalışmalar, ekran görüntüleri ve kurulum çıktıları bu kaynak deposuna dahil değildir. Güncel kurulum için [ana README](../README.md) dosyasını kullanın.

# Kongre Pusulası

Türkçe, yerel çalışan AHP kongre değerlendirme uygulaması. Backend FastAPI + Pydantic + SQLAlchemy, veritabanı SQLite'tır. Python 3.12+ kullanın. Arayüz Node/npm gerektirmez. İlk paket kurulumu dışında manuel değerlendirme internet gerektirmez.

## Windows masaüstü / Release 1.9.2

Windows için PyInstaller **onedir**, pywebview/WebView2 ve Inno Setup EXE altyapısı eklendi. AHP iş mantığı ve kayıt yapısı korundu. **1.9.2 düzeltmesi için bu Mac ortamında Windows EXE/installer üretilmedi; yeniden build ve hedef Windows bilgisayarında doğrulama gerekir.** Kaynak hazırlığı, Windows kurulumunun tamamlandığı anlamına gelmez. .NET Framework açıkça yüklenir, ilk hata korunur; build sırasında izole ve çevrimdışı WebView2 açılış testi zorunludur.

- [1.9.2 Windows başlangıç incelemesi ve düzeltme raporu](STARTUP_AUDIT_1.9.2.md)
- [1.9.1 bağlantı testi kök neden ve düzeltme raporu](NETWORK_FIX_1.9.1.md)
- [Mimari ve kararlar](WINDOWS_ARCHITECTURE.md)
- [Windows build, installer ve release üretimi](WINDOWS_BUILD.md)
- [IT deployment, ağ, kullanıcı verisi, backup/restore ve troubleshooting](../IT_DEPLOYMENT_NOTES.md)
- [Windows kabul testleri](WINDOWS_ACCEPTANCE.md)
- [Gerçekleşen doğrulamalar](WINDOWS_VERIFICATION.md)
- [Oluşturulan/değiştirilen dosyalar](WINDOWS_CHANGE_REPORT.md)

BT onaylı OCR paketi bir kez hazırlandıktan sonra Windows build bilgisayarında:

```bat
build_windows.bat --publisher "GERCEK YAYINCI ADI"
```

Build aracı son kullanıcıya değil geliştirici/BT'ye yöneliktir. Son kullanıcı Setup EXE ve uygulama kısayolunu kullanır; Python/pip/terminal gerekmez. Windows uygulama verileri `%LOCALAPPDATA%\AHP Congress Analyzer` altında, anahtarlar Windows Credential Manager'da tutulur. Veritabanı yedeği Dosya menüsünden alınır. Installer/uninstaller kullanıcı verisini silmez. Offline çekirdek çalışır; AI ve web araştırması internet ister. Sertifika/proxy/güvenlik hatalarında kontroller devre dışı bırakılmaz, IT belgesindeki yönergeler izlenir.

Aşağıdaki kurulum ve `.env` anlatımı **kaynak koddan geliştirme sürümü** içindir.

## Geliştirme ortamı — ilk kurulum

Python 3.12 ile proje klasöründe:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

İsteğe bağlı olarak `.env.example` dosyasını `.env` adıyla kopyalayıp port ve veritabanı yolunu ayarlayın. `.env` Git dışında tutulur. Manuel değerlendirme API anahtarı gerektirmez. AI kullanımı için uygulamadaki **AI bağlantısı** ekranından sağlayıcı seçip API anahtarını ve modelini kaydedin; yeniden başlatma gerekmez. Anahtar `.env` dosyasında yalnızca sahibi okuyup yazabilecek izinlerle (0600) tutulur, veritabanına veya tarayıcı depolamasına yazılmaz. Ayarlarda “tanımlı” görünmesi anahtarın geçerli olduğunu doğrulamaz; AI bağlantısı ekranındaki test düğmesi kayıtlı servise küçük bir gerçek API isteği yapar. Servisi/modeli/anahtarı değiştirirseniz önce kaydedin; ardından test edin. Test edilen servis adı sonuçta gösterilir.

## Başlatma

Mac’te **Baslat.command** dosyasına çift tıklayın. Alternatif olarak bu klasörde:

```sh
.venv/bin/python server.py --open
```

Tarayıcı adresi: http://127.0.0.1:8765

Terminali açık bırakın. Durdurmak için Ctrl+C. Port doluysa açık uygulamayı kullanın veya `.venv/bin/python server.py --port 8766 --open` çalıştırın.

Sağlık kontrolü: http://127.0.0.1:8765/api/health

Postman'a aktarılabilen OpenAPI şeması: http://127.0.0.1:8765/openapi.json

## Kullanım

1. İlk açılışta Excel’deki dört örnek kongre yüklenir; gerçek kanıt olarak sunulmaz.
2. Kongre ekle: ad, edisyon, değerlendirme profili ve değerlendireni girin.
3. 10 kriter için 0/1 veya 0–5 / 0–10 puan seçin. Her puan için kaynak/gerekçe girin. Bilinmeyen kriterleri boş bırakın.
4. Sonuç ekranında ağırlık, fayda ve katkıyı inceleyin. Eksik kayıtta kesin puan yerine sınırlar gösterilir.
5. Karşılaştırma ekranında tüm kongreleri görün; istediklerinizi veya tümünü seçerek yan yana inceleyin. Her kongrenin son kaydedilmiş değerlendirmesi kullanılır.
6. Senaryo ekranında geçici ağırlıklar deneyin; kayıtlı puanlar değişmez.
7. AHP modeli ekranında yeni model sürümü oluşturun. CR > 0,10 olan model yayınlanamaz. Geçmiş sonuçlar kendi modeliyle korunur.

“Düşük Uygunluk / Orta Uygunluk / Yüksek Uygunluk” model içi sınıflandırmadır. Manuel değerlendirmede kriter kabul koşullarını kullanıcı tanımlar; AI analizinde sürümlü proje kuralları uygulanır. Gelecekteki kongrenin henüz oluşmamış indeks/katılım/memnuniyet verileri uydurulmamalıdır.

## AI ile analiz

1. **AI bağlantısı** ekranında OpenAI, Gemini, OpenRouter, Groq veya AIMLAPI seçin; o sağlayıcının API anahtarını ve model adını kaydedin. Her sağlayıcının anahtarı ve modeli ayrı saklanır. Boş anahtar, yalnızca seçili sağlayıcının mevcut anahtarını korur. Model alanı `openai/gpt-oss-120b` gibi tam model adlarını kabul eder. API kullanımı seçilen sağlayıcı hesabından ücretlenebilir; modelin JSON Schema ile yapılandırılmış çıktı desteklemesi gerekir.
2. **AI ile analiz** ekranına düz metin, web URL'si, Jina/Tavily web araması, PDF, görsel veya Instagram gönderi metni ekleyin. Dört kaynak birlikte analiz edilebilir. Web girişi verilen adresi ve bu adreste bulunan, aynı kongre yolundaki en fazla dört ilgili sayfayı okur. Alt sayfa adresleri alıntılarla birlikte korunur. Yalnızca başlık/menü okunabiliyorsa AI çağrısı yapılmadan açıklayıcı hata verilir. Instagram'da bağlantı tek başına yeterli değildir, açıklama metni gerekir.
3. Ayrı profil veya analiz ayarı girmeniz gerekmez. İlk Excel AHP modeli otomatik uygulanır. Kriterler, açıklamalar, global ağırlıklar, kabul edilen değerler ve eşikler model sürümüyle birlikte AI isteğine eklenir. Kaynak metinleri, kullanıcı onayıyla seçilen sağlayıcıya gönderilir. Analiz ekranında otomatik geçiş açıkken, kota veya uygun bağlantı hatasında ekranda listelenen diğer kayıtlı AI sağlayıcılarına sırayla geçilir; tamamlanmış parçalar korunur. OpenRouter ve AIMLAPI istekleri kendi altyapıları üzerinden model sağlayıcısına iletir. API anahtarı yoksa sonuç taklit edilmez.
4. AI, 10 kriteri merkezi `app/congress_policy.py` kurallarına göre anlamsal olarak değerlendirir. Birebir alıntılar sunucuda doğrulanır; bu kontrol kaynağın güvenilirliğini veya yorumun doğruluğunu garanti etmez. Kaynak yokken gerçek üretilmez.
5. Her kriterin nihai proje puanı **0/1** olur. K1–K9 kanıtla karşılanamıyorsa 0; K10 memnuniyet için güvenilir olumsuz veri yoksa **proje kuralıyla 1** verilir. Varsayılanlar `basis=project_default`, **Düşük** güven ve açık gerekçe taşır. K10'daki bu 1 memnuniyetin kanıtı değildir. CPCI olumlu ve memnuniyet olumsuz bulguları için yüksek güven gerekir. CPCI ayrıca açık indeks ifadesi ve vaat/başvuru içermeyen kanıt gerektirir.
6. Sonuç tablosu kriter, puan, Yüksek/Orta/Düşük güven ve açılabilir gerekçe/kanıt/kaynak gösterir. **Ham puan X/10**, mevcut ağırlıklarla hesaplanan **AHP puanı /100** ve **kanıt kapsamı** ayrı gösterilir. Varsayılanlar da AHP hesabına katılır; düşük kanıt kapsamı kullanıcıya ayrıca bildirilir. Model ağırlıkları AI tarafından oluşturulmaz/değiştirilmez.
7. “Tüm proje puanlarını seç” ile varsayılanlar dahil AI puanlarını kabul edebilir, herhangi birini gerekçeyle düzeltebilir veya bilinmiyor bırakabilirsiniz. Bilinmiyor seçilirse yalnızca bu kullanıcı incelemesinin nihai puanı aralık olur. İlk AI sonucu ve inceleme kararları ayrı saklanır. Raporun JSON indirme düğmesi **ilk AI sonucunu** indirir; kullanıcı düzeltmeleri raporda ve kongre kaydındadır.
8. Yeni kongre oluşturun veya mevcut kongreye yeni değerlendirme ekleyin. Eski raporlar yeniden puanlanmaz. Karşılaştırmada farklı politikalar birlikte görünür; koşullar farklı olduğunda ortak sıralama yapılmaz.

Merkezi kurallar: K2 akademik kurul/konuşmacı temsili; K3 yalnız kayıt ücreti (ücretsiz veya kanıtlı makul ücret olumlu, ücret/karşılaştırma belirsizse 0); K4 yüz yüze/online/hibrit olumlu; K5 fiziksel konumun erişilebilirliği (tamamen online, adres yoksa uygulanamaz/0); K6 güvenilir önceki etkinlik veya edisyon bilgisi; K7 güncel anlamlı bilimsel içerik; K8 erişilen anlamlı geçmiş verisi; K9 birden fazla ülkenin katılımcı/kurul/konuşmacı/kurumlarla temsili. Güncel resmi kaynaklara öncelik verilir. Çözülemeyen çelişkiler korunur ve varsayılan düşük güvenli puan uygulanır. Yıllar karıştırılmaz; geçmiş yıllar K6/K8/K9'u destekleyebilir.

Her analiz kaynak kopyalarını, erişim tarihlerini, SHA-256 özetlerini, PDF sayfalarını, sağlayıcı/model ve kural sürümünü saklar. Kaynaktaki tarih ile erişim tarihi farklıdır. API `GET /api/ai/analyses/{id}/result`, belirtilen `congress_name`, `congress_year`, `analysis_date`, `scores`, `raw_score`, `max_score`, `general_explanation` yapısını ek referanslarla döndürür. Kaynakta yıl bulunmazsa yıl uydurulmaz. Eski politika raporlarında bu yeni JSON uç noktası bulunmaz.

Sınırlar: toplam 60.000 metin karakteri; PDF başına 4 MB / 30 sayfa; web yanıtı 1 MB, en fazla üç yönlendirme. Yerel/özel IP ve DNS yeniden bağlama koruması bulunur. Taranmış PDF üzerinde OCR, JavaScript ile yüklenen sayfalar, sınırsız web araması ve doğrudan Instagram API erişimi yoktur. Ek kurum/indeks/sosyal medya kaynaklarını kullanıcı ekleyebilir; erişilmeyen kaynak doğrulanmış sayılmaz. Kaynaklar ücretli API'ye onaydan sonra gönderilir. Kapanırken yarım kalan analiz başarısız olarak işaretlenir; geçici servis hatalarında aynı sağlayıcıya en fazla üç bağlantı denemesi yapılır.

Gemini bağlantısı `generateContent` üzerinde `responseMimeType` ve `responseJsonSchema` alanlarını kullanır. API'ye gönderilen şema referansları açılarak sadeleştirilir; uzunluk ve dizi sınırları tam Pydantic şemasıyla sunucuda doğrulanmaya devam eder. Eski MIME alanı ve karmaşık şema canlı API'de HTTP 400 ile reddedildi. Bu hesapta eski `gemini-2.5-flash` modeli de HTTP 404 verdiği için varsayılan, gerçek kongre kaynağıyla doğrulanan `gemini-3.5-flash` oldu. Analiz günü yöntem kaydına eklenir; geçmiş/gelecek tarih ayrımı bu güne göre yapılır. HTTP 404 model erişimi, 429 kota ve 503 hizmet yoğunluğu ayrı, anahtarı içermeyen mesajlarla gösterilir. Geçici servis hataları sınırlı yeniden deneme akışına alınır; ayrıntılar bağlantı dayanıklılığı bölümündedir. Başarısız rapordaki **Kaynaklarla yeniden analiz et** düğmesi önceki kaynakları forma getirir.

Groq isteklerinde AHP kriter açıklamaları bir kez gönderilir ve kaynak kayıtlarının hash/tarih gibi arşiv bilgileri API girdisinden çıkarılır; kongre metinleri, alıntı kimlikleri ve kayıtlı kaynak kopyaları aynen korunur. Bu, sınırlı token kotası olan hesaplarda istek boyutunu azaltır. HTTP 413 / bağlam boyutu hatası, kota hatası ve JSON üretim hatası ayrı mesajlarla gösterilir. `strict: true` ve sunucudaki tam yanıt doğrulaması korunur; geçici servis hatalarında aynı sağlayıcıya en fazla üç bağlantı denemesi yapılır. Bağlam veya çıktı token sınırında kaynak parçası kayıpsız küçültülür. En küçük parça da işlenemezse onaylı yedeğe geçilir; hepsi kullanılamıyorsa ilerleme saklanır ve açıklayıcı hata gösterilir.

## Web araştırması, görseller ve PDF

**AI bağlantısı → Web araştırması** bölümünde Jina AI Search veya Tavily anahtarınızı ayrı ayrı kaydedin. Bu servisler analiz modeli değildir: arama sonuçları seçili OpenAI/Gemini/OpenRouter/Groq/AIMLAPI modeline AHP değerlendirmesi için aktarılır. Kaydedilmiş olması geçerli anahtar anlamına gelmez; **Bağlantıyı test et** küçük bir örnek arama yaparak okunabilir kaynak döndüğünü kontrol eder. Bu işlem servis kotasını kullanabilir. Anahtarlar yanıtlara ve yedek veritabanına dahil edilmez.

Analizde **Web araması** kaynağını seçin, kongre adı ve yılını yazın. Her sorguda en fazla üç kaynak, kaynak başına ilk 12.000 karakter alınır. Tam içerik yoksa arama özeti kullanıldığı açıkça belirtilir. İlgili edisyon, resmi kaynak niteliği ve alıntılar ayrıca kontrol edilmelidir. Sorgu seçili arama servisine, bulunan metinler seçili analiz modeline gönderilir; onay metni iki alıcıyı da gösterir. Jina/Tavily anahtarı olmadan bu kaynak çalıştırılmaz. API: `GET/POST /api/search/settings`, `POST /api/search/test`.

**Görsel** kaynağı PNG, JPEG veya WebP afiş/broşür kabul eder: dosya başına 4 MB, 20 megapiksel, kenar başına 12.000 piksel. Yazılar işletim sistemine uygun yerel OCR ile okunur; AI sağlayıcısına görselin kendisi gönderilmez. Orijinal görsel ve OCR metni yerel analiz kaydında korunur. OCR hataları olabilir; alıntıyı orijinalle karşılaştırın. Windows masaüstü paketinde Türkçe/İngilizce Tesseract 5 birlikte gelir ve internet gerektirmez. macOS geliştirme sürümünde ilk çalıştırmada `swiftc` ile `app/native/vision_ocr.swift` derlenir ve `data/runtime/vision-ocr` olarak önbelleğe alınır; Xcode Command Line Tools gereklidir. Metinsiz fotoğraf veya taranmış PDF dosyası doğrudan görsel analizine çevrilmez; PDF sayfasını ayrı görsel olarak yükleyin.

Raporun **PDF indir** düğmesi, son kaydedilmiş inceleme kararlarını (inceleme yoksa ilk AI sonucunu), ham/AHP puanlarını, 10 kriter katkısını, gerekçeleri ve kaynak künyelerini yerelde PDF oluşturup indirir. Kaydedilmemiş form değişiklikleri PDF'ye dahil edilmez. **Yazdır** normal tarayıcıların yazdır penceresini açar; uygulama içi tarayıcılarda doğrudan PDF indirme kullanılabilir. API: `GET /api/ai/analyses/{id}/pdf`. Türkçe yazı tipleri macOS/Windows'ta Arial, Linux'ta DejaVu Sans üzerinden gömülür.

Resmi API referansları: [Jina Reader / Search](https://github.com/jina-ai/reader), [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Apple Vision OCR](https://developer.apple.com/documentation/vision/vnrecognizetextrequest).

## Analiz geçmişini silme

**AI ile analiz → Analiz geçmişi** bölümünde her analizin **Sil** düğmesi vardır. **Geçmişi temizle** tüm tamamlanmış/başarısız analizleri silinenlere taşır; çalışan analizler korunur. **Silinen analizler → Geri yükle** ile işlem geri alınabilir. Kongreler, kaydedilmiş değerlendirmeler, kaynak kopyaları ve inceleme kanıtları silinmez. Liste en son 100 kaydı gösterir; toplu işlem tüm geçmişe uygulanır. Kalıcı silme yapılmaz.

API: `GET /api/ai/analyses?deleted=true`, `POST /api/ai/analyses/{id}/delete`, `POST /api/ai/analyses/{id}/restore`, `POST /api/ai/analyses/clear` (gövde `{}`). Silinen rapor bağlantıları okunabilir; yeni inceleme için önce geri yüklemek gerekir.

## Kongre silme

Kongre listesindeki **Sil** veya detay ekranındaki **Kongreyi sil** ile kayıt çöp kutusuna taşınır. **Kongreler → Çöp kutusu → Geri yükle**, aynı kongreyi tüm değerlendirme geçmişiyle geri getirir. Aktif listeler, karşılaştırma, senaryo ve CSV silinen kayıtları içermez. AI raporları ve SQL yedeği geçmişi korur. Aynı ad/edisyon yeniden eklenmek istenirse önce geri yükleme önerilir. Silinen kayda değerlendirme eklenemez. Kalıcı temizleme düğmesi yoktur.

API: `GET /api/congresses/trash`, `POST /api/congresses/{id}/delete` (`previous_id`: güncel değerlendirme kimliği), `POST /api/congresses/{id}/restore` (`{}`). Silme sırasında kayıt başka pencerede değiştirilmişse 409 döner. Silme/geri yükleme işlemleri tekrarlanabilir ve tek işlemde kaydedilir.

## SQLite veritabanı bağlama

Sol menüde **Veritabanı** bölümünü açın. Kongre Pusulası’ndan alınan `.db`, `.sqlite` veya `.sqlite3` dosyasını seçin (en fazla 100 MB). **Dosyayı kontrol et** ile kongre, değerlendirme, AI analizi ve model sayılarını görün. Onay kutusunu işaretleyip **SQLite veritabanını bağla** düğmesine basın.

Uygulama dosyanın yerel çalışma kopyasını kullanır; yeni kayıtlar bu kopyaya yazılır. Seçilen kaynak dosya değişmez, önceki veritabanı yerinde kalır ve geçiş öncesi ayrıca yedeklenir. Kayıtlar birleştirilmez. Seçim yeniden açılışta korunur. Devam eden analiz/işlem varsa bitmesini bekleyin. API anahtarları ayrı saklanır ve bağlantı değişiminden etkilenmez.

**SQLite .db yedeğini indir** ile mevcut çalışma veritabanını başka bilgisayara taşıyabilirsiniz. Diğer programların farklı tablo yapıları, SQL metni ve daha yeni uygulama sürümüne ait veritabanları kabul edilmez. Dosya başka bir uygulamada açıkken ham dosyayı kopyalamak yerine o uygulamadan tutarlı yedek alın.

Bağlantı seçimi ana veritabanının yanındaki `kongre.db.connection.json`, çalışma kopyaları `kongre.db.connections/`, geçici önizlemeler `kongre.db.pending/` altında saklanır. Etkin çalışma dosyasının tam yolu arayüzde gösterilir. Bu dosyalar kullanıcı verisi içerir; kaynak/build paketine dahil edilmez.

## Veriler ve yedek

Veriler `data/kongre.db` içinde tutulur. Uygulama kapandığında korunur. Rehber sayfasından SQL yedeği ve aktif kongrelerin değerlendirmelerini içeren CSV alınabilir. Yedekler kaynak notları dahil kişisel verileri içerebilir.

Bir yedeği **yeni veritabanına**, mevcut dosyayı ezmeden geri yüklemek için:

```sh
python3 restore_backup.py /tam/yol/kongre-yedek.sql /tam/yol/yeni-kongre.db
.venv/bin/python server.py --db /tam/yol/yeni-kongre.db --open
```

Yalnızca uygulamanın kendi oluşturduğu, güvendiğiniz yedekleri geri yükleyin.

## Mimari

- `engine.py`: saf Python matris doğrulama, sütun ortalaması ağırlıklandırma, baş özdeğer CR, puanlama ve senaryo fonksiyonları.
- `server.py`: Uvicorn/FastAPI başlatıcısı ve eski Python çağrıları için uyumluluk katmanı.
- `app/main.py`: FastAPI uçları, hata yanıtları ve yerel erişim kontrolleri.
- `app/schemas.py`: Pydantic giriş şemaları; tip, tarih, ölçek ve gerekçe doğrulaması.
- `app/models.py`, `app/database.py`: SQLAlchemy eşlemeleri, oturumlar, yazma işlemleri ve şema sürümü.
- `app/services.py`: Kongre/model/değerlendirme iş mantığı, CSV ve senaryo servisi.
- `app/config.py`, `app/paths.py`: geliştirme/masaüstü yolları, sürüm ve yapılandırma.
- `app/sources.py`: metin, web, arama, PDF, görsel ve Instagram metni çıkarımı; kaynak kopyaları ve boyut/ağ sınırları.
- `app/ai_provider.py`, `app/provider_catalog.py`, `app/ai_schemas.py`: sabit sağlayıcı uçları, sağlayıcıya uygun istek/yanıt dönüşümü ve doğrulanan yapılandırılmış çıktı.
- `app/ai_rules.py`: alıntı doğrulama, çelişki ve eksik veri ayrımı.
- `app/congress_policy.py`: merkezi 10 kriter, sürümlü proje varsayılanları, güven etiketleri, ham puan ve kaynaklı JSON raporu.
- `app/ai_method.py`: değişmeyen Excel ağırlıklarıyla sürümlü AI politikası sözleşmesi.
- `app/ai_service.py`, `app/ai_settings.py`: analiz geçmişi, atomik insan incelemesi ve yerel bağlantı ayarları.
- `legacy_server.py`: Önceki backend; geçiş regresyonu ve geri dönüş referansı, normal kullanım için değil.
- `static/`: responsive Türkçe kullanıcı arayüzü. Haricî CDN/font bağımlılığı yok.
- `test_app.py`: Excel eşleşmesi, 4 sütun hata regresyonu, eksik veri, 1024 kombinasyon, geçmiş, mükerrer kayıt, senaryo ve yedek testleri.
- `tests/test_api.py`: API sözleşmesi, migration, eşzamanlılık ve giriş güvenliği testleri.
- `analiz/`: önceki Excel incelemesi ve referans sonuçları.

Şema v7, önceki araştırma profili ve parmak izi tablolarına kongre logolarının yerel saklama tablosunu ekler. Önceki v5 sınıflandırma geçişi eski yedekler için korunur. Puanlar, eşikler, ağırlıklar, kanıtlar ve silme/geri yükleme tabloları korunur. `PRAGMA user_version=7` kullanılır. Kongreler ve değerlendirmeler fiziksel olarak silinmez. Kaynak kopyaları analizin JSON kaydındadır. Kongre kaydı, değerlendirme ve inceleme tek işlemde kaydedilir. Yeni değerlendirmeler önceki kayıtları ezmez. Şema ve geri dönüş bilgisi `migrations/README.md` içindedir.

Geçiş öncesi veritabanı yedeği `data/backups/before-fastapi-20260927-211638.db` dosyasındadır. Yedek test verisi değil, geçiş öncesi kullanıcı kayıtlarını içerir.

## Doğrulama

```sh
.venv/bin/python -m unittest -v test_app tests.test_api tests.test_ai tests.test_providers tests.test_ahp_flow tests.test_policy tests.test_trash tests.test_extensions tests.test_retry tests.test_batches tests.test_classification tests.test_intelligence tests.test_logos
```

Excel başlangıç sonuçları: A 73.38331160, B 74.81644136, C 94.64248954, D 40.14684691.

AI testleri geçici veritabanı ve sahte test sağlayıcısıyla çalışır; gerçek API anahtarı kullanmaz ve ağ çağrısı yapmaz. Canlı model kalitesi ve hesabın erişimi ayrıca gerçek anahtarla doğrulanmalıdır. Sağlayıcı testleri doğru uç/anahtar seçimini, ayrı ayarları, eski OpenAI ayarlarının uyumluluğunu, yarım/geçersiz yanıtları ve gizli bilgilerin yanıtlara sızmamasını kontrol eder.

Resmi bağlantı referansları: [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs), [Gemini](https://ai.google.dev/gemini-api/docs/generate-content/structured-output), [OpenRouter](https://openrouter.ai/docs/guides/features/structured-outputs), [Groq](https://console.groq.com/docs/structured-outputs), [AIMLAPI](https://docs.aimlapi.com/api-references/text-models-llm/openai/gpt-5-mini).

## Yayın kapsamı

Bu sürüm **yerel tek kullanıcı** uygulamasıdır; Uvicorn yalnızca 127.0.0.1 üzerinde dinler. Genel internete yayınlanmış değildir. İnternete açık çok kullanıcılı kullanım için kimlik doğrulama, kullanıcı bazlı erişim, HTTPS ve barındırma gerekir.

Yeni özellik testleri `tests/test_extensions.py` içindedir. Arama API testleri sabit sözleşme yanıtlarıyla çalışır; canlı hesap doğrulaması için gerçek Jina/Tavily anahtarı gerekir. macOS OCR testini gerçek Apple Vision ile çalıştırmak için `RUN_NATIVE_OCR_TEST=1 .venv/bin/python -m unittest -v tests.test_extensions.NativeOCRTests` kullanın.

## Bağlantı dayanıklılığı (v1.6.1)

Geçici HTTP 408/500/502/503/504 yanıtlarında aynı anahtar, sağlayıcı, model ve kaynak metniyle istek/parça başına en fazla **üç toplam deneme** yapılır. İlk iki bekleme yaklaşık 2 ve 4 saniyedir; çakışmayı azaltmak için küçük rastgele gecikme eklenir. `Retry-After` varsa Groq için 65, diğer sağlayıcılarda 30 saniyeye kadar dikkate alınır; daha uzun bekleme istenirse erken tekrar gönderilmez. HTTP 429, kullanılabilecek yedek varsa beklemeden o sağlayıcıya geçer; yedek yoksa yalnızca geçerli, kısa bir `Retry-After` bulunduğunda aynı sağlayıcıda tekrar edilir. Anahtar, model, istek biçimi, kota ve şema hataları körlemesine yeniden gönderilmez. İsteğin henüz gönderilemediği bağlantı hataları tekrar edilebilir. Yanıt okuma zaman aşımında aynı sağlayıcıya körlemesine tekrar yapılmaz. Otomatik geçiş açıksa sıradaki izin verilen sağlayıcı denenir; ilk isteğin de ücretlenmiş olabileceği dikkate alınmalıdır. Yeniden deneme için toplam süre bütçesi 240 saniyedir; tek isteğin zaman aşımı en fazla 150 saniyedir. Tek sağlayıcı modunda başka servise geçilmez. Otomatik geçiş açıksa yalnız başlarken onaylanan kayıtlı AI servisleri kullanılır; model adları analiz boyunca sabittir. Tüm servislerin kotası dolduğunda sonuç üretilemez; ilerleme saklanır. Dış servisin kesintisiz çalışması garanti edilemez.

Arayüz `POST /api/ai/start` üzerinden analizi başlatıp hemen analiz kimliğini alır; işlem sunucuda arka planda sürer. `GET /api/ai/analyses/{id}/progress` ile küçük durum yanıtları okunur ve sonuç sayfası otomatik güncellenir. Sayfayı değiştirmek çalışan analizi iptal etmez. Uygulama kapanırsa yarıda kalan analiz bir sonraki açılışta başarısız işaretlenir. Eski senkron `POST /api/ai/analyze` API'si korunmuştur.

Başarısız rapordaki **Kayıtlı kaynaklarla tekrar dene** düğmesi kaydedilmiş kaynak kopyalarını kullanır; Jina/Tavily araması, web sayfası indirme veya OCR tekrar çalıştırılmaz. Sağlayıcı/model ve ücretli API kullanımı gönderimden önce gösterilir. `POST /api/ai/analyses/{id}/retry` yeni bir rapor oluşturur; eski rapor değişmez ve yeni rapora bağlanır. Aynı kaynak kaydı için aynı sağlayıcı/modelde çalışan veya başarılı bir yeniden deneme varsa tekrar tıklamak yeni ücretli iş başlatmaz. Bağlantı denemeleri ham API yanıtı ve anahtar kaydedilmeden izlenir.

Yeniden deneme politikası [Google'ın resmi Gemini hata giderme rehberine](https://ai.google.dev/gemini-api/docs/troubleshooting) uygundur. `tests/test_retry.py`, 503 ardından başarı, sınırlı tekrar, `Retry-After`, kalıcı hatalar, kaynakların korunması, çift tıklama ve arka plan durum akışını dış servis kullanmadan test eder. `tests/preview_retry.py` yalnızca geçici veritabanı ve sahte Gemini yanıtlarıyla tarayıcı testi içindir; gerçek analiz sunucusu değildir.

## Groq boyut sınırı ve çoklu katılım (v1.6.2)

Groq için kaynaklar en fazla 5.000 karakterlik gruplar halinde gönderilir. Uzun paragraflar 220 karakter örtüşmeyle bölünür; kaynak/segment kimlikleri ve orijinal arşiv değişmez. Yanıt bütçesi 12.000 yerine 3.000 token, GPT-OSS modellerinde reasoning effort `low` kullanılır. HTTP 413 / context-length reddinde **yalnızca reddedilen parça** küçültülür; 500 karakter alt sınırı ve toplam 64 parça isteği sınırı vardır (her biri en fazla üç geçici bağlantı denemesi). Bu limitler hesap kotasını yükseltmez; en küçük istek bile reddedilirse açık hata gösterilir.

Parçalar sırayla işlenir. Groq'un `x-ratelimit-reset-tokens` süresi (en fazla 65 saniye, başlık yoksa 60 saniye) beklenir; ilerleme raporda görünür. Böylece büyük isteğin ardından hemen kota aşan bir istek dizisi gönderilmez. Tüm parçalar tamamlanmadan puan hesaplanmaz. Her alıntı önce gönderildiği parçada doğrulanır. Kanıt yokluğu olumsuz oy sayılmaz; çelişen kararlar `conflict` olarak korunur ve mevcut proje varsayılanları açıkça uygulanır. Farklı parçalar arasında tamamlayıcı/çelişkili bulgular insan incelemesi gerektirebilir. AHP ağırlıkları ve formül değişmez. Çok parçalı analiz daha fazla API isteği ve zaman kullanabilir. Otomatik geçiş açıksa kalan parçalar onaylı yedek sağlayıcıda sürer; tamamlanan parçalar tekrar gönderilmez. Her sağlayıcının kayıtlı model adı korunur.

Katılım biçimi manuel ekleme, yeniden değerlendirme ve AI inceleme ekranlarında birden fazla onay kutusuyla seçilir. Veritabanındaki mevcut `format` metin alanına `Yüz yüze · Çevrim içi` gibi kaydedilir; şema değişikliği yoktur. Eski serbest metin değerleri de seçili seçenek olarak korunur. Boş seçim `Belirtilmedi` olur.

Referans: [Groq hız/token limitleri ve yanıt başlıkları](https://console.groq.com/docs/rate-limits). `tests/test_batches.py` dış API kullanmadan 413 ardından küçültme, tüm kaynakların korunması, kota bekleme, alıntı doğrulama, çelişki ve yarım sonuçta puan üretmeme kontrollerini kapsar.

## Tüm kongrelerle karşılaştırma (v1.6.3)

Karşılaştırma sayfası model veya profil nedeniyle kayıt gizlemez; tüm aktif kongreleri gösterir. Her kaydın en son değerlendirmesi, kendi model ağırlıkları ve kayıtlı sonuçlarıyla kullanılır. Arama ad, edisyon ve konumda çalışır. Tümünü seç / Görünenleri seç ve Seçimi temizle düğmeleri vardır. Arama, önceden seçilen kongreleri karşılaştırmadan çıkarmaz; arama dışında kalan seçim sayısı gösterilir.

Model, profil, ölçek, politika veya örnek/gerçek kayıt türü farklıysa karşılaştırma tablosu yine açılır; bu farklar belirtilir ve ortak kazanan ilan edilmez. Aynı koşullardaki eksiksiz kayıtlarda en yüksek puan ve eşitlikler gösterilir. Eksik veri için mevcut puan aralığı korunur. Silinen kongreler ve henüz kongreye kaydedilmemiş AI analizleri bu listeye dahil değildir. Kaydı olup değerlendirmesi bulunmayan kongreler görünür, ancak seçilemez.

Doğrulama: `node --test tests/test_compare.cjs` (ek paket gerektirmez).

## Uygunluk sınıflandırması (v1.6.4)

Varsayılan eşikler: puan < 70 **Düşük Uygunluk**, 70 ≤ puan < 90 **Orta Uygunluk**, 90 ≤ puan ≤ 100 **Yüksek Uygunluk**. Özel model eşikleri aynen uygulanır; gösterim yuvarlaması sınıfı değiştirmez. Eksik kriter içeren değerlendirmeler **Eksik veri** durumunda kalır. Matrislerin CR kontrolü ayrı olarak **Tutarlı / Tutarsız** gösterilir.

Hesaplama motoru, anlık önizleme, filtreler, göstergeler, karşılaştırma, senaryo, AI analizi/incelemesi, CSV, JSON ve PDF aynı uygunluk adlarını kullanır. Şema v5 ilk açılışta geçmiş ve silinen kayıtların sonuç alanlarını tek işlemde dönüştürür. Eski yedek geri yüklendiğinde de bu geçiş çalışır; puanlar yeniden hesaplanmaz. Kullanıcı notları ve kaynak alıntıları değiştirilmez. API ve eski model dosyalarıyla uyumluluk için `thresholds.average` Orta Uygunluk alt eşiğini, `thresholds.valid` Yüksek Uygunluk alt eşiğini taşımaya devam eder.

`analiz/hesaplama_sonuclari.json` güncel sınıfları içerir. Orijinal Excel dosyası ile `hucre_formul_denetimi.md` içindeki kaynak formüller tarihsel denetim kanıtıdır; yeniden adlandırılmaz. `audit_ahp.py` kaynak hücrelerini özgün etiketleriyle doğrular, uygulama referans sonuçlarını güncel sınıflarla üretir.

Doğrulama: `tests/test_classification.py` ve `node --test tests/test_classification.cjs tests/test_compare.cjs`.

## Araştırma profili, kongre önerileri ve organizasyonel benzerlik (v1.7.0)

**Araştırma Profilim** ekranından araştırma alanı ve anahtar kelime ekleyin; Enter
veya Ekle ile etiket oluşturabilirsiniz. Kaydet, etkinleştir/devre dışı bırak ve
onaylı profil silme işlemleri vardır. İlk sürüm araştırma alanı + keyword kapsamını
kullanır; bütçe/ülke tercihi gibi ek kişisel ayarlar eklenmemiştir. Profil bu yerel
çalışma alanına aittir; veriler AI sağlayıcılarına gönderilmez.

Kongre detayları ve tamamlanmış AI raporları, AHP sonucundan sonra üç ayrı bölüm
gösterir. Henüz kongreye kaydedilmemiş AI analizleri de desteklenir:

- **Kişisel uyum:** başlık, açıklama, CFP, alan/konu/anahtar kelimeler ve varsa
  kayıtlı kaynak metniyle araştırma terimlerinin eşleşmesi. Tanımlı Türkçe/İngilizce
  eşanlamlar kullanılır; her terimin eşleşen token oranı bulunup ortalanır. 0–100
  ölçeği kabul olasılığı değildir. Profil veya kullanılabilir konu metni yoksa
  skor `null` olur; eksik veri sıfır uyuma çevrilmez.
- **Benzer kongreler:** aynı konudaki aktif kayıtlar arasında yerel TF-IDF/cosine,
  etiket/kategori Jaccard ve karşılaştırılabilir AHP kriter benzerliği kullanılır.
  Örnek Excel kayıtları, silinmiş kayıtlar ve kongrenin kendisi aday değildir.
  Konu benzerliği alt eşiği ayrıca uygulanır; aynı AHP puanı tek başına öneri
  üretmez. En az 3 uygun aday olduğunda en fazla 5 kart gösterilir; daha azsa
  açık yetersiz-aday mesajı çıkar. Yeni web araması yapılmaz.
- **Organizasyonel benzerlik:** normalize organizatör, web hostu, kurumsal e-posta
  domainleri, kurul üyeleri, metin, adres, DOI/yayınevi ve geçmiş kongre adlarından
  hesaplanır. Ortak veri yoksa skor `null`; bilinen fakat farklı özellikler 0'dır.
  Eksik alanların ağırlıkları çıkarılıp kalanlar yeniden oranlanır. Veri kapsamı
  ayrıca görünür; tek domain eşleşmesinin %100 çıkması yeterli organizasyon kanıtı
  sayılmaz. Gmail gibi ortak e-posta hizmetleri domain kanıtı olarak kullanılmaz.
  Benzerlik aynı kongre, yeniden markalama veya kalite konusunda kesin hüküm değildir.

Öneri bileşimi varsayılan olarak %45 benzerlik + %35 AHP + %20 kişisel uyumdur;
tüm bileşenler 0–100 ölçeğindedir. AHP ancak aynı model, bağlam, ölçek ve politika
ile eksiksiz değerlendirilmiş kayıtlar arasında sıralamaya katılır. Diğerlerinde
puan gösterilir ancak fark hesaplanmaz. Önce karşılaştırılabilir ve daha yüksek
AHP puanlı alternatifler, sonra diğer karşılaştırılabilirler, son olarak AHP
karşılaştırması yapılamayanlar sıralanır; her grupta birleşik puan kullanılır.
Organizasyonel benzerlik öneri puanını veya AHP skorunu artırmaz.

**Kongre bilgileri → Konu ve organizasyon bilgileri** alanı manuel giriş ve AI
incelemesine eklenmiştir. İsteğe bağlı açıklama, CFP, akademik alanlar, keywords,
ülke/şehir, ücret, kurul, konuşmacı, yayınevi, DOI ve geçmiş kongre bilgileri
kaydedilebilir. İletişim e-postaları, uluslararası telefon numaraları ve DOI
önekleri mevcut AI kaynak metinlerinden de yerelde çıkarılır. İsim/adres/yayınevi
bilinmiyorsa uydurulmaz. Görsellerin daha önce çıkarılmış OCR metni kullanılır;
yeni OCR veya LLM isteği yapılmaz. Görsel/logo benzerliği bu sürümde yoktur.

Parmak izi deterministik SHA-256 içerir; hash yakınlığı benzerlik hesabı değildir.
Host normalizasyonu `www` ve URL yolunu kaldırır, alt domainleri korur. Farklı alt
domainler aynı organizasyon sayılmaz; tam kayıtlı-domain/PSL çözümlemesi yapılmaz.
Kişisel uyum ve metin benzerliği için `LocalTextSimilarity` ayrı adaptördür;
ileride embedding adaptörü eklenebilir. Bu sürüm bir semantik embedding modeli
kullanmaz. Sonuçlar mevcut açıklama ve kaynakların kalitesine bağlıdır.

Ağırlıklar, alt eşikler, öneri sayısı, metin sınırı ve terim eşleştirmeleri
`app/intelligence_config.json` dosyasındadır. Ağırlık toplamları 1 olmalıdır;
uygunsuz ayarlar uygulama başlarken açıklayıcı hatayla reddedilir. Ayar değişikliğinden
sonra sunucuyu yeniden başlatın. Varsayılan organizasyon benzerliği eşikleri
40 / 70 / 85; öneri benzerliği alt sınırı 35 ve konu benzerliği alt sınırı 20'dir.
Parmak izleri ihtiyaç anında oluşturulup SQLite'ta saklanır; kaynak/ayar değişikliği
önbelleği geçersiz kılar. Kaynak okuma sorguları arşivdeki büyük görsel verilerini
öneri taramasına taşımaz. Yeni özellikler dış servise bağlantı gerektirmez.

Yeni API'ler:

- `GET /api/profile/research`, `POST/PUT /api/profile/research`
- `DELETE /api/profile/research` veya `POST /api/profile/research/delete` (JSON `{}`)
- `GET /api/congresses/{id}/personal-fit`
- `GET /api/congresses/{id}/fingerprint`
- `GET /api/congresses/{id}/fingerprint/similar`
- `GET /api/congresses/{id}/recommendations`
- `GET /api/congresses/{id}/insights` (üç bölüm birlikte)
- `GET /api/ai/analyses/{id}/insights`

Kongre uçları isteğe bağlı `evaluation_id` ile belirli bir geçmiş değerlendirmeyi
kullanır. Profil o anki profilinizdir; AI/AHP raporunun orijinal kaydı değişmez.
PDF/CSV ve AI sonuç JSON'u AHP raporunu korur; canlı kişiselleştirme bu sabit
raporlara eklenmez. Tarayıcı Yazdır görünümü ek bölümleri de içerebilir.

Doğrulama: `tests/test_intelligence.py` (offline birim/API/veri geçişi testleri)
ve `node --test tests/test_intelligence.cjs tests/test_classification.cjs tests/test_compare.cjs`.


## Kongre logoları (v1.7.1)

Kayıtlı web sitesi olan gerçek kongrelerde logo araması arka planda yapılır.
Başlık alanındaki marka görseli önceliklidir; sponsor, indeks ve rastgele kapak
fotoğrafları logo yerine seçilmez. Uygun bir amblem yoksa sitenin simgesi
kullanılabilir; bu durum görsel açıklamasında ve logo düzenleme penceresinde
belirtilir. Hiç görsel bulunamazsa harf simgesi korunur. Excel örnekleri için
web araması yapılmaz.

Kongre detayındaki **Logoyu düzenle** düğmesiyle dosya yüklenebilir, web sitesi
tekrar kontrol edilebilir, logo gizlenebilir veya gizlenen logo geri getirilebilir.
Yeni manuel kayıtta ve AI incelemesinde de logo dosyası seçilebilir. PNG, JPG,
WebP ve ICO desteklenir; sınır 3 MB / 16 megapikseldir. Dosyalar doğrulanır,
metaverileri temizlenerek en fazla 512×512 PNG olarak SQLite içinde saklanır.
Yedekleme ve geri yükleme logoları da kapsar. Şeffaf ve açık renkli logolar,
görselin renkleri değiştirilmeden lacivert zeminde gösterilir.

Aynı kongrenin logosu genel bakış, liste, detay, karşılaştırma, senaryo,
öneriler, organizasyonel eşleşmeler, çöp kutusu, kaydedilmiş AI analiz geçmişi
ve raporunda kullanılır. Kaydedilmiş AI raporunun PDF çıktısı da yerel logoyu
içerir. Logo güncel görsel kimliktir; tarihsel değerlendirme snapshot'ının bir
parçası değildir ve AHP hesaplarına girmez.

Görseller tarayıcıya yalnızca yerel `/api/congresses/{id}/logo` üzerinden
sunulur. Uzak sayfa/görsel alımı genel IP adresleriyle sınırlıdır; her yönlendirme
yeniden doğrulanır, DNS hedefi bağlantıda sabitlenir, süre/boyut sınırları uygulanır.
SVG/HTML dosyaları logo olarak işlenmez. Başarısız otomatik denemeler 24 saat
önbelleğe alınır; yüklenmiş veya gizlenmiş logolar otomatik işlemle ezilmez.
Bağlantı sorunu AHP iş akışını durdurmaz.

API: `POST /api/congresses/{id}/logo/upload` (base64 `content`),
`POST .../logo/discover` (`force`), `POST .../logo/hide`, `POST .../logo/restore`.
`/api/state` yanıtında logo künyeleri `logos` alanındadır; görsel baytları dahil
edilmez. Ön yüzde `static/logos.js`, sunucuda `app/logo_service.py` kullanılır.
900 px ve altında logo detay başlığının üstüne gelecek şekilde dikey yerleşir;
650 px ve altında küçük görsel kutuları daralır. Görseller her boyutta oranı
korunarak yerleştirilir.

Doğrulama: `tests/test_logos.py` ve `node --test tests/test_logos.cjs`;
dosyaların doğrulanması, yerel ağ yönlendirmeleri, önbellek, eşzamanlı yükleme,
gizleme/geri getirme, yedekleme, v6 geçişi, AI geçmişi/PDF ve HTML kaçışları.

## Otomatik AI geçişi (1.10.0)

AI bağlantısı ekranında en az iki farklı sağlayıcının anahtarını kaydedin. Son kaydettiğiniz sağlayıcı önceliklidir. **AI ile analiz** ekranında **Kota dolarsa kayıtlı başka bir AI sağlayıcısıyla otomatik devam et** seçeneği varsayılan açık gelir. Kullanılacak sıra, kaynak aktarım onayının yanında gösterilir. İsterseniz yalnız bir sağlayıcıyı kullanmak için kapatabilirsiniz. Jina/Tavily arama servisleridir; AI yedeği listesine dahil olmazlar.

Kota/kredi sorunu veya sınırlı bağlantı denemelerinden sonra uygun sağlayıcı hatası oluştuğunda sıradaki izin verilen servis denenir. Tamamlanan kaynak parçaları SQLite içinde tutulur; yarım kalan parça yeni serviste yeniden değerlendirilir. Bozuk veya kesilmiş JSON yanıtı puanlanmaz. Tüm parçalar tamamlandığında mevcut alıntı doğrulaması, proje kuralları ve AHP hesabı uygulanır. Rapordaki **AI çalışma kaydı**, başarısız servisleri ve sonuca katkı veren sağlayıcı/model/parça sayılarını gösterir; PDF de bu bilgiyi içerir.

Tüm servisler kullanılamıyorsa ya da uygulama kapanırsa kayıtlı ilerleme kaybolmaz. **Kayıtlı kaynaklarla tekrar dene**, aynı kaynak/yöntem/prompt sürümünde tamamlanmış parçaları yeniden göndermeden kalanlarla devam eder. Web araması, dosya okuma ve OCR yinelenmez. Eski sürümde ilerleme kaydı olmayan analizlerde tüm kayıtlı kaynaklar tekrar analiz edilir. Her API isteği ücret veya kota kullanabilir; sınırsız deneme döngüsü yoktur.

Teknik kapsam, sınırlar ve testler: [AI otomatik geçiş notları](AI_FAILOVER_1.10.0.md). Windows'a dağıtım için 1.10.0 kaynağından yeni build gerekir; bu macOS ortamında Windows EXE üretilmemiştir.


## 1.11.0 — İsteğe bağlı bilimsel araştırma

AI sayfasında **Bilimsel kanıt politikası**, menüde **Conjoint tercih analizi** eklendi. Araştırma araçları varsayılan olarak kapalıdır. Mevcut kayıtlar yeniden puanlanmaz, üretim önerileri korunur.

- [Kriter kod kitabı](CRITERIA_CODEBOOK.md)
- [Araştırma yöntemi, kullanım ve sınırlamalar](SCIENTIFIC_RESEARCH.md)
- [Değişiklik, test ve geri alma raporu](SCIENTIFIC_CHANGE_REPORT_1.11.0.md)
- [Bilimsel rapor şablonu](SCIENTIFIC_REPORT_TEMPLATE.md)
