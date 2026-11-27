import asyncio

import pytest

from app.lyrics import _lyric_format, _render_lyrics, generate_lyrics
from app.schemas import SongRequest


def test_lyrics_repeat_the_hook_and_add_section_cues_for_natural_lead():
    lyric_format, sections = _lyric_format(60)
    payload = {
        "title": "Leave the Light",
        "verse_one": ["I sand the sill", "The paint curls back", "Your key stays put"],
        "chorus": ["Leave the light", "I know the way"],
        "verse_two": ["I shut the gate", "The key turns once", "I walk to town"],
    }

    title, lyrics = _render_lyrics(payload, lyric_format, sections, "natural")

    assert title == "Leave the Light"
    assert "[Verse 2 - close and conversational]" in lyrics
    assert lyrics.count("[Chorus - open and unforced]\nLeave the light\nI know the way") == 2

    payload["verse_one"][0] = "[Outro]\nI sand the sill"
    with pytest.raises(ValueError, match="verse_one"):
        _render_lyrics(payload, lyric_format, sections, "natural")


def test_supplied_lyrics_keep_the_authors_vocal_directions():
    lines = "[Verse 1 - half-spoken]\nI sand the sill\n\n[Chorus]\nLeave the light"
    request = SongRequest(prompt="a song about returning", lyrics=lines, vocal_preset="natural")
    _, lyrics = asyncio.run(generate_lyrics(request, "http://unused", "unused"))
    assert lyrics == lines
