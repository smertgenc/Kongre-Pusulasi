"""Application use cases. HTTP/UI-independent; AHP remains in engine.py."""
import csv
import io
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.config import ROOT
from app.models import Congress, Evaluation, ModelVersion, CongressDeletion
from app.schemas import EvaluationInput, ModelInput, PublishModelInput, ScenarioInput
from engine import CRITERIA, DEFAULT_MATRICES, calculate_model, score, scenario_weights

def now():
    return datetime.now(timezone.utc).isoformat()

def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)

def identity(meta):
    return ' '.join((meta['name'] + '|' + meta['edition']).casefold().split())

def serialize_model(row):
    return {'id': row.id, 'version': row.version, 'name': row.name,
            'created_at': row.created_at, **json.loads(row.data)}

def require_active(session, cid):
    congress=session.get(Congress,cid)
    if not congress:
        raise NotFoundError('Kongre bulunamadı.')
    if session.get(CongressDeletion,cid):
        raise ConflictError('Kongre çöp kutusunda. Önce Çöp kutusu ekranından geri yükleyin.')
    return congress

def check_identity(session, meta, cid=None, *, active_conflict=True):
    existing=session.scalar(select(Congress).where(Congress.identity_key==identity(meta)))
    if existing and existing.id != cid:
        if session.get(CongressDeletion,existing.id):
            raise ConflictError('Aynı ad ve edisyon çöp kutusunda. Kongreler → Çöp kutusu ekranından geri yükleyin.')
        if active_conflict: raise ConflictError('Bu ad ve edisyon zaten var. Mevcut kongreye değerlendirme ekleyin.')

class ConflictError(ValueError):
    pass

class NotFoundError(ValueError):
    pass

class CongressService:
    def __init__(self, db):
        self.db = db

    def initialize(self):
        self.db.initialize()
        with self.db.session(write=True) as session:
            if session.scalar(select(ModelVersion.id).limit(1)):
                return
            model = calculate_model(DEFAULT_MATRICES)
            mid = str(uuid.uuid4())
            session.add(ModelVersion(id=mid, version=1, name='Excel başlangıç modeli', data=encode(model), created_at=now()))
            session.flush()
            fixtures = json.loads((ROOT/'analiz/hesaplama_sonuclari.json').read_text(encoding='utf-8'))
            for fixture in fixtures['congresses']:
                cid = str(uuid.uuid4())
                meta = {'name':fixture['name'], 'edition':'Excel örneği', 'start_date':'', 'end_date':'',
                        'location':'', 'organizer':'', 'website':'', 'format':'Belirtilmedi',
                        'context':'Excel referans verisi', 'sample':True}
                utilities = {c[0]:v for c,v in zip(CRITERIA, fixture['inputs'])}
                payload = {'metadata':meta, 'utilities':utilities,
                           'notes':{c[0]:'Excel’den aktarılmış örnek; kaynak kanıtı yok.' for c in CRITERIA},
                           'scale':1, 'evaluator':'Excel aktarımı',
                           'result':score(model['weights'], utilities, model['thresholds'])}
                session.add(Congress(id=cid, identity_key=identity(meta), metadata_json=encode(meta), created_at=now()))
                session.flush()
                session.add(Evaluation(id=str(uuid.uuid4()), congress_id=cid, model_id=mid,
                                       data=encode(payload), created_at=now()))

    def state(self):
        with self.db.session() as session:
            models = [serialize_model(r) for r in session.scalars(select(ModelVersion).order_by(ModelVersion.version.desc()))]
            grouped = {}
            for e in session.scalars(select(Evaluation).order_by(Evaluation.created_at.desc(), Evaluation.id)):
                grouped.setdefault(e.congress_id, []).append({'id':e.id, 'model_id':e.model_id,
                                                              'created_at':e.created_at, **json.loads(e.data)})
            congresses = [{'id':c.id, 'metadata':json.loads(c.metadata_json), 'evaluations':grouped.get(c.id, [])}
                          for c in session.scalars(select(Congress).where(~Congress.id.in_(select(CongressDeletion.congress_id))).order_by(Congress.created_at.desc(), Congress.id))]
        return {'models':models, 'congresses':congresses,
                'criteria':[{'code':c,'name':n,'group':g,'description':d} for c,n,g,d in CRITERIA]}

    def trash(self):
        with self.db.session() as session:
            rows=session.execute(select(Congress,CongressDeletion).join(CongressDeletion,Congress.id==CongressDeletion.congress_id).order_by(CongressDeletion.deleted_at.desc())).all()
            return [{'id':c.id,'metadata':json.loads(c.metadata_json),'deleted_at':d.deleted_at} for c,d in rows]

    def delete_congress(self, cid, previous_id):
        with self.db.session(write=True) as session:
            if not session.get(Congress,cid): raise NotFoundError('Kongre bulunamadı.')
            if not session.get(CongressDeletion,cid):
                latest=session.scalar(select(Evaluation).where(Evaluation.congress_id==cid).order_by(Evaluation.created_at.desc(),Evaluation.id).limit(1))
                if not latest or latest.id!=previous_id:
                    raise ConflictError('Kongre kaydı değişmiş. Sayfayı yenileyip tekrar silin.')
                session.add(CongressDeletion(congress_id=cid,deleted_at=now()))
        return {'id':cid,'deleted':True}

    def restore_congress(self, cid):
        with self.db.session(write=True) as session:
            if not session.get(Congress,cid): raise NotFoundError('Kongre bulunamadı.')
            marker=session.get(CongressDeletion,cid)
            if marker: session.delete(marker)
        return {'id':cid,'deleted':False}

    def save_evaluation(self, request: EvaluationInput):
        meta = request.metadata.model_dump()
        utilities = {k:None if v is None else v/request.scale for k,v in request.scores.items()}
        notes = {c[0]:request.notes.get(c[0], '').strip() for c in CRITERIA}
        with self.db.session(write=True) as session:
            m = session.get(ModelVersion, request.model_id)
            if not m:
                raise NotFoundError('Model bulunamadı.')
            model = serialize_model(m)
            result = score(model['weights'], utilities, model['thresholds'])
            cid = request.congress_id
            check_identity(session,meta,cid,active_conflict=False)
            if cid:
                congress = require_active(session, cid)
                latest = session.scalar(select(Evaluation).where(Evaluation.congress_id==cid)
                                        .order_by(Evaluation.created_at.desc(), Evaluation.id).limit(1))
                if not latest or request.previous_id != latest.id:
                    raise ConflictError('Bu kayıt değişmiş. Sayfayı yenileyip tekrar deneyin.')
                meta['sample'] = json.loads(congress.metadata_json).get('sample', False)
                congress.metadata_json = encode(meta)
                congress.identity_key = identity(meta)
            else:
                cid = str(uuid.uuid4())
                meta['sample'] = False
                session.add(Congress(id=cid, identity_key=identity(meta), metadata_json=encode(meta), created_at=now()))
            session.flush()
            eid = str(uuid.uuid4())
            payload = {'metadata':meta, 'utilities':utilities, 'notes':notes, 'scale':request.scale,
                       'evaluator':request.evaluator, 'result':result}
            session.add(Evaluation(id=eid, congress_id=cid, model_id=m.id, data=encode(payload), created_at=now()))
        return {'id':cid, 'evaluation_id':eid, 'result':result}

    def preview_model(self, request: ModelInput):
        return calculate_model(request.matrices, request.thresholds.model_dump())

    def publish_model(self, request: PublishModelInput):
        model = self.preview_model(request)
        if not model['consistent']:
            raise ValueError('CR > 0,10 olan matris var. Karşılaştırmaları gözden geçirin.')
        with self.db.session(write=True) as session:
            latest = session.scalar(select(ModelVersion).order_by(ModelVersion.version.desc()).limit(1))
            if latest.id != request.base_id:
                raise ConflictError('Yeni bir model sürümü var. Sayfayı yenileyin.')
            mid, version = str(uuid.uuid4()), latest.version + 1
            session.add(ModelVersion(id=mid, version=version, name=request.name, data=encode(model), created_at=now()))
        return {'id':mid, 'version':version}

    def scenario(self, request: ScenarioInput):
        data = self.state()
        model = next((m for m in data['models'] if m['id']==request.model_id), None)
        if not model:
            raise NotFoundError('Model bulunamadı.')
        weights = scenario_weights(model['weights'], request.criterion, request.target)
        results = []
        for c in data['congresses']:
            e = next((e for e in c['evaluations'] if e['model_id']==model['id']), None)
            if e:
                results.append({'id':c['id'], 'name':e['metadata']['name'], 'context':e['metadata']['context'],
                                'scale':e['scale'], 'before':e['result'],
                                'after':score(weights, e['utilities'], model['thresholds'])})
        return {'weights':weights, 'results':results}

    def export_csv(self):
        data = self.state()
        models = {m['id']:m['version'] for m in data['models']}
        out = io.StringIO()
        writer = csv.writer(out, delimiter=';')
        writer.writerow(['Kongre','Edisyon','Model','Tarih','Değerlendiren','Puan','Durum','Kapsam']+[c[0] for c in CRITERIA])
        def safe(value):
            text = str(value)
            return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r')) else text
        for c in data['congresses']:
            for e in c['evaluations']:
                r, meta = e['result'], e['metadata']
                writer.writerow([safe(meta['name']),safe(meta['edition']),models[e['model_id']],e['created_at'],
                                 safe(e['evaluator']),r['total'] if r['total'] is not None else '',r['status'],r['coverage']]
                                +[e['utilities'][k[0]] for k in CRITERIA])
        return '\ufeff' + out.getvalue()
