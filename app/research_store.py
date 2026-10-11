"""Opt-in sidecar database; never adds tables to the operational SQLite file."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
import sqlite3
import uuid
from app.conjoint import design,fit,synthetic_responses
from app.services import ConflictError,NotFoundError

def stamp():return datetime.now(timezone.utc).isoformat()

class ResearchStore:
    def __init__(self,db):self.db=db
    @property
    def path(self):return self.db.path.with_name(self.db.path.name+'.research.sqlite3')
    @contextmanager
    def connection(self,create=False):
        if not self.path.exists() and not create:raise ConflictError('Araştırma modülü kapalı.')
        connection=sqlite3.connect(self.path,timeout=30)
        try:
            self.path.chmod(0o600)
            if create:
                connection.executescript('''CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS studies(id TEXT PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS responses(study TEXT NOT NULL,person TEXT NOT NULL,task TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(study,person,task));''')
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            connection.commit()
        except Exception:connection.rollback();raise
        finally:connection.close()
    def status(self):
        if not self.path.exists():return {'enabled':False,'studies':[]}
        with self.connection() as c:
            row=c.execute('SELECT enabled FROM settings WHERE id=1').fetchone()
            enabled=bool(row and row[0]);studies=[json.loads(r[0]) for r in c.execute('SELECT data FROM studies')]
        return {'enabled':enabled,'studies':[{'id':s['id'],'title':s['title'],'kind':s['kind'],'estimated':bool(s.get('model'))} for s in studies] if enabled else []}
    def enable(self,value):
        if not value and not self.path.exists():return self.status()
        with self.connection(create=True) as c:c.execute('INSERT OR REPLACE INTO settings VALUES(1,?)',(int(value),))
        return self.status()
    def require_enabled(self,c):
        row=c.execute('SELECT enabled FROM settings WHERE id=1').fetchone()
        if not row or not row[0]:raise ConflictError('Araştırma modülü kapalı.')
    def read(self,c,sid):
        self.require_enabled(c);row=c.execute('SELECT data FROM studies WHERE id=?',(sid,)).fetchone()
        if not row:raise NotFoundError('Tercih araştırması bulunamadı.')
        return json.loads(row[0])
    def create(self,request):
        if request.kind=='research' and (not request.collection_authorized or not all((request.approval_reference,request.consent_version,request.consent_text,request.data_management_reference))):
            raise ValueError('Gerçek katılımcı çalışmasında kurum/etik izin referansı, onam sürümü/metni, veri yönetimi planı ve izin beyanı gereklidir.')
        d=design(request.attributes,request.seed,request.tasks,request.alternatives,request.forbidden)
        value={'id':uuid.uuid4().hex,'created_at':stamp(),**request.model_dump(),'design':d,'model':None}
        with self.connection() as c:
            self.require_enabled(c);c.execute('INSERT INTO studies VALUES(?,?)',(value['id'],json.dumps(value,ensure_ascii=False)))
        return value
    def get(self,sid):
        with self.connection() as c:
            value=self.read(c,sid);value['response_count']=c.execute('SELECT count(*) FROM responses WHERE study=?',(sid,)).fetchone()[0]
            return value
    def respond(self,sid,request):
        with self.connection() as c:
            study=self.read(c,sid)
            if study['kind']=='synthetic':raise ConflictError('Sentetik çalışmaya gerçek seçim eklenemez.')
            if study['model']:raise ConflictError('Tahmin edilmiş çalışma donduruldu. Yeni çalışma oluşturun.')
            task=next((t for t in study['design']['tasks'] if t['id']==request.task),None)
            if not task or not 0<=request.choice<len(task['alternatives']):raise ValueError('Seçim görevi/alternatifi geçersiz.')
            if study['kind']=='research' and (not request.consent or request.consent_version!=study['consent_version']):raise ValueError('Güncel bilgilendirilmiş onam gereklidir.')
            if c.execute('SELECT count(*) FROM responses WHERE study=?',(sid,)).fetchone()[0]>=10000:raise ConflictError('Bu teknik sürüm en fazla 10000 seçim kaydını destekler.')
            try:c.execute('INSERT INTO responses VALUES(?,?,?,?)',(sid,request.respondent,request.task,json.dumps({**request.model_dump(),'recorded_at':stamp()})))
            except sqlite3.IntegrityError:raise ConflictError('Bu katılımcı bu görevi zaten yanıtladı.') from None
        return {'saved':True}
    def estimate(self,sid):
        with self.connection() as c:
            study=self.read(c,sid)
            if study['model']:return study
            if study['kind']=='synthetic':
                rows=synthetic_responses(study['design'],seed=study['seed'])
            else:rows=[{k:json.loads(r[0])[k] for k in ('respondent','task','choice')} for r in c.execute('SELECT data FROM responses WHERE study=? ORDER BY person,task',(sid,))]
            model=fit(study['design'],rows);model.update(data_origin=study['kind'],estimated_at=stamp(),status='Teknik test; araştırma verisi gerekiyor' if study['kind']!='research' else 'Veri üzerinde tahmin edildi; bağımsız deneysel doğrulama gerekiyor')
            if study['kind']=='synthetic':
                for r in rows:c.execute('INSERT INTO responses VALUES(?,?,?,?)',(sid,r['respondent'],r['task'],json.dumps(r)))
            study['model']=model;c.execute('UPDATE studies SET data=? WHERE id=?',(json.dumps(study,ensure_ascii=False),sid))
            return study
