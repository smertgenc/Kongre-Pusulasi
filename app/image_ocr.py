"""Local OCR; no uploaded image is sent to a model or an OCR service."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Lock
from app.config import ROOT

MAX_IMAGE = 4_000_000
_BUILD_LOCK = Lock()

def image_bytes(content):
    try: raw=base64.b64decode(content,validate=True)
    except (ValueError,TypeError): raise ValueError('Görsel verisi okunamadı.') from None
    if len(raw)>MAX_IMAGE: raise ValueError('Görsel en fazla 4 MB olabilir.')
    if raw.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
    elif raw.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
    elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP': mime='image/webp'
    else: raise ValueError('PNG, JPEG veya WebP biçiminde gerçek bir görsel seçin.')
    return raw,mime

def ocr_binary():
    if sys.platform!='darwin': raise ValueError('Görsel metin okuma bu sürümde macOS üzerinde çalışır; diğer sistemlerde metni yapıştırın.')
    source=ROOT/'app/native/vision_ocr.swift'
    runtime=ROOT/'data/runtime';binary=runtime/'vision-ocr'
    with _BUILD_LOCK:
        if binary.exists() and binary.stat().st_mtime>=source.stat().st_mtime:return binary
        compiler=shutil.which('swiftc')
        if not compiler: raise ValueError('Görsel okuma için macOS Swift komut satırı araçları gereklidir.')
        runtime.mkdir(parents=True,exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix='ocr-build-',dir=runtime) as tmp:
                target=Path(tmp)/'vision-ocr'
                result=subprocess.run([compiler,str(source),'-O','-module-cache-path',str(runtime/'swift-cache'),'-o',str(target)],capture_output=True,timeout=120)
                if result.returncode: raise ValueError('Görsel okuma bileşeni hazırlanamadı. Swift komut satırı araçlarını kontrol edin.')
                os.replace(target,binary)
        except (OSError,subprocess.TimeoutExpired): raise ValueError('Görsel okuma bileşeni başlatılamadı.') from None
    return binary

def extract_image(content):
    raw,mime=image_bytes(content)
    if sys.platform == 'win32':
        from app.windows_ocr import extract_windows_image
        data = extract_windows_image(raw)
        if len(data['text'].strip()) < 20:
            raise ValueError('Görselde yeterli okunabilir yazı bulunamadı. Net bir afiş/program görseli ekleyin.')
        return data, {'mime':mime,'data':base64.b64encode(raw).decode(),'width':data['width'],'height':data['height'],
                      'content_hash':hashlib.sha256(raw).hexdigest()}
    binary=ocr_binary()
    try:
        with tempfile.TemporaryDirectory(prefix='kongre-ocr-') as tmp:
            path=Path(tmp)/'source-image';path.write_bytes(raw)
            result=subprocess.run([str(binary),str(path)],capture_output=True,timeout=60)
        data=json.loads(result.stdout)
        if result.returncode or 'error' in data:
            messages={'IMAGE_TOO_LARGE':'Görsel en fazla 20 megapiksel ve kenar başına 12.000 piksel olabilir.',
                      'INVALID_IMAGE':'Görsel bozuk, desteklenmeyen veya hareketli bir dosya. Sabit PNG/JPEG/WebP kullanın.',
                      'TEXT_TOO_LARGE':'Görselden okunan metin 60.000 karakter sınırını aşıyor.'}
            raise ValueError(messages.get(data.get('error'),'Görseldeki yazılar okunamadı. Daha net bir görsel yükleyin.'))
    except subprocess.TimeoutExpired: raise ValueError('Görsel metin okuma zaman aşımına uğradı. Daha küçük bir görsel deneyin.') from None
    except (OSError,ValueError) as exc:
        if isinstance(exc,ValueError) and not isinstance(exc,json.JSONDecodeError):raise
        raise ValueError('Görsel okuma bileşeni geçerli sonuç üretmedi.') from None
    if len(data['text'].strip())<20: raise ValueError('Görselde yeterli okunabilir yazı bulunamadı. Afiş/program gibi metin içeren net bir görsel ekleyin.')
    return data,{'mime':mime,'data':base64.b64encode(raw).decode(),'width':data['width'],'height':data['height'],
                 'content_hash':hashlib.sha256(raw).hexdigest()}
