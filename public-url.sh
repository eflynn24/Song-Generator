#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
url="$(docker compose --profile public logs --no-color public-tunnel 2>&1 | sed -nE 's@.*(https://[a-z-]+\.trycloudflare\.com).*@\1@p' | tail -1)"
if [[ -z "$url" ]]; then
  echo "Public tunnel URL is not ready. Start it with: docker compose --profile public up -d public-tunnel" >&2
  exit 1
fi
echo "$url"
