"""Bundled, offline Tesseract 5 OCR. No PATH lookup or runtime downloads."""
import csv
import io
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageOps, UnidentifiedImageError
from app.config import ROOT

def extract_windows_image(raw, *, runtime=None):
    runtime = Path(runtime) if runtime else ROOT / 'ocr'
    executable = runtime / 'tesseract.exe'
    if not executable.is_file() or not all((runtime/'tessdata'/f'{lang}.traineddata').is_file() for lang in ('tur','eng')):
        raise ValueError('Windows OCR bileşeni eksik. BT biriminizden uygulamayı tam kurulum paketiyle onarmasını isteyin.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if max(width,height)>12000 or width*height>20_000_000:
                raise ValueError('Görsel en fazla 20 megapiksel ve kenar başına 12.000 piksel olabilir.')
            if getattr(image,'n_frames',1) != 1: raise ValueError('Sabit PNG/JPEG/WebP kullanın.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            width, height = image.size
            with tempfile.TemporaryDirectory(prefix='ahp-ocr-') as folder:
                source = Path(folder)/'image.png'; image.save(source)
                result = subprocess.run([str(executable), str(source), 'stdout', '--tessdata-dir',
                     str(runtime/'tessdata'), '-l', 'tur+eng', '--oem','1','--psm','3','-c','tessedit_create_tsv=1'],
                     capture_output=True, timeout=60, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode: raise ValueError('Görseldeki yazılar okunamadı. Daha net bir görsel yükleyin.')
        groups = {}
        for row in csv.DictReader(io.StringIO(result.stdout.decode('utf-8-sig')), delimiter='\t'):
            if row.get('level')!='5' or not row.get('text','').strip(): continue
            key = tuple(row[k] for k in ('page_num','block_num','par_num','line_num'))
            groups.setdefault(key,[]).append(row)
        lines = []
        for rows in groups.values():
            text = ' '.join(r['text'] for r in rows)
            x = min(int(r['left']) for r in rows); y = min(int(r['top']) for r in rows)
            right = max(int(r['left'])+int(r['width']) for r in rows)
            bottom = max(int(r['top'])+int(r['height']) for r in rows)
            lines.append({'text':text,'confidence':max(0,min(1,sum(float(r['conf']) for r in rows)/(100*len(rows)))),
                          'box':[x/width,1-bottom/height,(right-x)/width,(bottom-y)/height]})
        text = '\n'.join(row['text'] for row in lines)
        if len(text)>60_000: raise ValueError('Görselden okunan metin 60.000 karakter sınırını aşıyor.')
        return {'text':text,'lines':lines,'width':width,'height':height,'engine':'Tesseract 5 · Türkçe / İngilizce · yerel'}
    except subprocess.TimeoutExpired:
        raise ValueError('Görsel metin okuma zaman aşımına uğradı. Daha küçük bir görsel deneyin.') from None
    except (OSError,UnidentifiedImageError,Image.DecompressionBombError,UnicodeError,KeyError,csv.Error):
        raise ValueError('Görsel okuma bileşeni geçerli sonuç üretmedi.') from None
