import asyncio
import json

from fastapi import BackgroundTasks

from app import song_routes, storage
from app.schemas import SongRequest


def test_queued_songs_and_variation_seeds(api_client, monkeypatch, tmp_path):
    api_client.post("/api/auth/guest")
    user = storage.get_user_for_session(api_client.cookies.get("song_session"))
    user_id = str(user["id"])
    first = song_routes.create_job(
        SongRequest(prompt="Dreamy piano pop", variation_count=2,
                    variation_prompts=["quiet piano", "bright drums"]),
        BackgroundTasks(), user,
    )
    second = song_routes.create_job(
        SongRequest(prompt="Warm acoustic folk"), BackgroundTasks(), user,
    )
    first_request = SongRequest.model_validate_json(storage.get_song(user_id, first.id)["request_json"])
    second_request = SongRequest.model_validate_json(storage.get_song(user_id, second.id)["request_json"])
    assert len(set(first_request.variation_seeds)) == 2
    assert first.status == second.status == "queued"

    started = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def fake_lyrics(request, *_args):
        return "Song", "[Verse]\nSing this line"

    async def fake_audio(request, lyrics, output_dir, reference, seed):
        calls.append((request.prompt, seed))
        if len(calls) == 1:
            started.set()
            await release.wait()
        path = output_dir / "generated.wav"
        path.write_bytes(b"audio")
        return path

    monkeypatch.setattr(song_routes, "generate_lyrics", fake_lyrics)
    monkeypatch.setattr(song_routes, "generate_audio", fake_audio)
    monkeypatch.setattr(song_routes, "finalize_audio", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(song_routes, "GENERATED_DIR", tmp_path)

    async def run_jobs():
        one = asyncio.create_task(song_routes._generate_song(user_id, first.id, first_request))
        await started.wait()
        two = asyncio.create_task(song_routes._generate_song(user_id, second.id, second_request))
        await asyncio.sleep(0)
        assert storage.get_song(user_id, first.id)["status"] == "generating"
        assert storage.get_song(user_id, second.id)["status"] == "queued"
        release.set()
        await asyncio.gather(one, two)

    asyncio.run(run_jobs())
    assert [seed for _, seed in calls[:2]] == first_request.variation_seeds
    assert "quiet piano" in calls[0][0]
    assert "bright drums" in calls[1][0]
    assert calls[2][1] == second_request.variation_seeds[0]
    assert storage.get_song(user_id, first.id)["status"] == "completed"
    assert storage.get_song(user_id, second.id)["status"] == "completed"
