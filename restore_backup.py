"""Restore a trusted application SQL backup into a NEW database file."""
import argparse
import sqlite3
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    args=p.parse_args()
    if args.destination.exists():p.error('Hedef dosya zaten var; mevcut veriler korunmak için işlem durduruldu.')
    content=args.source.read_text(encoding='utf-8')
    with sqlite3.connect(':memory:') as staged:
        staged.executescript(content)
        tables={r[0] for r in staged.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'models','congresses','evaluations'}<=tables:p.error('Bu uygulamaya ait geçerli bir yedek değil.')
        if staged.execute('PRAGMA integrity_check').fetchone()[0]!='ok':p.error('Yedek bütünlük kontrolünü geçemedi.')
        if staged.execute('PRAGMA foreign_key_check').fetchall():p.error('Yedekte ilişki hataları var.')
        args.destination.parent.mkdir(parents=True,exist_ok=True)
        with args.destination.open('xb'):pass
        with sqlite3.connect(str(args.destination)) as dest:staged.backup(dest)
    print('Yedek yeni veritabanına geri yüklendi:',args.destination)

if __name__=='__main__':main()
