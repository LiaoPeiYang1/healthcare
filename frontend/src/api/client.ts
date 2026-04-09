import { API_BASE_URL } from '@/api/config'
import { useAuthStore } from '@/store/auth'

export class ApiError extends Error {
  status: number
  payload?: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

type ParseAs = 'json' | 'blob' | 'text' | 'void'

type RequestOptions = RequestInit & {
  skipAuth?: boolean
  timeoutMs?: number
  parseAs?: ParseAs
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefreshOnce() {
  if (!refreshPromise) {
    refreshPromise = useAuthStore.getState().refreshAuth().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth = false, timeoutMs = 12_000, parseAs = 'json', headers, body, ...rest } = options

  if (!skipAuth) {
    const { token, expiresAt, refreshAuth } = useAuthStore.getState()
    if (token && expiresAt && Date.now() > expiresAt - 60_000) {
      await refreshAuth()
    }
  }

  const token = useAuthStore.getState().token
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...rest,
      body,
      signal: controller.signal,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(skipAuth || !token ? {} : { Authorization: `Bearer ${token}` }),
        ...headers,
      },
    })

    if (response.status === 401 && !skipAuth) {
      const refreshed = await tryRefreshOnce()
      if (refreshed) {
        return request<T>(url, options)
      }
      useAuthStore.getState().logout(true)
      throw new ApiError('登录状态已失效，请重新登录', 401)
    }

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      const message =
        (payload && typeof payload === 'object' && 'detail' in payload && String(payload.detail)) ||
        `请求失败：${response.status}`
      throw new ApiError(message, response.status, payload)
    }

    if (parseAs === 'blob') return (await response.blob()) as unknown as T
    if (parseAs === 'text') return (await response.text()) as unknown as T
    if (parseAs === 'void' || response.status === 204) return undefined as unknown as T
    return (await response.json()) as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}
