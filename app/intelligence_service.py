"""Coordinates profiles, immutable congress snapshots and lazy fingerprint caches."""
import json
from sqlalchemy import select, func, literal_column
from app.models import Congress, Evaluation, AIAnalysis, ConferenceFingerprint, CongressDeletion
from app.services import require_active, now, encode, NotFoundError, ConflictError
from app.intelligence_config import load_intelligence_config
from app.text_similarity import LocalTextSimilarity
from app.personalization_service import PersonalizationService
from app.fingerprint_service import generate_fingerprint, calculate_fingerprint_similarity, stable_hash, FINGERPRINT_VERSION
from app.recommendation_service import RecommendationService

SOURCE_TEXT_PROJECTION = literal_column("(SELECT json_group_array(json_object('segments',json_extract(value,'$.segments'))) FROM json_each(ai_analyses.data,'$.sources'))")

class IntelligenceService:
    def __init__(self, db, ai):
        self.db,self.ai=db,ai
        self.config=load_intelligence_config()
        self.text=LocalTextSimilarity(self.config['aliases'])
        self.profiles=PersonalizationService(db,self.text)
        self.recommendations=RecommendationService(self.config,self.text,self.profiles)

    def _record(self, cid: str, evaluation: dict, sources: list[dict]) -> dict:
        meta=evaluation['metadata'];research=meta.get('research') or {}
        source_text='\n'.join(str(p.get('text','')) for source in sources for p in source.get('segments',[]))[:self.config['maximum_text_characters']]
        academic='\n'.join([meta.get('name',''),research.get('description',''),research.get('call_for_papers',''),
                            ' '.join(research.get('research_fields',[])+research.get('topics',[])+research.get('keywords',[])),source_text])
        return {'id':cid,'metadata':meta,'evaluation':evaluation,'academic_text':academic,'source_text':source_text,
                'utilities':evaluation.get('utilities',{}),'result':evaluation.get('result',{})}

    def _library(self) -> list[dict]:
        """One query for latest evaluations plus one for text-only source snapshots."""
        with self.db.session() as session:
            ranked=select(Evaluation.id.label('id'),func.row_number().over(partition_by=Evaluation.congress_id,
                order_by=(Evaluation.created_at.desc(),Evaluation.id)).label('rank')).subquery()
            rows=session.scalars(select(Evaluation).join(ranked,ranked.c.id==Evaluation.id)
                .where(ranked.c.rank==1,~Evaluation.congress_id.in_(select(CongressDeletion.congress_id)))).all()
            evaluations=[(r.congress_id,{'id':r.id,'model_id':r.model_id,'created_at':r.created_at,**json.loads(r.data)}) for r in rows]
            ids={e['analysis_id'] for _,e in evaluations if e.get('analysis_id')}
            sources={}
            if ids:
                # Project only segments in SQLite; do not load archived image bytes.
                for aid,raw in session.execute(select(AIAnalysis.id,SOURCE_TEXT_PROJECTION).where(AIAnalysis.id.in_(ids))):
                    sources[aid]=json.loads(raw) if raw else []
        return [self._record(cid,e,sources.get(e.get('analysis_id'),[])) for cid,e in evaluations]

    def congress(self, cid: str, evaluation_id: str | None = None) -> dict:
        with self.db.session() as session:
            require_active(session,cid)
            query=select(Evaluation).where(Evaluation.congress_id==cid)
            if evaluation_id:query=query.where(Evaluation.id==evaluation_id)
            row=session.scalar(query.order_by(Evaluation.created_at.desc(),Evaluation.id).limit(1))
            if not row:raise NotFoundError('Kongrenin değerlendirmesi bulunamadı.')
            e={'id':row.id,'model_id':row.model_id,'created_at':row.created_at,**json.loads(row.data)}
            raw=session.scalar(select(SOURCE_TEXT_PROJECTION).select_from(AIAnalysis).where(AIAnalysis.id==e.get('analysis_id'))) if e.get('analysis_id') else None
        return self._record(cid,e,json.loads(raw) if raw else [])

    def _analysis(self, aid: str) -> dict:
        data=self.ai.get(aid)
        if data['status']!='ready':raise ConflictError('Bu bilgiler için analizin tamamlanmış olması gerekir.')
        analysis=data['analysis'];review=data.get('review')
        meta=dict(review['metadata'] if review else analysis['metadata']);meta['context']=data['context']
        if not meta.get('website'):
            meta['website']=next((s['url'] for s in data['sources'] if s.get('kind')=='url' and s.get('url')),'')
        e={'id':review['saved']['evaluation_id'] if review else None,'model_id':data['model']['id'],'metadata':meta,
           'scale':1,'policy_version':analysis.get('policy_version'),'mode':'ai_reviewed',
           'utilities':{k:v['final_value'] for k,v in review['decisions'].items()} if review else analysis['utilities'],
           'result':review['saved']['result'] if review else analysis['result']}
        # Reviewed analysis uses its own snapshot, not the congress's newest evaluation.
        return self._record(review['saved']['id'] if review else 'analysis:'+aid,e,data['sources'])

    def fingerprint(self, record: dict, *, persist: bool = True) -> dict:
        dependency={'version':FINGERPRINT_VERSION,'metadata':record['metadata'],'academic_text':record['academic_text'],
                    'source_text':record['source_text'],'aliases':self.config['aliases']}
        digest=stable_hash(dependency);cid=record['id'];eid=record['evaluation'].get('id')
        if not persist or not eid:return generate_fingerprint(record,self.text)
        with self.db.session() as session:
            row=session.get(ConferenceFingerprint,cid)
            if row and row.source_hash==digest and row.evaluation_id==eid:return json.loads(row.data)
        data=generate_fingerprint(record,self.text)
        with self.db.session(write=True) as session:
            # Cache only current, active records; old report views cannot replace it.
            if not session.get(Congress,cid) or session.get(CongressDeletion,cid):return data
            latest=session.scalar(select(Evaluation.id).where(Evaluation.congress_id==cid).order_by(Evaluation.created_at.desc(),Evaluation.id).limit(1))
            if latest!=eid:return data
            row=session.get(ConferenceFingerprint,cid);timestamp=now()
            if row:
                row.evaluation_id=eid;row.source_hash=digest;row.data=encode(data);row.updated_at=timestamp
            else:session.add(ConferenceFingerprint(conference_id=cid,evaluation_id=eid,source_hash=digest,data=encode(data),created_at=timestamp,updated_at=timestamp))
        return data

    def insights(self, cid: str | None = None, *, aid: str | None = None, evaluation_id: str | None = None) -> dict:
        target=self._analysis(aid) if aid else self.congress(cid,evaluation_id)
        profile=self.profiles.get_profile();candidates=self._library()
        fingerprint=self.fingerprint(target,persist=not bool(aid))
        organizational=[]
        for candidate in candidates:
            if candidate['id']==target['id'] or candidate['metadata'].get('sample') or target['metadata'].get('sample'):continue
            similarity=calculate_fingerprint_similarity(fingerprint,self.fingerprint(candidate),self.config,self.text)
            if similarity['score'] is None or similarity['score']<=0:continue
            organizational.append({'id':candidate['id'],'name':candidate['metadata'].get('name',''),
                                   'edition':candidate['metadata'].get('edition',''),**similarity})
        organizational.sort(key=lambda x:(-x['score'],-x['coverage'],x['id']))
        return {'personal_fit':self.profiles.personal_fit(target,profile),'profile_updated_at':profile.get('updated_at'),
                'fingerprint':fingerprint,'organizational_matches':organizational[:self.config['maximum_recommendations']],
                'recommendations':self.recommendations.recommend(target,candidates,profile),
                'evaluation_id':target['evaluation'].get('id'),'method':self.text.version}

    def personal_fit(self, cid: str, evaluation_id: str | None = None) -> dict:
        return self.profiles.personal_fit(self.congress(cid,evaluation_id),self.profiles.get_profile())

    def recommend(self, cid: str, evaluation_id: str | None = None) -> dict:
        return self.recommendations.recommend(self.congress(cid,evaluation_id),self._library(),self.profiles.get_profile())
