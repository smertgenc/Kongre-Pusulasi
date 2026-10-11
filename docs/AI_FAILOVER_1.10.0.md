# AI otomatik geçişi — 1.10.0

10 Ekim 2026. Kaynak sürümü; yeni Windows installer henüz üretilmedi.

## Giderilen sorun

Eski akış yalnız seçili sağlayıcıda yeniden deniyordu. Kota bittiğinde analiz
başarısız oluyordu. Groq'un tamamladığı parçalar yalnız bellekte kaldığı için
daha sonraki bir hatada tekrar deneme tüm kaynakları yeniden gönderiyordu.

## Yeni akış

- Önce kayıtlı etkin AI sağlayıcısı kullanılır. Analiz ekranında otomatik geçiş
  varsayılan açıktır; anahtarı kayıtlı diğer servisler katalog sırasıyla gösterilir.
  Katalog sırası OpenAI, Gemini, OpenRouter, Groq, AIMLAPI'dir; etkin servis başa alınır.
- İstemci, aktarım onayıyla birlikte tam `fallback_providers` listesini ve model
  adlarını gönderir. Sunucu bunu tek bir kayıtlı ayar/anahtar kopyasıyla doğrular.
  İş sürerken eklenen servis veya değiştirilen model bu işe katılmaz. Geçiş,
  kullanıcının ayarlardaki öncelikli servis tercihini değiştirmez.
- Kota (429) veya kredi (402) sorununda yedek varsa hemen geçilir. Geçici servis
  hatalarında mevcut sınırlı yeniden denemeden sonra yedek denenir. Anahtar, erişim,
  model ve yanıt biçimi hataları da kayıtlı yedeğe geçirilebilir. SSL/proxy/ağ
  politikası hataları ve içerik reddi başka servise gönderilerek gizlenmez.
- Groq parçaları en fazla 5.000 kaynak karakteriyle başlar. Bağlam ya da çıktı token
  sınırında parça 500 karaktere kadar küçültülür; kaynak kimlikleri ve kısa alıntı
  sınırlarındaki örtüşme korunur. Diğer servislerde tüm metin tek istekle başlar;
  gerçek sınır hatası olmadıkça gereksiz bölünmez. Yarım JSON tamamlanmış sayılmaz.
- Her tamamlanan parçanın doğrulanmış çıktısı, sağlayıcı/modeli ve kalan kaynaklar
  SQLite'a yazılır. Yeni sağlayıcı yalnız yarım/kalan parçaları alır. Alıntı önce
  gönderilen parçada, ardından tüm kaynak arşivinde doğrulanır. Birleştirme çelişkili
  kanıtları korur; AHP ağırlıkları, eşikleri ve hesaplama motoru değiştirilmedi.
- Tüm servisler kullanılamıyorsa nihai puan yoktur. Kayıtlı kaynaklarla tekrar
  deneme aynı kaynak, yöntem ve prompt sürümünde kalan parçalarla devam eder.
  Eski rapor değişmez. Uygulama yeniden açıldığında kesilen analiz işaretlenir ve
  kayıtlı ilerleme korunur; otomatik olarak ücretli çağrı başlatılmaz.
- Bir denemede en fazla 64 parça isteği, her istekte mevcut en fazla üç HTTP
  denemesi vardır. Bu sınırda da ilerleme saklanır. Sağlayıcılar sonsuz döngüyle
  tekrar ziyaret edilmez. Aynı sağlayıcı/modelde çalışan veya tamamlanmış tekrar
  denemeyi yeniden tıklamak yeni ücretli iş oluşturmaz.

Jina/Tavily bu listeye girmez; arama servisleridir. Arama, OCR ve kaynak indirme
tekrar denemede yenilenmez. Başarısız API çağrısı ücretlenmiş olabilir; yedeğe geçiş
ek istek kullanır. Tüm hesaplarda kota kalmadığında kesintisiz analiz garantisi
verilemez. Kaynaklar ve tamamlanan parçalar saklanır.

## Uygulama alanları

`app/ai_failover.py` parça yönetimi ve geçişi; `app/ai_service.py` kalıcı kayıt ve
tekrar denemeyi; `app/ai_settings.py` tek ayar kopyasını;
`app/ai_schemas.py` açık alıcı sözleşmesini yönetir. `app/ai_provider.py` 402,
çıktı token sınırı ve parçaya özel istekleri ayrıştırır. `static/ai.js`, kullanım
rehberi ve `app/pdf_report.py` hangi sağlayıcının katkı verdiğini gösterir.
Anahtarlar yalnız bellekteki bağlantı nesnelerindedir; log, kaynak arşivi,
ilerleme kaydı ve API yanıtlarına eklenmez. DB şemasında değişiklik gerekmez.

## Doğrulama

`tests/test_failover.py` gerçek adaptörleri taklit HTTP yanıtlarıyla sınar:
429 → yedek, beş servisin tükenmesi, izinsiz alıcıya geçmeme, eski ayar reddi,
iş sırasında değişmeyen anahtar kopyası, parça ortasında geçiş, kaldığı yerden
devam, token nedeniyle bölünme, 402/503, SSL/içerik reddi, hatalı ilerleme kimliği
ve tekrar deneme tekilleştirme. `tests/test_failover.cjs` arayüz alıcı listesini,
geçişi kapatmayı, onay yenilemeyi ve rapor metnini kontrol eder.

`desktop/self_test.py` paketlenmiş uygulamada sahte 429 → Groq başarısı ve kalıcı
ilerleme kontrolü de çalıştırır. Gerçek API anahtarı/kotası tüketilmez. Windows
EXE ve kurulum kabulü ancak Windows build/test ortamında doğrulanabilir.

10 Ekim doğrulaması: 202 benzersiz Python testi ve 24 JavaScript testi geçti;
native OCR opt-in testi bu koşuda atlandı. Masaüstü kaynak self-test'i 24
kontrolü geçti. Gerçek ayrı backend süreç/port testi macOS'ta çalıştı. Tarayıcıda
izole veritabanı ve sahte HTTP yanıtlarıyla Gemini 429 → Groq → tamamlanmış
rapor akışı doğrulandı; tarayıcı konsolunda hata yoktu. API anahtarı tüketilmedi.
İstek bütçesinin dolması ve yeniden açılış sonrasında yalnız kalan parçaların
işlenmesi de test edildi. Bu sonuçlar Windows EXE veya canlı hesap testi değildir.

Proje kökünde test komutları:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest test_app
node --test tests/*.cjs
python desktop_main.py --self-test tmp/desktop-smoke.json
```

Windows'ta yeni build: `build_windows.bat --publisher "GERÇEK YAYINCI ADI"`.
Ayrıntılar: [Windows build belgesi](WINDOWS_BUILD.md).

Hata sınıflandırması referansları:
[Gemini sorun giderme](https://ai.google.dev/gemini-api/docs/troubleshooting),
[Groq kota ve başlıkları](https://console.groq.com/docs/rate-limits),
[OpenRouter hata sözleşmesi](https://github.com/OpenRouterTeam/docs/blob/main/api_reference/errors-and-debugging.mdx).
