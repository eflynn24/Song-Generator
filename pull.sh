#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

docker compose pull ace-step ollama

quality_model="$(docker compose config --environment | sed -n 's/^ACE_STEP_QUALITY_MODEL=//p')"
docker compose run --rm --no-deps -T \
  -e "ACE_STEP_QUALITY_MODEL=${quality_model:-acestep-v15-xl-sft}" \
  --entrypoint /app/.venv/bin/python ace-step -u - < ace-step/prefetch.py

./pull-model.sh

if [[ "${1:-}" == "--minimax" ]] || docker compose config --services | grep -qx minimax; then
  docker compose --profile minimax build minimax
  docker compose --profile minimax run --rm --no-deps -T \
    -e HF_HUB_OFFLINE=0 --entrypoint /app/.venv/bin/hf minimax \
    download Comfy-Org/MiniMax-Music-3 \
    diffusion_models/minimax_music3_dit_int8_convrot.safetensors \
    text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors \
    vae/minimax_music3_dav.safetensors \
    --revision 9e364ccd290a401561091fb441ed19cd7de92550 --local-dir /opt/comfy/models
fi
