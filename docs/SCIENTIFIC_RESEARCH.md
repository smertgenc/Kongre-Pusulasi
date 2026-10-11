# Bilimsel araştırma kullanımı · 1.11.0

## Açma, kapatma ve mevcut uygulama

AI ile analiz sayfasında **Puanlama politikası → Bilimsel kanıt politikası** seçilebilir. Varsayılan mevcut proje politikasıdır. Her kayıt yöntem/politika sürümünü saklar. Geçmiş puanlara toplu dönüşüm uygulanmaz.

Menüde **Tercih analizi → Tercih analizini aç** ile bağımsız araştırma bölümü etkinleştirilir. Başlangıçta kapalıdır. **Bu bölümü kapat** verileri silmez; araştırma API'lerini kapatır. Manuel kayıtlar, mevcut AI adaptörleri, profil ve sezgisel öneriler normal çalışır.

Önce **Örnek sonuçları gör** seçeneğini seçip **Örnek analizi başlat** düğmesine basın; çalışma ve sonuç otomatik hazırlanır. Sonuçlar sadece algoritma denemesidir. **Deneme** türünde seçimleri kendiniz girebilirsiniz; gerçek katılımcı araştırması olarak yorumlamayın. İlk model tahmininden sonra yanıtlar dondurulur; yeni veri için yeni çalışma gerekir.

## CBC yöntemi ve sınırları

Varsayılan örnek öznitelikler ücret (3 düzey), format (2), alan ilgisi (2), etkileşimdir (2). Bu liste bilimsel nihai ölçek değildir. Konum, yayın olanakları ve organizasyon geçmişi; bağımlılık, yük, içerik geçerliği ve AHP ile örtüşme incelendikten sonra eklenebilir. Formun ayrıntılarında özel `[{"id":"fee","label":"Ücret","levels":["Düşük","Yüksek"]}, ...]` listesi girilebilir. En az 2, en fazla 6 öznitelik; 2–4 düzey desteklenir. Yasak kombinasyon örneği: `[{"fee":"Yüksek","format":"Çevrim içi"}]`.

Seed ile rastgele benzersiz seçim setleri oluşturulur; her görevde 2/3 alternatif, 12–80 görev vardır. Görevlerin son yaklaşık %20'si tasarım oluşturulurken holdout olarak ayrılır. Alternatif sırası rastgeleleşir. Tasarım D-optimal veya dengeli olarak sunulmaz. Araştırma öncesi gerçekçilik ve katılımcı yükü pilot çalışmayla değerlendirilmelidir.

İlk düzey referans olarak sıfıra sabitlenir; ortak sabit/alternatife özgü sabit eklenmez. Her görev içindeki kodlanmış farklar üzerinde rank kontrolü yapılır. Fayda `V_ij = x_ij β`, seçim olasılığı `P_ij = exp(V_ij)/Σ_j exp(V_ij)` olur. Tahmin, eğitim seçim setleri üzerindeki negatif log-olabilirlik toplamı + `0,1 × ||β||²/2` minimizasyonudur. Newton/Hessian ve geri adımlı çizgi araması kullanılır; normalize gradient <1e-8 yakınsama ölçütüdür. Başarısız yakınsama sonuç yayınlamaz. Ek istatistik kütüphanesi kurulmaz.

Temel yöntem: [Train, Discrete Choice Methods with Simulation, bölüm 3](https://eml.berkeley.edu/books/choice2nd/Ch03_p34-75.pdf). Logit olasılıkları göreli fayda farklarını kullanır; ölçek ortak hata dağılımıyla sabitlenir. IIA ve bağımsız hata varsayımları vardır. Buradaki ridge cezası uygulamanın açıkça kaydedilen düzenlileştirme tercihidir; temel modelin cezasız maksimum olabilirliğiyle aynı tahmin olduğu iddia edilmez.

Göreli önem = öznitelik düzeyleri fayda aralığı / bütün aralıkların toplamı. Düzey aralıklarına bağlıdır; evrensel önem veya AHP ağırlığı değildir. Tüm aralıklar sıfırsa önem tanımsızdır. Model pooled MNL'dir; kişiye özel katsayı tahmini, mixed logit, standart hata/güven aralığı veya katsayı anlamlılığı yoktur. Katılımcı kodu korunur ancak kişi heterojenliği modellenmez.

Teknik tahmin alt sınırı max(20, 5×katsayı sayısı) eğitim ve 5 holdout seçimidir. Bu **araştırma örneklem büyüklüğü önerisi değildir**. Holdout choice accuracy ve log-loss yalnız önceden ayrılan görevlerden hesaplanır. Aynı katılımcılar hem eğitim hem holdout görevlerini cevaplayabilir; yeni katılımcıya genelleme testi sayılmaz. Pilot güç/tasarım çalışması, kişi bazlı dış doğrulama ve küme bootstrap ileriki araştırma gereksinimleridir.

## Gerçek katılımcı çalışması

`research` türü için kurum/etik izin referansı, onam sürümü/metni, veri yönetimi planı referansı ve izin alındığı beyanı zorunludur. Her seçimde güncel onam onaylanır. Yazılım izin belgesinin gerçekliğini denetlemez; sorumluluk araştırma yürütücüsündedir. Bu geliştirmede gerçek katılımcı verisi toplanmadı.

Yalnız takma katılımcı/uzman kodları kullanın. İsim/iletişim/anahtar/token yazmayın. Saklama süresi, erişim yetkisi, çekilme/silme süreci ve kimlik eşleme listesi kurumun veri yönetiminde belirlenmelidir. Bu yerel teknik prototip çok kullanıcılı anket sunucusu veya uçtan uca şifreli araştırma platformu değildir; internetten yayına açmayın.

## Hibrit araştırma modelleri

- M1: Uzman kriterlerinden mevcut AHP puanı.
- M2: Öğrenilmiş CBC faydası/seçim olasılığı sıralaması.
- M3: Uzman AHP puanı ≥ protokolde belirlenen τ olan tam adaylar içinde CBC faydası sıralaması.
- M4: M3 ile aynı CBC modeli/özellikleri ve τ, fakat AHP girdileri arşivlenmiş AI kriter değerleridir.

Bu **kısıtlı tercih modeli** toplamsal skor birleştirmez; keyfî bir alfa kullanmaz. AHP kabul kısıtı, CBC tercih sıralamasıdır. Ortak değişkenler iki rolü de etkileyebilir: örtüşme ortadan kalkmış sayılmaz. Protokol gerekçesi ve örtüşmenin değerlendirildiği beyanı zorunludur. Eşik veri görülmeden belirlenmeli, test sonuçlarına bakarak ayarlanmamalıdır. Eşit faydalarda kimlik sırası yalnız deterministik görüntüleme içindir.

Eksik AHP verisi M3/M4'e uygunluk kararı üretmez. Seçili adaylar için raporlanan CBC olasılıkları bütün aday havuzuna göredir; elenme sonrasında yeniden normalize edilmez. Sıralama yalnız faydaya bağlıdır. CBC modeli yoksa deney yalnız M1 çalıştırır ve `fallback=existing_heuristic` bildirir. Bu alan üretim motorunu çağırmaz/değiştirmez; mevcut uygulama zaten eski öneri motoruyla devam eder. %45/%35/%20 sezgisel yöntem Conjoint veya M3 olarak yeniden adlandırılmadı. Bu deney veri setinde metin/profil olmadığından onun karşılaştırma metriği henüz hesaplanmaz.

## Veri seti ve deney raporu

Araştırma ekranının altındaki **Araştırmacılar için: yöntemleri karşılaştır** alanındaki form `/api/research/dataset-schema` ile tanımlı JSON veri setini alır. `version`, `origin` (demo/synthetic/research), `ahp_model_id`, `records` gerekir. Her kayıtta kongre/edisyon/tarih/profil/politika/bağlam, train/test, K1–K10 uzman ve AI değerleri, CBC düzeyleri, relevance, karar gerekçesi ve AI sağlayıcı/model/prompt sürümü bulunur. Kaynak URL/hash/erişim zamanı ve takma uzman etiketleri desteklenir. Eksik durum alanları ayrıca unknown/not_applicable/conflict saklar. AI parametreleri bilinmiyorsa null bırakın; yeniden üretilebilirliği olduğundan fazla göstermeyin.

Aynı kongre serisi eğitim ve teste birlikte konulamaz. En az 2 test kaydı ve aynı karşılaştırma koşulları gerekir. CBC modeli ile veri setinin origin alanı eşleşmelidir. Gerçek veri deneyi izinli bir araştırma çalışmasına bağlanır. Operasyonel kongre kayıtları otomatik içeri aktarılmaz. Formda en fazla 100 kayıt / 200 KB istek sınırı vardır. Deney **canlı API isteği yapmaz**, eldeki AI etiketlerini değerlendirir.

Metrikler: AHP grup CR; AI ikili kriter precision/recall/F1/macro-F1 ve tahmin kapsamı; tam uzman-AI puan çiftlerinde MAE, Kendall tau-b ve Spearman; uzman çiftlerinde Cohen kappa; aynı aday havuzunun ideal sıralamasıyla M1–M4 NDCG@K; CBC'nin saklanmış holdout accuracy/log-loss değerleri. Bilinmeyen altın etiketler değerlendirmeden çıkarılır; AI çekimserliği pozitif recall'da kaçırma sayılır, kapsam ayrıca belirtilir. Tanımsız ölçüler null olur. NDCG için relevance ve uzman etiketlerinin bağımsızlığı araştırmacı tarafından belgelenmelidir.

Her rapor tam veri seti, sonuç/aday gerekçeleri, AHP ve CBC model kopyaları, seed, tarih, Python/platform, kod/requirements SHA256, train/test kimlikleri, prompt/LLM bilgileri ve protokol parametrelerini içerir. İlk test kongresi için K1 ±5 yüzde puan ve alternatif 60/80 eşiklerinin etkisi, eski modeli değiştirmeden ayrıca hesaplanır. Genel ağırlık duyarlılığı mevcut Senaryo analizi ekranında da çalışır. JSON raporu formdan indirilir; kaynak kod sürümü sabitlendiğinde yeniden çalıştırılabilir. LLM sağlayıcısının görünmeyen model revizyonu veya platformlar arası son basamak farkları garanti edilmez.

## Saklama, taşıma ve yedekleme

Araştırma yan dosyası aktif operasyonel SQLite'ın yanındadır: örneğin `kongre.db.research.sqlite3`. Deneyler `kongre.db.research.runs/` klasöründedir. Program Files altına yazılmaz. Modül kapalı ve dosya yokken okuma onu oluşturmaz. Standart uygulama SQLite yedeği yalnız operasyonel kaydı içerir; araştırma yan dosyaları **dahil değildir**.

Araştırma dosyalarını taşımak/yedeklemek için uygulamayı kapatın, yan SQLite ve runs klasörünü özel güvenli konuma birlikte kopyalayın. Uygulamanın Veritabanı bağlama ekranı yalnız operasyonel DB'yi taşır; araştırma dosyasını otomatik içeri almaz. Yeni aktif DB için araştırma modülü ayrı başlar. SQL şeması 7 ve eski tablo yapısı değişmedi.

## Yeniden üretilebilir doğrulama

Kaynak paketini özel bir test klasörüne çıkarın; üretim `.env` ve `data` dosyalarını kopyalamayın. Mevcut kilitli requirements kullanılır.

```text
python -m unittest discover -s tests
python -m unittest test_app
node --test tests/*.cjs
```

Windows PowerShell'de JavaScript testlerini dosya listesiyle çalıştırabilirsiniz: `node --test (Get-ChildItem tests/test*.cjs).FullName`. Testler geçici DB ve sahte sağlayıcı yanıtları kullanır. Windows EXE için `build_windows.bat` çalıştırılmalı; bu Mac geliştirmesi native EXE/installer kabulünü doğrulamaz.
