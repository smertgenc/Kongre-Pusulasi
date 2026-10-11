# Windows masaüstü dağıtım kararı — 1.8.0

Tarih: 4 Ekim 2026. Hedef: Windows 10 1809+ / Windows 11, x64, tek kullanıcılı yerel çalışma alanı. Desteklenen/güncel Windows sürümünü şirket BT politikası belirler. Windows ARM64 bu paketin kapsamı dışındadır.

## A. Mevcut mimari

Ana geliştirme girişi `server.py`; FastAPI/Uvicorn HTTP katmanı `app/main.py`; SQLAlchemy/SQLite veri katmanı `app/database.py` ve `app/models.py`; şema sürümü 7. Mevcut geliştirme Python sürümü 3.12.14. Arayüz derleme gerektirmeyen HTML/CSS/JavaScript (`static/`). AHP hesabı `engine.py`, iş akışları `app/services.py`, proje kriterleri `app/congress_policy.py` içinde. 10 kriter, model sürümleri, kanıtlar, analiz/inceleme geçmişi SQLite'ta korunur.

OpenAI, Gemini, OpenRouter, Groq, AIMLAPI için sağlayıcı adaptörleri; Jina/Tavily kaynak araması; HTML için BeautifulSoup, PDF okuma için pypdf, rapor için ReportLab, görsel/logo için Pillow kullanılır. Araştırma profili, kişisel uygunluk, Conference Fingerprint ve yerel benzer kongre önerileri mevcut uygulamada bulunur. Orijinal OCR macOS Apple Vision/Swift'e bağımlıdır. Bağımlılıklar gerçek `requirements.txt` sürümlerinden alınmıştır.

## B. Riskler

Kaynak dizinine yazılan `.env`, veritabanı ve Mac OCR derleme çıktısı Program Files için uygun değildi. Yerel serviste oturum doğrulaması, masaüstü süreç yönetimi ve dönen dosya logları yoktu. HTTP istemcileri kurumsal proxy ayarlarını kullanmıyordu. Kısıtlı bilgisayarda WebView2, .NET, uygulama çalıştırma ve harici API erişimi BT tarafından onaylanmalıdır. Mac üzerinde Windows binary/kurulum doğrulaması yapılamaz.

## C. Paketleyici

PyInstaller 6.22.3 **onedir**, Python 3.12 x64. Python çalışma zamanı ve gerekli bağımlılıklar birlikte gelir. UPX, obfuscation, onefile ile geçici dizine executable çıkarma kullanılmaz. İş mantığı taşınır; yeniden yazılmaz. Ayrı/temiz build venv'i gereksiz Qt/CEF/numpy/openpyxl paketlerinin dağıtıma girmesini önler.

## D. Masaüstü ve installer

pywebview 6.2.1, yalnız `edgechromium` renderer. MSHTML fallback yok. WebView2 Evergreen ve .NET Framework 4.6.2+ BT tarafından kurulur; installer eksik önkoşulda açık mesajla durur. Inno Setup 6.3+ EXE; yayıncı adı build parametresidir, hayali yayıncı yazılmaz. MSI/MSIX ya da portable ZIP eklenmedi. Inno sürümünün lisansını ve dağıtım hakkını build sahibi doğrular.

## E. Veriler

Program Files uygulama kodunu; `%LOCALAPPDATA%\AHP Congress Analyzer` gerçek oturum kullanıcısının database/config/log/cache/export/backups dizinlerini içerir. İlk açılış eski davranıştaki dört Excel örneğini ve AHP modelini oluşturur. Upgrade schema 7'yi değiştirmez. Şema yükseltmesinden önce SQLite backup API ile tutarlı kopya alınır. Başlangıçta günde bir otomatik yedek; son yedi otomatik kopya tutulur. Manuel, restore öncesi ve migration öncesi kopyalar otomatik silinmez. Installer/uninstaller kullanıcı verisini silmez.

## F. Anahtarlar

Windows Generic Credentials: `AHP Congress Analyzer/<PROVIDER>_API_KEY`. Her Windows hesabı kendi anahtarlarını görür. Model/sağlayıcı seçimi JSON; API anahtarları JSON, SQLite, log, browser response veya installer'a yazılmaz. Geliştirme `.env` davranışı korunur; release `.env` okumaz ve mevcut Mac anahtarlarını otomatik taşımaz. Anahtarlar Windows'ta AI bağlantısı ekranından yeniden girilir.

## G. Ağ ve süreç ömrü

Ana EXE bir backend child process başlatır. Child 127.0.0.1 üzerinde port 0 ile socket'i açıp aynı socket'i Uvicorn'a verir; port bulma/açma yarışı yoktur. Tek kullanımlık bootstrap token, HttpOnly/SameSite=Strict cookie, exact Host/Origin kontrolü uygulanır. Oturum her açılışta değişir. Backend access log kapalıdır. Ana pencere kapanırken kontrollü durdurma, zaman aşımında yalnız kendi child'ını sonlandırma; Windows Job Object ile ana EXE çökse bile backend/OCR descendants temizliği.

Ortam/Windows statik proxy ayarları ve sistem TLS kökleri kullanılır. PAC/WPAD betikleri çalıştırılmaz; otomatik algılama bayrağı bağlantıyı engellemez. Gerçek env/statik proxy yoksa doğrudan API isteği yapılır. Tanımlı proxy hatasında doğrudan bağlantıya fallback yapılmaz. Yerel servis proxyye gönderilmez. Genel web hedeflerinde IP doğrulaması ve redirect kontrolü korunur; proxy kullanıldığında son DNS/erişim sınırı kurumun güvenilen proxy'sindedir. Sertifika doğrulaması kapatılmaz. `KONGRE_OFFLINE=1` harici ağ işlemlerini engeller.

## H. Build / release

`build_windows.bat` sabit sürümlü build ortamını hazırlar, `tools/build_windows.py` paket/smoke test/installer/hash/manifest/lisans çıktılarını üretir. OCR için BT onaylı Tesseract 5 x64, DLL'ler ve Türkçe/İngilizce dil dosyaları önce `tools/prepare_ocr.py` ile kaynağı ve SHA256 listesi kaydedilerek hazırlanır. Runtime'da dil modeli indirilmez. Kullanıcıya OCR kurulumu yaptırılmaz; paket OCR'yi içerir. Değişen OCR dosyasında build durur.

## I. IT dağıtımı

Kurulum yükseltilmiş yetki; uygulama normal kullanıcı yetkisi. Servis, task, startup veya firewall istisnası eklenmez. Kurum sertifikası varsa Authenticode opsiyoneldir; EXE, installer ve uninstaller imzalanır. Güvenlik ürünü engellerse BT'nin inceleme/izin süreci uygulanır, güvenlik devre dışı bırakılmaz. Temiz Windows kabul testi dağıtımdan önce zorunludur.

## J. Değişiklik sınırı

Yeni masaüstü host, session/log/backup/secret/path/network adaptörleri ve Windows OCR; mevcut iş mantığında değişiklik yok. `engine.py`, AI kriter kuralları, ağırlıklar, uygunluk eşikleri, DB modelleri değişmedi. Ayrıntılı dosya listesi: `docs/WINDOWS_CHANGE_REPORT.md`.

## Birincil kaynaklar

- [PyInstaller çalışma biçimi](https://pyinstaller.org/en/stable/operating-mode.html)
- [pywebview paketleme](https://pywebview.flowrl.com/guide/freezing.html), [API](https://pywebview.flowrl.com/api/)
- [Microsoft WebView2 dağıtımı](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- [Inno AppMutex](https://jrsoftware.org/ishelp/topic_setup_appmutex.htm)
- [Tesseract kurulum/Windows binary kaynakları](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- [Tesseract TSV kullanımı](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)

Windows WinRT OCR kullanılmadı: [Microsoft belgesi](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr) desktop uygulamalarda paket kimliği gerektirir; Inno/Win32 uygulamasının bu önkoşulu yoktur. Tesseract bu bağımlılığı ve online OCR ihtiyacını kaldırır.

## 1.9.2 başlangıç revizyonu

Sabit pywebview 6.2.1 sürümü ilk CLR import hatasında CoreCLR denemesine geçebiliyor. Yeni başlatıcı önce installer'ın istediği .NET Framework runtime nesnesini açıkça yükler; ilk hatayı korur. DLL/kaynak varlığı kontrolü, erken aşama logları ve geçici kullanıcı dizininde offline gerçek WebView2 build testi eklendi. API anahtar deposu yerel açılışın parçası değildir. Bu revizyon AHP veya API bağlantı kurallarını değiştirmez. Gözlenen Windows hatası ve doğrulama sınırları: `STARTUP_AUDIT_1.9.2.md`.
