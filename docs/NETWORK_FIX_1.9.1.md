# Bağlantı testleri düzeltmesi — 1.9.1

Tarih: 6 Ekim 2026. Kapsam: AI ve web arama bağlantı testleri, hata sınıflandırması, güvenli tanılama ve Windows kaynak paketi.

## Kök neden

Eski `app/network.py`, `WinHttpGetIEProxyConfigForCurrentUser` ile Windows kullanıcısının `fAutoDetect` veya PAC URL ayarını okuyordu. Gerçek bir statik/ortam proxy adresi bulunmadığı halde bu bayraklardan biri varsa `proxy_for()` **API isteğinden önce** “Bu ağ otomatik proxy kullanıyor…” hatasını üretiyordu. Bayrak, o hedef için bir proxy bulunduğunu veya proxy kullanılması gerektiğini kanıtlamaz. Bu nedenle doğrudan erişebilen Windows bilgisayarlarında yanlış pozitif oluşabiliyordu.

Bu mesaj geniş bir `except Exception` bloğundan gelmiyordu; ön kontrol doğrudan üretiyordu. Bunun yanında `app/ai_provider.py` ve `app/search.py` bazı SSL, DNS ve bağlantı hatalarını aynı genel mesaj altında topluyordu. `static/ai.js`, arama testi için kaydedilmiş tercih yerine o an dropdown'daki değeri gönderiyor; `app/main.py` de gönderilen değeri test ediyordu. Kayıtlı Tavily / seçili Jina tutarsızlığının nedeni buydu.

WinHTTP'nin “Direct access” çıktısı ve ortam değişkenlerinin boş olması bu yanlış ön kontrolü engellemiyordu. TCP 443 erişiminin başarılı olması ise tek başına API anahtarı, TLS veya servis kotasının geçerli olduğunu göstermez.

## Yeni davranış

- AutoDetect/PAC bayrağına dayanarak isteği durduran kontrol kaldırıldı. Gerçek proxy adresi yoksa API'ye doğrudan istek yapılır; işletim sistemi ayarları değiştirilmez.
- `urllib.request.getproxies()` ile `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` ve işletim sisteminin statik proxy ayarları okunur. `NO_PROXY`/bypass korunur. Açıkça tanımlı proxy üzerinden başarısız olan istek doğrudan ağa geçirilmez.
- HTTPX'e proxy ve doğrulanan SSL bağlamı açıkça aktarılır. `trust_env=False`, ortam proxy ayarlarını yok saymak için değil, zaten çözümlenmiş ayarların ikinci kez uygulanmasını engellemek için kullanılır. `SSL_CERT_FILE`, `SSL_CERT_DIR` ve sistem sertifika kökleri korunur; `verify=False` kullanılmaz.
- PAC/WPAD betikleri ve SSPI oturum açma uygulanmış değildir. Yalnız otomatik algılama ayarının açık olması proxy hatası sayılmaz. Gerçekten PAC/SSPI gerektiren bir ağda BT'nin desteklenen erişim ayarını sağlaması gerekebilir; gerçek isteğin hatası gösterilir.
- Projede API istekleri için `requests`/`RequestException` kullanılmıyor. AI ve arama HTTPX kullanıyor. Genel web kaynakları mevcut IP/redirect denetimli HTTP istemcisini ve gerektiğinde HTTPX proxy adaptörünü kullanmaya devam ediyor.
- Genel exception blokları artık ortak sınıflandırıcıya başvurur. Proxy sınıfı yalnız `httpx.ProxyError` veya HTTP 407 için kullanılır; hata metninde “proxy” kelimesi bulunması yeterli değildir. Bilinmeyen hata güvenli teknik tanılamayla loglanır.

## Ayrı gerçek servis istekleri

| Servis | Test isteği |
|---|---|
| Gemini | Kayıtlı model ile `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`, kısa bir yanıt isteği |
| Tavily | `api.tavily.com/search`, küçük örnek arama |
| Jina AI Search | `s.jina.ai`, küçük örnek arama |

AI testinde kongre verisi gönderilmez. Anahtarın yalnız kayıtlı olması başarı sayılmaz. AI testi otomatik tekrarlanmaz. Arama testinde yanıtın okunabilir kaynak içerdiği de doğrulanır. Servis ücret/kotası uygulanabilir.

| Durum | Kullanıcı mesajı (servis adı ayrıca gösterilir) |
|---|---|
| Başarılı | Bağlantı başarılı |
| 401 | API anahtarı geçersiz veya yetkilendirme başarısız. |
| 403 | API erişimi reddedildi. API anahtarının yetkilerini kontrol edin. |
| 429 | API kota/rate limit sınırına ulaşıldı. |
| Zaman aşımı | API bağlantısı zaman aşımına uğradı. |
| SSL/CertificateError | SSL sertifika doğrulama hatası. |
| DNS/NameResolution | Servis adresi çözümlenemedi. |
| Bağlantı hatası | API sunucusuna bağlantı kurulamadı. |
| ProxyError / 407 | Proxy üzerinden API bağlantısı kurulamadı. |
| Bilinmeyen | Genel bir bağlantı hatası oluştu. Teknik ayrıntılar log dosyasına kaydedildi. |

Gemini'nin hatalı anahtar için döndürdüğü bazı HTTP 400 yanıtları da yetkilendirme hatasıdır. 404/model erişimi, 413/boyut sınırı ve 5xx/hizmet hataları kendi sınıflarında kalır. SSL/DNS nedenleri HTTPX'in iç içe exception zincirinden okunur. HTTP 403 proxy hatası sayılmaz.

## Kaydedilmiş servis ve arayüz

Önce AI/arama servisini seçip **ayarları kaydedin**, sonra bağlantı testini çalıştırın. Kaydedilmemiş sağlayıcı, model veya anahtar değişikliği varsa ilgili test düğmesi devre dışı kalır. Kayıtlı servis ve “Test edilen servis: Tavily / Jina AI Search / Gemini” açıkça gösterilir. Sunucu kayıtlı ayarların anlık kopyasını kullanır; başka sekmede değiştirilmiş bir ayarı eski sekme test etmeye çalışırsa 409 ile yeniden kaydetme ister. Yeni girilen anahtar test isteği gövdesinde taşınmaz.

## Etkilenen dosyalar

| Dosya | İşlev |
|---|---|
| `app/network.py` | Yanlış PAC ön kontrolünün kaldırılması, proxy/TLS davranışı |
| `app/connection_errors.py` | Yeni ortak HTTP/transport hata sınıflandırıcısı |
| `app/connection_probe.py` | Yeni küçük gerçek AI API testi |
| `app/ai_provider.py`, `app/search.py` | Ayrı hata nedenlerinin korunması |
| `app/ai_schemas.py`, `app/ai_settings.py`, `app/main.py` | Kayıtlı servis test sözleşmesi ve API uçları |
| `app/ai_service.py` | Arama hatasında doğru servis adının analiz kaydına aktarılması |
| `static/ai.js`, `static/app.js` | Kayıt/test tutarlılığı, sonuç adı, kullanım rehberi |
| `desktop/logging_setup.py`, `server.py` | Güvenli dosya tanılaması |
| `desktop/self_test.py`, `tests/test_connection_tests.py`, `tests/test_connection_settings.cjs` | Paket ve regresyon testleri |

Loglar Windows'ta `%LOCALAPPDATA%\AHP Congress Analyzer\logs\app.log` ve `error.log` dosyalarındadır. Kayıtlar servis adı, hata kodu, HTTP durumu, exception sınıfları, sayısal sistem hata kodu ve dosya/satır/fonksiyon bilgisini içerir. Ham hata metni, URL, header, response body, API anahtarı ve yerel değişkenler yazılmaz. Credential Manager ve .env saklama davranışları korunmuştur.

## Doğrulama

- Tam Python regresyonu: 170 test; 168 geçti, 2 koşullu test atlandı. Masaüstü gerçek süreç testi ayrıca açılarak geçti: toplam 169 test doğrulandı; native OCR bu çalışma kapsamında çalıştırılmadı.
- JavaScript: 21 test geçti. Kaydedilmemiş Jina seçiminin engellenmesi, kaydetme sonrası doğru sağlayıcının test edilmesi, model/anahtar değişimi ve hata mesajı kontrolleri dahil.
- Kaynak modunda masaüstü self-test: 20 kontrol geçti. Gemini/Tavily/Jina adaptörleri aynı self-test ile üretilen Windows EXE içinde de çalıştırılır.
- Üç servisin başarı, 401, 403, 429, SSL, DNS, timeout, bağlantı ve gerçek ProxyError senaryoları HTTPX MockTransport ile kontrol edildi. İstek oluşturma, adres, header ve HTTP yanıt işleme kodları gerçektir; ağ yanıtları test tarafından sağlanır. Gerçek API anahtarı, dış istek veya ücret kullanılmadı.
- Tarayıcıda Gemini ve Tavily başarı akışı, kaydedilmemiş Jina seçimi ve kaydedilmiş Jina 403 akışı ayrı geçici test uygulamasında doğrulandı.
- AHP modeli/puanlama ve veritabanı şeması değiştirilmedi. Bu testler hedef Windows ağındaki canlı API erişiminin kanıtı değildir.

## Windows'a uygulama

Eski kurulmuş EXE kendi Python kodunu içerir; yalnız web dosyalarını kopyalamak yeterli değildir. 1.9.1 kaynaklarından, mevcut onaylı OCR/build girdileriyle Windows'ta yeniden derleyin:

```powershell
.\build_windows.bat --publisher "GERCEK YAYINCI ADI"
```

Yayıncı yer tutucusunu gerçek adla değiştirin. Önkoşullar ve isteğe bağlı Inno yolu: `docs/WINDOWS_BUILD.md`. Çıktı `release\1.9.1\AHP-Congress-Analyzer-Setup-1.9.1.exe` olacaktır. Mevcut paketleme Inno Setup EXE'dir; MSI çıktısı yoktur. Bu Mac ortamında Windows binary üretilmedi.

Yedek aldıktan sonra uygulamayı kapatıp yeni sürümü kurun. AI bağlantısı ekranında Gemini'yi kaydedip test edin; ardından Tavily ve Jina'yı sırayla kaydedip test edin. Her seferinde servis adı ve gerçek HTTP/transport sonucu görünmelidir. Başarılı API yanıtı öncesinde proxy uyarısı çıkmamalıdır. Kullanıcı anahtarlarını hata raporuna eklemeyin.

Resmî dayanaklar: [Microsoft Windows proxy yapılandırma alanları](https://learn.microsoft.com/en-us/windows/win32/api/winhttp/ns-winhttp-winhttp_current_user_ie_proxy_config), [HTTPX exception sınıfları](https://www.python-httpx.org/exceptions/), [HTTPX ortam ayarları](https://www.python-httpx.org/environment_variables/), [Gemini generateContent](https://ai.google.dev/api/generate-content).
