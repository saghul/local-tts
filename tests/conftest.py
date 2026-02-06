from __future__ import annotations

import asyncio
from typing import AsyncIterator

import numpy as np
import pytest
from fastapi.testclient import TestClient

from local_tts.engines.base import SAMPLE_RATE, VoiceInfo, float32_to_int16
from local_tts.engines.registry import EngineRegistry, _registry
from local_tts.server.main import create_app


class FakeEngine:
    """A deterministic fake TTS engine for testing."""

    def __init__(self, engine_name: str = "fake", num_chunks: int = 3, samples_per_chunk: int = 2400):
        self._name = engine_name
        self._num_chunks = num_chunks
        self._samples_per_chunk = samples_per_chunk

    @property
    def name(self) -> str:
        return self._name

    def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(id="test_voice", name="Test Voice", language="en", gender="female"),
            VoiceInfo(id="test_voice2", name="Test Voice 2", language="en", gender="male"),
        ]

    def warmup(self) -> None:
        pass

    async def generate_audio_stream(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AsyncIterator[np.ndarray]:
        for i in range(self._num_chunks):
            # Generate a sine wave chunk so the audio is deterministic
            t = np.linspace(
                i * self._samples_per_chunk / SAMPLE_RATE,
                (i + 1) * self._samples_per_chunk / SAMPLE_RATE,
                self._samples_per_chunk,
                endpoint=False,
            )
            wave = np.sin(2 * np.pi * 440 * t).astype(np.float32)
            yield float32_to_int16(wave)


@pytest.fixture
def fake_engine():
    return FakeEngine()


@pytest.fixture
def app_with_fake_engine(fake_engine):
    """Create a FastAPI app with fake engines registered."""
    # Save original state
    original_engines = dict(_registry._engines)
    _registry._engines.clear()
    _registry.register(fake_engine)

    app = create_app()

    yield app

    # Restore
    _registry._engines.clear()
    _registry._engines.update(original_engines)


@pytest.fixture
def client(app_with_fake_engine):
    """TestClient that skips the lifespan (engines already registered)."""
    # Override lifespan to avoid loading real models
    app_with_fake_engine.router.lifespan_context = _noop_lifespan
    return TestClient(app_with_fake_engine)


from contextlib import asynccontextmanager

@asynccontextmanager
async def _noop_lifespan(app):
    yield
