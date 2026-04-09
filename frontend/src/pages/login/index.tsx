import { Button, Card, Form, Input, Typography } from 'antd'
import { Bot, LogIn, Mail, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { API_BASE_URL } from '@/api/config'
import { getFeishuSsoStatus } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

const DEMO_ACCOUNT = {
  email: 'demo@example.com',
  password: 'Passw0rd1',
}

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isLoading, setSession } = useAuthStore()
  const [isFeishuReady, setIsFeishuReady] = useState(false)
  const [isFeishuLoading, setIsFeishuLoading] = useState(true)

  const redirect = useMemo(() => {
    const search = new URLSearchParams(location.search)
    return search.get('redirect') || '/workspace'
  }, [location.search])

  useEffect(() => {
    let cancelled = false

    const search = new URLSearchParams(location.search)
    const loginStatus = search.get('login')
    if (loginStatus) {
      if (loginStatus === 'success' && search.get('provider') === 'feishu') {
        const accessToken = search.get('access_token')
        const refreshToken = search.get('refresh_token')
        const expiresAt = Number(search.get('expires_at') || '0')
        const userId = search.get('user_id')

        if (accessToken && refreshToken && expiresAt && userId) {
          setSession(
            {
              userId,
              name: search.get('name') || '飞书用户',
              email: search.get('email') || `${userId}@feishu.local`,
              avatar: search.get('avatar') || undefined,
            },
            {
              accessToken,
              refreshToken,
              expiresAt: expiresAt * 1000,
            },
          )
          toast.success('飞书登录成功')
          navigate(redirect, { replace: true })
          return
        }

        toast.error('飞书登录返回数据不完整，请重试')
      }

      if (loginStatus === 'error') {
        toast.error(search.get('message') || '飞书登录失败，请稍后重试')
      }

      const cleanSearch = new URLSearchParams(location.search)
      ;[
        'login',
        'provider',
        'message',
        'user_id',
        'name',
        'email',
        'avatar',
        'access_token',
        'refresh_token',
        'expires_at',
      ].forEach((key) => cleanSearch.delete(key))
      navigate(
        {
          pathname: location.pathname,
          search: cleanSearch.toString() ? `?${cleanSearch.toString()}` : '',
        },
        { replace: true },
      )
    }

    const loadFeishuStatus = async () => {
      setIsFeishuLoading(true)
      try {
        const status = await getFeishuSsoStatus()
        if (!cancelled) {
          setIsFeishuReady(status.enabled)
        }
      } catch {
        if (!cancelled) {
          setIsFeishuReady(false)
        }
      } finally {
        if (!cancelled) {
          setIsFeishuLoading(false)
        }
      }
    }

    void loadFeishuStatus()
    return () => {
      cancelled = true
    }
  }, [location.pathname, location.search, navigate, redirect, setSession])

  const handleFinish = async (values: { email: string; password: string }) => {
    try {
      await login(values)
      toast.success('登录成功')
      navigate(redirect, { replace: true })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '登录失败，请重试')
    }
  }

  const handleFeishuLogin = () => {
    if (!isFeishuReady) {
      toast.error('当前环境尚未启用飞书 SSO')
      return
    }
    const nextUrl = new URL(`${API_BASE_URL}/api/auth/feishu/login`, window.location.origin)
    nextUrl.searchParams.set('redirect', redirect)
    nextUrl.searchParams.set('origin', window.location.origin)
    window.location.href = nextUrl.toString()
  }

  const feishuStatusText = isFeishuLoading ? '飞书 SSO 检测中' : isFeishuReady ? '飞书 SSO 已启用' : '飞书 SSO 未配置'

  return (
    <div className="login-shell">
      <div className="login-backdrop" />
      <Card className="login-card" bordered={false}>
        <div className="login-headline">
          <div className="login-brand-mark">
            <Bot size={18} />
            {/* <span>AI</span> */}
          </div>
          <span className="brand-kicker">Medical Translation Workspace</span>
          <Typography.Title level={2} className="login-title">
            医药翻译
          </Typography.Title>
          <Typography.Paragraph>
            面向企业内部的文本与文件翻译工作台，支持多语种翻译、术语库约束和历史记录管理。
          </Typography.Paragraph>
        </div>

        <div className="login-highlight">
          <div>
            <ShieldCheck size={18} />
            <span>邮箱密码主登录</span>
          </div>
          <button
            type="button"
            className={`login-highlight-sso ${isFeishuReady ? 'is-ready' : 'is-disabled'}`}
            onClick={handleFeishuLogin}
            disabled={isFeishuLoading || !isFeishuReady}
          >
            <LogIn size={18} />
            <span>{feishuStatusText}</span>
          </button>
        </div>

        <Form layout="vertical" onFinish={handleFinish} initialValues={DEMO_ACCOUNT} className="login-form-shell">
          <Form.Item
            label="邮箱"
            name="email"
            rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入合法邮箱地址' }]}
          >
            <Input placeholder="name@company.com" size="large" prefix={<Mail size={16} />} />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少 8 位' }]}
          >
            <Input.Password placeholder="请输入密码" size="large" />
          </Form.Item>
          <div className="login-actions">
            <Button type="primary" htmlType="submit" size="large" loading={isLoading} block className="login-primary-button">
              邮箱登录
            </Button>
            <div className="login-sso-section">
              <span className="login-sso-caption">
                {isFeishuReady ? '或使用企业统一身份入口' : '飞书 SSO 需后端完成配置后启用'}
              </span>
              <Button
                size="large"
                block
                className="login-sso-button"
                onClick={handleFeishuLogin}
                disabled={isFeishuLoading || !isFeishuReady}
              >
                {isFeishuLoading ? '检查飞书配置...' : '飞书 SSO 登录'}
              </Button>
            </div>
          </div>
        </Form>
      </Card>
    </div>
  )
}
