from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.history import HistoryItemResponse, HistoryListResponse
from app.services.history_service import history_service


router = APIRouter(prefix='/history', tags=['history'])


@router.get('', response_model=ApiResponse[HistoryListResponse])
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    task_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[HistoryListResponse]:
    data = await history_service.list_history(session, current_user, page, page_size, task_type, keyword)
    return ApiResponse(data=data)


@router.get('/{history_id}', response_model=ApiResponse[HistoryItemResponse])
async def get_history_detail(
    history_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[HistoryItemResponse]:
    return ApiResponse(data=await history_service.get_history_detail(session, current_user, history_id))


@router.delete('/{history_id}', status_code=204)
async def delete_history(
    history_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await history_service.delete_history(session, current_user, history_id)
    return Response(status_code=204)
