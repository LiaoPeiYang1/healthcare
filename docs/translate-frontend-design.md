# 医药翻译产品 — 前端设计规范

> 版本：v1.0  
> 日期：2026-03-31  
> 作者：待填写

---

## 一、项目概述

医药翻译平台是一个面向企业内部的独立 Web 应用，支持文本翻译和文件（DOCX/PDF）翻译，内置医药行业术语库（MedDRA），提供账号密码登录、可选飞书 SSO、历史记录管理、双语对照预览与纯译文 PDF 下载能力。

本项目为**全新独立工程**，不依赖任何现有系统的代码。

---

## 二、技术选型

### 2.1 框架与工具链

| 分类 | 技术 | 版本 |
|---|---|---|
| 框架 | React | ^18.3 |
| 构建 | Vite | ^5.x |
| 路由 | React Router DOM | v6 |
| 语言 | TypeScript | ^5.x |
| 样式 | Tailwind CSS | ^3.4 |
| UI 组件库 | Ant Design | ^5.x |
| 包管理 | pnpm | ^9.x |

### 2.2 状态管理

| 技术 | 范围 |
|---|---|
| **Zustand** | 全局状态：登录态、翻译任务、历史列表 |
| React `useState` / `useReducer` | 局部 UI 状态：弹窗、表单字段 |

选用 Zustand 而非 Context 的原因：文件翻译涉及多任务并发状态（每个文件独立 status/progress），Context 方案在此场景会产生大量无效 re-render。

### 2.3 完整依赖清单

```bash
# 核心
pnpm add react react-dom react-router-dom
pnpm add typescript

# 样式
pnpm add tailwindcss postcss autoprefixer
pnpm add tailwind-merge clsx

# UI
pnpm add antd
pnpm add lucide-react

# 状态
pnpm add zustand

# 文件上传
pnpm add react-dropzone
pnpm add spark-md5        # 分片上传 hash 校验
pnpm add @types/spark-md5 -D

# 文件预览
pnpm add pdfjs-dist       # PDF 预览（必须懒加载）
pnpm add dompurify        # DOCX 转 HTML 后的 XSS 净化
pnpm add @types/dompurify -D

# 工具
pnpm add date-fns         # 时间格式化
pnpm add nanoid           # 本地唯一 ID 生成

# 通知
pnpm add sonner           # Toast 提示

# 构建工具
pnpm add vite @vitejs/plugin-react -D
pnpm add @types/react @types/react-dom -D
```

### 2.4 不引入的技术及理由

| 候选 | 决定 | 理由 |
|---|---|---|
| `axios` | ❌ | 原生 fetch + 封装拦截器已足够，无需额外依赖 |
| `@tanstack/react-query` | ❌ | 轮询逻辑量小，自实现约 80 行，引入整包过重 |
| `react-hook-form` | ❌ | 仅登录表单一处，`useState` 足够 |
| `mammoth` | ❌ | DOCX 前端解析对复杂医药文档还原率不可靠，由服务端转 HTML 后展示 |
| `@react-pdf-viewer` | ❌ | 包体 500KB+，自封装 `pdfjs-dist` 更可控 |
| `redux` / `mobx` | ❌ | Zustand 轻量足够，无需重型状态管理 |

---

## 三、工程结构

```
medical-translate/
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx                        ← 应用入口
    ├── router.tsx                      ← 路由表 + 路由守卫
    │
    ├── pages/
    │   ├── login/
    │   │   └── index.tsx               ← 账密主登录 + 可选飞书SSO
    │   └── workspace/
    │       └── index.tsx               ← 主工作区（左右布局）
    │
    ├── components/
    │   ├── error-boundary/
    │   │   └── index.tsx               ← 错误边界（全局 + 工作区两层）
    │   ├── history-sidebar/
    │   │   ├── index.tsx               ← 左侧历史列表容器
    │   │   ├── history-item.tsx        ← 单条历史记录
    │   │   └── history-search.tsx      ← 搜索/筛选栏
    │   ├── lang-selector/
    │   │   └── index.tsx               ← 源语言 + 目标语言选择器
    │   ├── text-panel/
    │   │   ├── index.tsx               ← 文本翻译面板
    │   │   ├── text-input.tsx          ← 输入区（5000字符限制）
    │   │   └── text-result.tsx         ← 原文/译文展示 + 复制
    │   ├── file-panel/
    │   │   ├── index.tsx               ← 文件翻译面板
    │   │   ├── file-upload.tsx         ← 拖拽上传区（react-dropzone）
    │   │   ├── file-list.tsx           ← 已选文件列表 + 移除
    │   │   ├── file-progress.tsx       ← 上传/翻译进度展示
    │   │   ├── pdf-viewer.tsx          ← PDF 预览（pdfjs，懒加载）
    │   │   └── docx-viewer.tsx         ← DOCX 预览（展示服务端转 HTML）
    │   └── download-bar/
    │       └── index.tsx               ← 纯译文 PDF 下载按钮
    │
    ├── store/
    │   ├── auth.ts                     ← 登录态、token、用户信息
    │   ├── translate.ts                ← 文本翻译任务状态
    │   └── file-translate.ts           ← 文件翻译任务状态（单文件）
    │
    ├── api/
    │   ├── client.ts                   ← fetch 封装（token 注入、401 处理、重试）
    │   ├── auth.ts                     ← 登录、SSO、token 刷新接口
    │   ├── translate.ts                ← 文本翻译接口
    │   ├── file.ts                     ← 文件上传（分片）、合并接口
    │   └── history.ts                  ← 历史记录增删查接口
    │
    ├── hooks/
    │   ├── use-text-translation.ts     ← 文本翻译逻辑
    │   ├── use-file-translation.ts     ← 文件翻译 + 轮询逻辑
    │   ├── use-file-upload.ts          ← 分片上传逻辑（含 hash 计算）
    │   ├── use-history.ts              ← 历史记录增删查
    │   └── use-file-download.ts        ← 安全下载（Blob 方式）
    │
    ├── workers/
    │   └── hash.worker.ts              ← Web Worker：SparkMD5 计算文件 hash
    │
    └── types/
        └── index.ts                    ← 全局类型定义
```

---

## 四、核心模块设计

### 4.1 认证模块

#### 登录流程

```
用户访问任意页面
  └─ 路由守卫 <RequireAuth> 检查 store.auth.token 有效性
       ├─ 有效 → 放行
       └─ 无效/过期 → Navigate to /login?redirect=当前路径

/login 页面
  ├─ 默认展示账号密码登录表单（邮箱 + 密码）
  │    └─ 提交 → POST /api/auth/login
  │         → 获得 accessToken + refreshToken + expiresAt
  │         → 写入 localStorage + Zustand store
  │         → Navigate to redirect 目标页
  └─ 仅当飞书已完成配置时展示"飞书登录"按钮（可选入口）
       └─ 点击 → 跳转飞书 Web OAuth2 Authorization Code 授权页 → 回调带 code
            → POST /api/auth/sso/callback
            → 获得 accessToken + refreshToken + expiresAt
            → 写入 localStorage + Zustand store
            → Navigate to redirect 目标页
```

- 默认主登录方式为邮箱 + 密码
- 飞书登录为可选入口；仅在企业完成配置后展示
- 不开放用户自注册；账号由运维通过脚本或数据库预置
- 不提供用户侧修改密码、找回密码功能

#### Token 存储策略

```typescript
// store/auth.ts
type AuthState = {
  token: string | null
  refreshToken: string | null
  expiresAt: number | null   // Unix 毫秒时间戳
  userInfo: {
    userId: string
    name: string
    avatar: string
  } | null
  isLoading: boolean
}
```

- token 存 `localStorage`（持久化），避免新开标签页失效
- 初始化时从 `localStorage` 恢复到 Zustand store
- **不**将 token 写入 URL、cookie
- 退出登录时主动清除 `localStorage` 对应 key

#### 路由守卫

```typescript
// router.tsx
function RequireAuth({ children }: { children: ReactNode }) {
  const { token, expiresAt } = useAuthStore()
  const location = useLocation()

  const isValid = token && expiresAt && Date.now() < expiresAt

  if (!isValid) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname)}`}
        replace
      />
    )
  }
  return <>{children}</>
}
```

#### Token 自动刷新

```typescript
// api/client.ts 请求前置拦截
if (expiresAt && Date.now() > expiresAt - 60_000) {
  // 距过期不足 1 分钟，提前刷新
  await refreshAuth()
}

// 401 响应处理
if (res.status === 401) {
  const refreshed = await tryRefreshToken()
  if (refreshed) return request(url, options)   // 重试原请求
  logout()
  window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
}
```

---

### 4.2 文件上传模块（分片上传，单文件模式）

> 单文件上限 100MB；每次仅允许 1 个文件处于上传/翻译流程，禁止批量。

#### 分片流程

```
1. 用户拖拽或点击选择文件（仅允许 1 个）；若已有进行中的任务，上传区整体 disabled，Toast 提示“当前有文件在处理，请先完成或删除”。
2. react-dropzone 前端校验：类型 .docx/.pdf；大小 ≤100MB；超过或第二个文件一律拒绝并提示。
3. 单文件加入状态机，状态 → hashing；Web Worker 用 SparkMD5 计算 hash。
4. hash 完成 → POST /api/file/check { fileHash, filename, fileSize }。
   - exists=true → 秒传，拿到 fileId，状态 → queued。
   - exists=false → 从第 1 片开始分片上传，状态 → uploading。
5. 分片上传：固定 5MB/片，**串行**；每片成功更新 uploadProgress (0-100)。
6. merge：POST /api/file/merge；返回 fileId。
7. 自动触发翻译，状态 → translating；翻译完成/失败后才解锁上传区。
```

- 上传阶段如果用户刷新页面、关闭页面或重新进入系统，本次上传不恢复，需重新上传文件
- 文件历史仅在“上传成功并提交翻译任务”后创建；上传失败不进入历史列表

#### 文件任务类型定义

```typescript
// types/index.ts

type FileTaskStatus =
  | 'pending'       // 单文件加入队列
  | 'hashing'       // 计算 hash 中
  | 'uploading'     // 分片上传中
  | 'queued'        // 等待翻译（服务端排队）
  | 'translating'   // 翻译进行中（轮询）
  | 'done'          // 翻译完成
  | 'failed'        // 失败（含上传/翻译）
  | 'cancelled'     // 用户主动取消/删除

type FileTask = {
  localId: string            // 前端 UUID（nanoid 生成）
  file: File                 // 原始 File 对象
  name: string
  size: number
  status: FileTaskStatus
  uploadProgress: number     // 0-100
  fileId?: string            // 服务端文件 ID（上传完成后）
  taskId?: string            // 服务端翻译任务 ID
  resultFileId?: string      // 翻译结果文件 ID
  sourceLang: string
  targetLang: string
  error?: string
}
```

---

### 4.3 翻译任务轮询

> 轮询绑定在 Zustand store 层，与组件生命周期**完全解耦**。

```typescript
// store/file-translate.ts 关键逻辑

// store 外部维护轮询 Map（不放进 state，避免触发 re-render）
const pollingMap = new Map<string, ReturnType<typeof setInterval>>()

const useFileTranslateStore = create<FileTranslateState>((set, get) => ({
  tasks: [] as FileTask[],

  startPolling(taskId: string) {
    if (pollingMap.has(taskId)) return  // 防重复启动

    const id = setInterval(async () => {
      const result = await api.getTaskStatus(taskId)
      const { status, resultFileId } = result

      if (status === 'done') {
        clearInterval(id)
        pollingMap.delete(taskId)
        get().updateTask(taskId, { status: 'done', resultFileId })
      } else if (status === 'failed') {
        clearInterval(id)
        pollingMap.delete(taskId)
        get().updateTask(taskId, { status: 'failed', error: result.error })
      }
      // pending/translating 继续轮询
    }, 2000)

    pollingMap.set(taskId, id)
  },

  stopPolling(taskId: string) {
    const id = pollingMap.get(taskId)
    if (id) {
      clearInterval(id)
      pollingMap.delete(taskId)
    }
  },
}))
```

> **组件 unmount 时不调用 stopPolling**，轮询继续在后台运行；只有任务完成/失败/手动重置时才停止。

---

### 4.4 接口封装

```typescript
// api/client.ts

type RequestOptions = RequestInit & {
  skipAuth?: boolean    // 登录接口不需要带 token
}

async function request<T>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth = false, ...fetchOptions } = options

  if (!skipAuth) {
    const { token, expiresAt, refreshAuth } = useAuthStore.getState()
    // 提前刷新
    if (expiresAt && Date.now() > expiresAt - 60_000) {
      await refreshAuth()
    }
  }

  const currentToken = useAuthStore.getState().token

  const res = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(skipAuth ? {} : { Authorization: `Bearer ${currentToken}` }),
      ...fetchOptions.headers,
    },
  })

  if (res.status === 401 && !skipAuth) {
    const refreshed = await tryRefreshOnce()
    if (refreshed) return request<T>(url, options)
    useAuthStore.getState().logout()
    window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
    return Promise.reject(new Error('Unauthorized'))
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.msg || `请求失败: ${res.status}`)
  }

  return res.json() as Promise<T>
}
```

---

### 4.5 安全文件下载

> 禁止使用带签名的 OSS 直链。所有文件下载必须经过鉴权接口，以 Blob 形式在前端触发。

```typescript
// hooks/use-file-download.ts

export function useFileDownload() {
  const token = useAuthStore(s => s.token)

  const download = async (fileId: string, filename: string) => {
    const res = await fetch(`/api/translate/download/${fileId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!res.ok) {
      sonner.error('下载失败，请重试')
      return
    }

    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    // 立即释放，防止内存泄漏
    URL.revokeObjectURL(objectUrl)
  }

  return { download }
}
```

---

### 4.6 PDF 预览（懒加载）

> `pdfjs-dist` gzip 后约 800KB+，**必须懒加载**，不能同步 import。

```typescript
// pages/workspace/index.tsx

const PdfViewer = lazy(() => import('@/components/file-panel/pdf-viewer'))

// JSX 中使用
<Suspense fallback={<div className="flex items-center justify-center h-full"><Spin size="large" /></div>}>
  <PdfViewer fileId={currentTask.resultFileId} />
</Suspense>
```

```typescript
// components/file-panel/pdf-viewer.tsx
// 该文件内部才 import pdfjs-dist，保证只在懒加载时请求该包

import * as pdfjsLib from 'pdfjs-dist'
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'
```

---

### 4.7 DOCX 预览（XSS 防护）

> 服务端将 DOCX 转为 HTML 片段返回，前端展示前必须净化。

```typescript
// components/file-panel/docx-viewer.tsx

import DOMPurify from 'dompurify'

function DocxViewer({ htmlContent }: { htmlContent: string }) {
  const clean = DOMPurify.sanitize(htmlContent, {
    ALLOWED_TAGS: ['p', 'span', 'table', 'tr', 'td', 'th', 'ul', 'ol', 'li',
                   'strong', 'em', 'br', 'h1', 'h2', 'h3', 'h4'],
    ALLOWED_ATTR: ['style', 'class'],
  })

  return (
    <div
      className="docx-preview overflow-y-auto h-full p-4"
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  )
}
```

---

### 4.8 错误边界

```typescript
// 布局结构（两层隔离）

<GlobalErrorBoundary
  fallback={<FullPageError onRetry={() => window.location.reload()} />}
>
  <RouterProvider router={router} />
</GlobalErrorBoundary>

// workspace/index.tsx 内部
<WorkspaceErrorBoundary
  fallback={<div>右侧内容加载失败，<button>点击重置</button></div>}
>
  <WorkspacePanel />
</WorkspaceErrorBoundary>
```

错误边界覆盖场景：
- PDF 渲染崩溃（pdfjs 解析异常）
- DOCX 转 HTML 返回格式异常
- 任意组件级 JS 运行时报错

### 4.9 双语对照版布局与下载

- 版式：左右并排（左原文，右译文），保持页码/目录与原文一致；如译文变长导致溢出，优先缩小字号和行距，仍放不下时再追加续页，但不修改原页页码。
- 预览：文件翻译完成后默认展示“双语对照预览”，使用 pdfjs 渲染合成后的双语 PDF；加载态与错误态复用 PDF 预览方案。
- 下载：`download-bar` 中仅提供 `纯译文 PDF` 按钮，命名规范 `<原文件名>_<目标语言>_<日期>.pdf`。
- 历史详情中不提供原始上传文件下载入口。
- 目录：若原文件有目录（TOC），双语预览需保留目录结构与页码映射；前端仅展示，目录生成在后端完成。

---

## 五、关键业务逻辑说明

### 5.1 语言自动检测交互

```
输入框输入文字
  └─ 防抖 500ms
       └─ 源语言处于"自动检测"模式时
            → 调用 /api/detect 接口
            → 返回语言代码
            → 更新源语言下拉框显示（仅展示，不切换为手动模式）

用户手动选择源语言
  └─ 标记为"手动模式"
       → 不再触发自动检测
       → 用户主动切回"自动检测"选项后，恢复检测逻辑
```

### 5.2 源语言与目标语言相同的处理

```
用户将源语言和目标语言选择为相同时：
  → 发送按钮置灰
  → 输入框下方显示提示："源语言与目标语言不能相同"
  → 不允许提交翻译请求
```

### 5.3 文本翻译历史继续交互

```
点击左侧文本翻译历史条目
  → 右侧加载该记录的原文与译文
  → 底部输入框可用，供用户继续输入新文本
  → 用户输入并发送
       → 若源语言和目标语言均未变化，则更新该历史记录内容
       → 若中途修改了源语言或目标语言，则创建新的历史记录
       → 历史列表该条目的时间戳更新为当前时间
       → 注意：每次翻译完全独立，不传入历史上下文

文本翻译失败时：
  → 保留失败历史记录
  → 用户点击“重试”后更新原历史记录，不新建记录
```

### 5.4 文件翻译模式互斥

```
当文件翻译任务处于 uploading / translating 状态时：
  → 文件上传区域禁用（react-dropzone 设置 disabled）
  → 允许点击并查看其他历史记录
  → 允许继续进行文本翻译
  → 但不允许再次发起新的文件翻译任务
```

### 5.4.1 关闭页面与任务恢复

```
用户关闭页面、刷新页面或切换浏览器标签页：
  → 若任务已进入 translating，则后台文件翻译继续执行，不因前端页面卸载而中断
  → 若仍处于 uploading，则本次上传作废，用户重新进入后需重新上传
  → 用户再次进入系统后，从 /api/history 拉取最新状态
  → 若任务已完成，则可直接在历史记录中查看结果并下载
  → 若任务仍在执行，则恢复轮询状态并继续展示进度
```

### 5.5 历史记录删除

```
用户点击历史条目的删除图标
  → 弹出 antd Modal 确认弹窗
标题："确认删除"
    内容："删除后不可恢复，将同时删除云端源文件与翻译结果。确认删除？"
    按钮：取消 / 确认删除（红色）

  → 用户点击确认
       1. 调用 DELETE /api/history/:id
       2. store.history 移除该条目
       3. 若右侧当前展示的正是该条 → 重置右侧为新翻译初始状态
       4. 解锁上传区（单文件模式）
       5. Toast 提示"已删除"

  → 若任务状态为 uploading / translating：
       - 优先提示“当前任务执行中，确认取消并删除？”；确认后先触发后台取消再删
       - 前端将本地状态更新为 cancelled，等待后端删除完成后移出列表
```

### 5.6 单文件失败处理（单文件模式）

```
仅有 1 个文件处于流程中：
  → 上传阶段失败：不保留历史记录，用户需重新上传文件
  → 翻译阶段失败：状态 → failed，展示错误提示 + “重试”按钮（复用已上传原文件）
  → 取消时：状态 → cancelled，展示“已取消”提示，并允许直接重新发起翻译
  → 用户可点击“删除”移除失败文件，上传区随即解锁
  → 无“部分失败”场景
```

### 5.7 文件历史复用规则

```
文件历史创建后：
  → 翻译失败后点击“重试”，复用已上传原文件，并更新原历史记录
  → 已取消后点击“重新发起翻译”，复用已上传原文件，并更新原历史记录
  → 已完成后再次对同一原文件、同一语言对发起翻译，更新原历史记录并覆盖旧结果
  → 已完成后若更换语言对重新发起翻译，则创建新的历史记录
  → 覆盖旧结果时仅保留最新结果；页面不展示历史版本列表
  → 历史列表始终按 updated_at 倒序展示，最近操作过的记录排在最上面
```

### 5.8 文件解析与提示边界

```
用户上传 PDF 后：
  → 系统尽早检测是否为可提取正文的文本型 PDF
  → 若为扫描版/图片版 PDF，立即提示“暂不支持扫描版 PDF，请上传可编辑文本型 PDF 或 DOCX”

用户上传页数超过 10 页的文件：
  → 仅提示“文件页数较多，处理时间可能较长”
  → 不阻止提交，也不额外弹确认框

文件任务状态为 queued：
  → 仅展示“排队中”
  → 不展示排队序号
```

---

## 六、非功能性设计

### 6.1 性能目标

| 场景 | 目标 | 实现方式 |
|---|---|---|
| 首屏 FCP | < 2s | pdfjs 懒加载；路由级 code splitting（React.lazy） |
| 文本翻译响应 | P95 ≤ 5s | 前端请求 timeout 12s；后端模型 timeout 10s；429/5xx 允许自动重试 1 次 |
| 文件翻译完成（10页内） | ≤ 3 分钟 | 异步任务 + 历史恢复；页面关闭后任务继续 |
| 文件翻译轮询 | 2s 间隔 | store 层 setInterval；完成自动 clearInterval |
| 文件 hash 计算 | 不阻塞 UI | Web Worker（workers/hash.worker.ts）独立线程 |
| 大文件分片 | 5MB/片 | 串行上传；每片完成更新 uploadProgress |

### 6.2 兼容性

- 浏览器：Chrome、Edge 最新两个版本
- 最小分辨率：1280 × 720
- 无移动端适配需求（内部企业工具）

### 6.3 安全规范

| 规范 | 说明 |
|---|---|
| Token 存储 | `localStorage`，不写 URL Query、不写 cookie |
| 接口传输 | 全程 HTTPS；token 通过 `Authorization` Header 传递 |
| 文件下载 | 必须走鉴权接口 + Blob 下载，禁止 OSS 直链 |
| HTML 净化 | DOCX 转 HTML 展示前必须经过 DOMPurify 净化 |
| CORS | 上线前与后端确认 `Access-Control-Allow-Origin` 白名单 |
| 敏感信息 | 文件内容不写入浏览器缓存（`Cache-Control: no-store`） |

### 6.4 错误处理规范

| 场景 | 处理方式 |
|---|---|
| 文件格式不支持 | 前端拦截（react-dropzone accept），Toast："仅支持 .docx / .pdf" |
| 文件为扫描版/图片版 PDF | 尽早提示"暂不支持扫描版 PDF，请上传可编辑文本型 PDF 或 DOCX" |
| 单文件超 100MB | 前端拦截，Toast："文件大小不能超过 100MB" |
| 当前已有进行中的文件任务 | Toast："当前已有文件在处理中，请先完成或删除当前任务" |
| 自动检测语言不在支持范围内 | 提示"暂不支持该语种翻译"，并禁止提交 |
| 网络请求超时/失败 | 翻译区域展示"翻译失败"提示 + 重试按钮 |
| 接口 500 | Toast 显示服务端 msg 字段，提示联系管理员 |
| PDF 渲染崩溃 | WorkspaceErrorBoundary 兜底，显示"预览失败，请直接下载查看" |
| Token 失效 | 自动刷新；失败则跳登录页并带 redirect 参数 |
| 飞书 SSO 回调失败 | 页面展示"授权失败，请重试"，并提供账密登录入口 |

---

## 七、接口清单（待与后端对齐）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | 账密登录 |
| POST | `/api/auth/sso/callback` | 飞书 SSO code 换 token |
| POST | `/api/auth/refresh` | refreshToken 换新 token |
| POST | `/api/auth/logout` | 登出（服务端失效 token） |
| POST | `/api/translate/text` | 文本翻译 |
| POST | `/api/detect` | 语言自动检测 |
| POST | `/api/file/check` | 秒传校验（传 fileHash） |
| POST | `/api/file/chunk` | 分片上传（传 chunkIndex、chunkData） |
| POST | `/api/file/merge` | 合并分片（传 fileHash、totalChunks） |
| POST | `/api/translate/file` | 提交文件翻译任务（传 fileId、语言对） |
| GET | `/api/translate/status/:taskId` | 轮询翻译任务状态 |
| POST | `/api/translate/cancel/:taskId` | 取消文件翻译任务 |
| GET | `/api/translate/download/:fileId` | 鉴权下载翻译结果 |
| GET | `/api/history` | 历史列表（分页、类型筛选、关键词） |
| GET | `/api/history/:id` | 单条历史详情 |
| DELETE | `/api/history/:id` | 删除历史记录（含关联文件） |

---

## 八、默认决策（v1）

| # | 默认决策 | 影响模块 |
|---|---|---|
| 1 | 单文件 ≤100MB，且一次只允许 1 个文件 | 前端上传校验 |
| 2 | 删除历史时同步删除存储桶内源文件、纯译文结果和双语预览资源 | 接口设计 |
| 3 | 上传阶段刷新页面需重新上传；翻译阶段关闭页面后后台任务继续，再次进入系统后通过历史记录恢复结果和状态 | 轮询策略 |
| 4 | 默认主登录方式为邮箱 + 密码；飞书采用 Web OAuth2 Authorization Code 模式作为可选登录方式，未配置时隐藏入口 | 登录功能 |
| 5 | 后端上线前必须配置 CORS 白名单，仅允许前端正式域名和本地开发域名 | 所有接口 |
| 6 | 分片固定 5MB、串行上传；不支持上传断点续传，也不支持并行多片 | 上传性能 |
| 7 | DOCX 预览由服务端转 HTML 片段，前端仅负责净化与展示；文件翻译仅支持 `.docx` 和 `.pdf` | 文件预览 |
| 8 | 文本和文件翻译历史统一保留 30 天，到期自动删除；文件结果支持手动删除 | 体验/存储 |
| 9 | 文件翻译完成后默认展示双语对照预览；下载仅保留纯译文 PDF | 结果展示 |
| 10 | 首批支持语种为中文、英文、日文、韩文、德文、法文；自动检测到不支持语种时禁止提交 | 语言配置 |
| 11 | 历史列表默认每页 20 条，仅支持按文本/文件筛选，并按标题/文件名搜索 | 历史记录 |
