from __future__ import annotations

from typing import Protocol

import numpy as np

from translator.audio.resample import rms_level

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]

try:
    from silero_vad import load_silero_vad
except ImportError:  # pragma: no cover
    load_silero_vad = None  # type: ignore[assignment]


class SpeechScorer(Protocol):
    window_size: int

    def score(self, frame: np.ndarray) -> float:
        ...


class EnergySpeechScorer:
    window_size = 512

    def __init__(self, threshold_hint: float = 0.012) -> None:
        self.threshold_hint = threshold_hint

    def score(self, frame: np.ndarray) -> float:
        rms = rms_level(frame)
        return min(1.0, rms / max(self.threshold_hint * 3.0, 1e-6))


class SileroSpeechScorer:
    window_size = 512

    def __init__(self) -> None:
        if load_silero_vad is None or torch is None:
            raise RuntimeError("silero-vad ou torch não está instalado.")
        self._model = load_silero_vad()

    def score(self, frame: np.ndarray) -> float:
        audio = np.asarray(frame, dtype=np.float32)
        if audio.size < self.window_size:
            audio = np.pad(audio, (0, self.window_size - audio.size))
        elif audio.size > self.window_size:
            audio = audio[: self.window_size]
        tensor = torch.from_numpy(audio)
        with torch.no_grad():
            output = self._model(tensor, 16000)
        if hasattr(output, "item"):
            return float(output.item())
        return float(output)


def create_speech_scorer() -> SpeechScorer:
    try:
        return SileroSpeechScorer()
    except Exception:
        return EnergySpeechScorer()
