from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from translator.cuda_paths import register_cuda_dlls

register_cuda_dlls()

try:
    import ctranslate2
except ImportError:  # pragma: no cover
    ctranslate2 = None  # type: ignore[assignment]

HIGH_VRAM_MB = 6144


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str
    reason: str


def cuda_vram_mb() -> int | None:
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=flags,
            env=os.environ.copy(),
        )
        values: list[int] = []
        for line in completed.stdout.splitlines():
            token = line.strip().split()[0] if line.strip() else ""
            if token.replace(".", "", 1).isdigit():
                values.append(int(float(token)))
        return max(values) if values else None
    except Exception:
        return None


def is_high_vram(vram_mb: int | None) -> bool:
    return vram_mb is None or vram_mb >= HIGH_VRAM_MB


def pick_cuda_compute_type(supported: set[str], vram_mb: int | None) -> str:
    order = (
        ("float16", "int8_float16", "int8", "float32")
        if is_high_vram(vram_mb)
        else ("int8", "int8_float16", "float16", "float32")
    )
    for compute_type in order:
        if compute_type in supported:
            return compute_type
    return "default"


def nllb_runtime(device_choice: DeviceChoice, vram_mb: int | None) -> tuple[str, str]:
    if device_choice.device != "cuda":
        return "cpu", "int8"
    if vram_mb is not None and vram_mb < HIGH_VRAM_MB:
        return "cpu", "int8"
    return device_choice.device, device_choice.compute_type


def detect_device() -> DeviceChoice:
    try:
        if ctranslate2 is None:
            return DeviceChoice("cpu", "int8", "CPU (ctranslate2 ausente)")
        count = int(ctranslate2.get_cuda_device_count())
        if count > 0:
            vram = cuda_vram_mb()
            supported = set(ctranslate2.get_supported_compute_types("cuda"))
            compute_type = pick_cuda_compute_type(supported, vram)
            vram_note = f", {vram} MB" if vram is not None else ""
            return DeviceChoice("cuda", compute_type, f"CUDA ({count} GPU{vram_note}), {compute_type}")
    except Exception:
        pass
    return DeviceChoice("cpu", "int8", "CPU (GPU indisponível)")


def is_out_of_memory(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = ("out of memory", "cuda oom", "cudnn_status_alloc_failed", "failed to allocate")
    return any(marker in text for marker in markers)


def is_cuda_runtime_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = (
        "cublas",
        "cudnn",
        "cuda",
        "cannot be loaded",
        "library",
        "no kernel image",
    )
    return any(marker in text for marker in markers)
