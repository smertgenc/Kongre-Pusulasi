"""Contracts for sources, provider output and human review."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from app.schemas import InputModel, CongressMetadata
from app.provider_catalog import ProviderId
from app.search import SearchProviderId

Code = Literal['K1','K2','K3','K4','K5','K6','K7','K8','K9','K10']
Short = Annotated[str, Field(max_length=2000)]

class SourceInput(InputModel):
    kind: Literal['text','url','pdf','instagram','image','search']
    label: Annotated[str, Field(max_length=200)] = ''
    content: Annotated[str, Field(max_length=5_600_000)]
    url: Annotated[str, Field(max_length=2000)] = ''
    search_provider: SearchProviderId | None = None

    @model_validator(mode='after')
    def search_query(self):
        if self.kind=='search' and (not self.search_provider or not 3<=len(self.content)<=500):
            raise ValueError('Web araması için sağlayıcı ve 3–500 karakterlik sorgu gereklidir.')
        return self

class SearchSettingsInput(InputModel):
    provider_id: SearchProviderId
    api_key: Annotated[str, Field(max_length=500)] = ''

class SearchTestInput(InputModel):
    # Optional expectation, never an instruction to test an unsaved service.
    provider_id: SearchProviderId | None = None

class AITestInput(InputModel):
    provider_id: ProviderId | None = None
    provider_model: Annotated[str, Field(max_length=200)] | None = None

class FallbackProviderInput(InputModel):
    provider_id: ProviderId
    provider_model: Annotated[str, Field(min_length=1, max_length=200)]

class AnalysisInput(InputModel):
    scoring_policy: Literal['legacy','scientific'] = 'legacy'
    model_id: str | None = None
    provider_id: ProviderId = 'openai'
    provider_model: Annotated[str, Field(max_length=200)] | None = None
    context: Annotated[str, Field(max_length=2000)] = ''
    sources: Annotated[list[SourceInput], Field(min_length=1, max_length=4)]
    transfer_consent: Literal[True]
    # Exact recipients/models shown beside the transfer consent. Old clients
    # remain single-provider; a newly saved key never silently joins a live job.
    fallback_providers: Annotated[list[FallbackProviderInput], Field(max_length=4)] = Field(default_factory=list)

class SettingsInput(InputModel):
    provider_id: ProviderId = 'openai'
    api_key: Annotated[str, Field(max_length=500)] = ''
    model: Annotated[str, Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}$')]

class RetryAnalysisInput(InputModel):
    provider_id: ProviderId
    provider_model: Annotated[str, Field(min_length=1,max_length=200)]
    transfer_consent: Literal[True]
    fallback_providers: Annotated[list[FallbackProviderInput], Field(max_length=4)] = Field(default_factory=list)

class Evidence(InputModel):
    source_id: str
    segment_id: str
    quote: Annotated[str, Field(min_length=8, max_length=2000)]

class Finding(InputModel):
    criterion: Code
    value: bool | None
    status: Literal['detected','not_found','conflict']
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    explanation: Short = Field(description="Kriter kararının somut gerekçesi. Yalnızca Türkçe yaz; çıkarımı ve doğrudan kanıtı ayır.")
    evidence: Annotated[list[Evidence], Field(max_length=8)]

class ProfileFact(InputModel):
    field: Literal['name','edition','start_date','end_date','location','organizer','format']
    value: Annotated[str, Field(max_length=500)]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=4)]

class ProviderOutput(InputModel):
    facts: Annotated[list[ProfileFact], Field(max_length=40)]
    findings: Annotated[list[Finding], Field(min_length=10, max_length=10)]

    @model_validator(mode='after')
    def all_criteria(self):
        if {f.criterion for f in self.findings} != {f'K{i}' for i in range(1,11)}:
            raise ValueError('K1–K10 birer kez bulunmalıdır.')
        return self

class ReviewDecision(InputModel):
    action: Literal['approve','correct','reject','unknown']
    value: bool | None = None
    note: Short = ''

class ReviewInput(InputModel):
    metadata: CongressMetadata
    evaluator: Annotated[str, Field(min_length=1, max_length=120)]
    decisions: dict[Code, ReviewDecision]
    congress_id: str | None = None
    previous_id: str | None = None

    @model_validator(mode='after')
    def all_decisions(self):
        if set(self.decisions) != {f'K{i}' for i in range(1,11)}:
            raise ValueError('On kriter için inceleme kararı gereklidir.')
        return self
