"""Stage an IT-approved Tesseract directory; never downloads or executes installers."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def prepare(source, licenses, version, provenance, destination):
    source, licenses, destination = Path(source).resolve(), Path(licenses).resolve(), Path(destination).resolve()
    if destination.exists(): raise ValueError('OCR hedefi zaten var. Mevcut kilidi koruyun veya başka bir hedef seçin.')
    required = [Path('tesseract.exe'),Path('tessdata/eng.traineddata'),Path('tessdata/tur.traineddata')]
    for relative in required:
        if not (source/relative).is_file(): raise ValueError('Eksik OCR bileşeni: '+str(relative))
    license_files = [p for p in licenses.rglob('*') if p.is_file() and not p.is_symlink()
                     and (p.suffix.lower() in ('.txt','.md','.rst','.html','.htm','.pdf') or
                          p.name.lower() in ('license','copying','notice','copyright'))]
    if not license_files: raise ValueError('Tesseract, Leptonica ve dağıtımdaki DLL lisans metinlerini sağlayın.')
    files = required + [p.relative_to(source) for p in source.glob('*.dll')]
    if len(files)==len(required): raise ValueError('OCR çalışma zamanı DLL dosyaları bulunamadı.')
    destination.mkdir(parents=True)
    for relative in files:
        origin = source/relative
        if origin.is_symlink(): raise ValueError('OCR paketi sembolik bağ içermemelidir.')
        target = destination/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(origin,target)
    for path in license_files:
        target = destination/'licenses'/path.relative_to(licenses)
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    manifest = {'version':version,'provenance':provenance,'files':{
        str(p.relative_to(destination)).replace('\\','/'):sha256(p) for p in sorted(destination.rglob('*')) if p.is_file()}}
    (destination/'ocr-lock.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return manifest

def verify(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'ocr-lock.json').read_text(encoding='utf-8'))
    if not str(manifest.get('version','')).startswith('5.') or not manifest.get('provenance'):
        raise ValueError('Tesseract 5 sürümü ve kaynak bilgisi OCR kilidinde bulunmalıdır.')
    files = manifest['files']
    expected = {'tesseract.exe','tessdata/eng.traineddata','tessdata/tur.traineddata'}
    if not expected <= set(files) or not any(k.startswith('licenses/') for k in files):
        raise ValueError('OCR kilidi eksik.')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='ocr-lock.json'}
    if actual != set(files): raise ValueError('OCR klasörü kilit manifestiyle eşleşmiyor.')
    for relative, digest in files.items():
        path = directory/relative
        if not path.resolve().is_relative_to(directory) or path.is_symlink() or sha256(path)!=digest:
            raise ValueError('OCR bütünlük kontrolü başarısız: '+relative)
        if Path(relative).suffix.lower() in ('.exe','.dll') and '/' in relative:
            raise ValueError('OCR paketinde beklenmeyen çalıştırılabilir dosya.')
        if Path(relative).suffix.lower()=='.exe' and relative!='tesseract.exe':
            raise ValueError('OCR paketinde ek çalıştırılabilir dosya.')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--licenses',type=Path,required=True)
    parser.add_argument('--version',required=True)
    parser.add_argument('--provenance',required=True)
    parser.add_argument('--destination',type=Path,default=ROOT/'vendor/ocr')
    args=parser.parse_args()
    prepare(args.source,args.licenses,args.version,args.provenance,args.destination)
    verify(args.destination)
    print('OCR paketi ve SHA256 kilidi hazır:',args.destination)
