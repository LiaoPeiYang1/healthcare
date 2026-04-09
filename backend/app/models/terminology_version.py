from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TerminologyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = 'terminology_versions'
    __table_args__ = (UniqueConstraint('source', 'version', name='uq_terminology_source_version'),)

    source: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active', nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
