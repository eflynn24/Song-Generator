from app.minimax import build_workflow
from app.schemas import SongRequest


def test_minimax_workflow_keeps_lyrics_and_uses_the_generated_length():
    request = SongRequest(
        prompt="A live acoustic arrangement", generation_model="minimax-music3",
        instruments=["guitar"], key_scale="D Major", duration_seconds=60,
        vocal_preset="natural",
    )
    lyrics = "[Verse]\nI let the rain come in"
    workflow = build_workflow(request, lyrics, 42, "test")

    encode = workflow["encode"]["inputs"]
    assert encode["lyrics"] == lyrics
    assert encode["max_duration"] == 60
    assert "D Major" in encode["caption"]
    assert "guitar with defined string attack" in encode["caption"]
    assert "close-miked lead" in encode["caption"]
    assert workflow["latent"]["inputs"]["seconds"] == ["encode", 1]
    assert workflow["sample"]["inputs"]["seed"] == encode["seed"] == 42

    instrumental = request.model_copy(update={"vocals": False})
    encode = build_workflow(instrumental, lyrics, 42, "test")["encode"]["inputs"]
    assert encode["lyrics"] == "[Instrumental]"
    assert "without sung or spoken vocals" in encode["caption"]


def test_minimax_strips_performance_notes_from_section_headings_only():
    request = SongRequest(prompt="An acoustic ballad", generation_model="minimax-music3")
    lyrics = (
        "[Verse 2 - close and conversational]\r\nI let the rain come in\r\n\r\n"
        "[Pre-Chorus — softer]\r\nLet it fall (let it fall)\r\n"
        "[Chorus: open and unforced]\r\n[Outro (quiet)]\r\n"
        "I wrote [Verse 1 - a note] on the wall"
    )

    encode = build_workflow(request, lyrics, 42, "test")["encode"]["inputs"]

    assert encode["lyrics"] == (
        "[Verse 2]\r\nI let the rain come in\r\n\r\n"
        "[Pre-Chorus]\r\nLet it fall (let it fall)\r\n"
        "[Chorus]\r\n[Outro]\r\nI wrote [Verse 1 - a note] on the wall"
    )


def test_minimax_arranges_supplied_lyrics_in_order_and_keeps_notes_out_of_sung_lines():
    lyrics = (
        "[Verse 1 - half-spoken]\nThe kettle clicks\n"
        "[Chorus]\nLeave the light on\n"
        "[Bridge]\nI open the door\n"
        "[Chorus]\nLeave the light on"
    )
    request = SongRequest(prompt="Sparse folk with piano", lyrics=lyrics, vocal_preset="natural")
    encode = build_workflow(request, lyrics, 42, "test")["encode"]["inputs"]
    caption = encode["caption"]

    assert caption.index("Verse 1:") < caption.index("Chorus:") < caption.index("Bridge:")
    assert "Performance cue: half-spoken." in caption
    assert "half-spoken" not in encode["lyrics"]
    assert "Leave the light on" not in caption
    assert encode["lyrics"] == lyrics.replace(" - half-spoken", "")
    assert caption.count("Blend quiet harmonies") == 1
    assert caption.rindex("Chorus:") < caption.index("Blend quiet harmonies")
