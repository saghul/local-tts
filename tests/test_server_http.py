"""Tests for HTTP streaming endpoints."""

import numpy as np


def test_list_models(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    models = r.json()
    assert len(models) == 1
    assert models[0]["model_id"] == "fake"


def test_list_voices(client):
    r = client.get("/v1/voices?model_id=fake")
    assert r.status_code == 200
    voices = r.json()
    assert len(voices) == 2
    assert voices[0]["voice_id"] == "test_voice"


def test_list_voices_unknown_model(client):
    r = client.get("/v1/voices?model_id=nonexistent")
    assert r.status_code == 400


def test_stream_tts(client):
    r = client.post(
        "/v1/text-to-speech/test_voice/stream",
        json={"text": "hello world", "model_id": "fake"},
    )
    assert r.status_code == 200
    assert "audio/pcm" in r.headers["content-type"]

    audio = np.frombuffer(r.content, dtype=np.int16)
    # FakeEngine: 3 chunks * 2400 samples = 7200 samples
    assert len(audio) == 7200
    assert audio.dtype == np.int16
    # Should contain non-zero audio (sine wave)
    assert np.any(audio != 0)


def test_stream_tts_unknown_model(client):
    r = client.post(
        "/v1/text-to-speech/test_voice/stream",
        json={"text": "hello", "model_id": "nonexistent"},
    )
    assert r.status_code == 400


def test_stream_tts_with_speed(client):
    r = client.post(
        "/v1/text-to-speech/test_voice/stream",
        json={
            "text": "hello",
            "model_id": "fake",
            "voice_settings": {"speed": 1.5},
        },
    )
    assert r.status_code == 200
    audio = np.frombuffer(r.content, dtype=np.int16)
    assert len(audio) == 7200
