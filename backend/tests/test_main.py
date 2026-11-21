from app.main import fallback_lyrics, SongRequest


def test_fallback_lyrics_have_sections():
    request = SongRequest(prompt="moving to a new city")
    title, lyrics = fallback_lyrics(request)
    assert title
    assert "[Verse 1]" in lyrics
    assert "[Chorus]" in lyrics

