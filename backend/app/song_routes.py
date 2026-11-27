import asyncio
import json
import logging
import secrets
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import media, storage
from .audio import finalize_audio, generate_audio
from .auth_routes import require_ready_user
from .lyrics import generate_lyrics
from .minimax import generate_minimax_audio
from .yue2 import generate_yue2_audio
from .schemas import Job, SongRequest
from .settings import GENERATED_DIR, OLLAMA_MODEL, OLLAMA_URL, UPLOAD_DIR


router = APIRouter(prefix="/api", tags=["songs"])
logger = logging.getLogger(__name__)
generation_lock = asyncio.Semaphore(1)


def _user_id(user: dict[str, object]) -> str:
    return str(user["id"])


def _job_from_row(row: dict[str, object]) -> Job:
    song_id = str(row["id"])
    completed = row["status"] == "completed"
    request_data = json.loads(str(row["request_json"]))
    request_data["reference_audio_id"] = None
    return Job.model_validate(
        {
            "id": song_id,
            "status": row["status"],
            "title": row["title"],
            "lyrics": row["lyrics"],
            "audio_url": f"/api/jobs/{song_id}/mp3" if completed else None,
            "wav_url": f"/api/jobs/{song_id}/wav" if completed else None,
            "mp3_url": f"/api/jobs/{song_id}/mp3" if completed else None,
            "error": row["error"],
            "request": request_data,
            "created_at": row["created_at"],
        }
    )


async def _generate_song(
    user_id: str, song_id: str, request: SongRequest
) -> None:
    reference = None
    if request.reference_audio_id:
        try:
            reference = media.reference_path(user_id, request.reference_audio_id)
        except HTTPException as exc:
            storage.update_song(
                user_id, song_id, status="failed", title=None, lyrics=None, error=str(exc.detail)
            )
            return
    try:
        async with generation_lock:
            title, lyrics = await generate_lyrics(request, OLLAMA_URL, OLLAMA_MODEL)
            storage.update_song(
                user_id, song_id, status="generating", title=title, lyrics=lyrics, error=None
            )
            uses_minimax = request.generation_model == "minimax-music3"
            with tempfile.TemporaryDirectory(dir=GENERATED_DIR) as temporary_dir:
                for variation in range(1, request.variation_count + 1):
                    direction = request.variation_prompts[variation - 1].strip() if len(request.variation_prompts) >= variation else ""
                    variation_request = request.model_copy(update={
                        "prompt": f"{request.prompt.strip()}\nVariation {variation} direction: {direction}"[:2000] if direction else request.prompt,
                    })
                    seed = request.variation_seeds[variation - 1]
                    if uses_minimax:
                        generated = await generate_minimax_audio(variation_request, lyrics, Path(temporary_dir), seed)
                    elif request.generation_model == "yue2":
                        generated = await generate_yue2_audio(variation_request, lyrics, Path(temporary_dir), seed)
                    else:
                        generated = await generate_audio(variation_request, lyrics, Path(temporary_dir), reference, seed)
                    await asyncio.to_thread(
                        finalize_audio,
                        song_id,
                        generated,
                        variation=variation,
                        fade_in=request.fade_in,
                        fade_out=request.fade_out,
                        duration_seconds=request.duration_seconds,
                        normalize_audio=request.normalize_audio,
                        studio_master=request.studio_master,
                        sample_rate=32000 if uses_minimax else 48000,
                    )
            if storage.get_song(user_id, song_id) is None:
                media.delete_song_files([song_id])
                return
            storage.update_song(
                user_id,
                song_id,
                status="completed",
                title=title,
                lyrics=lyrics,
                error=None,
            )
    except Exception as exc:
        logger.exception("Song generation failed for song %s", song_id)
        media.delete_song_files([song_id])
        storage.update_song(
            user_id,
            song_id,
            status="failed",
            title=locals().get("title"),
            lyrics=locals().get("lyrics"),
            error=str(exc),
        )
    finally:
        if request.reference_audio_id:
            (UPLOAD_DIR / f"{user_id}-{request.reference_audio_id}.mp3").unlink(
                missing_ok=True
            )


@router.post("/uploads/reference", status_code=201)
async def upload_reference(
    file: UploadFile = File(...),
    user: dict[str, object] = Depends(require_ready_user),
) -> dict[str, str]:
    upload_id = await media.save_reference_upload(_user_id(user), file)
    return {"id": upload_id, "filename": file.filename or "reference.mp3"}


@router.post("/jobs", response_model=Job, status_code=202)
def create_job(
    request: SongRequest,
    background_tasks: BackgroundTasks,
    user: dict[str, object] = Depends(require_ready_user),
) -> Job:
    if request.generation_model == "minimax-music3" and request.reference_audio_id:
        raise HTTPException(status_code=422, detail="MiniMax Music 3 uses text and lyrics. Choose ACE-Step for MP3 references.")
    song_id = str(uuid.uuid4())
    if any(len(direction) > 500 for direction in request.variation_prompts):
        raise HTTPException(status_code=422, detail="Variation directions must be at most 500 characters.")
    seeds = [secrets.randbelow(2**31) for _ in range(request.variation_count)]
    while len(set(seeds)) != len(seeds):
        seeds = [secrets.randbelow(2**31) for _ in range(request.variation_count)]
    request = request.model_copy(update={"variation_seeds": seeds})
    user_id = _user_id(user)
    stored_request = request.model_copy(update={"reference_audio_id": None})
    storage.create_song(user_id, song_id, request.model_dump_json(), status="queued")
    background_tasks.add_task(_generate_song, user_id, song_id, request)
    return Job(
        id=song_id,
        status="queued",
        request=stored_request,
        created_at=storage.get_song(user_id, song_id)["created_at"],
    )


@router.get("/songs", response_model=list[Job])
def list_library(
    user: dict[str, object] = Depends(require_ready_user),
) -> list[Job]:
    return [_job_from_row(row) for row in storage.list_songs(_user_id(user))]


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(
    job_id: str, user: dict[str, object] = Depends(require_ready_user)
) -> Job:
    song = storage.get_song(_user_id(user), job_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found.")
    return _job_from_row(song)


@router.get("/jobs/{job_id}/{format}")
def get_audio(
    job_id: str,
    format: str,
    variation: int = 1,
    user: dict[str, object] = Depends(require_ready_user),
) -> FileResponse:
    if format not in {"mp3", "wav"}:
        raise HTTPException(status_code=404, detail="Audio format not found.")
    if storage.get_song(_user_id(user), job_id) is None:
        raise HTTPException(status_code=404, detail="Song not found.")
    song = storage.get_song(_user_id(user), job_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found.")
    request_data = json.loads(str(song["request_json"]))
    if variation < 1 or variation > int(request_data.get("variation_count", 1)):
        raise HTTPException(status_code=404, detail="Song variation not found.")
    suffix = f"-variation-{variation}" if format == "mp3" and variation > 1 else ""
    path = GENERATED_DIR / f"{job_id}{suffix}.{format}"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found.")
    media_type = "audio/mpeg" if format == "mp3" else "audio/wav"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.delete("/songs/{song_id}", status_code=204)
def delete_song(
    song_id: str, user: dict[str, object] = Depends(require_ready_user)
) -> None:
    if not storage.delete_song(_user_id(user), song_id):
        raise HTTPException(status_code=404, detail="Song not found.")
    media.delete_song_files([song_id])
