# Bilimsel deney raporu şablonu

**Durum:** [Sentetik teknik test / pilot / bağımsız gerçek veri değerlendirmesi]. Sentetik sonucu bilimsel bulgu olarak sunmayın.

1. Araştırma sorusu, önceden tanımlı hipotezler, kayıt/protokol kimliği ve tarih.
2. Kurum/etik izin referansı, katılımcı onam sürümü, veri erişim/saklama/çekilme planı. Kişisel tanımlayıcı eklemeyin.
3. Kongre evreni, edisyon ve zaman aralığı; içerme/dışlama ölçütleri; kaynakların hash, tarih ve bağımsız doğrulaması.
4. Kriter kod kitabı ve ölçüm amacı; manuel/AI profil farkları; bilinmiyor/uygulanamaz/çelişki kuralları. Uzmanların kör değerlendirmesi ve uyuşmazlık çözümü.
5. AHP hiyerarşisi/matrisler, ağırlık kaynağı, CR değerleri; K1+K2 etkisi; sınıflandırma ve hibrit kabul eşiklerinin gerekçesi.
6. CBC attribute/level geliştirme, yasak kombinasyonlar, pilot ve deney tasarımı; kodlama/referanslar; katılımcı ve görev sayısı; split ve rank.
7. MNL olasılığı, ceza ve yakınsama ölçütü, katsayılar/önemler, holdout accuracy/log-loss. IIA/heterojenlik ve belirsizlik analizi sınırlamaları.
8. M1–M4 tanımı; çift sayım/örtüşme gerekçesi; eksik adayların dışlanma sayısı. Eski sezgisel motor ayrı karşılaştırma kolu olarak değerlendirilmişse ayrıca protokol ve sonucu.
9. Veri seti sürümü, bağımsız test grubu, metriklerin paydaları ve null değerleri; precision/recall/F1, NDCG@K, sıra uyumu, uzman uyumu. Örneklem belirsizliği ve genelleme sınırları.
10. Deney JSON manifesti: kod ve veri hash, model/prompt/LLM sürümleri, tarih, seed, parametreler. Gerçek API çağrısı yapıldıysa yöntem ve maliyetleri ayrıca raporlayın; API anahtarlarını eklemeyin.
11. Ağırlık/eşik/eksik veri duyarlılığı; bağımsız doğrulama; başarısız veya negatif sonuçlar. Sonuçların kanıtı aşan iddiaları olmamalı.

Uygulamanın çevrimdışı deney JSON'u bu şablonun teknik girdilerini sağlar; eksik etik onay, uzman görüşü, gerçek örneklem veya bilimsel bulguyu üretmez.
