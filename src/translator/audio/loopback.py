from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None  # type: ignore[assignment]

from translator.audio.devices import resolve_system_index
from translator.audio.resample import TARGET_RATE, resample_mono, rms_level, to_mono
from translator.audio.types import AudioChunk, enqueue_chunk


class SystemLoopbackCapture:
    def __init__(
        self,
        out_queue: queue.Queue,
        device_id: str | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._queue = out_queue
        self._device_id = device_id
        self._on_error = on_error
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="loopback-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        if pyaudio is None:
            if self._on_error:
                self._on_error("PyAudioWPatch não está instalado.")
            return

        audio = pyaudio.PyAudio()
        stream = None
        try:
            device_info = self._pick_device(audio)
            if device_info is None:
                if self._on_error:
                    self._on_error("Nenhum dispositivo de loopback WASAPI encontrado.")
                return

            native_rate = int(device_info.get("defaultSampleRate") or 48000)
            channels = max(1, int(device_info.get("maxInputChannels") or 2))
            frames = max(512, int(native_rate * 0.03))
            stream = audio.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=native_rate,
                input=True,
                input_device_index=int(device_info["index"]),
                frames_per_buffer=frames,
            )
            while not self._stop.is_set():
                raw = stream.read(frames, exception_on_overflow=False)
                data = np.frombuffer(raw, dtype=np.float32)
                if channels > 1:
                    usable = (data.size // channels) * channels
                    data = data[:usable].reshape(-1, channels)
                samples = resample_mono(to_mono(data), native_rate, TARGET_RATE)
                enqueue_chunk(
                    self._queue,
                    AudioChunk(
                        source="system",
                        samples=samples,
                        timestamp=time.monotonic(),
                        rms=rms_level(samples),
                    ),
                )
        except Exception as exc:
            if self._on_error:
                self._on_error(f"Falha no áudio do sistema: {exc}")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            audio.terminate()

    def _pick_device(self, audio) -> dict | None:  # type: ignore[no-untyped-def]
        requested = resolve_system_index(self._device_id)
        if requested is not None:
            try:
                info = audio.get_device_info_by_index(requested)
                info["index"] = requested
                return info
            except Exception:
                pass

        default_output_name = ""
        try:
            wasapi = audio.get_host_api_info_by_type(audio.paWASAPI)
            default_output = audio.get_device_info_by_index(wasapi["defaultOutputDevice"])
            default_output_name = str(default_output.get("name", ""))
        except Exception:
            default_output_name = ""

        fallback = None
        for index in range(audio.get_device_count()):
            try:
                info = audio.get_device_info_by_index(index)
            except Exception:
                continue
            if not info.get("isLoopbackDevice"):
                continue
            info = dict(info)
            info["index"] = index
            name = str(info.get("name", ""))
            if default_output_name and default_output_name in name:
                return info
            if fallback is None:
                fallback = info
        return fallback
