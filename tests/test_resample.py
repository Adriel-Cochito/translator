from __future__ import annotations

import numpy as np

from translator.audio.resample import rms_level, resample_mono, to_mono


def test_to_mono_averages_channels() -> None:
    stereo = np.array([[1.0, -1.0], [0.5, 0.5]], dtype=np.float32)
    mono = to_mono(stereo)
    assert mono.shape == (2,)
    assert np.allclose(mono, [0.0, 0.5])


def test_resample_preserves_length_ratio() -> None:
    source = np.linspace(-0.4, 0.4, 16000, dtype=np.float32)
    dest = resample_mono(source, 16000, 8000)
    assert dest.size == 8000


def test_resample_same_rate_is_noop_copy_safe() -> None:
    source = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    dest = resample_mono(source, 16000, 16000)
    assert np.allclose(dest, source)


def test_rms_empty_is_zero() -> None:
    assert rms_level(np.zeros(0, dtype=np.float32)) == 0.0


def test_rms_known_value() -> None:
    samples = np.ones(8, dtype=np.float32)
    assert abs(rms_level(samples) - 1.0) < 1e-6
