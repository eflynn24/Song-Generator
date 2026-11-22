import asyncio
import io
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app import media


def test_reference_upload_is_validated_and_owner_scoped(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(media, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(
        media.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="mp3\n30.0\n", stderr=""
        ),
    )
    upload = UploadFile(filename="reference.mp3", file=io.BytesIO(b"audio"))
    upload_id = asyncio.run(media.save_reference_upload("owner-a", upload))

    saved = media.reference_path("owner-a", upload_id)
    assert saved.read_bytes() == b"audio"
    with pytest.raises(HTTPException) as error:
        media.reference_path("owner-b", upload_id)
    assert error.value.status_code == 404


def test_invalid_reference_audio_is_removed(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(media, "UPLOAD_DIR", upload_dir)

    def reject_audio(command, **kwargs):
        Path(command[-1]).write_bytes(b"invalid")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(media.subprocess, "run", reject_audio)
    upload = UploadFile(filename="invalid.mp3", file=io.BytesIO(b"invalid"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(media.save_reference_upload("owner", upload))
    assert error.value.status_code == 415
    assert list(upload_dir.iterdir()) == []
