"""Source hashes in development, build-time manifest in a frozen distribution."""
import hashlib
import json
import re
from pathlib import Path

def source_hashes(root):
    root=Path(root)
    files=[root/name for name in ('engine.py','requirements.txt','VERSION')]
    for directory,patterns in {'app':['*.py'],'desktop':['*.py'],'static':['*.js','*.css','*.html'],'tools':['*.py']}.items():
        for pattern in patterns:files.extend(sorted((root/directory).glob(pattern)))
    return {str(p.relative_to(root).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

def code_hashes(root):
    root=Path(root)
    if (root/'engine.py').is_file():return source_hashes(root)
    path=root/'research-code-manifest.json'
    if not path.is_file():raise ValueError('Paket araştırma kod manifesti eksik; Windows paketini yeniden build edin.')
    result=json.loads(path.read_text(encoding='utf-8'))
    if result.get('version')!=(root/'VERSION').read_text(encoding='utf-8').strip():raise ValueError('Araştırma kod manifesti sürümü paketle uyuşmuyor.')
    hashes=result.get('hashes',{})
    if not all(k in hashes for k in ('engine.py','app/conjoint.py','app/research_experiments.py')) or any(not re.fullmatch('[a-f0-9]{64}',v) for v in hashes.values()):raise ValueError('Araştırma kod manifesti geçersiz.')
    return hashes
