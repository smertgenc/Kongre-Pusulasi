import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from app.models import Base
from app.classification_migration import migrate_classifications

SCHEMA_VERSION = 7

class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.engine = create_engine(URL.create('sqlite', database=str(self.path)),
                                    connect_args={'check_same_thread': False, 'timeout': 15})
        @event.listens_for(self.engine, 'connect')
        def configure(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

    def initialize(self, *, backup_before_migration=True):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Validate the original schema before applying versioned data migrations.
        with self.engine.connect() as connection:
            version = connection.exec_driver_sql('PRAGMA user_version').scalar()
            if version > SCHEMA_VERSION:
                raise RuntimeError('Veritabanı daha yeni bir uygulama sürümüne ait.')
            for table in Base.metadata.sorted_tables:
                columns = connection.exec_driver_sql(f'PRAGMA table_info({table.name})').all()
                if columns and {r[1] for r in columns} != {c.name for c in table.columns}:
                    raise RuntimeError('Veritabanı şeması uyumsuz: ' + table.name)
        if backup_before_migration and version < SCHEMA_VERSION:
            with self.engine.connect() as connection:
                has_models = bool(connection.exec_driver_sql("SELECT 1 FROM sqlite_master WHERE name='models'").first())
            if has_models:
                from app.backup import snapshot
                from app.config import PATHS
                from app.paths import is_desktop
                snapshot(self.path, PATHS.backups if is_desktop() else self.path.parent/'backups', prefix='before-migration')
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            version = connection.exec_driver_sql('PRAGMA user_version').scalar()
            if version > SCHEMA_VERSION:
                raise RuntimeError('Veritabanı daha yeni bir uygulama sürümüne ait.')
            if version < 5:
                migrate_classifications(connection)
            connection.exec_driver_sql(f'PRAGMA user_version={SCHEMA_VERSION}')

    @contextmanager
    def session(self, write=False):
        with Session(self.engine) as session:
            if write:
                # Acquire the SQLite write lock before checking revisions.
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            try:
                yield session
                if write:
                    session.commit()
            except Exception:
                session.rollback()
                raise

    def dump(self):
        # SQLite backup produces a coherent snapshot even during writes.
        with closing(sqlite3.connect(str(self.path))) as source, closing(sqlite3.connect(':memory:')) as target:
            source.backup(target)
            return '\n'.join(target.iterdump())

    def close(self):
        self.engine.dispose()
