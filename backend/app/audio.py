import asyncio
import json
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin

import httpx

from .schemas import SongRequest
from .settings import (
    ACE_STEP_MODELS,
    GENERATED_DIR,
    MUSIC_API_URL,
)


def build_music_form(
    request: SongRequest, lyrics: str, seed: int
) -> dict[str, str]:
    if request.vocals:
        style = f"{request.vocal_style}, " if request.vocal_style.strip() else ""
        vocals = (
            f"{style}natural, expressive lead singing with clear consonants, "
            "steady pitch, varied melodic phrasing; sing the supplied lyrics"
        )
    else:
        vocals = "instrumental only, no vocals"
    details = []
    if request.genre.strip():
        details.append(f"Target genre: {request.genre}.")
    if request.mood.strip():
        details.append(f"Mood: {request.mood}.")
    if request.instruments:
        details.append(f"Featuring {', '.join(request.instruments)}.")
    caption = f"Create music matching this description: {request.prompt}. " + " ".join(details + [vocals])
    model, inference_steps, guidance_scale = ACE_STEP_MODELS[request.generation_model]
    if request.generation_model in {"turbo", "turbo-shift1", "turbo-shift3", "xl-turbo"}:
        inference_steps = request.inference_steps
    lyrics_input = (
        lyrics if request.vocals else
        lyrics.strip() or "[Instrumental]"
    )
    data = {
        "prompt": caption,
        "lyrics": lyrics_input,
        "vocal_language": request.vocal_language,
        "audio_format": "wav",
        "task_type": "cover" if request.reference_audio_id else "text2music",
        # LM planning can improve composition and instrumental structure too.
        # ACE-Step skips this pass automatically for cover tasks.
        "thinking": "true" if request.music_planner and not request.reference_audio_id else "false",
        "use_format": "false",
        "use_cot_caption": "true" if request.enhance_prompt else "false",
        "use_cot_language": "true" if request.vocal_language == "unknown" and request.vocals else "false",
        "lm_temperature": str(request.lm_temperature),
        "lm_cfg_scale": str(request.lm_cfg_scale),
        "lm_negative_prompt": request.avoid.strip() or "NO USER INPUT",
        "inference_steps": str(inference_steps),
        "seed": str(seed),
        "use_random_seed": "false",
        "batch_size": "1",
        "model": model,
    }
    if request.key_scale:
        data["key_scale"] = request.key_scale
    if request.time_signature:
        data["time_signature"] = request.time_signature
    if guidance_scale is not None:
        data["guidance_scale"] = str(guidance_scale)
    if request.reference_audio_id:
        data["audio_cover_strength"] = str(request.reference_strength)
    data["audio_duration"] = str(request.duration_seconds)
    if request.bpm is not None:
        data["bpm"] = str(request.bpm)
    return data


async def generate_audio(
    request: SongRequest, lyrics: str, output_dir: Path, reference_audio: Path | None
) -> Path:
    data = build_music_form(request, lyrics, uuid.uuid4().int % 2**31)
    files = None
    source = None
    try:
        if reference_audio is not None:
            clipped_reference = output_dir / "reference.mp3"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error", "-i",
                    str(reference_audio), "-t", str(request.duration_seconds), "-vn", "-codec:a",
                    "libmp3lame", "-q:a", "2", str(clipped_reference),
                ],
                check=True,
            )
            source = clipped_reference.open("rb")
            files = {
                "src_audio": (
                    clipped_reference.name,
                    source,
                    "audio/mpeg",
                )
            }
        async with httpx.AsyncClient(timeout=1200) as client:
            await _ensure_model_loaded(client, data["model"])
            response = await client.post(
                f"{MUSIC_API_URL}/release_task", data=data, files=files
            )
            response.raise_for_status()
            task_id = response.json()["data"]["task_id"]
            deadline = time.monotonic() + 1100
            while time.monotonic() < deadline:
                result_response = await client.post(
                    f"{MUSIC_API_URL}/query_result",
                    json={"task_id_list": [task_id]},
                )
                result_response.raise_for_status()
                task = result_response.json()["data"][0]
                if task["status"] == 2:
                    raise RuntimeError(task.get("error") or "ACE-Step generation failed.")
                if task["status"] == 1:
                    items = json.loads(task.get("result") or "[]")
                    if not items or not items[0].get("file"):
                        raise RuntimeError("ACE-Step returned no generated audio file.")
                    audio_url = urljoin(
                        f"{MUSIC_API_URL}/", items[0]["file"].lstrip("/")
                    )
                    audio_response = await client.get(audio_url)
                    audio_response.raise_for_status()
                    output = output_dir / "generated.wav"
                    output.write_bytes(audio_response.content)
                    return output
                await asyncio.sleep(2)
        raise TimeoutError("ACE-Step did not finish within the generation timeout.")
    finally:
        if source is not None:
            source.close()


async def _ensure_model_loaded(client: httpx.AsyncClient, model: str) -> None:
    inventory_response = await client.get(f"{MUSIC_API_URL}/v1/model_inventory")
    inventory_response.raise_for_status()
    inventory = inventory_response.json().get("data", {})
    model_entry = next(
        (item for item in inventory.get("models", []) if item.get("name") == model),
        None,
    )
    if model_entry and model_entry.get("is_loaded"):
        return

    init_response = await client.post(
        f"{MUSIC_API_URL}/v1/init", json={"model": model, "slot": 1}
    )
    init_response.raise_for_status()
    result = init_response.json()
    if result.get("error"):
        raise RuntimeError(f"Could not load ACE-Step model '{model}': {result['error']}")
    loaded_model = result.get("data", {}).get("loaded_model")
    if loaded_model and loaded_model != model:
        raise RuntimeError(
            f"ACE-Step loaded '{loaded_model}' instead of requested model '{model}'."
        )


def finalize_audio(
    job_id: str,
    generated_path: Path,
    _reference_path: Path | None = None,
    _volume: float = 0.0,
    *,
    variation: int = 1,
    fade_in: bool = False,
    fade_out: bool = False,
    duration_seconds: int = 30,
    normalize_audio: bool = False,
) -> tuple[Path, Path]:
    wav_path = GENERATED_DIR / f"{job_id}.wav"
    mp3_name = f"{job_id}.mp3" if variation == 1 else f"{job_id}-variation-{variation}.mp3"
    mp3_path = GENERATED_DIR / mp3_name
    # The reference conditions model generation; it must not be overlaid on
    # the generated track, which would make it sound like a second playback.
    filters = []
    if normalize_audio:
        filters.append("loudnorm=I=-16:TP=-1.0:LRA=11")
    if fade_in:
        filters.append("afade=t=in:st=0:d=2")
    if fade_out:
        filters.append(f"afade=t=out:st={max(0, duration_seconds - 3)}:d=3")
    if variation == 1:
        command = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(generated_path)]
        if filters:
            command.extend(["-af", ",".join(filters)])
        command.append(str(wav_path))
        subprocess.run(command, check=True)
        mp3_source = wav_path
    else:
        mp3_source = generated_path
        if filters:
            mp3_source = generated_path.with_name(f"variation-{variation}-faded.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(generated_path), "-af", ",".join(filters), str(mp3_source)],
                check=True,
            )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_source),
            "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path),
        ],
        check=True,
    )
    return wav_path, mp3_path
