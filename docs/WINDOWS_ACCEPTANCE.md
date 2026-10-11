# Windows kabul testi — 1.10.0

Durum: 1.10.0 için asistanın erişebildiği Windows test ortamı yok; kullanıcının Windows bilgisayarında yeniden doğrulama gerekir. Aşağıdaki satırlar **bekliyor**; otomatik olarak başarılı sayılmaz. Testi yapan BT personeli tarih, Windows build, WebView2 sürümü, cihaz politikası ve installer SHA256 bilgisini kaydetsin. Kaynak testleri için `docs/WINDOWS_VERIFICATION.md` belgesine bakın.

| Senaryo | İşlem / beklenen sonuç | Windows sonucu |
|---|---|---|
| Build | Python 3.12 x64 ile tek komut; frozen self-test ve izole offline WebView2 testi geçer; iki JSON raporu/lisans/manifest/hash oluşur | Bekliyor |
| Clean install | Python/pip/Tesseract olmayan temiz Windows'a IT kurar; Apps listesi ve kısayollar görünür | Bekliyor |
| Eksik önkoşul | WebView2/.NET yoksa anlaşılır uyarı; güvenlik ayarı değişmez | Bekliyor |
| İlk açılış | Normal kullanıcı, API anahtarı ve ağ olmadan; konsol yok; AHP Congress Analyzer penceresi; 4 örnek kayıt | Bekliyor |
| Path | Program Files'a runtime yazma yok; DB/config/loglar doğru gerçek kullanıcı LocalAppData altında | Bekliyor |
| AHP | A=73.38331160365063, B=74.81644136416664, C=94.64248953544231, D=40.14684690866672 | Bekliyor |
| Manuel kayıt | Yeni kongre kaydet/düzenle/çoklu format; kapat-aç, kaydın aynı kaldığını doğrula | Bekliyor |
| Özellik paritesi | Karşılaştırma, senaryo, profil, öneriler, fingerprint, logo ve çöp kutusu | Bekliyor |
| Credential Manager | Test anahtarı kaydet; JSON/SQLite/log/HTML içinde yok; uygulama yeniden açıldığında kayıtlı | Bekliyor |
| AI | IT onaylı test anahtarıyla bir küçük analiz; kanıt ve AHP sonucu; PDF; ücretli istek için normal UI onayı | Bekliyor |
| AI otomatik geçiş | En az iki kayıtlı servis; görünür geçiş sırası, 429/402 sonrası yedek, rapor/PDF'de katkı veren servisler; frozen self-test'te `ai_failover_checkpoint_fixture` başarılı | Bekliyor |
| AI ilerleme | Tamamlanmış parça sonrası kesinti; yeniden aç → kayıtlı kaynaklarla tekrar dene; tamamlanmış parçalar yeniden gönderilmez, yarım analizden puan çıkmaz | Bekliyor |
| Arama / URL | Jina/Tavily küçük test; kongre web kaynağı; proxy/sertifika ve quota mesajları | Bekliyor |
| Ağ yok | Bağlantıyı test ortamında kes; manuel AHP/kayıt/PDF çalışır; AI hata verir, uygulama açık kalır | Bekliyor |
| OCR | Türkçe/İngilizce PNG/JPEG/WebP afiş: metin, satırlar; gerçek Tesseract Windows DLL'leri; ağ gerekmez | Bekliyor |
| PDF upload | Dosya seçici, 30 sayfa/4 MB sınırları; kaynak metni çıkarılır | Bekliyor |
| PDF download | WebView2 indirme penceresi, Türkçe karakterler, hedef dizin; yazdırma | Bekliyor |
| Yerel güvenlik | 127.0.0.1 dışında listen yok; cookiesiz health/state 403; yanlış Host/Origin 403 | Bekliyor |
| Çift açılış | İkinci EXE uyarı; ikinci backend/DB recovery oluşmaz | Bekliyor |
| Kapanış | Onayı iptal edince devam; onaylayınca server portu kapanır, backend/OCR kalmaz | Bekliyor |
| Çöküş | TEST hesabında host process sonlandır; Job Object backend/OCR'yi kapatır; yeniden açılış mümkün | Bekliyor |
| Uzayan AI | Pencereyi kapat; bounded kapanış; sonraki açılışta korunmuş yarım analiz ve retry | Bekliyor |
| Log | Hata simülasyonu, rotation; test anahtarını/özel metni arayarak loglarda olmadığını doğrula | Bekliyor |
| Backup | Açık uygulamada menüden; DB bütünlüğü ve restorasyon | Bekliyor |
| Restore failure | Bozuk ve gelecekteki schema yedeği: mevcut DB byte içeriği değişmez | Bekliyor |
| Upgrade | Kayıtlı verinin yedeği; yeni installer aynı AppId; kayıtlar/anahtarlar korunur | Bekliyor |
| Uninstall | Apps'ten kaldır; binary/kısayol yok; LocalAppData ve credentials korunmuş | Bekliyor |
| Reinstall | Aynı Windows hesabıyla tekrar kur; aynı kongreler ve profil görünür | Bekliyor |
| Restart | Windows yeniden başlat; otomatik startup yok, kısayoldan açılır ve veriler korunur | Bekliyor |
| İmza/hash | Final installer SHA256 ve varsa EXE/setup/uninstaller Authenticode doğrulanır | Bekliyor |

Canlı API testi hesap erişimi, ücret/kota ve kurum ağına bağlıdır. Test başarısızsa ham API yanıtı veya anahtarı hata raporuna koymayın. Tek kullanımlık test verilerini üretim hesabı yerine ayrı test hesabında kullanın.

## SQLite bağlantısı — Windows'ta ayrıca doğrulanacak

- Dosya seçicisinden Türkçe/boşluk içeren yoldaki uyumlu `.db` dosyasını seçme, sayıları önizleme ve onaylayarak bağlanma.
- Yeni kayıtların çalışma kopyasına yazılması, kaynak/önceki DB’nin korunması ve uygulama yeniden açıldığında seçimin hatırlanması.
- WebView2 üzerinden `.db` yedeği indirme ve indirilen yedeği tekrar bağlama.
- Masaüstü Dosya menüsü ve CLI backup/restore'un yeni aktif DB'yi kullanması.
- Bozuk/uyumsuz dosyanın reddedilmesi ve süren AI analizi sırasında geçişin engellenmesi.

## 1.9.1 bağlantı düzeltmesi — hedef Windows bilgisayarında

- Env/static proxy olmayan ve otomatik algılama açık olabilen ağda, geçerli anahtarla Gemini, Tavily ve Jina testlerini ayrı ayrı çalıştırın. API yanıtı alınmadan proxy uyarısı verilmemeli.
- Tavily kayıtlıyken Jina seçin: test kapanmalı, kaydetme uyarısı görünmeli. Jina'yı kaydedip test edin: hem kayıtlı hem test edilen servis Jina olmalı. Uygulamayı yeniden açıp seçimin korunduğunu kontrol edin.
- AI modeli veya anahtarı değişince kaydetmeden test edilememeli. İki sekmede farklı kayıt yapıldıysa eski sekmenin testi uyuşmazlık uyarısıyla durmalı.
- Test ortamında hatalı anahtar / yetki / kota / DNS / timeout / sertifika / proxy durumları kendi mesajlarını göstermeli. Güvenlik ayarlarını gevşetmeyin; canlı hesaba rate-limit yaratmayın, hata senaryoları için transport fixture'larını kullanın.
- Gerçek env/statik proxy verilmişken arıza durumunda doğrudan bağlantıya geçilmemeli; NO_PROXY davranışı korunmalı.
- Loglarda API anahtarı, Authorization header, ham response veya URL bulunmamalı; servis/kod/sayısal hata nedeni kaydedilmeli.

## 1.9.2 başlangıç incelemesi — hedef temiz VM

- Yerel arayüzü API anahtarı olmadan açın; `application_ready` aşaması kaydedilmeli. AI/arama bağlantı testi yalnız kullanıcı isteğinde yapılmalı.
- UI build testinde mevcut kullanıcı kayıt/ayarları korunmalı; geçici klasör ve dört örnek kayıt kullanılmalı.
- WebView2/.NET eksikse özel önkoşul mesajı, paket DLL'si eksikse dosyanın göreli adı ve ilk hatanın aşaması görünmeli.
- Yeni `.NET Framework` yüklemesi başarısızsa `netfx_runtime_loading` kaydı ve ilk cause zincirindeki sayısal hata kodunu inceleyin. CoreCLR denemesiyle ilk hata gizlenmemeli. Üç DLL'nin varlığı yüklenebildiklerini kanıtlamaz.
- Hata ekranında `%LOCALAPPDATA%` metni yerine gerçek kullanıcı/veri/log yolu görünmeli. Log dizini oluşturulamıyorsa TEMP tanılama yolu veya dosya oluşturulamadığı bilgisi gösterilmeli.
- Türkçe/boşluklu kullanıcı yolundan ve farklı çalışma dizini olan kısayoldan açılışı doğrulayın.

Kullanıcının eski logu CLR yükleme hatası gösterdi. Asistanın yeni sürümü Windows'ta çalıştırdığı iddia edilmez; bu satırların sonucu henüz bekliyor.
