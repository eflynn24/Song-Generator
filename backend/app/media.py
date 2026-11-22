import subprocess
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .settings import GENERATED_DIR, MAX_REFERENCE_BYTES, UPLOAD_DIR


async def save_reference_upload(user_id: str, upload: UploadFile) -> str:
    upload_id = uuid.uuid4().hex
    path = UPLOAD_DIR / f"{user_id}-{upload_id}.mp3"
    size = 0
    try:
        with path.open("wb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_REFERENCE_BYTES:
                    raise HTTPException(413, "MP3 uploads must be 50 MB or smaller.")
                target.write(chunk)
        details = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=format_name,duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if not details or "mp3" not in details[0].split(","):
            raise HTTPException(415, "Upload a valid MP3 audio file.")
        duration = float(details[-1])
        if duration > 600:
            raise HTTPException(413, "Reference MP3s must be 10 minutes or shorter.")
        return upload_id
    except (subprocess.CalledProcessError, ValueError, OSError) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(415, "Upload a valid MP3 audio file.") from exc
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def reference_path(user_id: str, upload_id: str) -> Path:
    if len(upload_id) != 32 or any(char not in "0123456789abcdef" for char in upload_id):
        raise HTTPException(400, "Invalid reference upload.")
    path = UPLOAD_DIR / f"{user_id}-{upload_id}.mp3"
    if not path.is_file():
        raise HTTPException(404, "Reference upload has expired.")
    return path


def delete_song_files(song_ids: list[str]) -> None:
    for song_id in song_ids:
        for suffix in (".wav", ".mp3", ".reference.mp3"):
            (GENERATED_DIR / f"{song_id}{suffix}").unlink(missing_ok=True)
        for path in GENERATED_DIR.glob(f"{song_id}-variation-*.mp3"):
            path.unlink(missing_ok=True)


def delete_user_uploads(user_id: str) -> None:
    for path in UPLOAD_DIR.glob(f"{user_id}-*.mp3"):
        path.unlink(missing_ok=True)


def clear_staged_uploads() -> None:
    for path in UPLOAD_DIR.glob("*.mp3"):
        path.unlink(missing_ok=True)
