AHP CONGRESS ANALYZER — WINDOWS RELEASE

Bu paket AHP tabanlı kongre analiz uygulamasıdır.
1. IT_DEPLOYMENT_NOTES.md ve kurum kurulum politikasını inceleyin.
2. SHA256.txt ile installer hash'ini doğrulayın; imza varsa doğrulayın.
3. BT, WebView2 Evergreen x64 Runtime ve .NET Framework 4.6.2+ önkoşullarını sağlar.
4. Setup EXE'yi BT yetkisiyle çalıştırın.
5. AHP Congress Analyzer kısayolunu normal kullanıcı olarak açın.

Python, pip ve terminal son kullanıcı için gerekli değildir.
AHP hesapları, manuel giriş, kayıtlar, profil/öneriler, PDF ve OCR offline çalışır.
AI/web kaynakları internet ve ilgili servisin geçerli API anahtarını gerektirir.
API anahtarlarını AI bağlantısı ekranından girin; Windows Credential Manager saklar.
Servis/model/anahtar seçimini önce kaydedin, sonra bağlantıyı test edin.
Test düğmesi kayıtlı servisi kullanır ve hangi servisin test edildiğini gösterir.
Kaydedilmemiş değişiklik varsa önce kaydetmeniz istenir.

Veriler: %LOCALAPPDATA%\AHP Congress Analyzer
Yedek: Veritabanı > SQLite .db yedeğini indir; veya Dosya > Veritabanını yedekle.
Başka DB: Veritabanı > dosya seç > Dosyayı kontrol et > onayla > SQLite veritabanını bağla.
Kaynak dosya ve eski kayıtlar korunur; yeni kayıtlar çalışma kopyasına yazılır.
Bağlantı yeniden açılışta hatırlanır. Restore ayrıntıları: IT_DEPLOYMENT_NOTES.md.
Uninstall kayıtları ve API anahtarlarını otomatik silmez.
Başlangıç hatasında ekranda gösterilen gerçek log dosyasıyla BT biriminize başvurun.
Normal kayıt: logs\desktop\error.log; yerel servis: logs\error.log.
.NET yükleme hatası API anahtarı veya proxy hatası değildir.
Uygulamanın yerel arayüzü API anahtarı ve internet olmadan açılabilir.
Güvenlik yazılımını, proxy'yi veya sertifika kontrolünü devre dışı bırakmayın.

Build bilgisi: BUILD_MANIFEST.json
Test kapsamı: PACKAGE_SMOKE_TEST.json ve UI_SMOKE_TEST.json
(Bunlar canlı AI veya hedef bilgisayarda installer kabul testi değildir.)
Sürüm: VERSION / CHANGELOG.md
