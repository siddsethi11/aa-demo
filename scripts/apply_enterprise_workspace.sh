#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RESET=$'\033[0m'
BOLD=$'\033[1m'
CYAN=$'\033[36m'
GREEN=$'\033[32m'
RED=$'\033[31m'
BLUE=$'\033[34m'

step() {
  local label="$1"
  printf "\n${BLUE}${BOLD}[%s]${RESET} %s\n" "$(date +%H:%M:%S)" "$label"
}

ok() {
  local message="$1"
  printf "${GREEN}  ✓${RESET} %s\n" "$message"
}

info() {
  local message="$1"
  printf "${CYAN}  •${RESET} %s\n" "$message"
}

fail() {
  local message="$1"
  printf "${RED}  ✗${RESET} %s\n" "$message" >&2
}

require_bin() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "Required command not found: $name"
    exit 1
  fi
}

if [[ ! -f .env ]]; then
  fail ".env not found in $ROOT_DIR"
  exit 1
fi

require_bin curl
require_bin jq
require_bin deck

set -a
source .env
set +a

KONG_ADMIN_ADDR="${KONG_ADMIN_ADDR:-http://localhost:8001}"
KONG_ADMIN_TOKEN="${KONG_ADMIN_TOKEN:-kong_admin_password}"
KONG_WORKSPACE="${KONG_WORKSPACE:-AIDemo}"
DECK_REDIS_HOST="${DECK_REDIS_HOST:-redis-stack}"
DECK_OTEL_TRACES_ENDPOINT="${DECK_OTEL_TRACES_ENDPOINT:-http://otel-collector:4318/v1/traces}"
DECK_LOKI_HTTP_ENDPOINT="${DECK_LOKI_HTTP_ENDPOINT:-http://loki:3100/loki/api/v1/push}"
DECK_OPIK_API_BASE_URL="${DECK_OPIK_API_BASE_URL:-http://opik-frontend:5173/api/v1/private}"
DECK_UI_SERVICE_URL="${DECK_UI_SERVICE_URL:-http://ui:80}"
DECK_ORCHESTRATOR_SERVICE_URL="${DECK_ORCHESTRATOR_SERVICE_URL:-http://orchestrator:8000}"
DECK_SUPPORT_AGENT_SERVICE_URL="${DECK_SUPPORT_AGENT_SERVICE_URL:-http://support-agent:8000}"
DECK_SUCCESS_AGENT_SERVICE_URL="${DECK_SUCCESS_AGENT_SERVICE_URL:-http://success-agent:8000}"
DECK_MOCK_API_SERVICE_URL="${DECK_MOCK_API_SERVICE_URL:-http://mock-api:8000}"
DECK_AI_PII_HOST="${DECK_AI_PII_HOST:-ai-pii-service}"
DECK_AI_PII_PORT="${DECK_AI_PII_PORT:-8080}"

export DECK_REDIS_HOST DECK_OTEL_TRACES_ENDPOINT DECK_LOKI_HTTP_ENDPOINT DECK_OPIK_API_BASE_URL
export DECK_UI_SERVICE_URL DECK_ORCHESTRATOR_SERVICE_URL DECK_SUPPORT_AGENT_SERVICE_URL
export DECK_SUCCESS_AGENT_SERVICE_URL DECK_MOCK_API_SERVICE_URL DECK_AI_PII_HOST DECK_AI_PII_PORT

echo
echo "${CYAN}========================================${RESET}"
echo "${BOLD}${GREEN}   Kong Enterprise Workspace Apply${RESET}"
echo "${CYAN}========================================${RESET}"

step "Ensuring workspace '${KONG_WORKSPACE}' exists"
http_code="$(curl -sS -o /tmp/kong_workspace_get.json -w "%{http_code}" \
  -H "Kong-Admin-Token: ${KONG_ADMIN_TOKEN}" \
  "${KONG_ADMIN_ADDR}/workspaces/${KONG_WORKSPACE}")"

case "$http_code" in
  200)
    ok "Workspace '${KONG_WORKSPACE}' already exists"
    ;;
  404)
    info "Workspace '${KONG_WORKSPACE}' not found; creating it"
    create_code="$(curl -sS -o /tmp/kong_workspace_create.json -w "%{http_code}" \
      -X POST \
      -H "Kong-Admin-Token: ${KONG_ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"${KONG_WORKSPACE}\"}" \
      "${KONG_ADMIN_ADDR}/workspaces")"
    if [[ "$create_code" != "201" && "$create_code" != "409" ]]; then
      fail "Failed to create workspace '${KONG_WORKSPACE}' (HTTP ${create_code})"
      cat /tmp/kong_workspace_create.json >&2 || true
      exit 1
    fi
    ok "Workspace '${KONG_WORKSPACE}' created"
    ;;
  *)
    fail "Failed to read workspace '${KONG_WORKSPACE}' (HTTP ${http_code})"
    cat /tmp/kong_workspace_get.json >&2 || true
    exit 1
    ;;
esac

step "Applying Kong config to workspace '${KONG_WORKSPACE}'"
deck gateway apply \
  -w "${KONG_WORKSPACE}" \
  --headers "Kong-Admin-Token:${KONG_ADMIN_TOKEN}" \
  --kong-addr "${KONG_ADMIN_ADDR}" \
  kong/deck/kong.yaml
ok "decK apply complete"

echo
echo "${BOLD}Applied To:${RESET}"
printf "  ${CYAN}Admin API${RESET}  %s\n" "${KONG_ADMIN_ADDR}"
printf "  ${CYAN}Workspace${RESET}  %s\n" "${KONG_WORKSPACE}"
echo
