# Temiz Windows başlangıç incelemesi — 1.9.2

Tarih: 8 Ekim 2026 (Windows hata kaydı: 7 Ekim 2026).

## ROOT CAUSE

**Windows logu UI başlatılırken Pythonnet/.NET yüklemesinde çöküldüğünü doğruladı.** Zincir `launcher.main → webview.start → winforms.py:17 → clr → pythonnet.load → set_runtime_from_env → _create_runtime_from_spec:90`; son cause OSError. API, proxy veya veritabanı aşaması değildir.

Sabitlenmiş `pywebview 6.2.1` wheel'i indirilip kaynak kodu okundu: `winforms.py` satır 14'teki ilk `import clr` başarısız olunca 16. satırda `PYTHONNET_RUNTIME=coreclr` yapılır ve 17. satırda yeniden denenir. Kullanıcının logu **ikinci denemeye** aittir. `pythonnet 3.2.0` satır 90 da açık seçilen runtime'ın başarısızlık bloğudur. Kurulum yalnız .NET Framework isterken WebView'in farklı CoreCLR çalışma zamanını denemesi ve ilk hatayı gizlemesi doğrulanmış entegrasyon kusurudur.

**İlk .NET Framework yüklemesinin neden başarısız olduğu henüz kesin değildir.** 1.9.1 logu iç OSError mesajı/sayısal kodunu içermiyor. Kullanıcının PowerShell kontrolünde ClrLoader.dll, Python.Runtime.dll ve WebView2Loader.dll için üç sonuç da `True`: bu dosyalar kurulu pakette mevcut. Dosyanın bulunması, Windows tarafından yüklenebildiğini kanıtlamaz. Eksik DLL veya yanlış kurulum kök neden ilan edilmedi. 1.9.2, .NET Framework runtime nesnesini ortam seçiminden bağımsız açıkça yükler; WebView'in CoreCLR fallback'ine bırakmaz ve ilk yükleme hatasını korur. Yeni sürümün hedef VM'de çalıştığı henüz doğrulanmadı.

Ayrıca **başlangıç tanılamasının yetersiz olduğu** doğrulandı. Bazı import/dizin/log kurulum hataları log kurulmadan meydana gelebiliyor; ValueError ayrı yoldan loglanmadan gösteriliyor; son hata mesajı gerçek veri yolu yerine literal `%LOCALAPPDATA%` içeriyordu. Paket self-test'i gerçek WebView2 penceresini açmadığı için başarılı olması UI başlangıcını doğrulamıyordu. Bunlar 1.9.2'de düzeltildi.

## HATANIN OLUŞTUĞU DOSYA / SATIR / FONKSİYON

- **1.9.1 `desktop/launcher.py`, `main()`, satır 129–132:** tüm beklenmeyen başlangıç hatalarını aynı mesajla gösteren blok. Bu, alttaki exception'ın kaynağı değildir.
- **1.9.1 `desktop/logging_setup.py`, `event()` / `SafeFormatter`:** tip ve bazı frame bilgileri vardı; başlangıç aşaması, güvenli açıklama ve tüm cause zincirinin traceback'i yoktu.
- **`desktop/backend.py`, `run_backend()`:** logging ve socket oluşturma korunan bloktan önceydi. Veritabanı yaşam döngüsü hatası üst sürece yalnız `BACKEND_START_FAILED` olarak iletiliyordu.
- **Gelen Windows kaydı:** 2026-10-07T19:49:29Z; `winforms.py:17` ve `pythonnet/__init__.py:90` CoreCLR fallback hatasını gösteriyor. İlk .NET Framework hatasının ayrıntısı mevcut eski logda yok.

## NEDEN GELİŞTİRME BİLGİSAYARINDA ÇALIŞIP TEMİZ VM'DE ÇALIŞMIYOR?

Kaynak web sunucusu `server.py`, WebView/CLR yüklemez. Windows masaüstü ise pencere açarken bu zinciri çalıştırır; gelen logdaki ayrım buradadır. Geliştirici Windows makinesinde çalışıp VM'de çalışmamasının daha alt nedeni, kurulu DLL/runtime kontrolüyle tamamlanmalıdır. Son düzeltmeyle ilişkiyi incelemek için aşağıdaki karşılaştırma yapıldı:

- Projede `.git` yok. `git status` / `git log` kullanılamadı. Bunun yerine saklanan 1.9.0 ve 1.9.1 kaynak ZIP'leri dosya içeriği bazında karşılaştırıldı.
- 1.9.1 çalışma ağacı saklanan 1.9.1 kaynak arşiviyle aynıydı.
- 1.9.0 → 1.9.1 arasında `desktop_main.py`, `desktop/launcher.py`, `desktop/backend.py`, `app/paths.py`, `app/config.py`, requirements, `.spec` ve installer değişmemişti.
- Yeni network modülleri gerçek API isteği sırasında çalışır. İncelenen başlangıç akışında zorunlu API/proxy bağlantı testi yoktur. Yeni `connection_probe` / `connection_errors` importları ve ilgili bağımlılıklar kaynak testlerinde sorunsuz yükleniyor; gerçek frozen Windows sonucu henüz yok.

Dolayısıyla API/proxy düzeltmesinden bağımsız bir masaüstü runtime yükleme problemi doğrulandı; bunu kullanıcı kurulum hatası diye nitelemek için henüz kanıt yok.

## İNCELEME VE YAPILAN DEĞİŞİKLİKLER

| Alan | Bulgular / işlem |
|---|---|
| Entry point | `desktop_main.py` zaten `multiprocessing.freeze_support()` kullanıyordu. Launcher importu sırasında oluşan hatalar için ek hata yakalama eklendi. |
| Veri yolu | `app/paths.py` zaten `os.getenv('LOCALAPPDATA')` kullanıyordu; DB yolu literal `%LOCALAPPDATA%` değildi. Kaynak ve kullanıcı yolları mutlak resolve edilir. Hata ekranı gerçek yolu ve error.log dosyasını gösterir. |
| Erken hata | Yeni `desktop/startup.py`, API/DB/UI importlarından önce log kurar. Ana log yolu oluşturulamıyorsa kullanıcı geçici dizininde `ahp-startup-*` tanılama dosyası oluşturmayı dener; başarılamazsa bunu açıkça belirtir. |
| Loglar | Aşama, component, exception tipi, tüm iç içe nedenlerin frame/satır/fonksiyonları ve sayısal OS hata kodları kaydedilir. `diagnostic.traceback` okunabilir çağrı zinciridir. |
| Hata metni / gizlilik | Modül adı, bilinen başlangıç kodu, errno/winerror gibi yapısal açıklamalar korunur. Key, URL, Authorization veya kullanıcı metni içerebilecek keyfi exception message'ları gizlenir. Source satırları/locals yazılmaz. Sadece regex ile ham `logger.exception` basmak anahtar gizliliğini garanti etmediği için kullanılmadı. |
| Windows API | Mutex/Job Object başarısızlıklarında `GetLastError` artık kaybedilmez. Süreç ve pipe temizliği başka bir hatayla ilk nedeni gizlemez. |
| Kaynak dosyaları | VERSION, static JS/CSS/HTML, AHP başlangıç JSON'u ve intelligence config başlangıçta denetlenir. Eksik dosyanın göreli adı loga yazılır. Bundle kaynakları salt okunur, DB/config/log/cache kullanıcı dizininde kalır. |
| Geliştirme ayarı / otomasyon | Hatalı KONGRE_PORT ortam değerinin masaüstünde gereksiz import çöküşü oluşturduğu yeniden üretildi ve düzeltildi. Otomatik UI testi, açık uygulama veya backend kapanışında modal pencere beklemez; başarısızlık raporlanır. |
| Encoding | `app/services.py` ilk kayıt JSON'unu platform varsayılanıyla okuyordu; UTF-8 açıkça belirtildi. Bu bir taşınabilirlik düzeltmesidir; VM çöküşünün nedeni olduğu iddia edilmez. |
| API anahtarları | `DesktopSettingsStore` Windows Credential Manager nesnesini artık yalnız anahtar gerektiğinde oluşturur. Ana arayüz ve yerel AHP açılırken anahtar okunmaz ve dış API isteği yapılmaz. Eksik anahtar AI özelliği kullanılırken gösterilir. |
| WebView2 / .NET | Mevcut WebView2 tespiti ve installer önkoşulu korunur. Çalıştırma sırasında .NET Framework 4.6.2+ kontrolü de yapılarak ayrı anlaşılır mesaj verilir. Eksik runtime nedeniyle güvenlik ayarı değiştirilmez. |
| Paketleme | PyInstaller onedir + Inno Setup EXE. Mevcut hidden importlar korundu. `.spec`, sabit paketlerden CLR/WebView DLL toplamasını açıkça yapar; build altı zorunlu DLL'nin doğru paket yolunda olduğunu denetler. Yeni dependency veya rastgele DLL eklenmedi. |
| Runtime seçimi | Yeni `desktop/runtime.py`, `pythonnet.load(clr_loader.get_netfx())` ile installer'ın istediği .NET Framework'ü açıkça kullanır. Ortamın PYTHONNET_RUNTIME seçimini almaz; pywebview'in başarısız ilk importu CoreCLR hatasıyla gizlemesini engeller. |
| Sertifika | Yeni paket self-test'i certifi CA dosyasının varlığını ve SSL doğrulama bağlamının açık olduğunu denetler. API anahtarı olmadan başlangıcı da kontrol eder. |
| Pencere testi | Build artık frozen EXE'yi `--smoke-ui` ile de açar. Geçici LOCALAPPDATA, çevrimdışı mod ve dört örnek kongreyle gerçek dashboard beklenir. Başarısızsa installer üretilmez; JSON ve güvenli loglar saklanır. |
| Çalışma dizini | Paket testleri kaynak kökü yerine build çalışma dizininden çalışır. Kaynak self-test farklı CWD'den ve stdout/stderr=None ile ayrıca geçti. |

Kaynak self-test'in geçmesi native DLL'lerin hedef VM'de yüklendiği anlamına gelmez. Sabit wheel'ler (`pythonnet 3.2.0`, `clr-loader 0.3.1`, `pywebview 6.2.1`, hooks-contrib 2026.8) yalnız inceleme için indirildi; Mac ortamına kurulmadı. Hook kaynakları DLL toplamayı destekliyor. PE import tablosunda ClrLoader.dll/Python.Runtime.dll bağımlılığı mscoree.dll, WebView2Loader.dll bağımlılığı KERNEL32.dll olarak görüldü. Bu nedenle kanıt olmadan Visual C++ Redistributable veya .NET Core kurdurulmadı. Kullanıcı üç temel DLL'nin varlığını doğruladı; Windows'un ilk yükleme hatasının kodu eski kayıtta bulunmuyor.

## AŞAMA KAYITLARI

Üst süreç: `application_starting`, `logging_initialized`, `app_data_directory_ready`, `configuration_loading/loaded`, `resources_resolving/resolved`, `instance_lock`, `webview_runtime_check`, `windows_runtime_files`, `netfx_runtime_loading/ready`, `database_backup`, `child_job_creation`, `backend_starting/ready`, `webview_import`, `ui_starting`, `ui_document_loaded`, `application_ready`.

Alt süreç: `socket_binding`, `application_import`, `application_creation`, `database_starting`; uygulama yaşam döngüsünde `database_initializing/initialized`, `analysis_recovery`, `ai_services_ready_without_credentials`. Başarısız aşama hata kaydında ayrı alan olarak tutulur. “Application ready” yerel sayfa verileriyle yüklendiğinde yazılır; API testi yapılmaz.

## TEST SONUÇLARI

- Genel Python koşusu, gerçek backend süreç/port testi etkin olarak: 188 test; **187 geçti**, yalnız native OCR opt-in kontrolü bu çalışma kapsamında atlandı.
- **21 JavaScript testi** geçti. Compileall başarılı.
- Kaynak masaüstü self-test **23 kontrol** geçti; Excel AHP sonuçları, yeni sertifika/kaynak/anahtarsız başlangıç kontrolleri dahil.
- 18 yeni test: erken log/fallback, çözülmüş yol, gizli metin filtreleme ve cause zinciri, eksik kaynak, anahtar deposu erişilemese bile yerel açılış, UTF-8, DB startup hatası, farklı CWD/konsolsuz self-test, ValueError kaydı, UI modül import hatası, runtime tespiti ve build çalışma dizini; açık .NET Framework seçimi, ilk hatanın korunması ve zorunlu DLL denetimi, kullanılmayan hatalı port ayarı ve açık uygulamada modal penceresiz test sonucu.
- Geliştirme sunucusu geçici kullanıcı/veritabanı dizininde `KONGRE_OFFLINE=1` ile başlatıldı. Tarayıcıda dört örnek kongre ve AHP dashboard'u açıldı. Üretim veritabanına dokunulmadı.
- **Yapılmayan:** yeni Windows EXE/installer üretimi, gerçek WebView2/CLR/Job Object testi ve kullanıcının temiz VM'sinde tekrar deneme. Bu Mac ortamında Windows için çapraz build yapılamaz.

## WINDOWS'TAN GEREKEN KAYIT

Gelen desktop_failed kaydı ve üç DLL'nin varlık kontrolü incelendi. Yeni sürümde de başlangıç başarısız olursa ilk .NET Framework hatasının sayısal kodu alt nedeni ayırmak için gereklidir. Önceki kayıtları koruyun. PowerShell'de aşağıdaki komut ilgili error.log dosyalarını açar (varsa):

```powershell
Get-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'AHP Congress Analyzer\logs\desktop\error.log') -Tail 5
Get-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'AHP Congress Analyzer\logs\error.log') -Tail 5
```

`desktop_failed`, `backend_failed`, varsa `application_startup_failed` kayıtları ve build klasöründeki `PACKAGE_SMOKE_TEST.json` içindeki ok/version alanları yeterlidir. API anahtarı, token, .env veya veritabanı göndermeyin. 1.9.2 erken log yolu başarısız olursa iletişim kutusunda gösterilen geçici error.log yolunu kullanın.

## YENİDEN BUILD VE TEMİZ VM TESTİ

Önkoşullar: `docs/WINDOWS_BUILD.md`. Windows x64/Python 3.12 x64 build bilgisayarında onaylı OCR, Inno Setup, WebView2 ve .NET hazır olmalıdır. Yeni UI build testi etkileşimli Windows masaüstü oturumu gerektirir.

```powershell
.\build_windows.bat --publisher "GERCEK YAYINCI ADI"
```

Başarılı olursa `release\1.9.2\AHP-Congress-Analyzer-Setup-1.9.2.exe`, `PACKAGE_SMOKE_TEST.json`, `UI_SMOKE_TEST.json` ve hash/manifest oluşur. Başarısız UI testi için `build\windows\ui-smoke.json` ve `ui-smoke.logs` klasörünü inceleyin. Paket EXE'yi tek başına `_internal` klasöründen ayırmayın; kullanıcıya Setup EXE gönderin.

Temiz VM'de önce yerel arayüzü API anahtarı girmeden açın. Sonra gerekiyorsa Gemini/Tavily/Jina ayarlarını kaydedip bağlantıyı test edin. Ana arayüz açılmıyorsa ilgili startup kaydı olmadan API ayarlarını değiştirmeyin.

## RESMÎ KAYNAKLAR

- [PyInstaller runtime kaynak yolları](https://pyinstaller.org/en/stable/runtime-information.html)
- [PyInstaller konsolsuz süreç ve multiprocessing kuralları](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)
- [Microsoft WebView2 dağıtımı ve runtime tespiti](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- [Microsoft .NET Framework Release denetimi](https://learn.microsoft.com/en-us/dotnet/framework/install/how-to-determine-which-versions-are-installed)
- [PyInstaller webview hook](https://github.com/pyinstaller/pyinstaller-hooks-contrib/blob/master/_pyinstaller_hooks_contrib/stdhooks/hook-webview.py), [CLR hook](https://github.com/pyinstaller/pyinstaller-hooks-contrib/blob/master/_pyinstaller_hooks_contrib/stdhooks/hook-clr.py)
