#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RESET=$'\033[0m'
BOLD=$'\033[1m'
CYAN=$'\033[36m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'

link() {
  local url="$1"
  local label="$2"
  printf '\033]8;;%s\033\\%s\033]8;;\033\\' "$url" "$label"
}

if [[ ! -f .env ]]; then
  echo ".env not found in $ROOT_DIR" >&2
  exit 1
fi

set -a
source .env
set +a

if [[ -z "${KONNECT_TOKEN:-}" || -z "${KONNECT_CONTROL_PLANE_NAME:-}" ]]; then
  echo "KONNECT_TOKEN or KONNECT_CONTROL_PLANE_NAME is not set in .env" >&2
  exit 1
fi

echo "Starting local stack with Opik..."
docker compose --profile opik up -d --build 

echo "Syncing Kong config..."
deck gateway sync \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$KONNECT_CONTROL_PLANE_NAME" \
  kong/deck/kong.yaml



echo "Ingesting fictional AtlasFlow support KB..."
python3 scripts/ingest_rag_kb.py

echo
echo "${CYAN}========================================${RESET}"
echo "${BOLD}${GREEN}        RAG Demo Startup Complete${RESET}"
echo "${CYAN}========================================${RESET}"
echo
echo "${BOLD}Open:${RESET}"
printf "  ${GREEN}UI${RESET}       %s\n" "$(link "http://localhost:8000" "http://localhost:8000")"
printf "  ${YELLOW}Grafana${RESET}  %s\n" "$(link "http://localhost:3001" "http://localhost:3001")"
printf "  ${CYAN}Opik${RESET}     %s\n" "$(link "http://localhost:5173" "http://localhost:5173")"
echo
