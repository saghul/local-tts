from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0
    use_speaker_boost: bool = True
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


class TTSRequest(BaseModel):
    text: str
    model_id: str = "kokoro"
    voice_settings: VoiceSettings | None = None


class VoiceResponse(BaseModel):
    voice_id: str
    name: str
    category: str


class ModelResponse(BaseModel):
    model_id: str
    name: str


class WSTextMessage(BaseModel):
    text: str
    voice_settings: VoiceSettings | None = None
    try_trigger_generation: bool | None = None
    flush: bool | None = None


class WSAudioMessage(BaseModel):
    audio: str = ""
    isFinal: bool = False
