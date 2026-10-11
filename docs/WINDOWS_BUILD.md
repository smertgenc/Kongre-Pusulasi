# Windows build ve release üretimi

Bu hazırlık **build bilgisayarına** yöneliktir. Son kullanıcı Python, pip, terminal, Tesseract veya proje bağımlılığı kurmaz. Mevcut macOS ortamında Windows EXE üretilemez; PyInstaller çapraz derleyici değildir. Bu kaynak tesliminde Windows installer veya ona ait SHA256 dosyası üretilmiş gibi gösterilmez.

## 1. Build bilgisayarı

BT onaylı Windows x64 ortamında, oturum açılmış etkileşimli masaüstünde (UI testi pencere açar):

1. Python 3.12 x64 (geliştirme referansı 3.12.14).
2. Inno Setup 6.3 veya üzeri; sürüm/lisans uygunluğunu BT doğrulasın. `ISCC.exe` yolunu gerekirse `--iscc` ile belirtin. Inno 7 lisans/sürüm geçişi otomatik yapılmaz.
3. .NET Framework 4.6.2+ ve bilgisayar genelinde WebView2 Evergreen Runtime.
4. Türkçe/İngilizce OCR için BT onaylı **Tesseract 5 x64** dağıtımı, tüm gereken DLL'leri, `eng.traineddata`, `tur.traineddata`, bileşenlerinin lisans metinleri. [Tesseract resmi kurulum belgesindeki Windows dağıtımları](https://tesseract-ocr.github.io/tessdoc/Installation.html) kullanılabilir; internetten rastgele executable almayın.
5. Kaynak proje: `app`, `static`, `engine.py`, `analiz/hesaplama_sonuclari.json`, `desktop`, `desktop_main.py`, `packaging`, `tools`, VERSION, requirements ve belgeler. **`.env`, data, tmp, outputs, .venv ve kişisel ekler dağıtıma taşınmaz.**

Bir kez OCR çalışma zamanı hazırlığı:

```bat
py -3.12 tools\prepare_ocr.py --source "C:\BT-Onayli\Tesseract-OCR" --licenses "C:\BT-Onayli\OCR-Lisanslari" --version "5.5.0" --provenance "https://github.com/UB-Mannheim/tesseract/wiki"
```

`--version` örnektir; onaylanan dağıtımın gerçek sürümünü yazın. Lisans klasörü yalnız Tesseract'ı değil Leptonica, dil modelleri ve dahil DLL'lerin gerekli metinlerini de içermelidir. Script yalnız `tesseract.exe`, üst dizindeki DLL'ler, iki dil dosyası ve lisansları alır; ek eğitim programlarını/installer'ı almaz. `vendor/ocr/ocr-lock.json` gerçek dosya SHA256 listesini ve kaynağını saklar. Bu dosyayı BT onay kaydıyla birlikte arşivleyin. Sonraki buildlerde aynı OCR paketini kullanın. Paket üzerinde değişiklik varsa build durur. Dil modelleri runtime'da indirilmez.

## 2. Tek komutla build

Proje kökünde normal Windows Command Prompt:

```bat
build_windows.bat --publisher "ONAYLANMIS GERCEK YAYINCI ADI" --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Yayıncı örnek metnini gerçek yayıncıyla değiştirin; otomatik hayali yayıncı kullanılmaz. Build admin yetkisi istemez. Kurulum ise Program Files'a yazacağı için BT yetkisi ister. Script PowerShell ya da execution-policy bypass kullanmaz.

İşlem sırası:

1. Ayrı `.venv-build` oluşturulur; `packaging/windows/requirements-build.txt` ve mevcut requirements sabit sürümleri yüklenir. `pip check` çalışır.
2. Windows x64/Python sürümü, SemVer, Inno yolu ve OCR kilit hash'leri kontrol edilir.
3. Yalnız üretilmiş `dist/AHP-Congress-Analyzer` temizlenir. Kullanıcı verisi ve kaynaklar silinmez.
4. PyInstaller onedir ve metadata/ikon oluşturulur; UPX/onefile yok.
5. Paket dosya listesi `.env`, database, key container ve log sızıntısına karşı kontrol edilir. CLR/WebView için altı zorunlu DLL’nin paket yolu denetlenir.
6. **Üretilen EXE** `--self-test` ile geçici veritabanında AHP, PDF, persistence, backup/restore, offline gate, Gemini/Tavily/Jina HTTP adaptörlerini sahte transport ile ve gerçek Windows OCR testini çalıştırır. Canlı AI anahtarı kullanılmaz. Başarısızsa installer üretilmez.
7. **Üretilen EXE** `--smoke-ui` ile boş/geçici LOCALAPPDATA ve offline modda gerçek WebView2 penceresini açar. Anahtarsız dashboard ve dört örnek kongre beklenir; başarısızsa installer üretilmez. Testler kaynak kökünden farklı çalışma dizininde çalışır.
8. İstenmişse ana EXE imzalanır ve doğrulanır.
9. Inno installer oluşturur; imza parametreleri varsa installer ve uninstaller imzalanır.
10. Gerçek installer SHA256, dependency/build inventory, her kurulu dosyanın hash'i, OCR manifesti, lisanslar ve belgeler release dizinine konur.

Çıktı:

```text
release/1.10.0/
  AHP-Congress-Analyzer-Setup-1.10.0.exe
  SHA256.txt
  README.txt
  IT_DEPLOYMENT_NOTES.md
  CHANGELOG.md
  VERSION
  BUILD_MANIFEST.json
  OCR_COMPONENTS.json
  PACKAGE_SMOKE_TEST.json
  UI_SMOKE_TEST.json
  THIRD_PARTY_NOTICES.md
  THIRD_PARTY_LICENSES/
```

Aynı sürümün release klasörü varsa build üzerine yazmaz. Sürümü artırın veya önceki/başarısız çıktıyı ayrı arşivleyin. `BUILD_MANIFEST.json` gerçekleşen Python/paket sürümlerini kaydeder. Tam byte-for-byte reproducible binary garantisi verilmez; Python/Inno/toolchain, Windows SDK, OCR kilidi ve imza zaman damgası ayrıca sabitlenmelidir. Build interneti kısıtlıysa BT onaylı pip index/wheelhouse için standart `PIP_INDEX_URL` veya `PIP_NO_INDEX`/`PIP_FIND_LINKS` politikası kullanılabilir; anahtarları komut satırına koymayın.

## 3. Optional: Authenticode Code Signing

Kod imzalama sertifikası olmadığı varsayılır. Sertifikanın özel anahtarını repo veya PFX parametresiyle taşımayın. BT Windows sertifika deposunu/erişim yetkisini sağlar:

```bat
build_windows.bat --publisher "GERCEK YAYINCI" --sign-thumbprint "SERTIFIKANIN_40_HEX_SHA1_KIMLIGI" --signtool "C:\OnayliSDK\signtool.exe" --timestamp-url "https://BT-ONAYLI-ZAMAN-DAMGASI"
```

Değerler yer tutucudur; gerçek sertifika ve hizmet bilgileri gerekir. SHA1 burada sertifika seçme kimliğidir; dosya ve timestamp digest'i SHA256 kullanır. Kimlik/URL verilmezse imzasız build çalışır. Son hash imzalamadan sonra oluşturulur. İmzalama hatası build'i durdurur.

## 4. Paket testinden sonra gerçek kabul testi

`docs/WINDOWS_ACCEPTANCE.md` listesini **Python bulunmayan ayrı, temiz Windows bilgisayarında/VM'de** uygulayın. Build testleri; installer, UAC, firewall/EDR, kurumsal proxy, hedef bilgisayardaki WebView2 davranışı veya canlı AI kotasının kanıtı değildir. Bunlar yapılmadan BT dağıtımını tamamlandı saymayın.

Build otomatik UI testini çalıştırır. Aynı testi tekrar çalıştırmak için uygulama kapalıyken:

```bat
"dist\AHP-Congress-Analyzer\AHP-Congress-Analyzer.exe" --smoke-ui "%TEMP%\ahp-ui-smoke.json"
```

Bu komut izole geçici kullanıcı dizini ve offline mod kullanır; mevcut kullanıcı kayıtlarını/anahtarlarını okumaz. WebView dashboard verilerinin yüklenmesini kontrol edip pencereyi kapatır. Sonuç JSON dosyasına, tanılama kayıtları yanındaki `.logs` klasörüne yazılır. Normal kullanıcı akışları ayrıca test edilmelidir. Build sırasında hata olursa `build/windows/ui-smoke.json` ve `ui-smoke.logs` klasörüne bakın.

## 5. Geliştirme sürümü

Mevcut `python server.py --open` ve Mac `Baslat.command` kalır. Geliştirme `.env` ve `data/kongre.db` kullanmaya devam eder. Masaüstü modu `%LOCALAPPDATA%` ve Credential Manager kullanır. EXE içindeki `VERSION` tek sürüm kaynağıdır; health ve HTML footer bu dosyadan gelir. Büyük bir sürüm güncellemesinde DB migration ve yükseltme testini ayrıca ele alın; yalnız sürüm numarasını değiştirmek yeterli değildir.

## 1.9.1 bağlantı düzeltmesini dağıtma

Kurulu EXE içindeki Python kodları da değiştiği için tam build gerekir. Mevcut onaylı OCR ve imza girdilerini koruyarak 1.9.1 kaynaklarından yeniden üretin. Kullanıcı verisini yedekleyip uygulamayı kapattıktan sonra yeni Setup EXE ile yükseltin. Kayıtlı ayarlar ve Credential Manager anahtarları korunur. Son test: Gemini, Tavily ve Jina ayarlarını sırayla kaydedip bağlantıyı test edin; gösterilen servis adı ve sonucu kontrol edin. Bkz. `docs/NETWORK_FIX_1.9.1.md`.

## 1.9.2 başlangıç düzeltmesini dağıtma

1.9.2 kaynaklarından tam build alın; önceki kurulu EXE yeni başlatıcıyı içermez. Onaylı OCR girdilerini aynı şekilde hazırlayın. Başarılı iki frozen testten sonra oluşan Setup EXE ile yükseltin; kullanıcı verisi ve API anahtarları korunur. Temiz VM'de API anahtarı girmeden ilk açılışı doğrulayın. Üç temel DLL'nin eski kurulumda bulunması doğrulandı; ilk .NET Framework yükleme hatasının alt nedeni eski logda olmadığından yeni VM sonucu gereklidir. Detay: `docs/STARTUP_AUDIT_1.9.2.md`.
