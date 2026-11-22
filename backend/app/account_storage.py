from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import uuid

from . import database


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,31}$")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_user(username: str, password: str) -> dict[str, str]:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Use 3–32 letters, numbers, dots, underscores, or hyphens.")
    if len(password) < database.MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {database.MIN_PASSWORD_LENGTH} characters."
        )

    user_id = str(uuid.uuid4())
    try:
        with database.connection() as connection:
            connection.execute(
                """
                INSERT INTO users (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    database.hash_password(password),
                    database.now().isoformat(),
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("That username is already registered.") from exc
    return {"id": user_id, "username": username}


def create_guest() -> tuple[dict[str, object], str]:
    user_id = str(uuid.uuid4())
    username = f"guest-{secrets.token_hex(8)}"
    password_hash = database.hash_password(secrets.token_urlsafe(32))
    with database.connection() as connection:
        connection.execute(
            """
            INSERT INTO users
                (id, username, password_hash, is_guest, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (user_id, username, password_hash, database.now().isoformat()),
        )
    token = create_session(user_id)
    return {"id": user_id, "username": username, "is_guest": True}, token


def get_user_by_username(username: str) -> dict[str, object] | None:
    with database.connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, must_change_password, is_guest
            FROM users WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    with database.connection() as connection:
        row = connection.execute(
            "SELECT is_guest FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise ValueError("User does not exist.")
        ttl = (
            database.GUEST_SESSION_TTL
            if row["is_guest"]
            else database.SESSION_TTL
        )
        expires_at = (database.now() + ttl).isoformat()
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )
    return token


def get_user_for_session(token: str) -> dict[str, object] | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = database.now().isoformat()
    with database.connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username, users.must_change_password, users.is_guest
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
        if row is None:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        elif row["is_guest"]:
            connection.execute(
                "UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
                ((database.now() + database.GUEST_SESSION_TTL).isoformat(), token_hash),
            )
    return dict(row) if row is not None else None


def delete_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with database.connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def delete_guest(user_id: str) -> list[str]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT songs.id FROM songs JOIN users ON users.id = songs.user_id
            WHERE users.id = ? AND users.is_guest = 1
            """,
            (user_id,),
        ).fetchall()
        connection.execute("DELETE FROM users WHERE id = ? AND is_guest = 1", (user_id,))
    return [str(row["id"]) for row in rows]


def purge_expired_guests() -> tuple[list[str], list[str]]:
    now = database.now().isoformat()
    with database.connection() as connection:
        user_rows = connection.execute(
            """
            SELECT users.id FROM users
            WHERE users.is_guest = 1
              AND NOT EXISTS (
                  SELECT 1 FROM sessions
                  WHERE sessions.user_id = users.id AND sessions.expires_at > ?
              )
            """,
            (now,),
        ).fetchall()
        expired_user_ids = [str(row["id"]) for row in user_rows]
        rows = connection.execute(
            """
            SELECT songs.id FROM songs
            JOIN users ON users.id = songs.user_id
            WHERE users.is_guest = 1
              AND NOT EXISTS (
                  SELECT 1 FROM sessions
                  WHERE sessions.user_id = users.id AND sessions.expires_at > ?
              )
            """,
            (now,),
        ).fetchall()
        connection.execute(
            """
            DELETE FROM users
            WHERE is_guest = 1 AND NOT EXISTS (
                SELECT 1 FROM sessions
                WHERE sessions.user_id = users.id AND sessions.expires_at > ?
            )
            """,
            (now,),
        )
    return expired_user_ids, [str(row["id"]) for row in rows]


def update_password(user_id: str, password: str) -> None:
    if len(password) < database.MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {database.MIN_PASSWORD_LENGTH} characters."
        )
    with database.connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 0
            WHERE id = ?
            """,
            (database.hash_password(password), user_id),
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
