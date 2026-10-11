"""Generate non-secret source provenance before PyInstaller removes .py sources."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.research_provenance import source_hashes

def main():
    target=ROOT/'build/windows/research-code-manifest.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'version':(ROOT/'VERSION').read_text().strip(),'hashes':source_hashes(ROOT)},indent=2),encoding='utf-8')
    print('Research code manifest created.')
if __name__=='__main__':main()
