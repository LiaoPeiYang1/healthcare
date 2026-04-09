import { request } from '@/api/client'
import type { ApiEnvelope, AuthTokens, UserInfo } from '@/types'

type LoginPayload = {
  email: string
  password: string
}

type RawAuthResponse = {
  user: {
    id: string
    name: string
    email?: string
    avatar?: string
  }
  tokens: {
    access_token: string
    refresh_token: string
    expires_at: number
  }
}

export async function loginWithPassword(payload: LoginPayload) {
  const response = await request<ApiEnvelope<RawAuthResponse>>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
    skipAuth: true,
  })

  return {
    user: {
      userId: response.data.user.id,
      name: response.data.user.name,
      email: response.data.user.email,
      avatar: response.data.user.avatar,
    } as UserInfo,
    tokens: {
      accessToken: response.data.tokens.access_token,
      refreshToken: response.data.tokens.refresh_token,
      expiresAt: response.data.tokens.expires_at * 1000,
    } as AuthTokens,
  }
}

export async function refreshSession(refreshToken?: string | null) {
  const response = await request<ApiEnvelope<RawAuthResponse['tokens']>>('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refreshToken }),
    skipAuth: true,
  })

  return {
    accessToken: response.data.access_token,
    refreshToken: response.data.refresh_token,
    expiresAt: response.data.expires_at * 1000,
  } as AuthTokens
}

export async function getFeishuSsoStatus() {
  const response = await request<ApiEnvelope<{ enabled: boolean; redirect_uri: string; scope: string }>>(
    '/api/auth/feishu/status',
    {
      skipAuth: true,
    },
  )

  return {
    enabled: Boolean(response.data.enabled),
    redirectUri: response.data.redirect_uri,
    scope: response.data.scope,
  }
}

export async function logoutRequest() {
  await request<void>('/api/auth/logout', {
    method: 'POST',
    parseAs: 'void',
  })
}
