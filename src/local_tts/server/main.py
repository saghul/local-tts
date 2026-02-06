from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..engines.registry import initialize_engines
from .routes import router
from .websocket import ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_engines()
    logger.info("TTS engines initialized")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Local TTS Server",
        description="ElevenLabs-compatible local TTS server",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(ws_router)
    return app


def run_server(host: str = "0.0.0.0", port: int = 8880) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = create_app()
    try:
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        pass
    # Work around a sentencepiece bug: its absl::Flag<bool> C++ destructor
    # crashes during normal process exit (__cxa_finalize_ranges). Using
    # _exit() skips C++ static destructors entirely.
    # https://github.com/google/sentencepiece/issues/1069
    os._exit(0)
