from __future__ import annotations

from dataclasses import dataclass

from translator.cuda_paths import register_cuda_dlls

register_cuda_dlls()

try:
    import ctranslate2
except ImportError:  # pragma: no cover
    ctranslate2 = None  # type: ignore[assignment]


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str
    reason: str


def detect_device() -> DeviceChoice:
    try:
        if ctranslate2 is None:
            return DeviceChoice("cpu", "int8", "CPU (ctranslate2 ausente)")
        count = int(ctranslate2.get_cuda_device_count())
        if count > 0:
            supported = set(ctranslate2.get_supported_compute_types("cuda"))
            if "int8" in supported:
                return DeviceChoice("cuda", "int8", f"CUDA ({count} GPU), int8")
            if "int8_float16" in supported:
                return DeviceChoice("cuda", "int8_float16", f"CUDA ({count} GPU), int8_float16")
            if "float16" in supported:
                return DeviceChoice("cuda", "float16", f"CUDA ({count} GPU), float16")
            return DeviceChoice("cuda", "default", f"CUDA ({count} GPU)")
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
