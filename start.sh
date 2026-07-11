#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/astock_trader"
FRONTEND_DIR="$ROOT_DIR/astock_trader_react/frontend"
ENV_FILE="$BACKEND_DIR/.env"
BACKEND_LOG="$BACKEND_DIR/api.log"
FRONTEND_LOG="$ROOT_DIR/astock_trader_react/frontend.log"
MODE="${1:-start}"

info() { printf '[ashare] %s\n' "$1"; }
fail() { printf '[ashare] 错误: %s\n' "$1" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

find_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    command_exists "$PYTHON_BIN" || fail "找不到 PYTHON_BIN=$PYTHON_BIN"
    printf '%s' "$PYTHON_BIN"
  elif command_exists python3.12; then
    printf '%s' python3.12
  elif command_exists python3; then
    python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' \
      || fail "需要 Python 3.12+；可通过 PYTHON_BIN 指定解释器"
    printf '%s' python3
  else
    fail "需要 Python 3.12+"
  fi
}

check_tools() {
  PYTHON="$(find_python)"
  command_exists node || fail "需要 Node.js 20+"
  command_exists npm || fail "需要 npm"
  command_exists curl || fail "需要 curl"
  node -e 'process.exit(Number(process.versions.node.split(".")[0]) < 20 ? 1 : 0)' \
    || fail "需要 Node.js 20+"
  info "Python: $($PYTHON --version 2>&1)"
  info "Node: $(node --version)"
  info "npm: $(npm --version)"
}

create_env() {
  if [ -f "$ENV_FILE" ]; then
    grep -q '^APP_PASSWORD=.' "$ENV_FILE" \
      || fail "$ENV_FILE 已存在，但 APP_PASSWORD 为空"
    return
  fi
  PASSWORD="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(24))')"
  umask 077
  {
    printf 'APP_PASSWORD=%s\n' "$PASSWORD"
    printf 'SESSION_TTL_SECONDS=28800\n'
    printf 'API_HOST=127.0.0.1\n'
    printf 'API_PORT=8000\n'
    printf 'CORS_ORIGINS=http://127.0.0.1:8888,http://localhost:8888\n'
  } > "$ENV_FILE"
  info "已创建 $ENV_FILE"
  info "首次登录密码: $PASSWORD"
  info "请立即保存该密码；也可以稍后编辑 .env 更换"
}

prepare_dependencies() {
  if [ ! -x "$BACKEND_DIR/venv/bin/python" ]; then
    info "创建 Python 虚拟环境"
    "$PYTHON" -m venv "$BACKEND_DIR/venv"
  fi
  if ! "$BACKEND_DIR/venv/bin/python" -c 'import fastapi, uvicorn, pandas, akshare' >/dev/null 2>&1; then
    info "安装后端依赖"
    "$BACKEND_DIR/venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
  fi
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "安装前端依赖"
    (cd "$FRONTEND_DIR" && npm ci)
  fi
}

if [ "$MODE" != "start" ] && [ "$MODE" != "--check" ] && [ "$MODE" != "--setup-only" ]; then
  fail "用法: ./start.sh [--check|--setup-only]"
fi

check_tools
if [ "$MODE" = "--check" ]; then
  [ -f "$ENV_FILE" ] && info ".env: 已配置" || info ".env: 尚未创建"
  [ -x "$BACKEND_DIR/venv/bin/python" ] && info "后端虚拟环境: 就绪" || info "后端虚拟环境: 尚未创建"
  [ -d "$FRONTEND_DIR/node_modules" ] && info "前端依赖: 就绪" || info "前端依赖: 尚未安装"
  exit 0
fi

create_env
prepare_dependencies
if [ "$MODE" = "--setup-only" ]; then
  info "初始化完成；运行 ./start.sh 启动系统"
  exit 0
fi

BACKEND_PID=''
FRONTEND_PID=''
cleanup() {
  trap - INT TERM EXIT
  info "正在停止服务"
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

info "启动后端，日志: $BACKEND_LOG"
(cd "$BACKEND_DIR" && ./venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000) \
  > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

READY=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then READY=1; break; fi
  kill -0 "$BACKEND_PID" 2>/dev/null || fail "后端启动失败，请查看 $BACKEND_LOG"
  sleep 1
done
[ "$READY" -eq 1 ] || fail "后端健康检查超时，请查看 $BACKEND_LOG"

info "启动前端，日志: $FRONTEND_LOG"
(cd "$FRONTEND_DIR" && npm run dev -- --host 127.0.0.1 --port 8888) \
  > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

READY=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8888 >/dev/null 2>&1; then READY=1; break; fi
  kill -0 "$FRONTEND_PID" 2>/dev/null || fail "前端启动失败，请查看 $FRONTEND_LOG"
  sleep 1
done
[ "$READY" -eq 1 ] || fail "前端就绪检查超时，请查看 $FRONTEND_LOG"

info "系统已启动: http://127.0.0.1:8888"
info "按 Ctrl+C 停止前后端"
wait "$BACKEND_PID" "$FRONTEND_PID"
