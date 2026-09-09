from __future__ import annotations

import numpy as np

TARGET_RATE = 16000


def to_mono(samples: np.ndarray) -> np.ndarray:
    data = np.asarray(samples, dtype=np.float32)
    if data.ndim == 1:
        return data
    if data.ndim == 2:
        return np.mean(data, axis=1, dtype=np.float32)
    raise ValueError(f"Formato de áudio inválido: {data.shape}")


def resample_mono(samples: np.ndarray, source_rate: int, target_rate: int = TARGET_RATE) -> np.ndarray:
    mono = to_mono(samples)
    if source_rate <= 0:
        raise ValueError("sample rate deve ser positivo")
    if source_rate == target_rate or mono.size == 0:
        return mono.astype(np.float32, copy=False)
    duration = mono.size / float(source_rate)
    dest_count = max(1, int(round(duration * target_rate)))
    source_x = np.linspace(0.0, 1.0, mono.size, endpoint=False)
    dest_x = np.linspace(0.0, 1.0, dest_count, endpoint=False)
    return np.interp(dest_x, source_x, mono).astype(np.float32)


def rms_level(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float32))))
