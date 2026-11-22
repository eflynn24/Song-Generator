import json
import logging

import httpx

from .schemas import SongRequest


logger = logging.getLogger(__name__)


def _song_title(request: SongRequest) -> str:
    title = f"{request.mood} {request.genre}".strip()
    if title:
        return title
    return request.prompt.strip().rstrip(".!?")[:60].strip() or "Untitled song"


def fallback_lyrics(request: SongRequest) -> tuple[str, str]:
    title = _song_title(request)
    lyrics = (
        "[Verse 1 - expressive]\n"
        "The morning opens slowly on the avenue\n"
        "A little light comes breaking through the blue\n"
        "I take the long way, let the moment breathe\n"
        "And find a brighter rhythm underneath\n\n"
        "[Chorus - stronger]\n"
        "We are here, we are alive\n"
        "Hear the honest voices rise\n"
        "Every word is clear and true\n"
        "Every road can start anew\n\n"
        "[Verse 2 - warm]\n"
        "The city hums a melody we know\n"
        "A steady beat beneath the afterglow\n"
        "The small things turn to something we can keep\n"
        "A promise in the quiet, not a dream\n\n"
        "[Chorus - stronger]\n"
        "We are here, we are alive\n"
        "Hear the honest voices rise\n"
        "Every word is clear and true\n"
        "Every road can start anew\n\n"
        "[Bridge - restrained]\n"
        "Take my hand and count to four\n"
        "There is room to hope once more\n\n"
        "[Outro - gentle]\n"
        "We are here, we are alive\n"
        "Hear the honest voices rise"
    )
    return title, lyrics


async def generate_lyrics(
    request: SongRequest, ollama_url: str, ollama_model: str
) -> tuple[str, str]:
    if not request.vocals:
        arrangement = (
            "[Intro - sparse instrumental]\n\n"
            "[Main Theme - full arrangement]\n\n"
            "[Instrumental Break]\n\n"
            "[Final Theme - fuller arrangement]\n\n"
            "[Outro - fade out]"
        )
        return _song_title(request), arrangement
    if request.lyrics.strip():
        return _song_title(request), request.lyrics.strip()

    system = (
        "Write original lyrics for a complete song, with clear, natural, "
        "easy-to-pronounce English and breath-length lines of about 6-10 "
        "syllables. Use a verse, repeated chorus, second verse, bridge, and "
        "outro. Use concise performance cues in section headers when useful, "
        "such as [Verse 1 - intimate], [Chorus - powerful], or "
        "[Bridge - whispered]. Match cues to the requested vocal style and "
        "use no more than one cue per header. Write enough lyrics "
        f"to fit a song about {request.duration_seconds} seconds long without "
        "cramming. Keep vocal directions in section headers, not in the sung "
        "lines. Return JSON with string fields title and lyrics only."
    )
    prompt = request.model_dump(exclude={"reference_audio_id"})
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": ollama_model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": json.dumps(prompt, ensure_ascii=False),
                        },
                    ],
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            title = str(payload.get("title", "")).strip()
            lyrics = str(payload.get("lyrics", "")).strip()
            if title and lyrics:
                return title, lyrics
            raise ValueError("The lyrics model returned an empty title or lyric.")
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        logger.warning("Lyrics model unavailable; using built-in lyrics.", exc_info=True)
        if request.lyrics.strip():
            return _song_title(request), request.lyrics.strip()
        return fallback_lyrics(request)
