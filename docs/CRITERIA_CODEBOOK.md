# Kriter kod kitabı · 1.11.0

Bu belge, farklı ölçüm amaçlarını eşit saymadan manuel ve AI değerlendirmelerini açıklar. Mevcut ağırlıklar/eşikler değiştirilmedi. İkili ölçüm gerçek kalitenin tam ölçüsü değildir; uzman operasyonelleştirmesi ve içerik geçerliği gerektirir.

|Kod|Manuel / kişisel koşul profili|AI / kongre kaynak profili|Tercih edilen kanıt ve bilimsel karar kuralı|
|---|---|---|---|
|K1 CPCI|İlgili yılın bildiri cildi indeksli mi?|Aynı kongre, edisyon ve yayın cildi|İndeks kaydı, ISBN/DOI, açık gerçekleşmiş indeksleme; başvuru/vaat yeterli değil. Ad/yıl/cilt tanımlayıcısı eksikse bilinmiyor; ters yön/yanlış yıl çelişkili.|
|K2 Temsiliyet|Kullanıcının kurul/uzmanlık eşiği|Akademik kurul/konuşmacı varlığı|Resmi kurul ve kurum kayıtları; kişisel temsil eşiği ile sadece akademik varlık aynı değişken değildir.|
|K3 Maliyet|Ulaşım/otel dahil kişisel toplam bütçe|Yalnız kayıt ücretinin makullüğü|Tarihli ücret kategorileri, para birimi ve gerekçeli karşılaştırma; karşılaştırma kanıtı yoksa bilinmiyor. Piyasa ortalaması uydurulmaz.|
|K4 Format|Kişisel katılım ihtiyacını karşılar mı?|Gerçekleştirilebilir yüz yüze/online/hibrit format|Resmi program/duyuru. Format varlığı, kullanıcının format tercihi değildir.|
|K5 Konum|Kişisel erişim gereksinimi|Fiziksel yerin erişilebilirliği|Doğrulanabilir adres/ulaşım bilgisi. Bilimsel politikada açıkça tamamen online ise uygulanamaz. Sadece yer eksikliği online kanıtı değildir.|
|K6 Süreklilik|Belirtilen geçmiş dönem eşiği|En az bir önceki gerçekleşmiş dönem|Aynı kongrenin eski programı, edisyonu ve tarihleri.|
|K7 Özgünlük|Uzmanın gerekçeli özgünlük hükmü|Tema/programın anlamsal yenilik çıkarımı|Somut çağrı/oturum/program. AI yorumu bağımsız alan uzmanı hükmüne eşit değildir.|
|K8 Şeffaflık|Geçmiş program/kurul/bildirilere erişim|Aynı kongrenin erişilmiş anlamlı geçmiş kayıtları|Açılmış arşiv/program/bildiri kitabı; sadece bağlantı bulunması kanıt değildir.|
|K9 Uluslararası kapsam|Belirtilmiş fiilî katılım eşiği|Birden fazla ülkeden doğrulanabilir temsil|Ülke/kurum/katılımcı bilgileri ve dönem. “International” adı veya davet yeterli değil.|
|K10 Memnuniyet|Örneklem/dönem belli sonuçların kullanıcı eşiği|Kaynağı belli memnuniyet/olumsuz deneyim bulgusu|Örneklemli anket veya güvenilir doğrulanabilir sonuç. Veri yokluğu memnuniyet sayılmaz.|

## Politika sürümleri

- Eski `congress-binary-v2` kayıtları kendi saklanmış değerleriyle açılır; yeniden hesaplanmaz.
- Yeni varsayılan `congress-binary-v3` (legacy): K1–K9 kanıt yoksa 0, K10 kanıt yoksa 1 proje varsayımı korunur. Açık CPCI yön/edisyon çelişkisi artık null ve insan incelemesi gerektirir. Gelecek vaatleri olumlu kabul edilmez.
- İsteğe bağlı `congress-evidence-v1`, profil `congress-source-evidence-v1`: desteklenmiş olumlu=1, desteklenmiş olumsuz=0; unknown, not_applicable ve conflict=null. Bu durumlar birbirinden ayrı saklanır.
- Null kriterlerin sabit ağırlıkları atılmaz ve diğer kriterlere dağıtılmaz. Mevcut motor, eksik kriter 0 olsaydı alt sınırı, 1 olsaydı üst sınırı verir. Uygulanamaz durumunda üst sınır bir katılım olasılığı değildir; koşullu matematiksel sınırdır. Tam puan/sınıf üretilmez. Bu tercihin yöntemsel alternatifi ayrı araştırma gerektirir.
- Kaynak alıntısının eşleşmesi ve ad/yıl/ISBN/DOI kontrolü muhafazakâr otomatik korumalardır. Bağımsız Clarivate doğrulaması veya anlamsal doğruluk garantisi değildir. İki farklı konuya ilişkin cümleler ya da yanlış kaynak kimliği uzman incelemesi gerektirir. Diğer kriterlerde mevcut çoklu kaynak çelişki kontrolü korunur; genel bir anlamsal çelişki çözücüsü geliştirilmiş sayılmaz.

## Kapsam ve güven

`completeness`: sayı/varsayım sayısından bağımsız, kanıtlı kriter adedi / 10.
`evidence_coverage`: kanıtlı kriterlerin global ağırlık toplamı.
`assigned_coverage` (motorun `result.coverage` alanı): sayı atanmış kriterlerin ağırlık toplamı; legacy varsayımları içerebilir.
İncelenmiş kayıttaki `completeness`, insanın sayı atadığı kriter oranıdır; ilk AI kanıt oranı ayrıca `evidence_completeness` olarak saklanır.

Bilimsel politikada birleşik AI güven yüzdesi gösterilmez. Ham model güveni denetim kaydında korunur fakat kalibre edilmiş doğruluk olasılığı değildir. Rapor, ilk kaynak alıntısını, AI açıklamasını, politika gerekçesini, kontrol bayraklarını ve ağırlıklı puan katkısını ayırır. İnsan düzeltmeleri ayrıca sürümlü kayıt oluşturur.

Varsayılan modelde K1+K2 ağırlığı %59,853153'tür. İkisi de 0→1 değişirse diğerleri sabitken toplam 59,853153 puan değişir. Bu, yüksek önem atamasıdır; kendiliğinden bilimsel gerekçe değildir. Ağırlıklar uzman grubuyla, 70/90 eşikleri bağımsız referans etiketleriyle doğrulanmalıdır.
