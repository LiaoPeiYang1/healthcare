import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import storage
from app.db.session import AsyncSessionLocal
from app.models.history import History
from app.models.translate_task import TranslateTask
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.translate import (
    FileTaskStatusResponse,
    FileTranslateRequest,
    FileTranslateResponse,
    TextTranslateRequest,
    TextTranslateResponse,
)
from app.services.document_service import document_service
from app.services.provider_service import SUPPORTED_LANGUAGES, TranslationProviderError, provider_service
from app.services.terminology_service import terminology_service


ACTIVE_FILE_STATUSES = {'pending', 'hashing', 'uploading', 'queued', 'translating'}
REUSABLE_FILE_STATUSES = {'failed', 'cancelled'}


class TranslateService:
    async def detect_language(self, text: str) -> tuple[str, float]:
        lang, confidence = await provider_service.detect_language(text)
        self._ensure_supported_language(lang)
        return lang, confidence

    async def translate_text(
        self,
        session: AsyncSession,
        user: User,
        payload: TextTranslateRequest,
    ) -> TextTranslateResponse:
        source_lang = payload.source_lang
        if source_lang == 'auto':
            source_lang, _ = await self.detect_language(payload.text)
        self._ensure_supported_language(source_lang)
        self._ensure_supported_language(payload.target_lang)
        if source_lang == payload.target_lang:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='源语言与目标语言不能相同')

        try:
            term_matches = await terminology_service.extract_terms(
                session,
                payload.text,
                source_lang,
                payload.target_lang,
            )
            protected_text = payload.text
            for item in term_matches:
                protected_text = protected_text.replace(item['original'], item['placeholder'])

            translated = await provider_service.translate(protected_text, source_lang, payload.target_lang)
            final_text = translated
            for item in term_matches:
                final_text = final_text.replace(item['placeholder'], item['translation'])
        except Exception as exc:
            task, history = await self._upsert_text_task(
                session=session,
                user=user,
                history_id=payload.history_id,
                source_text=payload.text,
                result_text=None,
                source_lang=source_lang,
                target_lang=payload.target_lang,
                terminology_version=await terminology_service.version_snapshot(session),
                status_value='failed',
                error_msg='翻译失败，请稍后重试',
            )
            await session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='翻译失败，请稍后重试') from exc

        task, history = await self._upsert_text_task(
            session=session,
            user=user,
            history_id=payload.history_id,
            source_text=payload.text,
            result_text=final_text,
            source_lang=source_lang,
            target_lang=payload.target_lang,
            terminology_version=await terminology_service.version_snapshot(session),
            status_value='success',
            error_msg=None,
        )
        await session.commit()

        return TextTranslateResponse(
            task_id=task.id,
            translated_text=final_text,
            source_lang=source_lang,
            terminology_count=len(term_matches),
            history_id=history.id,
        )

    async def submit_file_translation(
        self,
        session: AsyncSession,
        user: User,
        payload: FileTranslateRequest,
    ) -> FileTranslateResponse:
        uploaded = await session.scalar(select(UploadedFile).where(UploadedFile.id == payload.file_id))
        if not uploaded:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='文件不存在')

        source_lang = payload.source_lang
        if source_lang != 'auto':
            self._ensure_supported_language(source_lang)
        self._ensure_supported_language(payload.target_lang)
        if source_lang != 'auto' and source_lang == payload.target_lang:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='源语言与目标语言不能相同')

        if not payload.history_id:
            await self._ensure_no_active_file_task(session, user.id)

        task, history = await self._upsert_file_task(
            session=session,
            user=user,
            history_id=payload.history_id,
            uploaded=uploaded,
            source_lang=source_lang,
            target_lang=payload.target_lang,
        )
        await session.commit()
        self.enqueue_file_translation(task.id)
        return FileTranslateResponse(task_id=task.id, status=task.status, history_id=history.id)

    async def get_file_status(
        self,
        session: AsyncSession,
        user: User,
        task_id: str,
    ) -> FileTaskStatusResponse:
        task = await self._get_user_file_task(session, user.id, task_id)
        return self._build_file_status_response(task)

    async def cancel_file_translation(
        self,
        session: AsyncSession,
        user: User,
        task_id: str,
    ) -> FileTaskStatusResponse:
        task = await self._get_user_file_task(session, user.id, task_id)
        if task.status in ACTIVE_FILE_STATUSES:
            now = datetime.now(timezone.utc)
            task.status = 'cancelled'
            task.error_msg = None
            task.updated_at = now
            task.finished_at = now
            history = await session.scalar(
                select(History).where(History.task_id == task.id, History.user_id == user.id)
            )
            if history:
                history.updated_at = now
            await session.commit()
        return self._build_file_status_response(task)

    def enqueue_file_translation(self, task_id: str) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._run_file_translation(task_id))

    async def _run_file_translation(self, task_id: str) -> None:
        async with AsyncSessionLocal() as session:
            task = await session.scalar(select(TranslateTask).where(TranslateTask.id == task_id))
            if not task or task.task_type != 'file' or task.status != 'queued':
                return

            now = datetime.now(timezone.utc)
            task.status = 'translating'
            task.started_at = now
            task.updated_at = now
            history = await session.scalar(select(History).where(History.task_id == task.id))
            if history:
                history.updated_at = now
            await session.commit()

        async with AsyncSessionLocal() as session:
            task = await session.scalar(select(TranslateTask).where(TranslateTask.id == task_id))
            if not task or task.task_type != 'file' or task.status != 'translating':
                return

            history = await session.scalar(select(History).where(History.task_id == task.id))
            now = datetime.now(timezone.utc)
            try:
                storage.delete(task.result_file_id)
                storage.delete(task.bilingual_file_id)

                source_path = self._resolve_storage_path(task.source_file_id)
                source_sections = document_service.extract_sections(source_path)
                actual_source_lang = task.source_lang
                if actual_source_lang == 'auto':
                    actual_source_lang, _ = await self.detect_language('\n'.join(source_sections)[:500])
                    if actual_source_lang == task.target_lang:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail='自动检测结果与目标语言相同，无需翻译',
                        )

                translated_sections = await self._translate_sections(
                    source_sections,
                    actual_source_lang,
                    task.target_lang,
                    session,
                )
                task.source_lang = actual_source_lang
                if history:
                    history.source_lang = actual_source_lang
                task.result_file_id = storage.save_pdf_bytes(
                    document_service.build_translation_pdf(
                        task.original_filename or 'translated',
                        translated_sections,
                    ),
                    category='results',
                )
                task.bilingual_file_id = storage.save_pdf_bytes(
                    document_service.build_bilingual_preview_pdf(
                        task.original_filename or 'preview',
                        source_sections,
                        translated_sections,
                    ),
                    category='previews',
                )
                task.status = 'done'
                task.error_msg = None
            except HTTPException as exc:
                task.status = 'failed'
                task.error_msg = exc.detail
            except TranslationProviderError as exc:
                task.status = 'failed'
                task.error_msg = str(exc)
            except Exception:
                task.status = 'failed'
                task.error_msg = '文件翻译失败，请稍后重试'

            task.finished_at = now
            task.updated_at = now
            if history:
                history.updated_at = now
            await session.commit()

    async def _upsert_text_task(
        self,
        session: AsyncSession,
        user: User,
        history_id: str | None,
        source_text: str,
        result_text: str | None,
        source_lang: str,
        target_lang: str,
        terminology_version: str | None,
        status_value: str,
        error_msg: str | None,
    ) -> tuple[TranslateTask, History]:
        task: TranslateTask | None = None
        history: History | None = None
        create_history_id = history_id
        if history_id:
            history, task = await self._load_history_and_task(session, user.id, history_id, 'text')
        if task and (
            (source_lang != 'auto' and task.source_lang != source_lang) or task.target_lang != target_lang
        ):
            history = None
            task = None
            create_history_id = None

        if not task:
            task = TranslateTask(
                user_id=user.id,
                task_type='text',
                status=status_value,
                source_lang=source_lang,
                target_lang=target_lang,
                source_text=source_text,
                result_text=result_text,
                error_msg=error_msg,
                terminology_version=terminology_version,
                finished_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.flush()
            history = History(id=create_history_id, user_id=user.id, task_id=task.id, task_type='text')
            session.add(history)

        now = datetime.now(timezone.utc)
        task.status = status_value
        task.source_lang = source_lang
        task.target_lang = target_lang
        task.source_text = source_text
        task.result_text = result_text
        task.error_msg = error_msg
        task.terminology_version = terminology_version
        task.finished_at = now
        task.updated_at = now
        history.title = source_text[:50]
        history.source_lang = source_lang
        history.target_lang = target_lang
        history.updated_at = now
        return task, history

    async def _upsert_file_task(
        self,
        session: AsyncSession,
        user: User,
        history_id: str | None,
        uploaded: UploadedFile,
        source_lang: str,
        target_lang: str,
    ) -> tuple[TranslateTask, History]:
        task: TranslateTask | None = None
        history: History | None = None
        create_history_id = history_id
        if history_id:
            history, task = await self._load_history_and_task(session, user.id, history_id, 'file')
            if task and task.status in ACTIVE_FILE_STATUSES:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='当前文件任务正在处理中')
            if task and task.status == 'done':
                if (source_lang != 'auto' and task.source_lang != source_lang) or task.target_lang != target_lang:
                    history = None
                    task = None
                    create_history_id = None
            elif task and task.status not in REUSABLE_FILE_STATUSES:
                await self._ensure_no_active_file_task(session, user.id)

        if not task:
            await self._ensure_no_active_file_task(session, user.id)
            task = TranslateTask(
                user_id=user.id,
                task_type='file',
                status='queued',
                source_lang=source_lang,
                target_lang=target_lang,
                source_file_id=uploaded.file_key,
                original_filename=uploaded.filename,
                file_size=uploaded.file_size,
                terminology_version=await terminology_service.version_snapshot(session),
            )
            session.add(task)
            await session.flush()
            history = History(id=create_history_id, user_id=user.id, task_id=task.id, task_type='file')
            session.add(history)

        storage.delete(task.result_file_id)
        storage.delete(task.bilingual_file_id)

        now = datetime.now(timezone.utc)
        task.status = 'queued'
        task.source_lang = source_lang
        task.target_lang = target_lang
        task.source_file_id = uploaded.file_key
        task.original_filename = uploaded.filename
        task.file_size = uploaded.file_size
        task.result_file_id = None
        task.bilingual_file_id = None
        task.error_msg = None
        task.terminology_version = await terminology_service.version_snapshot(session)
        task.started_at = None
        task.finished_at = None
        task.updated_at = now
        history.title = uploaded.filename
        history.source_lang = source_lang
        history.target_lang = target_lang
        history.updated_at = now
        return task, history

    async def _load_history_and_task(
        self,
        session: AsyncSession,
        user_id: str,
        history_id: str,
        task_type: str,
    ) -> tuple[History | None, TranslateTask | None]:
        history = await session.scalar(
            select(History).where(
                History.id == history_id,
                History.user_id == user_id,
                History.task_type == task_type,
            )
        )
        if not history:
            return None, None

        task = await session.scalar(
            select(TranslateTask).where(
                TranslateTask.id == history.task_id,
                TranslateTask.user_id == user_id,
                TranslateTask.task_type == task_type,
            )
        )
        return history, task

    async def _get_user_file_task(
        self,
        session: AsyncSession,
        user_id: str,
        task_id: str,
    ) -> TranslateTask:
        task = await session.scalar(
            select(TranslateTask).where(
                TranslateTask.id == task_id,
                TranslateTask.user_id == user_id,
                TranslateTask.task_type == 'file',
            )
        )
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='任务不存在')
        return task

    async def _ensure_no_active_file_task(self, session: AsyncSession, user_id: str) -> None:
        task = await session.scalar(
            select(TranslateTask).where(
                TranslateTask.user_id == user_id,
                TranslateTask.task_type == 'file',
                TranslateTask.status.in_(ACTIVE_FILE_STATUSES),
            )
        )
        if task:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='当前已有文件在处理中，请先完成或删除当前任务')

    def _build_file_status_response(self, task: TranslateTask) -> FileTaskStatusResponse:
        updated_at = task.updated_at or datetime.now(timezone.utc)
        return FileTaskStatusResponse(
            task_id=task.id,
            status=task.status,
            result_file_id=task.result_file_id,
            bilingual_file_id=task.bilingual_file_id,
            updated_at=updated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            error=task.error_msg,
        )

    def _ensure_supported_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='暂不支持该语种翻译')

    async def _translate_sections(
        self,
        sections: list[str],
        source_lang: str,
        target_lang: str,
        session: AsyncSession,
    ) -> list[str]:
        translated_sections: list[str] = []
        for section in sections:
            protected_text = section
            term_matches = await terminology_service.extract_terms(session, section, source_lang, target_lang)
            for item in term_matches:
                protected_text = protected_text.replace(item['original'], item['placeholder'])

            translated_chunks: list[str] = []
            for chunk in document_service.split_for_translation(protected_text):
                translated_chunks.append(
                    await provider_service.translate(
                        chunk,
                        source_lang,
                        target_lang,
                        preserve_format=True,
                    )
                )

            translated_text = '\n'.join(part.strip() for part in translated_chunks if part.strip())
            for item in term_matches:
                translated_text = translated_text.replace(item['placeholder'], item['translation'])
            translated_sections.append(translated_text or '（未生成译文）')
        return translated_sections

    def _resolve_storage_path(self, file_key: str | None) -> Path:
        if not file_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='原始文件不存在')
        full_path = storage.root / file_key
        if not full_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='原始文件不存在')
        return full_path


translate_service = TranslateService()
