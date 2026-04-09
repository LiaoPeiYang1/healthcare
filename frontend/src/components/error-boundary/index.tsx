import type { ReactNode } from 'react'
import { Component } from 'react'
import { Button, Result } from 'antd'

type ErrorBoundaryProps = {
  children: ReactNode
  fallback?: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
}

class BaseErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    console.error('Render error:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <Result
            status="error"
            title="页面加载失败"
            subTitle="请刷新页面后重试。"
            extra={<Button onClick={() => window.location.reload()}>刷新页面</Button>}
          />
        )
      )
    }

    return this.props.children
  }
}

export function GlobalErrorBoundary({ children }: { children: ReactNode }) {
  return <BaseErrorBoundary>{children}</BaseErrorBoundary>
}

export function WorkspaceErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <BaseErrorBoundary
      fallback={
        <Result
          status="warning"
          title="工作区内容加载失败"
          subTitle="你可以刷新页面，或先查看其他历史记录。"
          extra={<Button onClick={() => window.location.reload()}>重新加载</Button>}
        />
      }
    >
      {children}
    </BaseErrorBoundary>
  )
}
