from datetime import date
from typing import Annotated
from urllib.parse import urlsplit
from pydantic import Field, StrictInt, StrictFloat, field_validator, model_validator
from app.input_model import InputModel
from app.intelligence_schemas import CongressResearchInput
from engine import CRITERIA

Numeric = StrictInt | StrictFloat
Text500 = Annotated[str, Field(max_length=500)]

class CongressMetadata(InputModel):
    name: Annotated[str, Field(min_length=1, max_length=500)]
    edition: Annotated[str, Field(min_length=1, max_length=500)]
    context: Annotated[str, Field(min_length=1, max_length=2000)]
    start_date: Text500 = ''
    end_date: Text500 = ''
    location: Text500 = ''
    organizer: Text500 = ''
    website: Text500 = ''
    format: Text500 = ''
    research: CongressResearchInput = Field(default_factory=CongressResearchInput)

    @field_validator('start_date', 'end_date')
    @classmethod
    def valid_date(cls, value):
        if value:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError('Tarih YYYY-AA-GG biçiminde olmalıdır.')
        return value

    @field_validator('website')
    @classmethod
    def valid_url(cls, value):
        if value:
            u = urlsplit(value)
            if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:
                raise ValueError('Geçerli bir http:// veya https:// adresi girin.')
        return value

    @model_validator(mode='after')
    def date_order(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError('Bitiş tarihi başlangıçtan önce olamaz.')
        return self

class EvaluationInput(InputModel):
    congress_id: str | None = None
    previous_id: str | None = None
    model_id: str
    metadata: CongressMetadata
    scale: StrictInt = 1
    evaluator: Annotated[str, Field(min_length=1, max_length=120)]
    scores: dict[str, Numeric | None]
    notes: dict[str, Annotated[str, Field(max_length=3000)]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def scoring_input(self):
        import math
        if self.scale not in (1,5,10):
            raise ValueError('Puan ölçeği 1, 5 veya 10 olmalıdır.')
        codes = {c[0] for c in CRITERIA}
        if set(self.scores) != codes or set(self.notes) - codes:
            raise ValueError('K1–K10 kriterlerinin tamamı gereklidir.')
        for code, value in self.scores.items():
            if value is not None:
                if not math.isfinite(value) or not 0 <= value <= self.scale or int(value) != value:
                    raise ValueError(code + ': puan seçilen ölçekte tam sayı olmalıdır.')
                if not self.notes.get(code, '').strip():
                    raise ValueError(code + ' için karar gerekçesi veya kaynak ekleyin.')
        return self

class DeleteCongressInput(InputModel):
    previous_id: str

class Thresholds(InputModel):
    average: Numeric = 70
    valid: Numeric = 90

    @model_validator(mode='after')
    def ordered(self):
        if not 0 <= self.average < self.valid <= 100:
            raise ValueError('Eşikler 0 ≤ Orta Uygunluk < Yüksek Uygunluk ≤ 100 olmalıdır.')
        return self

class ModelInput(InputModel):
    matrices: dict[str, list[list[Numeric]]]
    thresholds: Thresholds = Field(default_factory=Thresholds)
    # The existing UI sends these also to the preview endpoint.
    name: Annotated[str, Field(max_length=120)] = ''
    base_id: str | None = None

class PublishModelInput(ModelInput):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    base_id: str

class ScenarioInput(InputModel):
    model_id: str
    criterion: str
    target: Annotated[Numeric, Field(ge=0, le=1, allow_inf_nan=False)]
