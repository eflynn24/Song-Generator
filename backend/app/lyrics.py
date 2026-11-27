import json
import logging

import httpx

from .schemas import SongRequest


logger = logging.getLogger(__name__)

LYRIC_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
}

VOCAL_SECTION_CUES = {
    "natural": {
        "Verse 1": "close and conversational",
        "Verse 2": "close and conversational",
        "Chorus": "open and unforced",
        "Bridge": "soft and exposed",
    },
    "harmonies": {"Chorus": "lead with light backing harmonies"},
}


def _song_title(request: SongRequest) -> str:
    genre = ", ".join(request.genres) if request.genres else request.genre
    title = f"{request.mood} {genre}".strip()
    if title:
        return title
    return request.prompt.strip().rstrip(".!?")[:60].strip() or "Untitled song"


def _lyric_format(duration: int) -> tuple[dict, list[tuple[str, str]]]:
    line_counts = {
        "chorus": (2, 2 if duration <= 60 else 4),
        "verse_one": (3, 4),
    }
    sections = [("Verse 1", "verse_one"), ("Chorus", "chorus")]
    if duration > 30:
        line_counts["verse_two"] = (3, 4)
        sections += [("Verse 2", "verse_two"), ("Chorus", "chorus")]
    if duration >= 90:
        line_counts["bridge"] = (2, 2 if duration == 90 else 4)
        sections += [("Bridge", "bridge"), ("Chorus", "chorus")]
    properties = {"title": {"type": "string"}}
    for name, (minimum, maximum) in line_counts.items():
        properties[name] = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": minimum,
            "maxItems": maximum,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }, sections


def _render_lyrics(
    payload: dict, lyric_format: dict, sections: list[tuple[str, str]], vocal_preset: str,
) -> tuple[str, str]:
    title = payload["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("The lyrics model returned an empty or invalid title.")
    cues = VOCAL_SECTION_CUES.get(vocal_preset, {})
    rendered = []
    for heading, key in sections:
        lines = payload[key]
        bounds = lyric_format["properties"][key]
        if (
            not isinstance(lines, list)
            or not bounds["minItems"] <= len(lines) <= bounds["maxItems"]
            or any(
                not isinstance(line, str)
                or not line.strip()
                or len(line.splitlines()) != 1
                or line.lstrip().startswith("[")
                for line in lines
            )
        ):
            raise ValueError(f"The lyrics model returned an invalid {key} section.")
        cue = cues.get(heading)
        label = f"{heading} - {cue}" if cue else heading
        rendered.append("\n".join([f"[{label}]", *(line.strip() for line in lines)]))
    return title.strip(), "\n\n".join(rendered)


def fallback_lyrics(request: SongRequest) -> tuple[str, str]:
    verse = (
        "[Verse 1]\n"
        "The porch light keeps a ring of rain\n"
        "Your key still cools beside the door\n"
        "I turn it in my palm again\n"
        "As though a room could ask for more"
    )
    chorus = (
        "[Chorus]\n"
        "Leave the light where I can see it\n"
        "Let the dark decide what stays"
    )
    if request.duration_seconds <= 30:
        return _song_title(request), f"{verse}\n\n{chorus}"

    second_verse = (
        "[Verse 2]\n"
        "By spring the hinge gives up its rust\n"
        "I oil it with the window wide\n"
        "The sill wears half an inch of dust\n"
        "Where I once left your name to dry"
    )
    sections = [verse, chorus, second_verse, chorus]
    if request.duration_seconds >= 90:
        sections += [
            "[Bridge]\nI thought the lamp was calling you\nI see what it was keeping now",
            chorus,
        ]
    return _song_title(request), "\n\n".join(sections)


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

    genre_instruction = (
        f" Match the selected genre(s): {', '.join(request.genres)}."
        if request.genres
        else f" Match the requested genre: {request.genre}."
        if request.genre.strip()
        else ""
    )
    language = LYRIC_LANGUAGES.get(request.vocal_language)
    language_instruction = (
        f"Write the sung lines in {language}."
        if language
        else "Write the sung lines in the language requested by the song description."
    )
    lyric_format, sections = _lyric_format(request.duration_seconds)
    system = (
        f"Write an original song from the supplied brief. {language_instruction} "
        f"It runs about {request.duration_seconds} seconds. "
        "Start by writing a chorus hook the singer could actually say. Build the title from "
        "its most distinctive phrase. Let the verses give that same hook a deeper meaning. "
        "Make the opening instantly distinctive: begin with a short instrumental signature "
        "that leads straight into a vivid first vocal line, or open directly on the hook when "
        "that better fits the brief. Avoid a long ambient intro, throat-clearing, or generic "
        "setup. Give the first line a concrete image, strong verb, and natural melodic shape. "
        "Open the first verse with an action and a sensory detail from the brief. In the next "
        "verse, show a consequence or a choice. Use the bridge, when present, to change the "
        "singer's perspective. Stay with one central image and point of view. "
        "Read the lines as speech. Stress the important words, aim for roughly 6 to 10 sung "
        "syllables per line where natural, and keep corresponding verse lines close in length. "
        "Fit a supplied tempo and meter. Leave room for breaths between phrases. "
        "Favor internal echoes or slant rhyme "
        "over forced end rhyme or inverted word order. Use concrete nouns and verbs. "
        "Use one sung line per array item, without labels or directions. Write the chorus once."
        + genre_instruction
    )
    prompt = request.model_dump(include={
        "prompt", "mood", "vocal_style", "vocal_preset", "bpm", "time_signature",
    }, exclude_none=True)
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
                    "format": lyric_format,
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            return _render_lyrics(payload, lyric_format, sections, request.vocal_preset)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        logger.warning("Lyrics model unavailable; using built-in lyrics.", exc_info=True)
        return fallback_lyrics(request)
