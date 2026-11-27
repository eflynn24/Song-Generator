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

if [[ ! -f .env ]]; then
  echo "Run ./install.sh first to create the private account bootstrap password." >&2
  exit 1
fi

docker compose up -d

echo
echo "Song Generator is running:"
echo "  Application: http://localhost:5173"
echo "  API docs:    http://localhost:8000/docs"
if docker compose ps --services --status running | rg -q '^public-tunnel$'; then
  echo "  Public HTTPS: $(./public-url.sh 2>/dev/null || echo 'starting; run ./public-url.sh shortly')"
fi
echo
echo "Continue as guest for a temporary session, or sign in/create an account"
echo "to keep songs in a persistent library. Guest data is erased when you end"
echo "the session or after 20 minutes of inactivity."
echo "Describe a song, choose vocals/instruments, and generate. ACE-Step uses its"
echo "default song length. You can optionally add an MP3 reference."
echo "View logs with: docker compose logs -f"
echo "Stop containers with: docker compose down"
echo "The public tunnel uses a new HTTPS address after each restart."

