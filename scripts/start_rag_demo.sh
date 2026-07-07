#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RESET=$'\033[0m'
BOLD=$'\033[1m'
CYAN=$'\033[36m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
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

link() {
  local url="$1"
  local label="$2"
  printf '\033]8;;%s\033\\%s\033]8;;\033\\' "$url" "$label"
}

require_bin() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "Required command not found: $name"
    exit 1
  fi
}

compose_up() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --profile opik up -d
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose --profile opik up -d
    return
  fi
  fail "Neither 'docker compose' nor 'docker-compose' is available"
  exit 1
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  local sleep_sec="${4:-2}"
  local i=1
  while (( i <= attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      ok "$label is ready"
      return 0
    fi
    sleep "$sleep_sec"
    ((i++))
  done
  fail "$label did not become ready: $url"
  return 1
}

if [[ ! -f .env ]]; then
  fail ".env not found in $ROOT_DIR"
  exit 1
fi

require_bin curl
require_bin jq
require_bin python3
require_bin deck
require_bin docker

set -a
source .env
set +a

KONG_ADMIN_ADDR="${KONG_ADMIN_ADDR:-http://localhost:8001}"
KONG_WORKSPACE="${KONG_WORKSPACE:-AIDemo}"
KONG_PROXY_URL="${KONG_PROXY_URL:-http://localhost:8000}"

echo
echo "${CYAN}========================================${RESET}"
echo "${BOLD}${GREEN}    Demo Startup (Kong Enterprise)${RESET}"
echo "${CYAN}========================================${RESET}"

step "Starting docker containers"
compose_up
ok "Containers started"

step "Waiting for core demo services"
wait_for_http "http://localhost:18080/health" "orchestrator"
wait_for_http "http://localhost:18081/health" "support-agent"
wait_for_http "http://localhost:18082/health" "success-agent"
wait_for_http "http://localhost:18083/health" "mock-api"
wait_for_http "http://localhost:3000" "ui"

step "Applying Kong config to Enterprise workspace"
./scripts/apply_enterprise_workspace.sh

step "Validating Kong-routed UI"
wait_for_http "${KONG_PROXY_URL}/" "kong ui route"

step "Optional RAG ingest for local kong-dp container"
if docker ps --format '{{.Names}}' | grep -q '^kong-dp$'; then
  python3 scripts/ingest_rag_kb.py
  ok "RAG knowledge base ingested"
else
  info "Skipping ingest (container 'kong-dp' is not running)"
fi

echo
echo "${CYAN}========================================${RESET}"
echo "${BOLD}${GREEN}        Demo Startup Complete${RESET}"
echo "${CYAN}========================================${RESET}"
echo
echo "${BOLD}URLs:${RESET}"
printf "  ${CYAN}UI (via Kong)${RESET}  %s\n" "$(link "${KONG_PROXY_URL}" "${KONG_PROXY_URL}")"
printf "  ${CYAN}UI (direct)${RESET}    %s\n" "$(link "http://localhost:3000" "http://localhost:3000")"
printf "  ${CYAN}Grafana${RESET}  %s\n" "$(link "http://localhost:3001" "http://localhost:3001")"
printf "  ${CYAN}Opik${RESET}     %s\n" "$(link "http://localhost:5173" "http://localhost:5173")"
printf "  ${CYAN}Jaeger${RESET}   %s\n" "$(link "http://localhost:16686" "http://localhost:16686")"
echo
echo "${BOLD}Kong Enterprise Target:${RESET}"
printf "  ${CYAN}Admin API${RESET}  %s\n" "${KONG_ADMIN_ADDR}"
printf "  ${CYAN}Workspace${RESET}  %s\n" "${KONG_WORKSPACE}"
echo
