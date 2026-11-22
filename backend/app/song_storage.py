from __future__ import annotations

from . import database


def create_song(
    user_id: str, song_id: str, request_json: str, status: str = "queued"
) -> None:
    now = database.now().isoformat()
    with database.connection() as connection:
        connection.execute(
            """
            INSERT INTO songs (id, user_id, status, request_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (song_id, user_id, status, request_json, now, now),
        )


def update_song(
    user_id: str,
    song_id: str,
    *,
    status: str,
    title: str | None,
    lyrics: str | None,
    error: str | None,
) -> None:
    with database.connection() as connection:
        connection.execute(
            """
            UPDATE songs
            SET status = ?, title = ?, lyrics = ?, error = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                status,
                title,
                lyrics,
                error,
                database.now().isoformat(),
                song_id,
                user_id,
            ),
        )


def get_song(user_id: str, song_id: str) -> dict[str, object] | None:
    with database.connection() as connection:
        row = connection.execute(
            "SELECT * FROM songs WHERE id = ? AND user_id = ?",
            (song_id, user_id),
        ).fetchone()
    return dict(row) if row is not None else None


def list_songs(user_id: str) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM songs
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_song(user_id: str, song_id: str) -> bool:
    with database.connection() as connection:
        cursor = connection.execute(
            "DELETE FROM songs WHERE id = ? AND user_id = ?",
            (song_id, user_id),
        )
    return cursor.rowcount == 1
