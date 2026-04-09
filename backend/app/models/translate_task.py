from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TranslateTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = 'translate_tasks'

    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    task_type: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default='pending', nullable=False)
    source_lang: Mapped[str] = mapped_column(nullable=False)
    target_lang: Mapped[str] = mapped_column(nullable=False)
    terminology_version: Mapped[str | None] = mapped_column(nullable=True)

    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_file_id: Mapped[str | None] = mapped_column(nullable=True)
    result_file_id: Mapped[str | None] = mapped_column(nullable=True)
    bilingual_file_id: Mapped[str | None] = mapped_column(nullable=True)
    original_filename: Mapped[str | None] = mapped_column(nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
