from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, TokenBundle, UserInfo


class AuthService:
    def is_feishu_enabled(self) -> bool:
        return bool(
            settings.feishu_sso_enabled
            and settings.feishu_client_id
            and settings.feishu_client_secret
        )

    async def ensure_seed_user(self, session: AsyncSession) -> None:
        existing_user = await session.scalar(select(User).where(User.email == settings.seed_user_email))
        if existing_user:
            return
        session.add(
            User(
                email=settings.seed_user_email,
                name=settings.seed_user_name,
                auth_type='password',
                password_hash=hash_password(settings.seed_user_password),
                is_active=True,
            )
        )
        await session.commit()

    async def login(self, session: AsyncSession, email: str, password: str) -> AuthResponse:
        user = await session.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='邮箱或密码错误')
        return self._build_auth_response(user)

    async def refresh(self, session: AsyncSession, refresh_token: str) -> TokenBundle:
        payload = decode_token(refresh_token, expected_type='refresh')
        user = await session.scalar(select(User).where(User.id == payload['sub'], User.is_active.is_(True)))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='用户不存在或已停用')
        return self._build_auth_response(user).tokens

    async def handle_feishu_callback(self, session: AsyncSession, code: str) -> AuthResponse:
        if not self.is_feishu_enabled():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='飞书 SSO 未启用')

        token_data = await self._exchange_feishu_code(code)
        access_token = str(token_data.get('access_token') or '')
        if not access_token:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='未获取到飞书访问令牌')

        user_data = await self._fetch_feishu_user_info(access_token)
        union_id = str(user_data.get('union_id') or user_data.get('open_id') or code)
        email = str(user_data.get('email') or user_data.get('enterprise_email') or f'{union_id[:24]}@feishu.local')
        name = str(user_data.get('name') or user_data.get('en_name') or '飞书用户')
        avatar_url = str(user_data.get('avatar_url') or user_data.get('avatar_thumb') or '') or None

        user = await session.scalar(select(User).where(User.feishu_union_id == union_id))
        if not user:
            user = await session.scalar(select(User).where(User.email == email))

        if not user:
            user = User(
                email=email,
                name=name,
                avatar_url=avatar_url,
                auth_type='feishu',
                feishu_union_id=union_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            user.name = name
            user.email = email
            user.avatar_url = avatar_url
            user.auth_type = 'feishu'
            user.feishu_union_id = union_id
            await session.commit()
            await session.refresh(user)
        return self._build_auth_response(user)

    async def _exchange_feishu_code(self, code: str) -> dict:
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.feishu_redirect_uri,
            'app_id': settings.feishu_client_id,
            'app_secret': settings.feishu_client_secret,
            'client_id': settings.feishu_client_id,
            'client_secret': settings.feishu_client_secret,
        }
        return await self._request_feishu_json(settings.feishu_token_url, method='POST', payload=payload)

    async def _fetch_feishu_user_info(self, access_token: str) -> dict:
        return await self._request_feishu_json(
            settings.feishu_user_info_url,
            headers={'Authorization': f'Bearer {access_token}'},
        )

    async def _request_feishu_json(
        self,
        url: str,
        *,
        method: str = 'GET',
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        request_headers = {'Accept': 'application/json'}
        if headers:
            request_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.request(method, url, json=payload, headers=request_headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or str(exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'飞书接口调用失败：{detail}') from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='无法连接飞书开放平台') from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='飞书返回了无法识别的响应') from exc

        error_code = response_payload.get('code')
        if error_code not in (None, 0):
            message = response_payload.get('msg') or response_payload.get('message') or '飞书接口调用失败'
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'飞书登录失败：{message}')

        data = response_payload.get('data')
        return data if isinstance(data, dict) else response_payload

    def _build_auth_response(self, user: User) -> AuthResponse:
        expires_at = int(datetime.now(timezone.utc).timestamp()) + settings.access_token_expire_seconds
        return AuthResponse(
            user=UserInfo(id=user.id, name=user.name, email=user.email, avatar=user.avatar_url),
            tokens=TokenBundle(
                access_token=create_access_token(user.id),
                refresh_token=create_refresh_token(user.id),
                expires_at=expires_at,
            ),
        )


auth_service = AuthService()
