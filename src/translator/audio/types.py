from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Literal

import numpy as np


AudioSource = Literal["mic", "system"]


@dataclass(frozen=True)
class AudioChunk:
    source: AudioSource
    samples: np.ndarray
    timestamp: float
    rms: float


def enqueue_chunk(out_queue: queue.Queue[AudioChunk], chunk: AudioChunk) -> None:
    try:
        out_queue.put_nowait(chunk)
        return
    except queue.Full:
        pass
    try:
        out_queue.get_nowait()
    except queue.Empty:
        pass
    try:
        out_queue.put_nowait(chunk)
    except queue.Full:
        return
