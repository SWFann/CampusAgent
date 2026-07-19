#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_PORT="${WEB_PORT:-3000}"
API_PORT="${API_PORT:-8000}"
WEB_PORT_EXPLICIT=0
API_PORT_EXPLICIT=0
MODE="auto"
INSTALL_DEPS=1
SEED_DEMO=1
RUN_SMOKE=0

usage() {
  cat <<'EOF'
CampusAgent one-click starter

Usage:
  ./scripts/start.sh [options]

Options:
  --mode auto|docker|sqlite   Runtime mode. Default: auto.
  --web-port PORT             Web port. Default: 3000.
  --api-port PORT             API port. Default: 8000.
  --no-install                Skip dependency installation.
  --no-seed                   Skip demo seed/reset.
  --smoke                     Run demo smoke test and exit.
  -h, --help                  Show this help.

Examples:
  ./scripts/start.sh
  ./scripts/start.sh --mode sqlite
  ./scripts/start.sh --smoke
EOF
}

log() {
  printf '\033[0;34m[CampusAgent]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[CampusAgent]\033[0m %s\n' "$*"
}

fail() {
  printf '\033[0;31m[CampusAgent]\033[0m %s\n' "$*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

port_in_use() {
  local port="$1"
  if have ss; then
    ss -ltn "( sport = :$port )" | tail -n +2 | grep -q .
  elif have lsof; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

find_free_port() {
  local port="$1"
  local avoid="${2:-}"
  while port_in_use "$port" || [[ -n "$avoid" && "$port" == "$avoid" ]]; do
    port=$((port + 1))
  done
  printf '%s\n' "$port"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        MODE="${2:-}"
        shift 2
        ;;
      --web-port)
        WEB_PORT="${2:-}"
        WEB_PORT_EXPLICIT=1
        shift 2
        ;;
      --api-port)
        API_PORT="${2:-}"
        API_PORT_EXPLICIT=1
        shift 2
        ;;
      --no-install)
        INSTALL_DEPS=0
        shift
        ;;
      --no-seed)
        SEED_DEMO=0
        shift
        ;;
      --smoke)
        RUN_SMOKE=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
  done

  case "$MODE" in
    auto|docker|sqlite) ;;
    *) fail "--mode must be one of: auto, docker, sqlite" ;;
  esac
}

require_base_tools() {
  have conda || fail "Conda is required. Create/activate the CampusAgent env first."
  conda env list | awk '{print $1}' | grep -qx "CampusAgent" || fail "Conda env 'CampusAgent' was not found."
  have corepack || fail "corepack is required for pnpm. Install Node.js >= 18."
  have node || fail "Node.js is required."
  have git || fail "git is required."
}

choose_mode() {
  if [[ "$MODE" == "auto" ]]; then
    if have docker && docker compose version >/dev/null 2>&1; then
      MODE="docker"
    else
      MODE="sqlite"
    fi
  fi

  if [[ "$MODE" == "docker" ]] && ! { have docker && docker compose version >/dev/null 2>&1; }; then
    fail "Docker mode requested, but 'docker compose' is unavailable. Install Docker or run --mode sqlite."
  fi
}

prepare_env() {
  cd "$ROOT_DIR"
  [[ -f .env ]] || cp .env.example .env
  while IFS='=' read -r key value || [[ -n "$key" ]]; do
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ -z "$key" || "$key" == \#* ]] && continue
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "$key=$value"
  done < .env

  mkdir -p "$ROOT_DIR/.local"

  export APP_ENV="${APP_ENV:-development}"
  export APP_DEBUG="${APP_DEBUG:-false}"
  export APP_SECRET="${APP_SECRET:-dev-secret-key-change-in-production}"
  export FIELD_ENCRYPTION_KEY="${FIELD_ENCRYPTION_KEY:-dev-encryption-key-change-in-production}"
  export MODEL_GATEWAY_API_KEY
  export MODEL_GATEWAY_MODEL="${MODEL_GATEWAY_MODEL:-step-3.7-flash}"
  export MODEL_GATEWAY_TIMEOUT_MS="${MODEL_GATEWAY_TIMEOUT_MS:-60000}"
  export MODEL_GATEWAY_IS_EXTERNAL="${MODEL_GATEWAY_IS_EXTERNAL:-true}"
  export ENABLE_EXTERNAL_MODEL="${ENABLE_EXTERNAL_MODEL:-false}"
  export NEXT_PUBLIC_API_URL="http://localhost:${API_PORT}"

  if [[ "$MODE" == "docker" ]]; then
    export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/campus_agent}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
    export MODEL_GATEWAY_BASE_URL="${MODEL_GATEWAY_BASE_URL:-http://localhost:8001}"
  else
    export DATABASE_URL="sqlite:///$ROOT_DIR/.local/campus_agent.dev.db"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/1}"
    export MODEL_GATEWAY_BASE_URL="${MODEL_GATEWAY_BASE_URL:-http://localhost:8001}"
  fi
}

install_deps() {
  if [[ "$INSTALL_DEPS" -eq 0 ]]; then
    return
  fi
  log "Installing dependencies if needed..."
  corepack pnpm install --frozen-lockfile
  conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
}

start_dependencies() {
  if [[ "$MODE" == "docker" ]]; then
    log "Starting Docker dependencies: postgres, redis, mock-model..."
    docker compose up -d postgres redis mock-model
  else
    warn "Docker is unavailable or disabled. Using SQLite fallback."
    warn "Redis/model health may show degraded, but the website and API can start."
  fi
}

tcp_open() {
  local host="$1"
  local port="$2"
  timeout 1 bash -c ":</dev/tcp/${host}/${port}" >/dev/null 2>&1
}

container_ip() {
  local name="$1"
  docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$name" 2>/dev/null
}

refresh_docker_runtime_env() {
  if [[ "$MODE" != "docker" ]]; then
    return
  fi

  local postgres_host="localhost"
  local redis_host="localhost"
  local model_host="localhost"

  if ! tcp_open localhost 5432; then
    postgres_host="$(container_ip campus-agent-postgres)"
    [[ -n "$postgres_host" ]] || fail "PostgreSQL container IP not found."
    warn "localhost:5432 is not reachable from WSL. Using PostgreSQL container IP ${postgres_host}."
  fi

  if ! tcp_open localhost 6379; then
    redis_host="$(container_ip campus-agent-redis)"
    [[ -n "$redis_host" ]] || fail "Redis container IP not found."
    warn "localhost:6379 is not reachable from WSL. Using Redis container IP ${redis_host}."
  fi

  if ! tcp_open localhost 8001; then
    model_host="$(container_ip campus-agent-mock-model)"
    [[ -n "$model_host" ]] || warn "Mock model container IP not found; keeping configured model URL."
  fi

  export DATABASE_URL="postgresql://postgres:postgres@${postgres_host}:5432/campus_agent"
  export REDIS_URL="redis://${redis_host}:6379/0"
  if [[ "${ENABLE_EXTERNAL_MODEL}" != "true" && -n "$model_host" ]]; then
    export MODEL_GATEWAY_BASE_URL="http://${model_host}:8001"
  fi
}

run_migrations() {
  if [[ "$MODE" == "docker" ]]; then
    log "Waiting for PostgreSQL to be ready..."
    local waited=0
    while ! DATABASE_URL="$DATABASE_URL" conda run -n CampusAgent python - <<'PY' >/dev/null 2>&1
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("select 1"))
PY
    do
      if (( waited >= 30 )); then
        fail "PostgreSQL did not become ready within 30s"
      fi
      sleep 1
      (( waited++ ))
    done
    log "PostgreSQL is ready (waited ${waited}s)"
  fi

  log "Running database migrations..."
  (
    cd "$ROOT_DIR/apps/api"
    conda run -n CampusAgent alembic -c alembic.ini upgrade head
  )
}

seed_demo() {
  if [[ "$SEED_DEMO" -eq 0 ]]; then
    return
  fi
  log "Seeding demo data..."
  conda run -n CampusAgent python scripts/demo/seed_demo.py --json
}

run_smoke() {
  log "Running demo smoke test..."
  conda run -n CampusAgent python scripts/demo/run_demo_smoke.py
}

check_ports() {
  if port_in_use "$API_PORT"; then
    if [[ "$API_PORT_EXPLICIT" -eq 1 ]]; then
      fail "API port $API_PORT is already in use. Pass --api-port PORT."
    fi
    local next_api_port
    if [[ "$MODE" == "docker" ]]; then
      next_api_port="$(find_free_port "$API_PORT" 8001)"
    else
      next_api_port="$(find_free_port "$API_PORT")"
    fi
    warn "API port $API_PORT is already in use. Using $next_api_port instead."
    API_PORT="$next_api_port"
    export NEXT_PUBLIC_API_URL="http://localhost:${API_PORT}"
  fi
  if port_in_use "$WEB_PORT"; then
    if [[ "$WEB_PORT_EXPLICIT" -eq 1 ]]; then
      fail "Web port $WEB_PORT is already in use. Pass --web-port PORT."
    fi
    local next_web_port
    next_web_port="$(find_free_port "$WEB_PORT")"
    warn "Web port $WEB_PORT is already in use. Using $next_web_port instead."
    WEB_PORT="$next_web_port"
  fi
}

cleanup() {
  local code=$?
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WEB_PID:-}" ]] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  exit "$code"
}

start_servers() {
  trap cleanup INT TERM EXIT

  log "Starting API on http://localhost:${API_PORT}"
  (
    cd "$ROOT_DIR/apps/api"
    conda run -n CampusAgent uvicorn src.main:app --reload --port "$API_PORT"
  ) &
  API_PID=$!

  log "Starting Web on http://localhost:${WEB_PORT}"
  (
    cd "$ROOT_DIR/apps/web"
    NEXT_DIST_DIR=".next-${WEB_PORT}" NEXT_PUBLIC_API_URL="http://localhost:${API_PORT}" corepack pnpm dev --port "$WEB_PORT"
  ) &
  WEB_PID=$!

  cat <<EOF

CampusAgent is starting.

Web:      http://localhost:${WEB_PORT}
API:      http://localhost:${API_PORT}
API Docs: http://localhost:${API_PORT}/docs

Demo accounts:
  demo_admin@example.com
  demo_alice@example.com
  demo_bob@example.com
  demo_carol@example.com

Demo password:
  CampusAgentDemo2026!

Press Ctrl+C to stop both servers.
EOF

  wait "$API_PID" "$WEB_PID"
}

main() {
  parse_args "$@"
  cd "$ROOT_DIR"
  require_base_tools
  choose_mode
  prepare_env
  check_ports

  if [[ "$RUN_SMOKE" -eq 1 ]]; then
    install_deps
    run_smoke
    exit 0
  fi

  install_deps
  start_dependencies
  refresh_docker_runtime_env
  run_migrations
  seed_demo
  start_servers
}

main "$@"
