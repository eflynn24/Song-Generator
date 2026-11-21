import json
import math
import os
import random
import struct
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


APP_DIR = Path(os.getenv("APP_DIR", str(Path(__file__).resolve().parents[1])))
GENERATED_DIR = APP_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MUSIC_API_URL = os.getenv("MUSIC_API_URL", "").strip()

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost"
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="Local Song Generator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict] = {}


class SongRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1200)
    genre: str = Field(default="Synth-pop", max_length=80)
    mood: str = Field(default="Hopeful", max_length=80)
    bpm: int = Field(default=110, ge=40, le=220)
    duration_seconds: int = Field(default=30, ge=10, le=300)
    vocals: bool = True
    lyrics: str = Field(default="", max_length=6000)
    instruments: list[str] = Field(default=["guitar", "piano", "bass", "drums"])
    vocal_style: str = Field(default="Pop vocalist", max_length=100)


class Job(BaseModel):
    id: str
    status: Literal["queued", "generating", "completed", "failed"]
    title: str | None = None
    lyrics: str | None = None
    audio_url: str | None = None
    wav_url: str | None = None
    mp3_url: str | None = None
    error: str | None = None
    request: SongRequest


def fallback_lyrics(request: SongRequest) -> tuple[str, str]:
    title = f"{request.mood} {request.genre}".strip()
    lyrics = (
        "[Intro]\n"
        "Soft lights moving in the evening glow\n\n"
        "[Verse 1]\n"
        f"We chase the feeling that the {request.prompt.lower()} came to show\n"
        "Every heartbeat leaves a new road in the air\n\n"
        "[Chorus]\n"
        "Rise with the rhythm, turn the night to gold\n"
        "Take every spark and make it bold\n\n"
        "[Outro]\n"
        "This is our moment, this is our song"
    )
    return title, lyrics


async def generate_lyrics(request: SongRequest) -> tuple[str, str]:
    system = (
        "You write concise original song lyrics. Return JSON with exactly "
        'two string fields: "title" and "lyrics". The lyrics should include '
        "section labels such as [Verse 1], [Chorus], and [Outro]."
    )
    user = json.dumps(request.model_dump())

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "format": "json",
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
            parsed = json.loads(content)
            title = str(parsed.get("title", "")).strip()
            lyrics = str(parsed.get("lyrics", "")).strip()
            if title and lyrics:
                return title, lyrics
    except Exception:
        pass

    return fallback_lyrics(request)


def synthesize_preview(job_id: str, request: SongRequest) -> Path:
    sample_rate = 22050
    duration = request.duration_seconds
    frame_count = sample_rate * duration
    output = GENERATED_DIR / f"{job_id}.wav"
    beat_seconds = 60.0 / request.bpm
    rng = random.Random(job_id)
    chords = [
        [110.00, 130.81, 164.81],
        [98.00, 123.47, 146.83],
        [130.81, 164.81, 196.00],
        [146.83, 174.61, 220.00],
    ]

    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()

        for index in range(frame_count):
            time = index / sample_rate
            envelope = min(1.0, time * 3.0) * min(1.0, (duration - time) * 3.0)

            beat_index = int(time // beat_seconds)
            beat_phase = (time % beat_seconds) / beat_seconds
            chord = chords[(beat_index // 4) % len(chords)]

            # Soft synthesizer pad chord.
            pad = sum(
                math.sin(2 * math.pi * note * time)
                for note in chord
            ) / len(chord)

            # Warm bass note following the active chord.
            bass_note = chord[0] / 2
            bass_phase = (time % beat_seconds) / beat_seconds
            bass = math.sin(2 * math.pi * bass_note * time)
            bass *= 0.55 + 0.45 * math.exp(-3.5 * bass_phase)

            # Short plucked lead melody.
            melody_notes = [chord[0] * 2, chord[1] * 2, chord[2] * 2]
            melody_note = melody_notes[(beat_index + 1) % len(melody_notes)]
            half_beat = beat_seconds / 2
            melody_phase = (time % half_beat) / half_beat
            lead = math.sin(2 * math.pi * melody_note * time)
            lead *= math.exp(-5.0 * melody_phase)

            # Kick, snare and hat create a real rhythmic drum arrangement.
            kick_phase = (time % beat_seconds) / beat_seconds
            kick = math.sin(2 * math.pi * (55 - 25 * kick_phase) * time)
            kick *= math.exp(-12 * kick_phase)

            snare_active = beat_index % 4 in (1, 3)
            snare_phase = (time % beat_seconds) / beat_seconds
            snare = (rng.random() * 2 - 1) * math.exp(-18 * snare_phase) if snare_active else 0

            hat_phase = ((time % (beat_seconds / 2)) / (beat_seconds / 2))
            hat = (rng.random() * 2 - 1) * math.exp(-35 * hat_phase)

            signal = envelope * (
                0.10 * pad
                + 0.16 * bass
                + 0.09 * lead
                + 0.22 * kick
                + 0.08 * snare
                + 0.025 * hat
            )
            frames.extend(struct.pack("<h", int(max(-1, min(1, signal)) * 32767)))

        wav.writeframes(frames)

    return output


def encode_mp3(job_id: str, wav_path: Path) -> Path:
    mp3_path = GENERATED_DIR / f"{job_id}.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(mp3_path),
        ],
        check=True,
    )
    return mp3_path


async def generate_audio(job_id: str, request: SongRequest) -> Path:
    if MUSIC_API_URL:
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                if MUSIC_API_URL.endswith("/generate"):
                    instruments = ", ".join(request.instruments)
                    vocal_instruction = (
                        f"{request.vocal_style} vocals" if request.vocals
                        else "instrumental only, no vocals"
                    )
                    prompt = (
                        f"{request.genre}, {request.mood}, {request.bpm} BPM, "
                        f"instruments: {instruments}, {vocal_instruction}"
                    )
                    payload = {
                        "output_path": "/app/outputs",
                        "audio_duration": float(request.duration_seconds),
                        "prompt": prompt,
                        "lyrics": request.lyrics or "[verse]\n[chorus]",
                        "infer_step": 27,
                        "guidance_scale": 15.0,
                        "seed": int(job_id[:8], 16) % 2147483647,
                    }
                else:
                    payload = request.model_dump()

                response = await client.post(MUSIC_API_URL, json=payload)
                response.raise_for_status()
                result = response.json()
                remote_output = Path(str(result.get("output_path", "")))
                if remote_output.name:
                    shared_output = Path("/ace_outputs") / remote_output.name
                    if shared_output.exists():
                        output = GENERATED_DIR / f"{job_id}.wav"
                        output.write_bytes(shared_output.read_bytes())
                        return output
                if response.headers.get("content-type", "").startswith("audio/"):
                    output = GENERATED_DIR / f"{job_id}.wav"
                    output.write_bytes(response.content)
                    return output
        except Exception:
            pass

    return synthesize_preview(job_id, request)


@app.get("/api/health")
async def health():
    ollama = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama = response.status_code == 200
    except Exception:
        pass
    return {
        "status": "ok",
        "ollama": ollama,
        "music_api": bool(MUSIC_API_URL),
    }


@app.post("/api/jobs", response_model=Job, status_code=202)
async def create_job(request: SongRequest):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "queued",
        "title": None,
        "lyrics": None,
        "audio_url": None,
        "wav_url": None,
        "mp3_url": None,
        "error": None,
        "request": request,
    }
    jobs[job_id] = job

    job["status"] = "generating"
    try:
        title, lyrics = await generate_lyrics(request)
        output = await generate_audio(job_id, request)
        mp3_output = encode_mp3(job_id, output)
        job["title"] = title
        job["lyrics"] = lyrics
        job["audio_url"] = f"/api/jobs/{job_id}/mp3"
        job["wav_url"] = f"/api/jobs/{job_id}/wav"
        job["mp3_url"] = f"/api/jobs/{job_id}/mp3"
        job["status"] = "completed"
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)

    return Job.model_validate(job)


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return Job.model_validate(job)


@app.get("/api/jobs/{job_id}/wav")
async def get_wav(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    output = GENERATED_DIR / f"{job_id}.wav"
    if not output.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(output, media_type="audio/wav", filename=f"{job_id}.wav")


@app.get("/api/jobs/{job_id}/mp3")
async def get_mp3(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    output = GENERATED_DIR / f"{job_id}.mp3"
    if not output.exists():
        raise HTTPException(status_code=404, detail="MP3 not found")
    return FileResponse(output, media_type="audio/mpeg", filename=f"{job_id}.mp3")


@app.get("/api/jobs/{job_id}/audio")
async def get_audio(job_id: str):
    return await get_mp3(job_id)

