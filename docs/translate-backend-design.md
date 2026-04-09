# 医药翻译产品 — 后端设计规范

> 版本：v1.0  
> 日期：2026-03-31  
> 作者：待填写  
> 关联文档：translate-frontend-design.md

---

## 一、技术选型

### 1.1 核心框架

| 分类 | 技术 | 版本 | 说明 |
|---|---|---|---|
| AI Agent 框架 | **Agno** | ^1.x | 翻译 Pipeline 编排、术语库 Agent、多步骤 Workflow |
| Web 框架 | **FastAPI** | ^0.115 | HTTP API 层（Agno Runtime 内置） |
| 语言 | **Python** | ^3.11 | 全量类型注解 |
| 任务队列 | **Celery** | ^5.x | 文件翻译异步任务 |
| 消息中间件 | **Redis** | ^7.x | Celery Broker + 轮询状态缓存 |
| 数据库 | **PostgreSQL** | ^16 | 持久化存储（用户、历史、任务） |
| ORM | **SQLAlchemy** | ^2.x | 异步 ORM（async engine） |
| 数据库迁移 | **Alembic** | ^1.x | Schema 版本管理 |
| 文件存储 | **MinIO / 阿里云 OSS** | — | 原文件 + 译文文件存储 |
| 容器 | **Docker + Docker Compose** | — | 本地开发 + 生产部署 |

### 1.2 完整依赖清单

```bash
# web + agno
pip install agno fastapi uvicorn[standard]

# 数据库
pip install sqlalchemy asyncpg alembic psycopg2-binary

# 缓存 / 队列
pip install redis celery

# 文件处理
pip install python-docx PyMuPDF  # DOCX 解析 + PDF 解析
pip install python-multipart      # 文件上传

# 对象存储
pip install boto3                 # MinIO / S3 兼容
pip install oss2                  # 阿里云 OSS（二选一）

# 认证
pip install python-jose[cryptography]  # JWT
pip install passlib[bcrypt]            # 密码 hash
pip install httpx                      # 飞书 SSO 回调请求

# 翻译 LLM（通义千问免费模型，OpenAI 兼容协议）
pip install dashscope             # 通义千问 SDK，兼容 OpenAI API

# 配置
pip install pydantic-settings     # 环境变量管理

# 工具
pip install python-dotenv
pip install structlog              # 结构化日志

# 开发 / 测试
pip install pytest pytest-asyncio httpx ruff mypy
```

### 1.3 架构分层

```
┌─────────────────────────────────────────────┐
│            FastAPI (HTTP 入口层)             │
│  routers/ — 路由  │  middleware/ — 鉴权/日志 │
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│              Service 层（业务逻辑）           │
│  auth_service  translate_service  file_service│
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│           Agno Workflow / Agent 层           │
│  TranslationWorkflow                         │
│    ├── TerminologyAgent  (MedDRA 术语匹配)   │
│    ├── TranslatorAgent   (LLM 翻译)          │
│    └── PostProcessAgent  (术语回写/校对)      │
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│              基础设施层                       │
│  PostgreSQL  │  Redis  │  MinIO/OSS  │  Celery│
└─────────────────────────────────────────────┘
```

---

## 二、工程结构

```
medical-translate-backend/
├── pyproject.toml                  ← 依赖 + 工具配置
├── alembic.ini
├── .env.example
├── docker-compose.yml
├── Dockerfile
│
├── alembic/
│   └── versions/                  ← 数据库迁移文件
│
├── app/
│   ├── main.py                    ← FastAPI 应用入口
│   ├── config.py                  ← 环境变量 (pydantic-settings)
│   ├── deps.py                    ← 全局依赖注入（DB Session、当前用户）
│   │
│   ├── routers/                   ← HTTP 路由层（只做参数校验和调用 service）
│   │   ├── auth.py                ← /api/auth/*
│   │   ├── translate.py           ← /api/translate/*
│   │   ├── file.py                ← /api/file/*
│   │   └── history.py             ← /api/history/*
│   │
│   ├── schemas/                   ← Pydantic 请求/响应模型
│   │   ├── auth.py
│   │   ├── translate.py
│   │   ├── file.py
│   │   └── history.py
│   │
│   ├── models/                    ← SQLAlchemy ORM 模型
│   │   ├── base.py                ← DeclarativeBase + 公共字段
│   │   ├── user.py
│   │   ├── translate_task.py
│   │   ├── file_chunk.py
│   │   ├── terminology_version.py
│   │   ├── terminology_term.py
│   │   └── history.py
│   │
│   ├── services/                  ← 业务逻辑层
│   │   ├── auth_service.py        ← 飞书SSO、JWT、账密登录
│   │   ├── translate_service.py   ← 文本翻译入口（调用 Workflow）
│   │   ├── file_service.py        ← 分片上传、合并、秒传
│   │   └── history_service.py     ← 历史记录 CRUD
│   │
│   ├── agents/                    ← Agno Agent / Workflow 定义
│   │   ├── translation_workflow.py← 核心翻译 Workflow
│   │   ├── terminology_agent.py   ← MedDRA 术语匹配 Agent
│   │   ├── translator_agent.py    ← LLM 翻译 Agent
│   │   └── tools/
│   │       ├── meddra_tool.py     ← MedDRA 术语库查询工具
│   │       └── detect_lang_tool.py← 语言检测工具
│   │
│   ├── tasks/                     ← Celery 异步任务
│   │   ├── celery_app.py          ← Celery 实例
│   │   └── file_translate_task.py ← 文件翻译异步任务
│   │
│   ├── core/
│   │   ├── security.py            ← JWT 生成/校验、密码 hash
│   │   ├── storage.py             ← MinIO/OSS 文件上传下载封装
│   │   └── exceptions.py          ← 自定义异常 + 全局异常处理
│   │
│   └── db/
│       ├── session.py             ← async SQLAlchemy engine + session
│       └── redis.py               ← Redis 连接池
│
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_translate.py
    └── test_file.py
```

---

## 三、数据库设计

### 3.1 users 表

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE,
    name        VARCHAR(100) NOT NULL,
    avatar_url  VARCHAR(500),
    auth_type   VARCHAR(20) NOT NULL,  -- 'feishu' | 'password'
    password_hash VARCHAR(255),        -- 仅 auth_type='password' 时有值
    feishu_union_id VARCHAR(100),      -- 飞书唯一标识
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 translate_tasks 表

```sql
CREATE TABLE translate_tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type   VARCHAR(20) NOT NULL,  -- 'text' | 'file'
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | hashing | uploading | queued | translating | done | failed | cancelled
    source_lang VARCHAR(10) NOT NULL,
    target_lang VARCHAR(10) NOT NULL,
    terminology_version VARCHAR(50),   -- 术语库版本，便于结果追溯

    -- 文本翻译字段
    source_text TEXT,
    result_text TEXT,

    -- 文件翻译字段
    source_file_id  VARCHAR(255),      -- 存储桶中的 key
    result_file_id  VARCHAR(255),      -- 纯译文 PDF key
    bilingual_file_id VARCHAR(255),    -- 双语对照预览 PDF key（仅页面预览，不提供下载）
    original_filename VARCHAR(255),
    file_size   BIGINT,

    error_msg   TEXT,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_translate_tasks_user_id ON translate_tasks(user_id);
CREATE INDEX idx_translate_tasks_status ON translate_tasks(status);
```

### 3.3 file_chunks 表（分片上传追踪）

```sql
CREATE TABLE file_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash    VARCHAR(64) NOT NULL,   -- SparkMD5 hash
    user_id      UUID NOT NULL REFERENCES users(id),
    chunk_index  INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunk_key    VARCHAR(255) NOT NULL,  -- 存储桶中的临时 key
    uploaded_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (file_hash, chunk_index)
);

CREATE INDEX idx_file_chunks_hash ON file_chunks(file_hash);
```

### 3.4 uploaded_files 表（秒传记录）

```sql
CREATE TABLE uploaded_files (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash   VARCHAR(64) UNIQUE NOT NULL,
    file_key    VARCHAR(255) NOT NULL,   -- 存储桶中的最终 key
    filename    VARCHAR(255),
    file_size   BIGINT,
    mime_type   VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.5 terminology_versions 表（术语库版本）

```sql
CREATE TABLE terminology_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      VARCHAR(20) NOT NULL,      -- 'meddra' | 'enterprise'
    version     VARCHAR(50) NOT NULL,      -- 如 '27.0' / '2026.04'
    status      VARCHAR(20) NOT NULL DEFAULT 'active',
    -- draft | active | archived
    description VARCHAR(255),
    released_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, version)
);

CREATE UNIQUE INDEX idx_terminology_versions_active
ON terminology_versions(source)
WHERE status = 'active';
```

### 3.6 terminology_terms 表（术语条目）

```sql
CREATE TABLE terminology_terms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      UUID NOT NULL REFERENCES terminology_versions(id) ON DELETE CASCADE,
    source          VARCHAR(20) NOT NULL,      -- 'meddra' | 'enterprise'
    term            VARCHAR(255) NOT NULL,     -- 原始术语
    normalized_term VARCHAR(255) NOT NULL,     -- 归一化后术语，用于精确查询
    translation     VARCHAR(255) NOT NULL,     -- 标准译法
    source_lang     VARCHAR(10) NOT NULL,
    target_lang     VARCHAR(10) NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 100,
    -- 数值越小优先级越高；企业自定义术语可覆盖 MedDRA 默认结果
    is_active       BOOLEAN DEFAULT TRUE,
    metadata        JSONB DEFAULT '{}'::jsonb, -- pt/llt/code/category 等扩展信息
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (version_id, normalized_term, source_lang, target_lang)
);

CREATE INDEX idx_terminology_terms_lookup
ON terminology_terms(normalized_term, source_lang, target_lang, is_active);

CREATE INDEX idx_terminology_terms_version_id
ON terminology_terms(version_id);
```

> 说明：
> - `terminology_versions` 用于管理 MedDRA 标准术语库版本和企业自定义术语版本。
> - `terminology_terms` 为统一条目表；运行时按 `priority` + `source` 规则查询，优先命中企业自定义术语，再回退到 MedDRA。
> - `translate_tasks.terminology_version` 可记录本次翻译命中的版本快照，例如 `meddra:27.0|enterprise:2026.04`，用于结果追溯。

### 3.7 history 表（翻译历史记录）

```sql
CREATE TABLE history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id     UUID NOT NULL REFERENCES translate_tasks(id) ON DELETE CASCADE,
    title       VARCHAR(255),           -- 自动截取原文前50字/文件名
    task_type   VARCHAR(20) NOT NULL,
    source_lang VARCHAR(10),
    target_lang VARCHAR(10),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_history_user_id ON history(user_id);
CREATE INDEX idx_history_created_at ON history(created_at DESC);
```

---

## 四、Agno 翻译 Workflow 设计

### 4.1 核心架构说明

Agno Workflow 用于编排翻译 Pipeline 的多步骤执行，每一步可以是 Agent 或普通函数：

```
TranslationWorkflow
  Step 1: detect_language()          ← 普通函数（本地正则/langdetect）
  Step 2: TerminologyAgent            ← Agent：在文本中识别 MedDRA 术语，建立替换表
  Step 3: TranslatorAgent             ← Agent：调用 LLM 翻译，占位符保护术语不被翻译
  Step 4: PostProcessAgent            ← Agent：将占位符替换回标准术语译文
```

### 4.2 翻译 Workflow 实现

```python
# app/agents/translation_workflow.py

from agno.workflow import Workflow
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.agents.tools.meddra_tool import MedDRALookupTool
from app.config import settings
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationInput:
    text: str
    source_lang: str
    target_lang: str


@dataclass
class TranslationOutput:
    translated_text: str
    terminology_map: dict[str, str]   # {原文术语: 标准译文}


# Step 1 - 术语识别 Agent
terminology_agent = Agent(
    name="TerminologyAgent",
    model=OpenAIChat(
        id=settings.LLM_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,  # 通义千问 OpenAI 兼容
    ),
    tools=[MedDRALookupTool()],
    instructions=[
        "你是医药术语识别专家。",
        "从输入文本中识别所有医药专业术语，调用 meddra_lookup 工具查询标准译法。",
        "返回 JSON 格式：{\"terms\": [{\"original\": \"随机对照试验\", \"translation\": \"randomized controlled trial\", \"placeholder\": \"__TERM_0__\"}]}",
        "如果术语库中不存在该词，不加入列表。",
    ],
    response_model=None,
)

# Step 2 - 翻译 Agent
translator_agent = Agent(
    name="TranslatorAgent",
    model=OpenAIChat(
        id=settings.LLM_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
    ),
    instructions=[
        "你是专业医药翻译引擎。",
        "输入文本中的 __TERM_N__ 是术语占位符，翻译时原样保留，不得修改。",
        "保持原文格式（段落、标点、换行）不变。",
        "只返回译文，不要解释、不要加前缀。",
    ],
)

# Step 3 - 后处理 Agent
postprocess_agent = Agent(
    name="PostProcessAgent",
    model=OpenAIChat(
        id=settings.LLM_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
    ),
    instructions=[
        "将译文中的占位符替换为对应的标准术语译文。",
        "只做替换，不修改其他任何内容。",
        "返回最终译文。",
    ],
)


class TranslationWorkflow(Workflow):
    """医药文本翻译 Workflow"""

    name: str = "MedicalTranslationWorkflow"

    terminology_agent: Agent = terminology_agent
    translator_agent: Agent = translator_agent
    postprocess_agent: Agent = postprocess_agent

    def run(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        执行完整翻译流程，返回最终译文
        """
        # Step 1: 识别术语，建立占位符映射
        term_response = self.terminology_agent.run(
            f"识别以下{source_lang}文本中的医药术语：\n\n{text}"
        )
        term_data = self._parse_terms(term_response.content)

        # Step 2: 用占位符替换原文中的术语
        protected_text = text
        for item in term_data:
            protected_text = protected_text.replace(
                item["original"], item["placeholder"]
            )

        # Step 3: 翻译（含占位符的文本）
        translate_prompt = (
            f"将以下{source_lang}文本翻译为{target_lang}，"
            f"占位符原样保留：\n\n{protected_text}"
        )
        translated_response = self.translator_agent.run(translate_prompt)
        translated_with_placeholders = translated_response.content

        # Step 4: 将占位符替换为标准术语译文
        final_text = translated_with_placeholders
        for item in term_data:
            final_text = final_text.replace(
                item["placeholder"], item["translation"]
            )

        return final_text

    def _parse_terms(self, content: str) -> list[dict]:
        """解析术语 Agent 返回的 JSON，容错处理"""
        import json, re
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get("terms", [])
        except Exception:
            pass
        return []
```

### 4.3 MedDRA 术语查询工具

```python
# app/agents/tools/meddra_tool.py

from agno.tools import Tool
from app.db.session import get_sync_session


class MedDRALookupTool(Tool):
    """查询 MedDRA 医药术语库"""

    name: str = "meddra_lookup"
    description: str = "在本地术语库中查询医药专业术语的标准译法，优先企业术语，再回退到 MedDRA"

    def meddra_lookup(self, term: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        查询术语标准译法。
        :param term: 待查询术语（原文）
        :param source_lang: 源语言代码
        :param target_lang: 目标语言代码
        :return: 标准译文，若不存在返回空字符串
        """
        with get_sync_session() as session:
            result = session.execute(
                """
                SELECT t.translation
                FROM terminology_terms t
                JOIN terminology_versions v ON v.id = t.version_id
                WHERE t.normalized_term = :normalized_term
                  AND t.source_lang = :sl
                  AND t.target_lang = :tl
                  AND t.is_active = TRUE
                  AND v.status = 'active'
                ORDER BY t.priority ASC,
                         CASE WHEN t.source = 'enterprise' THEN 0 ELSE 1 END,
                         v.released_at DESC NULLS LAST
                LIMIT 1
                """,
                {
                    "normalized_term": term.strip().lower(),
                    "sl": source_lang,
                    "tl": target_lang,
                }
            ).fetchone()
            return result[0] if result else ""
```

#### 默认决策

- MedDRA 术语库采用本地数据库表维护，不依赖在线公共 API，避免运行时外部依赖和合规风险。
- 术语库支持独立更新，不依赖应用发版；每次更新生成 `version`，并在 `translate_tasks.terminology_version` 中落库，保证历史结果可追溯。
- 查询优先级为：企业自定义术语 > MedDRA 标准术语 > 通用模型翻译。

---

## 五、核心接口设计

### 5.1 认证 `/api/auth`

#### POST /api/auth/login — 账密登录

```python
# Request
class LoginRequest(BaseModel):
    email: str
    password: str

# Response
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int        # Unix 毫秒时间戳
    token_type: str = "Bearer"
    user_info: UserInfo
```

- 默认主登录方式为邮箱 + 密码
- 系统不开放用户自注册；账号由运维通过脚本或数据库预置
- 不提供用户侧修改密码、找回密码能力，也不提供管理端
- 会话策略：access token 1 小时，refresh token 7 天

#### POST /api/auth/sso/callback — 飞书 SSO

```python
# Request
class SSOCallbackRequest(BaseModel):
    code: str              # 飞书授权码

# 内部流程：
# 作为可选登录方式接入，默认不展示；仅在企业完成配置后启用
# 采用飞书开放平台 Web 应用 OAuth2 Authorization Code 模式
# 1. 用 code 换飞书 user_access_token
# 2. 用 token 获取飞书用户信息
# 3. upsert users 表
# 4. 生成本系统 JWT 返回
```

#### JWT 规范

```python
# core/security.py

ACCESS_TOKEN_EXPIRE = 60 * 60        # 1小时
REFRESH_TOKEN_EXPIRE = 60 * 60 * 24 * 7  # 7天

# Payload
{
    "sub": "user_id",                # UUID
    "type": "access" | "refresh",
    "iat": 1711900000,
    "exp": 1711903600
}
```

---

### 5.2 语言检测 `/api/detect`

#### POST /api/detect

```python
# Request
class DetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)

# Response
class DetectResponse(BaseModel):
    lang: str    # 'zh' | 'en' | 'ja' | 'ko' | 'de' | 'fr' 等
    confidence: float  # 0-1

# 实现：优先用 langdetect 本地检测，不调用 LLM，保证低延迟
```

---

### 5.3 文本翻译 `/api/translate/text`

#### POST /api/translate/text

```python
# Request
class TextTranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_lang: str       # 'auto' 或具体语言代码
    target_lang: str
    history_id: Optional[str] = None   # 传入则更新该历史记录

# Response（非流式）
class TextTranslateResponse(BaseModel):
    task_id: str
    translated_text: str
    source_lang: str       # 实际使用的源语言（auto 时返回检测结果）
    terminology_count: int # 命中的术语数量

# 流程
# 1. 校验参数
# 2. source_lang='auto' 时先检测语言
# 3. 调用 TranslationWorkflow（同步，目标 P95 ≤ 5s）
# 4. 若检测结果不在支持语种（zh/en/ja/ko/de/fr）范围内，则返回“不支持该语种翻译”
# 5. 写入 translate_tasks 表
# 6. 新增或更新 history 表
#    - 当前会话内连续发送且语言对不变：更新原 history
#    - 点击“新建翻译”或语言对变更：创建新 history
#    - 失败重试：更新原 history，保留失败记录
# 7. 返回结果
```

**性能保障**：文本翻译在 FastAPI 的异步 handler 中直接执行 Workflow，不走 Celery，目标 `P95 ≤ 5s`。后端模型调用 timeout 10s，对 `429/5xx` 自动重试 1 次；前端请求 timeout 12s，与后端保持一致体验。

---

### 5.4 文件上传 `/api/file`

#### POST /api/file/check — 秒传检查

```python
# Request
class FileCheckRequest(BaseModel):
    file_hash: str         # SparkMD5 hash
    filename: str
    file_size: int         # 字节数
    total_chunks: int
    # 约束：单文件模式，若当前用户存在 uploading/queued/translating 任务则返回 409，前端需先完成或删除

# Response
class FileCheckResponse(BaseModel):
    exists: bool
    file_id: Optional[str]   # exists=True 时返回，可直接用于翻译
```

#### POST /api/file/chunk — 上传分片

```python
# Multipart Form
# - file_hash: str
# - chunk_index: int
# - total_chunks: int
# - chunk: UploadFile
# 约束：服务端固定 chunk 大小 5MB（最后一片可小于等于 5MB）；若 total_chunks 与 file_size/5MB 不符则 400
# 单文件模式：检测到当前用户已有活动文件任务时直接 409
# 刷新页面或重新进入系统后不做上传恢复，用户需重新上传整个文件

# Response
class ChunkUploadResponse(BaseModel):
    chunk_index: int
    success: bool
```

#### POST /api/file/merge — 合并分片

```python
# Request
class FileMergeRequest(BaseModel):
    file_hash: str
    filename: str
    total_chunks: int
    mime_type: str         # 'application/pdf' | 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

# 校验文件大小
# Response
class FileMergeResponse(BaseModel):
    file_id: str           # 合并后的文件 ID，用于提交翻译

# 合并流程：
# 1. 校验 total_chunks 片全部存在
# 2. 校验 total_chunks == ceil(file_size / 5MB)，且 file_size ≤ 100MB
# 3. 按顺序从 MinIO 读取各片，流式 append 到目标 key
# 4. 删除临时分片
# 5. 写入 uploaded_files 表
# 6. 返回 file_id
# 7. 仅在提交翻译任务成功后创建 history；上传阶段失败不保留历史记录
```

---

### 5.5 文件翻译 `/api/translate/file`

#### POST /api/translate/file — 提交翻译任务

```python
# Request
class FileTranslateRequest(BaseModel):
    file_id: str
    source_lang: str
    target_lang: str

# Response（立即返回，任务异步执行）
class FileTranslateResponse(BaseModel):
    task_id: str
    status: str = "queued"

# 约束：单文件模式。提交前检查当前用户是否已有 status ∈ {uploading, queued, translating} 的文件任务，若有返回 409
# Celery 端应为同一 user_id 设置互斥锁，防止并行消费
# 历史规则：
# - 上传成功并提交翻译任务后立即创建 history
# - failed / cancelled 状态重新发起翻译时，无论语言对是否变化，均更新原 history
# - done 状态下同语言对重新翻译：更新原 history 并覆盖旧结果
# - done 状态下更换语言对重新翻译：创建新 history
```

#### GET /api/translate/status/{task_id} — 轮询状态

```python
# Response
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str            # pending|queued|translating|done|failed|cancelled
    progress: Optional[int]   # 0-100，翻译进度百分比（可选）
    result_file_id: Optional[str]
    bilingual_file_id: Optional[str]  # 仅用于页面双语预览
    error: Optional[str]
    updated_at: datetime
```

#### POST /api/translate/cancel/{task_id} — 取消文件翻译

```python
# Response
class TaskCancelResponse(BaseModel):
    task_id: str
    status: str = "cancelled"

# 流程
# 1. 校验 task_id 属于当前用户且 task_type='file'
# 2. 若任务处于 pending/queued/translating，则撤销 Celery 任务并释放用户级互斥锁
# 3. 更新 translate_tasks.status='cancelled'
# 4. 保留原始文件，便于后续直接重新发起翻译；结果文件由后续重试覆盖或删除接口统一清理
```

---

### 5.6 文件下载 `/api/translate/download/{file_id}`

```python
# GET /api/translate/download/{file_id}
# Header: Authorization: Bearer <token>

# 流程：
# 1. 校验 token，获取 user_id
# 2. 查询 translate_tasks，确认该 file_id 为当前用户的纯译文结果文件（数据隔离）
# 3. 从 MinIO/OSS 生成限时私有下载 URL（有效期 60s）
# 4. 以 StreamingResponse 代理返回，不暴露存储桶直链

# 约束：
# - 仅支持下载纯译文 PDF
# - 不提供原始上传文件和双语预览文件的下载接口

from fastapi.responses import StreamingResponse

@router.get("/download/{file_id}")
async def download_file(file_id: str, current_user = Depends(get_current_user)):
    # 权限校验
    task = await translate_service.get_task_by_file_id(file_id, current_user.id)
    if not task:
        raise HTTPException(403, "无权访问该文件")

    # 从存储桶流式读取，代理响应
    stream = await storage.stream_file(file_id)
    return StreamingResponse(
        stream,
        media_type=task.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{task.translated_filename}"'}
    )
```

---

### 5.7 历史记录 `/api/history`

#### GET /api/history — 列表（分页+筛选）

```python
# Query Params
class HistoryQueryParams(BaseModel):
    page: int = 1
    page_size: int = 20        # 最大 50
    task_type: Optional[str]   # 'text' | 'file'
    keyword: Optional[str]     # 搜索 title

# Response
class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
```

#### DELETE /api/history/{id} — 删除

```python
# 流程：
# 1. 校验 history.user_id == current_user.id（数据隔离）
# 2. 若关联文件任务状态为 pending/queued/translating，先调用 cancel 逻辑，将状态置为 cancelled
# 3. 尝试删除 MinIO/OSS 上的原文件 + 纯译文 PDF + 双语预览文件（忽略对象不存在）
# 4. 删除 translate_tasks 记录
# 5. 删除 history 记录
# 6. 返回 204 No Content
```

---

## 六、Celery 异步文件翻译任务

```python
# app/tasks/file_translate_task.py

from app.tasks.celery_app import celery
from app.agents.translation_workflow import TranslationWorkflow
from app.core.storage import storage
from app.db.session import get_sync_session
import structlog

logger = structlog.get_logger()


@celery.task(bind=True, max_retries=2, default_retry_delay=5)
def translate_file_task(self, task_id: str):
    """
    文件翻译异步任务
    1. 从存储桶下载原文件
    2. 解析文本（DOCX/PDF 分别处理）
       - 仅支持 `.docx` 与文本型 `.pdf`
       - 扫描版/图片版 PDF 不做 OCR，尽早返回“不支持扫描版 PDF”
    3. 按段落调用 TranslationWorkflow
    4. 统一生成 PDF 结果
       - 纯译文 PDF：用于下载
       - 双语对照 PDF：仅用于页面预览，左右并排排版，保留原页码/目录；若译文超长优先缩放字体/留白，不改页码编号
    6. 更新任务状态
    """
    log = logger.bind(task_id=task_id)

    with get_sync_session() as db:
        try:
            # 1. 更新状态为 translating
            task = db.query(TranslateTask).filter_by(id=task_id).first()
            if task.status == "cancelled":
                log.info("file_translation_skipped_cancelled", task_id=task_id)
                return
            task.status = "translating"
            task.started_at = datetime.utcnow()
            db.commit()

            log.info("file_translation_started", filename=task.original_filename)

            # 2. 下载原文件
            file_bytes = storage.download(task.source_file_id)

            # 3. 解析 + 翻译
            workflow = TranslationWorkflow()
            if task.original_filename.endswith(".pdf"):
                result = _translate_pdf(file_bytes, task, workflow)
            else:
                result = _translate_docx(file_bytes, task, workflow)

            # 4. 上传结果文件
            result_key = f"results/{task_id}/translated.pdf"
            bilingual_key = f"results/{task_id}/bilingual-preview.pdf"
            storage.upload(result_key, result.translated_bytes)
            storage.upload(bilingual_key, result.bilingual_bytes)

            # 5. 更新状态为 done
            task.status = "done"
            task.result_file_id = result_key
            task.bilingual_file_id = bilingual_key
            task.finished_at = datetime.utcnow()
            db.commit()

            log.info("file_translation_done", task_id=task_id)

        except Exception as exc:
            if task.status == "cancelled":
                log.info("file_translation_cancelled", task_id=task_id)
                db.commit()
                return
            log.error("file_translation_failed", error=str(exc))
            task.status = "failed"
            task.error_msg = str(exc)
            task.finished_at = datetime.utcnow()
            db.commit()

            # Celery 自动重试（最多2次）
            raise self.retry(exc=exc)
```

---

## 七、中间件与安全

### 7.1 认证中间件

```python
# app/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.core.security import decode_token

security = HTTPBearer()

async def get_current_user(token = Depends(security), db = Depends(get_db)):
    payload = decode_token(token.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
```

### 7.2 数据隔离规范

**所有涉及用户数据的查询，必须在 WHERE 条件中带上 `user_id = current_user.id`**，不允许仅凭 `task_id` 查询数据：

```python
# ✅ 正确
task = await db.execute(
    select(TranslateTask)
    .where(TranslateTask.id == task_id)
    .where(TranslateTask.user_id == current_user.id)   # 数据隔离
)

# ❌ 错误：缺少 user_id 过滤
task = await db.get(TranslateTask, task_id)
```

### 7.3 CORS 配置

```python
# app/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,   # 从环境变量读取，不写死
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 7.4 文件安全校验

```python
# app/services/file_service.py

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def validate_file_chunk(chunk: UploadFile, file_size: int):
    # 1. 校验 MIME Type（不信任客户端传来的 mime_type，从文件头 magic bytes 检测）
    header_bytes = chunk.file.read(16)
    chunk.file.seek(0)
    detected_mime = detect_mime_from_bytes(header_bytes)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "不支持的文件格式")

    # 2. 校验文件大小
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, "文件大小不能超过 100MB")

    # 3. PDF 必须为可提取正文的文本型 PDF；扫描版/图片版 PDF 不做 OCR
```

### 7.5 限流

```python
# 基于 Redis 的滑动窗口限流

# 文本翻译：每用户每分钟最多 30 次
# 文件翻译：每用户同时最多 1 个任务（前端也禁用并发）
# 文件上传：每用户每小时最多 500 片（防止恶意分片轰炸；单文件模式下主要防刷）
# 默认部署：Celery worker 并发 2~4；v1 不引入优先级队列，文本翻译走同步接口，不占用 Celery 队列
```

---

## 八、环境变量

```ini
# .env.example

# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/medical_translate

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# 飞书 SSO
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_REDIRECT_URI=https://yourdomain.com/api/auth/sso/callback

# LLM（通义千问免费模型，OpenAI 兼容协议）
LLM_PROVIDER=dashscope      # 'dashscope' 兼容 openai api
LLM_MODEL=qwen-turbo
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 对象存储（MinIO）
STORAGE_PROVIDER=minio      # 'minio' | 'oss'
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=medical-translate
MINIO_SECURE=false

# CORS
ALLOWED_ORIGINS=["http://localhost:5173","https://yourdomain.com"]

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## 九、Docker Compose（本地开发）

```yaml
# docker-compose.yml

version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: .
    env_file: .env
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medical_translate
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  miniodata:
```

---

## 十、非功能性设计

### 10.1 性能目标

| 接口 | 目标 | 方案 |
|---|---|---|
| 文本翻译 | P95 ≤ 5s | 同步执行 Workflow；LLM timeout 10s；429/5xx 自动重试 1 次 |
| 文件翻译入队 | ≤ 200ms | 立即返回 taskId，Celery 异步处理 |
| 文件翻译完成 | ≤ 3 分钟（10页内） | Celery worker 独立进程；页面关闭后继续；完成后从历史恢复 |
| 轮询接口 | ≤ 50ms | Redis 缓存任务状态，不查数据库 |
| 文件下载代理 | 流式传输 | StreamingResponse，不缓存到内存 |

### 10.2 错误处理规范

```python
# app/core/exceptions.py

class AppException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

# 统一响应格式
{
    "code": 0,       # 0=成功，非0=业务错误
    "msg": "success",
    "data": {}
}

# 业务错误码
1001: Token 无效
1002: Token 已过期
1003: 无权访问该资源
2001: 文件格式不支持
2002: 文件大小超限
2003: 翻译任务不存在
2004: 翻译服务暂时不可用
2005: 文件任务已取消
```

### 10.3 运行日志规范

```python
# 使用 structlog 结构化日志，每条日志必须包含：
{
    "timestamp": "2026-03-31T10:00:00Z",
    "level": "info",
    "event": "text_translation_completed",
    "user_id": "uuid",
    "task_id": "uuid",
    "source_lang": "zh",
    "target_lang": "en",
    "duration_ms": 1234,
    "terminology_hits": 3,
    "trace_id": "request-id"
}
```

- 日志仅记录元数据，不落原文、译文、文件正文，避免敏感内容进入日志系统

### 10.4 数据保留

- 文本和文件翻译历史统一保留 30 天；到期后由定时任务自动删除历史记录
- 文件翻译结果到期时同步删除存储桶中的原文件、纯译文 PDF 和双语预览文件
- 用户可在到期前手动删除；手动删除优先于自动清理
- 自动清理任务每日凌晨执行 1 次

### 10.5 可用性

- FastAPI 无状态，水平扩展
- Celery Worker 可独立扩容
- 健康检查接口 `GET /health`，返回 DB/Redis/Storage 连通性
- 监控与告警默认接入 Prometheus + Alertmanager，至少覆盖 `LLM 429/超时率`、`文件任务失败率`、`存储删除失败数`

---

## 十一、接口汇总

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/auth/login` | ❌ | 账密登录 |
| POST | `/api/auth/sso/callback` | ❌ | 飞书 SSO |
| POST | `/api/auth/refresh` | ❌（refresh token） | 刷新 token |
| POST | `/api/auth/logout` | ✅ | 登出 |
| POST | `/api/detect` | ✅ | 语言检测 |
| POST | `/api/translate/text` | ✅ | 文本翻译 |
| POST | `/api/file/check` | ✅ | 秒传校验 |
| POST | `/api/file/chunk` | ✅ | 上传分片 |
| POST | `/api/file/merge` | ✅ | 合并分片 |
| POST | `/api/translate/file` | ✅ | 提交文件翻译 |
| GET | `/api/translate/status/{task_id}` | ✅ | 轮询翻译状态 |
| POST | `/api/translate/cancel/{task_id}` | ✅ | 取消文件翻译 |
| GET | `/api/translate/download/{file_id}` | ✅ | 鉴权下载 |
| GET | `/api/history` | ✅ | 历史列表 |
| GET | `/api/history/{id}` | ✅ | 历史详情 |
| DELETE | `/api/history/{id}` | ✅ | 删除历史 |
| GET | `/health` | ❌ | 健康检查 |

---

## 十二、默认决策（v1）

| # | 默认决策 | 影响模块 |
|---|---|---|
| 1 | MedDRA 术语库采用本地数据库表维护，独立版本化更新，不依赖在线公共 API | terminology_agent |
| 2 | LLM 使用通义千问免费模型（dashscope 兼容 OpenAI），代码保留 provider 适配层便于后续切换 | translator_agent |
| 3 | 双语对照版左右并排且保留原页码/目录；超长时优先缩放字体与留白，不直接改页码 | file_translate_task |
| 4 | 文本和文件翻译历史统一保留 30 天；每日定时清理，同时支持用户手动删除 | 存储成本 |
| 5 | Celery worker 默认并发 2~4；v1 不引入优先级队列，文本翻译继续走同步接口 | 任务调度 |
| 6 | 默认主登录方式为邮箱 + 密码；飞书 SSO 采用飞书开放平台 Web 应用 OAuth2 Authorization Code 模式作为可选登录方式 | auth_service |
| 7 | 文件上传不支持断点续传；页面刷新后需重新上传 | 上传性能 |
| 8 | 文件翻译仅支持 `.docx` 和 `.pdf`；扫描版/图片版 PDF 不做 OCR，尽早返回错误 | 文件处理 |
| 9 | 文件翻译统一输出 PDF；下载仅保留纯译文 PDF，双语对照仅用于页面预览 | 结果展示 |
| 10 | 首批支持语种为 zh/en/ja/ko/de/fr；自动检测到不支持语种时禁止提交 | 语言配置 |
| 11 | 同一用户同一时间只允许 1 个文件翻译任务；文件翻译期间仍允许文本翻译和查看其他历史 | 任务并发 |
