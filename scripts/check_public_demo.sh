#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

check_env_file() {
  [[ -f .env ]] || fail ".env not found. Copy .env.example to .env and fill public demo values."
}

check_required_env() {
  local missing=0
  local key
  for key in PUBLIC_WEB_HOST PUBLIC_API_HOST PUBLIC_API_URL APP_SECRET FIELD_ENCRYPTION_KEY MODEL_GATEWAY_API_KEY; do
    if ! grep -Eq "^${key}=.+" .env; then
      printf 'Missing required .env key: %s\n' "$key" >&2
      missing=1
    fi
  done
  [[ "$missing" -eq 0 ]] || fail "Required public demo env vars are missing."
}

check_no_tracked_secrets() {
  if git grep -n "MODEL_GATEWAY_API_KEY=.*[A-Za-z0-9]\\{20,\\}" -- . ':!.env' ':!.env.example' >/tmp/campus_secret_scan.txt; then
    cat /tmp/campus_secret_scan.txt >&2
    fail "Potential tracked model API key found."
  fi
  if git grep -n "2Y73" -- . ':!.env' >/tmp/campus_stepfun_scan.txt; then
    cat /tmp/campus_stepfun_scan.txt >&2
    fail "Real StepFun key appears in tracked files."
  fi
}

check_compose() {
  have docker || fail "docker command not found."
  docker compose -f compose.yaml -f compose.public-demo.yaml config >/tmp/campus_public_compose.yaml
}

check_env_file
check_required_env
check_no_tracked_secrets
check_compose

printf 'Public demo configuration check passed.\n'
printf 'Next: docker compose -f compose.yaml -f compose.public-demo.yaml up -d --build\n'
