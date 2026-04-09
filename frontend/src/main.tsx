import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { RouterProvider } from 'react-router-dom'
import { Toaster } from 'sonner'

import { GlobalErrorBoundary } from '@/components/error-boundary/index'
import { router } from '@/router'

import 'antd/dist/reset.css'
import '@/styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#ab4f23',
          borderRadius: 18,
          colorBgLayout: '#f4efe7',
          fontFamily: '"Iowan Old Style", "Songti SC", serif',
        },
      }}
    >
      <GlobalErrorBoundary>
        <RouterProvider router={router} />
      </GlobalErrorBoundary>
      <Toaster position="top-center" richColors />
    </ConfigProvider>
  </StrictMode>,
)
