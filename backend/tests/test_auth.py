import uuid

from fastapi.testclient import TestClient

from app import storage
from app.schemas import SongRequest

BOOTSTRAP_PASSWORD = "temporary-bootstrap-password-for-tests"


def test_default_user_must_change_bootstrap_password(api_client: TestClient):
    response = api_client.post(
        "/api/auth/login",
        json={"username": "user", "password": BOOTSTRAP_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    assert api_client.get("/api/songs").status_code == 403

    changed = api_client.post(
        "/api/auth/change-password",
        json={
            "current_password": BOOTSTRAP_PASSWORD,
            "new_password": "a-private-password-with-more-than-twelve",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert api_client.get("/api/songs").json() == []


def test_guest_logout_erases_guest_songs_and_files(api_client: TestClient, tmp_path):
    response = api_client.post("/api/auth/guest")
    assert response.status_code == 201
    assert response.json()["is_guest"] is True
    token = api_client.cookies.get("song_session")
    guest = storage.get_user_for_session(token)
    assert guest is not None

    song_id = str(uuid.uuid4())
    storage.create_song(
        str(guest["id"]),
        song_id,
        SongRequest(prompt="a song about moonlit gardens").model_dump_json(),
        status="completed",
    )
    generated_dir = tmp_path / "generated"
    audio_path = generated_dir / f"{song_id}.mp3"
    audio_path.write_bytes(b"mp3")

    assert api_client.post("/api/auth/logout").status_code == 204
    assert api_client.cookies.get("song_session") is None
    assert api_client.get("/api/songs").status_code == 401
    assert storage.get_song(str(guest["id"]), song_id) is None
    assert not audio_path.exists()


def test_song_library_is_user_scoped(api_client: TestClient):
    assert api_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "a-private-password-for-alice"},
    ).status_code == 201
    alice = storage.get_user_by_username("alice")
    assert alice is not None
    song_id = str(uuid.uuid4())
    request = SongRequest(prompt="a song about moonlit gardens")
    storage.create_song(str(alice["id"]), song_id, request.model_dump_json())
    storage.update_song(
        str(alice["id"]),
        song_id,
        status="completed",
        title="Moonlit Garden",
        lyrics="[Verse 1]\nSilver flowers wake",
        error=None,
    )
    assert api_client.get("/api/songs").json()[0]["title"] == "Moonlit Garden"

    api_client.post("/api/auth/logout")
    assert api_client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "a-private-password-for-bob"},
    ).status_code == 201
    assert api_client.get("/api/songs").json() == []
    assert api_client.get(f"/api/jobs/{song_id}").status_code == 404

    api_client.post("/api/auth/logout")
    assert api_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "a-private-password-for-alice"},
    ).status_code == 200
    listed = api_client.get("/api/songs").json()
    assert listed[0]["id"] == song_id
