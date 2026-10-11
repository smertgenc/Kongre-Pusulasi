# Değişiklik günlüğü

## Arayüz iyileştirmesi — 10 Ekim 2026

- Tercih analizi sade açıklamalar, üç başlangıç yolu ve tek düğmeyle örnek sonuç akışıyla düzenlendi.
- İleri araştırma/JSON ayarları açılır alanlara taşındı; sonuçlarda açıklamalı etki grafiği, seçim ekranında kongre kartları ve soru ilerlemesi eklendi.
- Hesaplama motoru/API/veritabanı değişmedi. Kayıtlı çalışmalar korunur.

## 1.11.0 — 10 Ekim 2026

- CPCI yön/edisyon çelişkileri puansız uzman incelemesine ayrılır; politika v3.
- İsteğe bağlı bilimsel kanıt politikası: eksik/uygulanamaz/çelişkili durumlar, sabit ağırlıklarla puan aralığı; eski kayıtlar korunur.
- Dashboard karşılaştırılabilir grup seçimi; politika/profil/yöntem/tarih/örnek kayıt ayrımı.
- Varsayılan kapalı CBC/MNL araştırma modülü, ayrı SQLite, onam ve izin kayıtları, sentetik teknik deneme ve görev holdout ölçümleri.
- Deneysel kısıtlı AHP–CBC M1–M4 modelleri; offline veri şeması, metrikler, hassas olmayan çalıştırma manifesti ve JSON raporu.
- Üretim AHP çekirdeği, şema 7, ağırlıklar/eşikler, sezgisel öneriler ve geçmiş puanlar değiştirilmedi.
- Teknik doğrulama bilimsel yayın kabulü değildir; gerçek katılımcı/uzman doğrulaması ve hedef Windows paket testi gerekir. Ayrıntılar: docs/SCIENTIFIC_CHANGE_REPORT_1.11.0.md.

## 1.10.0 — 10 Ekim 2026

- Analizde kota/kredi sınırı ve uygun servis hatalarında, açıkça onaylanan kayıtlı AI sağlayıcılarına sıralı otomatik geçiş.
- Kaynak parçaları için kalıcı ilerleme kaydı: sağlayıcı değişiminde ve tekrar denemede tamamlanan parçalar korunur.
- Bağlam/çıktı token sınırında kayıpsız parçalama; eksik JSON veya yarım analizden puan üretilmez.
- Arayüzde geçiş seçeneği, alıcı sırası, sağlayıcı katkıları ve hata geçmişi; PDF'de sağlayıcı bilgileri.
- Anahtar/model listesi iş başında sabitlenir, API anahtarları rapor/veritabanına yazılmaz. Eski istemciler yedek listesi belirtmezse başka servise geçilmez.
- Paket içi çevrimdışı self-test'e gerçek adaptörlerle sahte 429 → yedek sağlayıcı kontrolü eklendi. Windows installer hedef Windows ortamında yeniden üretilmelidir.

## 1.9.2 — Windows başlangıcı ve tanılama (8 Ekim 2026)

- Kullanıcının logunda pywebview'in ilk CLR yükleme hatasından sonra CoreCLR denemesine geçtiği doğrulandı. Üç temel DLL kurulumda mevcut; ilk .NET Framework hatasının alt nedeni eski logda bulunmuyor. Hata API/proxy aşamasında değil, masaüstü UI runtime yüklemesinde.
- Installer'ın istediği .NET Framework açıkça seçilir; ilk yükleme hatası başka runtime denemesiyle gizlenmez. Önkoşullar ve paket DLL yolları denetlenir.
- Import/klasör/DB/UI başlangıç aşamaları ve güvenli cause/traceback/Windows hata kodları kaydedilir. Mesajda gerçek veri ve log yolu gösterilir; keyfi hata metinleri, anahtarlar ve istek içerikleri loglanmaz.
- Hatalı geliştirme portu ayarı masaüstü açılışını engellemez. Otomatik UI testi açık uygulama veya backend kapanışında modal pencere beklemez.
- Credential Manager yerel açılış sırasında yüklenmez. Başlangıç JSON'u UTF-8 okunur; kaynak dosyaları ve sertifika deposu paket testine dahil edilir.
- Frozen EXE, ayrı geçici kullanıcı klasöründe API anahtarsız ve offline WebView2 açılış testini geçmeden installer oluşturulmaz. Build etkileşimli Windows masaüstü oturumu gerektirir.
- 187 Python testi, 21 JavaScript testi ve 23 kaynak self-test kontrolü geçti. Mac'te izole offline dashboard açıldı. Yeni Windows EXE/installer ve hedef VM sonucu henüz doğrulanmadı; bu sürümün VM çökmesini kesin çözdüğü iddia edilmez.
- AHP hesabı ve şema 7 korundu. Ayrıntılar: `docs/STARTUP_AUDIT_1.9.2.md`.

## 1.9.1 — AI / web arama bağlantı testleri (6 Ekim 2026)

- Windows AutoDetect/PAC bayrağını zorunlu proxy sayıp API çağrısını engelleyen yanlış ön kontrol kaldırıldı. Gerçek env/statik proxy ayarı ve TLS doğrulaması korunur.
- Gemini için küçük gerçek API bağlantı testi; Tavily ve Jina testlerinde 401/403/429, SSL, DNS, timeout, bağlantı ve ProxyError ayrı gösterilir.
- Testler kayıtlı servisi/modeli kullanır. Kaydedilmemiş değişiklikte test düğmesi kapanır; kayıtlı ve test edilen servis açıkça gösterilir. Sunucu eski sekmelerdeki ayar uyuşmazlığını reddeder.
- Loglara anahtar/URL/yanıt gövdesi yazmadan exception zinciri, kod ve HTTP durumu eklenir. Analiz sırasında arama servisi hatası kendi adıyla korunur.
- 169 Python, 21 JavaScript testi ve 20 kaynak masaüstü smoke kontrolü geçti. Native OCR ve hedef Windows canlı ağ/installer doğrulaması bu çalışma kapsamında yapılmadı.
- AHP hesapları ve şema 7 değişmedi. Windows'a gönderilecek 1.9.1 kaynak paketi güncellendi; düzeltme için Windows EXE yeniden build edilmelidir.
- Ayrıntılar: `docs/NETWORK_FIX_1.9.1.md`.

## 1.9.0 — SQLite bağlantı ekranı (5 Ekim 2026)

- Veritabanı menüsünden uyumlu `.db`, `.sqlite` veya `.sqlite3` dosyası seçme, içerik önizleme ve onaylayarak bağlanma.
- Kaynak ve önceki veritabanı korunur; yeni bağlantı yönetilen bir çalışma kopyasına yapılır. Geçiş öncesi SQLite yedeği alınır, seçim yeniden açılışta hatırlanır.
- SQLite `.db` yedeği indirme. Masaüstü yedekleme/geri yükleme araçları seçili veritabanını kullanır.
- Bozuk/uyumsuz/yeni sürüm dosya reddi; devam eden analiz ve eski sekmelerin farklı veritabanına yazmasına karşı geçiş kontrolü.
- AHP hesabı ve şema sürümü 7 değişmedi. Windows kaynak paketi güncellendi; gerçek Windows EXE ve kurulum doğrulaması halen bekliyor.

## 1.8.0 — Windows masaüstü hazırlığı (4 Ekim 2026)

- PyInstaller onedir + pywebview/WebView2 masaüstü girişi ve Inno Setup EXE build tanımları.
- Dinamik loopback portu, masaüstü oturum doğrulaması, tek instance kontrolü, kontrollü backend kapanışı ve Windows Job Object.
- Program Files kaynakları ile LocalAppData kullanıcı verilerinin ayrılması; Windows Credential Manager anahtar deposu.
- Tutarlı SQLite yedekleri, migration öncesi kurtarma kopyası, doğrulanan/geri alınabilir offline restore.
- Sistem proxy/TLS ayarları, açık offline modu, PAC için doğrudan bağlantıya düşmeden açıklayıcı hata.
- Dönen ve hassas içerik yazmayan yapısal loglar; son kullanıcıya traceback göstermeyen başlangıç hataları.
- Windows için paketlenmiş Tesseract Türkçe/İngilizce OCR adaptörü; Mac Apple Vision yolu korundu.
- Sürüm kaynağı VERSION; mevcut favicon'dan Windows ikon/metadata; geliştiriciye özgü runtime kaynak yolu temizliği.
- Sabit build paketleri, OCR SHA256 kilidi, release hash/manifest/lisans üretimi, isteğe bağlı Authenticode imzası ve BT kabul belgeleri.
- AHP algoritması, ağırlıklar, eşikler, uygunluk sınıfları, şema sürümü 7 ve değerlendirme mantığı değiştirilmedi.

Windows installer üretimi/gerçek kurulum testleri bu Mac ortamında tamamlanmış değildir; bu sürüm henüz Windows dağıtımı onaylanmış release olarak etiketlenmemelidir.

## 1.7.1

Kongre logoları, logo keşfi/yükleme ve PDF'de logo kullanımı; araştırma profili kullanım rehberi.

## 1.7.0

Araştırma profili, kişiselleştirme, Conference Fingerprint ve yerel kongre önerileri.
