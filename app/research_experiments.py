"""Offline, versioned datasets; no provider clients or API keys are imported."""
from datetime import date,datetime,timezone
from pathlib import Path
import itertools
import platform
import re
from typing import Annotated,Literal
from urllib.parse import urlsplit,parse_qsl
from pydantic import Field,model_validator,field_validator
from app.input_model import InputModel
from app.conjoint import digest
from app.research_provenance import code_hashes
from app.research_models import compare_models,sensitivity
from app.research_metrics import binary_metrics,kendall,spearman,kappa,ndcg
from engine import score

class SourceReference(InputModel):
    url: str=Field(default='',max_length=2000)
    label: str=Field(max_length=200)
    content_hash: str=Field(pattern=r'^[0-9a-f]{64}$')
    retrieved_at: datetime=Field(strict=False)
    @field_validator('url')
    @classmethod
    def safe_url(cls,value):
        p=urlsplit(value)
        if value and (p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.fragment or any(re.search(r'key|token|secret|password|signature|credential',key,re.I) for key,_ in parse_qsl(p.query))):raise ValueError('Kaynak URL kimlik bilgisi veya gizli sorgu parametresi içeremez.')
        return value
class AIProvenance(InputModel):
    provider: str=Field(max_length=80)
    model: str=Field(max_length=200)
    prompt_version: str=Field(max_length=100)
    temperature: float|None=Field(default=None,ge=0,le=2,allow_inf_nan=False)
    seed: int|None=None
class ResearchRecord(InputModel):
    id: str=Field(min_length=1,max_length=80)
    congress_id: str=Field(min_length=1,max_length=80)
    edition: str=Field(min_length=1,max_length=100)
    decision_date: date=Field(strict=False)
    criteria_profile: str=Field(min_length=1,max_length=100)
    policy: str=Field(min_length=1,max_length=100)
    context: str=Field(min_length=1,max_length=500)
    scale: Literal[1]=1
    partition: Literal['train','test']
    attributes: dict[str,str]
    expert_values: dict[str,int|None]
    ai_values: dict[str,int|None]
    raters: dict[str,dict[str,int|None]]=Field(default_factory=dict,max_length=10)
    sources: list[SourceReference]=Field(default_factory=list,max_length=20)
    ai: AIProvenance
    missing_states: dict[str,Literal['unknown','not_applicable','conflict']]=Field(default_factory=dict)
    relevance: float=Field(ge=0,le=20,allow_inf_nan=False)
    decision_rationale: str=Field(min_length=1,max_length=2000)
    @model_validator(mode='after')
    def complete_codes(self):
        codes={f'K{i}' for i in range(1,11)}
        for values in [self.expert_values,self.ai_values,*self.raters.values()]:
            if set(values)!=codes or any(v is not None and (type(v)!=int or v not in (0,1)) for v in values.values()):raise ValueError('Her değerlendirme K1–K10 için 0, 1 veya null içermeli.')
        if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',r) for r in self.raters):raise ValueError('Uzmanlar için yalnız takma kod kullanın.')
        if not set(self.missing_states).issubset(codes):raise ValueError('Eksik veri kriter kodu geçersiz.')
        if any(self.ai_values[k] is not None for k in self.missing_states):raise ValueError('Eksik/uygulanamaz/çelişkili AI kriteri null olmalıdır.')
        return self
class ResearchDataset(InputModel):
    version: str=Field(min_length=1,max_length=100)
    origin: Literal['demo','synthetic','research']
    ahp_model_id: str=Field(min_length=1,max_length=100)
    records: list[ResearchRecord]=Field(min_length=2,max_length=100)
    @model_validator(mode='after')
    def split_integrity(self):
        if len({r.id for r in self.records})!=len(self.records):raise ValueError('Kayıt kimlikleri benzersiz olmalı.')
        series={}
        for r in self.records:series.setdefault(r.congress_id,set()).add(r.partition)
        if any(len(v)>1 for v in series.values()):raise ValueError('Aynı kongre serisi eğitim ve testte birlikte bulunamaz.')
        if len([r for r in self.records if r.partition=='test'])<2:raise ValueError('En az iki test kaydı gerekli.')
        return self
class ExperimentInput(InputModel):
    dataset: ResearchDataset
    study_id: str|None=Field(default=None,pattern=r'^[0-9a-f]{32}$')
    minimum_ahp: float=Field(ge=0,le=100,allow_inf_nan=False)
    overlap_acknowledged: Literal[True]
    protocol_rationale: str=Field(min_length=20,max_length=2000)
    seed: int=42
    ndcg_k: int=Field(default=5,ge=1,le=100)


def run_experiment(request,ahp,conjoint=None,root=None):
    ds=request.dataset
    if ahp['id']!=ds.ahp_model_id:raise ValueError('AHP model kimliği veri setiyle uyuşmuyor.')
    if conjoint and conjoint.get('data_origin')!=ds.origin:raise ValueError('CBC ve kongre veri setinin veri türü eşleşmeli.')
    test=[r.model_dump(mode='json') for r in ds.records if r.partition=='test']
    result=compare_models(test,ahp,conjoint,minimum_ahp=request.minimum_ahp,overlap_acknowledged=request.overlap_acknowledged)
    gold=[r['expert_values'][f'K{k}'] for r in test for k in range(1,11)];pred=[r['ai_values'][f'K{k}'] for r in test for k in range(1,11)]
    paired=[(r['M1']['total'],r['M4_ahp']['total']) for r in result['candidates'] if r['M1']['total'] is not None and r['M4_ahp']['total'] is not None]
    metrics={'ai_criteria':binary_metrics(gold,pred),'ahp_consistency_ratio':{k:v['cr'] for k,v in ahp['results'].items()},
             'expert_ai_paired_scores':{'n':len(paired),'mae':sum(abs(a-b) for a,b in paired)/len(paired) if paired else None,
                 'kendall_tau_b':kendall([a for a,_ in paired],[b for _,b in paired]),'spearman':spearman([a for a,_ in paired],[b for _,b in paired])}}
    raters=sorted({name for r in test for name in r['raters']});agreements=[]
    for a,b in itertools.combinations(raters,2):
        matching=[r for r in test if a in r['raters'] and b in r['raters']]
        av=[r['raters'][a][f'K{k}'] for r in matching for k in range(1,11)];bv=[r['raters'][b][f'K{k}'] for r in matching for k in range(1,11)]
        agreements.append({'raters':[a,b],'known_pairs':sum(x is not None and y is not None for x,y in zip(av,bv)),'cohen_kappa':kappa(av,bv)})
    metrics['expert_agreement']=agreements;relevance={r['id']:r['relevance'] for r in test}
    metrics['ndcg']={name:ndcg([relevance[i] for i in m['ranking']],request.ndcg_k,list(relevance.values())) for name,m in result['models'].items()}
    if conjoint:metrics['cbc_holdout']={k:conjoint[k] for k in ('holdout_n','holdout_accuracy','holdout_log_loss')}
    root=Path(root or Path(__file__).resolve().parents[1])
    manifest={'app_version':(root/'VERSION').read_text().strip(),'python':platform.python_version(),'platform':platform.system(),
              'code_hashes':code_hashes(root),
              'created_at':datetime.now(timezone.utc).isoformat(),'seed':request.seed,'dataset_version':ds.version,'dataset_hash':digest(ds.model_dump(mode='json')),
              'origin':ds.origin,'ahp_model':ahp,'conjoint_model':conjoint,'parameters':request.model_dump(mode='json',exclude={'dataset'}),
              'split':{p:[r.id for r in ds.records if r.partition==p] for p in ('train','test')},'live_api_calls':0}
    return {'manifest':manifest,'dataset':ds.model_dump(mode='json'),'results':result,'metrics':metrics,
            'sensitivity_example':sensitivity(ahp,test[0]['expert_values'],'K1',[max(0,ahp['weights']['K1']-.05),ahp['weights']['K1'],min(1,ahp['weights']['K1']+.05)],[ahp['thresholds'],{'average':60,'valid':80}]),
            'limitations':['Relevance ve uzman referanslarının bağımsız doğruluğu araştırmacı tarafından belgelenmelidir.','Sentetik/demo sonuçlar bilimsel araştırma bulgusu değildir.','M3/M4 eşik ve öznitelik protokolü veri görülmeden belirlenmeli; test verisiyle ayarlamayın.','Güven aralığı, bootstrap, katılımcı genellemesi ve anlamlılık testi bu sürümde yok.','M4 kaydedilmiş AI etiketlerinin etkisini ölçer; canlı AI çağrısı veya otomatik bilimsel doğrulama yapmaz.','Mevcut sezgisel öneri motoru ayrı korunur; bu deneyde profil/metin verisi bulunmadığından kıyas metriği hesaplanmaz.']}
