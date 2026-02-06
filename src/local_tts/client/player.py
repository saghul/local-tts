from __future__ import annotations

import queue
import threading

import numpy as np
import sounddevice as sd

from ..engines.base import SAMPLE_RATE


class AudioPlayer:
    """Streams int16 PCM chunks to the default audio output device."""

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._stream: sd.OutputStream | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._done = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            # Clean up any existing stream first
            self._cleanup_locked()
            self._stop.clear()
            self._done.clear()
            # Drain any leftover items
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=2400,  # 100ms at 24kHz
            )
            self._stream.start()
            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()

    def _playback_loop(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    chunk = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if chunk is None:
                    break
                with self._lock:
                    if self._stream is not None and not self._stop.is_set():
                        self._stream.write(chunk.reshape(-1, 1))
        finally:
            self._done.set()

    def play_chunk(self, audio: np.ndarray) -> None:
        if not self._stop.is_set():
            self._queue.put(audio)

    def drain(self) -> None:
        """Wait for all queued audio to finish playing."""
        self._queue.put(None)
        self._done.wait(timeout=60)

    def interrupt(self) -> None:
        """Stop playback immediately and discard queued audio."""
        self._stop.set()
        # Drain the queue so the thread can exit
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        # Put a sentinel to unblock the thread if it's waiting on get()
        self._queue.put(None)
        self._done.wait(timeout=2)
        with self._lock:
            self._cleanup_locked()

    def stop(self) -> None:
        """Stop playback gracefully after all queued audio is played."""
        self.drain()
        with self._lock:
            self._cleanup_locked()

    def _cleanup_locked(self) -> None:
        """Close stream and thread. Must be called with self._lock held."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._thread = None
