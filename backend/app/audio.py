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


GENRE_SOUND = {
    "Rock": "rock, overdriven electric-guitar riffs, electric bass, live drum kit, strong backbeat",
    "Blues": "blues, expressive bent-note electric guitar, blues-rock shuffle feel, electric bass, live drums",
    "Pop": "pop, clear melodic hook, polished production, tight drums, warm bass",
    "Hip-hop / rap": "hip-hop, beat-led groove, punchy drums, deep bass, rhythmic vocal phrasing",
    "R&B / soul": "R&B and soul, warm bass, rich chords, expressive vocals, relaxed pocket",
    "Country": "country, acoustic and electric guitar, steady live drums, warm bass, story-led vocals",
    "Jazz": "jazz, rich harmony, nimble bass, live drums, expressive instrumental interplay",
    "Electronic / EDM": "electronic dance music, precise beat, layered synths, strong bass pulse, rising build",
    "Indie / alternative": "indie alternative, distinctive guitar textures, dynamic live band, expressive vocals",
    "Folk / acoustic": "folk, acoustic strings, intimate vocals, natural dynamics, light percussion",
    "Metal": "metal, heavy distorted guitar riffs, forceful drums, powerful bass, dramatic dynamics",
    "Reggae": "reggae, offbeat guitar or keyboard chops, relaxed one-drop groove, rounded bass",
    "Funk / disco": "funk and disco, syncopated bass, tight drums, bright rhythmic accents, dance groove",
    "Classical / cinematic": "cinematic orchestral music, evolving motifs, strings, broad dynamics, emotional arc",
    "Latin": "Latin music, syncopated percussion, danceable pulse, warm bass, bright rhythmic accents",
}

VOCAL_PRESETS = {
    "auto": "",
    "natural": (
        "single dry close-miked lead, conversational verse phrasing, audible breaths at phrase breaks, "
        "gentle pitch variation on held notes, open unforced chorus, sparse backing"
    ),
    "clear": "focused pop lead, articulate consonants, centered dry vocal, restrained vibrato",
    "intimate": "close-miked soft lead, warm tone, gentle dynamics, minimal room sound",
    "soul": "warm soul lead, expressive dynamics, controlled vibrato and brief melodic runs",
    "rock": "forward rock lead, controlled rasp, strong sustained notes, clear consonants",
    "harmonies": "single clear lead in verses, tight backing harmonies on chorus lyrics",
}

INSTRUMENT_DETAIL = {
    "guitar": "defined string attack",
    "piano": "varied key dynamics",
    "bass": "defined bass note decay",
    "drums": "crisp drum transients",
    "saxophone": "audible reed articulation",
    "strings": "natural bow articulation",
}


def _trim_caption_part(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    shortened = value[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return shortened or value[:limit]


def _music_caption(request: SongRequest, vocal_direction: str) -> str:
    selected_genres = list(dict.fromkeys(request.genres)) or (
        [request.genre.strip()] if request.genre.strip() else []
    )
    profiles = [GENRE_SOUND[genre] for genre in selected_genres if genre in GENRE_SOUND]
    if len(selected_genres) == 2 and set(selected_genres) == {"Rock", "Blues"}:
        style = (
            "blues-rock (rock + blues), expressive electric guitar with bent blues notes, "
            "memorable guitar riffs, electric bass, live drums, strong backbeat"
        )
    elif profiles:
        style = "; ".join(profiles)
        if len(style) > 160:
            style = ", ".join(selected_genres)
    elif selected_genres:
        style = ", ".join(selected_genres)
    else:
        style = ""

    details = []
    if request.mood.strip():
        details.append(f"{request.mood.strip()} mood")
    if request.instruments:
        details.append(f"feature {', '.join(request.instruments)}")
    if request.bpm is not None:
        details.append(f"{request.bpm} BPM")
    details.extend(INSTRUMENT_DETAIL[name] for name in request.instruments if name in INSTRUMENT_DETAIL)
    # Reserve room for vocal direction and the song idea, even with many genres.
    style_budget = min(185, 512 - len(vocal_direction) - 64 - 6)
    style = _trim_caption_part(style, style_budget)
    sound_budget = min(100, max(0, 512 - len(style) - len(vocal_direction) - 64 - 6))
    sound = _trim_caption_part(", ".join(details), sound_budget)
    fixed = [part for part in (style, sound, vocal_direction) if part]
    idea = _trim_caption_part(request.prompt, 512 - sum(len(part) + 2 for part in fixed))
    return ". ".join(part for part in (style, idea, sound, vocal_direction) if part)


def build_music_form(
    request: SongRequest, lyrics: str, seed: int
) -> dict[str, str]:
    if request.vocals:
        vocals = ", ".join(part for part in (
            request.vocal_style.strip(),
            VOCAL_PRESETS[request.vocal_preset],
            "clear lead vocal, sing the supplied lyrics",
        ) if part)
    else:
        vocals = "instrumental only, no vocals"
    caption = _music_caption(request, vocals)
    model, inference_steps, guidance_scale = ACE_STEP_MODELS[request.generation_model]
    if request.generation_model in {"turbo-lite", "turbo", "turbo-shift1", "turbo-shift3", "xl-turbo"}:
        inference_steps = request.inference_steps
    lyrics_input = (
        lyrics if request.vocals else
        lyrics.strip() or "[Instrumental]"
    )
    use_planner = request.generation_model != "turbo-lite"
    explicit_vocal = request.vocals and (
        request.vocal_preset != "auto" or bool(request.vocal_style.strip())
    )
    data = {
        "prompt": caption,
        "lyrics": lyrics_input,
        "vocal_language": request.vocal_language,
        "audio_format": "wav32" if request.studio_master else "wav",
        "task_type": "cover" if request.reference_audio_id else "text2music",
        # LM planning can improve composition and instrumental structure too.
        # ACE-Step skips this pass automatically for cover tasks.
        "thinking": "true" if (
            request.music_planner
            and use_planner
            and not request.reference_audio_id
        ) else "false",
        "use_format": "false",
        "use_cot_caption": "true" if (
            use_planner and request.enhance_prompt and not request.genres and not explicit_vocal
        ) else "false",
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
    if request.generation_model in {"turbo-lite", "turbo", "xl-turbo", "turbo-shift3"}:
        # ACE-Step's inference guide recommends shift=3 for Turbo checkpoints.
        data["shift"] = "3.0"
    elif request.generation_model in {"turbo-shift1", "sft", "xl-sft"}:
        data["shift"] = "1.0"
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
                await asyncio.sleep(0.75)
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
    studio_master: bool = False,
    sample_rate: int = 48000,
) -> tuple[Path, Path]:
    wav_path = GENERATED_DIR / f"{job_id}.wav"
    mp3_name = f"{job_id}.mp3" if variation == 1 else f"{job_id}-variation-{variation}.mp3"
    mp3_path = GENERATED_DIR / mp3_name
    # The reference conditions model generation; it must not be overlaid on
    # the generated track, which would make it sound like a second playback.
    filters = []
    if studio_master:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    elif normalize_audio:
        filters.append("loudnorm=I=-16:TP=-1.0:LRA=11")
    if fade_in:
        filters.append("afade=t=in:st=0:d=2")
    if fade_out:
        filters.append(f"afade=t=out:st={max(0, duration_seconds - 3)}:d=3")
    command = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(generated_path)]
    mp3_input = "0:a:0"
    if variation == 1:
        wav_input = "0:a:0"
        if filters:
            command.extend([
                "-filter_complex", f"[0:a:0]{','.join(filters)},asplit=2[wav][mp3]",
            ])
            wav_input, mp3_input = "[wav]", "[mp3]"
        command.extend([
            "-map", wav_input, "-ar", str(sample_rate),
            "-codec:a", "pcm_s24le" if studio_master else "pcm_s16le", str(wav_path),
        ])
    elif filters:
        command.extend(["-af", ",".join(filters)])
    command.extend([
        "-map", mp3_input, "-ar", str(sample_rate), "-codec:a", "libmp3lame",
        "-b:a", "320k" if studio_master else "192k", str(mp3_path),
    ])
    subprocess.run(command, check=True)
    return wav_path, mp3_path
