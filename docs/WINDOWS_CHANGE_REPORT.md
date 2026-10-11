# Dosya değişiklik raporu — Windows 1.8.0 hazırlığı

## Created Files

| Dosya | Amaç |
|---|---|
| `VERSION` | Tek uygulama SemVer kaynağı |
| `desktop_main.py` | Frozen multiprocessing uyumlu, konsolsuz giriş |
| `desktop/__init__.py` | Masaüstü modülü |
| `desktop/launcher.py` | WebView2 pencere, backend açılış/kapanış, menü ve maintenance komutları |
| `desktop/backend.py` | Dinamik loopback socket'ini sahiplenen ayrı Uvicorn process |
| `desktop/session.py` | Tek kullanımlık başlangıç token'ı, cookie, exact Host/Origin |
| `desktop/windows.py` | Windows mutex, Job Object ve native mesaj pencereleri |
| `desktop/logging_setup.py` | Hassas içerik içermeyen dönen loglar |
| `desktop/self_test.py` | Üretilen EXE içinden çalışacak izole offline smoke testi |
| `app/paths.py` | Read-only resource ve kullanıcı verisi yolları |
| `app/secret_store.py` | Windows Credential Manager + atomik non-secret JSON |
| `app/network.py` | Sistem proxy/TLS politikası, offline gate, bounded proxy stream adaptörü |
| `app/backup.py` | Tutarlı yedek, doğrulanmış ve eski veriyi koruyan restore |
| `app/windows_ocr.py` | Paket içi Tesseract 5 Türkçe/İngilizce offline OCR |
| `build_windows.bat` | Ayrı build venv'i ve tek komutlu Windows build |
| `packaging/windows/requirements-build.txt` | Paketleyici ve Windows runtime bağımlılıklarının sabit sürümleri |
| `packaging/windows/app.spec` | PyInstaller onedir kaynak allowlist'i ve Windows metadata |
| `packaging/windows/installer.iss` | Inno kurulum/upgrade/kısayol/uninstall/önkoşul tanımı |
| `packaging/windows/app.svg`, `app.ico` | Mevcut favicon geometrisinin Windows ikon sürümü |
| `tools/make_icon.py` | İkonun kaynak geometriden tekrar üretimi |
| `tools/prepare_ocr.py` | BT onaylı OCR girdilerini seçip SHA256 kilidi oluşturma |
| `tools/build_windows.py` | Doğrulama → frozen build → smoke → isteğe bağlı imza → installer → manifest/hash/lisans |
| `tools/create_build_kit.py` | Kullanıcı verisi/credential içermeyen açık allowlist ile kaynak ZIP |
| `tests/test_desktop.py` | Masaüstü güvenlik/veri/ağ/paket sözleşmesi ve süreç testleri |
| `IT_DEPLOYMENT_NOTES.md` | IT için gerçek dosya/ağ/izin/uninstall/restore davranışı |
| `THIRD_PARTY_NOTICES.md` | Bağımlılık lisansları ve vendor onay sınırı |
| `CHANGELOG.md` | 1.8.0 değişiklikleri ve Windows test durumu |
| `docs/WINDOWS_ARCHITECTURE.md` | A–J mimari inceleme ve teknik kararlar |
| `docs/WINDOWS_BUILD.md` | Tam build, OCR hazırlığı, signing ve release adımları |
| `docs/WINDOWS_ACCEPTANCE.md` | Temiz Windows test listesi; bekleyen kontroller |
| `docs/WINDOWS_VERIFICATION.md` | Gerçekleşen testler, sayılar ve doğrulama sınırları |
| `docs/WINDOWS_README.txt` | Son kullanıcı release notu |
| `docs/WINDOWS_CHANGE_REPORT.md` | Bu dosya raporu |
| `release/STATUS.txt` | Installer'ın henüz üretilmediğini açıklar |
| `release/AHP-Congress-Analyzer-Windows-Build-Kit-1.8.0.zip` | Windows ortamında build alınacak kaynak teslimi; installer değildir |
| `release/SOURCE_SHA256.txt` | Yalnız kaynak ZIP bütünlük özeti; installer hash'i değildir |

## Modified Files

| Dosya | Değişiklik |
|---|---|
| `app/config.py` | VERSION/resource/data ayrımı; frozen release'te `.env` ve dev DB override'ı okunmaz |
| `app/ai_settings.py` | Windows güvenli depoya yönlendirme; dev `.env` ve API sözleşmesi korunur |
| `app/ai_provider.py` | Kurumsal proxy/TLS adaptörü; offline/policy hatası anlaşılır mesajla ve retriesiz döner |
| `app/search.py` | Jina/Tavily için aynı proxy/TLS politikası |
| `app/sources.py` | Web kaynakları/ortak logo bağlantısında proxy adaptörü, offline DNS engeli, platform bağımsız OCR açıklaması |
| `app/database.py` | Migration öncesi yedek ve SQLite snapshot bağlantılarının açıkça kapatılması |
| `app/main.py` | Opsiyonel desktop session middleware, VERSION'dan health/footer, güvenli hata logu |
| `app/pdf_report.py` | Windows font dizininde WINDIR kullanımı |
| `app/image_ocr.py` | Windows OCR yönlendirmesi; mevcut Mac Vision yolu korunur |
| `static/app.js`, `static/ai.js` | OCR açıklamalarında “bu bilgisayarda” ifadesi |
| `static/index.html` | VERSION'dan doldurulan footer |
| `audit_ahp.py` | Excel kaynağı sabit kişisel dizin yerine CLI argümanı; raporda yalnız dosya adı |
| `analiz/hesaplama_sonuclari.json` | Kaynak workbook'un kişisel mutlak yolunu dosya adına indirme; sayısal değerler değişmedi |
| `README.md` | Windows build/release/data/backup/restore/troubleshooting yönlendirmeleri; geliştirme ayrımı |
| `.gitignore` | Build, dist, release, vendor, log, binary ve imza anahtarı çıktılarının hariç tutulması |

## Removed Files

Yok. Mevcut iş mantığı ve özellik kaldırılmadı. `engine.py`, AHP kriter/ağırlık/uygunluk eşikleri ve DB modelleri değiştirilmedi. Veri dosyaları kaynak/build paketine alınmadı; mevcut veritabanı silinmedi veya yeniden oluşturulmadı.

## Build özeti

Windows x64 + Python 3.12 + BT onaylı Inno Setup/WebView2/.NET + kilitlenmiş OCR girdisi hazırlandıktan sonra:

```bat
build_windows.bat --publisher "GERCEK YAYINCI ADI"
```

Tam önkoşullar, OCR hazırlama komutu, imza seçenekleri ve gerçek release dosya listesi `docs/WINDOWS_BUILD.md` içindedir. Bu kaynak teslimi, Windows EXE'nin derlendiği/kurulduğu anlamına gelmez.


## 1.9.0 ek değişiklikler

- Yeni: `app/database_connection.py`, `static/database.js`, `tests/test_database_connection.py`.
- Güncellenenler: `app/main.py`, `app/ai_service.py`, `server.py`, `desktop/launcher.py`, `desktop/self_test.py`, arayüz yönlendirmesi/menüsü/stilleri, uyumluluk testleri, VERSION ve kullanım/build belgeleri.
- Son kaynak teslimi: `AHP-Congress-Analyzer-Windows-Build-Kit-1.9.0.zip`. AHP hesabı ve şema 7 korundu; gerçek Windows kurulum doğrulaması bekliyor.

## 1.9.1 bağlantı düzeltmesi

AutoDetect/PAC ön kontrolü kaldırıldı; gerçek proxy adresi varsa kullanılır, yoksa gerçek API isteği yapılır. Yeni `app/connection_errors.py` ve `app/connection_probe.py` ile HTTP/SSL/DNS/proxy hataları ayrılır ve Gemini bağlantısı kongre verisi göndermeden test edilir. Arama testi kayıtlı servisi kullanır, henüz kaydedilmemiş seçimler test edilmez. `desktop/logging_setup.py` güvenli exception zinciri/kod/HTTP durumu kaydeder; paket self-test'i üç servis adaptörünü kapsar. Tam dosya listesi ve doğrulama: `docs/NETWORK_FIX_1.9.1.md`.

Kaynak teslimi: `AHP-Congress-Analyzer-Windows-Build-Kit-1.9.1.zip`. Mevcut kurulu EXE bu yeni kaynaklardan yeniden build edilmelidir; AHP hesabı ve şema 7 korunur.

## 1.9.2 Windows başlangıç düzeltmesi

- Yeni `desktop/runtime.py`: açık .NET Framework yüklemesi ve altı paket DLL'sinin denetimi.
- Yeni `desktop/startup.py`: erken log, aşamalar, kaynak dosyası denetimi ve gerçek veri/log yolu.
- `desktop_main.py`, `desktop/launcher.py`, `desktop/backend.py`: import/başlangıç/temizleme hatalarının korunması; NetFx önkoşulu; izole gerçek UI smoke testi ve rapor/log kopyası.
- `desktop/logging_setup.py`, `desktop/windows.py`: güvenli tam exception zinciri, yapısal açıklama ve Windows sayısal hata kodları; özgün hata temizleme sırasında kaybolmaz.
- `app/main.py`, `app/paths.py`, `app/secret_store.py`, `app/services.py`, `app/config.py`: DB başlangıç hatasının kaydı, mutlak yollar, yalnız anahtar gerektiğinde Credential Manager yükleme, UTF-8 başlangıç JSON'u; masaüstünün kullanmadığı geliştirme portunu yok sayma.
- `desktop/self_test.py`: kaynak/sertifika/anahtarsız açılış kontrolleri ve güvenli hata raporu.
- `packaging/windows/app.spec`, `tools/build_windows.py`: açık CLR/WebView DLL toplaması, dosya denetimi, farklı CWD ve iki zorunlu frozen test; UI başarısızsa installer yok.
- Yeni `tests/test_startup.py`, `docs/STARTUP_AUDIT_1.9.2.md`; VERSION, release durum ve kullanım/build belgeleri güncellendi.

Kaynak teslimi: `AHP-Congress-Analyzer-Windows-Build-Kit-1.9.2.zip`. Gerçek Windows binary bu Mac ortamında üretilmedi. Üç temel DLL'nin kullanıcı makinesinde bulunduğu doğrulandı; ilk NetFx hatasının nedenini eski log açıklamıyor. AHP hesabı, ağırlıklar, eşikler ve şema 7 değişmedi.
