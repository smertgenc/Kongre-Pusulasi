# Şema sürümü 1 — mevcut tablolara SQLAlchemy eşlemesi

Bu fazda `models`, `congresses`, `evaluations` tablolarının kolonları değiştirilmez.
`app/database.py` mevcut kolonları doğrular, eksik tabloları oluşturur ve SQLite
`PRAGMA user_version=1` ile başlangıç sürümünü kaydeder. JSON kayıtları, UUID'ler,
zamanlar ve puanlar aynen korunur. Daha ileri bir sürüm görülürse eski uygulama
veritabanını açmayı reddeder.

Geri dönüş: sunucuyu durdurun, `data/backups/before-fastapi-*.db` yedeğini ayrı bir
yola kopyalayın ve `python3 legacy_server.py --db /tam/yol/kopya.db` çalıştırın.
Geçişten sonra eklenen kayıtları kaybetmemek için geri dönüşten önce güncel yedek alın.

## Şema sürümü 2 — AI analizi ve inceleme

`ai_analyses` ve `ai_reviews` tabloları eklenir; mevcut tablolar ve kayıtlar değişmez.
Analiz kaydı kaynak kopyaları, alım tarihi, içerik özeti, model/kural/prompt sürümü,
ham AI çıktısı ve doğrulanmış bulguları içerir. İnceleme kaydı bir değerlendirmeye
bağlıdır ve analiz başına tektir. `PRAGMA user_version=2` kullanılır.

Geçiş öncesi yedek: `data/backups/before-ai-v2-20260927-223358.db`.
Eski uygulamaya dönüş için sunucuyu durdurup bu yedeğin ayrı kopyasını kullanın;
v2 veritabanını v1 uygulamaya bağlamayın. v2 sonrasında oluşan AI kayıtları bu eski
yedekte bulunmaz; güncel SQL yedeğini ayrıca koruyun.

Dinamik kriter/kural tabloları gelecekte ayrı sürümlü geçiş gerektirir.
`create_all` mevcut kolonların dönüşümünü yapmaz.

## Şema sürümü 3 — geri alınabilir kongre silme

`congress_deletions(congress_id PRIMARY KEY REFERENCES congresses(id), deleted_at)`
tablosu eklenir. Önceki beş tablonun kolonları ve kayıtları değişmez.
`PRAGMA user_version=3` kullanılır. Silme bir işaret ekler, geri yükleme bu işareti
kaldırır; AI raporları, incelemeler ve değerlendirme geçmişi korunur. Aktif
liste/CSV/senaryo sorguları işaretli kongreleri dışlar. SQL yedeği çöp kutusunu da içerir.

AI politikası `congress-binary-v2` yalnızca yeni analizlere uygulanır; JSON içinde
politika/yöntem sürümü ve kuralların kopyası saklanır. Eski raporlar dönüştürülmez.
Geri dönüşte v3 dosyasını eski uygulamayla açmayın; geçiş öncesi yedeğin ayrı kopyasını
kullanın. Eski sürüm çöp kutusu işaretlerini tanımaz.

## Şema sürümü 4 — geri alınabilir analiz geçmişi

`ai_analysis_deletions(analysis_id PRIMARY KEY REFERENCES ai_analyses(id), deleted_at)`
tablosu eklenir. Önceki tabloların verileri ve JSON kayıtları değiştirilmez.
Listeleme bu işarete göre aktif/silinen geçmişi ayırır. AI incelemesi ve kongre
değerlendirme bağlantıları korunur. Toplu temizleme çalışan analizleri atlar.

Görsel kaynaklar orijinal görüntü, OCR metni ve özetiyle mevcut analiz JSON'unda;
arama kaynakları sorgu, servis, kaynak URL ve okunmuş metinleriyle tutulur.
Jina/Tavily anahtarları veritabanına girmez. Geçiş öncesi yedek:
`data/backups/before-search-images-v4-20261001-215213.db`.
Eski sürüme dönüşte bu dosyanın ayrı kopyasını kullanın; v4 sonrasında eklenen
veriler bu yedekte bulunmaz. Güncel SQL yedeği silinen analizleri de içerir.

## Şema sürümü 5 — uygunluk sınıflandırması

`app/classification_migration.py` eski üç sınıflandırma etiketini Düşük / Orta / Yüksek Uygunluk adlarına dönüştürür. Yalnızca `evaluations.data.result.status`, `ai_analyses.data.analysis.result.status`, `ai_analyses.data.analysis.report.ahp_result.status` ve `ai_reviews.data.saved.result.status` alanları güncellenir. Silinen kayıtlar da kapsanır. Analiz iş durumları, sayısal sonuçlar, tarihler, kimlikler, eşikler, ağırlıklar, notlar ve kaynak kanıtları değişmez. Eksik veri durumu korunur.

Geçiş ve `PRAGMA user_version=5` tek SQLite yazma işlemi içinde uygulanır. Herhangi bir hata bütün etiket değişikliklerini geri alır. Tekrar açılışta yinelenmez; SQL yedeklerinden geri yüklenen eski şemalarda otomatik çalışır. API eşik anahtarları eski istemcilerle uyumluluk için korunur.

Geri dönüş için uygulamayı durdurun ve geçiş öncesi yedeğin ayrı kopyasını eski sürümle açın. v5 dosyasını eski uygulamaya bağlamayın.

## Şema sürümü 6 — araştırma profili ve kongre parmak izi

`user_research_profiles(id, user_id UNIQUE, data, created_at, updated_at)` ve
`conference_fingerprints(conference_id PRIMARY KEY REFERENCES congresses(id),
evaluation_id REFERENCES evaluations(id), source_hash, data, created_at, updated_at)`
tabloları eklenir. Eski tablolar ve değerlendirme JSON'ları değiştirilmez.
`PRAGMA user_version=6` kullanılır; v5 ve daha eski dosyalar ilk açılışta geçer.

Uygulamada oturum/kullanıcı tablosu olmadığı için profil sahibi sunucuda sabit
`local-workspace` kimliğidir. İstemci başka kullanıcı kimliği gönderemez. Bu, mevcut
tek kullanıcılı yerel erişim modelidir; yeni bir çok kullanıcılı kimlik doğrulama
sistemi değildir. Profil değişiklikleri kongre/AI kayıtlarını değiştirmez.

Parmak izleri türetilmiş önbellektir. Kaynak metni, değerlendirme veya normalleştirme
kuralları değiştiğinde yenilenir. Eski bir değerlendirmeyi görüntülemek en yeni
parmak izi önbelleğinin üzerine yazmaz. Silinen kongreler önerilere katılmaz;
AI kaynak/inceleme bağlantıları korunur. SQL yedeği iki yeni tabloyu da içerir.

Konu ve organizasyon bilgileri yeni değerlendirmelerde `metadata.research`
altında saklanır. Eski kayıtlarda bu alanın olmaması desteklenir. AHP ağırlıkları,
puanları, 70/90 varsayılan sınıflandırma eşikleri ve politika sürümleri değişmez.
Eski uygulamaya dönüşte güncel dosyayı kullanmayın; geçiş öncesi yedeğin ayrı
kopyasını kullanın.


## Şema v7 — Kongre logoları

`congress_logos` tablosu kongre kimliğine bağlı güncel PNG görselini, kaynak
adresini, web sitesini, görünürlük durumunu ve güncelleme zamanını saklar.
`PRAGMA user_version=7` kullanılır. İlk açılışta yalnızca eksik tablo oluşturulur;
önceki kongre, değerlendirme, AI analizi, profil ve parmak izi kayıtları değişmez.
Logolar SQL/SQLite yedeğinin parçasıdır; kongreyi çöp kutusuna taşımak görseli
silmez. Logoyu gizleme PNG baytlarını korur ve geri alınabilir.

Önceki uygulamaya dönmek gerekirse yükseltme öncesi yedeği ayrı bir dosyaya
geri yükleyin. Eski uygulama v7 veritabanını açmaz; sürüm numarasını elle
azaltmayın. Geçiş ve bayt düzeyinde veri korunması `tests/test_logos.py` ile
kontrol edilir.
