from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


DATABASE_PATH = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parents[1] / "data" / "song_generator.sqlite3"),
    )
)
SESSION_TTL = timedelta(days=14)
GUEST_SESSION_TTL = timedelta(minutes=20)
MIN_PASSWORD_LENGTH = 12
BOOTSTRAP_PASSWORD_LENGTH = 24
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


@contextmanager
def connection() -> Generator[sqlite3.Connection, None, None]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(DATABASE_PATH, timeout=30)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA busy_timeout = 30000")
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=64,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def initialize_storage(default_password: str) -> tuple[list[str], list[str]]:
    with connection() as database:
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                is_guest INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_user_id ON sessions(user_id);
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                title TEXT,
                lyrics TEXT,
                error TEXT,
                request_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS songs_user_created
                ON songs(user_id, created_at DESC);
            """
        )
        user_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(users)")
        }
        if "is_guest" not in user_columns:
            database.execute(
                "ALTER TABLE users ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0"
            )
        guest_user_ids = [
            str(row["id"])
            for row in database.execute("SELECT id FROM users WHERE is_guest = 1")
        ]
        guest_song_ids = [
            str(row["id"])
            for row in database.execute(
                "SELECT songs.id FROM songs JOIN users ON users.id = songs.user_id "
                "WHERE users.is_guest = 1"
            )
        ]
        database.execute("DELETE FROM users WHERE is_guest = 1")
        default_user = database.execute(
            "SELECT id FROM users WHERE username = ?", ("user",)
        ).fetchone()
        if default_user is None:
            if len(default_password) < BOOTSTRAP_PASSWORD_LENGTH:
                raise RuntimeError(
                    "Set DEFAULT_USER_PASSWORD to a private password of at least "
                    f"{BOOTSTRAP_PASSWORD_LENGTH} characters before starting the API."
                )
            database.execute(
                """
                INSERT INTO users (id, username, password_hash, must_change_password, created_at)
                VALUES (?, 'user', ?, 1, ?)
                """,
                (str(uuid.uuid4()), hash_password(default_password), now().isoformat()),
            )
        database.execute(
            "DELETE FROM sessions WHERE expires_at <= ?", (now().isoformat(),)
        )
        database.execute(
            """
            UPDATE songs
            SET status = 'failed',
                error = 'Generation was interrupted by a server restart.',
                updated_at = ?
            WHERE status IN ('queued', 'generating')
            """,
            (now().isoformat(),),
        )
    DATABASE_PATH.chmod(0o600)
    return guest_user_ids, guest_song_ids
