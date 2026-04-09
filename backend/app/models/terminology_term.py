from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TerminologyTerm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = 'terminology_terms'
    __table_args__ = (
        UniqueConstraint(
            'version_id',
            'normalized_term',
            'source_lang',
            'target_lang',
            name='uq_terminology_term_lookup',
        ),
    )

    version_id: Mapped[str] = mapped_column(ForeignKey('terminology_versions.id', ondelete='CASCADE'), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    translation: Mapped[str] = mapped_column(String(255), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
