from app import storage
from app.schemas import SongRequest


def test_saved_yue2_song_plays_and_downloads_for_its_owner(api_client, tmp_path):
    api_client.post("/api/auth/guest")
    user = storage.get_user_for_session(api_client.cookies.get("song_session"))
    song_id = "saved-yue2-song"
    request = SongRequest(prompt="A song to revisit", generation_model="yue2", variation_count=2)
    storage.create_song(str(user["id"]), song_id, request.model_dump_json(), status="completed")
    (tmp_path / "generated" / f"{song_id}.mp3").write_bytes(b"first version")
    (tmp_path / "generated" / f"{song_id}-variation-2.mp3").write_bytes(b"second version")
    (tmp_path / "generated" / f"{song_id}.wav").write_bytes(b"wav version")

    songs = api_client.get("/api/songs")
    assert songs.status_code == 200
    assert songs.json()[0]["mp3_url"] == f"/api/jobs/{song_id}/mp3"

    playback = api_client.get(f"/api/jobs/{song_id}/mp3")
    assert playback.status_code == 200
    assert playback.content == b"first version"
    assert playback.headers["content-disposition"].startswith("inline;")

    second = api_client.get(f"/api/jobs/{song_id}/mp3?variation=2&download=true")
    assert second.status_code == 200
    assert second.content == b"second version"
    assert second.headers["content-disposition"].startswith("attachment;")

    wav = api_client.get(f"/api/jobs/{song_id}/wav?download=true")
    assert wav.status_code == 200
    assert wav.content == b"wav version"
    assert wav.headers["content-disposition"].startswith("attachment;")
