"""Create a source-only Windows handoff archive from an explicit allowlist."""
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['VERSION','README.md','requirements.txt','build_windows.bat','desktop_main.py','server.py',
       'engine.py','legacy_server.py','test_app.py','restore_backup.py','audit_ahp.py','.gitignore','.env.example',
       'IT_DEPLOYMENT_NOTES.md','THIRD_PARTY_NOTICES.md','CHANGELOG.md','analiz/hesaplama_sonuclari.json']
PATTERNS={'app':('*.py','*.json','native/*.swift'),'desktop':('*.py',),
          'static':('*.js','*.css','*.html'),'tools':('*.py',),'docs':('*.md','*.txt'),
          'packaging/windows':('*.txt','*.spec','*.iss','*.ico','*.svg'),
          'tests':('*.py','*.cjs','fixtures/*.png')}

def source_files():
    files={ROOT/path for path in FILES}
    for folder, patterns in PATTERNS.items():
        for pattern in patterns: files.update((ROOT/folder).glob(pattern))
    for path in files:
        if not path.is_file() or path.is_symlink(): raise ValueError('Build kit kaynağı eksik veya symlink: '+path.name)
        if path.name=='.env' or path.suffix in ('.db','.log','.pfx','.p12') or any(p in ('data','__pycache__','.venv','outputs','tmp') for p in path.relative_to(ROOT).parts):
            raise ValueError('Build kit içinde özel/veri dosyası olamaz.')
    return sorted(files)

def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    output=ROOT/'release';output.mkdir(exist_ok=True)
    target=output/f'AHP-Congress-Analyzer-Windows-Build-Kit-{version}.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source_files(): archive.write(path,'AHP-Congress-Analyzer/'+path.relative_to(ROOT).as_posix())
    with target.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    (output/'SOURCE_SHA256.txt').write_text(digest+'  '+target.name+'\n',encoding='utf-8')
    print(target)

if __name__=='__main__': main()
