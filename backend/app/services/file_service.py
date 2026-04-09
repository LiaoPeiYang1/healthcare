from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.storage import storage
from app.models.file_chunk import FileChunk
from app.models.translate_task import TranslateTask
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.file import FileCheckRequest, FileCheckResponse, FileMergeRequest, FileMergeResponse


ACTIVE_FILE_STATUSES = {'pending', 'hashing', 'uploading', 'queued', 'translating'}
SUPPORTED_FILE_EXTENSIONS = {'.docx', '.pdf'}


class FileService:
    async def check_file(self, session: AsyncSession, user: User, payload: FileCheckRequest) -> FileCheckResponse:
        await self._ensure_no_active_file_task(session, user.id)
        self._validate_file(payload.filename, payload.file_size, payload.total_chunks)
        uploaded = await session.scalar(select(UploadedFile).where(UploadedFile.file_hash == payload.file_hash))
        return FileCheckResponse(exists=bool(uploaded), file_id=uploaded.id if uploaded else None)

    async def save_chunk(
        self,
        session: AsyncSession,
        user: User,
        file_hash: str,
        chunk_index: int,
        total_chunks: int,
        chunk: UploadFile,
    ) -> None:
        await self._ensure_no_active_file_task(session, user.id)
        key = storage.save_chunk(file_hash, chunk_index, await chunk.read())
        existing = await session.scalar(
            select(FileChunk).where(FileChunk.file_hash == file_hash, FileChunk.chunk_index == chunk_index)
        )
        if existing:
            existing.chunk_key = key
            existing.total_chunks = total_chunks
        else:
            session.add(
                FileChunk(
                    file_hash=file_hash,
                    user_id=user.id,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    chunk_key=key,
                )
            )
        await session.commit()

    async def merge_chunks(self, session: AsyncSession, user: User, payload: FileMergeRequest) -> FileMergeResponse:
        await self._ensure_no_active_file_task(session, user.id)
        suffix = Path(payload.filename).suffix.lower()
        if suffix not in SUPPORTED_FILE_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='仅支持 .docx 和 .pdf')

        chunks_stmt = select(FileChunk).where(FileChunk.file_hash == payload.file_hash, FileChunk.user_id == user.id)
        chunks = (await session.scalars(chunks_stmt)).all()
        if len(chunks) != payload.total_chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='分片数量不完整，无法合并')

        merged_key = storage.merge_chunks(payload.file_hash, payload.total_chunks, suffix)
        merged_path = settings.storage_path / merged_key
        merged_size = merged_path.stat().st_size
        if merged_size > settings.file_max_size_mb * 1024 * 1024:
            storage.delete(merged_key)
            storage.cleanup_chunks(payload.file_hash, payload.total_chunks)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='文件大小不能超过 100MB')
        if suffix == '.pdf' and self._is_scanned_pdf(merged_path):
            storage.delete(merged_key)
            storage.cleanup_chunks(payload.file_hash, payload.total_chunks)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='暂不支持扫描版 PDF，请上传可编辑文本型 PDF 或 DOCX',
            )

        uploaded = await session.scalar(select(UploadedFile).where(UploadedFile.file_hash == payload.file_hash))
        if not uploaded:
            uploaded = UploadedFile(
                file_hash=payload.file_hash,
                file_key=merged_key,
                filename=payload.filename,
                file_size=merged_size,
                mime_type=payload.mime_type,
            )
            session.add(uploaded)
            await session.flush()
        storage.cleanup_chunks(payload.file_hash, payload.total_chunks)
        await session.execute(
            FileChunk.__table__.delete().where(FileChunk.file_hash == payload.file_hash, FileChunk.user_id == user.id)
        )
        await session.commit()
        return FileMergeResponse(file_id=uploaded.id)

    async def _ensure_no_active_file_task(self, session: AsyncSession, user_id: str) -> None:
        active_count = await session.scalar(
            select(func.count(TranslateTask.id)).where(
                TranslateTask.user_id == user_id,
                TranslateTask.task_type == 'file',
                TranslateTask.status.in_(ACTIVE_FILE_STATUSES),
            )
        )
        if active_count:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='当前已有文件在处理中，请先完成或删除当前任务')

    def _validate_file(self, filename: str, file_size: int, total_chunks: int) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_FILE_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='仅支持 .docx 和 .pdf')
        if file_size > settings.file_max_size_mb * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='文件大小不能超过 100MB')
        expected_chunks = max(1, (file_size + settings.file_chunk_size - 1) // settings.file_chunk_size)
        if total_chunks != expected_chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='分片数量与文件大小不匹配')

    def _is_scanned_pdf(self, path: Path) -> bool:
        if path.suffix.lower() != '.pdf':
            return False
        # Many text PDFs store page streams after compressed object headers, so
        # checking only the first few KB causes false positives. Scan the file
        # for basic text operators before treating it as image-only.
        content = path.read_bytes()
        text_markers = (b'BT', b'ET', b'/Font', b'/ToUnicode', b'/Subtype /XML')
        return not any(marker in content for marker in text_markers)


file_service = FileService()
