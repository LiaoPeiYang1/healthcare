import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'

import LoginPage from '@/pages/login'
import WorkspacePage from '@/pages/workspace'
import { useAuthStore } from '@/store/auth'

function RequireAuth({ children }: { children?: ReactNode }) {
  const { token, expiresAt } = useAuthStore()
  const location = useLocation()
  const isValid = Boolean(token && expiresAt && Date.now() < expiresAt)

  if (!isValid) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />
  }

  return children ? <>{children}</> : <Outlet />
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/workspace" replace />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: '/workspace',
        element: <WorkspacePage />,
      },
    ],
  },
])
