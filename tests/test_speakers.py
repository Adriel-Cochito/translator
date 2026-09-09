from __future__ import annotations

import numpy as np

from translator.diarization.speakers import SpeakerRegistry, SourceOnlyEncoder, cosine_similarity


class FakeEncoder(SourceOnlyEncoder):
    def __init__(self) -> None:
        self.vectors = {
            "mic": np.array([1.0, 0.0, 0.0], dtype=np.float32),
            "system-a": np.array([0.0, 1.0, 0.0], dtype=np.float32),
            "system-b": np.array([0.0, 0.0, 1.0], dtype=np.float32),
        }
        self.next_system = "system-a"

    def encode(self, audio: np.ndarray, source: str) -> np.ndarray | None:
        del audio
        if source == "mic":
            return self.vectors["mic"]
        if self.next_system == "system-a":
            self.next_system = "system-b"
            return self.vectors["system-a"]
        return self.vectors["system-b"]


def test_cosine_identical_vectors() -> None:
    vector = np.array([0.3, 0.4, 0.0], dtype=np.float32)
    assert cosine_similarity(vector, vector) > 0.99


def test_source_only_keeps_one_person_per_source() -> None:
    registry = SpeakerRegistry(encoder=SourceOnlyEncoder())
    silence = np.zeros(16000, dtype=np.float32)
    first = registry.assign(silence, "mic")
    second = registry.assign(silence, "mic")
    remote = registry.assign(silence, "system")
    assert first.speaker_id == second.speaker_id == 1
    assert first.name == "Microfone"
    assert remote.speaker_id == 2
    assert remote.name == "Vídeo"


def test_different_embeddings_on_same_source_create_new_person() -> None:
    registry = SpeakerRegistry(threshold=0.8, new_speaker_threshold=0.4, encoder=FakeEncoder())
    audio = np.zeros(16000, dtype=np.float32)
    person_a = registry.assign(audio, "system")
    person_b = registry.assign(audio, "system")
    assert person_a.speaker_id == 1
    assert person_b.speaker_id == 2
    assert person_a.name == "Pessoa 1"
    assert person_b.name == "Pessoa 2"


def test_similar_embeddings_stay_same_person() -> None:
    class NearEncoder(SourceOnlyEncoder):
        def __init__(self) -> None:
            self.toggle = False

        def encode(self, audio: np.ndarray, source: str) -> np.ndarray | None:
            del audio, source
            if not self.toggle:
                self.toggle = True
                return np.array([1.0, 0.2, 0.0], dtype=np.float32)
            return np.array([1.0, 0.35, 0.05], dtype=np.float32)

    registry = SpeakerRegistry(encoder=NearEncoder())
    audio = np.zeros(16000, dtype=np.float32)
    first = registry.assign(audio, "system")
    second = registry.assign(audio, "system")
    assert first.speaker_id == second.speaker_id == 1


def test_short_clip_does_not_create_new_person() -> None:
    class JumpEncoder(SourceOnlyEncoder):
        def encode(self, audio: np.ndarray, source: str) -> np.ndarray | None:
            del source
            if audio.size < 4000:
                return np.array([0.0, 1.0, 0.0], dtype=np.float32)
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)

    registry = SpeakerRegistry(encoder=JumpEncoder())
    long_audio = np.zeros(16000, dtype=np.float32)
    short_audio = np.zeros(2000, dtype=np.float32)
    first = registry.assign(long_audio, "system")
    second = registry.assign(short_audio, "system")
    assert first.speaker_id == second.speaker_id == 1


def test_rename_does_not_renumber() -> None:
    registry = SpeakerRegistry(encoder=SourceOnlyEncoder())
    audio = np.zeros(8000, dtype=np.float32)
    first = registry.assign(audio, "mic")
    second = registry.assign(audio, "system")
    registry.rename(first.speaker_id, "Você")
    assert registry.display_name(first.speaker_id) == "Você"
    assert registry.display_name(second.speaker_id) == "Vídeo"
    assert [speaker.speaker_id for speaker in registry.speakers()] == [1, 2]
