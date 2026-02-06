"""Tests for WebSocket streaming endpoint."""

import base64
import json

import numpy as np


def test_websocket_basic_flow(client):
    with client.websocket_connect(
        "/v1/text-to-speech/test_voice/stream-input?model_id=fake&output_format=pcm_24000"
    ) as ws:
        # BOS
        ws.send_text(json.dumps({"text": " "}))

        # Text
        ws.send_text(json.dumps({"text": "hello world"}))

        # EOS
        ws.send_text(json.dumps({"text": ""}))

        # Receive audio chunks
        chunks = []
        while True:
            raw = ws.receive_text()
            msg = json.loads(raw)
            if msg["isFinal"]:
                break
            audio_bytes = base64.b64decode(msg["audio"])
            chunk = np.frombuffer(audio_bytes, dtype=np.int16)
            chunks.append(chunk)

        # FakeEngine: 3 chunks * 2400 samples
        assert len(chunks) == 3
        total_samples = sum(len(c) for c in chunks)
        assert total_samples == 7200


def test_websocket_multiple_text_messages(client):
    with client.websocket_connect(
        "/v1/text-to-speech/test_voice/stream-input?model_id=fake"
    ) as ws:
        # BOS
        ws.send_text(json.dumps({"text": " "}))

        # Multiple text messages
        ws.send_text(json.dumps({"text": "hello "}))
        ws.send_text(json.dumps({"text": "world"}))

        # EOS
        ws.send_text(json.dumps({"text": ""}))

        # Should receive audio
        chunks = []
        while True:
            raw = ws.receive_text()
            msg = json.loads(raw)
            if msg["isFinal"]:
                break
            chunks.append(msg["audio"])

        assert len(chunks) > 0


def test_websocket_unknown_model(client):
    with client.websocket_connect(
        "/v1/text-to-speech/test_voice/stream-input?model_id=nonexistent"
    ) as ws:
        # The server should close the connection
        try:
            ws.receive_text()
        except Exception:
            pass  # Expected: connection closed with error


def test_websocket_voice_settings(client):
    with client.websocket_connect(
        "/v1/text-to-speech/test_voice/stream-input?model_id=fake"
    ) as ws:
        # BOS with voice settings
        ws.send_text(json.dumps({
            "text": " ",
            "voice_settings": {"speed": 1.5},
        }))
        ws.send_text(json.dumps({"text": "fast speech"}))
        ws.send_text(json.dumps({"text": ""}))

        chunks = []
        while True:
            raw = ws.receive_text()
            msg = json.loads(raw)
            if msg["isFinal"]:
                break
            chunks.append(msg["audio"])

        assert len(chunks) > 0


def test_websocket_empty_eos_without_text(client):
    """EOS without any text should just send isFinal."""
    with client.websocket_connect(
        "/v1/text-to-speech/test_voice/stream-input?model_id=fake"
    ) as ws:
        # BOS
        ws.send_text(json.dumps({"text": " "}))
        # EOS immediately (no text)
        ws.send_text(json.dumps({"text": ""}))

        raw = ws.receive_text()
        msg = json.loads(raw)
        assert msg["isFinal"] is True
