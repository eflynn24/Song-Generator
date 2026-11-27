#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODEL="${1:-$(docker compose config --environment | sed -n 's/^OLLAMA_MODEL=//p')}"
MODEL="${MODEL:-llama3.2}"
if [[ -z "$(docker compose ps ollama --status running --quiet)" ]]; then
  docker compose up -d --no-deps ollama
fi

for ((attempt = 1; attempt <= 60; attempt++)); do
  if docker compose exec -T ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Pulling model: $MODEL"
docker compose exec -T ollama ollama pull "$MODEL"

