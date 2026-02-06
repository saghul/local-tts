"""Tests for TTS engine abstraction and registry."""

import asyncio

import numpy as np
import pytest

from local_tts.engines.base import SAMPLE_RATE, VoiceInfo
from local_tts.engines.registry import EngineRegistry

from conftest import FakeEngine


def test_fake_engine_properties():
    engine = FakeEngine()
    assert engine.name == "fake"
    voices = engine.list_voices()
    assert len(voices) == 2
    assert all(isinstance(v, VoiceInfo) for v in voices)


@pytest.mark.asyncio
async def test_fake_engine_generates_audio():
    engine = FakeEngine(num_chunks=3, samples_per_chunk=2400)
    chunks = []
    async for chunk in engine.generate_audio_stream("test", "test_voice"):
        chunks.append(chunk)

    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk.dtype == np.int16
        assert chunk.shape == (2400,)
        # Sine wave should have non-zero values
        assert np.any(chunk != 0)


@pytest.mark.asyncio
async def test_fake_engine_output_is_deterministic():
    engine = FakeEngine(num_chunks=2)
    chunks1 = []
    async for chunk in engine.generate_audio_stream("test", "test_voice"):
        chunks1.append(chunk)

    chunks2 = []
    async for chunk in engine.generate_audio_stream("test", "test_voice"):
        chunks2.append(chunk)

    for c1, c2 in zip(chunks1, chunks2):
        np.testing.assert_array_equal(c1, c2)


def test_registry_register_and_get():
    registry = EngineRegistry()
    engine = FakeEngine(engine_name="test_engine")
    registry.register(engine)
    assert registry.get("test_engine") is engine


def test_registry_unknown_engine():
    registry = EngineRegistry()
    with pytest.raises(ValueError, match="Unknown engine"):
        registry.get("nonexistent")


def test_registry_list_models():
    registry = EngineRegistry()
    registry.register(FakeEngine(engine_name="engine_a"))
    registry.register(FakeEngine(engine_name="engine_b"))
    models = registry.list_models()
    assert len(models) == 2
    ids = [m["model_id"] for m in models]
    assert "engine_a" in ids
    assert "engine_b" in ids
