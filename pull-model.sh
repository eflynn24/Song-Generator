#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-llama3.2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! docker compose ps ollama --status running --format json 2>/dev/null | grep -q '"running"'; then
  docker compose up -d ollama
fi

echo "Pulling model: $MODEL"
docker compose exec ollama ollama pull "$MODEL"

