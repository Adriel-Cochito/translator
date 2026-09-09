from __future__ import annotations

import queue
import time
from typing import Callable

import numpy as np

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None  # type: ignore[assignment]

from translator.audio.devices import resolve_mic_index, wasapi_input_settings
from translator.audio.resample import TARGET_RATE, resample_mono, rms_level, to_mono
from translator.audio.types import AudioChunk, enqueue_chunk


class MicrophoneCapture:
    def __init__(
        self,
        out_queue: queue.Queue,
        device_id: str | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._queue = out_queue
        self._device_id = device_id
        self._on_error = on_error
        self._stream = None

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice não está instalado.")
        device = resolve_mic_index(self._device_id)
        try:
            info = sd.query_devices(device, "input")
            native_rate = int(info.get("default_samplerate") or TARGET_RATE)
        except Exception:
            native_rate = TARGET_RATE

        blocksize = max(256, int(native_rate * 0.03))

        def callback(indata, frames, _time_info, status) -> None:  # type: ignore[no-untyped-def]
            del frames
            if status and self._on_error:
                self._on_error(str(status))
            mono = to_mono(np.array(indata, dtype=np.float32, copy=True))
            samples = resample_mono(mono, native_rate, TARGET_RATE)
            enqueue_chunk(
                self._queue,
                AudioChunk(
                    source="mic",
                    samples=samples,
                    timestamp=time.monotonic(),
                    rms=rms_level(samples),
                ),
            )

        extra = wasapi_input_settings()
        kwargs = {
            "samplerate": native_rate,
            "channels": 1,
            "dtype": "float32",
            "device": device,
            "blocksize": blocksize,
            "callback": callback,
        }
        if extra is not None:
            kwargs["extra_settings"] = extra
        try:
            self._stream = sd.InputStream(**kwargs)
        except Exception:
            kwargs.pop("extra_settings", None)
            self._stream = sd.InputStream(**kwargs)
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None
