from typing import Literal

from pydantic import BaseModel, Field

from . import storage


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,31}$",
    )
    password: str = Field(min_length=storage.MIN_PASSWORD_LENGTH, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=storage.MIN_PASSWORD_LENGTH, max_length=256)


class AccountResponse(BaseModel):
    username: str
    must_change_password: bool = False
    is_guest: bool = False


class SongRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    duration_seconds: int = Field(default=30, ge=30, le=120)
    generation_model: Literal[
        "turbo-lite", "turbo", "turbo-shift1", "turbo-shift3", "sft", "xl-turbo", "xl-sft", "minimax-music3"
    ] = "turbo"
    variation_count: int = Field(default=1, ge=1, le=3)
    variation_prompts: list[str] = Field(default_factory=list, max_length=3)
    variation_seeds: list[int] = Field(default_factory=list, max_length=3)
    genres: list[
        Literal[
            "Pop", "Rock", "Hip-hop / rap", "R&B / soul", "Country", "Jazz",
            "Electronic / EDM", "Indie / alternative", "Folk / acoustic", "Metal",
            "Reggae", "Blues", "Classical / cinematic", "Latin", "Funk / disco",
        ]
    ] = Field(default_factory=list, max_length=15)
    # Kept for older saved requests that used a free-text genre field.
    genre: str = Field(default="", max_length=80)
    mood: str = Field(default="", max_length=80)
    bpm: int | None = Field(default=None, ge=40, le=220)
    key_scale: str = Field(default="", max_length=32)
    time_signature: Literal["", "2", "3", "4", "6"] = ""
    normalize_audio: bool = False
    studio_master: bool = False
    fade_in: bool = False
    fade_out: bool = False
    vocal_language: Literal[
        "en", "es", "zh", "ja", "ko", "fr", "de", "pt", "unknown"
    ] = "en"
    music_planner: bool = True
    enhance_prompt: bool = True
    lm_temperature: float = Field(default=0.85, ge=0.0, le=2.0)
    lm_cfg_scale: float = Field(default=2.0, ge=1.0, le=5.0)
    avoid: str = Field(default="", max_length=300)
    inference_steps: Literal[8, 12, 16] = 8
    vocals: bool = True
    lyrics: str = Field(default="", max_length=6000)
    instruments: list[str] = Field(default_factory=list)
    vocal_style: str = Field(default="", max_length=100)
    vocal_preset: Literal["auto", "natural", "clear", "intimate", "soul", "rock", "harmonies"] = "auto"
    reference_audio_id: str | None = None
    reference_strength: float = Field(default=0.7, ge=0.0, le=1.0)


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
    created_at: str
