# Kongre Pusulası

**AHP tabanlı akademik kongre analizi ve karar destek uygulaması.**

Kongreleri belirlenen kriterlerle değerlendirin, kaynaklara dayalı AI bulgularını inceleyin ve uygunluk puanlarını karşılaştırın. Türkçe arayüz; Python, FastAPI, SQLAlchemy ve SQLite ile bu bilgisayarda çalışır.

## Özellikler

- **AHP değerlendirmesi:** 10 kriter, sürümlü model ağırlıkları, tutarlılık kontrolü ve senaryo analizi.
- **Manuel veya AI analizi:** Metin, bağlantı, PDF ve görsellerden elde edilen bulguları kaynaklarıyla inceleme.
- **Birden fazla AI sağlayıcısı:** OpenAI, Gemini, OpenRouter, Groq ve AIMLAPI; onaylanan yedekler arasında kota/bağlantı hatasında otomatik geçiş.
- **Web araştırması:** Tavily ve Jina AI Search bağlantıları.
- **Kongre kütüphanesi:** Karşılaştırma, logolar, değerlendirme geçmişi, çöp kutusu ve geri yükleme.
- **Uygunluk düzeyleri:** Düşük Uygunluk, Orta Uygunluk ve Yüksek Uygunluk. Eksik bilgi ayrıca gösterilir.
- **Raporlar:** PDF/CSV dışa aktarma ve SQLite yedekleme/bağlama.
- **İsteğe bağlı bilimsel araçlar:** Kanıt belirsizliği politikası, Conjoint tercih analizi ve çevrimdışı yöntem karşılaştırmaları.

### Tercih analizi

Bu bölümde üç başlangıç seçeneği vardır: **Örnek sonuçları gör**, **Seçim yaparak dene** ve **Katılımcılarla araştır**. İlk seçenekte örnek seçimler ve sonuçlar tek düğmeyle hazırlanır. Özelliklerin tercih üzerindeki etkisi açıklamalı çubuklarla gösterilir; ileri ayarlar ayrı açılır alanlardadır.

Araştırma bölümü başlangıçta kapalıdır. Örnek sonuçlar teknik deneme içindir; bilimsel doğrulama için gerçek araştırma tasarımı ve veri gerekir. Tercih etkileri AHP uygunluk puanlarından ayrı tutulur.

## Kurulum

Python **3.12** kullanın. Uygulamayı çalıştırmak için Node.js/npm gerekmez. Aşağıdaki komutları bu README'nin bulunduğu klasörde çalıştırın.

### macOS / Linux

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --open
```

macOS'ta kurulumdan sonra `Baslat.command` dosyası da kullanılabilir.

### Windows — kaynak koddan

PowerShell'de:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe server.py --open
```

Adres: **http://127.0.0.1:8765**. Terminal açık kalmalıdır; durdurmak için `Ctrl+C` kullanın. Port doluysa başlatma komutuna `--port 8766` ekleyebilirsiniz.

Windows masaüstü EXE/kurulum paketi üretimi ayrı bir işlemdir. Windows x64 build ortamı ve ek bileşenler için [Windows build rehberine](docs/WINDOWS_BUILD.md) bakın. Bu depo hazır veya Windows üzerinde doğrulanmış bir installer içermez.

## İlk kullanım

1. İlk açılışta AHP modelinin dört **örnek** kongresi yüklenir. Bunlar kullanıcıların gerçek analiz kayıtları değildir.
2. **Kongreler → Kongre ekle** ile manuel değerlendirme oluşturun.
3. AI kullanacaksanız **AI bağlantısı** ekranında sağlayıcı, model ve kendi API anahtarınızı kaydedin. Manuel AHP ve örnek tercih analizi API anahtarı gerektirmez.
4. **AI ile analiz** bölümüne kaynak ekleyin; bulguları ve alıntıları inceleyerek sonucu kaydedin.
5. **Karşılaştırma**, **Senaryo analizi** ve uygulama içindeki **Kullanım rehberi** bölümlerinden devam edin.

Varsayılan proje puanlama politikası ve isteğe bağlı **Bilimsel kanıt politikası** farklı varsayımlar kullanır. Bilimsel politikada bilinmeyen, uygulanamaz ve çelişkili kriterler kesin puan almaz; olası puan aralığı gösterilir. [Kriter kod kitabı](docs/CRITERIA_CODEBOOK.md) bu ayrımı açıklar.

## Yapılandırma ve veriler

- `.env.example` yalnız boş anahtar alanları ve örnek ayarlar içerir. İsterseniz `.env` adıyla kopyalayın; kendi anahtarlarınızı yalnız yerel `.env` veya uygulamanın ayar ekranına girin.
- `.env`, API anahtarları, kullanıcı veritabanları, loglar, yedekler ve analiz çıktıları depoya dahil değildir. `.gitignore` bunları dışarıda tutar.
- İlk çalıştırmada yerel `data/kongre.db` oluşturulur. Başlangıç modelinin sayısal referansı `analiz/hesaplama_sonuclari.json` içindedir; asıl Excel dosyası uygulamayı çalıştırmak için gerekmez.
- Araştırma verileri ayrı `.research.sqlite3` dosyasında tutulur; standart kongre veritabanı yedeğine dahil değildir.
- AI ve web araştırması internet ve kullanıcının servis hesabını gerektirir. Kota/ücret sağlayıcıya bağlıdır; bütün sağlayıcılar kullanılamazsa uygulama ilerlemeyi korur.
- Uygulama yerel ve tek kullanıcılıdır. GitHub'a kaynak yüklemek uygulamayı internetten erişilebilir bir hizmete dönüştürmez.

## Testler

macOS / Linux:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m unittest test_app
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe -m unittest test_app
```

JavaScript testleri için ayrıca Node.js gerekir:

```sh
node --test tests/*.cjs
```

PowerShell'de dosya listesini açıkça geçirin:

```powershell
node --test (Get-ChildItem tests/test*.cjs).FullName
```

JavaScript testleri Python karşılaştırması için proje içindeki `.venv` ortamını kullanır; bu ortam yoksa sistem Python'ını dener. Farklı bir ortam kullanıyorsanız `PYTHON` ortam değişkenini Python çalıştırılabilir dosyasının tam yoluna ayarlayın.

Standart testler geçici veritabanları ve sahte sağlayıcı yanıtları kullanır. Yerel OCR, Windows masaüstü/installer ve gerçek servis hesabı doğrulamaları ayrı kontrollerdir. Test başarısı bilimsel yöntem geçerliği veya kesintisiz API erişimi garantisi değildir.

## Proje yapısı

| Klasör / dosya | İçerik |
|---|---|
| `engine.py` | AHP hesapları ve puanlama |
| `app/` | FastAPI, veri modelleri, AI/arama, araştırma modülleri |
| `static/` | Türkçe HTML/CSS/JavaScript arayüzü |
| `desktop/` | Masaüstü başlatma ve paket kontrolleri |
| `packaging/windows/` | Windows paketleme tanımları |
| `tools/` | Build ve bakım araçları |
| `tests/`, `test_app.py` | Regresyon ve hesaplama testleri |
| `analiz/` | AHP başlangıç referansı ve Excel yöntem incelemesi |
| `migrations/` | Veritabanı şema geçmişi |
| `docs/` | Yöntem, geliştirme ve kurulum belgeleri |

`audit_ahp.py` isteğe bağlı Excel denetim aracıdır; ayrıca `numpy`, `openpyxl` ve kendi Excel girdinizi gerektirir. Normal uygulama başlangıcının parçası değildir.

## Belgeler

- [Bilimsel araştırma araçları](docs/SCIENTIFIC_RESEARCH.md)
- [Kriter kod kitabı](docs/CRITERIA_CODEBOOK.md)
- [Bilimsel rapor şablonu](docs/SCIENTIFIC_REPORT_TEMPLATE.md)
- [Geliştirme notları ve eski sürüm açıklamaları](docs/DEVELOPMENT_NOTES.md)
- [Windows build rehberi](docs/WINDOWS_BUILD.md)
- [BT dağıtım notları](IT_DEPLOYMENT_NOTES.md)
- [Veritabanı şema geçmişi](migrations/README.md)
- [Değişiklik günlüğü](CHANGELOG.md)
- [Üçüncü taraf bileşenler](THIRD_PARTY_NOTICES.md)
