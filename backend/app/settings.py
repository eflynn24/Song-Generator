import os
from pathlib import Path


APP_DIR = Path(os.getenv("APP_DIR", str(Path(__file__).resolve().parents[1])))
GENERATED_DIR = APP_DIR / "generated"
UPLOAD_DIR = APP_DIR / "uploads"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MUSIC_API_URL = os.getenv("MUSIC_API_URL", "http://ace-step:8001").rstrip("/")
ACE_STEP_MODEL = os.getenv("ACE_STEP_MODEL", "acestep-v15-turbo")
ACE_STEP_QUALITY_MODEL = os.getenv(
    "ACE_STEP_QUALITY_MODEL", "acestep-v15-xl-sft"
)
ACE_STEP_MODELS = {
    "turbo": (ACE_STEP_MODEL, 8, None),
    "turbo-shift1": ("acestep-v15-turbo-shift1", 8, None),
    "turbo-shift3": ("acestep-v15-turbo-shift3", 8, None),
    "sft": ("acestep-v15-sft", 50, 7.0),
    "xl-turbo": ("acestep-v15-xl-turbo", 8, None),
    "xl-sft": (ACE_STEP_QUALITY_MODEL, 50, 7.0),
}
SESSION_COOKIE = "song_session"
SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() in {
    "1",
    "true",
    "yes",
}
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost"
    ).split(",")
    if origin.strip()
]

MAX_REFERENCE_BYTES = 50 * 1024 * 1024
