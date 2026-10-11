import json
import copy
import uuid
from threading import BoundedSemaphore
from sqlalchemy import select, func
from app.ai_provider import get_provider, PROMPT_VERSION, ProviderError
from app.ai_failover import AnalysisRunner, public_connection
from app.connection_errors import ConnectionFailure
from app.ai_method import DEFAULT_CONTEXT, method_snapshot
from app.ai_rules import validate_evidence
from app.congress_policy import apply_policy
from app.ai_settings import AISettings
from app.models import AIAnalysis, AIReview, ModelVersion, Congress, Evaluation, CongressDeletion, AIAnalysisDeletion
from app.search import search_web
from app.services import now, encode, identity, serialize_model, ConflictError, NotFoundError, require_active, check_identity
from app.sources import extract_sources
from engine import score

def recover_interrupted_analyses(db):
    with db.session(write=True) as session:
        for row in session.scalars(select(AIAnalysis).where(AIAnalysis.status=='processing')):
            data=json.loads(row.data); data['error']='Uygulama kapanırken analiz yarıda kaldı. Kayıtlı kaynaklarla tekrar deneyebilirsiniz; saklanan tamamlanmış parçalar yeniden gönderilmez.'
            data['stage']='Analiz kesildi; kayıtlı ilerleme korundu'
            row.status='failed'; row.data=encode(data)

class AIService:
    def __init__(self, db, settings_path=None, provider=None):
        self.db=db
        self.settings=AISettings(settings_path)
        self.provider=provider
        self.capacity=BoundedSemaphore(2)

    def recover(self):
        recover_interrupted_analyses(self.db)

    def list(self, deleted=False):
        with self.db.session() as session:
            # Do not load base64 images / full source archives for a history list.
            query=select(AIAnalysis.id,AIAnalysis.status,AIAnalysis.created_at,
                         func.json_extract(AIAnalysis.data,'$.analysis.metadata.name').label('name'),
                         func.coalesce(func.nullif(func.json_extract(AIAnalysis.data,'$.analysis.metadata.website'),''),
                                       func.json_extract(AIAnalysis.data,'$.sources[0].url')).label('website'),
                         func.json_extract(AIReview.data,'$.saved.id').label('congress_id'))
            query=query.outerjoin(AIReview,AIReview.analysis_id==AIAnalysis.id)
            query=query.outerjoin(AIAnalysisDeletion,AIAnalysisDeletion.analysis_id==AIAnalysis.id)
            query=query.where(AIAnalysisDeletion.analysis_id.is_not(None) if deleted else AIAnalysisDeletion.analysis_id.is_(None))
            return [{'id':r.id,'status':r.status,'created_at':r.created_at,
                     'name':r.name or 'Kongre analizi', 'congress_id':r.congress_id, 'website':r.website or ''}
                    for r in session.execute(query.order_by(AIAnalysis.created_at.desc()).limit(100))]

    def delete(self, aid):
        with self.db.session(write=True) as session:
            row=session.execute(select(AIAnalysis.status).where(AIAnalysis.id==aid)).first()
            if not row: raise NotFoundError('Analiz bulunamadı.')
            if row.status=='processing': raise ConflictError('Çalışan analiz tamamlanmadan silinemez.')
            if not session.get(AIAnalysisDeletion,aid):session.add(AIAnalysisDeletion(analysis_id=aid,deleted_at=now()))
        return {'id':aid,'deleted':True}

    def restore(self, aid):
        with self.db.session(write=True) as session:
            if not session.scalar(select(AIAnalysis.id).where(AIAnalysis.id==aid)): raise NotFoundError('Analiz bulunamadı.')
            row=session.get(AIAnalysisDeletion,aid)
            if row:session.delete(row)
        return {'id':aid,'deleted':False}

    def clear_history(self):
        with self.db.session(write=True) as session:
            rows=session.execute(select(AIAnalysis.id,AIAnalysis.status).outerjoin(AIAnalysisDeletion,AIAnalysisDeletion.analysis_id==AIAnalysis.id)
                                 .where(AIAnalysisDeletion.analysis_id.is_(None))).all()
            finished=[r for r in rows if r.status!='processing']
            for row in finished:session.add(AIAnalysisDeletion(analysis_id=row.id,deleted_at=now()))
            return {'deleted':len(finished),'processing':len(rows)-len(finished)}

    def get(self, aid):
        with self.db.session() as session:
            row=session.get(AIAnalysis,aid)
            if not row: raise NotFoundError('Analiz bulunamadı.')
            result={'id':row.id,'status':row.status,'created_at':row.created_at,**json.loads(row.data)}
            result['deleted']=bool(session.get(AIAnalysisDeletion,aid))
            latest=session.execute(select(AIAnalysis.id,AIAnalysis.status).outerjoin(AIAnalysisDeletion,AIAnalysisDeletion.analysis_id==AIAnalysis.id)
                .where(func.json_extract(AIAnalysis.data,'$.retry_of')==aid,AIAnalysisDeletion.analysis_id.is_(None))
                .order_by(AIAnalysis.created_at.desc()).limit(1)).first()
            if latest:result['latest_retry']={'id':latest.id,'status':latest.status}

            review=session.scalar(select(AIReview).where(AIReview.analysis_id==aid))
            if review:
                result['review']=json.loads(review.data)
                result['review']['saved']['deleted']=bool(session.get(CongressDeletion,result['review']['saved']['id']))
            result.pop('execution',None)  # Internal resume state duplicates source passages.
        return result

    def _connection(self, request):
        active,connections=self.settings.analysis_connections()
        connection=connections[active]
        if request.provider_id!=connection.provider_id or (request.provider_model is not None and request.provider_model!=connection.model):
            raise ConflictError('AI bağlantısı değişmiş. Analiz sayfasını yenileyip seçili sağlayıcıyı kontrol edin.')
        if not connection.key:raise ConflictError('AI bağlantısı kurulmamış. AI bağlantısı ekranından API anahtarınızı ekleyin.')
        plan=[connection];seen={active}
        for selected in request.fallback_providers:
            fallback=connections[selected.provider_id]
            if fallback.provider_id in seen:
                raise ConflictError('Otomatik geçiş listesinde her AI sağlayıcısı yalnızca bir kez yer alabilir.')
            if not fallback.key or fallback.model!=selected.provider_model:
                raise ConflictError('Yedek AI bağlantıları değişmiş. Sayfayı yenileyip otomatik geçiş listesini kontrol edin.')
            seen.add(fallback.provider_id);plan.append(fallback)
        return tuple(plan)

    def _data(self, model, context, connections, scoring_policy='legacy'):
        connection=connections[0]
        return {'model':model,'context':context or ('Bilimsel kaynak kanıtı · congress-evidence-v1' if scoring_policy=='scientific' else DEFAULT_CONTEXT),'scoring_policy':scoring_policy,'method':method_snapshot(model,scoring_policy),
                'provider_model':connection.model,'provider_id':connection.provider_id,'provider_name':connection.provider.name,
                'requested_provider_id':connection.provider_id,'requested_provider_model':connection.model,
                'provider_plan':[public_connection(c) for c in connections],
                'prompt_version':PROMPT_VERSION,'stage':'Kaynaklar okunuyor','sources':[],'connection_events':[]}

    def prepare_analysis(self, request):
        connections=self._connection(request)
        search_connections={s.search_provider:self.settings.search_credentials(s.search_provider) for s in request.sources if s.kind=='search'}
        if any(not c.key for c in search_connections.values()):
            raise ConflictError('Seçili web arama servisinin anahtarı kayıtlı değil. AI bağlantısından ekleyin.')
        if not self.capacity.acquire(blocking=False):raise ConflictError('İki analiz zaten çalışıyor. Biri tamamlandığında tekrar deneyin.')
        try:
            with self.db.session(write=True) as session:
                m=session.get(ModelVersion,request.model_id) if request.model_id else session.scalar(select(ModelVersion).order_by(ModelVersion.version).limit(1))
                if not m:raise NotFoundError('AHP modeli bulunamadı.')
                aid=str(uuid.uuid4());data=self._data(serialize_model(m),request.context,connections,request.scoring_policy)
                session.add(AIAnalysis(id=aid,model_id=m.id,status='processing',data=encode(data),created_at=now()))
            return aid,data,connections,request.sources,search_connections
        except Exception:
            self.capacity.release();raise

    def prepare_retry(self, aid, request):
        connections=self._connection(request)
        connection=connections[0]
        if not self.capacity.acquire(blocking=False):raise ConflictError('İki analiz zaten çalışıyor. Biri tamamlandığında tekrar deneyin.')
        try:
            with self.db.session(write=True) as session:
                row=session.get(AIAnalysis,aid)
                if not row:raise NotFoundError('Analiz bulunamadı.')
                if session.get(AIAnalysisDeletion,aid):raise ConflictError('Önce analizi silinenlerden geri yükleyin.')
                if row.status!='failed':raise ConflictError('Yalnızca başarısız analiz yeniden denenebilir.')
                original=json.loads(row.data)
                if not original.get('sources'):raise ConflictError('Bu kayıtta okunmuş kaynak bulunmuyor. Kaynakları yeniden ekleyin.')
                previous=session.execute(select(AIAnalysis.id,AIAnalysis.status).outerjoin(AIAnalysisDeletion,AIAnalysisDeletion.analysis_id==AIAnalysis.id)
                    .where(func.json_extract(AIAnalysis.data,'$.retry_of')==aid,
                           func.coalesce(func.json_extract(AIAnalysis.data,'$.requested_provider_id'),func.json_extract(AIAnalysis.data,'$.provider_id'))==connection.provider_id,
                           func.coalesce(func.json_extract(AIAnalysis.data,'$.requested_provider_model'),func.json_extract(AIAnalysis.data,'$.provider_model'))==connection.model,
                           AIAnalysis.status.in_(['processing','ready']),AIAnalysisDeletion.analysis_id.is_(None))
                    .order_by(AIAnalysis.created_at.desc()).limit(1)).first()
                if not previous:
                    new_id=str(uuid.uuid4());data=self._data(original['model'],original.get('context',''),connections,original.get('scoring_policy','legacy'))
                    data.update(sources=original['sources'],retry_of=aid,stage='Kayıtlı kaynaklar yeniden değerlendiriliyor')
                    if original.get('execution') and original.get('prompt_version')==PROMPT_VERSION:
                        data['execution']=copy.deepcopy(original['execution'])
                        data['method']=original['method']
                        data['resumed_batches']=len(data['execution']['completed'])
                        data['completed_batches']=data['resumed_batches']
                    session.add(AIAnalysis(id=new_id,model_id=row.model_id,status='processing',data=encode(data),created_at=now()))
            if previous:
                self.capacity.release()
                return previous.id,None,None,None,None
            return new_id,data,connections,None,None
        except Exception:
            self.capacity.release();raise

    def run_analysis(self, aid, data, connections, source_inputs=None, search_connections=None):
        try:
            if source_inputs is not None:
                data['sources']=extract_sources(source_inputs,search=lambda query,pid:search_web(query,search_connections[pid]))
            data['stage']='Yapay zekâ kanıtları inceliyor'
            self._update(aid,'processing',data)
            connection=connections[0]
            def progress(event):
                data['connection_events'].append({**event,'at':now()})
                data['connection_progress']=event
                provider_name=event.get('provider_name',connection.provider.name)
                if event['phase']=='waiting':
                    data['stage']=f"{provider_name} geçici olarak yanıt veremedi. {event['delay_seconds']} saniye sonra {event['next_attempt']}/{event['max_attempts']}. deneme yapılacak."
                elif event['phase']=='request':data['stage']=f"{provider_name} kanıtları inceliyor · Bağlantı denemesi {event['attempt']}/{event['max_attempts']}"
                elif event['phase']=='complete':data['stage']='Kaynak yanıtı alındı'
                elif event['phase']=='batch':data['stage']=f'{provider_name} kaynak parçasını inceliyor'
                elif event['phase']=='resizing':data['stage']=f'{provider_name} token sınırına göre kaynak daha küçük parçalara ayrılıyor'
                elif event['phase']=='quota_wait':data['stage']=f"{provider_name} token kotası bekleniyor · {event['delay_seconds']} saniye"
                elif event['phase']=='provider_switch':data['stage']=f"{event['previous_provider']} devam edemedi; {provider_name} ile otomatik devam ediliyor. {event['completed_batches']} tamamlanmış parça korundu."
                elif event['phase']=='checkpoint':data['stage']=f"{event['completed_batches']} kaynak parçası tamamlandı ve kaydedildi"
                elif event['phase']=='merging':data['stage']='Tüm parçalardaki doğrulanmış kanıtlar birleştiriliyor'
                if event.get('batches',1)>1 and 'batch' in event:data['stage']+=f" · Parça {event['batch']}/{event['batches']}"
                self._update(aid,'processing',data)
            if self.provider is None:
                output=AnalysisRunner(connections,data,factory=get_provider,progress=progress,
                                      save=lambda:self._update(aid,'processing',data)).run()
            else:
                provider=self.provider or get_provider(connection.provider_id)
                if hasattr(provider,'on_progress'):provider.on_progress=progress
                output=provider.analyze(data['sources'],data['context'],connection.key,connection.model,ahp_method=data['method'])
            data['raw_output']=output.model_dump()
            from app.scientific_policy import apply_scientific_policy
            policy=apply_scientific_policy if data.get('scoring_policy')=='scientific' else apply_policy
            data['analysis']=policy(validate_evidence(output,data['sources'],data['model']),data['sources'],data['model'],data['method']['analysis_date'])
            data['stage']='İncelemeye hazır';data['completed_at']=now()
            self._update(aid,'ready',data)
        except Exception as exc:
            data['error']=str(exc) if isinstance(exc,(ValueError,ConflictError)) else 'Analiz tamamlanamadı. Kaynakları ve bağlantıyı kontrol edin.'
            data['stage']='Analiz tamamlanamadı'
            if isinstance(exc,ProviderError):data['error_details']=exc.details
            elif isinstance(exc,ConnectionFailure):
                data['error_details']={'provider':exc.service,'code':exc.code,'http_status':exc.http_status,
                                       'retryable':exc.code in ('TIMEOUT','RATE_LIMIT','DNS_ERROR','CONNECTION_ERROR','SERVICE_UNAVAILABLE')}
            self._update(aid,'failed',data)
        finally:self.capacity.release()

    def analyze(self, request):
        job=self.prepare_analysis(request)
        self.run_analysis(*job)
        return self.get(job[0])

    def progress(self, aid):
        with self.db.session() as session:
            row=session.execute(select(AIAnalysis.status,func.json_extract(AIAnalysis.data,'$.stage').label('stage'),
                                       func.json_extract(AIAnalysis.data,'$.connection_progress').label('progress')).where(AIAnalysis.id==aid)).first()
            if not row:raise NotFoundError('Analiz bulunamadı.')
            return {'id':aid,'status':row.status,'stage':row.stage,'connection_progress':json.loads(row.progress) if row.progress else None}

    def _update(self, aid, status, data):
        with self.db.session(write=True) as session:
            row=session.get(AIAnalysis,aid); row.status=status; row.data=encode(data)

    def review(self, aid, request):
        # One transaction saves the review, congress evaluation and final score together.
        with self.db.session(write=True) as session:
            row=session.get(AIAnalysis,aid)
            if not row: raise NotFoundError('Analiz bulunamadı.')
            previous=session.scalar(select(AIReview).where(AIReview.analysis_id==aid))
            if previous: return json.loads(previous.data)['saved']
            if session.get(AIAnalysisDeletion,aid): raise ConflictError('Bu analiz silinenler arasında. Önce analiz geçmişinden geri yükleyin.')
            if row.status!='ready': raise ConflictError('Yalnızca tamamlanan analiz incelenebilir.')
            data=json.loads(row.data); analysis=data['analysis']; model=data['model']
            if request.metadata.context != data['context']:
                raise ValueError('Analizin kayıtlı değerlendirme bağlamı değiştirilemez. Yeni bir analiz başlatın.')
            finals={}; audit={}; notes={}
            for f in analysis['findings']:
                code=f['criterion']; decision=request.decisions[code]
                value=None
                if decision.action=='approve':
                    if f['value'] is None or (not analysis.get('policy_version') and (f['status']!='detected' or not f['evidence'])):
                        raise ValueError(code+': onaylanabilir kanıt yok; düzeltin veya bilinmiyor seçin.')
                    value=f['value']
                elif decision.action=='correct':
                    if decision.value is None or not decision.note.strip():
                        raise ValueError(code+': düzeltmede değer ve gerekçe gereklidir.')
                    value=decision.value
                elif decision.action=='reject' and not decision.note.strip():
                    raise ValueError(code+': reddetme gerekçesi gereklidir.')
                finals[code]=None if value is None else int(value)
                audit[code]={'ai_value':f['value'],'user_value':decision.value if decision.action=='correct' else None,
                             'final_value':value,**decision.model_dump()}
                citations=' | '.join(f"{e['source_id']}/{e['segment_id']}: {e['quote']}" for e in f['evidence'])
                notes[code]=(decision.note or f['explanation'])+'\n'+citations
            result=score(model['weights'],finals,model['thresholds'])
            meta=request.metadata.model_dump(); meta['sample']=False
            check_identity(session,meta,request.congress_id)
            if request.congress_id:
                congress=require_active(session,request.congress_id)
                latest=session.scalar(select(Evaluation).where(Evaluation.congress_id==congress.id).order_by(Evaluation.created_at.desc(),Evaluation.id).limit(1))
                if not latest or latest.id!=request.previous_id: raise ConflictError('Kongre kaydı değişmiş. Sayfayı yenileyin.')
                cid=congress.id; congress.metadata_json=encode(meta); congress.identity_key=identity(meta)
            else:
                cid=str(uuid.uuid4()); session.add(Congress(id=cid,identity_key=identity(meta),metadata_json=encode(meta),created_at=now()))
            session.flush(); eid=str(uuid.uuid4())
            payload={'metadata':meta,'utilities':finals,'notes':notes,'scale':1,'evaluator':request.evaluator,'result':result,
                     'mode':'ai_reviewed','analysis_id':aid,'ai_confidence':analysis['confidence'],
                     'completeness':sum(v is not None for v in finals.values())/10,
                     'criteria_profile':analysis.get('criteria_profile','legacy'),
                     'decision_date':data['method']['analysis_date'],
                     'criterion_states':{f['criterion']:('positive' if finals[f['criterion']]==1 else 'negative' if finals[f['criterion']]==0 else f.get('state') if f.get('state') in ('conflict','not_applicable') else 'unknown') for f in analysis['findings']}}
            session.add(Evaluation(id=eid,congress_id=cid,model_id=row.model_id,data=encode(payload),created_at=now()))
            session.flush()
            raw_score=sum(finals.values()) if all(v is not None for v in finals.values()) else None
            if analysis.get('policy_version'):
                payload.update(policy_version=analysis['policy_version'],raw_score=raw_score,max_score=10,
                               evidence_completeness=analysis['completeness'],project_defaults=sum(f['basis']=='project_default' for f in analysis['findings']))
                session.get(Evaluation,eid).data=encode(payload)
            saved={'id':cid,'evaluation_id':eid,'result':result}
            if analysis.get('policy_version'): saved.update(raw_score=raw_score,max_score=10)
            review={'decisions':audit,'metadata':meta,'evaluator':request.evaluator,'saved':saved,'created_at':now()}
            session.add(AIReview(id=str(uuid.uuid4()),analysis_id=aid,evaluation_id=eid,data=encode(review),created_at=now()))
        return saved
