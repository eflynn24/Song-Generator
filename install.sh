#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop with WSL integration or Docker Engine with Compose." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is required. Install the Docker Compose plugin, then retry." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "The Docker daemon is unavailable. Start Docker and retry." >&2
  exit 1
fi

if ! docker info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
  echo "The ACE-Step service requires the NVIDIA Container Toolkit runtime." >&2
  echo "Configure NVIDIA GPU support for Docker, then retry." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

if [[ -z "${OLLAMA_MODEL:-}" && -f .env ]]; then
  OLLAMA_MODEL="$(sed -nE 's/^[[:space:]]*OLLAMA_MODEL[[:space:]]*=[[:space:]]*([^[:space:]#]+).*/\1/p' .env | tail -n 1)"
  OLLAMA_MODEL="${OLLAMA_MODEL%\"}"
  OLLAMA_MODEL="${OLLAMA_MODEL#\"}"
  OLLAMA_MODEL="${OLLAMA_MODEL%\'}"
  OLLAMA_MODEL="${OLLAMA_MODEL#\'}"
fi
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"

wait_for_service() {
  local name="$1"
  shift

  for ((attempt = 1; attempt <= 300; attempt++)); do
    if "$@" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  echo "$name did not become ready. Check its logs with: docker compose logs $name" >&2
  return 1
}

echo "Starting Ollama and downloading model: $OLLAMA_MODEL"
docker compose up -d ollama
wait_for_service ollama docker compose exec -T ollama ollama list
docker compose exec -T ollama ollama pull "$OLLAMA_MODEL"

echo "Building and starting the application containers..."
docker compose up -d --build

echo "Waiting for the ACE-Step service to finish starting..."
wait_for_service ace-step docker compose exec -T ace-step python3 -c \
  'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)'

echo "Downloading and initializing the default ACE-Step checkpoint..."
docker compose exec -T ace-step python3 -c \
  'import runpy; runpy.run_path("/app/infer-wrapper.py")["get_pipeline"]()'

docker compose down

echo "Installation complete. Start the application with ./run.sh"
