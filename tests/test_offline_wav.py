from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from translator.audio.resample import resample_mono, to_mono
from translator.diarization.speakers import SpeakerRegistry, SourceOnlyEncoder


def _write_wav(path: Path, samples: np.ndarray, rate: int = 48000) -> None:
    pcm = np.clip(samples, -1.0, 1.0)
    data = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(data.tobytes())


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        rate = handle.getframerate()
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return samples, rate


def test_wav_resample_and_source_speakers(tmp_path: Path) -> None:
    english = np.sin(2 * np.pi * 220 * np.linspace(0, 1, 48000, endpoint=False)).astype(np.float32) * 0.2
    portuguese = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 48000, endpoint=False)).astype(np.float32) * 0.2
    en_path = tmp_path / "en.wav"
    pt_path = tmp_path / "pt.wav"
    _write_wav(en_path, english)
    _write_wav(pt_path, portuguese)

    en_audio, en_rate = _read_wav(en_path)
    pt_audio, pt_rate = _read_wav(pt_path)
    en_16k = resample_mono(to_mono(en_audio), en_rate, 16000)
    pt_16k = resample_mono(to_mono(pt_audio), pt_rate, 16000)
    assert 15900 <= en_16k.size <= 16100
    assert 15900 <= pt_16k.size <= 16100

    registry = SpeakerRegistry(encoder=SourceOnlyEncoder())
    mic_speaker = registry.assign(en_16k, "mic")
    system_speaker = registry.assign(pt_16k, "system")
    assert mic_speaker.name == "Microfone"
    assert system_speaker.name == "Vídeo"
    assert mic_speaker.source == "mic"
    assert system_speaker.source == "system"
