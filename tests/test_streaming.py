from __future__ import annotations

import numpy as np

from translator.asr.streaming import UtteranceCollector
from translator.asr.vad import EnergySpeechScorer
from translator.audio.types import AudioChunk


class ForcedScorer(EnergySpeechScorer):
    def __init__(self, speech: bool) -> None:
        super().__init__()
        self.speech = speech

    def score(self, frame: np.ndarray) -> float:
        del frame
        return 0.9 if self.speech else 0.0


def _chunk(source: str, seconds: float, level: float) -> AudioChunk:
    samples = np.full(int(16000 * seconds), level, dtype=np.float32)
    return AudioChunk(source=source, samples=samples, timestamp=0.0, rms=level)  # type: ignore[arg-type]


def test_silence_does_not_emit() -> None:
    collector = UtteranceCollector(scorer=ForcedScorer(False))
    events = collector.feed(_chunk("mic", 1.0, 0.0))
    assert events == []


def test_speech_then_silence_emits_final() -> None:
    talking = UtteranceCollector(
        scorer=ForcedScorer(True),
        min_speech_seconds=0.2,
        silence_commit_seconds=0.3,
        partial_interval_seconds=10,
        min_partial_seconds=10,
    )
    events = talking.feed(_chunk("mic", 0.6, 0.2))
    assert all(event.kind == "partial" for event in events)

    talking.scorer = ForcedScorer(False)  # type: ignore[assignment]
    finals = talking.feed(_chunk("mic", 0.5, 0.0))
    kinds = [event.kind for event in finals]
    assert "final" in kinds
    final = next(event for event in finals if event.kind == "final")
    assert final.source == "mic"
    assert final.audio.size >= int(0.2 * 16000)


def test_partial_emits_while_speaking() -> None:
    collector = UtteranceCollector(
        scorer=ForcedScorer(True),
        min_partial_seconds=0.3,
        partial_interval_seconds=0.4,
        max_utterance_seconds=30,
    )
    events = collector.feed(_chunk("system", 1.0, 0.3))
    assert any(event.kind == "partial" for event in events)
    assert all(event.source == "system" for event in events)


def test_sources_are_isolated() -> None:
    collector = UtteranceCollector(
        scorer=ForcedScorer(True),
        min_partial_seconds=0.2,
        partial_interval_seconds=0.25,
    )
    mic_events = collector.feed(_chunk("mic", 0.6, 0.2))
    sys_events = collector.feed(_chunk("system", 0.6, 0.2))
    assert all(event.source == "mic" for event in mic_events)
    assert all(event.source == "system" for event in sys_events)
