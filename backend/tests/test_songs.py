import uuid

from fastapi.testclient import TestClient

from app import storage
from app.schemas import SongRequest


def test_song_api_preserves_requested_duration_without_cover_features(api_client: TestClient):
    assert api_client.post(
        "/api/auth/register",
        json={"username": "listener", "password": "a-private-password-for-listener"},
    ).status_code == 201
    user = storage.get_user_by_username("listener")
    assert user is not None
    song_id = str(uuid.uuid4())
    storage.create_song(
        str(user["id"]),
        song_id,
        SongRequest(prompt="a song with model-selected length").model_dump_json(),
        status="completed",
    )

    response = api_client.get(f"/api/jobs/{song_id}")
    assert response.status_code == 200
    job = response.json()
    assert "cover_url" not in job
    assert "cover_error" not in job
    assert "duration_seconds" not in job
    assert job["request"]["duration_seconds"] == 30
    assert job["request"]["vocal_preset"] == "auto"
    assert job["request"]["studio_master"] is False
    assert "generate_cover_art" not in job["request"]

    assert api_client.get(f"/api/songs/{song_id}/cover").status_code == 404
    assert api_client.put(
        f"/api/songs/{song_id}/cover",
        files={"file": ("cover.png", b"image", "image/png")},
    ).status_code == 404
