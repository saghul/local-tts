from __future__ import annotations

import logging
from typing import Any

from .base import ModelOptions, TTSEngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, TTSEngine] = {}

    def register(self, engine: TTSEngine) -> None:
        logger.info("Registering TTS engine: %s", engine.name)
        self._engines[engine.name] = engine

    def get(self, name: str) -> TTSEngine:
        if name not in self._engines:
            available = ", ".join(self._engines.keys())
            raise ValueError(f"Unknown engine: {name!r}. Available: {available}")
        return self._engines[name]

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"model_id": name, "name": name.title()}
            for name in self._engines
        ]

    @property
    def engine_names(self) -> list[str]:
        return list(self._engines.keys())


_registry = EngineRegistry()


def get_registry() -> EngineRegistry:
    return _registry


def initialize_engines(model_options: ModelOptions | None = None) -> None:
    if model_options is None:
        model_options = ModelOptions()

    disabled = model_options.disabled

    from .kitten import KittenEngine
    from .kokoro import KokoroEngine
    from .pocket import PocketEngine

    engines = []

    if "kokoro" not in disabled:
        kokoro = KokoroEngine()
        _registry.register(kokoro)
        engines.append(kokoro)

    if "pocket" not in disabled:
        pocket = PocketEngine()
        _registry.register(pocket)
        engines.append(pocket)

    if "kitten" not in disabled:
        kitten = KittenEngine(model_size=model_options.kitten.model_size)
        _registry.register(kitten)
        engines.append(kitten)

    if model_options.preload and engines:
        logger.info("Preloading models (this may take a while on first run)...")
        for engine in engines:
            engine.warmup()
        logger.info("All models preloaded")
