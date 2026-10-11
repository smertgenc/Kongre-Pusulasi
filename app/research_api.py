"""Local optional research endpoints using the application's existing boundaries."""
from typing import Literal
from pydantic import Field
from fastapi.responses import FileResponse
from app.input_model import InputModel
from app.research_store import ResearchStore
from app.config import ROOT

class EnabledInput(InputModel):
    enabled: bool
class StudyInput(InputModel):
    title: str=Field(min_length=1,max_length=200)
    kind: Literal['demo','synthetic','research']='demo'
    seed: int=42
    tasks: int=Field(default=24,ge=12,le=80)
    alternatives: int=Field(default=3,ge=2,le=3)
    attributes: list[dict] | None=None
    forbidden: list[dict]=Field(default_factory=list,max_length=100)
    collection_authorized: bool=False
    approval_reference: str=Field(default='',max_length=300)
    consent_version: str=Field(default='',max_length=80)
    consent_text: str=Field(default='',max_length=5000)
    data_management_reference: str=Field(default='',max_length=300)
class ChoiceInput(InputModel):
    respondent: str=Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    task: str=Field(max_length=4)
    choice: int=Field(ge=0,le=2)
    consent: bool=False
    consent_version: str=Field(default='',max_length=80)

def register_research(app,db,service):
    store=ResearchStore(db);app.state.research=store
    @app.get('/research.js',include_in_schema=False)
    def javascript():return FileResponse(ROOT/'static/research.js',media_type='text/javascript')
    @app.get('/api/research/status')
    def status():return store.status()
    @app.post('/api/research/settings')
    def settings(request:EnabledInput):return store.enable(request.enabled)
    @app.post('/api/research/studies',status_code=201)
    def create(request:StudyInput):return store.create(request)
    @app.get('/api/research/studies/{sid}')
    def read(sid:str):return store.get(sid)
    @app.post('/api/research/studies/{sid}/responses')
    def respond(sid:str,request:ChoiceInput):return store.respond(sid,request)
    @app.post('/api/research/studies/{sid}/estimate')
    def estimate(sid:str):return store.estimate(sid)

    @app.get('/api/research/dataset-schema')
    def dataset_schema():return ResearchDataset.model_json_schema()
    @app.post('/api/research/experiments')
    def experiment(request:ExperimentInput):
        import json,os,uuid
        from sqlalchemy import select
        from app.models import ModelVersion
        from app.services import serialize_model,ConflictError,NotFoundError
        with store.connection() as c:
            store.require_enabled(c)
            study=store.read(c,request.study_id) if request.study_id else None
            if request.dataset.origin=='research' and (not study or study['kind']!='research'):raise ValueError('Gerçek veri deneyi izinli araştırma çalışmasına bağlanmalıdır.')
            if study and not study['model']:raise ConflictError('Önce CBC modelini tahmin edin.')
            with db.session() as session:
                row=session.get(ModelVersion,request.dataset.ahp_model_id)
                if not row:raise NotFoundError('AHP modeli bulunamadı.')
                model=serialize_model(row)
            report=run_experiment(request,model,study['model'] if study else None,ROOT)
            run_id=uuid.uuid4().hex;report['run_id']=run_id
            folder=store.path.with_suffix('.runs');folder.mkdir(mode=0o700,exist_ok=True)
            target=folder/(run_id+'.json')
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,allow_nan=False,indent=2)
        return report

from app.research_experiments import ExperimentInput,ResearchDataset,run_experiment
