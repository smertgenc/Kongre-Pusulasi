# Üçüncü taraf bileşenler

Uygulamanın dağıtım lisansı/yayıncı sahipliği bu görevde varsayılmadı; yayın sahibi ve BT dağıtımdan önce belirlemelidir. Yeni bir açık kaynak lisansı keyfi olarak atanmadı.

Python ve uygulamanın mevcut requirements paketleri, PyInstaller, pywebview, pythonnet/.NET, WebView2, SQLite ve OCR bileşenleri kendi lisanslarıyla kullanılır. Windows build scripti yüklü Python dağıtımlarının sürüm/lisans metadata'sını BUILD_MANIFEST.json'a ve paketlerdeki LICENSE/NOTICE metinlerini THIRD_PARTY_LICENSES dizinine kopyalar. PyInstaller'ın Python runtime lisansını ve vendor dosyalarının dağıtım koşullarını ayrıca gözden geçirin; otomatik metadata toplama hukukî/lisans uygunluğu garantisi değildir.

Tesseract ve Leptonica ile gerekli DLL'lerin, eng/tur dil verilerinin lisansları BT onaylı OCR girdisinin `licenses/` dizininden paketlenir. OCR kilidi sürümü, kaynak bilgisi ve her bileşenin SHA256 değerini kaydeder. `tools/prepare_ocr.py` eksik lisans dizininde durur; tüm transitif lisansların doğruluğunu build sahibi teyit eder.

Microsoft WebView2 Runtime/.NET Framework uygulama installer'ına gömülmez; BT bunları Microsoft'un dağıtım şartları ve şirket politikasıyla sağlar. Installer önkoşulları kontrol eder. Inno Setup'ın seçilen sürümü için lisans şartlarını build sahibi doğrular.

Kaynaklar:
- https://www.python.org/psf/license/
- https://pyinstaller.org/en/stable/license.html
- https://pywebview.flowrl.com/
- https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE
- https://github.com/DanBloomberg/leptonica/blob/master/leptonica-license.txt
- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
- https://jrsoftware.org/isinfo.php
