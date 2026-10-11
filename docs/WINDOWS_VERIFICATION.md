# Gerçekleşen doğrulamalar — 4 Ekim 2026

Ortam: macOS 26.2 arm64, Python 3.12.14. Erişilebilir Windows makinesi/CI yok; kullanıcı da Windows ortamı olmadığını belirtti. Bu nedenle Windows binary, WebView2/Credential Manager/Job Object, gerçek Tesseract Windows runtime ve installer testleri **bekliyor**.

## Geçen kontroller

- Mevcut 135 Python testinin 134'ü geçti; macOS native OCR testi opt-in olduğu için atlandı.
- Yeni masaüstü test dosyasında 13 birim/entegrasyon testi geçti: kullanıcı yolları, güvenli ayar adaptörü ve secret sızıntısı, oturum/cookie/Host/Origin, migration yedeği, restore/bozuk-yeni schema koruması, offline ve proxy/PAC sınırı, hassas veri içermeyen loglar/rotation, Windows OCR komut/sözleşme testi, OCR manifest hash kontrolü ve paket özel dosya kontrolü.
- Ek socket/process testi izinli olarak gerçek ayrı backend process ile çalıştırıldı: dinamik 127.0.0.1 portu, cookiesiz erişime 403, oturum açılınca erişim ve kapanıştan sonra portun kapanması doğrulandı. Bu test Mac'te yapıldı; Windows Job Object doğrulaması değildir.
- Toplam **148 Python testi geçti** (genel koşudaki 149 testten biri ayrı process koşusunda tamamlandı, yalnız native OCR atlandı).
- **18 JavaScript testi geçti**: uygunluk sınıfları, karşılaştırma, profil/öneriler, logo ve escape kontrolleri.
- Masaüstü `--self-test` kaynak modunda **16 kontrol geçti**: sürüm, yedi statik kaynak, Excel AHP sonuçları, SQLite yazma/AHP, sahte sağlayıcıyla offline AI iş akışı, Türkçe PDF export, PDF import, yeniden açılışta kalıcılık, backup/restore ve offline ağ engeli. Frozen EXE'de Windows OCR kontrolü de çalışacak; burada gerçek Windows OCR çalıştırılmadı.
- Python compileall ve JavaScript sözdizimi/test kontrolleri başarılı.
- Mevcut kullanıcı veritabanının yükseltme öncesi yedeği alındı. Geliştirme sunucusu 1.8.0 ile 127.0.0.1:8765'te açıldı; health `ok`, schema 7. Yeniden başlatma öncesi/sonrası SQL logical dump SHA256 eşleşti: **kayıt içerikleri değişmedi**.

## Komutlar

```sh
.venv/bin/python -m unittest -q test_app tests.test_api tests.test_ai tests.test_providers tests.test_ahp_flow tests.test_policy tests.test_trash tests.test_extensions tests.test_retry tests.test_batches tests.test_classification tests.test_intelligence tests.test_logos tests.test_desktop
RUN_DESKTOP_PROCESS_TEST=1 .venv/bin/python -m unittest -v tests.test_desktop.BackendProcessTests
node --test tests/test_logos.cjs tests/test_intelligence.cjs tests/test_classification.cjs tests/test_compare.cjs
.venv/bin/python desktop_main.py --self-test tmp/desktop-smoke.json
.venv/bin/python -m compileall -q app desktop tools desktop_main.py
```

TestClient, kullanılan mevcut Starlette sürümünden httpx2 geçişine dair bir deprecation uyarısı üretiyor. Testler başarılı; packaging görevi sırasında transport iş mantığını etkileyebilecek ayrı bağımlılık geçişi yapılmadı.

## Yapılmayan / yapılmış gibi sayılmayan kontroller

- Windows EXE ve installer derlemesi; final installer SHA256 ve Authenticode imzası.
- Temiz Windows install/first launch/upgrade/uninstall/reinstall/reboot.
- Gerçek Windows Credential Manager, .NET/WebView2, dosya indirme/seçici ve Job Object.
- Gerçek Windows Tesseract/dil modelleri ve tüm vendor DLL'lerin temiz makinede çözümlenmesi.
- Kurum proxy/PAC/SSPI/sertifika/AV/EDR izinleri.
- Gerçek sağlayıcı hesaplarıyla yeni ücretli AI/search isteği; testlerde fake/mocked sağlayıcı kullanıldı.

Windows kabul listesi: `docs/WINDOWS_ACCEPTANCE.md`. Windows build başarısı tek başına installer kabulü değildir. `release/STATUS.txt` ve kaynak build kit'i bu sınırı açıkça belirtir; `.exe` veya installer SHA256 uydurulmamıştır.


## 1.9.0 SQLite bağlantısı — 5 Ekim 2026

- Genel koşuda 160 Python testi: 158 geçti, 2 opt-in test atlandı. Masaüstü process testi ayrıca izinli ortamda geçti: toplam 159 benzersiz Python testi geçti, yalnız native OCR opt-in kontrolü atlandı.
- 11 yeni veritabanı bağlantı testi: dosya önizleme/çalışma kopyası, kaynak ve önceki DB'nin korunması, yeniden başlatma, `.db` indirme, bozuk/uyumsuz/yeni şema, trigger/kolon kontrolü, hatalı AHP verisi, onay ve süre sınırı, eski sekme yazma engeli, süren AI analizi, disk/bağlantı dosyası yazma hatasında eski bağlantıyı koruma.
- 18 JavaScript testi ve Python compileall geçti. Kaynak modunda masaüstü self-test 1.9.0 ile 17 kontrolü geçti; `/database.js` paket kaynağı da denetlendi.
- Mac in-app browser ile izole test DB'sinde gerçek dosya seçme → 5 kaydı önizleme → onay → bağlanma → kongre listesinin açılması doğrulandı. İndirilen `.db` dosyasına SQLite integrity check yapıldı ve 5 test kaydı doğrulandı.
- Kullanıcının mevcut yedeği ayrı geçici veritabanında bağlantı önizlemesinden geçti. Çalışan uygulama 1.9.0/schema 7 olarak açıldı. Öncesi/sonrası SQL dump SHA256 eşleşti; gerçek kayıtlar değiştirilmedi.
- Windows native dosya seçici/WebView2 indirmesi, EXE ve installer kabulü halen Windows ortamında yapılmalıdır.

Ek komut:

```sh
.venv/bin/python -m unittest -q tests.test_database_connection
```

## 1.9.1 bağlantı testleri — 6 Ekim 2026

Kullanıcı başka Windows bilgisayarında 1.9.0 proxy yanlış pozitifini bildirdi. Bu düzeltmenin kaynak testleri Mac üzerinde yapıldı; asistan hedef Windows'a erişmedi.

- Genel Python koşusu: 170 test, 168 geçti, 2 koşullu test atlandı. Masaüstü backend süreç testi ayrıca çalıştırılıp geçti: 169 benzersiz test doğrulandı, yalnız native OCR bu çalışmada atlandı.
- 21 JavaScript testi, Python compileall, kaynak modunda 20 masaüstü self-test kontrolü geçti.
- Gemini/Tavily/Jina başarı, 401/403/429/407, SSL/DNS/timeout/ConnectionError/ProxyError/unknown senaryoları HTTPX MockTransport ile çalıştırıldı. Gerçek hesap veya ücretli dış istek kullanılmadı.
- Geçici DB/ayarlarla tarayıcıda kayıtlı servis, kaydetmeden testin engellenmesi, kaydetme ve servis adıyla hata akışı doğrulandı.
- AHP şeması 7 ve hesap kuralları değişmedi. Windows EXE build, WebView2 UI ve gerçek hedef ağdaki canlı bağlantı sonucu henüz doğrulanmadı.

Yeni testler: `tests/test_connection_tests.py`, `tests/test_connection_settings.cjs`. Tam rapor: `docs/NETWORK_FIX_1.9.1.md`.

```sh
.venv/bin/python -m unittest -q test_app tests.test_api tests.test_ai tests.test_providers tests.test_ahp_flow tests.test_policy tests.test_trash tests.test_extensions tests.test_retry tests.test_batches tests.test_classification tests.test_intelligence tests.test_logos tests.test_desktop tests.test_database_connection tests.test_connection_tests
RUN_DESKTOP_PROCESS_TEST=1 .venv/bin/python -m unittest -q tests.test_desktop.BackendProcessTests
node --test tests/test_*.cjs
.venv/bin/python desktop_main.py --self-test tmp/network-desktop-smoke.json
```

1.9.1 yerel sunucu sağlık kontrolü: `ok`, schema 7. Yeniden açılış öncesi SQLite yedeği alındı; tablo içerikleri yedekle karşılaştırıldı. Kongreler, değerlendirmeler, profil, modeller ve AI geçmişi aynı kaldı. Sayfa açılışında yalnız üç logo önbelleğinin `updated_at` alanı normal logo kontrolüyle yenilendi; logo içerikleri aynı.

## 1.9.2 Windows başlangıç incelemesi — 8 Ekim 2026

Kullanıcının Windows logu `winforms.py:17` → pythonnet → CoreCLR yükleme hatası gösterdi. İndirilen sabit wheel kaynaklarında ilk CLR hatasının pywebview tarafından gizlendiği doğrulandı. Kullanıcı ClrLoader.dll / Python.Runtime.dll / WebView2Loader.dll varlığı için üç `True` sonucu sağladı. İlk .NET Framework yüklemesinin alt nedeni eski logda yok; yeni sürümün hedef Windows'ta açıldığı henüz doğrulanmadı.

- Genel koşu, gerçek backend süreç/port testi etkin olarak: 188 Python testi; 187 geçti, yalnız native OCR opt-in kontrolü atlandı.
- 18 yeni başlangıç testi: erken/fallback log, kaynak/yol, secretsiz tam cause/frame zinciri, anahtarsız yerel açılış, UTF-8, DB hata aşaması, farklı CWD/konsolsuz self-test, UI import başarısızlığı, açık NetFx seçimi ve ilk hatanın korunması, DLL denetimi, önkoşul tespiti, build CWD, hatalı kullanılmayan port ve açık uygulamada modal penceresiz hata.
- 21 JavaScript testi ve compileall başarılı. Kaynak self-test 1.9.2 ile 23 kontrol geçti.
- İzole LOCALAPPDATA/veritabanıyla `KONGRE_OFFLINE=1` geliştirme sunucusu tarayıcıda açıldı; dört örnek kongre ve Excel AHP sonuçları görüldü. Üretim veritabanına dokunulmadı.
- Yeni gerçek Windows UI testi build aracına eklendi ancak Mac'te çalıştırılmış gibi sayılmaz. EXE/installer/CLR/WebView2 ve hedef VM sonucu bekliyor. Canlı ücretli API testi yapılmadı.

Komutlar:

```sh
RUN_DESKTOP_PROCESS_TEST=1 .venv/bin/python -m unittest -q test_app tests.test_api tests.test_ai tests.test_providers tests.test_ahp_flow tests.test_policy tests.test_trash tests.test_extensions tests.test_retry tests.test_batches tests.test_classification tests.test_intelligence tests.test_logos tests.test_desktop tests.test_database_connection tests.test_connection_tests tests.test_startup
node --test tests/test_*.cjs
.venv/bin/python desktop_main.py --self-test tmp/startup-desktop-smoke.json
.venv/bin/python -m compileall -q app desktop tools desktop_main.py tests/test_startup.py
```

Detaylı inceleme: `docs/STARTUP_AUDIT_1.9.2.md`.


## 1.10.0 otomatik AI geçişi — 10 Ekim 2026

- 202 benzersiz Python testi geçti: tests/ koşusunda 185, kök AHP testlerinde 16,
  ayrıca gerçek backend süreç/port kontrolünde 1. Native OCR opt-in testi atlandı.
- 24 JavaScript testi ve compileall geçti. Kaynak modunda masaüstü self-test
  1.10.0 ile 24 kontrolü geçti; ai_failover_checkpoint_fixture dahil.
- Gemini 429 → Groq başarısı gerçek adaptörler ve sahte HTTP ile tarayıcıda
  doğrulandı. Sağlayıcı sırası, katkı veren model, kota hatası ve tamamlanmış
  AHP raporu görünür; konsol hatası yok. Gerçek anahtar/kota kullanılmadı.
- Birden çok API'de kota hatası, yarım çıktı, token nedeniyle bölme, kalıcı parça
  kaydı, uygulama yeniden açılınca devam ve istek bütçesi sınırı test edildi.
- AHP motoru, ağırlıklar, eşikler ve DB şeması değişmedi.
- Windows EXE/Setup üretimi, WebView2 ve hedef Windows'ta canlı servis testi
  bekliyor. Ayrıntılar: [AI geçiş raporu](AI_FAILOVER_1.10.0.md).
