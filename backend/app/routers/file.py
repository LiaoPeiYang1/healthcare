from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.file import FileCheckRequest, FileCheckResponse, FileMergeRequest, FileMergeResponse
from app.services.file_service import file_service


router = APIRouter(prefix='/file', tags=['file'])


@router.post('/check', response_model=ApiResponse[FileCheckResponse])
async def check_file(
    payload: FileCheckRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FileCheckResponse]:
    return ApiResponse(data=await file_service.check_file(session, current_user, payload))


@router.post('/chunk', response_model=ApiResponse[dict])
async def upload_chunk(
    file_hash: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    await file_service.save_chunk(session, current_user, file_hash, chunk_index, total_chunks, chunk)
    return ApiResponse(data={'success': True, 'chunk_index': chunk_index, 'total_chunks': total_chunks})


@router.post('/merge', response_model=ApiResponse[FileMergeResponse])
async def merge_file(
    payload: FileMergeRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FileMergeResponse]:
    return ApiResponse(data=await file_service.merge_chunks(session, current_user, payload))
