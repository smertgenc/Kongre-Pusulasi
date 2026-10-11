"""Preview a SQLite upload, then switch to a managed copy without replacing user files."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from threading import Lock
import time
import uuid
from starlette.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.backup import snapshot, validate
from app.database import Database, SCHEMA_VERSION
from app.models import Base
from app.services import CongressService, ConflictError
from engine import calculate_model, score

MAX_DATABASE_BYTES = 100 * 1024 * 1024
PREVIEW_TTL = 30 * 60

def connection_file(base): return Path(base).with_name(Path(base).name+'.connection.json')
def connections_dir(base): return Path(base).with_name(Path(base).name+'.connections')

def read_connection(base):
    base=Path(base).resolve(); config=connection_file(base)
    if not config.exists(): return base, base.name
    try:
        data=json.loads(config.read_text(encoding='utf-8'))
        filename=data['file']
        if not re.fullmatch(r'[a-f0-9]{32}\.db',filename): raise ValueError()
        target=connections_dir(base)/filename
        if target.is_symlink() or not target.is_file(): raise ValueError()
        return target, str(data.get('label') or filename)[:200]
    except (OSError,ValueError,KeyError,TypeError):
        raise ValueError('Kayıtlı veritabanı bağlantısı bulunamadı. Bağlantı dosyasını ve çalışma kopyasını kontrol edin; eski veritabanınız korunuyor.') from None

def active_database_path(base): return read_connection(base)[0]

class DatabaseGate:
    """A switch cannot overlap HTTP requests, including their AI background tasks."""
    def __init__(self):
        self.lock=Lock();self.active=0;self.switching=False

class DatabaseBoundary:
    def __init__(self,app,*,gate,connections):
        self.app=app;self.gate=gate;self.connections=connections
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope['path'].startswith('/api/'):
            return await self.app(scope,receive,send)
        exclusive=scope['path']=='/api/database/connect' and scope['method']=='POST'
        error=None
        with self.gate.lock:
            if self.gate.switching or (exclusive and self.gate.active):
                error='Devam eden işlem veya AI analizi var. İşlem tamamlandıktan sonra tekrar deneyin.'
            else:
                token=dict(scope['headers']).get(b'x-ahp-database',b'').decode('ascii',errors='replace')
                if scope['method'] not in ('GET','HEAD','OPTIONS') and token and token!=self.connections.identity:
                    error='Veritabanı başka bir pencerede değişti. Kaydetmeden önce sayfayı yenileyin.'
                else:
                    if exclusive:self.gate.switching=True
                    else:self.gate.active+=1
        if error:
            return await JSONResponse({'error':error},status_code=409)(scope,receive,send)
        try: await self.app(scope,receive,send)
        finally:
            with self.gate.lock:
                if exclusive:self.gate.switching=False
                else:self.gate.active-=1

class DatabaseConnections:
    def __init__(self,base,db):
        self.base=Path(base).resolve();self.db=db
        _,self.label=read_connection(self.base)
        self.pending={};self.lock=Lock()
        self.pending_dir=self.base.with_name(self.base.name+'.pending')

    @property
    def identity(self): return hashlib.sha256(str(self.db.path).encode()).hexdigest()[:32]

    def status(self):
        with closing(sqlite3.connect(self.db.path)) as connection:
            counts={table:connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                    for table in ('models','congresses','evaluations','ai_analyses')}
            counts['active_congresses']=connection.execute('SELECT count(*) FROM congresses WHERE id NOT IN (SELECT congress_id FROM congress_deletions)').fetchone()[0]
        return {'label':self.label,'path':str(self.db.path),'database_id':self.identity,
                'schema_version':SCHEMA_VERSION,'counts':counts,'max_bytes':MAX_DATABASE_BYTES,
                'managed_copy':self.db.path!=self.base}

    def new_upload(self):
        self.pending_dir.mkdir(parents=True,exist_ok=True)
        self.cleanup()
        fd,name=tempfile.mkstemp(dir=self.pending_dir,suffix='.db');os.close(fd)
        return Path(name)

    def cleanup(self):
        with self.lock:
            for token,item in list(self.pending.items()):
                if time.time()-item['created']>PREVIEW_TTL:
                    item['path'].unlink(missing_ok=True);del self.pending[token]
            # Remove abandoned uploads from previous sessions after a day.
            for path in self.pending_dir.glob('*.db'):
                if time.time()-path.stat().st_mtime>86400:path.unlink(missing_ok=True)

    def inspect(self,path,label):
        """Validate and migrate only the uploaded copy. The selected source is untouched."""
        path=Path(path)
        label=Path(label.replace('\\','/')).name[:200] or 'SQLite veritabanı'
        temporary=None;accepted=False
        try:
            with path.open('rb') as stream:
                if stream.read(16)!=b'SQLite format 3\x00': raise ValueError('Gerçek bir SQLite .db dosyası seçin. SQL metni veya şifreli veritabanı desteklenmiyor.')
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('PRAGMA trusted_schema=OFF')
                deadline=time.monotonic()+15
                connection.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
                objects=connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall()
                if any(name not in Base.metadata.tables and name!='sqlite_sequence' for name,_ in objects):
                    raise ValueError('Bu SQLite dosyası Kongre Pusulası veri yapısına uymuyor.')
                if any('VIRTUAL TABLE' in (sql or '').upper() for _,sql in objects):
                    raise ValueError('Bu veritabanı desteklenmeyen tablolar içeriyor.')
                validate(connection)
            temporary=Database(path);temporary.initialize(backup_before_migration=False)
            state=CongressService(temporary).state()
            if not state['models']: raise ValueError('Dosyada kullanılabilir bir AHP modeli yok.')
            expected={f'K{i}' for i in range(1,11)}
            models={m['id']:m for m in state['models']}
            for model in state['models']:
                if set(model['weights'])!=expected or not isinstance(model['thresholds'],dict):
                    raise ValueError('Dosyadaki AHP modeli uyumlu değil.')
                # Check the same numeric rules as the engine without changing saved values.
                calculate_model(model['matrices'],model['thresholds'])
                score(model['weights'],dict.fromkeys(expected),model['thresholds'])
            for congress in state['congresses']:
                if not congress['evaluations'] or not all(k in congress['metadata'] for k in ('name','edition')):
                    raise ValueError('Dosyadaki kongre kayıtları eksik veya uyumsuz.')
                for evaluation in congress['evaluations']:
                    model=models[evaluation['model_id']]
                    score(model['weights'],evaluation['utilities'],model['thresholds'])
                    if not {'total','lower','upper','coverage','missing','contributions','status'}<=evaluation['result'].keys():
                        raise ValueError('Dosyadaki değerlendirme sonuçları eksik.')
            # Interrupted jobs from another computer must never appear to be still running.
            from app.ai_service import recover_interrupted_analyses
            recover_interrupted_analyses(temporary)
            with closing(sqlite3.connect(path)) as connection:
                validate(connection)
                counts={table:connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                        for table in ('models','congresses','evaluations','ai_analyses')}
            counts['active_congresses']=len(state['congresses'])
            temporary.close();temporary=None
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            token=uuid.uuid4().hex
            item={'path':path,'label':label,'counts':counts,'digest':digest,'created':time.time()}
            with self.lock:self.pending[token]=item
            accepted=True
            return {'token':token,'label':label,'counts':counts,'schema_version':SCHEMA_VERSION,'expires_in':PREVIEW_TTL}
        except (sqlite3.Error,SQLAlchemyError,RuntimeError,KeyError,TypeError,AttributeError,json.JSONDecodeError):
            raise ValueError('Veritabanı okunamadı veya kayıtları uygulamayla uyumsuz. Uygulamadan alınmış sağlam bir .db yedeği seçin.') from None
        finally:
            if temporary:temporary.close()
            if not accepted:path.unlink(missing_ok=True)

    def connect(self,token,expected_id):
        if expected_id!=self.identity:raise ConflictError('Veritabanı değişti. Sayfayı yenileyip dosyayı tekrar seçin.')
        with self.lock:item=self.pending.get(token)
        if not item or time.time()-item['created']>PREVIEW_TTL:
            raise ValueError('Dosya önizlemesinin süresi doldu. Dosyayı yeniden seçin.')
        with item['path'].open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=item['digest']:
                raise ValueError('Önizlenen dosya değişti. Dosyayı yeniden seçin.')
        # Keep both a coherent recovery copy and the original database in place.
        backup=snapshot(self.db.path,self.base.parent/'backups',prefix='before-connect')
        directory=connections_dir(self.base);directory.mkdir(parents=True,exist_ok=True)
        target=directory/(uuid.uuid4().hex+'.db')
        old_engine=self.db.engine
        config=connection_file(self.base)
        replacement=None;temporary=None
        try:
            os.replace(item['path'],target)
            replacement=Database(target)
            fd,temporary=tempfile.mkstemp(dir=config.parent,prefix='.connection-',suffix='.tmp')
            # Ensure we can open the final path before persisting its selection.
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                with replacement.engine.connect() as connection:connection.exec_driver_sql('SELECT 1 FROM models LIMIT 1')
                json.dump({'file':target.name,'label':item['label']},stream,ensure_ascii=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,config)
        except Exception:
            if replacement:replacement.close()
            # Return the prepared copy to its preview slot so a failed switch is retryable.
            if target.exists():os.replace(target,item['path'])
            raise
        finally:
            if temporary:Path(temporary).unlink(missing_ok=True)
        self.db.engine=replacement.engine;self.db.path=target;self.label=item['label']
        old_engine.dispose()
        with self.lock:self.pending.pop(token,None)
        return {**self.status(),'previous_backup':str(backup)}
