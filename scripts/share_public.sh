#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
SHARE_WEB_PORT="${SHARE_WEB_PORT:-3100}"
PROXY_PORT="${PROXY_PORT:-8787}"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-}"

usage() {
  cat <<'EOF'
CampusAgent public sharing tunnel

Usage:
  ./scripts/share_public.sh [options]

Options:
  --api-port PORT        Local API port. Default: 8000.
  --web-port PORT        Internal share web port. Default: 3100.
  --proxy-port PORT      Internal proxy port. Default: 8787.
  -h, --help             Show this help.

Before running:
  1. Start CampusAgent locally:
     ./scripts/start.sh --mode docker

  2. Then run this script in another terminal:
     ./scripts/share_public.sh

Keep this terminal open while classmates are using the public URL.
EOF
}

log() {
  printf '\033[0;34m[CampusAgent Share]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[CampusAgent Share]\033[0m %s\n' "$*"
}

fail() {
  printf '\033[0;31m[CampusAgent Share]\033[0m %s\n' "$*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --api-port)
        API_PORT="${2:-}"
        shift 2
        ;;
      --web-port)
        SHARE_WEB_PORT="${2:-}"
        shift 2
        ;;
      --proxy-port)
        PROXY_PORT="${2:-}"
        shift 2
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

wait_for_http() {
  local url="$1"
  local name="$2"
  for _ in $(seq 1 40); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  fail "$name did not become ready: $url"
}

ensure_tools() {
  have node || fail "Node.js is required."
  have corepack || fail "corepack is required."
  have curl || fail "curl is required."
}

ensure_api_running() {
  local ready_url="http://127.0.0.1:${API_PORT}/health/ready"
  if ! curl -fsS "$ready_url" >/dev/null 2>&1; then
    fail "API is not ready on ${ready_url}. Start it first with: ./scripts/start.sh --mode docker"
  fi
}

ensure_cloudflared() {
  if [[ -n "$CLOUDFLARED_BIN" && -x "$CLOUDFLARED_BIN" ]]; then
    return 0
  fi
  if have cloudflared; then
    CLOUDFLARED_BIN="$(command -v cloudflared)"
    return 0
  fi

  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64)
      arch="amd64"
      ;;
    aarch64|arm64)
      arch="arm64"
      ;;
    *)
      fail "Unsupported CPU architecture for automatic cloudflared install: $arch"
      ;;
  esac

  mkdir -p "$ROOT_DIR/.local/bin"
  CLOUDFLARED_BIN="$ROOT_DIR/.local/bin/cloudflared"
  log "cloudflared not found. Downloading local binary to $CLOUDFLARED_BIN ..."
  curl -fL \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}" \
    -o "$CLOUDFLARED_BIN"
  chmod +x "$CLOUDFLARED_BIN"
}

cleanup() {
  local code=$?
  if [[ -n "${TUNNEL_PID:-}" ]] && kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    kill "$TUNNEL_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${PROXY_PID:-}" ]] && kill -0 "$PROXY_PID" >/dev/null 2>&1; then
    kill "$PROXY_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WEB_PID:-}" ]] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  exit "$code"
}

start_share_web() {
  if port_in_use "$SHARE_WEB_PORT"; then
    fail "Share web port ${SHARE_WEB_PORT} is already in use. Pass --web-port PORT."
  fi
  log "Starting share web on http://127.0.0.1:${SHARE_WEB_PORT} with same-origin API mode..."
  (
    cd "$ROOT_DIR/apps/web"
    NEXT_DIST_DIR=".next-share" NEXT_PUBLIC_API_URL="" corepack pnpm dev --port "$SHARE_WEB_PORT"
  ) &
  WEB_PID=$!
  wait_for_http "http://127.0.0.1:${SHARE_WEB_PORT}" "Share web"
}

start_proxy() {
  if port_in_use "$PROXY_PORT"; then
    fail "Proxy port ${PROXY_PORT} is already in use. Pass --proxy-port PORT."
  fi
  log "Starting local public proxy on http://127.0.0.1:${PROXY_PORT} ..."
  node "$ROOT_DIR/scripts/public_proxy.mjs" \
    --web "http://127.0.0.1:${SHARE_WEB_PORT}" \
    --api "http://127.0.0.1:${API_PORT}" \
    --port "$PROXY_PORT" &
  PROXY_PID=$!
  wait_for_http "http://127.0.0.1:${PROXY_PORT}" "Public proxy"
}

start_tunnel() {
  log "Starting Cloudflare Quick Tunnel..."
  cat <<EOF

When the tunnel is ready, copy the HTTPS URL that looks like:
  https://something.trycloudflare.com

Send that single URL to classmates. Keep this terminal open.

EOF
  "$CLOUDFLARED_BIN" tunnel --url "http://127.0.0.1:${PROXY_PORT}" &
  TUNNEL_PID=$!
  wait "$TUNNEL_PID"
}

main() {
  parse_args "$@"
  cd "$ROOT_DIR"
  trap cleanup INT TERM EXIT
  ensure_tools
  ensure_api_running
  ensure_cloudflared
  start_share_web
  start_proxy
  start_tunnel
}

main "$@"
