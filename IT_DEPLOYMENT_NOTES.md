# AHP Congress Analyzer — IT deployment notes

Version: 1.9.2. Publisher: release build sırasında `--publisher` ile verilmesi zorunludur; gerçekleşen değer `BUILD_MANIFEST.json` ve EXE/installer metadata'sında bulunur. Bu kaynak tesliminde yayıncı/sertifika varsayılmamıştır.

**Durum:** Bu dosya uygulanan kaynak kodu ve installer tanımını açıklar. Windows build, gerçek Credential Manager/WebView2/OCR ve temiz makinede kurulum/upgrade/uninstall henüz bu Mac ortamında doğrulanmamıştır. `docs/WINDOWS_ACCEPTANCE.md` kabul listesini uygulayın.

## Amaç / mimari

AHP tabanlı kongre analiz ve karar destek sistemi. Python 3.12 + FastAPI/Uvicorn + SQLAlchemy/SQLite + yerel HTML/CSS/JS + pywebview/WebView2. PyInstaller onedir; Inno Setup EXE. Python son kullanıcıya ayrı kurulmaz. Windows 10 1809+ veya Windows 11 x64; ARM64 bu paketçe kabul edilmez. Kurumun desteklenen Windows politikası geçerlidir.

## Kurulum ve izinler

- Uygulama: `%ProgramFiles%\AHP Congress Analyzer\AHP-Congress-Analyzer.exe` ve `_internal` bağımlılık/resource dizini.
- Yükseltilmiş yetki: yalnız IT kurulum/upgrade/uninstall için. Günlük kullanım admin istemez.
- Önkoşullar: bilgisayar genelinde WebView2 Evergreen x64 Runtime; .NET Framework 4.6.2+. Installer kontrol eder, eksikse durur. Otomatik önkoşul indirme/kurma yok.
- Tesseract 5, gerekli DLL'ler, eng/tur dil modelleri installer'a dahildir. End user PATH ayarı veya OCR kurmaz. Build sahibinin onaylı OCR paketi ve tüm lisans metinleri gerekir.
- Başlat menüsü ve isteğe bağlı genel masaüstü kısayolu; Başlat menüsünde yedekleme kısayolu.
- Installed Apps/uninstall kayıtları Inno tarafından oluşturulur. Uygulama runtime'da kalıcı registry ayarı yazmaz; WebView2/proxy bilgilerini okur. Credential Manager Windows tarafından yönetilir.
- Installer her upgrade'de yalnız uygulamanın `_internal` kod dizinini temizleyerek eski DLL artıklarını kaldırır. Yerel veri dizinine yazmaz.

## Kullanıcı verisi / oluşturulan dosyalar

Her Windows hesabı için `%LOCALAPPDATA%\AHP Congress Analyzer\`:

| Yol | İçerik |
|---|---|
| `database\kongre.db` | Kongreler, AHP modelleri, değerlendirmeler, kaynaklar, görseller/logolar, profil ve geçmiş |
| `database\kongre.db.connection.json` | Etkin çalışma kopyasının seçimi |
| `database\kongre.db.connections\*.db` | Bağlanan veritabanlarının çalışma kopyaları |
| `database\kongre.db.pending\*.db` | Geçici dosya önizlemeleri |
| `database\backups\*.db` | Arayüzden bağlantı değiştirmeden önce alınan yedekler |
| `database\exports\*.db` | İndirme sırasında oluşturulan, yanıt sonrası temizlenen geçici yedekler |
| `config\settings.json` | Etkin sağlayıcı ve model isimleri; anahtar içermez |
| `backups\*.db` | Tutarlı SQLite kopyaları |
| `logs\app.log`, `logs\error.log` | Backend logları |
| `logs\desktop\app.log`, `logs\desktop\error.log` | Masaüstü host logları |
| `cache\webview2` | WebView2 için ayrılmış cache yolu; private mode ek geçici profil kullanabilir |
| `exports` | Kullanıcının exportları için ayrılmış dizin; indirme penceresinde başka hedef seçilebilir |

OCR geçici normalize görseli işletim sisteminin kullanıcı TEMP dizininde oluşturulur; işlem sonunda silinir. Zorla kapanışta kalan geçici dosyalar kurumun TEMP temizliği politikasına tabidir. Çalıştırılabilir OCR/uygulama Program Files'tan çalışır, TEMP'e executable çıkarılmaz.

Log rotation: dosya başına yaklaşık 2 MB, üç geçmiş kopya. Hata türü/kod dosyası/fonksiyon/satır numarası kaydedilir; ham exception metni, request URL/query/body, kaynak metni ve anahtar kaydedilmez. Loglar kullanıcı verisi içermez diye mutlak bir dış paket garantisi verilmez; support paylaşımından önce BT inceleyebilir. SQLite ve yedekler kullanıcı içeriklerini barındırır; cihazın disk/hesap güvenliği ve yedek politikası uygulanmalıdır.

## Credentials

Windows Credential Manager Generic Credentials hedef öneki: `AHP Congress Analyzer/`. İlgili adlar: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `AIMLAPI_API_KEY`, `JINA_API_KEY`, `TAVILY_API_KEY`. API anahtarı EXE/installer/SQLite/JSON/log içine gömülmez. Uninstall anahtarları otomatik silmez. Mac `.env` dosyasını Windows'a veya release paketine kopyalamayın; Windows AI bağlantısı ekranında tekrar girin.

## Ağ erişimi

Inbound: yalnız `127.0.0.1:<dinamik TCP port>`. Ağ arayüzüne bind yok, firewall kuralı yok. Her açılışta tek kullanımlık başlangıç token'ı ve HttpOnly SameSite=Strict oturum cookie'si; Host/Origin kontrolü. Dış bilgisayarların erişmesi amaçlanmaz. Yerel UI internet istemez.

Outbound kullanıcı talep ederse:

| Özellik | Hedef | Port |
|---|---|---|
| OpenAI | api.openai.com | TCP 443 |
| Gemini | generativelanguage.googleapis.com | TCP 443 |
| OpenRouter | openrouter.ai | TCP 443 |
| Groq | api.groq.com | TCP 443 |
| AIMLAPI | api.aimlapi.com | TCP 443 |
| Jina Search | s.jina.ai | TCP 443 |
| Tavily | api.tavily.com | TCP 443 |
| Web kaynakları/logolar | Kullanıcının seçtiği genel kongre siteleri ve doğrulanmış yönlendirmeleri | TCP 443 / 80 |

DNS kurumun normal çözümleme mekanizmasını kullanır. Son kullanıcının açtığı dış bağlantılar varsayılan tarayıcıya gider; kurum tarayıcı politikası geçerlidir. WebView2 güncellemeleri Microsoft/kurum yönetimindedir; uygulama bir updater/service kurmaz. AI sağlayıcısı aracı hizmet üzerinden çalışıyorsa onun alt sağlayıcı/veri politikası ayrıca değerlendirilmelidir.

HTTP_PROXY / HTTPS_PROXY / ALL_PROXY / NO_PROXY ortam ayarları ve Windows statik internet proxy ayarı okunur. Gerçek proxy adresi yoksa doğrudan API isteği denenir; AutoDetect/PAC ayarının açık olması tek başına proxy kullanıldığının kanıtı değildir ve isteği durdurmaz. Açıkça tanımlı proxy başarısız olduğunda doğrudan bağlantıya fallback yoktur. PAC/WPAD betikleri ve SSPI otomatik oturum açma uygulanmadı. Bunların gerektiği ağlarda BT desteklenen erişim ayarını sağlamalıdır; offline çekirdek çalışır. Sistem sertifika kökleri ve SSL_CERT_FILE / SSL_CERT_DIR desteklenir; TLS doğrulaması daima açıktır. Proxy/sertifika politikalarını atlatma yoktur.

## Offline / hata davranışı

AHP hesabı, manuel kongre girişi, kayıt okuma/düzenleme/karşılaştırma, profil, yerel öneriler/fingerprint, geçmiş, PDF okuma/rapor oluşturma ve görsel OCR offline çalışır. Kaynaklardan AI yorumu, web araması, URL indirme, logo keşfi internet gerektirir. `KONGRE_OFFLINE=1` harici bağlantıları durdurur. Ağ hataları tüm uygulamayı kapatmaz. AI yarıda kalırsa kaynak kaydı korunur, sonraki açılışta tamamlanamayan analiz olarak görünür; kendiliğinden ücretli tekrar gönderilmez.

Pencere kapanışı onay ister; backend kontrollü kapanır. Uzayan işlem için zaman aşımı sonrası uygulamanın kendi backend'i sonlandırılır. Windows Job Object ana host çöktüğünde backend ve OCR alt süreçlerinin kalmasını önler. Güvenlik yazılımı Job Object atamasını engellerse uygulama gizlice korumayı atlamaz, başlangıç hatası verir.

## Sistem değişiklikleri

Windows services: yok. Scheduled tasks: yok. Startup entries: yok. Firewall/EDR/antivirus ayarı: yok. Execution-policy değişikliği: yok. Registry: installer/uninstaller kayıtları; runtime yalnız yukarıda belirtilen okumalardır. Sistem PATH değişikliği yok. Environment variables uygulama tarafından kalıcı olarak değiştirilmez. `KONGRE_DESKTOP=1` yalnız kendi süreç ailesinde ayarlanır; release DB yolunu Program Files ya da geliştirici `.env` üzerinden almaz.

## Backup / restore / taşıma

Masaüstü Dosya → Veritabanını yedekle; veya uygulama kapalıyken Başlat → Veritabanını yedekle. SQLite backup API aktif yazmalarla tutarlı snapshot oluşturur. Açılışta günde bir otomatik yedek, son yedi otomatik kopya korunur; manuel/migration/restore kopyaları otomatik silinmez.

Başka bilgisayardan alınan **güvenilen `.db` yedeği** taşınabilir. Profil/analiz görselleri DB içinde gelir; API anahtarları gelmez. Uygulamayı kapatıp Windows Çalıştır penceresinden veya BT terminalinden:

```bat
"C:\Program Files\AHP Congress Analyzer\AHP-Congress-Analyzer.exe" --restore "D:\OnayliYedek\conference.db"
```

Onay sorulur, integrity/foreign-key/schema sürümü kontrol edilir, kopya üzerinde migration denenir, mevcut DB önce ayrı yedeklenir; başarılı kontrolden sonra atomik değiştirilir. Hatalı/yeni sürüm yedeği mevcut DB'ye yazılmaz. Eski web sürümünün SQL exportu için geliştirme `restore_backup.py` ile **yeni** `.db` dosyası üretilebilir; güvenilmeyen SQL çalıştırılmamalıdır. Uygulama EXE restore komutu SQL dosyası kabul etmez.

## Upgrade / uninstall / reinstall

Aynı AppId ile yeni sürüm mevcut kurulum yerine yüklenir. Önce uygulama ve diğer Windows oturumlarındaki kopyaları kapatın; installer süreçleri zorla kapatmaz. Aynı oturum mutex'i açık uygulamayı saptar. Birden çok kullanıcı oturumu varsa BT rollout öncesinde tüm oturumları kapatmalıdır. Güncellemeden önce manuel yedek alın. Migration sırasında ön yedek alınır. Şema gelecekte değişirse eski EXE yeni DB'yi açmayı reddeder; downgrade için eski sürümün uygun yedeğini ayrı koruyun.

Settings → Apps → Installed Apps → AHP Congress Analyzer → Uninstall; veya IT için `unins000.exe /VERYSILENT /NORESTART`. Binary'ler ve kısayollar kaldırılır; LocalAppData ve Credential Manager anahtarları korunur. Reinstall aynı Windows hesabındaki kayıtları bulur. Tüm veri kaldırma ayrı ve açık IT/kullanıcı kararıdır: önce yedek, uygulamayı kapatma, ilgili kullanıcı LocalAppData dizinini silme ve Credential Manager'da yalnız bu uygulamanın önekli girdilerini kaldırma. Diğer uygulama credential'larına dokunulmaz.

## Hash / imza / dağıtım

Gerçek build çıktısı `release\<sürüm>\` altında installer, SHA256.txt, README.txt, bu belge, CHANGELOG, BUILD_MANIFEST, OCR manifesti, package ve UI smoke raporları ve lisansları içerir. Installer oluştuktan/imzalandıktan sonra SHA256 hesaplanır. PowerShell'in normal oturumunda (policy değiştirmeden):

```powershell
Get-FileHash .\AHP-Congress-Analyzer-Setup-1.9.2.exe -Algorithm SHA256
Get-AuthenticodeSignature .\AHP-Congress-Analyzer-Setup-1.9.2.exe
```

SHA256 değerini aynı güvenilir kanaldan alınmış SHA256.txt ile karşılaştırın. Hash tek başına yayıncı kimliğini doğrulamaz. İmzasız build mümkündür; SmartScreen/AV kararı cihaz politikasına bağlıdır. Engellenirse BT inceleme ve onay süreci gerekir; koruma devre dışı bırakılmaz. Tarama için kullanıcı verisi/API anahtarları içeren dosyaları harici servislere yüklemeyin.

Sessiz kurulum BT aracı üzerinden `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="<BT'nin izin verdiği yol>"`; WebView2/.NET önkoşullarını önceden sağlayın, sonuç kodunu kontrol edin. Kullanıcı verisini installer admin hesabıyla oluşturmayın; ilk gerçek kullanıcı açılışı oluşturur.

## Optional: Authenticode Code Signing

Build sahibinin Windows sertifika deposunda erişebildiği bir code-signing sertifikası ve SDK SignTool gerekir. Sertifika/parola repository'ye konmaz. `build_windows.bat` için `--sign-thumbprint`, `--signtool`, `--timestamp-url` parametrelerini verin. Build ana EXE'yi, Inno installer ve generated uninstaller'ı imzalar; doğrulamadan sonra hash üretir. Sertifika yoksa parametreleri atlayın. Paket içindeki üçüncü taraf DLL/EXE'lerin imza/lisans/provenance incelemesi ayrıca yapılmalıdır.

## SQLite bağlantı ekranı (1.9.0)

Sol menüde Veritabanı → dosya seç → Dosyayı kontrol et → kayıt sayılarını incele → onayla → SQLite veritabanını bağla. Yalnız uygulamaya uygun SQLite tabloları kabul edilir; 100 MB yükleme sınırı vardır. Kaynak dosya değişmez; veri kullanıcı veri dizinindeki yönetilen çalışma kopyasına yazılır. Eski bağlantı dosyası korunur ve geçiş öncesi `before-connect` yedeği alınır. Aktif AI/HTTP işlemleri bitmeden geçiş yapılmaz.

Ana DB adının yanındaki `.connection.json` seçim dosyası ile `.connections` klasörü birlikte korunmalıdır. `.pending` geçici dosyalardır. Gerçek aktif dosya UI’da gösterilir; masaüstü/CLI backup ve restore komutları da bu seçimi kullanır. Başka bilgisayara taşımak için UI’dan SQLite `.db` yedeği indirin ve hedef uygulamadan bağlayın. API anahtarları yedeğe dahil değildir. Bu akış DB birleştirme işlemi yapmaz.

## AI ve arama bağlantı tanılaması (1.9.1)

Önce servis/model/anahtar ayarlarını kaydedin, sonra test edin. Test kayıtlı servisi kullanır; sonuçta servis adı görünür. 401, 403, 429, SSL, DNS, timeout ve gerçek proxy hataları ayrıdır. Geçici dropdown seçimi kaydedilmeden test edilmez. Anahtar veya ham API yanıtını destek kaydına koymayın. Teknik kodlar ve exception zinciri `%LOCALAPPDATA%\AHP Congress Analyzer\logs` altında tutulur. Kök neden, kapsam ve Windows tekrar testi: `docs/NETWORK_FIX_1.9.1.md`.

## Windows başlangıç tanılaması (1.9.2)

Masaüstü, installer ile aynı .NET Framework çalışma zamanını açıkça yükler. Başarısız ilk CLR yüklemesini CoreCLR denemesiyle gizlemez. WebView2/.NET önkoşulları ve paket DLL yolları kontrol edilir; API anahtarı veya ağ erişimi yerel açılışın önkoşulu değildir.

Başlangıç hatasında ekrandaki gerçek log yolunu kullanın. Normal konum `logs/desktop/error.log`; backend için `logs/error.log`. Aşama, exception/cause zinciri, güvenli yapısal açıklama ve sayısal Windows hata kodları kaydedilir. Keyfi hata mesajı/source satırları/locals kaydedilmez. Ana log yolu açılamazsa kullanıcı TEMP dizininde `ahp-startup-*` klasörü denenir ve oluşan yol gösterilir.

Build sırasında `--self-test` ve gerçek `--smoke-ui` testi birlikte zorunludur. UI testi geçici LOCALAPPDATA ve offline mod kullanır; mevcut kullanıcı DB/anahtarlarına dokunmaz. `UI_SMOKE_TEST.json`, build bilgisayarındaki pencere açılışını doğrular; hedef VM kabulünün yerine geçmez. Detay: `docs/STARTUP_AUDIT_1.9.2.md`.
