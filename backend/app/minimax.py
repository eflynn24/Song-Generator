import asyncio
import re
import shutil
import uuid
from pathlib import Path

import httpx

from .audio import INSTRUMENT_DETAIL, VOCAL_PRESETS
from .schemas import SongRequest
from .settings import MINIMAX_OUTPUT_DIR, MINIMAX_URL


SECTION_WITH_DIRECTION = re.compile(
    r"^(?P<indent>[^\S\r\n]*)\["
    r"(?P<section>(?:intro|verse|pre[- ]chorus|chorus|post[- ]chorus|bridge|hook|refrain|outro"
    r"|instrumental(?: break)?|breakdown|final chorus|solo|interlude)(?:[ \t]+\d+)?)"
    r"[ \t]*(?:[-–—:][ \t]*(?P<direction>[^\]\r\n]+)|\((?P<parenthetical>[^\]\r\n]+)\))?[ \t]*\]"
    r"(?=[ \t]*\r?$)",
    re.IGNORECASE | re.MULTILINE,
)


def _arrange_supplied_lyrics(lyrics: str, preset: str) -> str:
    sections = list(SECTION_WITH_DIRECTION.finditer(lyrics))
    if not sections:
        return (
            "Start with a clear lead and minimal accompaniment. Gradually add rhythmic support and "
            "instrumental answers in vocal gaps. Bring back the opening motif to close."
        )

    chorus_count = sum(
        re.sub(r"\s+\d+$", "", section["section"].lower()) in {"chorus", "final chorus", "hook", "refrain"}
        for section in sections
    )
    chorus = verse = 0
    timeline = []
    for section in sections:
        label = section["section"]
        kind = re.sub(r"\s+\d+$", "", label.lower()).replace(" ", "-")
        if kind == "verse":
            verse += 1
            direction = (
                "Expose the lead over a sparse version of the central groove."
                if verse == 1 else
                "Return to the verse groove with one added texture and short fills between vocal lines."
            )
        elif kind in {"chorus", "final-chorus", "hook", "refrain"}:
            chorus += 1
            direction = (
                "Open the arrangement around the hook with fuller rhythm and a wider stereo texture."
                if chorus == 1 else
                "Keep the familiar hook melody and groove. Add one layer for a stronger lift."
            )
            if preset == "harmonies" or chorus == chorus_count:
                direction += " Blend quiet harmonies behind the lead on the existing hook words and line endings."
        else:
            direction = {
                "intro": "Introduce the main instrumental motif and establish the pulse.",
                "pre-chorus": "Build tension with a gradual rhythmic lift and leave space before the hook.",
                "post-chorus": "Let the instrumental motif answer the hook while keeping the pulse.",
                "bridge": "Thin the rhythm and shift the texture for contrast before returning to the main groove.",
                "outro": "Resolve the main motif and let the instruments decay together.",
            }.get(kind, "Give one instrument the foreground and keep the other parts in support.")
        note = (section["direction"] or section["parenthetical"] or "").strip()
        performance = f" Performance cue: {note[:120]}." if note else ""
        timeline.append(f"{label}: {direction}{performance}")
    if len(timeline) > 12:
        timeline = timeline[:6] + ["Middle sections: follow the lyric order and develop the established groove."] + timeline[-6:]
    return "\n".join(timeline)


def build_workflow(request: SongRequest, lyrics: str, seed: int, prefix: str) -> dict:
    instruments = ", ".join(
        f"{name} with {INSTRUMENT_DETAIL[name]}" if name in INSTRUMENT_DETAIL else name
        for name in request.instruments
    )
    genre = ", ".join(request.genres) or request.genre
    metadata = ", ".join(part for part in (
        genre, request.mood, request.key_scale,
        f"{request.bpm} BPM" if request.bpm is not None else "",
        f"{request.time_signature}/{8 if request.time_signature == '6' else 4} meter"
        if request.time_signature else "",
    ) if part)
    vocal = ", ".join(part for part in (
        request.vocal_style,
        VOCAL_PRESETS[request.vocal_preset],
        f"{request.vocal_language} vocals" if request.vocal_language != "unknown" else "",
    ) if part) if request.vocals else "Instrumental, without sung or spoken vocals."
    caption = (
        f"Global Metadata: {metadata or 'Follow the arrangement description.'}\n"
        f"Vocal Details: {vocal}\n"
        f"Arrangement: {request.prompt}"
    )
    if instruments:
        caption += f"\nFeatured instruments: {instruments}."
    if request.vocals and request.lyrics.strip():
        caption += (
            "\nKeep a consistent lead voice, groove, and instrumental palette. Center the lead, "
            "keep accompaniment below it during sung phrases, and let fills answer in the gaps. "
            "Give bass and percussion complementary roles and use a shared subtle room sound. "
            "Use only the supplied words for lead and backing parts. Explicit directions in the "
            "brief and performance cues take priority over the suggested arrangement.\n"
            + _arrange_supplied_lyrics(lyrics, request.vocal_preset)
        )

    return {
        "clip": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors",
            "type": "minimax",
            "device": "default",
        }},
        "encode": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
            "clip": ["clip", 0], "caption": caption,
            "lyrics": SECTION_WITH_DIRECTION.sub(r"\g<indent>[\g<section>]", lyrics)
            if request.vocals else "[Instrumental]",
            "seed": seed, "max_duration": request.duration_seconds,
            "cfg_scale": 1.7, "top_k": 50,
        }},
        "model": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_music3_dit_int8_convrot.safetensors", "weight_dtype": "default",
        }},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_music3_dav.safetensors"}},
        "negative": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["encode", 0]}},
        "latent": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {
            "seconds": ["encode", 1], "batch_size": 1,
        }},
        "sample": {"class_type": "KSampler", "inputs": {
            "model": ["model", 0], "positive": ["encode", 0], "negative": ["negative", 0],
            "latent_image": ["latent", 0], "seed": seed, "steps": 30, "cfg": 1.7,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
        }},
        "decode": {"class_type": "VAEDecodeAudioTiled", "inputs": {
            "samples": ["sample", 0], "vae": ["vae", 0], "tile_size": 1536, "overlap": 64,
        }},
        "save": {"class_type": "SaveAudio", "inputs": {"audio": ["decode", 0], "filename_prefix": prefix}},
    }


async def generate_minimax_audio(request: SongRequest, lyrics: str, output_dir: Path, seed: int | None = None) -> Path:
    prefix = uuid.uuid4().hex
    graph = build_workflow(request, lyrics, seed if seed is not None else uuid.uuid4().int % 2**31, prefix)
    async with httpx.AsyncClient(base_url=MINIMAX_URL, timeout=15) as client:
        response = await client.post("/prompt", json={"prompt": graph})
        if response.is_error:
            raise RuntimeError(f"MiniMax rejected the workflow: {response.text[:700]}")
        prompt_id = response.json()["prompt_id"]
        try:
            async with asyncio.timeout(1800):
                while True:
                    history = (await client.get(f"/history/{prompt_id}")).raise_for_status().json()
                    if result := history.get(prompt_id):
                        break
                    await asyncio.sleep(1)

            if result["status"]["status_str"] != "success":
                errors = [
                    detail.get("exception_message", "")
                    for event, detail in result["status"].get("messages", [])
                    if event == "execution_error"
                ]
                raise RuntimeError(f"MiniMax generation failed. {' '.join(errors)[:400]}".strip())

            audio = result["outputs"]["save"]["audio"][0]
            name = audio["filename"]
            if Path(name).name != name or not name.startswith(prefix + "_") or audio.get("subfolder"):
                raise RuntimeError("MiniMax returned an unexpected output file.")
            path = output_dir / "minimax.flac"
            await asyncio.to_thread(shutil.move, MINIMAX_OUTPUT_DIR / name, path)
            return path
        except TimeoutError:
            (await client.post("/interrupt", json={"prompt_id": prompt_id})).raise_for_status()
            raise TimeoutError("MiniMax did not finish within the generation timeout.") from None
        finally:
            # Keep loaded weights available for the next song. ComfyUI can
            # offload them when the GPU needs room for ACE-Step or another job.
            try:
                await client.post("/free", json={"free_memory": True})
            except httpx.HTTPError:
                # The result may already be saved when the worker stops.
                pass
