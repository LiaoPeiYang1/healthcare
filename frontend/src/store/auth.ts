import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { loginWithPassword, logoutRequest, refreshSession } from '@/api/auth'
import type { AuthTokens, UserInfo } from '@/types'

type LoginPayload = {
  email: string
  password: string
}

type AuthState = {
  token: string | null
  refreshToken: string | null
  expiresAt: number | null
  userInfo: UserInfo | null
  isLoading: boolean
  setSession: (user: UserInfo, tokens: AuthTokens) => void
  login: (payload: LoginPayload) => Promise<void>
  refreshAuth: () => Promise<boolean>
  logout: (silent?: boolean) => Promise<void>
}

function redirectToLogin() {
  if (window.location.pathname === '/login') return
  const redirect = encodeURIComponent(window.location.pathname)
  window.location.href = `/login?redirect=${redirect}`
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      expiresAt: null,
      userInfo: null,
      isLoading: false,
      setSession(user, tokens) {
        set({
          token: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          expiresAt: tokens.expiresAt,
          userInfo: user,
        })
      },
      async login(payload) {
        set({ isLoading: true })
        try {
          const response = await loginWithPassword(payload)
          get().setSession(response.user, response.tokens)
        } finally {
          set({ isLoading: false })
        }
      },
      async refreshAuth() {
        const refreshToken = get().refreshToken
        if (!refreshToken) return false
        try {
          const nextTokens = await refreshSession(refreshToken)
          set({
            token: nextTokens.accessToken,
            refreshToken: nextTokens.refreshToken,
            expiresAt: nextTokens.expiresAt,
          })
          return true
        } catch {
          await get().logout(true)
          return false
        }
      },
      async logout(silent = false) {
        try {
          if (!silent && get().token) {
            await logoutRequest()
          }
        } catch {
          // Ignore logout errors and clear local state anyway.
        } finally {
          set({
            token: null,
            refreshToken: null,
            expiresAt: null,
            userInfo: null,
            isLoading: false,
          })
          if (!silent) redirectToLogin()
        }
      },
    }),
    {
      name: 'medical-translate-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        userInfo: state.userInfo,
      }),
    },
  ),
)
