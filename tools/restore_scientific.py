"""Check or restore this source update only; never touches data or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def restore(root,backup,apply=False):
    root=Path(root).resolve();backup=Path(backup).resolve()
    manifest=json.loads((backup/'changes.json').read_text(encoding='utf-8'))
    for rel,entry in manifest.items():
        path=root/rel
        if Path(rel).is_absolute() or '..' in Path(rel).parts or Path(rel).parts[0] in ('data','.env','.venv') or path.is_symlink():raise ValueError('Güvenli olmayan dosya yolu.')
        if sha(path)!=entry['after']:raise ValueError('Güncelleme sonrasında değişmiş dosya var; üzerine yazılmadı: '+rel)
        if entry['before'] is not None and sha(backup/'before'/rel)!=entry['before']:raise ValueError('Kaynak yedek hash uyuşmazlığı: '+rel)
    if apply:
        for rel,entry in manifest.items():
            path=root/rel;saved=backup/'rolled-back-version'/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
            if entry['before'] is not None:shutil.copy2(backup/'before'/rel,path)
            else:path.unlink()
    return len(manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('backup',type=Path);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();n=restore(Path(__file__).resolve().parents[1],args.backup,args.apply)
    print(f'{n} kaynak dosyası '+('geri alındı.' if args.apply else 'kontrol edildi. Değişiklik yapılmadı; geri almak için --apply ekleyin.'))
