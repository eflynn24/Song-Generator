import fcntl
import json
import os
from pathlib import Path

from acestep.model_downloader import (
    MAIN_MODEL_COMPONENTS,
    check_model_exists,
    download_main_model,
    download_submodel,
    download_vae,
)


CHECKPOINTS = Path("/app/checkpoints")


def model_is_ready(name: str) -> bool:
    directory = CHECKPOINTS / name
    if not (directory / "config.json").is_file() or not check_model_exists(name, CHECKPOINTS):
        return False
    for index in directory.glob("*.safetensors.index.json"):
        try:
            files = set(json.loads(index.read_text())["weight_map"].values())
        except (ValueError, KeyError, AttributeError):
            return False
        if not files or any(not (directory / file).is_file() for file in files):
            return False
    return True


def prefetch() -> None:
    if not all(map(model_is_ready, MAIN_MODEL_COMPONENTS)):
        ok, message = download_main_model(CHECKPOINTS, force=True, prefer_source="huggingface")
        if not ok:
            raise RuntimeError(message)

    models = dict.fromkeys([
        *MAIN_MODEL_COMPONENTS,
        os.environ["ACESTEP_CONFIG_PATH"],
        os.environ["ACESTEP_LM_MODEL_PATH"],
        "acestep-v15-turbo-shift1",
        "acestep-v15-turbo-shift3",
        "acestep-v15-sft",
        "acestep-v15-xl-turbo",
        os.environ["ACE_STEP_QUALITY_MODEL"],
    ])
    for name in models:
        if not model_is_ready(name) and name not in MAIN_MODEL_COMPONENTS:
            ok, message = download_submodel(name, CHECKPOINTS, force=True, prefer_source="huggingface")
            if not ok:
                raise RuntimeError(message)
        if not model_is_ready(name):
            raise RuntimeError(f"Checkpoint is incomplete: {name}")
        print(f"Ready: {name}", flush=True)

    vae_variant = os.getenv("ACESTEP_VAE_CHECKPOINT", "official")
    if vae_variant != "official":
        if not model_is_ready(vae_variant):
            ok, message = download_vae(vae_variant, CHECKPOINTS, force=True, prefer_source="huggingface")
            if not ok:
                raise RuntimeError(message)
        if not model_is_ready(vae_variant):
            raise RuntimeError(f"Decoder checkpoint is incomplete: {vae_variant}")
        print(f"Ready: {vae_variant}", flush=True)


if __name__ == "__main__":
    with (CHECKPOINTS / ".prefetch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prefetch()
