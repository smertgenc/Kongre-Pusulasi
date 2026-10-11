"""Build only on Windows x64. No private files or live credentials enter the bundle."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
from prepare_ocr import verify as verify_ocr

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def run(command, **options):
    subprocess.run([str(x) for x in command],cwd=options.pop('cwd',ROOT),check=True,**options)

def version_info(version, publisher):
    numbers = tuple(int(x) for x in version.split('.'))+(0,)
    strings = {'CompanyName':publisher,'FileDescription':'AHP-Based Conference Analysis and Decision Support System',
               'FileVersion':version,'InternalName':'AHP-Congress-Analyzer',
               'OriginalFilename':'AHP-Congress-Analyzer.exe','ProductName':'AHP Congress Analyzer','ProductVersion':version}
    table = ','.join(f'StringStruct({key!r},{value!r})' for key,value in strings.items())
    return f"VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r},prodvers={numbers!r},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[{table}])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])"

def licenses_and_inventory(destination):
    inventory=[]
    for distribution in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name=distribution.metadata['Name']; version=distribution.version
        inventory.append({'name':name,'version':version,'license':distribution.metadata.get('License-Expression') or distribution.metadata.get('License','')})
        for item in distribution.files or []:
            if '.dist-info/' not in str(item).replace('\\','/'): continue
            if not any(word in item.name.lower() for word in ('license','copying','notice')): continue
            source=Path(distribution.locate_file(item))
            if source.is_file():
                relative = '/'.join(Path(str(item)).parts[1:])
                target=destination/'THIRD_PARTY_LICENSES'/name/relative
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    return inventory

def reject_private_files(directory):
    for path in directory.rglob('*'):
        if not path.is_file(): continue
        if path.name.startswith('.env') or path.suffix.lower() in ('.db','.sqlite','.sqlite3','.pfx','.p12','.log'):
            raise RuntimeError('Paket içinde özel/veri dosyası bulundu: '+path.name)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publisher',required=True,help='BT/yayın sahibinin onayladığı gerçek yayıncı adı')
    parser.add_argument('--ocr-dir',type=Path,default=ROOT/'vendor/ocr')
    parser.add_argument('--iscc',type=Path,default=None)
    parser.add_argument('--sign-thumbprint',help='Windows sertifika deposundaki kod imzalama sertifikasının SHA1 kimliği; parola alınmaz')
    parser.add_argument('--signtool',type=Path)
    parser.add_argument('--timestamp-url',help='BT tarafından onaylanmış RFC3161 zaman damgası servisi')
    args=parser.parse_args()
    if sys.platform!='win32' or struct.calcsize('P')!=8 or sys.version_info[:2]!=(3,12) or platform.machine().upper() not in ('AMD64','X86_64'):
        parser.error('Build, Windows x64 ve Python 3.12 x64 ortamında çalıştırılmalıdır.')
    if not args.publisher.strip() or any(c in args.publisher for c in '\r\n"'):
        parser.error('Geçerli bir yayıncı adı girin.')
    if args.sign_thumbprint and (not re.fullmatch('[0-9A-Fa-f]{40}',args.sign_thumbprint) or not args.signtool or not args.timestamp_url):
        parser.error('İmzalama için sertifika kimliği, signtool ve zaman damgası URL gereklidir.')
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): parser.error('VERSION SemVer biçiminde olmalıdır.')
    if any(int(x)>65535 for x in version.split('.')): parser.error('Windows sürüm bileşeni 65535 değerini aşamaz.')
    ocr=verify_ocr(args.ocr_dir)
    iscc=args.iscc or Path(os.environ.get('ISCC_EXE',r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'))
    if not iscc.is_file(): parser.error('Inno Setup 6.3+ ISCC.exe bulunamadı; --iscc ile BT onaylı derleyiciyi belirtin.')
    release=ROOT/'release'/version
    if release.exists(): parser.error('Bu sürümün release klasörü zaten var; üzerine yazılmaz. Sürümü artırın veya eski çıktıyı arşivleyin.')
    work=ROOT/'build/windows'; work.mkdir(parents=True,exist_ok=True)
    (work/'version-info.txt').write_text(version_info(version,args.publisher),encoding='utf-8')
    # Cleaning is restricted to generated application binaries, never user data.
    dist=ROOT/'dist/AHP-Congress-Analyzer'
    if dist.exists(): shutil.rmtree(dist)
    run([sys.executable,'-m','pip','check'])
    run([sys.executable,ROOT/'tools/create_research_manifest.py'])
    run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--workpath',work/'pyinstaller',
         '--distpath',ROOT/'dist',ROOT/'packaging/windows/app.spec'],env={**os.environ,'AHP_OCR_DIR':str(args.ocr_dir.resolve())})
    executable=dist/'AHP-Congress-Analyzer.exe'
    reject_private_files(dist)
    sys.path.insert(0,str(ROOT))
    from desktop.runtime import verify_packaged_runtime
    verify_packaged_runtime(dist/'_internal')
    # Different working directory catches accidental dependencies on the checkout.
    run([executable,'--self-test',work/'package-smoke.json'],timeout=180,cwd=work)
    if not json.loads((work/'package-smoke.json').read_text(encoding='utf-8'))['ok']: raise RuntimeError('Paket smoke testi başarısız.')
    run([executable,'--smoke-ui',work/'ui-smoke.json'],timeout=120,cwd=work)
    if not json.loads((work/'ui-smoke.json').read_text(encoding='utf-8'))['ok']: raise RuntimeError('Paket WebView2 başlangıç testi başarısız.')
    if args.sign_thumbprint:
        run([args.signtool,'sign','/sha1',args.sign_thumbprint,'/fd','SHA256','/tr',args.timestamp_url,'/td','SHA256',executable])
        run([args.signtool,'verify','/pa',executable])
    inventory=licenses_and_inventory(dist)
    for filename in ('IT_DEPLOYMENT_NOTES.md','THIRD_PARTY_NOTICES.md','CHANGELOG.md'):
        shutil.copy2(ROOT/filename,dist/filename)
    release.mkdir(parents=True)
    command=[iscc,'/DAppVersion='+version,'/DPublisher='+args.publisher,'/DSourceDir='+str(dist),'/DReleaseDir='+str(release)]
    if args.sign_thumbprint:
        # Inno signs the installer and its generated uninstaller. No shell invocation.
        sign_command=f'$q{args.signtool}$q sign /sha1 {args.sign_thumbprint} /fd SHA256 /tr $q{args.timestamp_url}$q /td SHA256 $f'
        command += ['/DSignCommand=1','/Sapproved='+sign_command]
    run(command+[ROOT/'packaging/windows/installer.iss'])
    installer=release/f'AHP-Congress-Analyzer-Setup-{version}.exe'
    if args.sign_thumbprint: run([args.signtool,'verify','/pa',installer])
    for filename in ('IT_DEPLOYMENT_NOTES.md','THIRD_PARTY_NOTICES.md','CHANGELOG.md','VERSION'):
        shutil.copy2(ROOT/filename,release/filename)
    shutil.copy2(ROOT/'docs/WINDOWS_README.txt',release/'README.txt')
    shutil.copytree(dist/'THIRD_PARTY_LICENSES',release/'THIRD_PARTY_LICENSES')
    shutil.copy2(work/'package-smoke.json',release/'PACKAGE_SMOKE_TEST.json')
    shutil.copy2(work/'ui-smoke.json',release/'UI_SMOKE_TEST.json')
    shutil.copy2(args.ocr_dir/'ocr-lock.json',release/'OCR_COMPONENTS.json')
    metadata={'product':'AHP Congress Analyzer','version':version,'publisher':args.publisher,'python':platform.python_version(),
              'architecture':platform.machine(),'signed':bool(args.sign_thumbprint),'ocr':ocr['version'],
              'dependencies':inventory,'windows_installation_verified':False,
              'installed_files':{p.relative_to(dist).as_posix():digest(p) for p in sorted(dist.rglob('*')) if p.is_file()}}
    (release/'BUILD_MANIFEST.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (release/'SHA256.txt').write_text(digest(installer)+'  '+installer.name+'\n',encoding='utf-8')
    print('Release hazır:',release)
    print('Kurulum/upgrade/uninstall kabul testleri: docs/WINDOWS_ACCEPTANCE.md')

if __name__=='__main__': main()
