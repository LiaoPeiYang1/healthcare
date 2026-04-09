#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
RUN_DIR="${ROOT_DIR}/.run"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5175}"

mkdir -p "${RUN_DIR}"

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

find_free_port() {
  local preferred_port="$1"
  local port="${preferred_port}"
  while lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo "${port}"
}

wait_for_service_ready() {
  local name="$1"
  local pid="$2"
  local port="$3"
  local log_file="$4"
  local retries=30
  local delay=0.2

  for _ in $(seq 1 "${retries}"); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      echo "${name} exited unexpectedly. Check log: ${log_file}" >&2
      return 1
    fi
    if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "${name} did not become ready on port ${port}. Check log: ${log_file}" >&2
  return 1
}

stop_pid_file_process() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    return
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    sleep 0.3
  fi
  rm -f "${pid_file}"
}

require_command lsof
require_command npm

if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
  echo "Backend virtualenv not found: ${BACKEND_DIR}/.venv/bin/python" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  echo "Frontend dependencies not found. Please run: cd frontend && npm install" >&2
  exit 1
fi

stop_pid_file_process "${RUN_DIR}/backend.pid"
stop_pid_file_process "${RUN_DIR}/frontend.pid"

BACKEND_PORT="$(find_free_port "${BACKEND_PORT}")"
FRONTEND_PORT="$(find_free_port "${FRONTEND_PORT}")"

(
  cd "${BACKEND_DIR}"
  nohup .venv/bin/python -m uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" \
    >"${RUN_DIR}/backend.log" 2>&1 &
  echo $! >"${RUN_DIR}/backend.pid"
)

if ! wait_for_service_ready "Backend" "$(cat "${RUN_DIR}/backend.pid")" "${BACKEND_PORT}" "${RUN_DIR}/backend.log"; then
  stop_pid_file_process "${RUN_DIR}/backend.pid"
  exit 1
fi

(
  cd "${FRONTEND_DIR}"
  nohup env VITE_API_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}" \
    npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" \
    >"${RUN_DIR}/frontend.log" 2>&1 &
  echo $! >"${RUN_DIR}/frontend.pid"
)

if ! wait_for_service_ready "Frontend" "$(cat "${RUN_DIR}/frontend.pid")" "${FRONTEND_PORT}" "${RUN_DIR}/frontend.log"; then
  stop_pid_file_process "${RUN_DIR}/frontend.pid"
  stop_pid_file_process "${RUN_DIR}/backend.pid"
  exit 1
fi

cat >"${RUN_DIR}/env.sh" <<EOF
export BACKEND_HOST="${BACKEND_HOST}"
export BACKEND_PORT="${BACKEND_PORT}"
export FRONTEND_HOST="${FRONTEND_HOST}"
export FRONTEND_PORT="${FRONTEND_PORT}"
EOF

echo "Services started."
echo "Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "Health:   http://${BACKEND_HOST}:${BACKEND_PORT}/health"
echo "PIDs:     backend=$(cat "${RUN_DIR}/backend.pid"), frontend=$(cat "${RUN_DIR}/frontend.pid")"
echo "Logs:     ${RUN_DIR}/backend.log, ${RUN_DIR}/frontend.log"
