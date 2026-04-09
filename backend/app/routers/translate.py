from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.deps import get_current_user
from app.models.history import History
from app.models.translate_task import TranslateTask
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.translate import DetectRequest, DetectResponse, FileTaskStatusResponse, FileTranslateRequest, FileTranslateResponse, TextTranslateRequest, TextTranslateResponse
from app.services.document_service import document_service
from app.services.translate_service import translate_service
from app.core.storage import storage


router = APIRouter(tags=['translate'])


async def _load_file_task_by_identifier(
    session: AsyncSession,
    user_id: str,
    identifier: str,
) -> TranslateTask | None:
    task = await session.scalar(
        select(TranslateTask).where(
            TranslateTask.id == identifier,
            TranslateTask.user_id == user_id,
            TranslateTask.task_type == 'file',
        )
    )
    if task:
        return task

    history = await session.scalar(
        select(History).where(
            History.id == identifier,
            History.user_id == user_id,
            History.task_type == 'file',
        )
    )
    if not history:
        return None

    return await session.scalar(
        select(TranslateTask).where(
            TranslateTask.id == history.task_id,
            TranslateTask.user_id == user_id,
            TranslateTask.task_type == 'file',
        )
    )


@router.post('/detect', response_model=ApiResponse[DetectResponse])
async def detect_language(payload: DetectRequest) -> ApiResponse[DetectResponse]:
    lang, confidence = await translate_service.detect_language(payload.text)
    return ApiResponse(data=DetectResponse(lang=lang, confidence=confidence))


@router.post('/translate/text', response_model=ApiResponse[TextTranslateResponse])
async def translate_text(
    payload: TextTranslateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[TextTranslateResponse]:
    return ApiResponse(data=await translate_service.translate_text(session, current_user, payload))


@router.post('/translate/file', response_model=ApiResponse[FileTranslateResponse])
async def submit_file_translate(
    payload: FileTranslateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FileTranslateResponse]:
    return ApiResponse(data=await translate_service.submit_file_translation(session, current_user, payload))


@router.get('/translate/status/{task_id}', response_model=ApiResponse[FileTaskStatusResponse])
async def get_file_task_status(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FileTaskStatusResponse]:
    return ApiResponse(data=await translate_service.get_file_status(session, current_user, task_id))


@router.post('/translate/cancel/{task_id}', response_model=ApiResponse[FileTaskStatusResponse])
async def cancel_file_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FileTaskStatusResponse]:
    return ApiResponse(data=await translate_service.cancel_file_translation(session, current_user, task_id))


@router.get('/translate/download/{task_id}')
async def download_translation(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    task = await _load_file_task_by_identifier(session, current_user.id, task_id)
    if not task or not task.result_file_id:
        return Response(status_code=404)
    filename_base = (task.original_filename or 'translation').rsplit('.', 1)[0]
    filename = f'{filename_base}_{task.target_lang}_{task.updated_at.strftime("%Y%m%d")}.pdf'
    ascii_filename = f'translation_{task.target_lang}_{task.updated_at.strftime("%Y%m%d")}.pdf'
    disposition = (
        f'attachment; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=storage.read_bytes(task.result_file_id),
        media_type='application/pdf',
        headers={'Content-Disposition': disposition},
    )


@router.get('/translate/preview/{task_id}')
async def preview_translation(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    task = await _load_file_task_by_identifier(session, current_user.id, task_id)
    preview_file_id = task.bilingual_file_id if task else None
    if not preview_file_id and task:
        preview_file_id = task.result_file_id
    if not task or not preview_file_id:
        return Response(status_code=404)

    return Response(
        content=storage.read_bytes(preview_file_id),
        media_type='application/pdf',
        headers={'Content-Disposition': 'inline; filename="preview.pdf"'},
    )


@router.get('/translate/source/{task_id}')
async def preview_source_file(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    task = await _load_file_task_by_identifier(session, current_user.id, task_id)
    if not task or not task.source_file_id:
        return Response(status_code=404)

    source_path = storage.root / task.source_file_id
    if not source_path.exists():
        return Response(status_code=404)

    if source_path.suffix.lower() == '.pdf':
        return Response(
            content=storage.read_bytes(task.source_file_id),
            media_type='application/pdf',
            headers={'Content-Disposition': 'inline; filename="source.pdf"'},
        )

    sections = document_service.extract_sections(source_path)
    return Response(
        content=document_service.build_source_pdf(task.original_filename or 'source', sections),
        media_type='application/pdf',
        headers={'Content-Disposition': 'inline; filename="source-preview.pdf"'},
    )


@router.get('/translate/result/{task_id}')
async def preview_result_file(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    task = await _load_file_task_by_identifier(session, current_user.id, task_id)
    if not task or not task.result_file_id:
        return Response(status_code=404)

    return Response(
        content=storage.read_bytes(task.result_file_id),
        media_type='application/pdf',
        headers={'Content-Disposition': 'inline; filename="result-preview.pdf"'},
    )
