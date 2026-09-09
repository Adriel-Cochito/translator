from __future__ import annotations

import queue
import time
from typing import Callable

from translator.audio.capture import MicrophoneCapture
from translator.audio.loopback import SystemLoopbackCapture
from translator.audio.types import AudioChunk


class AudioMixer:
    def __init__(
        self,
        on_error: Callable[[str], None] | None = None,
        max_queue: int = 200,
    ) -> None:
        self.queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=max_queue)
        self._on_error = on_error
        self._mic: MicrophoneCapture | None = None
        self._system: SystemLoopbackCapture | None = None
        self._last_rms = {"mic": 0.0, "system": 0.0}
        self._last_seen = {"mic": 0.0, "system": 0.0}
        self.capturing = False

    def start(self, mic_enabled: bool, system_enabled: bool, mic_device: str | None, system_device: str | None) -> None:
        self.stop()
        if mic_enabled:
            self._mic = MicrophoneCapture(self.queue, mic_device, self._on_error)
            try:
                self._mic.start()
            except Exception as exc:
                self._mic = None
                if self._on_error:
                    self._on_error(f"Falha no microfone: {exc}")
        if system_enabled:
            self._system = SystemLoopbackCapture(self.queue, system_device, self._on_error)
            self._system.start()
        self.capturing = bool(self._mic or self._system)

    def stop(self) -> None:
        if self._mic is not None:
            self._mic.stop()
            self._mic = None
        if self._system is not None:
            self._system.stop()
            self._system = None
        self.capturing = False
        self._drain()

    def _drain(self) -> None:
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                return

    def poll(self, timeout: float = 0.05) -> AudioChunk | None:
        try:
            chunk = self.queue.get(timeout=timeout)
        except queue.Empty:
            self._decay_idle_levels()
            return None
        self._last_rms[chunk.source] = chunk.rms
        self._last_seen[chunk.source] = time.monotonic()
        return chunk

    def levels(self) -> tuple[float, float]:
        self._decay_idle_levels()
        return self._last_rms["mic"], self._last_rms["system"]

    def _decay_idle_levels(self) -> None:
        now = time.monotonic()
        for source in ("mic", "system"):
            if now - self._last_seen[source] > 0.4:
                self._last_rms[source] = 0.0
