"""Tests for audio conversion utilities."""

import numpy as np

from local_tts.engines.base import float32_to_int16


def test_float32_to_int16_silence():
    silence = np.zeros(100, dtype=np.float32)
    result = float32_to_int16(silence)
    assert result.dtype == np.int16
    assert np.all(result == 0)


def test_float32_to_int16_full_scale():
    # Full positive
    ones = np.ones(10, dtype=np.float32)
    result = float32_to_int16(ones)
    assert result.dtype == np.int16
    assert np.all(result == 32767)

    # Full negative
    neg_ones = -np.ones(10, dtype=np.float32)
    result = float32_to_int16(neg_ones)
    assert np.all(result == -32767)


def test_float32_to_int16_clipping():
    # Values beyond [-1, 1] should be clipped
    loud = np.array([2.0, -2.0, 1.5, -1.5], dtype=np.float32)
    result = float32_to_int16(loud)
    assert result[0] == 32767
    assert result[1] == -32767
    assert result[2] == 32767
    assert result[3] == -32767


def test_float32_to_int16_preserves_shape():
    audio = np.random.randn(48000).astype(np.float32) * 0.5
    result = float32_to_int16(audio)
    assert result.shape == audio.shape


def test_float32_to_int16_midrange():
    half = np.array([0.5, -0.5], dtype=np.float32)
    result = float32_to_int16(half)
    assert result[0] == 16383  # int(0.5 * 32767)
    assert result[1] == -16383
