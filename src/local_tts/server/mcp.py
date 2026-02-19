from __future__ import annotations

import contextvars
import logging
from urllib.parse import parse_qs

import numpy as np
from fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

from ..engines.base import SAMPLE_RATE
from ..engines.registry import get_registry

logger = logging.getLogger(__name__)

DEFAULT_VOICES = {
    "kokoro": "af_heart",
    "pocket": "alba",
    "kitten": "bella",
}

_mcp_model: contextvars.ContextVar[str] = contextvars.ContextVar("mcp_model", default="kokoro")
_mcp_voice: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcp_voice", default=None)

mcp = FastMCP("local-tts")


@mcp.tool()
async def text_to_speech(
    text: str,
    speed: float = 1.0,
) -> str:
    """Synthesize text to speech and play it on the server's audio output.

    Args:
        text: The text to synthesize.
        speed: Speech speed multiplier (0.25 - 4.0).
    """
    from ..client.player import AudioPlayer

    model = _mcp_model.get()
    voice = _mcp_voice.get() or DEFAULT_VOICES.get(model, "af_heart")
    engine = get_registry().get(model)

    chunks: list[np.ndarray] = []
    async for chunk in engine.generate_audio_stream(text, voice, speed):
        chunks.append(chunk)

    if not chunks:
        return f"No audio generated for: {text!r}"

    player = AudioPlayer(sample_rate=SAMPLE_RATE)
    player.start()
    try:
        for chunk in chunks:
            player.play_chunk(chunk)
        player.drain()
    finally:
        player.stop()

    total_samples = sum(len(c) for c in chunks)
    duration = total_samples / SAMPLE_RATE

    return f"Spoke {len(text)} chars in {duration:.1f}s using {model}/{voice}"


class _MCPMiddleware:
    """Extract model/voice query parameters and set them as context vars."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        params = parse_qs(scope.get("query_string", b"").decode())
        model_token = _mcp_model.set(params.get("model", ["kokoro"])[0])
        voice_values = params.get("voice")
        voice_token = _mcp_voice.set(voice_values[0] if voice_values else None)
        try:
            await self.app(scope, receive, send)
        finally:
            _mcp_model.reset(model_token)
            _mcp_voice.reset(voice_token)


class NormalizeMountPath:
    """Append trailing slash to a mount path so Starlette's Mount matches it.

    Starlette's ``Mount("/mcp")`` only matches ``/mcp/…``, not ``/mcp``.
    This middleware rewrites the path before routing so both forms work.
    """

    def __init__(self, app: ASGIApp, *, path: str) -> None:
        self.app = app
        self.path = path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == self.path:
            scope = dict(scope, path=self.path + "/")
        await self.app(scope, receive, send)


def create_mcp_app() -> ASGIApp:
    """Create the MCP ASGI app with query-parameter config support."""
    app = mcp.http_app(path="/")
    wrapped = _MCPMiddleware(app)
    # Expose the lifespan so it can be composed with the parent FastAPI app.
    wrapped.lifespan = app.router.lifespan_context  # type: ignore[attr-defined]
    return wrapped
