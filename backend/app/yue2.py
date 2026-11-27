import shutil
import uuid
from pathlib import Path

import httpx

from .schemas import SongRequest
from .settings import YUE2_URL


def build_yue2_request(request: SongRequest, lyrics: str, seed: int) -> dict[str, object]:
    genres = ", ".join(request.genres) or request.genre
    style = ", ".join(part for part in (
        request.vocal_language if request.vocals else "instrumental",
        genres,
        request.mood,
        request.prompt,
        f"{request.bpm} BPM" if request.bpm else "",
        request.key_scale,
        f"Featuring {', '.join(request.instruments)}" if request.instruments else "",
        request.vocal_style,
    ) if part)
    return {"style": style[:2000], "lyrics": lyrics if request.vocals else "[Instrumental]", "seed": seed}


async def generate_yue2_audio(request: SongRequest, lyrics: str, output_dir: Path) -> Path:
    payload = build_yue2_request(request, lyrics, uuid.uuid4().int % (2**31))
    async with httpx.AsyncClient(timeout=3600) as client:
        response = await client.post(f"{YUE2_URL}/generate", json=payload)
        if response.is_error:
            detail = response.json().get("error", response.text)
            raise RuntimeError(f"YuE2 generation failed: {str(detail)[:700]}")
        source = Path(response.json()["path"])
        if source.name != "audio.flac" or not source.is_file():
            raise RuntimeError("YuE2 returned an unexpected audio file.")
        target = output_dir / "yue2.flac"
        await __import__("asyncio").to_thread(shutil.copyfile, source, target)
        return target
