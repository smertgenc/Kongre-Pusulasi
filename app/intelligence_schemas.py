"""Optional research metadata and local workspace profile inputs."""
from typing import Annotated
from pydantic import Field, field_validator
from app.input_model import InputModel
from app.text_similarity import normalize_text

Term = Annotated[str,Field(min_length=1,max_length=200)]
Terms = Annotated[list[Term],Field(max_length=40)]
Names = Annotated[list[Term],Field(max_length=100)]

class ResearchProfileInput(InputModel):
    enabled: bool = True
    research_fields: Terms = Field(default_factory=list)
    keywords: Terms = Field(default_factory=list)

    @field_validator('research_fields','keywords')
    @classmethod
    def unique_terms(cls, values):
        seen=set();result=[]
        for value in values:
            key=normalize_text(value)
            if not key:raise ValueError('Alan ve anahtar kelimeler harf veya rakam içermelidir.')
            if key not in seen:result.append(value);seen.add(key)
        return result

class CongressResearchInput(InputModel):
    description: Annotated[str,Field(max_length=6000)] = ''
    call_for_papers: Annotated[str,Field(max_length=12000)] = ''
    research_fields: Terms = Field(default_factory=list)
    topics: Terms = Field(default_factory=list)
    keywords: Terms = Field(default_factory=list)
    country: Annotated[str,Field(max_length=200)] = ''
    city: Annotated[str,Field(max_length=200)] = ''
    fee: Annotated[str,Field(max_length=500)] = ''
    address: Annotated[str,Field(max_length=1000)] = ''
    committee_members: Names = Field(default_factory=list)
    speaker_names: Names = Field(default_factory=list)
    contact_emails: Terms = Field(default_factory=list)
    phones: Terms = Field(default_factory=list)
    publishers: Terms = Field(default_factory=list)
    proceedings: Annotated[str,Field(max_length=2000)] = ''
    doi_prefixes: Terms = Field(default_factory=list)
    past_congresses: Terms = Field(default_factory=list)
    past_years: Annotated[list[Annotated[int,Field(ge=1800,le=2200)]],Field(max_length=40)] = Field(default_factory=list)
    social_links: Terms = Field(default_factory=list)
