import sqlite3
from datetime import datetime, timedelta, timezone

from app import database, storage
from app.schemas import SongRequest


def test_schema_migration_preserves_existing_account_and_song(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.sqlite3"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE songs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT,
                lyrics TEXT,
                error TEXT,
                request_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO users VALUES ('user-1', 'alice', 'legacy-hash', 0, 'old-date');
            INSERT INTO songs VALUES (
                'song-1', 'user-1', 'completed', 'Saved song', 'saved lyrics',
                NULL, '{"prompt":"saved"}', 'old-date', 'old-date'
            );
            """
        )
    finally:
        connection.close()

    database.initialize_storage("a-private-bootstrap-password-for-tests")

    with database.connection() as connection:
        account = connection.execute(
            "SELECT username, is_guest FROM users WHERE id = 'user-1'"
        ).fetchone()
        song = connection.execute(
            "SELECT title, lyrics FROM songs WHERE id = 'song-1'"
        ).fetchone()
    assert tuple(account) == ("alice", 0)
    assert tuple(song) == ("Saved song", "saved lyrics")


def test_expired_guest_pruning_removes_session_and_song(monkeypatch, api_client):
    assert api_client.get("/api/auth/me").status_code == 401
    user, _token = storage.create_guest()
    song_id = "guest-song"
    storage.create_song(
        str(user["id"]),
        song_id,
        SongRequest(prompt="temporary guest song").model_dump_json(),
    )
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    monkeypatch.setattr(database, "now", lambda: future)

    user_ids, song_ids = storage.purge_expired_guests()

    assert user_ids == [str(user["id"])]
    assert song_ids == [song_id]
    assert storage.get_song(str(user["id"]), song_id) is None
