from app import audio
from app.schemas import SongRequest


def test_music_form_requests_30_second_clip_and_keeps_vocal_lyrics(monkeypatch):
    lyrics = "[Verse 1]\nEvery word is clear"
    monkeypatch.setattr(audio, "ACE_STEP_MODEL", "acestep-v15-xl-turbo")
    request = SongRequest(
        prompt="bright pop song",
        lyrics=lyrics,
    )
    form = audio.build_music_form(request, lyrics, 42)
    assert form["lyrics"] == lyrics
    assert form["audio_duration"] == "30"
    assert "clear diction" in form["prompt"]
    assert form["model"] == "acestep-v15-xl-turbo"

    instrumental = audio.build_music_form(
        SongRequest(prompt="bright instrumental", vocals=False), lyrics, 42
    )
    assert instrumental["lyrics"] == "[Instrumental]"
    assert "instrumental only" in instrumental["prompt"]


def test_final_audio_converts_generated_wav_and_returns_paths(tmp_path, monkeypatch):
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    monkeypatch.setattr(audio, "GENERATED_DIR", generated_dir)
    commands = []
    monkeypatch.setattr(audio.subprocess, "run", lambda command, check: commands.append(command))

    wav, mp3 = audio.finalize_audio(
        "song-id", tmp_path / "generated.wav", None, 0.2
    )

    assert wav == generated_dir / "song-id.wav"
    assert mp3 == generated_dir / "song-id.mp3"
    assert len(commands) == 2
