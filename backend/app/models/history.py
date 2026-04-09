from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class History(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = 'history'

    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey('translate_tasks.id', ondelete='CASCADE'), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
