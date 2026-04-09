from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.storage import storage
from app.models.history import History
from app.models.translate_task import TranslateTask
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.history import HistoryItemResponse, HistoryListResponse


class HistoryService:
    async def list_history(
        self,
        session: AsyncSession,
        user: User,
        page: int,
        page_size: int,
        task_type: str | None,
        keyword: str | None,
    ) -> HistoryListResponse:
        await self.prune_expired_history(session)
        stmt = select(History).where(History.user_id == user.id)
        if task_type:
            stmt = stmt.where(History.task_type == task_type)
        if keyword:
            stmt = stmt.where(History.title.ilike(f'%{keyword}%'))
        stmt = stmt.order_by(History.updated_at.desc())

        all_histories = (await session.scalars(stmt)).all()
        start = (page - 1) * page_size
        current_histories = all_histories[start : start + page_size]
        items = [await self._serialize_history(session, history) for history in current_histories]
        return HistoryListResponse(items=items, total=len(all_histories), page=page, page_size=page_size)

    async def get_history_detail(self, session: AsyncSession, user: User, history_id: str) -> HistoryItemResponse:
        await self.prune_expired_history(session)
        history = await session.scalar(select(History).where(History.id == history_id, History.user_id == user.id))
        if not history:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='历史不存在')
        return await self._serialize_history(session, history)

    async def delete_history(self, session: AsyncSession, user: User, history_id: str) -> None:
        history = await session.scalar(select(History).where(History.id == history_id, History.user_id == user.id))
        if not history:
            return
        task = await session.scalar(select(TranslateTask).where(TranslateTask.id == history.task_id, TranslateTask.user_id == user.id))
        if not task:
            await session.delete(history)
            await session.commit()
            return

        if task.status in {'queued', 'translating'}:
            task.status = 'cancelled'

        await self._delete_task_files(session, task)
        await session.delete(history)
        await session.delete(task)
        await session.commit()

    async def prune_expired_history(self, session: AsyncSession) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.file_retention_days)
        expired_histories = (await session.scalars(select(History).where(History.updated_at < cutoff))).all()
        if not expired_histories:
            return

        for history in expired_histories:
            task = await session.scalar(select(TranslateTask).where(TranslateTask.id == history.task_id))
            if task:
                await self._delete_task_files(session, task)
                await session.delete(task)
            await session.delete(history)
        await session.commit()

    async def _serialize_history(self, session: AsyncSession, history: History) -> HistoryItemResponse:
        task = await session.scalar(select(TranslateTask).where(TranslateTask.id == history.task_id))
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='任务不存在')
        return HistoryItemResponse(
            id=history.id,
            task_type=history.task_type,
            title=history.title or '',
            status=task.status,
            source_lang=history.source_lang or '',
            target_lang=history.target_lang or '',
            updated_at=history.updated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            result_preview=task.result_text,
            source_text=task.source_text,
            translated_text=task.result_text,
            file_id=task.source_file_id,
            task_id=task.id,
            result_file_id=task.result_file_id,
            bilingual_file_id=task.bilingual_file_id,
        )

    async def _delete_task_files(self, session: AsyncSession, task: TranslateTask) -> None:
        storage.delete(task.source_file_id)
        storage.delete(task.result_file_id)
        storage.delete(task.bilingual_file_id)
        if task.source_file_id:
            uploaded = await session.scalar(select(UploadedFile).where(UploadedFile.file_key == task.source_file_id))
            if uploaded:
                await session.delete(uploaded)


history_service = HistoryService()
