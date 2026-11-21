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

docker compose up -d

echo
echo "Song Generator is running:"
echo "  Application: http://localhost:5173"
echo "  API docs:    http://localhost:8000/docs"
echo
echo "Use the application page to generate and download songs."
echo "View logs with: docker compose logs -f"
echo "Stop containers with: docker compose down"

