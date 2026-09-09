from __future__ import annotations

from dataclasses import dataclass

from translator.audio.types import AudioSource


@dataclass(frozen=True)
class CaptionLine:
    speaker_id: int
    speaker_name: str
    text: str
    is_partial: bool
    source: AudioSource


@dataclass(frozen=True)
class SpeakerInfo:
    speaker_id: int
    name: str
    source: AudioSource


@dataclass(frozen=True)
class PipelineStatus:
    listening: bool
    message: str
    device: str
    asr_model: str
    phase: str = "stopped"
