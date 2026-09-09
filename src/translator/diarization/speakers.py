from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from translator.audio.resample import TARGET_RATE
from translator.audio.types import AudioSource
from translator.paths import ecapa_dir

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]

try:
    from speechbrain.inference.speaker import EncoderClassifier
    from speechbrain.utils.fetching import LocalStrategy
except ImportError:  # pragma: no cover
    EncoderClassifier = None  # type: ignore[misc, assignment]
    LocalStrategy = None  # type: ignore[misc, assignment]


@dataclass
class Speaker:
    speaker_id: int
    name: str
    source: AudioSource
    embedding: np.ndarray
    utterance_count: int = 1


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    data = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(data))
    if norm <= 1e-8:
        return data
    return (data / norm).astype(np.float32)


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a = l2_normalize(left)
    b = l2_normalize(right)
    return float(np.clip(np.dot(a, b), -1.0, 1.0))


class SpeakerRegistry:
    def __init__(
        self,
        threshold: float = 0.38,
        new_speaker_threshold: float = 0.22,
        encoder: SpeakerEncoder | None = None,
        min_new_speaker_seconds: float = 1.0,
    ) -> None:
        self.threshold = threshold
        self.new_speaker_threshold = new_speaker_threshold
        self.min_new_speaker_samples = int(min_new_speaker_seconds * TARGET_RATE)
        self.encoder = encoder or SourceOnlyEncoder()
        self._speakers: dict[int, Speaker] = {}
        self._next_id = 1
        self._last_by_source: dict[AudioSource, int] = {}

    def reset(self) -> None:
        self._speakers.clear()
        self._next_id = 1
        self._last_by_source.clear()

    def speakers(self) -> list[Speaker]:
        return [self._speakers[key] for key in sorted(self._speakers)]

    def rename(self, speaker_id: int, name: str) -> None:
        speaker = self._speakers.get(speaker_id)
        if speaker is None:
            return
        cleaned = name.strip() or speaker.name
        speaker.name = cleaned

    def display_name(self, speaker_id: int | None) -> str:
        if speaker_id is None:
            return "Pessoa ?"
        speaker = self._speakers.get(speaker_id)
        if speaker is None:
            return "Pessoa ?"
        return speaker.name

    def assign(self, audio: np.ndarray, source: AudioSource) -> Speaker:
        embedding = self.encoder.encode(audio, source)
        if embedding is None:
            return self._reuse_or_create(source, self.encoder.fallback_embedding(source))

        embedding = l2_normalize(embedding)
        best, best_score = self._best_match(embedding, source)
        last = self.last_for_source(source)

        if best is not None and best_score >= self.threshold:
            self._reinforce(best, embedding, audio)
            self._last_by_source[source] = best.speaker_id
            return best

        if last is not None:
            last_score = cosine_similarity(embedding, last.embedding)
            if last_score >= self.new_speaker_threshold or audio.size < self.min_new_speaker_samples:
                self._last_by_source[source] = last.speaker_id
                return last

        if best is not None and best_score >= self.new_speaker_threshold:
            self._last_by_source[source] = best.speaker_id
            return best

        if last is not None and audio.size < self.min_new_speaker_samples:
            return last

        return self._create(source, embedding)

    def last_for_source(self, source: AudioSource) -> Speaker | None:
        speaker_id = self._last_by_source.get(source)
        if speaker_id is None:
            return None
        return self._speakers.get(speaker_id)

    def _best_match(self, embedding: np.ndarray, source: AudioSource) -> tuple[Speaker | None, float]:
        best: Speaker | None = None
        best_score = -1.0
        for speaker in self._speakers.values():
            if speaker.source != source:
                continue
            score = cosine_similarity(embedding, speaker.embedding)
            if score > best_score:
                best_score = score
                best = speaker
        return best, best_score

    def _reinforce(self, speaker: Speaker, embedding: np.ndarray, audio: np.ndarray) -> None:
        speaker.utterance_count += 1
        if audio.size < int(0.75 * TARGET_RATE):
            return
        speaker.embedding = l2_normalize(_ema(speaker.embedding, embedding, 0.06))

    def _reuse_or_create(self, source: AudioSource, embedding: np.ndarray) -> Speaker:
        existing = self.last_for_source(source)
        if existing is not None:
            return existing
        return self._create(source, embedding)

    def _create(self, source: AudioSource, embedding: np.ndarray) -> Speaker:
        speaker_id = self._next_id
        self._next_id += 1
        if type(self.encoder) is SourceOnlyEncoder:
            name = "Microfone" if source == "mic" else "Vídeo"
        else:
            name = f"Pessoa {speaker_id}"
        speaker = Speaker(
            speaker_id=speaker_id,
            name=name,
            source=source,
            embedding=l2_normalize(embedding),
        )
        self._speakers[speaker_id] = speaker
        self._last_by_source[source] = speaker_id
        return speaker


class SpeakerEncoder:
    def encode(self, audio: np.ndarray, source: AudioSource) -> np.ndarray | None:
        raise NotImplementedError

    def fallback_embedding(self, source: AudioSource) -> np.ndarray:
        seed = 1.0 if source == "mic" else 2.0
        return np.array([seed, 0.0, 0.0], dtype=np.float32)


class SourceOnlyEncoder(SpeakerEncoder):
    def encode(self, audio: np.ndarray, source: AudioSource) -> np.ndarray | None:
        del audio
        return self.fallback_embedding(source)


class EcapaEncoder(SpeakerEncoder):
    def __init__(self) -> None:
        if EncoderClassifier is None or torch is None:
            raise RuntimeError("speechbrain ou torch não está instalado.")
        kwargs = {
            "source": "speechbrain/spkrec-ecapa-voxceleb",
            "savedir": str(ecapa_dir()),
            "run_opts": {"device": "cpu"},
        }
        if LocalStrategy is not None:
            kwargs["local_strategy"] = LocalStrategy.COPY
        self._classifier = EncoderClassifier.from_hparams(**kwargs)

    def encode(self, audio: np.ndarray, source: AudioSource) -> np.ndarray | None:
        del source
        if audio.size < 8000 or torch is None:
            return None
        waveform = torch.from_numpy(np.asarray(audio, dtype=np.float32)).unsqueeze(0)
        with torch.no_grad():
            embedding = self._classifier.encode_batch(waveform)
        vector = embedding.squeeze().detach().cpu().numpy().astype(np.float32)
        return l2_normalize(vector)


def create_speaker_encoder(*, detect_multiple_voices: bool = False) -> SpeakerEncoder:
    if not detect_multiple_voices:
        return SourceOnlyEncoder()
    try:
        return EcapaEncoder()
    except Exception:
        return SourceOnlyEncoder()


def _ema(current: np.ndarray, incoming: np.ndarray, rate: float) -> np.ndarray:
    return ((1.0 - rate) * current + rate * incoming).astype(np.float32)
