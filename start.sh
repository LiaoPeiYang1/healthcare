#!/usr/bin/env bash
# 启动前后端开发环境
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[start]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
error() { echo -e "${RED}[error]${NC} $*"; exit 1; }

cleanup() {
  log "正在停止所有服务..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  log "已停止。"
}

# ── 后端 ────────────────────────────────────────────────────────────────
log "启动后端 (FastAPI / uvicorn)..."
cd "$BACKEND_DIR"

if [[ ! -d ".venv" ]]; then
  warn "未找到 .venv，正在创建虚拟环境..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# 安装依赖（仅当 egg-info 不存在时）
if [[ ! -d "medical_translate_backend.egg-info" ]]; then
  log "安装 Python 依赖..."
  pip install -e ".[dev]" --quiet
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
log "后端 PID: $BACKEND_PID  →  http://localhost:8000"

# ── 前端 ────────────────────────────────────────────────────────────────
log "启动前端 (Vite)..."
cd "$FRONTEND_DIR"

if [[ ! -d "node_modules" ]]; then
  log "安装 Node 依赖..."
  npm install
fi

npm run dev &
FRONTEND_PID=$!
log "前端 PID: $FRONTEND_PID  →  http://localhost:5173"

# ── 等待退出信号 ──────────────────────────────────────────────────────────
trap cleanup SIGINT SIGTERM
log "按 Ctrl+C 停止所有服务。"
wait
