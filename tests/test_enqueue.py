from __future__ import annotations

import queue

import numpy as np

from translator.audio.types import AudioChunk, enqueue_chunk


def test_enqueue_drops_oldest_when_full() -> None:
    q: queue.Queue[AudioChunk] = queue.Queue(maxsize=2)
    first = AudioChunk("mic", np.zeros(4, dtype=np.float32), 1.0, 0.1)
    second = AudioChunk("mic", np.zeros(4, dtype=np.float32), 2.0, 0.2)
    third = AudioChunk("system", np.zeros(4, dtype=np.float32), 3.0, 0.3)
    enqueue_chunk(q, first)
    enqueue_chunk(q, second)
    enqueue_chunk(q, third)
    assert q.qsize() == 2
    kept = [q.get_nowait(), q.get_nowait()]
    assert kept[0].timestamp == 2.0
    assert kept[1].source == "system"
