from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import auth_routes, database, media, song_routes
from app.main import app


BOOTSTRAP_PASSWORD = "temporary-bootstrap-password-for-tests"


@pytest.fixture
def api_client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    generated_dir = tmp_path / "generated"
    upload_dir = tmp_path / "uploads"
    generated_dir.mkdir()
    upload_dir.mkdir()
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "songs.sqlite3")
    monkeypatch.setattr(media, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(media, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(song_routes, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(song_routes, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(auth_routes, "SESSION_COOKIE_SECURE", False)
    monkeypatch.setenv("DEFAULT_USER_PASSWORD", BOOTSTRAP_PASSWORD)
    with TestClient(app) as client:
        yield client
