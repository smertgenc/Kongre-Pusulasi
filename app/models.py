"""Table mappings; versioned snapshot migrations live in app/database.py."""
from sqlalchemy import ForeignKey, Integer, Text, Index, LargeBinary
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class ModelVersion(Base):
    __tablename__ = 'models'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(Text)
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)

class Congress(Base):
    __tablename__ = 'congresses'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    identity_key: Mapped[str] = mapped_column(Text, unique=True)
    metadata_json: Mapped[str] = mapped_column('metadata', Text)
    created_at: Mapped[str] = mapped_column(Text)

class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    congress_id: Mapped[str] = mapped_column(Text, ForeignKey('congresses.id'))
    model_id: Mapped[str] = mapped_column(Text, ForeignKey('models.id'))
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
    __table_args__ = (Index('evaluations_congress', 'congress_id', 'created_at'),)

class CongressDeletion(Base):
    """Reversible deletion keeps evaluations and AI review references intact."""
    __tablename__ = 'congress_deletions'
    congress_id: Mapped[str] = mapped_column(Text, ForeignKey('congresses.id'), primary_key=True)
    deleted_at: Mapped[str] = mapped_column(Text)

class AIAnalysis(Base):
    __tablename__ = 'ai_analyses'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    model_id: Mapped[str] = mapped_column(Text, ForeignKey('models.id'))
    status: Mapped[str] = mapped_column(Text)
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)

class AIReview(Base):
    __tablename__ = 'ai_reviews'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(Text, ForeignKey('ai_analyses.id'), unique=True)
    evaluation_id: Mapped[str] = mapped_column(Text, ForeignKey('evaluations.id'))
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)

class AIAnalysisDeletion(Base):
    """Hide history reversibly without breaking saved evaluation references."""
    __tablename__ = 'ai_analysis_deletions'
    analysis_id: Mapped[str] = mapped_column(Text, ForeignKey('ai_analyses.id'), primary_key=True)
    deleted_at: Mapped[str] = mapped_column(Text)

class UserResearchProfile(Base):
    """Owned by the local workspace today; user_id can bind to future auth."""
    __tablename__ = 'user_research_profiles'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, unique=True)
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)

class ConferenceFingerprint(Base):
    """Derived cache; historical evaluations remain immutable."""
    __tablename__ = 'conference_fingerprints'
    conference_id: Mapped[str] = mapped_column(Text, ForeignKey('congresses.id'), primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(Text, ForeignKey('evaluations.id'))
    source_hash: Mapped[str] = mapped_column(Text)
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)

class CongressLogo(Base):
    """Current visual identity, independent of immutable AHP evaluations."""
    __tablename__ = 'congress_logos'
    congress_id: Mapped[str] = mapped_column(Text, ForeignKey('congresses.id'), primary_key=True)
    image: Mapped[bytes] = mapped_column(LargeBinary, default=b'')
    status: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default='')
    source_url: Mapped[str] = mapped_column(Text, default='')
    website: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[str] = mapped_column(Text)
