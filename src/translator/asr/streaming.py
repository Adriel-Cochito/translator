from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from translator.audio.resample import TARGET_RATE
from translator.audio.types import AudioChunk, AudioSource
from translator.asr.vad import EnergySpeechScorer, SpeechScorer


@dataclass(frozen=True)
class UtteranceEvent:
    kind: str
    source: AudioSource
    audio: np.ndarray


@dataclass
class _SourceBuffer:
    pending: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    speech: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    in_speech: bool = False
    silence_samples: int = 0
    samples_since_partial: int = 0


class UtteranceCollector:
    def __init__(
        self,
        scorer: SpeechScorer | None = None,
        speech_threshold: float = 0.55,
        min_speech_seconds: float = 1.0,
        silence_commit_seconds: float = 1.35,
        partial_interval_seconds: float = 2.4,
        min_partial_seconds: float = 2.0,
        max_utterance_seconds: float = 18.0,
    ) -> None:
        self.scorer = scorer or EnergySpeechScorer()
        self.speech_threshold = speech_threshold
        self.min_speech_samples = int(min_speech_seconds * TARGET_RATE)
        self.silence_commit_samples = int(silence_commit_seconds * TARGET_RATE)
        self.partial_interval_samples = int(partial_interval_seconds * TARGET_RATE)
        self.min_partial_samples = int(min_partial_seconds * TARGET_RATE)
        self.max_utterance_samples = int(max_utterance_seconds * TARGET_RATE)
        self._sources: dict[AudioSource, _SourceBuffer] = {
            "mic": _SourceBuffer(),
            "system": _SourceBuffer(),
        }

    def reset(self) -> None:
        self._sources = {"mic": _SourceBuffer(), "system": _SourceBuffer()}

    def feed(self, chunk: AudioChunk) -> list[UtteranceEvent]:
        state = self._sources[chunk.source]
        state.pending = np.concatenate([state.pending, chunk.samples.astype(np.float32, copy=False)])
        events: list[UtteranceEvent] = []
        window = self.scorer.window_size
        while state.pending.size >= window:
            frame = state.pending[:window]
            state.pending = state.pending[window:]
            events.extend(self._consume_frame(chunk.source, state, frame))
        return events

    def _consume_frame(self, source: AudioSource, state: _SourceBuffer, frame: np.ndarray) -> list[UtteranceEvent]:
        events: list[UtteranceEvent] = []
        speaking = self.scorer.score(frame) >= self.speech_threshold
        if speaking:
            state.in_speech = True
            state.silence_samples = 0
            state.speech = np.concatenate([state.speech, frame])
            state.samples_since_partial += frame.size
            if (
                state.speech.size >= self.min_partial_samples
                and state.samples_since_partial >= self.partial_interval_samples
            ):
                events.append(UtteranceEvent("partial", source, state.speech.copy()))
                state.samples_since_partial = 0
            if state.speech.size >= self.max_utterance_samples:
                events.append(UtteranceEvent("final", source, state.speech.copy()))
                state.speech = np.zeros(0, dtype=np.float32)
                state.in_speech = False
                state.silence_samples = 0
                state.samples_since_partial = 0
            return events

        if not state.in_speech:
            return events

        state.silence_samples += frame.size
        state.speech = np.concatenate([state.speech, frame])
        if state.silence_samples >= self.silence_commit_samples:
            if state.speech.size >= self.min_speech_samples:
                events.append(UtteranceEvent("final", source, state.speech.copy()))
            state.speech = np.zeros(0, dtype=np.float32)
            state.in_speech = False
            state.silence_samples = 0
            state.samples_since_partial = 0
        return events
