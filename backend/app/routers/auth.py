import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, SSOCallbackRequest
from app.schemas.common import ApiResponse
from app.services.auth_service import auth_service


router = APIRouter(prefix='/auth', tags=['auth'])
FEISHU_LOGIN_STATE_TTL_SECONDS = 600
feishu_login_states: dict[str, dict[str, object]] = {}


def prune_feishu_login_states() -> None:
    now = time.time()
    expired_states = [
        state
        for state, state_data in feishu_login_states.items()
        if float(state_data.get('expires_at', 0)) <= now
    ]
    for state in expired_states:
        feishu_login_states.pop(state, None)


def sanitize_frontend_redirect_path(redirect_path: str | None) -> str:
    if not redirect_path:
        return '/workspace'
    parsed = urlsplit(redirect_path)
    if parsed.scheme or parsed.netloc:
        return '/workspace'
    safe_path = parsed.path or '/workspace'
    if not safe_path.startswith('/') or safe_path.startswith('//'):
        return '/workspace'
    return urlunsplit(('', '', safe_path, parsed.query, parsed.fragment))


def resolve_frontend_base_url(frontend_base_url: str | None) -> str:
    default_base_url = settings.frontend_base_url.rstrip('/')
    if not frontend_base_url:
        return default_base_url
    normalized_candidate = frontend_base_url.rstrip('/')
    allowed_base_urls = {origin.rstrip('/') for origin in settings.allowed_origin_list}
    return normalized_candidate if normalized_candidate in allowed_base_urls else default_base_url


def build_frontend_redirect_url(
    params: dict[str, str],
    *,
    redirect_path: str | None = None,
    frontend_base_url: str | None = None,
) -> str:
    sanitized = {key: value for key, value in params.items() if value}
    safe_redirect = sanitize_frontend_redirect_path(redirect_path)
    parsed_redirect = urlsplit(safe_redirect)
    merged_query = dict(parse_qsl(parsed_redirect.query, keep_blank_values=True))
    merged_query.update(sanitized)
    base_url_parts = urlsplit(resolve_frontend_base_url(frontend_base_url))
    return urlunsplit(
        (
            base_url_parts.scheme,
            base_url_parts.netloc,
            parsed_redirect.path or '/workspace',
            urlencode(merged_query),
            parsed_redirect.fragment,
        )
    )


def build_frontend_login_redirect_url(
    params: dict[str, str],
    *,
    redirect_path: str | None = None,
    frontend_base_url: str | None = None,
) -> str:
    safe_redirect = sanitize_frontend_redirect_path(redirect_path)
    query = {'redirect': safe_redirect}
    query.update({key: value for key, value in params.items() if value})
    base_url_parts = urlsplit(resolve_frontend_base_url(frontend_base_url))
    return urlunsplit(
        (
            base_url_parts.scheme,
            base_url_parts.netloc,
            '/login',
            urlencode(query),
            '',
        )
    )


@router.post('/login', response_model=ApiResponse[AuthResponse])
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> ApiResponse[AuthResponse]:
    return ApiResponse(data=await auth_service.login(session, payload.email, payload.password))


@router.post('/refresh', response_model=ApiResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> ApiResponse[dict]:
    tokens = await auth_service.refresh(session, payload.refresh_token)
    return ApiResponse(data=tokens.model_dump())


@router.get('/feishu/status', response_model=ApiResponse[dict])
async def feishu_status() -> ApiResponse[dict]:
    return ApiResponse(
        data={
            'enabled': auth_service.is_feishu_enabled(),
            'redirect_uri': settings.feishu_redirect_uri,
            'scope': settings.feishu_scope,
        }
    )


@router.get('/feishu/login')
async def feishu_login(
    redirect: str | None = Query(default='/workspace'),
    origin: str | None = Query(default=None),
) -> RedirectResponse:
    redirect_path = sanitize_frontend_redirect_path(redirect)
    frontend_base_url = resolve_frontend_base_url(origin)

    if not auth_service.is_feishu_enabled():
        return RedirectResponse(
            build_frontend_login_redirect_url(
                {
                    'login': 'error',
                    'provider': 'feishu',
                    'message': '飞书 SSO 尚未配置',
                },
                redirect_path=redirect_path,
                frontend_base_url=frontend_base_url,
            ),
            status_code=302,
        )

    prune_feishu_login_states()
    state = secrets.token_urlsafe(24)
    feishu_login_states[state] = {
        'expires_at': time.time() + FEISHU_LOGIN_STATE_TTL_SECONDS,
        'redirect_path': redirect_path,
        'frontend_base_url': frontend_base_url,
    }
    query = {
        'response_type': 'code',
        'redirect_uri': settings.feishu_redirect_uri,
        'state': state,
        'app_id': settings.feishu_client_id,
        'client_id': settings.feishu_client_id,
    }
    if settings.feishu_scope:
        query['scope'] = settings.feishu_scope
    return RedirectResponse(f'{settings.feishu_auth_url}?{urlencode(query)}', status_code=302)


@router.post('/sso/callback', response_model=ApiResponse[AuthResponse])
async def sso_callback(payload: SSOCallbackRequest, session: AsyncSession = Depends(get_db_session)) -> ApiResponse[AuthResponse]:
    return ApiResponse(data=await auth_service.handle_feishu_callback(session, payload.code))


@router.get('/feishu/callback')
async def feishu_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    redirect_path = '/workspace'
    frontend_base_url = settings.frontend_base_url

    if state:
        prune_feishu_login_states()
        state_data = feishu_login_states.get(state)
        if state_data:
            redirect_path = str(state_data.get('redirect_path') or redirect_path)
            frontend_base_url = resolve_frontend_base_url(str(state_data.get('frontend_base_url') or ''))

    if error:
        if state:
            feishu_login_states.pop(state, None)
        return RedirectResponse(
            build_frontend_login_redirect_url(
                {
                    'login': 'error',
                    'provider': 'feishu',
                    'message': error_description or error,
                },
                redirect_path=redirect_path,
                frontend_base_url=frontend_base_url,
            ),
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            build_frontend_login_redirect_url(
                {
                    'login': 'error',
                    'provider': 'feishu',
                    'message': '飞书回调缺少必要参数',
                },
                redirect_path=redirect_path,
                frontend_base_url=frontend_base_url,
            ),
            status_code=302,
        )

    state_data = feishu_login_states.pop(state, None)
    expires_at = float(state_data.get('expires_at', 0)) if state_data else 0
    if state_data:
        redirect_path = str(state_data.get('redirect_path') or redirect_path)
        frontend_base_url = resolve_frontend_base_url(str(state_data.get('frontend_base_url') or ''))
    if not state_data or expires_at <= time.time():
        return RedirectResponse(
            build_frontend_login_redirect_url(
                {
                    'login': 'error',
                    'provider': 'feishu',
                    'message': '飞书登录状态已失效，请重新发起登录',
                },
                redirect_path=redirect_path,
                frontend_base_url=frontend_base_url,
            ),
            status_code=302,
        )

    try:
        response = await auth_service.handle_feishu_callback(session, code)
    except Exception as exc:
        message = getattr(exc, 'detail', None) or str(exc) or '飞书登录失败'
        return RedirectResponse(
            build_frontend_login_redirect_url(
                {
                    'login': 'error',
                    'provider': 'feishu',
                    'message': message,
                },
                redirect_path=redirect_path,
                frontend_base_url=frontend_base_url,
            ),
            status_code=302,
        )

    return RedirectResponse(
        build_frontend_login_redirect_url(
            {
                'login': 'success',
                'provider': 'feishu',
                'user_id': response.user.id,
                'name': response.user.name,
                'email': response.user.email,
                'avatar': response.user.avatar or '',
                'access_token': response.tokens.access_token,
                'refresh_token': response.tokens.refresh_token,
                'expires_at': str(response.tokens.expires_at),
            },
            redirect_path=redirect_path,
            frontend_base_url=frontend_base_url,
        ),
        status_code=302,
    )


@router.post('/logout', status_code=204)
async def logout() -> Response:
    return Response(status_code=204)
