"""Coherent SQLite snapshots and validated, reversible offline restores."""
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile

def stamp(): return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

def validate(connection):
    from app.database import SCHEMA_VERSION
    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('Yedek dosyası bütünlük kontrolünden geçemedi.')
    if connection.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Yedekte kayıt ilişkileri bozuk.')
    if connection.execute('PRAGMA user_version').fetchone()[0] > SCHEMA_VERSION:
        raise ValueError('Yedek daha yeni bir uygulama sürümüne ait.')
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'models','congresses','evaluations'} <= tables:
        raise ValueError('Bu dosya bir Kongre Pusulası veritabanı değil.')
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():
        raise ValueError('Yedek desteklenmeyen veritabanı nesneleri içeriyor.')

def snapshot(source, directory, *, prefix='conference'):
    source, directory = Path(source), Path(directory)
    if not source.is_file(): raise ValueError('Yedeklenecek veritabanı bulunamadı.')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (prefix+'_'+stamp()+'.db')
    fd = os.open(target, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600); os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as original, closing(sqlite3.connect(target)) as copy:
            original.backup(copy)
            validate(copy)
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise

def restore(source, destination, backups):
    """Caller must hold the desktop instance lock, with the backend stopped."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination: raise ValueError('Etkin veritabanı kendi üzerine geri yüklenemez.')
    if not source.is_file(): raise ValueError('Yedek dosyası bulunamadı.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=destination.parent, suffix='.restore.db'); os.close(fd)
    staging = Path(name)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as original, closing(sqlite3.connect(staging)) as copy:
            validate(original)
            original.backup(copy)
        # Validate/migrate a copy, never the source file or active database.
        from app.database import Database
        database = Database(staging)
        try: database.initialize(backup_before_migration=False)
        finally: database.close()
        with closing(sqlite3.connect(staging)) as copy: validate(copy)
        if destination.exists(): snapshot(destination, backups, prefix='before-restore')
        # A leftover WAL could overwrite restored contents; normalize under the instance lock.
        if destination.exists():
            with closing(sqlite3.connect(destination)) as current:
                if current.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] not in (0,):
                    raise ValueError('Veritabanı kullanımda. Uygulamayı kapatıp tekrar deneyin.')
                current.execute('PRAGMA journal_mode=DELETE')
        os.replace(staging, destination)
    finally:
        staging.unlink(missing_ok=True)
