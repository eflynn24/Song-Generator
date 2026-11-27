from app import audio
from app.schemas import SongRequest


def test_music_form_requests_30_second_clip_and_keeps_vocal_lyrics():
    lyrics = "[Verse 1]\nEvery word is clear"
    request = SongRequest(
        prompt="bright pop song",
        lyrics=lyrics,
        generation_model="xl-turbo",
    )
    form = audio.build_music_form(request, lyrics, 42)
    assert form["lyrics"] == lyrics
    assert form["audio_duration"] == "30"
    assert "clear lead vocal" in form["prompt"]
    assert form["model"] == "acestep-v15-xl-turbo"

    instrumental = audio.build_music_form(
        SongRequest(prompt="bright instrumental", vocals=False), "", 42
    )
    assert instrumental["lyrics"] == "[Instrumental]"
    assert "instrumental only" in instrumental["prompt"]


def test_vocal_and_master_options_survive_a_full_caption():
    request = SongRequest(
        prompt="A song about the sea. " * 50,
        genres=["Rock", "Blues", "Folk / acoustic"],
        instruments=["acoustic guitar"] * 20,
        vocal_preset="harmonies",
        vocal_style="smoky alto",
        generation_model="turbo-lite",
        studio_master=True,
    )
    form = audio.build_music_form(request, "Sing to the sea", 42)
    assert len(form["prompt"]) <= 512
    assert "A song about the sea" in form["prompt"]
    assert "smoky alto" in form["prompt"]
    assert "backing harmonies" in form["prompt"]
    assert form["thinking"] == form["use_cot_caption"] == "false"
    assert form["audio_format"] == "wav32"


def test_natural_vocals_use_the_sft_schedule_and_keep_their_direction():
    request = SongRequest(prompt="an acoustic ballad", vocal_preset="natural", generation_model="xl-sft")
    form = audio.build_music_form(request, "Let the light come in", 42)

    assert "audible breaths" in form["prompt"]
    assert form["use_cot_caption"] == "false"
    assert form["shift"] == "1.0"
    assert form["inference_steps"] == "50"
    assert form["guidance_scale"] == "7.0"


def test_selected_instruments_get_performance_details_in_an_instrumental():
    request = SongRequest(prompt="a quiet instrumental", vocals=False, instruments=["guitar", "piano"])
    form = audio.build_music_form(request, "", 42)

    assert "feature guitar, piano" in form["prompt"]
    assert "defined string attack" in form["prompt"]
    assert "varied key dynamics" in form["prompt"]
    assert form["lyrics"] == "[Instrumental]"


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
    assert len(commands) == 1
    assert "pcm_s16le" in commands[0]
    assert "192k" in commands[0]


def test_studio_master_shares_filters_between_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "GENERATED_DIR", tmp_path)
    commands = []
    monkeypatch.setattr(audio.subprocess, "run", lambda command, check: commands.append(command))

    audio.finalize_audio("song-id", tmp_path / "generated.wav", studio_master=True, fade_in=True)
    audio.finalize_audio("song-id", tmp_path / "generated.wav", studio_master=True, variation=2)

    first, second = commands
    assert "pcm_s24le" in first
    assert "320k" in first and "320k" in second
    assert "loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=2,asplit=2" in first[first.index("-filter_complex") + 1]
    assert "-af" in second
    assert second[-1].endswith("-variation-2.mp3")
