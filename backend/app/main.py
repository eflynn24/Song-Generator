import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import media, storage
from .auth_routes import router as auth_router
from .settings import (
    CORS_ORIGINS,
    MINIMAX_URL,
    MUSIC_API_URL,
    OLLAMA_URL,
    SESSION_COOKIE_SECURE,
)
from .song_routes import router as song_router


logger = logging.getLogger(__name__)


async def _purge_expired_guests() -> None:
    while True:
        await asyncio.sleep(60)
        user_ids, song_ids = storage.purge_expired_guests()
        media.delete_song_files(song_ids)
        for user_id in user_ids:
            media.delete_user_uploads(user_id)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    expired_user_ids, expired_song_ids = storage.initialize_storage(
        os.getenv("DEFAULT_USER_PASSWORD", "")
    )
    media.delete_song_files(expired_song_ids)
    for user_id in expired_user_ids:
        media.delete_user_uploads(user_id)
    media.clear_staged_uploads()
    cleanup_task = asyncio.create_task(_purge_expired_guests())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Local Song Generator",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(song_router)


@app.get("/api/health")
async def health() -> dict[str, bool | str]:
    async with httpx.AsyncClient(timeout=2) as client:
        results = await asyncio.gather(
            client.get(f"{OLLAMA_URL}/api/tags"),
            client.get(f"{MUSIC_API_URL}/health"),
            client.get(f"{MINIMAX_URL}/system_stats"),
            return_exceptions=True,
        )
    return {
        "status": "ok",
        "ollama": isinstance(results[0], httpx.Response)
        and results[0].status_code == 200,
        "music_api": isinstance(results[1], httpx.Response)
        and results[1].status_code == 200,
        "cookie_secure": SESSION_COOKIE_SECURE,
        "minimax": isinstance(results[2], httpx.Response) and results[2].status_code == 200,
    }
