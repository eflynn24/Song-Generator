#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
umask 077

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

write_default_user_password() {
  local password="$1"
  if grep -q '^DEFAULT_USER_PASSWORD=' .env; then
    sed -i "s/^DEFAULT_USER_PASSWORD=.*/DEFAULT_USER_PASSWORD=$password/" .env
  else
    printf '\nDEFAULT_USER_PASSWORD=%s\n' "$password" >> .env
  fi
}

DEFAULT_USER_PASSWORD="${DEFAULT_USER_PASSWORD:-$(sed -nE 's/^DEFAULT_USER_PASSWORD=(.*)$/\1/p' .env | tail -n 1 | tr -d '\r')}"
GENERATED_BOOTSTRAP_PASSWORD=false
if [[ ! "$DEFAULT_USER_PASSWORD" =~ ^[A-Za-z0-9_-]{24,}$ ]]; then
  DEFAULT_USER_PASSWORD="$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  write_default_user_password "$DEFAULT_USER_PASSWORD"
  GENERATED_BOOTSTRAP_PASSWORD=true
else
  write_default_user_password "$DEFAULT_USER_PASSWORD"
fi
BOOTSTRAP_PASSWORD="$DEFAULT_USER_PASSWORD"
unset DEFAULT_USER_PASSWORD
chmod 600 .env

if [[ "$GENERATED_BOOTSTRAP_PASSWORD" == true ]]; then
  echo "Default account: user"
  echo "Temporary password (change it at first login): $BOOTSTRAP_PASSWORD"
fi
unset BOOTSTRAP_PASSWORD

./pull.sh

echo "Building the application containers..."
docker compose build

echo "Installation complete. Start the application with ./run.sh"
