#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Stopping local stack and removing Opik volumes..."
docker compose --profile opik down -v

echo "RAG demo stack stopped."
